"""
Pydantic models for XP and Streak management
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, date
from uuid import UUID


# ==================== XP MODELS ====================

class XPAward(BaseModel):
    """XP award record"""
    user_id: UUID
    amount: int = Field(..., gt=0)
    source: str = Field(..., description="Source of XP: session, badge, daily_bonus, streak_bonus")
    occurred_at: datetime


class XPSummary(BaseModel):
    """User XP summary"""
    user_id: UUID
    total_xp: int
    today_xp: int
    current_level: int
    xp_to_next_level: int
    level_progress_pct: int


class XPLeaderboardEntry(BaseModel):
    """Leaderboard entry"""
    rank: int
    user_id: UUID
    username: Optional[str] = None
    total_xp: int
    current_level: int
    current_streak: int


class XPLeaderboardResponse(BaseModel):
    """Leaderboard response"""
    period: str = Field(..., description="daily, weekly, all_time")
    entries: List[XPLeaderboardEntry]
    user_rank: Optional[int] = None


# ==================== STREAK MODELS ====================

class StreakInfo(BaseModel):
    """User streak information"""
    user_id: UUID
    current_streak: int
    longest_streak: int
    last_active_date: date
    is_active_today: bool
    streak_status: str = Field(
        ...,
        description="active, at_risk (no activity today), broken"
    )


class StreakHistoryEntry(BaseModel):
    """Daily streak activity entry"""
    date: date
    sessions_completed: int
    modalities_completed: List[str]
    total_xp_earned: int
    streak_day: int


class StreakCalendar(BaseModel):
    """Calendar view of streak activity"""
    user_id: UUID
    current_month: str
    days: List[StreakHistoryEntry]
    current_streak: int
    perfect_days: int = Field(..., description="Days with all 3 modalities")


# ==================== DAILY PROGRESS ====================

class DailyGoal(BaseModel):
    """Daily learning goal"""
    goal_type: str = Field(..., description="xp, sessions, time_minutes")
    target: int
    current: int
    is_completed: bool


class DailyProgress(BaseModel):
    """User's progress for today"""
    user_id: UUID
    date: date
    xp_earned: int
    xp_goal: int = Field(default=100)
    sessions_completed: int
    session_goal: int = Field(default=3)
    time_spent_minutes: int
    modalities_completed: List[str]
    goals: List[DailyGoal]
    is_perfect_day: bool = Field(
        ...,
        description="True if all 3 modalities completed"
    )


# ==================== XP CALCULATION ====================

class XPCalculation(BaseModel):
    """Detailed XP calculation breakdown"""
    base_xp: int = Field(..., description="Base XP for session completion")
    accuracy_bonus: int = Field(default=0, description="Bonus for high accuracy")
    speed_bonus: int = Field(default=0, description="Bonus for quick completion")
    streak_bonus: int = Field(default=0, description="Bonus for active streak")
    perfect_score_bonus: int = Field(default=0, description="100% accuracy bonus")
    first_of_day_bonus: int = Field(default=0, description="First session of the day")
    modality_completion_bonus: int = Field(default=0, description="All 3 modalities today")
    total_xp: int


class XPBonus(BaseModel):
    """XP bonus configuration"""
    name: str
    description: str
    xp_amount: int
    condition: str


# ==================== REWARDS & ACHIEVEMENTS ====================

class MilestoneReward(BaseModel):
    """Milestone achievement reward"""
    milestone_key: str
    title: str
    description: str
    xp_reward: int
    achieved_at: Optional[datetime] = None
    is_achieved: bool


class UserMilestones(BaseModel):
    """User's milestone progress"""
    user_id: UUID
    milestones: List[MilestoneReward]
    total_achieved: int
    total_available: int


# ==================== LEVEL SYSTEM ====================

class LevelInfo(BaseModel):
    """User level information"""
    current_level: int
    level_name: str = Field(..., description="Beginner, Intermediate, Advanced, Expert, Master")
    total_xp: int
    xp_for_current_level: int
    xp_for_next_level: int
    xp_to_next_level: int
    progress_pct: int


class LevelUpResponse(BaseModel):
    """Level up notification"""
    new_level: int
    level_name: str
    xp_earned: int
    bonus_awarded: int
    message: str = "Congratulations on leveling up!"


# ==================== STATISTICS ====================

class UserStats(BaseModel):
    """Comprehensive user statistics"""
    user_id: UUID
    total_xp: int
    current_level: int
    current_streak: int
    longest_streak: int
    total_sessions: int
    total_time_minutes: int
    average_score_pct: float
    favorite_modality: Optional[str] = None
    total_badges: int
    perfect_days: int
    join_date: date
    days_active: int


# ==================== API RESPONSES ====================

class DailyXPResponse(BaseModel):
    """Daily XP summary response"""
    user_id: UUID
    date: date
    xp_earned_today: int
    xp_goal: int
    goal_completion_pct: int
    sessions_today: int
    breakdown: List[XPAward]


class StreakUpdateResponse(BaseModel):
    """Streak update response"""
    current_streak: int
    longest_streak: int
    is_new_record: bool
    streak_bonus_xp: int
    message: str
