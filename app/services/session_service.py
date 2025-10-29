"""
Session service for managing learning sessions
"""

from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime
import structlog

from app.domain.models import Session, SessionStatus, User
from app.services.supabase_client import get_supabase_client
from app.services.redis_client import session_manager
from app.services.summary_service import summary_service

logger = structlog.get_logger(__name__)


class SessionService:
    """Service for managing learning sessions"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.session_manager = session_manager
        self.summary_service = summary_service
    
    async def create_session(
        self,
        user_external_id: str,
        mode_code: str,
        language_code: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Session]:
        """
        Create a new learning session
        
        Args:
            user_external_id: External user identifier
            mode_code: Teaching mode code
            language_code: Target language code
            metadata: Optional session metadata
            
        Returns:
            Session object if successful, None otherwise
        """
        try:
            # Get or create user
            user = await self._get_or_create_user(user_external_id)
            if not user:
                logger.error("Failed to get or create user", user_external_id=user_external_id)
                return None
            
            # Validate mode and language exist
            if not await self._validate_mode_and_language(mode_code, language_code):
                logger.error("Invalid mode or language", 
                           mode_code=mode_code, 
                           language_code=language_code)
                return None
            
            # Check if user has an active session and close it
            existing_session_id = await self.session_manager.get_user_active_session(str(user.id))
            if existing_session_id:
                logger.info("Closing existing session for user", 
                          user_id=user.id,
                          existing_session_id=existing_session_id)
                await self.close_session(UUID(existing_session_id))
            
            # Generate new session ID
            session_id = uuid4()
            
            # Prepare session data for database
            session_data = {
                "id": str(session_id),
                "user_id": str(user.id),
                "mode_code": mode_code,
                "language_code": language_code,
                "metadata": metadata or {}
            }
            
            # Insert session into database
            response = self.supabase.table("sessions").insert(session_data).execute()
            
            if not response.data:
                logger.error("Failed to create session in database", session_id=session_id)
                return None
            
            session_record = response.data[0]
            
            # Prepare session data for Redis
            redis_session_data = {
                "user_id": str(user.id),
                "mode_code": mode_code,
                "language_code": language_code,
                "metadata": metadata or {}
            }
            
            # Store session in Redis
            if not await self.session_manager.create_session(str(session_id), redis_session_data):
                # Rollback database insert if Redis fails
                self.supabase.table("sessions").delete().eq("id", str(session_id)).execute()
                logger.error("Failed to create session in Redis", session_id=session_id)
                return None
            
            # Create domain model
            session = Session(
                id=session_id,
                user_id=user.id,
                mode_code=mode_code,
                language_code=language_code,
                started_at=datetime.fromisoformat(session_record["started_at"].replace("Z", "+00:00")),
                metadata=metadata or {},
                status=SessionStatus.ACTIVE
            )
            
            logger.info("Session created successfully", 
                       session_id=session_id,
                       user_id=user.id,
                       mode_code=mode_code,
                       language_code=language_code)
            
            return session
            
        except Exception as e:
            logger.error("Error creating session", 
                        user_external_id=user_external_id,
                        mode_code=mode_code,
                        language_code=language_code,
                        error=str(e))
            return None
    
    async def get_session(self, session_id: UUID) -> Optional[Session]:
        """
        Get session by ID
        
        Args:
            session_id: Session UUID
            
        Returns:
            Session object if found, None otherwise
        """
        try:
            response = self.supabase.table("sessions")\
                .select("*")\
                .eq("id", str(session_id))\
                .limit(1)\
                .execute()
            
            if not response.data:
                return None
            
            record = response.data[0]
            
            return Session(
                id=UUID(record["id"]),
                user_id=UUID(record["user_id"]),
                mode_code=record["mode_code"],
                language_code=record["language_code"],
                started_at=datetime.fromisoformat(record["started_at"].replace("Z", "+00:00")),
                closed_at=datetime.fromisoformat(record["closed_at"].replace("Z", "+00:00")) if record.get("closed_at") else None,
                metadata=record.get("metadata", {}),
                status=SessionStatus(record.get("status", "active"))
            )
            
        except Exception as e:
            logger.error("Error getting session", 
                        session_id=session_id,
                        error=str(e))
            return None
    
    async def close_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Close a session and generate summary
        
        Args:
            session_id: Session UUID
            
        Returns:
            Summary JSON if successful, None otherwise
        """
        try:
            # Get session from database
            session = await self.get_session(session_id)
            if not session:
                logger.error("Session not found for closing", session_id=session_id)
                return None
            
            if session.status == SessionStatus.CLOSED:
                logger.info("Session already closed", session_id=session_id)
                # Return existing summary if available
                existing_summary = await self.summary_service.get_summary_by_session(session_id)
                if existing_summary:
                    return existing_summary.summary_json
                return {"message": "Session already closed"}
            
            # Update session status in database
            close_time = datetime.utcnow().isoformat()
            update_response = self.supabase.table("sessions")\
                .update({
                    "closed_at": close_time,
                    "status": SessionStatus.CLOSED.value
                })\
                .eq("id", str(session_id))\
                .execute()
            
            if not update_response.data:
                logger.error("Failed to update session status", session_id=session_id)
                return None
            
            # Generate and store summary
            session_summary = await self.summary_service.generate_and_store_summary(
                session_id=session_id,
                user_id=session.user_id
            )
            
            # Clean up Redis session
            await self.session_manager.close_session(str(session_id))
            
            if session_summary:
                logger.info("Session closed successfully with summary", 
                          session_id=session_id,
                          summary_id=session_summary.id)
                return session_summary.summary_json
            else:
                logger.warning("Session closed but summary generation failed", 
                             session_id=session_id)
                return {"message": "Session closed successfully"}
                
        except Exception as e:
            logger.error("Error closing session", 
                        session_id=session_id,
                        error=str(e))
            return None
    
    async def get_user_sessions(
        self,
        user_external_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[SessionStatus] = None
    ) -> List[Session]:
        """
        Get sessions for a user
        
        Args:
            user_external_id: External user identifier
            limit: Maximum number of sessions
            offset: Pagination offset
            status_filter: Optional status filter
            
        Returns:
            List of Session objects
        """
        try:
            # Get user
            user = await self._get_user_by_external_id(user_external_id)
            if not user:
                return []
            
            query = self.supabase.table("sessions")\
                .select("*")\
                .eq("user_id", str(user.id))
            
            if status_filter:
                query = query.eq("status", status_filter.value)
            
            response = query.order("started_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            sessions = []
            for record in response.data:
                session = Session(
                    id=UUID(record["id"]),
                    user_id=UUID(record["user_id"]),
                    mode_code=record["mode_code"],
                    language_code=record["language_code"],
                    started_at=datetime.fromisoformat(record["started_at"].replace("Z", "+00:00")),
                    closed_at=datetime.fromisoformat(record["closed_at"].replace("Z", "+00:00")) if record.get("closed_at") else None,
                    metadata=record.get("metadata", {}),
                    status=SessionStatus(record.get("status", "active"))
                )
                sessions.append(session)
            
            logger.debug("Retrieved user sessions", 
                        user_external_id=user_external_id,
                        count=len(sessions))
            
            return sessions
            
        except Exception as e:
            logger.error("Error getting user sessions", 
                        user_external_id=user_external_id,
                        error=str(e))
            return []
    
    async def get_active_session_for_user(self, user_external_id: str) -> Optional[Session]:
        """
        Get active session for a user
        
        Args:
            user_external_id: External user identifier
            
        Returns:
            Active Session object if found, None otherwise
        """
        try:
            # Get user
            user = await self._get_user_by_external_id(user_external_id)
            if not user:
                return None
            
            # Check Redis first
            active_session_id = await self.session_manager.get_user_active_session(str(user.id))
            if active_session_id:
                return await self.get_session(UUID(active_session_id))
            
            # Fallback to database query
            response = self.supabase.table("sessions")\
                .select("*")\
                .eq("user_id", str(user.id))\
                .eq("status", SessionStatus.ACTIVE.value)\
                .order("started_at", desc=True)\
                .limit(1)\
                .execute()
            
            if response.data:
                record = response.data[0]
                return Session(
                    id=UUID(record["id"]),
                    user_id=UUID(record["user_id"]),
                    mode_code=record["mode_code"],
                    language_code=record["language_code"],
                    started_at=datetime.fromisoformat(record["started_at"].replace("Z", "+00:00")),
                    closed_at=datetime.fromisoformat(record["closed_at"].replace("Z", "+00:00")) if record.get("closed_at") else None,
                    metadata=record.get("metadata", {}),
                    status=SessionStatus(record.get("status", "active"))
                )
            
            return None
            
        except Exception as e:
            logger.error("Error getting active session for user", 
                        user_external_id=user_external_id,
                        error=str(e))
            return None
    
    async def _get_or_create_user(self, external_id: str) -> Optional[User]:
        """
        Get existing user or create new one
        
        Args:
            external_id: External user identifier
            
        Returns:
            User object if successful, None otherwise
        """
        try:
            # Try to get existing user
            response = self.supabase.table("users")\
                .select("*")\
                .eq("external_id", external_id)\
                .limit(1)\
                .execute()
            
            if response.data:
                record = response.data[0]
                return User(
                    id=UUID(record["id"]),
                    external_id=record["external_id"],
                    display_name=record.get("display_name"),
                    created_at=datetime.fromisoformat(record["created_at"].replace("Z", "+00:00")) if record.get("created_at") else None
                )
            
            # Create new user
            user_data = {
                "external_id": external_id,
                "display_name": f"User {external_id}"
            }
            
            create_response = self.supabase.table("users").insert(user_data).execute()
            
            if create_response.data:
                record = create_response.data[0]
                logger.info("New user created", user_id=record["id"], external_id=external_id)
                return User(
                    id=UUID(record["id"]),
                    external_id=record["external_id"],
                    display_name=record.get("display_name"),
                    created_at=datetime.fromisoformat(record["created_at"].replace("Z", "+00:00")) if record.get("created_at") else None
                )
            
            return None
            
        except Exception as e:
            logger.error("Error getting or creating user", 
                        external_id=external_id,
                        error=str(e))
            return None
    
    async def _get_user_by_external_id(self, external_id: str) -> Optional[User]:
        """
        Get user by external ID
        
        Args:
            external_id: External user identifier
            
        Returns:
            User object if found, None otherwise
        """
        try:
            response = self.supabase.table("users")\
                .select("*")\
                .eq("external_id", external_id)\
                .limit(1)\
                .execute()
            
            if response.data:
                record = response.data[0]
                return User(
                    id=UUID(record["id"]),
                    external_id=record["external_id"],
                    display_name=record.get("display_name"),
                    created_at=datetime.fromisoformat(record["created_at"].replace("Z", "+00:00")) if record.get("created_at") else None
                )
            
            return None
            
        except Exception as e:
            logger.error("Error getting user by external ID", 
                        external_id=external_id,
                        error=str(e))
            return None
    
    async def _validate_mode_and_language(self, mode_code: str, language_code: str) -> bool:
        """
        Validate that mode and language exist in database
        
        Args:
            mode_code: Teaching mode code
            language_code: Language code
            
        Returns:
            True if both exist, False otherwise
        """
        try:
            # Check mode exists
            mode_response = self.supabase.table("teaching_modes")\
                .select("code")\
                .eq("code", mode_code)\
                .limit(1)\
                .execute()
            
            if not mode_response.data:
                logger.error("Teaching mode not found", mode_code=mode_code)
                return False
            
            # Check language exists
            language_response = self.supabase.table("supported_languages")\
                .select("code")\
                .eq("code", language_code)\
                .limit(1)\
                .execute()
            
            if not language_response.data:
                logger.error("Language not found", language_code=language_code)
                return False
            
            return True
            
        except Exception as e:
            logger.error("Error validating mode and language", 
                        mode_code=mode_code,
                        language_code=language_code,
                        error=str(e))
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (maintenance operation)
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            # Find sessions that should be expired based on Redis TTL or long inactivity
            # This is a maintenance function that can be called periodically
            
            # For now, just log that this would be implemented
            logger.info("Session cleanup would run here - implement based on requirements")
            return 0
            
        except Exception as e:
            logger.error("Error cleaning up expired sessions", error=str(e))
            return 0


# Global session service instance
session_service = SessionService()