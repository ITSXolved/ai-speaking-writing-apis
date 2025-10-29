"""
FastAPI dependency injection for services and common dependencies
Enhanced with email reports and writing evaluation services
"""

from typing import Dict, Any
from fastapi import Depends, HTTPException, Query, status
from uuid import UUID
import structlog
from functools import lru_cache

from app.services.supabase_client import get_supabase_client
from app.services.redis_client import session_manager
from app.services.teaching_service import teaching_service
from app.services.session_service import session_service
from app.services.conversation_service import conversation_service
from app.services.scoring_service import scoring_service
from app.services.summary_service import summary_service
from app.services.email_service import EmailService  # New
from app.services.writing_evaluation_service import WritingEvaluationService  # New
from app.services.speaking_evaluation_service import SpeakingEvaluationService  # New
from app.api.schemas import PaginationParams, DateFilterParams

logger = structlog.get_logger(__name__)


# Service Dependencies

def get_teaching_service():
    """Dependency for teaching service"""
    return teaching_service

def get_session_service():
    """Dependency for session service"""
    return session_service

def get_conversation_service():
    """Dependency for conversation service"""
    return conversation_service

def get_summary_service():
    """Dependency for summary service"""
    return summary_service

def get_scoring_service():
    """Dependency for scoring service"""
    return scoring_service

async def get_session_manager():
    """Dependency for Redis session manager"""
    if not session_manager.redis:
        await session_manager.initialize()
    return session_manager

# NEW SERVICE DEPENDENCIES

@lru_cache()
def get_email_service() -> EmailService:
    """
    Create and cache email service instance
    """
    try:
        return EmailService()
    except Exception as e:
        logger.error("Failed to initialize email service", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service unavailable"
        )

@lru_cache()
def get_writing_evaluation_service() -> WritingEvaluationService:
    """
    Create and cache writing evaluation service instance
    """
    try:
        return WritingEvaluationService()
    except Exception as e:
        logger.error("Failed to initialize writing evaluation service", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Writing evaluation service unavailable"
        )

@lru_cache()
def get_speaking_evaluation_service() -> SpeakingEvaluationService:
    """
    Create and cache speaking evaluation service instance
    """
    try:
        return SpeakingEvaluationService()
    except Exception as e:
        logger.error("Failed to initialize speaking evaluation service", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speaking evaluation service unavailable"
        )

# NEW VALIDATION DEPENDENCIES

async def validate_writing_evaluation_exists(
    evaluation_id: str,
    writing_service: WritingEvaluationService = Depends(get_writing_evaluation_service)
) -> str:
    """
    Validate that a writing evaluation exists
    
    Args:
        evaluation_id: Writing evaluation ID to validate
        writing_service: Writing evaluation service dependency
        
    Returns:
        Evaluation ID if valid
        
    Raises:
        HTTPException: If evaluation not found
    """
    try:
        # This would need to be implemented in the writing service
        # For now, we'll assume the validation happens at the route level
        if not evaluation_id or len(evaluation_id) < 10:
            raise ValueError("Invalid evaluation ID format")
        return evaluation_id
    except Exception as e:
        logger.warning("Writing evaluation validation failed", 
                      evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Writing evaluation {evaluation_id} not found"
        )

