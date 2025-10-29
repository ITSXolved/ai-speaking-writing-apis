from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from uuid import UUID
import uuid
import logging
from datetime import datetime, timedelta, timezone

from ..deps import get_speaking_evaluation_service
from ...services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/speaking", tags=["speaking-evaluation"])

# Schema definitions
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class SpeakingEvaluationRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to evaluate")
    language: str = Field(default="english")
    user_level: str = Field(default="intermediate")
    user_id: Optional[str] = None
    save_evaluation: bool = Field(default=True)

class SpeakingEvaluationResponse(BaseModel):
    overall_score: int
    scores: Dict[str, int]
    suggestions: List[str]


def _normalize_scores(scores: Optional[Dict[str, int]]) -> Dict[str, int]:
    """Ensure score keys use the simplified schema terminology."""
    if not scores:
        return {}

    normalized = dict(scores)

    if 'coherence' in normalized and 'focus' not in normalized:
        normalized['focus'] = normalized.pop('coherence')
    if 'comprehension' in normalized and 'understanding' not in normalized:
        normalized['understanding'] = normalized.pop('comprehension')

    return normalized

class SpeakingProgressEntry(BaseModel):
    date: str
    overall_score: int
    scores: Dict[str, int]
    total_turns: int

class ProgressTrend(BaseModel):
    start_score: int
    end_score: int
    change: int
    direction: str

class SpeakingProgressResponse(BaseModel):
    user_id: str
    days: int
    start_date: str
    end_date: str
    evaluations: List[SpeakingProgressEntry]
    trend: ProgressTrend

class SpeakingEvaluationUploadRequest(BaseModel):
    user_id: str = Field(..., description="UUID of the user")
    session_id: str = Field(..., description="UUID of the session")
    evaluation_id: Optional[str] = Field(None, description="Optional existing evaluation ID")
    language: str = "english"
    user_level: str = "intermediate"
    total_turns: int = 0
    overall_score: int = Field(..., ge=0, le=100)
    scores: Dict[str, int]
    suggestions: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    conversation_summary: Optional[str] = None
    feedback_summary: Optional[str] = None
    fluency_level: Optional[str] = None
    vocabulary_range: Optional[str] = None
    created_at: Optional[str] = Field(None, description="ISO timestamp (defaults to now)")

class SpeakingSelfEvaluationScores(BaseModel):
    """Self-evaluation scores for speaking assessment (0-100 for each category)"""
    fluency: int = Field(..., ge=0, le=100, description="Fluency score")
    pronunciation: int = Field(..., ge=0, le=100, description="Pronunciation score")
    vocabulary: int = Field(..., ge=0, le=100, description="Vocabulary score")
    grammar: int = Field(..., ge=0, le=100, description="Grammar score")
    focus: int = Field(..., ge=0, le=100, description="Focus score")
    understanding: int = Field(..., ge=0, le=100, description="Understanding score")

class SpeakingSelfEvaluationRequest(BaseModel):
    """Request model for speaking self-evaluation"""
    user_id: str = Field(..., description="UUID of the user")
    session_id: str = Field(..., description="UUID of the session")
    scores: SpeakingSelfEvaluationScores = Field(..., description="Scores for each category (0-100)")
    user_level: str = Field(default="intermediate", description="User proficiency level")
    evaluation_id: Optional[str] = Field(None, description="Optional existing evaluation ID")
    created_at: Optional[str] = Field(None, description="ISO timestamp (defaults to now)")

class SpeakingDailyCompetency(BaseModel):
    """Competency scores for a single day"""
    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    overall_score: int = Field(..., ge=0, le=100, description="Overall score (average of all competencies)")
    fluency: int = Field(..., ge=0, le=100, description="Fluency score")
    pronunciation: int = Field(..., ge=0, le=100, description="Pronunciation score")
    vocabulary: int = Field(..., ge=0, le=100, description="Vocabulary score")
    grammar: int = Field(..., ge=0, le=100, description="Grammar score")
    focus: int = Field(..., ge=0, le=100, description="Focus score")
    understanding: int = Field(..., ge=0, le=100, description="Understanding score")
    evaluation_count: int = Field(..., description="Number of evaluations on this day")

