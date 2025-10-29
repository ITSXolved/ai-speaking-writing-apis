from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uuid
import logging
from datetime import datetime, timedelta, timezone

# CHANGE THESE IMPORTS:
# from ..deps import get_writing_evaluation_service, get_supabase_client, get_email_service
# from ..schemas import StandardResponse
# from ...services.writing_evaluation_service import WritingEvaluationService, WritingEvaluation
# from ...services.supabase_client import SupabaseClient
# from ...services.email_service import EmailService

# TO THESE IMPORTS (matching your existing structure):
from ..deps import get_writing_evaluation_service
from ...services.supabase_client import get_supabase_client  # Use your existing function

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/writing", tags=["writing-evaluation"])

# Add local schema definitions
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class WritingEvaluationRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    language: str = Field(default="english")
    writing_type: str = Field(default="general")
    user_level: str = Field(default="intermediate")
    user_id: Optional[str] = None
    save_evaluation: bool = Field(default=True)

class ErrorHighlightResponse(BaseModel):
    """Error highlighting with visual markers"""
    error_text: str  # Text with error (red highlight on frontend)
    correction: str  # Corrected text (green highlight on frontend)
    error_type: str  # Type: grammar, spelling, punctuation, word choice
    position: int    # Position in original text

class EvaluationResponse(BaseModel):
    """Minimal response with only 3 essential fields"""
    overall_score: int
    scores: Dict[str, int]
    improved_version: str  # HTML with inline red/green highlighting (ready for Next.js)

# Legacy response for backward compatibility
class EvaluationResponseFull(BaseModel):
    evaluation_id: str
    original_text: str
    scores: Dict[str, int]
    strengths: List[str]
    improvements: List[str]
    suggestions: List[str]
    improved_version: str
    overall_score: int
    feedback_summary: str
    error_highlights: List[ErrorHighlightResponse]
    created_at: datetime

class WritingTipsResponse(BaseModel):
    """Response schema for writing tips endpoint"""
    language: str
    writing_type: str
    tips: List[str]

class WritingProgressEntry(BaseModel):
    date: str
    overall_score: int
    scores: Dict[str, int]

class ProgressTrend(BaseModel):
    start_score: int
    end_score: int
    change: int
    direction: str

class WritingProgressResponse(BaseModel):
    user_id: str
    days: int
    start_date: str
    end_date: str
    evaluations: List[WritingProgressEntry]
    trend: ProgressTrend

class WritingEvaluationUploadRequest(BaseModel):
    user_id: str = Field(..., description="UUID of the user")
    evaluation_id: Optional[str] = Field(None, description="Optional existing evaluation ID")
    original_text: str
    language: str = "english"
    writing_type: str = "general"
    user_level: str = "intermediate"
    overall_score: int = Field(..., ge=0, le=100)
    scores: Dict[str, int]
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    improved_version: str
    feedback_summary: Optional[str] = None
    created_at: Optional[str] = Field(None, description="ISO timestamp (defaults to now)")

class SelfEvaluationScores(BaseModel):
    """Self-evaluation scores for writing assessment (0-100 for each category)"""
    grammar: int = Field(..., ge=0, le=100, description="Grammar score")
    vocabulary: int = Field(..., ge=0, le=100, description="Vocabulary score")
    coherence: int = Field(..., ge=0, le=100, description="Coherence score")
    style: int = Field(..., ge=0, le=100, description="Style score")
    clarity: int = Field(..., ge=0, le=100, description="Clarity score")
    engagement: int = Field(..., ge=0, le=100, description="Engagement score")

class WritingSelfEvaluationRequest(BaseModel):
    """Request model for writing self-evaluation"""
    user_id: str = Field(..., description="UUID of the user")
    scores: SelfEvaluationScores = Field(..., description="Scores for each category (0-100)")
    user_level: str = Field(default="intermediate", description="User proficiency level")
    evaluation_id: Optional[str] = Field(None, description="Optional existing evaluation ID")
    created_at: Optional[str] = Field(None, description="ISO timestamp (defaults to now)")

