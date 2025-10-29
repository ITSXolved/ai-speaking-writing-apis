"""
Unified models for combining LRG, Writing, and Speaking activities
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from uuid import UUID


# ==================== UNIFIED USER ACTIVITY ====================

class UnifiedUserStats(BaseModel):
    """Combined statistics across all learning activities"""
    user_id: UUID
    display_name: Optional[str]
    email: Optional[str]
    skill_level: Optional[str]
    target_language: Optional[str]
    
    # LRG stats
    lrg_sessions: int = 0
    lrg_time_sec: int = 0
    lrg_avg_score: Optional[float] = None
    
    # Writing stats
    writing_evaluations: int = 0
    writing_avg_score: Optional[float] = None
    
    # Speaking stats
    speaking_sessions: int = 0
    
    # Gamification
    current_streak: int = 0
    longest_streak: int = 0
    total_xp: int = 0
    
    # Last activity
    last_activity: Optional[datetime] = None


class UnifiedDailyActivity(BaseModel):
    """Daily activity across all modalities"""
    user_id: UUID
    activity_date: date
    
    # LRG activities
    reading_done: bool = False
    listening_done: bool = False
    grammar_done: bool = False
    
    # Other activities
    writing_done: bool = False
    speaking_done: bool = False
    
    # Time metrics
    total_time_sec: int = 0
    
    @property
    def activities_completed(self) -> int:
        """Count of completed activities"""
        return sum([
            self.reading_done,
            self.listening_done,
            self.grammar_done,
            self.writing_done,
            self.speaking_done
        ])
    
    @property
    def is_perfect_day(self) -> bool:
        """Check if all LRG activities completed"""
        return all([
            self.reading_done,
            self.listening_done,
            self.grammar_done
        ])


# ==================== UNIFIED DASHBOARD ====================

class UnifiedDashboardSummary(BaseModel):
    """Complete dashboard combining all learning activities"""
    user_id: UUID
    as_of: datetime
    
    # Overall stats
    total_activities: int
    total_time_minutes: int
    current_streak: int
    total_xp: int
    
    # Activity breakdown
    lrg_stats: Dict[str, Any]  # From LRG sessions
    writing_stats: Dict[str, Any]  # From writing evaluations
    speaking_stats: Dict[str, Any]  # From speaking sessions
    
    # Recent activity (last 7 days)
    recent_activities: List[UnifiedDailyActivity]
    
    # Badges and achievements
    badges: List[Dict[str, Any]]
    next_milestone: Dict[str, Any]


class ActivityTimelineItem(BaseModel):
    """Single item in activity timeline"""
    timestamp: datetime
    activity_type: str  # 'reading', 'listening', 'grammar', 'writing', 'speaking'
    title: str
    score: Optional[int] = None
    duration_sec: Optional[int] = None
    details: Dict[str, Any] = {}


class UnifiedTimeline(BaseModel):
    """User's complete activity timeline"""
    user_id: UUID
    items: List[ActivityTimelineItem]
    total_count: int
    page: int = 1
    page_size: int = 20


# ==================== INTEGRATION MODELS ====================

class WritingEvaluationSummary(BaseModel):
    """Summary of writing evaluation from existing table"""
    id: UUID
    user_id: str
    overall_score: int
    feedback_summary: str
    created_at: datetime
    
    # Key metrics from scores JSONB
    grammar_score: Optional[int] = None
    vocabulary_score: Optional[int] = None
    coherence_score: Optional[int] = None


class SpeakingSessionSummary(BaseModel):
    """Summary of speaking session from existing table"""
    id: UUID
    user_id: UUID
    mode_code: Optional[str]
    language_code: Optional[str]
    started_at: datetime
    closed_at: Optional[datetime]
    duration_sec: Optional[int]
    
    # Evaluation metrics if available
    evaluation_score: Optional[float] = None


class ConceptMasteryStatus(BaseModel):
    """Status of concept mastery from existing table"""
    concept_id: UUID
    concept_name: str
    mastery_score: float = Field(..., ge=0, le=1)
    practice_count: int = 0
    last_practiced: Optional[datetime] = None


# ==================== XP AND REWARDS ====================

class XPTransaction(BaseModel):
    """XP transaction record"""
    xp_id: UUID
    user_id: UUID
    source: str  # 'lrg_session', 'writing', 'speaking', 'badge', etc.
    amount: int
    occurred_at: datetime
    description: Optional[str] = None


class XPSummary(BaseModel):
    """XP breakdown by source"""
    user_id: UUID
    total_xp: int
    
    # Breakdown by source
    lrg_xp: int = 0
    writing_xp: int = 0
    speaking_xp: int = 0
    badge_xp: int = 0
    other_xp: int = 0
    
    # Recent transactions
    recent_transactions: List[XPTransaction] = []


class StreakInfo(BaseModel):
    """Streak information"""
    user_id: UUID
    current_streak: int
    longest_streak: int
    last_active_date: Optional[date]
    
    # Prediction
    streak_at_risk: bool = False  # True if no activity today
    next_milestone: int  # Next streak badge milestone


# ==================== COMPREHENSIVE PROGRESS ====================

class ComprehensiveProgress(BaseModel):
    """Complete progress report across all activities"""
    user_id: UUID
    report_period: str  # 'weekly', 'monthly', 'all_time'
    
    # Time metrics
    total_time_minutes: int
    avg_session_minutes: float
    
    # Activity counts
    total_lrg_sessions: int
    total_writing_submissions: int
    total_speaking_sessions: int
    
    # Performance metrics
    lrg_avg_accuracy: Optional[float]
    writing_avg_score: Optional[float]
    speaking_evaluation_avg: Optional[float]
    
    # Engagement
    active_days: int
    current_streak: int
    consistency_score: float  # 0-100
    
    # Achievements
    total_xp: int
    badges_earned: int
    concepts_mastered: int
    
    # Improvement trends
    improvements: List[str] = []
    areas_for_focus: List[str] = []


# ==================== ANALYTICS AGGREGATIONS ====================

class WeeklyComparison(BaseModel):
    """Week-over-week comparison"""
    current_week: Dict[str, Any]
    previous_week: Dict[str, Any]
    changes: Dict[str, float]  # Percentage changes


class MonthlyReport(BaseModel):
    """Monthly progress report"""
    user_id: UUID
    month: str  # 'YYYY-MM'
    
    # Activity summary
    total_activities: int
    total_time_hours: float
    days_active: int
    
    # Performance
    overall_performance: float  # 0-100
    best_activity: str
    most_improved: str
    
    # Detailed breakdown
    lrg_breakdown: Dict[str, Any]
    writing_breakdown: Dict[str, Any]
    speaking_breakdown: Dict[str, Any]
    
    # Goals
    goals_completed: List[str]
    next_month_goals: List[str]