"""
Pydantic schemas for API request and response models
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator

from app.domain.models import SessionStatus, ConversationRole


# Teaching Modes Schemas

class TeachingModeCreate(BaseModel):
    """Schema for creating a teaching mode"""
    code: str = Field(..., min_length=1, max_length=50, description="Unique mode code")
    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    description: Optional[str] = Field(None, max_length=1000, description="Mode description")
    rubric: Dict[str, Any] = Field(default_factory=dict, description="Scoring rubric configuration")

class TeachingModeUpdate(BaseModel):
    """Schema for updating a teaching mode"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Display name")
    description: Optional[str] = Field(None, max_length=1000, description="Mode description")
    rubric: Optional[Dict[str, Any]] = Field(None, description="Scoring rubric configuration")

class TeachingModeResponse(BaseModel):
    """Schema for teaching mode response"""
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    rubric: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Scenarios Schemas

class ScenarioCreate(BaseModel):
    """Schema for creating a scenario"""
    mode_code: str = Field(..., min_length=1, max_length=50, description="Teaching mode code")
    title: str = Field(..., min_length=1, max_length=200, description="Scenario title")
    prompt: str = Field(..., min_length=1, description="Scenario prompt text")
    language_code: str = Field(..., min_length=1, max_length=10, description="Target language code")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ScenarioUpdate(BaseModel):
    """Schema for updating a scenario"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Scenario title")
    prompt: Optional[str] = Field(None, min_length=1, description="Scenario prompt text")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class ScenarioResponse(BaseModel):
    """Schema for scenario response"""
    id: UUID
    mode_code: str
    title: str
    prompt: str
    language_code: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Languages Schemas

class LanguageCreate(BaseModel):
    """Schema for creating a supported language"""
    code: str = Field(..., min_length=1, max_length=10, description="Language code (e.g., en-US)")
    label: str = Field(..., min_length=1, max_length=100, description="Display label")
    level_cefr: Optional[str] = Field(None, max_length=5, description="CEFR level (A1-C2)")

class LanguageUpdate(BaseModel):
    """Schema for updating a supported language"""
    label: Optional[str] = Field(None, min_length=1, max_length=100, description="Display label")
    level_cefr: Optional[str] = Field(None, max_length=5, description="CEFR level (A1-C2)")

class LanguageResponse(BaseModel):
    """Schema for language response"""
    code: str
    label: str
    level_cefr: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Sessions Schemas

class SessionCreateRequest(BaseModel):
    """Schema for session creation request"""
    user_external_id: str = Field(..., min_length=1, max_length=100, description="External user identifier")
    mode_code: str = Field(..., min_length=1, max_length=50, description="Teaching mode code")
    language_code: str = Field(..., min_length=1, max_length=10, description="Target language code")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")

class SessionResponse(BaseModel):
    """Schema for session response"""
    id: UUID
    user_id: UUID
    mode_code: str
    language_code: str
    started_at: datetime
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: SessionStatus

    class Config:
        from_attributes = True

class SessionCreateResponse(BaseModel):
    """Schema for session creation response"""
    session_id: UUID = Field(..., description="Created session ID")
    status: str = Field(default="created", description="Creation status")


# Conversations Schemas

class ConversationTurnRequest(BaseModel):
    """Schema for adding a conversation turn"""
    role: ConversationRole = Field(..., description="Speaker role (user or assistant)")
    text: str = Field(..., min_length=1, description="Turn text content")

    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')
        return v.strip()

class EvaluationResponse(BaseModel):
    """Schema for evaluation data in responses"""
    total_score: float = Field(..., ge=0, le=100, description="Total score (0-100)")
    metrics: Dict[str, Any] = Field(..., description="Individual metric scores")
    evaluation_id: int = Field(..., description="Evaluation record ID")

class ConversationTurnResponse(BaseModel):
    """Schema for conversation turn response"""
    conversation_id: int
    turn_index: int
    role: ConversationRole
    text: str
    created_at: Optional[datetime] = None
    evaluation: Optional[EvaluationResponse] = None

class ConversationHistoryResponse(BaseModel):
    """Schema for conversation history response"""
    conversations: List[ConversationTurnResponse]
    total_count: int
    page: int
    page_size: int


# Summaries Schemas

class SessionCloseResponse(BaseModel):
    """Schema for session close response"""
    session_id: UUID
    status: str = Field(default="closed")
    summary_json: Dict[str, Any] = Field(..., description="Generated session summary")

class SummaryResponse(BaseModel):
    """Schema for summary response"""
    id: UUID
    session_id: UUID
    user_id: UUID
    summary_json: Dict[str, Any]
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SummaryListResponse(BaseModel):
    """Schema for summary list response"""
    summaries: List[SummaryResponse]
    total_count: int
    page: int
    page_size: int


# Query Parameters

class PaginationParams(BaseModel):
    """Schema for pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database queries"""
        return self.page_size

class DateFilterParams(BaseModel):
    """Schema for date filtering parameters"""
    from_date: Optional[datetime] = Field(None, description="Start date (ISO format)")
    to_date: Optional[datetime] = Field(None, description="End date (ISO format)")

    @validator('to_date')
    def validate_date_range(cls, v, values):
        if v and 'from_date' in values and values['from_date']:
            if v < values['from_date']:
                raise ValueError('to_date must be after from_date')
        return v


# Error Schemas

class ErrorDetail(BaseModel):
    """Schema for error detail"""
    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")

# Health and Status Schemas

class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    services: Dict[str, str] = Field(default_factory=dict, description="Dependent service status")
    version: Optional[str] = Field(None, description="API version")

class StatusResponse(BaseModel):
    """Schema for status endpoint response"""
    service: str
    status: str
    version: str
    features: List[str]
    active_sessions: int
    supported_languages: int
    teaching_modes: int


# Statistics Schemas

class SessionStatistics(BaseModel):
    """Schema for session statistics"""
    total_turns: int
    average_score: float
    score_trend: str = Field(..., description="improving|declining|stable|insufficient_data")
    metric_averages: Dict[str, float]
    strengths: List[str]
    areas_for_improvement: List[str]
    score_distribution: Dict[str, int]

class UserProgressSummary(BaseModel):
    """Schema for user progress summary"""
    user_id: str
    total_evaluations: int
    recent_average: float
    progress_trend: str
    best_score: Optional[float] = None
    most_recent_score: Optional[float] = None


# Search and Filter Schemas

class ConversationSearchParams(BaseModel):
    """Schema for conversation search parameters"""
    user_external_id: Optional[str] = Field(None, max_length=100)
    session_id: Optional[UUID] = None
    text_search: Optional[str] = Field(None, min_length=1, max_length=200)
    role_filter: Optional[ConversationRole] = None

class TeachingModeFilter(BaseModel):
    """Schema for teaching mode filtering"""
    code: Optional[str] = Field(None, max_length=50)

class ScenarioFilter(BaseModel):
    """Schema for scenario filtering"""
    mode_code: Optional[str] = Field(None, max_length=50)
    language_code: Optional[str] = Field(None, max_length=10)

class SummaryFilter(BaseModel):
    """Schema for summary filtering"""
    user_external_id: Optional[str] = Field(None, max_length=100)


# Combined Request/Response Models

class TeachingModesListResponse(BaseModel):
    """Schema for teaching modes list response"""
    teaching_modes: List[TeachingModeResponse]
    total_count: int

class ScenariosListResponse(BaseModel):
    """Schema for scenarios list response"""
    scenarios: List[ScenarioResponse]
    total_count: int

class LanguagesListResponse(BaseModel):
    """Schema for languages list response"""
    languages: List[LanguageResponse]
    total_count: int

class SessionsListResponse(BaseModel):
    """Schema for sessions list response"""
    sessions: List[SessionResponse]
    total_count: int
    page: int
    page_size: int

    
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class EmailReportRequest(BaseModel):
    recipient_email: EmailStr
    user_name: str
    report_type: str = "weekly"
    session_id: Optional[str] = None
    include_detailed_stats: bool = True

class WritingFeedbackEmailRequest(BaseModel):
    recipient_email: EmailStr
    user_name: str
    evaluation_id: str

class WritingEvaluationRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    language: str = "english"
    writing_type: str = "general"
    user_level: str = "intermediate"
    user_id: Optional[str] = None
    save_evaluation: bool = True
# Add these to your app/api/schemas.py file

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

class SkillScores(BaseModel):
    """Skill scores model for session summaries"""
    pronunciation: int = Field(default=75, ge=0, le=100, description="Pronunciation score out of 100")
    grammar: int = Field(default=75, ge=0, le=100, description="Grammar score out of 100")
    vocabulary: int = Field(default=75, ge=0, le=100, description="New vocabulary learning score out of 100")
    comprehension: int = Field(default=75, ge=0, le=100, description="Level of understanding score out of 100")

class SummaryResponse(BaseModel):
    """Response model for session summaries with skill scores"""
    id: UUID
    session_id: UUID
    user_id: UUID
    title: str
    skill_scores: SkillScores
    summary_json: Dict[str, Any]
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, summary):
        """Convert SessionSummary ORM object to response"""
        summary_json = summary.summary_json
        
        # Extract skill scores from summary_json
        skill_scores_data = summary_json.get("skill_scores", {})
        skill_scores = SkillScores(
            pronunciation=skill_scores_data.get("pronunciation", 75),
            grammar=skill_scores_data.get("grammar", 75),
            vocabulary=skill_scores_data.get("vocabulary", 75),
            comprehension=skill_scores_data.get("comprehension", 75)
        )
        
        return cls(
            id=summary.id,
            session_id=summary.session_id,
            user_id=summary.user_id,
            title=summary_json.get("title", "Session Summary"),
            skill_scores=skill_scores,
            summary_json=summary_json,
            created_at=summary.created_at
        )

class SummaryListResponse(BaseModel):
    """Response model for paginated summaries list"""
    summaries: List[SummaryResponse]
    total_count: int
    page: int
    page_size: int

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    @property
    def limit(self) -> int:
        return self.page_size
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

class DateFilterParams(BaseModel):
    """Date filter parameters"""
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="High-level error summary")
    detail: Optional[str] = Field(None, description="Detailed error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Structured validation details")
    error_code: Optional[str] = Field(None, description="Application-specific error code")
    request_id: Optional[str] = Field(None, description="Request identifier for tracing")

# Update your domain models in app/domain/models.py

class SessionSummarySchema(BaseModel):
    """Schema for session summary JSON structure with skill scores"""
    title: str
    skill_scores: Dict[str, int] = Field(description="Skill scores as percentages out of 100")
    subtitle: Dict[str, Dict[str, Any]]
    
    class Config:
        extra = "allow"
        schema_extra = {
            "example": {
                "title": "Session ABC123 Study Notes — Spanish (Conversation)",
                "skill_scores": {
                    "pronunciation": 78,
                    "grammar": 85,
                    "vocabulary": 72,
                    "comprehension": 81
                },
                "subtitle": {
                    "0": {
                        "heading": "Key Phrases Practiced",
                        "points": {
                            "0": "Hello, how are you?",
                            "1": "I would like to order coffee"
                        }
                    },
                    "1": {
                        "heading": "Grammar & Corrections",
                        "points": {
                            "0": "Good progress with verb conjugations",
                            "1": "Continue practicing past tense forms"
                        }
                    },
                    "2": {
                        "heading": "Pronunciation / Fluency Tips",
                        "points": {
                            "0": "Practice rolling your 'rr' sounds",
                            "1": "Focus on clear vowel pronunciation"
                        }
                    },
                    "3": {
                        "heading": "Next Steps",
                        "points": {
                            "0": "Practice daily conversation for 10-15 minutes",
                            "1": "Continue practicing Spanish regularly"
                        }
                    }
                }
            }
        }

class SessionSummary(BaseModel):
    """Session summary domain model"""
    id: UUID
    session_id: UUID
    user_id: UUID
    summary_json: Dict[str, Any] = Field(description="Summary content including skill_scores")
    created_at: Optional[datetime] = None

    class Config:
        extra = "allow"


# CBT Evaluation Schemas

class CBTEvaluationRequest(BaseModel):
    """Request schema for CBT-based question evaluation"""
    question: str = Field(..., min_length=1, description="The question or prompt")
    options: Optional[List[str]] = Field(None, description="Answer options (for multiple choice)")
    answer: str = Field(..., min_length=1, description="The student's answer")
    skill_type: str = Field(..., description="Type of skill: speaking, writing, listening, reading, or grammar")
    user_id: Optional[str] = Field(None, description="Optional user ID for tracking")

    @validator('skill_type')
    def validate_skill_type(cls, v):
        allowed_skills = ['speaking', 'writing', 'listening', 'reading', 'grammar']
        if v.lower() not in allowed_skills:
            raise ValueError(f'skill_type must be one of: {", ".join(allowed_skills)}')
        return v.lower()


class CBTEvaluationResponse(BaseModel):
    """Response schema for CBT-based evaluation"""
    skill_type: str = Field(..., description="The evaluated skill type")
    evaluation: str = Field(..., description="Brief evaluation of the answer")
    cbt_suggestion: str = Field(..., description="Short CBT-based therapeutic suggestion")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence in evaluation (0-1)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now())

    class Config:
        schema_extra = {
            "example": {
                "skill_type": "speaking",
                "evaluation": "Your answer demonstrates good understanding but lacks fluency in connecting ideas.",
                "cbt_suggestion": "Remember, making mistakes is part of learning. Instead of thinking 'I'm bad at this,' try 'I'm improving with each practice.' Focus on small wins and be patient with yourself.",
                "confidence_score": 0.85,
                "timestamp": "2025-01-15T10:30:00"
            }
        }


# Competency and Progress Schemas

class SaveSpeakingEvaluationRequest(BaseModel):
    """Request schema for saving speaking evaluation with day_code"""
    user_id: UUID = Field(..., description="User UUID from auth.users")
    session_id: UUID = Field(..., description="Session UUID")
    day_code: str = Field(..., description="Day code (e.g., day1, day2)")
    language: str = Field(default="english", description="Language being practiced")
    user_level: str = Field(default="intermediate", description="User proficiency level")
    total_turns: int = Field(..., ge=1, description="Total conversation turns")
    scores: Dict[str, int] = Field(..., description="Score breakdown by category")
    strengths: List[str] = Field(default_factory=list, description="Identified strengths")
    improvements: List[str] = Field(default_factory=list, description="Areas for improvement")
    suggestions: List[str] = Field(default_factory=list, description="Practice suggestions")
    conversation_summary: str = Field(..., description="Summary of the conversation")
    overall_score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    feedback_summary: str = Field(..., description="Feedback summary")
    fluency_level: str = Field(..., description="Assessed fluency level")
    vocabulary_range: str = Field(..., description="Vocabulary range assessment")


class SaveWritingEvaluationRequest(BaseModel):
    """Request schema for saving writing evaluation with day_code"""
    user_id: str = Field(..., description="User ID (text field in writing_evaluations)")
    day_code: str = Field(..., description="Day code (e.g., day1, day2)")
    original_text: str = Field(..., description="Original text submitted")
    language: str = Field(default="english", description="Language")
    writing_type: str = Field(default="general", description="Type of writing")
    user_level: str = Field(default="intermediate", description="User level")
    scores: Dict[str, int] = Field(..., description="Score breakdown")
    strengths: List[str] = Field(default_factory=list, description="Strengths")
    improvements: List[str] = Field(default_factory=list, description="Improvements")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions")
    improved_version: str = Field(..., description="Improved version of text")
    overall_score: int = Field(..., ge=0, le=100, description="Overall score")
    feedback_summary: str = Field(..., description="Feedback summary")


class EvaluationSavedResponse(BaseModel):
    """Response after saving an evaluation"""
    success: bool = Field(..., description="Whether save was successful")
    evaluation_id: UUID = Field(..., description="ID of saved evaluation")
    day_code: str = Field(..., description="Day code")
    overall_score: int = Field(..., description="Overall score")
    message: str = Field(default="Evaluation saved successfully")


class UserDayProgress(BaseModel):
    """User progress for a specific day"""
    day_code: str = Field(..., description="Day code")
    speaking_completed: bool = Field(default=False, description="Speaking evaluation done")
    writing_completed: bool = Field(default=False, description="Writing evaluation done")
    speaking_score: Optional[int] = Field(None, description="Speaking score if completed")
    writing_score: Optional[int] = Field(None, description="Writing score if completed")
    speaking_evaluation_id: Optional[UUID] = Field(None, description="Speaking evaluation ID")
    writing_evaluation_id: Optional[UUID] = Field(None, description="Writing evaluation ID")
    completed_at: Optional[datetime] = Field(None, description="When last completed")


class UserCompetencyResponse(BaseModel):
    """Response with user competency across multiple days"""
    user_id: str = Field(..., description="User ID")
    total_days_available: int = Field(..., description="Total days with content")
    days_completed: int = Field(..., description="Days with both speaking and writing done")
    progress_by_day: List[UserDayProgress] = Field(..., description="Progress for each day")
    average_speaking_score: Optional[float] = Field(None, description="Average speaking score")
    average_writing_score: Optional[float] = Field(None, description="Average writing score")


class DayCompetencyStatsResponse(BaseModel):
    """Statistics for a specific day across all users"""
    day_code: str
    total_users_attempted: int
    speaking_completions: int
    writing_completions: int
    average_speaking_score: Optional[float]
    average_writing_score: Optional[float]
    top_performers: List[Dict[str, Any]] = Field(default_factory=list)
