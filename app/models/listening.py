"""
Pydantic models for listening evaluation and recording
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict
from datetime import datetime, timezone
from uuid import UUID


# ==================== LISTENING SESSION START ====================

class ListeningSessionStart(BaseModel):
    """Start a new listening test session"""
    user_id: UUID
    day_code: str = Field(..., pattern=r"^day\d+$")
    audio_url: Optional[str] = Field(None, description="URL to the listening audio file")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ListeningSessionStartResponse(BaseModel):
    """Response when listening session is created"""
    session_id: UUID
    user_id: UUID
    modality: str = "listening"
    day_code: str
    audio_url: Optional[str]
    started_at: datetime
    message: str = "Listening session started successfully"


# ==================== LISTENING ANSWER SUBMISSION ====================

class ListeningAnswerSubmission(BaseModel):
    """Individual listening answer in a session"""
    item_id: str = Field(..., description="Question ID")
    question_type: Literal[
        "multiple_choice",
        "fill_blank",
        "true_false",
        "short_answer",
        "matching"
    ] = Field(..., description="Type of listening question")
    user_answer: Optional[str] = Field(None, description="User's answer")
    correct_answer: str = Field(..., description="Correct answer for verification")
    is_correct: bool
    time_spent_sec: int = Field(..., ge=0, description="Time spent on this question")
    skill: Literal[
        "vocabulary",
        "main_idea",
        "details",
        "inference",
        "speaker_purpose",
        "tone",
        "organization",
        "connecting_ideas"
    ] = Field(..., description="Specific listening skill being evaluated")
    audio_timestamp_start: Optional[int] = Field(
        None,
        description="Start timestamp in audio (seconds) relevant to this question"
    )
    audio_timestamp_end: Optional[int] = Field(
        None,
        description="End timestamp in audio (seconds) relevant to this question"
    )
    topic: Optional[str] = Field(None, description="Audio passage topic/category")


class ListeningSessionSubmit(BaseModel):
    """Submit completed listening session with all answers"""
    answers: List[ListeningAnswerSubmission] = Field(..., min_items=1)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_sec: int = Field(..., ge=0, description="Total session duration")
    score_pct: int = Field(..., ge=0, le=100)
    xp_earned: int = Field(..., ge=0)
    audio_replay_count: Optional[int] = Field(
        0,
        ge=0,
        description="Number of times user replayed the audio"
    )
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
            if abs(calculated_score - score_pct) > 1:
                raise ValueError(
                    f"Score mismatch: calculated {calculated_score}%, provided {score_pct}%"
                )
        return score_pct


class ListeningSessionSubmitResponse(BaseModel):
    """Response after listening session submission"""
    session_id: UUID
    analytics_recorded: bool
    xp_awarded: int
    badges_awarded: List[Dict[str, str]]
    streak_updated: bool
    current_streak: int
    skill_mastery_recorded: bool
    message: str = "Listening session submitted successfully"


# ==================== LISTENING SESSION DETAILS ====================

class ListeningAnswerDetail(BaseModel):
    """Detailed listening answer information"""
    answer_id: UUID
    item_id: str
    question_type: str
    user_answer: Optional[str]
    correct_answer: str
    is_correct: bool
    time_spent_sec: int
    skill: str
    audio_timestamp_start: Optional[int]
    audio_timestamp_end: Optional[int]
    topic: Optional[str]


class ListeningSessionDetail(BaseModel):
    """Detailed listening session information"""
    session_id: UUID
    user_id: UUID
    modality: str = "listening"
    day_code: str
    audio_url: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_sec: Optional[int]
    score_pct: Optional[int]
    xp_earned: int
    audio_replay_count: int
    answers: List[ListeningAnswerDetail]


# ==================== LISTENING SKILL MASTERY ====================

class ListeningSkillScore(BaseModel):
    """Listening skill performance in a session"""
    skill: Literal[
        "vocabulary",
        "main_idea",
        "details",
        "inference",
        "speaker_purpose",
        "tone",
        "organization",
        "connecting_ideas"
    ]
    correct: int = Field(..., ge=0)
    total: int = Field(..., gt=0)
    mastery_pct: int = Field(..., ge=0, le=100)
    mastery_level: Literal["beginner", "developing", "proficient", "advanced"]


class ListeningSessionMasteryResponse(BaseModel):
    """Listening session mastery breakdown by skills"""
    session_id: UUID
    modality: str = "listening"
    day_code: str
    overall_score_pct: int
    duration_sec: int
    audio_replay_count: int
    skills: List[ListeningSkillScore]
    mastery_levels: Dict[str, int] = Field(
        ...,
        description="Count of skills at each mastery level"
    )


class ListeningSkillProgressDetail(BaseModel):
    """User progress in a specific listening skill"""
    skill: str
    sessions_practiced: int
    total_questions: int
    correct_answers: int
    overall_mastery_pct: int
    mastery_level: Literal["beginner", "developing", "proficient", "advanced"]
    trend: Literal["improving", "stable", "declining"]
    avg_time_per_question: float = Field(
        ...,
        description="Average time spent per question in seconds"
    )


class UserListeningProgressResponse(BaseModel):
    """User's listening skill progress across sessions"""
    modality: str = "listening"
    date_range: str
    overall_mastery_pct: int
    total_sessions: int
    total_audio_replay_count: int
    skills: List[ListeningSkillProgressDetail]


# ==================== LISTENING ANALYTICS ====================

class ListeningAnalytics(BaseModel):
    """Listening-specific analytics data"""
    user_id: UUID
    total_sessions: int
    avg_score_pct: float
    total_duration_sec: int
    total_audio_replays: int
    strongest_skill: str
    weakest_skill: str
    improvement_rate: float = Field(
        ...,
        description="Percentage improvement from first to latest session"
    )


class ListeningDayProgress(BaseModel):
    """Progress tracking for a specific day's listening content"""
    day_code: str
    is_completed: bool
    score_pct: Optional[int]
    mastery_level: Optional[str]
    attempts: int
    best_score_pct: int
    last_attempted_at: Optional[datetime]
