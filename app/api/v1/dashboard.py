"""
Dashboard API endpoints for analytics and metrics
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
from typing import Literal
import logging

from app.services.dashboard_service import DashboardService
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    window: Literal["7d", "30d", "90d"] = Query(default="7d", description="Time window"),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get comprehensive dashboard summary
    Includes streak, XP, weekly activity, accuracy trends, and recent results
    
    Query Parameters:
    - window: Time window for analytics (7d, 30d, or 90d)
    """
    try:
        dashboard_service = DashboardService()
        result = await dashboard_service.get_summary(
            user_id=UUID(current_user_id),
            window=window
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/detail/{modality}")
async def get_modality_detail(
    modality: Literal["listening", "reading", "grammar"],
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get detailed analytics for a specific modality
    Includes accuracy trends, topic breakdown, and best performance
    
    Path Parameters:
    - modality: The learning modality (listening, reading, or grammar)
    """
    try:
        dashboard_service = DashboardService()
        result = await dashboard_service.get_modality_detail(
            user_id=UUID(current_user_id),
            modality=modality
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching modality detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/progress")
async def get_user_progress(
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get overall user progress metrics
    Includes total sessions, time, accuracy by modality, and engagement metrics
    """
    try:
        dashboard_service = DashboardService()
        
        # Get summary for full history
        summary = await dashboard_service.get_summary(
            user_id=UUID(current_user_id),
            window="365d"  # Full year
        )
        
        # Extract progress metrics
        return {
            'user_id': current_user_id,
            'total_xp': summary['xp']['total'],
            'current_streak': summary['streak_days'],
            'badges_earned': len(summary['badges']),
            'total_sessions': len(summary['recent_results']),
            'last_activity': summary['last_activity']
        }
        
    except Exception as e:
        logger.error(f"Error fetching user progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))