"""
Pydantic models for sessions and submissions
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict
from datetime import datetime, timezone
from uuid import UUID


# ==================== SESSION START ====================

class SessionStart(BaseModel):
    """Start a new test session"""
    user_id: UUID
    modality: Literal["listening", "reading", "grammar"]
    day_code: str = Field(..., pattern=r"^day\d+$")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionStartResponse(BaseModel):
    """Response when session is created"""
    session_id: UUID
    user_id: UUID
    modality: str
    day_code: str
    started_at: datetime
    message: str = "Session started successfully"


# ==================== SESSION SUBMIT ====================

class AnswerSubmission(BaseModel):
    """Individual answer in a session"""
    item_id: str = Field(..., description="Question/task ID")
    user_answer: Optional[str] = Field(None, description="User's answer")
    correct_answer: str = Field(..., description="Correct answer for verification")
    is_correct: bool
    time_spent_sec: int = Field(..., ge=0)
    topic: Optional[str] = Field(None, description="Topic/category for analytics")
    skill: str = Field(..., description="Specific skill being evaluated (e.g., vocabulary, comprehension, inference)")


class SessionSubmit(BaseModel):
    """Submit completed session with all answers"""
    answers: List[AnswerSubmission] = Field(..., min_items=1)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_sec: int = Field(..., ge=0)
    score_pct: int = Field(..., ge=0, le=100)
    xp_earned: int = Field(..., ge=0)
    skill_scores: Optional[Dict[str, Dict[str, int]]] = Field(
        None,
        description="Skill-level breakdown: {skill: {correct: n, total: m, mastery_pct: p}}"
    )
    
    @field_validator('score_pct')
    @classmethod
    def validate_score(cls, score_pct, info):
        answers = info.data.get('answers', [])
        if answers:
            correct = sum(1 for a in answers if a.is_correct)
            calculated_score = int((correct / len(answers)) * 100)
            if abs(calculated_score - score_pct) > 1:  # Allow 1% rounding tolerance
                raise ValueError(
                    f"Score mismatch: calculated {calculated_score}%, provided {score_pct}%"
                )
        return score_pct


class BadgeAwarded(BaseModel):
    """Badge information"""
    badge_key: str
    title: str
    earned_at: datetime


class SessionSubmitResponse(BaseModel):
    """Response after session submission"""
    session_id: UUID
    analytics_recorded: bool
    xp_awarded: int
    badges_awarded: List[BadgeAwarded]
    streak_updated: bool
    current_streak: int
    message: str = "Session submitted successfully"


# ==================== SESSION RETRIEVAL ====================

class AnswerDetail(BaseModel):
    """Detailed answer information"""
    answer_id: UUID
    item_id: str
    user_answer: Optional[str]
    correct_answer: str
    is_correct: bool
    time_spent_sec: int
    topic: Optional[str]


class SessionDetail(BaseModel):
    """Detailed session information"""
    session_id: UUID
    user_id: UUID
    modality: str
    day_code: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_sec: Optional[int]
    score_pct: Optional[int]
    xp_earned: int
    answers: List[AnswerDetail]


class SessionSummary(BaseModel):
    """Session summary for lists"""
    session_id: UUID
    day_code: str
    modality: str
    score_pct: Optional[int]
    duration_sec: Optional[int]
    completed_at: Optional[datetime]
    xp_earned: int


# ==================== SKILL MASTERY ====================

class SkillScore(BaseModel):
    """Skill performance in a session"""
    skill: str
    correct: int = Field(..., ge=0)
    total: int = Field(..., gt=0)
    mastery_pct: int = Field(..., ge=0, le=100)
    mastery_level: Literal["beginner", "developing", "proficient", "advanced"]


class SessionMasteryResponse(BaseModel):
    """Session mastery breakdown by skills"""
    session_id: UUID
    modality: str
    day_code: str
    overall_score_pct: int
    duration_sec: int
    skills: List[SkillScore]
    mastery_levels: Dict[str, int] = Field(
        ...,
        description="Count of skills at each mastery level"
    )


class SkillProgressDetail(BaseModel):
    """User progress in a specific skill"""
    skill: str
    sessions_practiced: int
    total_questions: int
    correct_answers: int
    overall_mastery_pct: int
    mastery_level: Literal["beginner", "developing", "proficient", "advanced"]
    trend: Literal["improving", "stable", "declining"]
    avg_time_per_question: Optional[float] = Field(None, description="Average time per question in seconds")


class UserSkillProgressResponse(BaseModel):
    """User's skill progress across sessions"""
    modality: str
    date_range: str
    skills: List[SkillProgressDetail]


class MasteryOverview(BaseModel):
    """Overall mastery across all modalities"""
    overall_mastery_pct: int
    skills: Dict[str, int] = Field(
        ...,
        description="Mastery percentage per skill"
    )


class UserMasteryOverviewResponse(BaseModel):
    """Complete mastery overview for a user"""
    user_id: UUID
    listening: MasteryOverview
    reading: MasteryOverview
    grammar: MasteryOverview