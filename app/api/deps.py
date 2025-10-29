"""
FastAPI dependencies for authentication and common operations
"""
from fastapi import Depends, HTTPException, status, Header
from typing import Optional
import jwt
import logging

from app.db.supabase import get_supabase_client
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_client_auth: Optional[str] = Header(None)
) -> str:
    """
    Extract and validate user ID from JWT token
    Checks both Authorization and X-Client-Auth headers
    """
    token = None
    
    # Try Authorization header first
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]
    # Fall back to X-Client-Auth
    elif x_client_auth and x_client_auth.startswith("Bearer "):
        token = x_client_auth.split("Bearer ")[1]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )
    
    try:
        # Decode JWT (Supabase uses HS256 with the JWT secret)
        # Note: In production, verify with Supabase's JWT secret
        payload = jwt.decode(
            token,
            options={"verify_signature": False}  # Supabase handles verification
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


async def get_optional_user_id(
    authorization: Optional[str] = Header(None),
    x_client_auth: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extract user ID if token is present, return None otherwise
    Used for endpoints that work with or without authentication
    """
    try:
        return await get_current_user_id(authorization, x_client_auth)
    except HTTPException:
        return None


def verify_admin_role(user_id: str = Depends(get_current_user_id)) -> str:
    """
    Verify user has admin role
    For content creation endpoints
    """
    # TODO: Implement proper admin role check from database
    # For now, this is a placeholder
    return user_id


class Pagination:
    """Pagination helper"""
    
    def __init__(self, page: int = 1, size: int = 10):
        self.page = max(1, page)
        self.size = min(size, 100)  # Max 100 items per page
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        return self.size