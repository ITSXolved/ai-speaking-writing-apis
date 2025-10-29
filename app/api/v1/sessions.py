"""
Session API endpoints for starting and submitting tests
"""
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging

from app.models.sessions import (
    SessionStart, SessionStartResponse,
    SessionSubmit, SessionSubmitResponse,
    SessionDetail
)
from app.services.session_service import SessionService
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions", response_model=SessionStartResponse, status_code=201)
async def start_session(
    data: SessionStart,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Start a new test session
    Creates a session record and returns session_id
    """
    try:
        # Verify user_id matches authenticated user
        if str(data.user_id) != current_user_id:
            raise HTTPException(status_code=403, detail="Cannot create session for another user")
        
        session_service = SessionService()
        result = await session_service.create_session(data)
        
        return SessionStartResponse(
            session_id=result['session_id'],
            user_id=result['user_id'],
            modality=result['modality'],
            day_code=result['day_code'],
            started_at=result['started_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/submit", response_model=SessionSubmitResponse)
async def submit_session(
    session_id: UUID,
    data: SessionSubmit,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Submit completed session with answers
    Triggers analytics, XP, streaks, and badge awards
    """
    try:
        session_service = SessionService()
        
        # Verify session belongs to current user
        session = await session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if str(session.user_id) != current_user_id:
            raise HTTPException(status_code=403, detail="Cannot submit another user's session")
        
        # Submit session
        result = await session_service.submit_session(session_id, data)
        
        return SessionSubmitResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get detailed session information including all answers
    """
    try:
        session_service = SessionService()
        result = await session_service.get_session(session_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify session belongs to current user
        if str(result.user_id) != current_user_id:
            raise HTTPException(status_code=403, detail="Cannot view another user's session")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_user_sessions(
    limit: int = 10,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's session history
    Returns paginated list of sessions
    """
    try:
        session_service = SessionService()
        sessions = await session_service.get_user_sessions(
            user_id=UUID(current_user_id),
            limit=min(limit, 100),  # Max 100 per request
            offset=offset
        )
        
        return {
            'sessions': sessions,
            'limit': limit,
            'offset': offset,
            'count': len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error fetching user sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))