class DailyCompetency(BaseModel):
    """Competency scores for a single day"""
    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    overall_score: int = Field(..., ge=0, le=100, description="Overall score (average of all competencies)")
    grammar: int = Field(..., ge=0, le=100, description="Grammar score")
    vocabulary: int = Field(..., ge=0, le=100, description="Vocabulary score")
    coherence: int = Field(..., ge=0, le=100, description="Coherence score")
    style: int = Field(..., ge=0, le=100, description="Style score")
    clarity: int = Field(..., ge=0, le=100, description="Clarity score")
    engagement: int = Field(..., ge=0, le=100, description="Engagement score")
    evaluation_count: int = Field(..., description="Number of evaluations on this day")

class WritingCompetenciesResponse(BaseModel):
    """Response containing daily competency scores for writing"""
    user_id: str
    days: int
    start_date: str
    end_date: str
    daily_competencies: List[DailyCompetency]
    average_scores: Dict[str, float] = Field(..., description="Average score for each competency across all days")

class WritingTask(BaseModel):
    """Daily writing task/question"""
    task_id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description/prompt")
    writing_type: str = Field(default="general", description="Type of writing (essay, email, story, etc.)")
    difficulty_level: str = Field(default="intermediate", description="Task difficulty level")
    word_count_min: Optional[int] = Field(None, description="Minimum word count")
    word_count_max: Optional[int] = Field(None, description="Maximum word count")
    time_limit_minutes: Optional[int] = Field(None, description="Suggested time limit in minutes")
    tags: List[str] = Field(default_factory=list, description="Task tags/categories")

class DailyWritingTasksResponse(BaseModel):
    """Response containing daily writing tasks"""
    date: str = Field(..., description="Date for which tasks are returned")
    tasks: List[WritingTask]
    total_count: int

class SubmitWritingTaskRequest(BaseModel):
    """Request to submit and evaluate a writing task"""
    task_id: str = Field(..., description="ID of the task being submitted")
    user_id: str = Field(..., description="UUID of the user")
    text: str = Field(..., min_length=10, max_length=5000, description="Written response")
    language: str = Field(default="english")
    user_level: str = Field(default="intermediate")
    save_evaluation: bool = Field(default=True)

