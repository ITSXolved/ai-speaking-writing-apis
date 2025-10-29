"""
Conversation service for managing conversation turns and history
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog

from app.domain.models import Conversation, ConversationRole, Evaluation
from app.services.supabase_client import get_supabase_client
from app.services.redis_client import session_manager
from app.services.scoring_service import scoring_service

logger = structlog.get_logger(__name__)


class ConversationService:
    """Service for managing conversation turns and scoring"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.session_manager = session_manager
        self.scoring_service = scoring_service
    
    async def add_turn(
        self,
        session_id: UUID,
        role: ConversationRole,
        text: str,
        user_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Add a conversation turn and optionally score it
        
        Args:
            session_id: Session UUID
            role: Speaker role (user or assistant)
            text: Text content of the turn
            user_id: User UUID (if not provided, will get from session)
            
        Returns:
            Dictionary with turn data and scoring if applicable
        """
        try:
            # Get session data to validate and get user_id if needed
            session_data = await self.session_manager.get_session(str(session_id))
            if not session_data:
                logger.error("Session not found", session_id=session_id)
                return None
            
            # Use session user_id if not provided
            if user_id is None:
                user_id = UUID(session_data["user_id"])
            
            # Get and increment turn index atomically
            turn_index = await self.session_manager.increment_turn_index(str(session_id))
            if turn_index is None:
                logger.error("Failed to increment turn index", session_id=session_id)
                return None
            
            # Prepare conversation data
            conversation_data = {
                "session_id": str(session_id),
                "user_id": str(user_id),
                "role": role.value,
                "turn_index": turn_index,
                "text": text
            }
            
            # Insert conversation turn
            response = self.supabase.table("conversations").insert(conversation_data).execute()
            
            if not response.data:
                logger.error("Failed to insert conversation turn", 
                           session_id=session_id,
                           turn_index=turn_index)
                return None
            
            conversation_record = response.data[0]
            conversation_id = conversation_record["id"]
            
            logger.info("Conversation turn added", 
                       session_id=session_id,
                       turn_index=turn_index,
                       role=role.value,
                       conversation_id=conversation_id)
            
            # Create response data
            result = {
                "conversation_id": conversation_id,
                "turn_index": turn_index,
                "role": role.value,
                "text": text,
                "created_at": conversation_record.get("created_at")
            }
            
            # Score user turns
            if role == ConversationRole.USER and text.strip():
                mode_code = session_data.get("mode_code", "conversation")
                
                evaluation = await self.scoring_service.score_conversation_turn(
                    conversation_id=conversation_id,
                    session_id=session_id,
                    user_id=user_id,
                    text=text,
                    mode_code=mode_code
                )
                
                if evaluation:
                    result["evaluation"] = {
                        "total_score": evaluation.total_score,
                        "metrics": evaluation.metrics,
                        "evaluation_id": evaluation.id
                    }
                    
                    logger.info("Turn scored", 
                               conversation_id=conversation_id,
                               score=evaluation.total_score)
                else:
                    logger.warning("Failed to score user turn", 
                                 conversation_id=conversation_id)
            
            return result
            
        except Exception as e:
            logger.error("Error adding conversation turn", 
                        session_id=session_id,
                        role=role.value if role else "unknown",
                        error=str(e))
            return None
    
    async def get_session_conversations(
        self,
        session_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Session UUID
            limit: Maximum number of turns to return
            offset: Number of turns to skip
            
        Returns:
            List of conversation turns with evaluations
        """
        try:
            # Get conversations
            conversations_response = self.supabase.table("conversations")\
                .select("*")\
                .eq("session_id", str(session_id))\
                .order("turn_index")\
                .range(offset, offset + limit - 1)\
                .execute()
            
            conversations = conversations_response.data
            
            if not conversations:
                return []
            
            # Get conversation IDs for evaluation lookup
            conversation_ids = [conv["id"] for conv in conversations]
            
            # Get evaluations for these conversations
            evaluations_response = self.supabase.table("evaluations")\
                .select("*")\
                .in_("conversation_id", conversation_ids)\
                .execute()
            
            evaluations_by_conv_id = {
                eval_data["conversation_id"]: eval_data 
                for eval_data in evaluations_response.data
            }
            
            # Combine conversations with evaluations
            result = []
            for conv in conversations:
                conversation_data = {
                    "id": conv["id"],
                    "session_id": conv["session_id"],
                    "user_id": conv["user_id"],
                    "role": conv["role"],
                    "turn_index": conv["turn_index"],
                    "text": conv["text"],
                    "created_at": conv.get("created_at")
                }
                
                # Add evaluation if exists
                if conv["id"] in evaluations_by_conv_id:
                    eval_data = evaluations_by_conv_id[conv["id"]]
                    conversation_data["evaluation"] = {
                        "id": eval_data["id"],
                        "total_score": eval_data["total_score"],
                        "metrics": eval_data["metrics"]
                    }
                
                result.append(conversation_data)
            
            logger.debug("Retrieved session conversations", 
                        session_id=session_id,
                        count=len(result))
            
            return result
            
        except Exception as e:
            logger.error("Error getting session conversations", 
                        session_id=session_id,
                        error=str(e))
            return []
    
    async def get_conversation_count(self, session_id: UUID) -> int:
        """
        Get total count of conversations in a session
        
        Args:
            session_id: Session UUID
            
        Returns:
            Total number of conversation turns
        """
        try:
            response = self.supabase.table("conversations")\
                .select("count", count="exact")\
                .eq("session_id", str(session_id))\
                .execute()
            
            return response.count or 0
            
        except Exception as e:
            logger.error("Error getting conversation count", 
                        session_id=session_id,
                        error=str(e))
            return 0
    
    async def get_user_recent_conversations(
        self,
        user_id: UUID,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversations for a user across all sessions
        
        Args:
            user_id: User UUID
            limit: Maximum number of turns to return
            
        Returns:
            List of recent conversation turns
        """
        try:
            response = self.supabase.table("conversations")\
                .select("*, evaluations(total_score, metrics)")\
                .eq("user_id", str(user_id))\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            conversations = []
            for record in response.data:
                conversation_data = {
                    "id": record["id"],
                    "session_id": record["session_id"],
                    "role": record["role"],
                    "turn_index": record["turn_index"],
                    "text": record["text"],
                    "created_at": record.get("created_at")
                }
                
                # Add evaluation data if exists
                if record.get("evaluations"):
                    evaluation = record["evaluations"][0] if record["evaluations"] else None
                    if evaluation:
                        conversation_data["evaluation"] = {
                            "total_score": evaluation["total_score"],
                            "metrics": evaluation["metrics"]
                        }
                
                conversations.append(conversation_data)
            
            logger.debug("Retrieved user recent conversations", 
                        user_id=user_id,
                        count=len(conversations))
            
            return conversations
            
        except Exception as e:
            logger.error("Error getting user recent conversations", 
                        user_id=user_id,
                        error=str(e))
            return []
    
    async def delete_session_conversations(self, session_id: UUID) -> bool:
        """
        Delete all conversations for a session (admin operation)
        
        Args:
            session_id: Session UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete evaluations first (foreign key constraint)
            evaluations_response = self.supabase.table("evaluations")\
                .delete()\
                .eq("session_id", str(session_id))\
                .execute()
            
            # Delete conversations
            conversations_response = self.supabase.table("conversations")\
                .delete()\
                .eq("session_id", str(session_id))\
                .execute()
            
            logger.info("Session conversations deleted", 
                       session_id=session_id,
                       evaluations_deleted=len(evaluations_response.data) if evaluations_response.data else 0,
                       conversations_deleted=len(conversations_response.data) if conversations_response.data else 0)
            
            return True
            
        except Exception as e:
            logger.error("Error deleting session conversations", 
                        session_id=session_id,
                        error=str(e))
            return False
    
    async def search_conversations(
        self,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        text_search: Optional[str] = None,
        role_filter: Optional[ConversationRole] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search conversations with various filters
        
        Args:
            user_id: Filter by user ID
            session_id: Filter by session ID
            text_search: Search in text content
            role_filter: Filter by role
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of matching conversations
        """
        try:
            query = self.supabase.table("conversations").select("*")
            
            # Apply filters
            if user_id:
                query = query.eq("user_id", str(user_id))
            
            if session_id:
                query = query.eq("session_id", str(session_id))
            
            if role_filter:
                query = query.eq("role", role_filter.value)
            
            if text_search:
                query = query.ilike("text", f"%{text_search}%")
            
            # Apply pagination and ordering
            response = query.order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            conversations = []
            for record in response.data:
                conversations.append({
                    "id": record["id"],
                    "session_id": record["session_id"],
                    "user_id": record["user_id"],
                    "role": record["role"],
                    "turn_index": record["turn_index"],
                    "text": record["text"],
                    "created_at": record.get("created_at")
                })
            
            logger.debug("Conversation search completed", 
                        results=len(conversations),
                        filters={
                            "user_id": str(user_id) if user_id else None,
                            "session_id": str(session_id) if session_id else None,
                            "text_search": text_search,
                            "role_filter": role_filter.value if role_filter else None
                        })
            
            return conversations
            
        except Exception as e:
            logger.error("Error searching conversations", 
                        error=str(e))
            return []


# Global conversation service instance
conversation_service = ConversationService()