def validate_email_address(email: str) -> str:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        Email if valid
        
    Raises:
        HTTPException: If email is invalid
    """
    import re
    
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    if not email_pattern.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format"
        )
    
    return email

def validate_text_length(
    text: str,
    min_length: int = 10,
    max_length: int = 5000
) -> str:
    """
    Validate text length for writing evaluation
    
    Args:
        text: Text to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        
    Returns:
        Text if valid
        
    Raises:
        HTTPException: If text length is invalid
    """
    text_length = len(text.strip())
    
    if text_length < min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Text must be at least {min_length} characters long"
        )
    
    if text_length > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Text must not exceed {max_length} characters"
        )
    
    return text.strip()

# Validation Dependencies (Existing)

async def validate_session_exists(
    session_id: UUID,
    session_svc = Depends(get_session_service)
) -> UUID:
    """
    Validate that a session exists and return the session ID
    
    Args:
        session_id: Session UUID to validate
        session_svc: Session service dependency
        
    Returns:
        Session UUID if valid
        
    Raises:
        HTTPException: If session not found
    """
    session = await session_svc.get_session(session_id)
    if not session:
        logger.warning("Session not found", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return session_id

async def validate_teaching_mode_exists(
    mode_code: str,
    teaching_svc = Depends(get_teaching_service)
) -> str:
    """
    Validate that a teaching mode exists
    
    Args:
        mode_code: Teaching mode code to validate
        teaching_svc: Teaching service dependency
        
    Returns:
        Mode code if valid
        
    Raises:
        HTTPException: If mode not found
    """
    mode = await teaching_svc.get_mode_by_code(mode_code)
    if not mode:
        logger.warning("Teaching mode not found", mode_code=mode_code)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teaching mode '{mode_code}' not found"
        )
    return mode_code

async def validate_language_exists(
    language_code: str,
    teaching_svc = Depends(get_teaching_service)
) -> str:
    """
    Validate that a language exists
    
    Args:
        language_code: Language code to validate
        teaching_svc: Teaching service dependency
        
    Returns:
        Language code if valid
        
    Raises:
        HTTPException: If language not found
    """
    language = await teaching_svc.get_language_by_code(language_code)
    if not language:
        logger.warning("Language not found", language_code=language_code)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language '{language_code}' not supported"
        )
    return language_code

async def validate_scenario_exists(
    scenario_id: UUID,
    teaching_svc = Depends(get_teaching_service)
) -> UUID:
    """
    Validate that a scenario exists
    
    Args:
        scenario_id: Scenario UUID to validate
        teaching_svc: Teaching service dependency
        
    Returns:
        Scenario UUID if valid
        
    Raises:
        HTTPException: If scenario not found
    """
    scenarios = await teaching_svc.get_scenarios()
    scenario_exists = any(s.id == scenario_id for s in scenarios)
    
    if not scenario_exists:
        logger.warning("Scenario not found", scenario_id=scenario_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {scenario_id} not found"
        )
    return scenario_id


# Query Parameter Dependencies

def get_pagination_params(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """
    Dependency for pagination parameters
    
    Args:
        page: Page number (1-based)
        page_size: Items per page
        
    Returns:
        PaginationParams object
    """
    return PaginationParams(page=page, page_size=page_size)

def get_date_filter_params(
    from_date: str = Query(None, description="Start date (ISO format)"),
    to_date: str = Query(None, description="End date (ISO format)")
) -> DateFilterParams:
    """
    Dependency for date filtering parameters
    
    Args:
        from_date: Start date (ISO format)
        to_date: End date (ISO format)
        
    Returns:
        DateFilterParams object
    """
    from datetime import datetime
    
    parsed_from_date = None
    parsed_to_date = None
    
    if from_date:
        try:
            parsed_from_date = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid from_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    if to_date:
        try:
            parsed_to_date = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid to_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    # Validate date range
    if parsed_from_date and parsed_to_date and parsed_to_date < parsed_from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_date must be after from_date"
        )
    
    return DateFilterParams(from_date=parsed_from_date, to_date=parsed_to_date)

def get_optional_filters(
    mode_code: str = Query(None, description="Filter by teaching mode"),
    language_code: str = Query(None, description="Filter by language")
) -> Dict[str, Any]:
    """
    Dependency for optional filter parameters
    
    Args:
        mode_code: Optional teaching mode filter
        language_code: Optional language filter
        
    Returns:
        Dictionary of filters
    """
    filters = {}
    if mode_code:
        filters["mode_code"] = mode_code
    if language_code:
        filters["language_code"] = language_code
    return filters

# NEW QUERY PARAMETER DEPENDENCIES

def get_writing_evaluation_filters(
    language: str = Query(None, description="Filter by language"),
    writing_type: str = Query(None, description="Filter by writing type"),
    user_level: str = Query(None, description="Filter by user level"),
    min_score: int = Query(None, ge=0, le=100, description="Minimum overall score"),
    max_score: int = Query(None, ge=0, le=100, description="Maximum overall score")
) -> Dict[str, Any]:
    """
    Dependency for writing evaluation filter parameters
    """
    filters = {}
    if language:
        filters["language"] = language
    if writing_type:
        filters["writing_type"] = writing_type
    if user_level:
        filters["user_level"] = user_level
    if min_score is not None:
        filters["min_score"] = min_score
    if max_score is not None:
        filters["max_score"] = max_score
    
    # Validate score range
    if min_score is not None and max_score is not None and min_score > max_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_score cannot be greater than max_score"
        )
    
    return filters

def get_email_report_params(
    report_type: str = Query("weekly", description="Report type: daily, weekly, monthly"),
    include_detailed_stats: bool = Query(True, description="Include detailed statistics")
) -> Dict[str, Any]:
    """
    Dependency for email report parameters
    """
    valid_types = ["daily", "weekly", "monthly", "session"]
    
    if report_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type. Must be one of: {', '.join(valid_types)}"
        )
    
    return {
        "report_type": report_type,
        "include_detailed_stats": include_detailed_stats
    }


# Database Health Dependencies

async def check_database_health():
    """
    Check database connectivity
    
    Raises:
        HTTPException: If database is not available
    """
    try:
        supabase = get_supabase_client()
        # Simple health check query
        response = supabase.table("teaching_modes").select("count", count="exact").execute()
        if response.count is None:
            raise Exception("Database query returned no count")
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )

async def check_redis_health():
    """
    Check Redis connectivity
    
    Raises:
        HTTPException: If Redis is not available
    """
    try:
        session_mgr = await get_session_manager()
        if not await session_mgr.health_check():
            raise Exception("Redis health check failed")
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service unavailable"
        )

# NEW HEALTH CHECKS

async def check_email_service_health(
    email_service: EmailService = Depends(get_email_service)
):
    """
    Check email service health
    
    Raises:
        HTTPException: If email service is not available
    """
    try:
        # Simple configuration check
        if not email_service.email_address or not email_service.email_password:
            raise Exception("Email service not properly configured")
    except Exception as e:
        logger.error("Email service health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service unavailable"
        )

async def check_writing_evaluation_health(
    writing_service: WritingEvaluationService = Depends(get_writing_evaluation_service)
):
    """
    Check writing evaluation service health
    
    Raises:
        HTTPException: If writing evaluation service is not available
    """
    try:
        # Simple configuration check
        if not writing_service.genai_api_key:
            raise Exception("Writing evaluation service not properly configured")
    except Exception as e:
        logger.error("Writing evaluation service health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Writing evaluation service unavailable"
        )


# Error Handling Dependencies

def create_error_response(
    error_message: str,
    details: list = None,
    request_id: str = None
) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        error_message: Main error message
        details: Optional list of error details
        request_id: Optional request identifier
        
    Returns:
        Error response dictionary
    """
    response = {
        "error": error_message
    }
    
    if details:
        response["details"] = details
    
    if request_id:
        response["request_id"] = request_id
    
    return response


