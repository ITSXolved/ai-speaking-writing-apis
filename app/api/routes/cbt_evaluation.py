"""
CBT Evaluation API Routes
Endpoint for evaluating language learning questions with CBT-based suggestions
"""

import logging
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.api.schemas import CBTEvaluationRequest, CBTEvaluationResponse
from app.services.cbt_evaluation_service import get_cbt_evaluation_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/cbt-evaluation",
    tags=["CBT Evaluation"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/evaluate",
    response_model=CBTEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate question with CBT suggestions",
    description="""
    Evaluates a language learning question (speaking, writing, listening, reading, or grammar)
    and provides a brief Cognitive Behavioral Therapy (CBT) based suggestion.

    This endpoint helps learners by:
    - Providing constructive feedback on their answers
    - Offering therapeutic suggestions to build confidence
    - Promoting growth mindset and self-compassion
    - Reframing negative thoughts about language learning
    """
)
async def evaluate_question(
    request: CBTEvaluationRequest
) -> CBTEvaluationResponse:
    """
    Evaluate a question and provide CBT-based suggestions

    Args:
        request: CBTEvaluationRequest containing question, answer, skill type, and optional options

    Returns:
        CBTEvaluationResponse with evaluation and therapeutic suggestions

    Raises:
        HTTPException: If evaluation fails
    """
    try:
        logger.info(
            f"Evaluating {request.skill_type} question for user {request.user_id or 'anonymous'}"
        )

        # Get the service
        service = get_cbt_evaluation_service()

        # Perform evaluation
        result = await service.evaluate_question(
            question=request.question,
            answer=request.answer,
            skill_type=request.skill_type,
            options=request.options
        )

        # Return response
        return CBTEvaluationResponse(**result)

    except Exception as e:
        logger.error(f"Error evaluating question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate question: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for CBT evaluation service",
    description="Check if the CBT evaluation service is operational"
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for CBT evaluation service

    Returns:
        Dictionary with service status
    """
    try:
        service = get_cbt_evaluation_service()
        return {
            "status": "healthy",
            "service": "CBT Evaluation Service",
            "supported_skills": ["speaking", "writing", "listening", "reading", "grammar"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
