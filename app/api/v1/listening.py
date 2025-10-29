"""
Listening Evaluation API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
from typing import Optional
import logging

from app.models.listening import (
    ListeningSessionStart,
    ListeningSessionStartResponse,
    ListeningSessionSubmit,
    ListeningSessionSubmitResponse,
    ListeningSessionDetail,
    ListeningSessionMasteryResponse,
    UserListeningProgressResponse,
    ListeningAnalytics
)
from app.services.listening_service import ListeningService
from app.services.skill_mastery_service import SkillMasteryService
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/listening/sessions",
    response_model=ListeningSessionStartResponse,
    status_code=201
)
async def start_listening_session(
    data: ListeningSessionStart,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Start a new listening test session

    Creates a listening session record with optional audio URL
    Returns session_id for submitting answers
    """
    try:
        # Verify user_id matches authenticated user
        if str(data.user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot create session for another user"
            )

        listening_service = ListeningService()
        result = await listening_service.create_listening_session(
            user_id=data.user_id,
            day_code=data.day_code,
            audio_url=data.audio_url
        )

        return ListeningSessionStartResponse(
            session_id=result['session_id'],
            user_id=result['user_id'],
            day_code=result['day_code'],
            audio_url=result.get('audio_url'),
            started_at=result['started_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting listening session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/listening/sessions/{session_id}/submit",
    response_model=ListeningSessionSubmitResponse
)
async def submit_listening_session(
    session_id: UUID,
    data: ListeningSessionSubmit,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Submit completed listening session with answers

    Automatically:
    - Records all answers with listening-specific data
    - Calculates skill mastery breakdown
    - Updates user's cumulative listening skill mastery
    - Awards XP and badges
    - Updates streaks
    """
    try:
        listening_service = ListeningService()

        # Verify session belongs to current user
        session = await listening_service.get_listening_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Listening session not found")

        if str(session['user_id']) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot submit another user's session"
            )

        # Convert answers to dict format
        answers_data = [answer.dict() for answer in data.answers]

        # Submit session
        result = await listening_service.submit_listening_session(
            session_id=session_id,
            answers=answers_data,
            duration_sec=data.duration_sec,
            score_pct=data.score_pct,
            xp_earned=data.xp_earned,
            audio_replay_count=data.audio_replay_count or 0,
            completed_at=data.completed_at
        )

        return ListeningSessionSubmitResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting listening session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/listening/sessions/{session_id}",
    response_model=ListeningSessionDetail
)
async def get_listening_session(
    session_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get detailed listening session information

    Returns:
    - Session metadata (day, duration, score)
    - All answers with listening-specific fields
    - Audio replay count
    """
    try:
        listening_service = ListeningService()
        result = await listening_service.get_listening_session(session_id)

        if not result:
            raise HTTPException(status_code=404, detail="Listening session not found")

        # Verify session belongs to current user
        if str(result['user_id']) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's session"
            )

        return ListeningSessionDetail(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching listening session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/listening/sessions/{session_id}/mastery",
    response_model=ListeningSessionMasteryResponse
)
async def get_listening_session_mastery(
    session_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get listening skill mastery breakdown for a session

    Returns:
    - Overall session performance
    - Skill-by-skill breakdown with mastery levels
    - Audio replay count
    - Distribution of mastery levels
    """
    try:
        skill_service = SkillMasteryService()
        listening_service = ListeningService()

        # Get session mastery data
        result = await skill_service.get_session_mastery(session_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Session not found or no skill data available"
            )

        # Add listening-specific data
        session = await listening_service.get_listening_session(session_id)
        result['audio_replay_count'] = session.get('audio_replay_count', 0) if session else 0

        return ListeningSessionMasteryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching listening session mastery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/listening/users/{user_id}/progress",
    response_model=UserListeningProgressResponse
)
async def get_user_listening_progress(
    user_id: UUID,
    from_day: Optional[str] = Query(None, regex=r"^day\d+$"),
    to_day: Optional[str] = Query(None, regex=r"^day\d+$"),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's listening skill progress across sessions

    Query Parameters:
    - from_day: Optional start day (e.g., "day1")
    - to_day: Optional end day (e.g., "day10")

    Returns:
    - Overall listening mastery percentage
    - Total sessions completed
    - Audio replay statistics
    - Skill-by-skill progress with trends
    - Average time per question for each skill
    """
    try:
        # Verify user is requesting their own data
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's listening progress"
            )

        listening_service = ListeningService()
        result = await listening_service.get_user_listening_progress(
            user_id=user_id,
            from_day=from_day,
            to_day=to_day
        )

        return UserListeningProgressResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user listening progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/listening/users/{user_id}/analytics",
    response_model=ListeningAnalytics
)
async def get_listening_analytics(
    user_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get comprehensive listening analytics for a user

    Returns:
    - Total sessions and average score
    - Total listening duration
    - Audio replay statistics
    - Strongest and weakest skills
    - Improvement rate over time
    """
    try:
        # Verify user is requesting their own data
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's analytics"
            )

        listening_service = ListeningService()
        result = await listening_service.get_listening_analytics(user_id)

        return ListeningAnalytics(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching listening analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