# Authentication Dependencies (Placeholder)

async def get_current_user():
    """
    Placeholder for user authentication
    In a real implementation, this would validate JWT tokens, API keys, etc.
    
    Returns:
        User information or None if not authenticated
    """
    # For now, return None to indicate no authentication required
    # In production, implement proper authentication here
    return None

def require_authentication():
    """
    Dependency that requires authentication
    Use this on protected endpoints
    """
    async def _require_auth(current_user = Depends(get_current_user)):
        if current_user is None:
            # For now, allow all requests
            # In production, raise authentication error
            pass
        return current_user
    
    return Depends(_require_auth)


# Rate Limiting Dependencies

async def check_email_rate_limit(
    user_ip: str = None
):
    """
    Check email sending rate limits
    
    Args:
        user_ip: Client IP address for rate limiting
    """
    # Placeholder for email rate limiting
    # In production, implement proper rate limiting based on IP/user
    pass

async def check_writing_evaluation_rate_limit(
    user_id: str = None
):
    """
    Check writing evaluation rate limits
    
    Args:
        user_id: User identifier for rate limiting
    """
    # Placeholder for writing evaluation rate limiting
    # In production, implement proper rate limiting
    pass


# Logging Dependencies

def get_request_logger():
    """
    Get a structured logger for request processing
    
    Returns:
        Structured logger instance
    """
    return logger


# Cache Dependencies (Future Enhancement)