class SpeakingCompetenciesResponse(BaseModel):
    """Response containing daily competency scores for speaking"""
    user_id: str
    days: int
    start_date: str
    end_date: str
    daily_competencies: List[SpeakingDailyCompetency]
    average_scores: Dict[str, float] = Field(..., description="Average score for each competency across all days")

@router.post("/evaluate", response_model=SpeakingEvaluationResponse)
async def evaluate_speaking(
    request: SpeakingEvaluationRequest,
    background_tasks: BackgroundTasks,
    speaking_service = Depends(get_speaking_evaluation_service)
):
    """
    Evaluate speaking performance based on session conversation data

    This endpoint retrieves all conversation turns from a session and uses LLM
    to provide a focused speaking evaluation including:
    - Fluency assessment
    - Pronunciation feedback
    - Vocabulary usage
    - Grammar accuracy
    - Focus and understanding scores
    """
    try:
        # Validate session_id is a valid UUID
        try:
            session_uuid = UUID(request.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id format")

        # Perform evaluation
        evaluation = await speaking_service.evaluate_speaking(
            session_id=session_uuid,
            language=request.language,
            user_level=request.user_level
        )

        # Normalize scores to the simplified schema terminology
        normalized_scores = _normalize_scores(evaluation.scores)

        # Generate unique evaluation ID for persistence (not returned in schema)
        evaluation_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        # Save to database if requested
        stored_user_id = None
        if request.user_id:
            try:
                stored_user_id = str(UUID(request.user_id))
            except ValueError:
                logger.warning("Skipping evaluation persistence for non-UUID user_id", user_id=request.user_id)

        if request.save_evaluation and stored_user_id:
            evaluation_data = {
                "id": evaluation_id,
                "user_id": stored_user_id,
                "session_id": request.session_id,
                "language": request.language,
                "user_level": request.user_level,
                "total_turns": evaluation.total_turns,
                "scores": normalized_scores,
                "suggestions": evaluation.suggestions,
                "overall_score": evaluation.overall_score,
                "strengths": [],
                "improvements": [],
                "conversation_summary": "Summary not provided in simplified schema",
                "feedback_summary": "Detailed feedback not provided in simplified schema",
                "fluency_level": "not_assessed",
                "vocabulary_range": "not_assessed",
                "created_at": created_at
            }

            # Background task to save to database
            background_tasks.add_task(_save_evaluation_to_db, evaluation_data)

        return SpeakingEvaluationResponse(
            overall_score=evaluation.overall_score,
            scores=normalized_scores,
            suggestions=evaluation.suggestions
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speaking evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.get("/tips", response_model=Dict[str, List[str]])
async def get_speaking_tips(
    language: str = "english",
    proficiency_level: str = "intermediate",
    speaking_service = Depends(get_speaking_evaluation_service)
):
    """
    Get speaking tips for specified language and proficiency level
    """
    try:
        tips = await speaking_service.get_speaking_tips(language, proficiency_level)

        return {
            "language": language,
            "proficiency_level": proficiency_level,
            "tips": tips
        }

    except Exception as e:
        logger.error(f"Failed to get speaking tips: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve speaking tips")

@router.get("/evaluation/{session_id}", response_model=SpeakingEvaluationResponse)
async def get_evaluation(
    session_id: str
):
    """
    Retrieve a specific speaking evaluation by session ID
    """
    try:
        supabase = get_supabase_client()

        # Get evaluation from database
        response = supabase.table("speaking_evaluations")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        evaluation_data = response.data[0]

        scores = _normalize_scores(evaluation_data.get("scores"))
        suggestions = evaluation_data.get("suggestions") or []
        overall = evaluation_data.get("overall_score", 0)

        return SpeakingEvaluationResponse(
            overall_score=overall,
            scores=scores,
            suggestions=suggestions
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve evaluation")

@router.get("/evaluations/user/{user_id}", response_model=List[SpeakingEvaluationResponse])
async def get_user_evaluations(
    user_id: str,
    limit: int = 20,
    offset: int = 0
):
    """
    Get all speaking evaluations for a specific user
    """
    try:
        supabase = get_supabase_client()

        response = supabase.table("speaking_evaluations")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        evaluations = []
        for eval_data in response.data:
            evaluations.append(SpeakingEvaluationResponse(
                overall_score=eval_data.get("overall_score", 0),
                scores=_normalize_scores(eval_data.get("scores")),
                suggestions=eval_data.get("suggestions") or []
            ))

        return evaluations

    except Exception as e:
        logger.error(f"Failed to get user evaluations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve evaluations")

@router.get("/progress", response_model=SpeakingProgressResponse)
async def get_speaking_progress(
    user_id: str = Query(..., description="User identifier"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include")
):
    """
    Retrieve speaking evaluation progress for the specified user over the last `days`.
    """
    try:
        try:
            user_uuid = str(UUID(user_id))
        except ValueError:
            logger.warning("Speaking progress requested with non-UUID user_id", user_id=user_id)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days - 1)
            empty_trend = ProgressTrend(
                start_score=0,
                end_score=0,
                change=0,
                direction="stable"
            )
            return SpeakingProgressResponse(
                user_id=user_id,
                days=days,
                start_date=start_date.date().isoformat(),
                end_date=end_date.date().isoformat(),
                evaluations=[],
                trend=empty_trend
            )

        supabase = get_supabase_client()
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days - 1)

        start_iso = start_date.isoformat()

        response = supabase.table("speaking_evaluations")\
            .select("created_at, overall_score, scores, total_turns")\
            .eq("user_id", user_uuid)\
            .gte("created_at", start_iso)\
            .order("created_at", desc=False)\
            .execute()

        evaluations = []
        overall_scores = []

        for record in response.data or []:
            created_at = record.get("created_at")
            overall = record.get("overall_score", 0)
            scores = _normalize_scores(record.get("scores"))
            total_turns = record.get("total_turns") or 0

            timestamp = end_date
            if created_at:
                try:
                    created_at = created_at.replace("Z", "+00:00")
                    timestamp = datetime.fromisoformat(created_at)
                except ValueError:
                    logger.warning("Failed to parse speaking evaluation timestamp", created_at=created_at)

            numeric_scores = {}
            for k, v in scores.items():
                try:
                    numeric_scores[k] = int(round(float(v)))
                except (TypeError, ValueError):
                    numeric_scores[k] = 0

            try:
                overall_int = int(round(float(overall)))
            except (TypeError, ValueError):
                overall_int = 0

            try:
                total_turns_int = int(total_turns)
            except (TypeError, ValueError):
                total_turns_int = 0

            evaluations.append(SpeakingProgressEntry(
                date=timestamp.date().isoformat(),
                overall_score=overall_int,
                scores=numeric_scores,
                total_turns=total_turns_int
            ))
            overall_scores.append(overall_int)

        if not evaluations:
            trend = ProgressTrend(
                start_score=0,
                end_score=0,
                change=0,
                direction="stable"
            )
        else:
            start_score = overall_scores[0]
            end_score = overall_scores[-1]
            change = end_score - start_score
            if change > 0:
                direction = "improving"
            elif change < 0:
                direction = "declining"
            else:
                direction = "stable"
            trend = ProgressTrend(
                start_score=start_score,
                end_score=end_score,
                change=change,
                direction=direction
            )

        return SpeakingProgressResponse(
            user_id=user_id,
            days=days,
            start_date=start_date.date().isoformat(),
            end_date=end_date.date().isoformat(),
            evaluations=evaluations,
            trend=trend
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve speaking progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve speaking progress")

@router.get("/competencies", response_model=SpeakingCompetenciesResponse)
async def get_speaking_competencies(
    user_id: str = Query(..., description="User identifier"),
    days: int = Query(30, ge=1, le=365, description="Number of past days to include")
):
    """
    Retrieve daily competency scores (by category) for speaking evaluations.

    Returns scores for each competency category (fluency, pronunciation, vocabulary,
    grammar, focus, understanding) grouped by day, along with average scores across
    all days.
    """
    try:
        supabase = get_supabase_client()
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days - 1)
        start_iso = start_date.isoformat()

        # Fetch all evaluations in date range
        response = supabase.table("speaking_evaluations")\
            .select("created_at, scores, overall_score")\
            .eq("user_id", user_id)\
            .gte("created_at", start_iso)\
            .order("created_at", desc=False)\
            .execute()

        # Group evaluations by date and aggregate scores
        daily_data = {}
        all_scores = {
            "overall_score": [],
            "fluency": [],
            "pronunciation": [],
            "vocabulary": [],
            "grammar": [],
            "focus": [],
            "understanding": []
        }

        for record in response.data or []:
            created_at = record.get("created_at")
            scores = _normalize_scores(record.get("scores"))
            overall_score = record.get("overall_score", 0)

            # Parse date
            try:
                created_at = created_at.replace("Z", "+00:00")
                timestamp = datetime.fromisoformat(created_at)
                date_key = timestamp.date().isoformat()
            except (ValueError, AttributeError):
                logger.warning(f"Failed to parse timestamp: {created_at}")
                continue

            # Initialize daily data if not exists
            if date_key not in daily_data:
                daily_data[date_key] = {
                    "overall_score": [],
                    "fluency": [],
                    "pronunciation": [],
                    "vocabulary": [],
                    "grammar": [],
                    "focus": [],
                    "understanding": []
                }

            # Add overall score
            try:
                overall_int = int(round(float(overall_score)))
            except (TypeError, ValueError):
                overall_int = 0
            daily_data[date_key]["overall_score"].append(overall_int)
            all_scores["overall_score"].append(overall_int)

            # Add scores to daily aggregation
            for category in ["fluency", "pronunciation", "vocabulary", "grammar", "focus", "understanding"]:
                score = scores.get(category, 0)
                try:
                    score_int = int(round(float(score)))
                except (TypeError, ValueError):
                    score_int = 0

                daily_data[date_key][category].append(score_int)
                all_scores[category].append(score_int)

        # Calculate daily averages
        daily_competencies = []
        for date_key, scores_data in sorted(daily_data.items()):
            evaluation_count = len(scores_data["fluency"])

            daily_comp = SpeakingDailyCompetency(
                date=date_key,
                overall_score=int(round(sum(scores_data["overall_score"]) / evaluation_count)) if evaluation_count > 0 else 0,
                fluency=int(round(sum(scores_data["fluency"]) / evaluation_count)) if evaluation_count > 0 else 0,
                pronunciation=int(round(sum(scores_data["pronunciation"]) / evaluation_count)) if evaluation_count > 0 else 0,
                vocabulary=int(round(sum(scores_data["vocabulary"]) / evaluation_count)) if evaluation_count > 0 else 0,
                grammar=int(round(sum(scores_data["grammar"]) / evaluation_count)) if evaluation_count > 0 else 0,
                focus=int(round(sum(scores_data["focus"]) / evaluation_count)) if evaluation_count > 0 else 0,
                understanding=int(round(sum(scores_data["understanding"]) / evaluation_count)) if evaluation_count > 0 else 0,
                evaluation_count=evaluation_count
            )
            daily_competencies.append(daily_comp)

        # Calculate overall averages
        average_scores = {}
        for category, scores_list in all_scores.items():
            if scores_list:
                average_scores[category] = round(sum(scores_list) / len(scores_list), 2)
            else:
                average_scores[category] = 0.0

        return SpeakingCompetenciesResponse(
            user_id=user_id,
            days=days,
            start_date=start_date.date().isoformat(),
            end_date=end_date.date().isoformat(),
            daily_competencies=daily_competencies,
            average_scores=average_scores
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve speaking competencies: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve speaking competencies")

@router.post("/evaluation/save", response_model=StandardResponse)
async def save_speaking_evaluation(payload: SpeakingEvaluationUploadRequest):
    """
    Manually persist a speaking evaluation record to Supabase.
    """
    try:
        try:
            user_uuid = UUID(payload.user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="user_id must be a valid UUID string")

        try:
            session_uuid = UUID(payload.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="session_id must be a valid UUID string")

        evaluation_id = payload.evaluation_id or str(uuid.uuid4())
        created_at = payload.created_at or datetime.now(timezone.utc).isoformat()

        normalized_scores = {}
        for k, v in _normalize_scores(payload.scores).items():
            try:
                normalized_scores[k] = int(round(float(v)))
            except (TypeError, ValueError):
                normalized_scores[k] = 0

        record = {
            "id": evaluation_id,
            "user_id": str(user_uuid),
            "session_id": str(session_uuid),
            "language": payload.language,
            "user_level": payload.user_level,
            "total_turns": int(payload.total_turns),
            "scores": normalized_scores,
            "suggestions": payload.suggestions,
            "overall_score": int(payload.overall_score),
            "strengths": payload.strengths,
            "improvements": payload.improvements,
            "conversation_summary": payload.conversation_summary or "",
            "feedback_summary": payload.feedback_summary or "",
            "fluency_level": payload.fluency_level or "not_assessed",
            "vocabulary_range": payload.vocabulary_range or "not_assessed",
            "created_at": created_at
        }

        supabase = get_supabase_client()
        supabase.table("speaking_evaluations").insert(record).execute()

        return StandardResponse(
            success=True,
            message="Speaking evaluation saved",
            data={"evaluation_id": evaluation_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save speaking evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to save speaking evaluation")

@router.post("/evaluation/self-save", response_model=StandardResponse)
async def save_self_evaluation(payload: SpeakingSelfEvaluationRequest):
    """
    Save self-evaluation for speaking assessment.

    Accepts scores from user (0-100 for each category):
    - Fluency
    - Pronunciation
    - Vocabulary
    - Grammar
    - Focus
    - Understanding

    Overall score is computed automatically as weighted average.
    """
    try:
        # Validate user_id is a valid UUID
        try:
            user_uuid = UUID(payload.user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="user_id must be a valid UUID string")

        # Validate session_id is a valid UUID
        try:
            session_uuid = UUID(payload.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="session_id must be a valid UUID string")

        evaluation_id = payload.evaluation_id or str(uuid.uuid4())
        created_at = payload.created_at or datetime.now(timezone.utc).isoformat()

        # Convert SpeakingSelfEvaluationScores to dict
        scores_dict = {
            "fluency": payload.scores.fluency,
            "pronunciation": payload.scores.pronunciation,
            "vocabulary": payload.scores.vocabulary,
            "grammar": payload.scores.grammar,
            "focus": payload.scores.focus,
            "understanding": payload.scores.understanding
        }

        # Calculate weighted average for overall score
        # Weights matching the importance of each speaking skill
        weights = {
            "fluency": 0.20,
            "pronunciation": 0.20,
            "vocabulary": 0.15,
            "grammar": 0.15,
            "focus": 0.15,
            "understanding": 0.15
        }

        overall_score = sum(scores_dict[key] * weights[key] for key in scores_dict.keys())
        overall_score = int(round(overall_score))

        # Stationary/constant fields
        language = "english"
        total_turns = 0
        suggestions = []
        strengths = []
        improvements = []
        conversation_summary = ""
        feedback_summary = ""
        fluency_level = "self_assessed"
        vocabulary_range = "self_assessed"

        record = {
            "id": evaluation_id,
            "user_id": str(user_uuid),
            "session_id": str(session_uuid),
            "language": language,
            "user_level": payload.user_level,
            "total_turns": total_turns,
            "scores": scores_dict,
            "suggestions": suggestions,
            "overall_score": overall_score,
            "strengths": strengths,
            "improvements": improvements,
            "conversation_summary": conversation_summary,
            "feedback_summary": feedback_summary,
            "fluency_level": fluency_level,
            "vocabulary_range": vocabulary_range,
            "created_at": created_at
        }

        supabase = get_supabase_client()
        supabase.table("speaking_evaluations").insert(record).execute()

        return StandardResponse(
            success=True,
            message="Self-evaluation saved successfully",
            data={
                "evaluation_id": evaluation_id,
                "overall_score": overall_score,
                "scores": scores_dict
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save self-evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to save self-evaluation")

@router.delete("/evaluation/{evaluation_id}", response_model=StandardResponse)
async def delete_evaluation(
    evaluation_id: str
):
    """
    Delete a speaking evaluation
    """
    try:
        supabase = get_supabase_client()

        result = supabase.table("speaking_evaluations")\
            .delete()\
            .eq("id", evaluation_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        return StandardResponse(
            success=True,
            message="Evaluation deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete evaluation")

# Helper function for background task
async def _save_evaluation_to_db(evaluation_data: Dict[str, Any]):
    """Background task to save evaluation to database"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("speaking_evaluations").insert(evaluation_data).execute()
        logger.info(f"Saved speaking evaluation {evaluation_data['id']} to database")
    except Exception as e:
        logger.error(f"Failed to save speaking evaluation to database: {e}")
