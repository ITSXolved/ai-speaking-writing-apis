"""
Competency API Routes
Endpoints for saving and tracking speaking/writing evaluations by day
"""

import logging
from fastapi import APIRouter, HTTPException, status, Path, Query
from uuid import UUID

from app.api.schemas import (
    SaveSpeakingEvaluationRequest,
    SaveWritingEvaluationRequest,
    EvaluationSavedResponse,
    UserCompetencyResponse,
    DayCompetencyStatsResponse
)
from app.services.competency_service import get_competency_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/competency",
    tags=["Competency & Progress"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/speaking/save",
    response_model=EvaluationSavedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save speaking evaluation with day code",
    description="""
    Save a speaking evaluation result to the database with day_code tracking.

    This allows tracking user progress across different days (day1, day2, etc.).
    The evaluation includes scores, feedback, and CBT-style suggestions.
    """
)
async def save_speaking_evaluation(
    request: SaveSpeakingEvaluationRequest
) -> EvaluationSavedResponse:
    """
    Save speaking evaluation with day_code

    Args:
        request: Speaking evaluation data including day_code

    Returns:
        Confirmation with evaluation_id

    Raises:
        HTTPException: If save fails
    """
    try:
        logger.info(f"Saving speaking evaluation for user {request.user_id}, day {request.day_code}")

        service = get_competency_service()

        result = await service.save_speaking_evaluation(
            user_id=request.user_id,
            session_id=request.session_id,
            day_code=request.day_code,
            language=request.language,
            user_level=request.user_level,
            total_turns=request.total_turns,
            scores=request.scores,
            strengths=request.strengths,
            improvements=request.improvements,
            suggestions=request.suggestions,
            conversation_summary=request.conversation_summary,
            overall_score=request.overall_score,
            feedback_summary=request.feedback_summary,
            fluency_level=request.fluency_level,
            vocabulary_range=request.vocabulary_range
        )

        return EvaluationSavedResponse(**result, message="Speaking evaluation saved successfully")

    except Exception as e:
        logger.error(f"Error saving speaking evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save speaking evaluation: {str(e)}"
        )


@router.post(
    "/writing/save",
    response_model=EvaluationSavedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save writing evaluation with day code",
    description="""
    Save a writing evaluation result to the database with day_code tracking.

    This allows tracking user progress across different days (day1, day2, etc.).
    The evaluation includes scores, feedback, and improved text version.
    """
)
async def save_writing_evaluation(
    request: SaveWritingEvaluationRequest
) -> EvaluationSavedResponse:
    """
    Save writing evaluation with day_code

    Args:
        request: Writing evaluation data including day_code

    Returns:
        Confirmation with evaluation_id

    Raises:
        HTTPException: If save fails
    """
    try:
        logger.info(f"Saving writing evaluation for user {request.user_id}, day {request.day_code}")

        service = get_competency_service()

        result = await service.save_writing_evaluation(
            user_id=request.user_id,
            day_code=request.day_code,
            original_text=request.original_text,
            language=request.language,
            writing_type=request.writing_type,
            user_level=request.user_level,
            scores=request.scores,
            strengths=request.strengths,
            improvements=request.improvements,
            suggestions=request.suggestions,
            improved_version=request.improved_version,
            overall_score=request.overall_score,
            feedback_summary=request.feedback_summary
        )

        return EvaluationSavedResponse(**result, message="Writing evaluation saved successfully")

    except Exception as e:
        logger.error(f"Error saving writing evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save writing evaluation: {str(e)}"
        )


@router.get(
    "/user/{user_id}",
    response_model=UserCompetencyResponse,
    summary="Get user competency across all days",
    description="""
    Retrieve a user's speaking and writing evaluation progress across all available days.

    Returns completion status and scores for each day, plus average scores.
    Useful for displaying user progress dashboards and competency reports.
    """
)
async def get_user_competency(
    user_id: str = Path(..., description="User ID (UUID or text)")
) -> UserCompetencyResponse:
    """
    Get user's competency and progress across all days

    Args:
        user_id: User identifier

    Returns:
        User progress across all days with scores

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.info(f"Getting competency for user {user_id}")

        service = get_competency_service()
        result = await service.get_user_competency(user_id)

        return UserCompetencyResponse(**result)

    except Exception as e:
        logger.error(f"Error getting user competency: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user competency: {str(e)}"
        )


@router.get(
    "/day/{day_code}/stats",
    response_model=DayCompetencyStatsResponse,
    summary="Get statistics for a specific day",
    description="""
    Retrieve statistics for a specific day across all users.

    Includes total users, completion counts, average scores, and top performers.
    Useful for admin dashboards and progress tracking.
    """
)
async def get_day_stats(
    day_code: str = Path(..., description="Day code (e.g., day1, day2)")
) -> DayCompetencyStatsResponse:
    """
    Get statistics for a specific day across all users

    Args:
        day_code: Day identifier (e.g., day1, day2)

    Returns:
        Statistics including user counts and average scores

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.info(f"Getting stats for day {day_code}")

        service = get_competency_service()
        result = await service.get_day_stats(day_code)

        return DayCompetencyStatsResponse(**result)

    except Exception as e:
        logger.error(f"Error getting day stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get day stats: {str(e)}"
        )


@router.get(
    "/user/{user_id}/day/{day_code}",
    summary="Get user progress for specific day",
    description="""
    Get a user's speaking and writing evaluation results for a specific day.

    Returns completion status and scores if evaluations exist.
    """
)
async def get_user_day_progress(
    user_id: str = Path(..., description="User ID"),
    day_code: str = Path(..., description="Day code (e.g., day1)")
):
    """
    Get user's progress for a specific day

    Args:
        user_id: User identifier
        day_code: Day identifier

    Returns:
        Day-specific progress including scores

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.info(f"Getting progress for user {user_id}, day {day_code}")

        service = get_competency_service()
        competency = await service.get_user_competency(user_id)

        # Filter for specific day
        day_progress = next(
            (d for d in competency["progress_by_day"] if d["day_code"] == day_code),
            None
        )

        if not day_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for day {day_code}"
            )

        return day_progress

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user day progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user day progress: {str(e)}"
        )