async def get_cache_key(
    endpoint: str,
    params: Dict[str, Any] = None
) -> str:
    """
    Generate cache key for endpoint and parameters
    
    Args:
        endpoint: API endpoint name
        params: Optional parameters
        
    Returns:
        Cache key string
    """
    import hashlib
    import json
    
    key_data = {
        "endpoint": endpoint,
        "params": params or {}
    }
    
    key_string = json.dumps(key_data, sort_keys=True)
    return f"api_cache:{hashlib.md5(key_string.encode()).hexdigest()}"


# Common Query Utilities

def build_filters_dict(**kwargs) -> Dict[str, Any]:
    """
    Build filters dictionary from keyword arguments, excluding None values
    
    Args:
        **kwargs: Filter parameters
        
    Returns:
        Dictionary with non-None filters
    """
    return {k: v for k, v in kwargs.items() if v is not None}


# NEW UTILITY FUNCTIONS

def validate_user_permissions(
    user_id: str,
    resource_id: str,
    action: str
) -> bool:
    """
    Validate user permissions for resource access
    
    Args:
        user_id: User identifier
        resource_id: Resource identifier
        action: Action being performed
        
    Returns:
        True if allowed, False otherwise
    """
    # Placeholder for permission validation
    # In production, implement proper authorization logic
    return True

async def log_api_usage(
    endpoint: str,
    user_id: str = None,
    execution_time: float = None
):
    """
    Log API usage for monitoring and analytics
    
    Args:
        endpoint: API endpoint called
        user_id: Optional user identifier
        execution_time: Optional execution time in seconds
    """
    logger.info("API usage", 
                endpoint=endpoint,
                user_id=user_id,
                execution_time=execution_time)
from functools import lru_cache

# Add these new dependency functions to your existing deps.py
@lru_cache()
def get_email_service():
    """Get email service instance"""
    try:
        from ..services.email_service import EmailService
        return EmailService()
    except Exception as e:
        import logging
        logging.error(f"Failed to initialize email service: {e}")
        raise HTTPException(status_code=503, detail="Email service unavailable")

@lru_cache()
def get_speaking_evaluation_service_alt():
    """Get speaking evaluation service instance (alternate)"""
    try:
        from ..services.speaking_evaluation_service import SpeakingEvaluationService
        return SpeakingEvaluationService()
    except Exception as e:
        import logging
        logging.error(f"Failed to initialize speaking evaluation service: {e}")
        raise HTTPException(status_code=503, detail="Speaking evaluation service unavailable")

# """
# FastAPI dependency injection for services and common dependencies
# """

# from typing import Dict, Any
# from fastapi import Depends, HTTPException, Query, status
# from uuid import UUID
# import structlog

# from app.services.supabase_client import get_supabase_client
# from app.services.redis_client import session_manager
# from app.services.teaching_service import teaching_service
# from app.services.session_service import session_service
# from app.services.conversation_service import conversation_service
# from app.services.scoring_service import scoring_service
# from app.services.summary_service import summary_service
# from app.api.schemas import PaginationParams, DateFilterParams

# logger = structlog.get_logger(__name__)


# # Service Dependencies

# def get_teaching_service():
#     """Dependency for teaching service"""
#     return teaching_service

# def get_session_service():
#     """Dependency for session service"""
#     return session_service

# def get_conversation_service():
#     """Dependency for conversation service"""
#     return conversation_service


# def get_summary_service():
#     """Dependency for summary service"""
#     return summary_service

# async def get_session_manager():
#     """Dependency for Redis session manager"""
#     if not session_manager.redis:
#         await session_manager.initialize()
#     return session_manager


# # Validation Dependencies

# async def validate_session_exists(
#     session_id: UUID,
#     session_svc = Depends(get_session_service)
# ) -> UUID:
#     """
#     Validate that a session exists and return the session ID
    
#     Args:
#         session_id: Session UUID to validate
#         session_svc: Session service dependency
        
#     Returns:
#         Session UUID if valid
        
#     Raises:
#         HTTPException: If session not found
#     """
#     session = await session_svc.get_session(session_id)
#     if not session:
#         logger.warning("Session not found", session_id=session_id)
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Session {session_id} not found"
#         )
#     return session_id

# async def validate_teaching_mode_exists(
#     mode_code: str,
#     teaching_svc = Depends(get_teaching_service)
# ) -> str:
#     """
#     Validate that a teaching mode exists
    
