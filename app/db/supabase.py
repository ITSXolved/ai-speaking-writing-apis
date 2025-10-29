"""
Supabase database client and connection management
"""
from supabase import create_client, Client
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Supabase client instances
_supabase_client: Optional[Client] = None
_supabase_admin: Optional[Client] = None


def init_supabase():
    """Initialize Supabase clients"""
    global _supabase_client, _supabase_admin
    
    try:
        # Client with anon key (for user operations)
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        
        # Admin client with service role key (for admin operations)
        _supabase_admin = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        logger.info("Supabase clients initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        raise


def get_supabase_client() -> Client:
    """Get Supabase client for user operations"""
    if _supabase_client is None:
        init_supabase()
    return _supabase_client


def get_supabase_admin() -> Client:
    """Get Supabase admin client for privileged operations"""
    if _supabase_admin is None:
        init_supabase()
    return _supabase_admin


class SupabaseService:
    """Base service class with Supabase client access"""
    
    def __init__(self, use_admin: bool = False):
        self.client = get_supabase_admin() if use_admin else get_supabase_client()
    
    @property
    def db(self):
        """Shorthand for database operations"""
        return self.client.table
    
    @property
    def storage(self):
        """Shorthand for storage operations"""
        return self.client.storage