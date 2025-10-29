"""
Redis client service for session management and caching
"""

import asyncio
import json
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

import redis.asyncio as redis
import structlog

from app.config import REDIS_URL, SESSION_TIMEOUT_SECONDS

logger = structlog.get_logger(__name__)

# Global Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client with connection pooling
    """
    global _redis_pool, _redis_client
    
    if _redis_client is None:
        try:
            _redis_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
            _redis_client = redis.Redis(connection_pool=_redis_pool)
            
            # Test connection
            await _redis_client.ping()
            logger.info("Redis client created successfully")
            
        except Exception as e:
            logger.error("Failed to create Redis client", error=str(e))
            raise
    
    return _redis_client


class RedisSessionManager:
    """Redis-based session management"""
    
    def __init__(self):
        self.redis = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis = await get_redis_client()
    
    def _session_key(self, session_id: str) -> str:
        """Get Redis key for session data"""
        return f"sess:{session_id}"
    
    def _session_lock_key(self, session_id: str) -> str:
        """Get Redis key for session lock"""
        return f"sess:{session_id}:lock"
    
    def _user_active_session_key(self, user_id: str) -> str:
        """Get Redis key for user's active session"""
        return f"user_active_sess:{user_id}"
    
    async def create_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Create a new session in Redis
        """
        try:
            if not self.redis:
                await self.initialize()
            
            session_key = self._session_key(session_id)
            user_session_key = self._user_active_session_key(session_data.get("user_id"))
            
            # Prepare session data with metadata
            redis_data = {
                **session_data,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "last_turn_index": 0,
                "status": "active"
            }
            
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Store session data
            pipe.hset(session_key, mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                                          for k, v in redis_data.items()})
            
            # Set session timeout
            pipe.expire(session_key, SESSION_TIMEOUT_SECONDS)
            
            # Update user's active session
            pipe.set(user_session_key, session_id, ex=SESSION_TIMEOUT_SECONDS)
            
            await pipe.execute()
            
            logger.info("Session created in Redis", 
                       session_id=session_id, 
                       user_id=session_data.get("user_id"))
            return True
            
        except Exception as e:
            logger.error("Failed to create session in Redis", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data from Redis
        """
        try:
            if not self.redis:
                await self.initialize()
            
            session_key = self._session_key(session_id)
            session_data = await self.redis.hgetall(session_key)
            
            if not session_data:
                return None
            
            # Parse JSON fields back to objects
            parsed_data = {}
            for key, value in session_data.items():
                try:
                    parsed_data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_data[key] = value
            
            return parsed_data
            
        except Exception as e:
            logger.error("Failed to get session from Redis", 
                        session_id=session_id, 
                        error=str(e))
            return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data in Redis
        """
        try:
            if not self.redis:
                await self.initialize()
            
            session_key = self._session_key(session_id)
            
            # Add last activity timestamp
            updates["last_activity"] = datetime.utcnow().isoformat()
            
            # Convert complex types to JSON
            redis_updates = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                           for k, v in updates.items()}
            
            await self.redis.hset(session_key, mapping=redis_updates)
            
            # Refresh session timeout
            await self.redis.expire(session_key, SESSION_TIMEOUT_SECONDS)
            
            logger.debug("Session updated in Redis", 
                        session_id=session_id, 
                        updates=list(updates.keys()))
            return True
            
        except Exception as e:
            logger.error("Failed to update session in Redis", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def increment_turn_index(self, session_id: str) -> Optional[int]:
        """
        Atomically increment turn index for session
        """
        try:
            if not self.redis:
                await self.initialize()
            
            session_key = self._session_key(session_id)
            
            # Get current turn index
            current_index = await self.redis.hget(session_key, "last_turn_index")
            if current_index is None:
                current_index = 0
            else:
                current_index = int(current_index)
            
            new_index = current_index + 1
            
            # Update with new index
            await self.update_session(session_id, {"last_turn_index": new_index})
            
            return new_index
            
        except Exception as e:
            logger.error("Failed to increment turn index", 
                        session_id=session_id, 
                        error=str(e))
            return None
    
    async def close_session(self, session_id: str) -> bool:
        """
        Close session and clean up Redis data
        """
        try:
            if not self.redis:
                await self.initialize()
            
            # Get session data to find user_id
            session_data = await self.get_session(session_id)
            if not session_data:
                logger.warning("Session not found for closing", session_id=session_id)
                return True  # Already closed
            
            user_id = session_data.get("user_id")
            
            # Prepare keys
            session_key = self._session_key(session_id)
            session_lock_key = self._session_lock_key(session_id)
            user_session_key = self._user_active_session_key(user_id) if user_id else None
            
            # Use pipeline for atomic cleanup
            pipe = self.redis.pipeline()
            pipe.delete(session_key)
            pipe.delete(session_lock_key)
            if user_session_key:
                pipe.delete(user_session_key)
            
            await pipe.execute()
            
            logger.info("Session closed and cleaned up from Redis", 
                       session_id=session_id, 
                       user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to close session in Redis", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def get_user_active_session(self, user_id: str) -> Optional[str]:
        """
        Get user's currently active session ID
        """
        try:
            if not self.redis:
                await self.initialize()
            
            user_session_key = self._user_active_session_key(user_id)
            session_id = await self.redis.get(user_session_key)
            
            return session_id
            
        except Exception as e:
            logger.error("Failed to get user active session", 
                        user_id=user_id, 
                        error=str(e))
            return None
    
    async def acquire_session_lock(self, session_id: str, timeout: int = 10) -> bool:
        """
        Acquire an exclusive lock on a session (for atomic operations)
        """
        try:
            if not self.redis:
                await self.initialize()
            
            lock_key = self._session_lock_key(session_id)
            
            # Try to acquire lock with timeout
            result = await self.redis.set(lock_key, "locked", nx=True, ex=timeout)
            
            if result:
                logger.debug("Session lock acquired", session_id=session_id)
                return True
            else:
                logger.debug("Session lock already held", session_id=session_id)
                return False
                
        except Exception as e:
            logger.error("Failed to acquire session lock", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def release_session_lock(self, session_id: str) -> bool:
        """
        Release session lock
        """
        try:
            if not self.redis:
                await self.initialize()
            
            lock_key = self._session_lock_key(session_id)
            await self.redis.delete(lock_key)
            
            logger.debug("Session lock released", session_id=session_id)
            return True
            
        except Exception as e:
            logger.error("Failed to release session lock", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def health_check(self) -> bool:
        """
        Check Redis connection health
        """
        try:
            if not self.redis:
                await self.initialize()
            
            await self.redis.ping()
            return True
            
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False


# Global session manager instance
session_manager = RedisSessionManager()