#     Args:
#         mode_code: Teaching mode code to validate
#         teaching_svc: Teaching service dependency
        
#     Returns:
#         Mode code if valid
        
#     Raises:
#         HTTPException: If mode not found
#     """
#     mode = await teaching_svc.get_mode_by_code(mode_code)
#     if not mode:
#         logger.warning("Teaching mode not found", mode_code=mode_code)
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Teaching mode '{mode_code}' not found"
#         )
#     return mode_code

# async def validate_language_exists(
#     language_code: str,
#     teaching_svc = Depends(get_teaching_service)
# ) -> str:
#     """
#     Validate that a language exists
    
#     Args:
#         language_code: Language code to validate
#         teaching_svc: Teaching service dependency
        
#     Returns:
#         Language code if valid
        
#     Raises:
#         HTTPException: If language not found
#     """
#     language = await teaching_svc.get_language_by_code(language_code)
#     if not language:
#         logger.warning("Language not found", language_code=language_code)
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Language '{language_code}' not supported"
#         )
#     return language_code

# async def validate_scenario_exists(
#     scenario_id: UUID,
#     teaching_svc = Depends(get_teaching_service)
# ) -> UUID:
#     """
#     Validate that a scenario exists
    
#     Args:
#         scenario_id: Scenario UUID to validate
#         teaching_svc: Teaching service dependency
        
#     Returns:
#         Scenario UUID if valid
        
#     Raises:
#         HTTPException: If scenario not found
#     """
#     scenarios = await teaching_svc.get_scenarios()
#     scenario_exists = any(s.id == scenario_id for s in scenarios)
    
#     if not scenario_exists:
#         logger.warning("Scenario not found", scenario_id=scenario_id)
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Scenario {scenario_id} not found"
#         )
#     return scenario_id


# # Query Parameter Dependencies

# def get_pagination_params(
#     page: int = Query(default=1, ge=1, description="Page number (1-based)"),
#     page_size: int = Query(default=20, ge=1, le=100, description="Items per page")
# ) -> PaginationParams:
#     """
#     Dependency for pagination parameters
    
#     Args:
#         page: Page number (1-based)
#         page_size: Items per page
        
#     Returns:
#         PaginationParams object
#     """
#     return PaginationParams(page=page, page_size=page_size)

# def get_date_filter_params(
#     from_date: str = Query(None, description="Start date (ISO format)"),
#     to_date: str = Query(None, description="End date (ISO format)")
# ) -> DateFilterParams:
#     """
#     Dependency for date filtering parameters
    
#     Args:
#         from_date: Start date (ISO format)
#         to_date: End date (ISO format)
        
#     Returns:
#         DateFilterParams object
#     """
#     from datetime import datetime
    
#     parsed_from_date = None
#     parsed_to_date = None
    
#     if from_date:
#         try:
#             parsed_from_date = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
#         except ValueError:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid from_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
#             )
    
#     if to_date:
#         try:
#             parsed_to_date = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
#         except ValueError:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid to_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
#             )
    
#     # Validate date range
#     if parsed_from_date and parsed_to_date and parsed_to_date < parsed_from_date:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="to_date must be after from_date"
#         )
    
#     return DateFilterParams(from_date=parsed_from_date, to_date=parsed_to_date)

# def get_optional_filters(
#     mode_code: str = Query(None, description="Filter by teaching mode"),
#     language_code: str = Query(None, description="Filter by language")
# ) -> Dict[str, Any]:
#     """
#     Dependency for optional filter parameters
    
#     Args:
#         mode_code: Optional teaching mode filter
#         language_code: Optional language filter
        
#     Returns:
#         Dictionary of filters
#     """
#     filters = {}
#     if mode_code:
#         filters["mode_code"] = mode_code
#     if language_code:
#         filters["language_code"] = language_code
#     return filters


# # Database Health Dependencies

# async def check_database_health():
#     """
#     Check database connectivity
    
#     Raises:
#         HTTPException: If database is not available
#     """
#     try:
#         supabase = get_supabase_client()
#         # Simple health check query
#         response = supabase.table("teaching_modes").select("count", count="exact").execute()
#         if response.count is None:
#             raise Exception("Database query returned no count")
#     except Exception as e:
#         logger.error("Database health check failed", error=str(e))
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="Database service unavailable"
#         )