class WritingTaskEvaluationResponse(BaseModel):
    """Response after evaluating a writing task submission"""
    task_id: str
    evaluation_id: str
    overall_score: int
    scores: Dict[str, int]
    improved_version: str
    feedback_summary: str
    strengths: List[str]
    improvements: List[str]
    word_count: int
    meets_requirements: bool

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_writing(
    request: WritingEvaluationRequest,
    background_tasks: BackgroundTasks,
    writing_service = Depends(get_writing_evaluation_service)
):
    """
    Evaluate writing and return simplified response with error highlights

    Returns:
    - overall_score: Overall writing score (0-100)
    - scores: Detailed category scores
    - improved_version: Corrected text
    - error_highlights: List of errors with corrections (red/green highlighting)
    """
    try:
        # Perform evaluation
        evaluation = await writing_service.evaluate_writing(
            text=request.text,
            language=request.language,
            writing_type=request.writing_type,
            user_level=request.user_level
        )

        # Generate unique evaluation ID
        evaluation_id = str(uuid.uuid4())

        # Convert error highlights to response format
        error_highlights_response = [
            ErrorHighlightResponse(
                error_text=eh.error_text,
                correction=eh.correction,
                error_type=eh.error_type,
                position=eh.position
            )
            for eh in evaluation.error_highlights
        ]

        # Save to database if requested
        if request.save_evaluation and request.user_id:
            evaluation_data = {
                "id": evaluation_id,
                "user_id": request.user_id,
                "original_text": evaluation.original_text,
                "language": request.language,
                "writing_type": request.writing_type,
                "user_level": request.user_level,
                "scores": evaluation.scores,
                "improved_version": evaluation.improved_version,
                "overall_score": evaluation.overall_score,
                "strengths": evaluation.strengths or [],
                "improvements": evaluation.improvements or [],
                "suggestions": evaluation.suggestions or [],
                "feedback_summary": evaluation.feedback_summary or "",
                "created_at": datetime.now().isoformat()
            }

            # Background task to save to database
            background_tasks.add_task(_save_evaluation_to_db, evaluation_data)

        # Return minimal response (only 3 fields)
        return EvaluationResponse(
            overall_score=evaluation.overall_score,
            scores=evaluation.scores,
            improved_version=evaluation.improved_version_html  # HTML with red/green highlighting
        )

    except Exception as e:
        logger.error(f"Writing evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.post("/improve", response_model=Dict[str, str])
async def improve_writing(
    request: WritingEvaluationRequest,  # Reuse the same request model
    writing_service = Depends(get_writing_evaluation_service)
):
    """Get an improved version of the provided text"""
    try:
        # First evaluate to get improvement suggestions
        evaluation = await writing_service.evaluate_writing(
            text=request.text,
            language=request.language,
            writing_type=request.writing_type
        )
        
        return {
            "original_text": request.text,
            "improved_version": evaluation.improved_version,
            "key_improvements": ", ".join(evaluation.improvements[:3])
        }
        
    except Exception as e:
        logger.error(f"Text improvement failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to improve text")

@router.get("/tips", response_model=WritingTipsResponse)
async def get_writing_tips(
    language: str = "english",
    writing_type: str = "general",
    writing_service = Depends(get_writing_evaluation_service)
):
    """Get writing tips for specified language and writing type"""
    try:
        tips = await writing_service.get_writing_tips(language, writing_type)
        
        return WritingTipsResponse(
            language=language,
            writing_type=writing_type,
            tips=tips
        )
        
    except Exception as e:
        logger.error(f"Failed to get writing tips: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve writing tips")

@router.get("/progress", response_model=WritingProgressResponse)
async def get_writing_progress(
    user_id: str = Query(..., description="User identifier"),
    days: int = Query(30, ge=1, le=365, description="Number of past days to include")
):
    """
    Retrieve writing evaluation progress for the specified user over the last `days`.
    """
    try:
        supabase = get_supabase_client()
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days - 1)

        start_iso = start_date.isoformat()

        response = supabase.table("writing_evaluations")\
            .select("created_at, overall_score, scores")\
            .eq("user_id", user_id)\
            .gte("created_at", start_iso)\
            .order("created_at", desc=False)\
            .execute()

        evaluations = []
        overall_scores = []

        for record in response.data or []:
            created_at = record.get("created_at")
            overall = record.get("overall_score", 0)
            scores = record.get("scores") or {}

            timestamp = end_date
            if created_at:
                try:
                    created_at = created_at.replace("Z", "+00:00")
                    timestamp = datetime.fromisoformat(created_at)
                except ValueError:
                    logger.warning("Failed to parse writing evaluation timestamp", created_at=created_at)

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

            evaluations.append(WritingProgressEntry(
                date=timestamp.date().isoformat(),
                overall_score=overall_int,
                scores=numeric_scores
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

        return WritingProgressResponse(
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
        logger.error(f"Failed to retrieve writing progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve writing progress")

@router.get("/competencies", response_model=WritingCompetenciesResponse)
async def get_writing_competencies(
    user_id: str = Query(..., description="User identifier"),
    days: int = Query(30, ge=1, le=365, description="Number of past days to include")
):
    """
    Retrieve daily competency scores (by category) for writing evaluations.

    Returns scores for each competency category (grammar, vocabulary, coherence,
    style, clarity, engagement) grouped by day, along with average scores across
    all days.
    """
    try:
        supabase = get_supabase_client()
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days - 1)
        start_iso = start_date.isoformat()

        # Fetch all evaluations in date range
        response = supabase.table("writing_evaluations")\
            .select("created_at, scores, overall_score")\
            .eq("user_id", user_id)\
            .gte("created_at", start_iso)\
            .order("created_at", desc=False)\
            .execute()

        # Group evaluations by date and aggregate scores
        daily_data = {}
        all_scores = {
            "overall_score": [],
            "grammar": [],
            "vocabulary": [],
            "coherence": [],
            "style": [],
            "clarity": [],
            "engagement": []
        }

        for record in response.data or []:
            created_at = record.get("created_at")
            scores = record.get("scores") or {}
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
                    "grammar": [],
                    "vocabulary": [],
                    "coherence": [],
                    "style": [],
                    "clarity": [],
                    "engagement": []
                }

            # Add overall score
            try:
                overall_int = int(round(float(overall_score)))
            except (TypeError, ValueError):
                overall_int = 0
            daily_data[date_key]["overall_score"].append(overall_int)
            all_scores["overall_score"].append(overall_int)

            # Add scores to daily aggregation
            for category in ["grammar", "vocabulary", "coherence", "style", "clarity", "engagement"]:
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
            evaluation_count = len(scores_data["grammar"])

            daily_comp = DailyCompetency(
                date=date_key,
                overall_score=int(round(sum(scores_data["overall_score"]) / evaluation_count)) if evaluation_count > 0 else 0,
                grammar=int(round(sum(scores_data["grammar"]) / evaluation_count)) if evaluation_count > 0 else 0,
                vocabulary=int(round(sum(scores_data["vocabulary"]) / evaluation_count)) if evaluation_count > 0 else 0,
                coherence=int(round(sum(scores_data["coherence"]) / evaluation_count)) if evaluation_count > 0 else 0,
                style=int(round(sum(scores_data["style"]) / evaluation_count)) if evaluation_count > 0 else 0,
                clarity=int(round(sum(scores_data["clarity"]) / evaluation_count)) if evaluation_count > 0 else 0,
                engagement=int(round(sum(scores_data["engagement"]) / evaluation_count)) if evaluation_count > 0 else 0,
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

        return WritingCompetenciesResponse(
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
        logger.error(f"Failed to retrieve writing competencies: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve writing competencies")

@router.post("/evaluation/save", response_model=StandardResponse)
async def save_writing_evaluation(payload: WritingEvaluationUploadRequest):
    """
    Manually persist a writing evaluation record to Supabase.
    """
    try:
        try:
            user_uuid = uuid.UUID(payload.user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="user_id must be a valid UUID string")

        evaluation_id = payload.evaluation_id or str(uuid.uuid4())
        created_at = payload.created_at or datetime.now(timezone.utc).isoformat()

        normalized_scores = {}
        for k, v in payload.scores.items():
            try:
                normalized_scores[k] = int(round(float(v)))
            except (TypeError, ValueError):
                normalized_scores[k] = 0

        record = {
            "id": evaluation_id,
            "user_id": str(user_uuid),
            "original_text": payload.original_text,
            "language": payload.language,
            "writing_type": payload.writing_type,
            "user_level": payload.user_level,
            "scores": normalized_scores,
            "improved_version": payload.improved_version,
            "overall_score": int(payload.overall_score),
            "strengths": payload.strengths,
            "improvements": payload.improvements,
            "suggestions": payload.suggestions,
            "feedback_summary": payload.feedback_summary or "",
            "created_at": created_at
        }

        supabase = get_supabase_client()
        supabase.table("writing_evaluations").insert(record).execute()

        return StandardResponse(
            success=True,
            message="Writing evaluation saved",
            data={"evaluation_id": evaluation_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save writing evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to save writing evaluation")

@router.post("/evaluation/self-save", response_model=StandardResponse)
async def save_self_evaluation(payload: WritingSelfEvaluationRequest):
    """
    Save self-evaluation for writing assessment.

    Accepts scores from user (0-100 for each category):
    - Grammar
    - Vocabulary
    - Coherence
    - Style
    - Clarity
    - Engagement

    Overall score is computed automatically as weighted average.
    """
    try:
        # Validate user_id is a valid UUID
        try:
            user_uuid = uuid.UUID(payload.user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="user_id must be a valid UUID string")

        evaluation_id = payload.evaluation_id or str(uuid.uuid4())
        created_at = payload.created_at or datetime.now(timezone.utc).isoformat()

        # Convert SelfEvaluationScores to dict and normalize
        scores_dict = {
            "grammar": payload.scores.grammar,
            "vocabulary": payload.scores.vocabulary,
            "coherence": payload.scores.coherence,
            "style": payload.scores.style,
            "clarity": payload.scores.clarity,
            "engagement": payload.scores.engagement
        }

        # Calculate weighted average for overall score
        # Equal weights for all categories
        weights = {
            "grammar": 0.20,
            "vocabulary": 0.15,
            "coherence": 0.20,
            "style": 0.15,
            "clarity": 0.15,
            "engagement": 0.15
        }

        overall_score = sum(scores_dict[key] * weights[key] for key in scores_dict.keys())
        overall_score = int(round(overall_score))

        # Stationary/constant fields
        original_text = ""  # Empty or could be user-provided in future
        language = "english"
        writing_type = "self_evaluation"
        improved_version = ""
        strengths = []
        improvements = []
        suggestions = []
        feedback_summary = ""

        record = {
            "id": evaluation_id,
            "user_id": str(user_uuid),
            "original_text": original_text,
            "language": language,
            "writing_type": writing_type,
            "user_level": payload.user_level,
            "scores": scores_dict,
            "improved_version": improved_version,
            "overall_score": overall_score,
            "strengths": strengths,
            "improvements": improvements,
            "suggestions": suggestions,
            "feedback_summary": feedback_summary,
            "created_at": created_at
        }

        supabase = get_supabase_client()
        supabase.table("writing_evaluations").insert(record).execute()

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

@router.get("/tasks/daily", response_model=DailyWritingTasksResponse)
async def get_daily_writing_tasks(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty level"),
    writing_type: Optional[str] = Query(None, description="Filter by writing type"),
    limit: int = Query(5, ge=1, le=20, description="Number of tasks to return")
):
    """
    Get writing tasks/questions for a specific day.

    Returns a curated list of writing tasks for the specified date.
    Tasks can be filtered by difficulty level and writing type.
    """
    try:
        # Default to today if no date provided
        if not date:
            date = datetime.now(timezone.utc).date().isoformat()
        else:
            # Validate date format
            try:
                datetime.fromisoformat(date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Generate tasks based on date (using date as seed for consistency)
        import hashlib
        date_seed = int(hashlib.md5(date.encode()).hexdigest(), 16) % 1000

        # Sample task templates
        task_templates = [
            {
                "title": "Describe Your Ideal Vacation",
                "description": "Write a descriptive essay about your ideal vacation destination. Include details about the location, activities, and why this place appeals to you.",
                "writing_type": "essay",
                "difficulty_level": "beginner",
                "word_count_min": 150,
                "word_count_max": 300,
                "time_limit_minutes": 20,
                "tags": ["descriptive", "personal", "travel"]
            },
            {
                "title": "Formal Email to a Professor",
                "description": "Write a formal email to your professor requesting an extension for an assignment. Explain your situation professionally and provide valid reasons.",
                "writing_type": "email",
                "difficulty_level": "intermediate",
                "word_count_min": 100,
                "word_count_max": 200,
                "time_limit_minutes": 15,
                "tags": ["formal", "professional", "request"]
            },
            {
                "title": "Climate Change Opinion Essay",
                "description": "Write an opinion essay discussing the most effective solutions to climate change. Support your arguments with logical reasoning and examples.",
                "writing_type": "essay",
                "difficulty_level": "advanced",
                "word_count_min": 300,
                "word_count_max": 500,
                "time_limit_minutes": 30,
                "tags": ["opinion", "argumentative", "environment"]
            },
            {
                "title": "Creative Story Opening",
                "description": "Write the opening paragraph of a short story. Create an engaging hook that introduces a character and setting while building intrigue.",
                "writing_type": "story",
                "difficulty_level": "intermediate",
                "word_count_min": 100,
                "word_count_max": 250,
                "time_limit_minutes": 15,
                "tags": ["creative", "narrative", "fiction"]
            },
            {
                "title": "Product Review",
                "description": "Write a review of a product you recently purchased. Describe its features, pros and cons, and whether you would recommend it to others.",
                "writing_type": "review",
                "difficulty_level": "beginner",
                "word_count_min": 150,
                "word_count_max": 300,
                "time_limit_minutes": 20,
                "tags": ["review", "descriptive", "evaluation"]
            },
            {
                "title": "Job Application Cover Letter",
                "description": "Write a cover letter for a job application in your field of interest. Highlight your skills, experience, and why you're a good fit for the position.",
                "writing_type": "letter",
                "difficulty_level": "advanced",
                "word_count_min": 250,
                "word_count_max": 400,
                "time_limit_minutes": 25,
                "tags": ["formal", "professional", "persuasive"]
            },
            {
                "title": "Technology Impact Analysis",
                "description": "Analyze how social media has impacted modern communication. Discuss both positive and negative aspects with specific examples.",
                "writing_type": "essay",
                "difficulty_level": "advanced",
                "word_count_min": 300,
                "word_count_max": 500,
                "time_limit_minutes": 30,
                "tags": ["analytical", "technology", "society"]
            },
            {
                "title": "Complaint Letter to Service Provider",
                "description": "Write a complaint letter to a service provider about a recent negative experience. Be firm but professional in expressing your concerns.",
                "writing_type": "letter",
                "difficulty_level": "intermediate",
                "word_count_min": 150,
                "word_count_max": 300,
                "time_limit_minutes": 20,
                "tags": ["formal", "complaint", "professional"]
            }
        ]

        # Filter tasks
        filtered_tasks = task_templates
        if difficulty_level:
            filtered_tasks = [t for t in filtered_tasks if t["difficulty_level"] == difficulty_level]
        if writing_type:
            filtered_tasks = [t for t in filtered_tasks if t["writing_type"] == writing_type]

        # Select tasks based on date seed and limit
        import random
        random.seed(date_seed)
        selected_tasks = random.sample(filtered_tasks, min(limit, len(filtered_tasks)))

        # Create task objects with unique IDs
        tasks = []
        for idx, template in enumerate(selected_tasks):
            task = WritingTask(
                task_id=f"{date}-task-{idx+1}",
                **template
            )
            tasks.append(task)

        return DailyWritingTasksResponse(
            date=date,
            tasks=tasks,
            total_count=len(tasks)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get daily writing tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve daily writing tasks")

@router.post("/tasks/submit", response_model=WritingTaskEvaluationResponse)
async def submit_writing_task(
    request: SubmitWritingTaskRequest,
    background_tasks: BackgroundTasks,
    writing_service = Depends(get_writing_evaluation_service)
):
    """
    Submit and evaluate a writing task response.

    Evaluates the submitted writing task and returns detailed feedback including
    scores, improvements, and whether the submission meets task requirements.
    """
    try:
        # Evaluate the writing
        evaluation = await writing_service.evaluate_writing(
            text=request.text,
            language=request.language,
            writing_type="general",
            user_level=request.user_level
        )

        # Generate unique evaluation ID
        evaluation_id = str(uuid.uuid4())

        # Calculate word count
        word_count = len(request.text.split())

        # Check if meets basic requirements (placeholder - could be enhanced)
        meets_requirements = word_count >= 50  # Basic requirement

        # Save to database if requested
        if request.save_evaluation and request.user_id:
            evaluation_data = {
                "id": evaluation_id,
                "user_id": request.user_id,
                "original_text": request.text,
                "language": request.language,
                "writing_type": f"task_{request.task_id}",
                "user_level": request.user_level,
                "scores": evaluation.scores,
                "improved_version": evaluation.improved_version,
                "overall_score": evaluation.overall_score,
                "strengths": evaluation.strengths or [],
                "improvements": evaluation.improvements or [],
                "suggestions": evaluation.suggestions or [],
                "feedback_summary": evaluation.feedback_summary or "",
                "created_at": datetime.now().isoformat()
            }

            # Background task to save to database
            background_tasks.add_task(_save_evaluation_to_db, evaluation_data)

        return WritingTaskEvaluationResponse(
            task_id=request.task_id,
            evaluation_id=evaluation_id,
            overall_score=evaluation.overall_score,
            scores=evaluation.scores,
            improved_version=evaluation.improved_version,
            feedback_summary=evaluation.feedback_summary or "Good work! Keep practicing.",
            strengths=evaluation.strengths or ["Clear expression"],
            improvements=evaluation.improvements or ["Continue practicing"],
            word_count=word_count,
            meets_requirements=meets_requirements
        )

    except Exception as e:
        logger.error(f"Writing task evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

# Helper function for background task
async def _save_evaluation_to_db(evaluation_data: Dict[str, Any]):
    """Background task to save evaluation to database"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("writing_evaluations").insert(evaluation_data).execute()
        logger.info(f"Saved evaluation {evaluation_data['id']} to database")
    except Exception as e:
        logger.error(f"Failed to save evaluation to database: {e}")




#   # End of file
