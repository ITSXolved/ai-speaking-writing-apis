"""
Supabase client service for database operations
"""

from functools import lru_cache
from supabase import create_client, Client
import structlog

from app.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

logger = structlog.get_logger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.
    Uses LRU cache to ensure singleton behavior.
    """
    try:
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("Supabase client created successfully")
        return client
    except Exception as e:
        logger.error("Failed to create Supabase client", error=str(e))
        raise


class SupabaseService:
    """Service class for Supabase operations with error handling and logging"""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    async def health_check(self) -> bool:
        """
        Check if Supabase connection is healthy
        """
        try:
            # Simple query to test connection
            response = self.client.table("teaching_modes").select("count", count="exact").execute()
            return True
        except Exception as e:
            logger.error("Supabase health check failed", error=str(e))
            return False
    
    def execute_with_logging(self, operation_name: str, query_func):
        """
        Execute a Supabase operation with logging and error handling
        """
        try:
            logger.debug("Executing Supabase operation", operation=operation_name)
            result = query_func()
            logger.debug("Supabase operation completed", 
                        operation=operation_name, 
                        result_count=len(result.data) if hasattr(result, 'data') else 0)
            return result
        except Exception as e:
            logger.error("Supabase operation failed", 
                        operation=operation_name, 
                        error=str(e))
            raise