# async def check_redis_health():
#     """
#     Check Redis connectivity
    
#     Raises:
#         HTTPException: If Redis is not available
#     """
#     try:
#         session_mgr = await get_session_manager()
#         if not await session_mgr.health_check():
#             raise Exception("Redis health check failed")
#     except Exception as e:
#         logger.error("Redis health check failed", error=str(e))
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="Redis service unavailable"
#         )


# # Error Handling Dependencies

# def create_error_response(
#     error_message: str,
#     details: list = None,
#     request_id: str = None
# ) -> Dict[str, Any]:
#     """
#     Create standardized error response
    
#     Args:
#         error_message: Main error message
#         details: Optional list of error details
#         request_id: Optional request identifier
        
#     Returns:
#         Error response dictionary
#     """
#     response = {
#         "error": error_message
#     }
    
#     if details:
#         response["details"] = details
    
#     if request_id:
#         response["request_id"] = request_id
    
#     return response


# # Authentication Dependencies (Placeholder)

# async def get_current_user():
#     """
#     Placeholder for user authentication
#     In a real implementation, this would validate JWT tokens, API keys, etc.
    
#     Returns:
#         User information or None if not authenticated
#     """
#     # For now, return None to indicate no authentication required
#     # In production, implement proper authentication here
#     return None

# def require_authentication():
#     """
#     Dependency that requires authentication
#     Use this on protected endpoints
#     """
#     async def _require_auth(current_user = Depends(get_current_user)):
#         if current_user is None:
#             # For now, allow all requests
#             # In production, raise authentication error
#             pass
#         return current_user
    
#     return Depends(_require_auth)


# # Logging Dependencies

# def get_request_logger():
#     """
#     Get a structured logger for request processing
    
#     Returns:
#         Structured logger instance
#     """
#     return logger


# # Cache Dependencies (Future Enhancement)

# async def get_cache_key(
#     endpoint: str,
#     params: Dict[str, Any] = None
# ) -> str:
#     """
#     Generate cache key for endpoint and parameters
    
#     Args:
#         endpoint: API endpoint name
#         params: Optional parameters
        
#     Returns:
#         Cache key string
#     """
#     import hashlib
#     import json
    
#     key_data = {
#         "endpoint": endpoint,
#         "params": params or {}
#     }
    
#     key_string = json.dumps(key_data, sort_keys=True)
#     return f"api_cache:{hashlib.md5(key_string.encode()).hexdigest()}"


# # Rate Limiting Dependencies (Placeholder)

# async def check_rate_limit(
#     user_id: str = None,
#     endpoint: str = None
# ):
#     """
#     Placeholder for rate limiting
#     In production, implement rate limiting logic here
    
#     Args:
#         user_id: Optional user identifier
#         endpoint: API endpoint being accessed
#     """
#     # For now, allow all requests
#     # In production, implement rate limiting
#     pass


# # Common Query Utilities

# def build_filters_dict(**kwargs) -> Dict[str, Any]:
#     """
#     Build filters dictionary from keyword arguments, excluding None values
    
#     Args:
#         **kwargs: Filter parameters
        
#     Returns:
#         Dictionary with non-None filters
#     """
#     return {k: v for k, v in kwargs.items() if v is not None}
# # app/api/deps.py - Updated with new dependencies

# from functools import lru_cache
# from typing import Generator
# import os


# from ..services.redis_client import RedisClient
# from ..services.scoring_service import ScoringService
# from ..services.email_service import EmailService  # New
# from ..services.writing_evaluation_service import WritingEvaluationService  # New

# # Existing dependencies (keep these as they are)

# @lru_cache()
# def get_redis_client() -> RedisClient:
#     return RedisClient()







# def get_scoring_service() -> ScoringService:
#     return ScoringService()


# # New dependencies for email and writing evaluation
# @lru_cache()
# def get_email_service() -> EmailService:
#     """
#     Create and cache email service instance
#     """
#     return EmailService()

# @lru_cache()
# def get_writing_evaluation_service() -> WritingEvaluationService:
#     """
#     Create and cache writing evaluation service instance
#     """
#     return WritingEvaluationService()