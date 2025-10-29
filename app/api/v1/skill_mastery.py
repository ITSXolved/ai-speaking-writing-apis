"""
Skill Mastery API endpoints for evaluation and progress tracking
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
from typing import Optional
import logging

from app.models.sessions import (
    SessionMasteryResponse,
    UserSkillProgressResponse,
    UserMasteryOverviewResponse
)
from app.services.skill_mastery_service import SkillMasteryService
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/sessions/{session_id}/mastery",
    response_model=SessionMasteryResponse
)
async def get_session_mastery(
    session_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get skill mastery breakdown for a specific session

    Returns:
    - Overall session score and duration
    - Skill-by-skill performance (correct/total, mastery %, mastery level)
    - Count of skills at each mastery level
    """
    try:
        skill_service = SkillMasteryService()
        result = await skill_service.get_session_mastery(session_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Session not found or no skill data available"
            )

        # TODO: Verify session belongs to current user

        return SessionMasteryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session mastery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}/skills/progress",
    response_model=UserSkillProgressResponse
)
async def get_user_skill_progress(
    user_id: UUID,
    modality: str = Query(..., regex="^(listening|reading|grammar)$"),
    from_day: Optional[str] = Query(None, regex=r"^day\d+$"),
    to_day: Optional[str] = Query(None, regex=r"^day\d+$"),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's skill progress for a specific modality

    Query Parameters:
    - modality: listening, reading, or grammar
    - from_day: Optional start day (e.g., "day1")
    - to_day: Optional end day (e.g., "day10")

    Returns:
    - List of skills with practice stats, mastery %, and trends
    """
    try:
        # Verify user is requesting their own data
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's skill progress"
            )

        skill_service = SkillMasteryService()
        result = await skill_service.get_user_skill_progress(
            user_id=user_id,
            modality=modality,
            from_day=from_day,
            to_day=to_day
        )

        return UserSkillProgressResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user skill progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}/mastery-overview",
    response_model=UserMasteryOverviewResponse
)
async def get_mastery_overview(
    user_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get complete mastery overview across all modalities

    Returns:
    - Overall mastery percentage per modality
    - Skill-by-skill mastery percentages for listening, reading, and grammar
    """
    try:
        # Verify user is requesting their own data
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's mastery overview"
            )

        skill_service = SkillMasteryService()
        result = await skill_service.get_mastery_overview(user_id)

        return UserMasteryOverviewResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching mastery overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}/competencies/{modality}/day/{day_code}",
    response_model=UserSkillProgressResponse
)
async def get_competencies_by_day(
    user_id: UUID,
    modality: str,
    day_code: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get skill competencies (mastery breakdown) for a specific modality and day

    Path Parameters:
    - user_id: User UUID
    - modality: listening, reading, or grammar
    - day_code: Specific day (e.g., "day1", "day5", "day10")

    Returns:
    - Skill breakdown with mastery percentages, levels, and trends for that day
    """
    try:
        # Verify user is requesting their own data
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's competencies"
            )

        # Validate modality
        if modality not in ["listening", "reading", "grammar"]:
            raise HTTPException(
                status_code=400,
                detail="Modality must be 'listening', 'reading', or 'grammar'"
            )

        # Validate day_code format
        import re
        if not re.match(r"^day\d+$", day_code):
            raise HTTPException(
                status_code=400,
                detail="Day code must be in format 'dayN' (e.g., 'day1', 'day10')"
            )

        skill_service = SkillMasteryService()
        result = await skill_service.get_competencies_by_day(
            user_id=user_id,
            modality=modality,
            day_code=day_code
        )

        return UserSkillProgressResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching competencies by day: {e}")
        raise HTTPException(status_code=500, detail=str(e))
