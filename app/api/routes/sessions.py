"""
API routes for session management
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from app.api.schemas import (
    SessionCreateRequest, SessionCreateResponse, SessionResponse, 
    SessionsListResponse, SessionCloseResponse, PaginationParams,
    ErrorResponse
)
from app.api.deps import (
    get_session_service, get_request_logger, get_pagination_params,
    validate_session_exists
)
from app.services.session_service import SessionService
from app.domain.models import SessionStatus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["sessions"])


@router.post(
    "/sessions/open",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def open_session(
    session_data: SessionCreateRequest,
    session_svc: SessionService = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Open a new learning session
    
    Creates a new session for the specified user with the given teaching mode and language.
    If the user has an existing active session, it will be automatically closed.
    
    The session is stored in both the database (for persistence) and Redis (for active session management).
    """
    try:
        request_logger.info("Opening new session", 
                          user_external_id=session_data.user_external_id,
                          mode_code=session_data.mode_code,
                          language_code=session_data.language_code)
        
        # Create the session
        session = await session_svc.create_session(
            user_external_id=session_data.user_external_id,
            mode_code=session_data.mode_code,
            language_code=session_data.language_code,
            metadata=session_data.metadata
        )
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create session. Check that mode and language are valid."
            )
        
        request_logger.info("Session opened successfully", 
                          session_id=session.id,
                          user_external_id=session_data.user_external_id)
        
        return SessionCreateResponse(session_id=session.id)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error opening session", 
                           user_external_id=session_data.user_external_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_session(
    session_id: UUID = Depends(validate_session_exists),
    session_svc: SessionService = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get session details
    
    Retrieves detailed information about a specific session including its status,
    start/end times, and metadata.
    """
    try:
        request_logger.debug("Getting session details", session_id=session_id)
        
        session = await session_svc.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return SessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting session", 
                           session_id=session_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/sessions",
    response_model=SessionsListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_user_sessions(
    user_external_id: str = Query(..., description="External user identifier"),
    status_filter: Optional[SessionStatus] = Query(None, description="Filter by session status"),
    pagination: PaginationParams = Depends(get_pagination_params),
    session_svc: SessionService = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get sessions for a user
    
    Retrieves a paginated list of sessions for the specified user.
    Can be filtered by session status (active, closed, expired).
    """
    try:
        request_logger.debug("Getting user sessions", 
                           user_external_id=user_external_id,
                           status_filter=status_filter,
                           page=pagination.page,
                           page_size=pagination.page_size)
        
        sessions = await session_svc.get_user_sessions(
            user_external_id=user_external_id,
            limit=pagination.limit,
            offset=pagination.offset,
            status_filter=status_filter
        )
        
        response_sessions = [SessionResponse.from_orm(session) for session in sessions]
        
        return SessionsListResponse(
            sessions=response_sessions,
            total_count=len(response_sessions),  # Note: This is a simplification; in production you'd get total count separately
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except Exception as e:
        request_logger.error("Error getting user sessions", 
                           user_external_id=user_external_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/sessions/active/{user_external_id}",
    response_model=SessionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No active session found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_active_session(
    user_external_id: str,
    session_svc: SessionService = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get active session for a user
    
    Retrieves the currently active session for the specified user.
    Returns 404 if no active session is found.
    """
    try:
        request_logger.debug("Getting active session", user_external_id=user_external_id)
        
        session = await session_svc.get_active_session_for_user(user_external_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active session found for user {user_external_id}"
            )
        
        return SessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting active session", 
                           user_external_id=user_external_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post(
    "/sessions/{session_id}/close",
    response_model=SessionCloseResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        400: {"model": ErrorResponse, "description": "Session already closed"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def close_session(
    session_id: UUID = Depends(validate_session_exists),
    session_svc: SessionService = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Close a session and generate summary
    
    Closes the specified session, marks it as completed in the database,
    generates a learning summary, and cleans up Redis session data.
    
    The generated summary includes:
    - Key phrases practiced
    - Grammar corrections and tips
    - Pronunciation feedback
    - Next steps for continued learning
    
    Once closed, a session cannot be reopened.
    """
    try:
        request_logger.info("Closing session", session_id=session_id)
        
        # Close the session and generate summary
        summary_json = await session_svc.close_session(session_id)
        
        if not summary_json:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to close session"
            )
        
        request_logger.info("Session closed successfully", session_id=session_id)
        
        return SessionCloseResponse(
            session_id=session_id,
            summary_json=summary_json
        )
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error closing session", 
                           session_id=session_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post(
    "/sessions/{session_id}/turns",
    response_model=dict,  # Will be defined in conversations.py, but included here for completeness
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        400: {"model": ErrorResponse, "description": "Invalid turn data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def add_session_turn(
    session_id: UUID = Depends(validate_session_exists),
    # turn_data: ConversationTurnRequest = Body(...),  # Would import from conversations schema
    session_svc: SessionService = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Add a turn to a session
    
    This endpoint is a convenience alias that forwards to the conversations API.
    It's included here for backward compatibility and to maintain the session-centric view.
    
    For full turn management, use the /api/v1/sessions/{session_id}/turns endpoint
    in the conversations router.
    """
    # This would typically redirect to the conversations endpoint
    # or import and call the conversation service directly
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Please use /api/v1/sessions/{session_id}/turns in the conversations API"
    )

@router.get(
    "/sessions/{session_id}/status",
    response_model=dict,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_session_status(
    session_id: UUID = Depends(validate_session_exists),
    session_svc: SessionService = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get detailed session status
    
    Returns current session status including turn count, active time,
    and other session metrics useful for monitoring and debugging.
    """
    try:
        request_logger.debug("Getting session status", session_id=session_id)
        
        session = await session_svc.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        # Get additional status information from Redis if available
        from app.services.redis_client import session_manager
        await session_manager.initialize()
        redis_session = await session_manager.get_session(str(session_id))
        
        status_info = {
            "session_id": str(session_id),
            "status": session.status.value,
            "started_at": session.started_at.isoformat(),
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
            "mode_code": session.mode_code,
            "language_code": session.language_code,
            "user_id": str(session.user_id)
        }
        
        if redis_session:
            status_info.update({
                "redis_active": True,
                "last_turn_index": redis_session.get("last_turn_index", 0),
                "last_activity": redis_session.get("last_activity"),
                "created_at": redis_session.get("created_at"),
                "turns": redis_session.get("turns"),
                "user_level": redis_session.get("user_level"),
                "mother_language": redis_session.get("mother_language"),
                "session_type": redis_session.get("session_type"),
                "conversation_id": redis_session.get("conversation_id"),
                "mode": redis_session.get("mode"),
                "language": redis_session.get("language"),
                "metadata": redis_session.get("metadata"),
            })
        else:
            status_info.update({
                "redis_active": False
            })
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting session status", 
                           session_id=session_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete(
    "/sessions/{session_id}/clear",
    response_model=dict,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def clear_session(
    session_id: UUID = Depends(validate_session_exists),
    session_svc: SessionService = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Clear (delete) a session and all related data.
    Removes the session from the database and cleans up Redis session data.
    """
    try:
        request_logger.info("Clearing session", session_id=session_id)
        # Delete session from database
        deleted = await session_svc.delete_session(session_id)
        # Clean up Redis session data
        from app.services.redis_client import session_manager
        await session_manager.initialize()
        await session_manager.delete_session(str(session_id))
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or could not be deleted"
            )
        request_logger.info("Session cleared successfully", session_id=session_id)
        return {"detail": f"Session {session_id} cleared successfully"}
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error clearing session", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
