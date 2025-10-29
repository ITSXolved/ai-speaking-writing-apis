"""
Pydantic models for dashboard and analytics
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from uuid import UUID


# ==================== DASHBOARD SUMMARY ====================

class XPInfo(BaseModel):
    """XP information"""
    total: int
    today: int


class DailyTarget(BaseModel):
    """Daily target progress"""
    target: int = 3  # R, L, G
    completed: int


class WeeklyMinutes(BaseModel):
    """Minutes spent per day"""
    date: date
    listening_min: int = 0
    reading_min: int = 0
    grammar_min: int = 0
    
    @property
    def total_min(self) -> int:
        return self.listening_min + self.reading_min + self.grammar_min


class AccuracyPoint(BaseModel):
    """Accuracy data point"""
    date: date
    accuracy: float = Field(..., ge=0, le=1)


class ModalityAccuracyTrend(BaseModel):
    """Accuracy trend for all modalities"""
    listening: List[AccuracyPoint]
    reading: List[AccuracyPoint]
    grammar: List[AccuracyPoint]


class CompletionDay(BaseModel):
    """Completion status for a day"""
    date: date
    L: bool = False  # Listening completed
    R: bool = False  # Reading completed
    G: bool = False  # Grammar completed


class RecentResult(BaseModel):
    """Recent session result"""
    session_id: UUID
    day_code: str
    modality: str
    score_pct: int
    duration_sec: int
    completed_at: datetime


class Badge(BaseModel):
    """Badge information"""
    badge_key: str
    title: str
    description: Optional[str]
    earned_at: datetime


class NextReward(BaseModel):
    """Next reward progress"""
    type: str  # 'xp', 'badge', 'streak'
    target: int
    current: int
    
    @property
    def progress_pct(self) -> float:
        if self.target == 0:
            return 100.0
        return min((self.current / self.target) * 100, 100.0)


class DashboardSummary(BaseModel):
    """Main dashboard summary response"""
    user_id: UUID
    as_of: datetime
    
    # Header stats
    streak_days: int
    xp: XPInfo
    daily_target: DailyTarget
    last_activity: Optional[datetime]
    
    # Charts
    weekly_minutes: List[WeeklyMinutes]
    accuracy_trend: ModalityAccuracyTrend
    completion_heatmap: List[CompletionDay]
    
    # Recent & rewards
    recent_results: List[RecentResult]
    badges: List[Badge]
    next_reward: NextReward


# ==================== DASHBOARD DETAIL ====================

class TopicBreakdown(BaseModel):
    """Performance by topic"""
    topic: str
    accuracy: float = Field(..., ge=0, le=1)
    attempts: int


class ModalityDetail(BaseModel):
    """Detailed view for a specific modality"""
    modality: str
    
    # Performance over time
    accuracy_by_day: List[AccuracyPoint]
    minutes_by_day: List[Dict[str, Any]]  # [{date, minutes}]
    
    # Topic analysis
    question_breakdown: List[TopicBreakdown]
    
    # Highlights
    best_day: Optional[date]
    best_accuracy: float = 0.0
    total_time_minutes: int = 0
    total_questions: int = 0
    
    # Last session
    last_session: Optional[RecentResult]


# ==================== ANALYTICS ====================

class UserProgress(BaseModel):
    """Overall user progress metrics"""
    user_id: UUID
    total_sessions: int
    total_time_minutes: int
    total_questions_answered: int
    overall_accuracy: float
    
    # Per modality
    listening_accuracy: float = 0.0
    reading_accuracy: float = 0.0
    grammar_accuracy: float = 0.0
    
    # Engagement
    active_days: int
    current_streak: int
    longest_streak: int
    total_xp: int


class LeaderboardEntry(BaseModel):
    """Leaderboard entry"""
    rank: int
    user_id: UUID
    display_name: str
    total_xp: int
    current_streak: int
    accuracy: float


class WeeklyReport(BaseModel):
    """Weekly progress report"""
    user_id: UUID
    week_start: date
    week_end: date
    
    total_sessions: int
    total_minutes: int
    average_accuracy: float
    
    listening_sessions: int
    reading_sessions: int
    grammar_sessions: int
    
    xp_earned: int
    badges_earned: List[str]
    
    improvement_areas: List[str]
    strengths: List[str]