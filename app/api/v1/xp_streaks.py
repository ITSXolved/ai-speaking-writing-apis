"""
XP and Streak Management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
from typing import Optional
import logging

from app.models.xp_streaks import (
    XPSummary,
    StreakInfo,
    DailyProgress,
    StreakCalendar,
    LevelInfo,
    DailyXPResponse
)
from app.services.analytics_service import AnalyticsService
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/users/{user_id}/xp",
    response_model=XPSummary
)
async def get_user_xp(
    user_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's XP summary

    Returns:
    - Total XP earned
    - Today's XP
    - Current level and progress to next level
    """
    try:
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's XP"
            )

        analytics = AnalyticsService()

        # Get XP totals
        xp_data = await analytics.get_user_xp(user_id)

        # Calculate level
        level_info = analytics.calculate_level(xp_data['total'])

        return XPSummary(
            user_id=user_id,
            total_xp=xp_data['total'],
            today_xp=xp_data['today'],
            current_level=level_info['current_level'],
            xp_to_next_level=level_info['xp_to_next_level'],
            level_progress_pct=level_info['progress_pct']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user XP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}/xp/daily",
    response_model=DailyXPResponse
)
async def get_daily_xp(
    user_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get detailed XP breakdown for today

    Returns:
    - Total XP earned today
    - Goal progress
    - Breakdown by source (sessions, bonuses, badges)
    """
    try:
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's XP"
            )

        analytics = AnalyticsService()
        from datetime import date

        today = date.today()

        # Get today's XP transactions
        xp_ledger = analytics.db('xp_ledger').select('*').eq(
            'user_id', str(user_id)
        ).gte(
            'occurred_at', f"{today}T00:00:00Z"
        ).execute()

        breakdown = xp_ledger.data or []
        total_today = sum(x['amount'] for x in breakdown)

        xp_goal = 100  # Default daily goal
        goal_pct = min(int((total_today / xp_goal) * 100), 100)

        return DailyXPResponse(
            user_id=user_id,
            date=today,
            xp_earned_today=total_today,
            xp_goal=xp_goal,
            goal_completion_pct=goal_pct,
            sessions_today=len([x for x in breakdown if 'session' in x['source']]),
            breakdown=breakdown
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily XP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}/level",
    response_model=LevelInfo
)
async def get_user_level(
    user_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's level information

    Returns:
    - Current level and level name
    - XP progress within current level
    - XP required for next level
    """
    try:
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's level"
            )

        analytics = AnalyticsService()
        xp_data = await analytics.get_user_xp(user_id)
        level_info = analytics.calculate_level(xp_data['total'])

        return LevelInfo(**level_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user level: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}/streak",
    response_model=StreakInfo
)
async def get_user_streak(
    user_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's streak information

    Returns:
    - Current streak
    - Longest streak
    - Last active date
    - Streak status (active, at_risk, broken)
    """
    try:
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's streak"
            )

        analytics = AnalyticsService()
        from datetime import date

        # Get streak data
        streak_result = analytics.db('streaks').select('*').eq(
            'user_id', str(user_id)
        ).execute()

        if not streak_result.data:
            # No streak yet
            return StreakInfo(
                user_id=user_id,
                current_streak=0,
                longest_streak=0,
                last_active_date=date.today(),
                is_active_today=False,
                streak_status="broken"
            )

        streak = streak_result.data[0]
        from datetime import datetime

        last_active = datetime.fromisoformat(streak['last_active_date']).date()
        today = date.today()

        is_active_today = last_active == today
        days_since_active = (today - last_active).days

        if days_since_active == 0:
            status = "active"
        elif days_since_active == 1:
            status = "at_risk"
        else:
            status = "broken"

        return StreakInfo(
            user_id=user_id,
            current_streak=streak['current_streak'],
            longest_streak=streak['longest_streak'],
            last_active_date=last_active,
            is_active_today=is_active_today,
            streak_status=status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user streak: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}/daily-progress",
    response_model=DailyProgress
)
async def get_daily_progress(
    user_id: UUID,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's daily progress

    Returns:
    - XP earned today
    - Sessions completed
    - Goals progress
    - Time spent
    - Perfect day status
    """
    try:
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's progress"
            )

        analytics = AnalyticsService()
        progress = await analytics.get_daily_progress(user_id)

        return DailyProgress(**progress)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}/streak-calendar",
    response_model=StreakCalendar
)
async def get_streak_calendar(
    user_id: UUID,
    month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's streak calendar for a month

    Query Parameters:
    - month: Optional month in format YYYY-MM (default: current month)

    Returns:
    - Calendar view with daily activity
    - Sessions and XP per day
    - Current streak
    - Perfect days count
    """
    try:
        if str(user_id) != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view another user's calendar"
            )

        analytics = AnalyticsService()
        calendar_data = await analytics.get_streak_calendar(user_id, month)

        return StreakCalendar(**calendar_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting streak calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))
