"""
Unified API endpoints for combined LRG, Writing, and Speaking data
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
from typing import Literal
import logging

from app.services.unified_service import UnifiedService
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/unified/stats")
async def get_unified_stats(
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get unified statistics across all learning activities
    Includes LRG, writing, and speaking data
    """
    try:
        unified_service = UnifiedService()
        result = await unified_service.get_unified_stats(UUID(current_user_id))
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching unified stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/dashboard")
async def get_unified_dashboard(
    days: int = Query(default=7, ge=1, le=365, description="Number of days to include"),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get comprehensive unified dashboard
    Combines LRG, writing, and speaking activities
    
    Query Parameters:
    - days: Number of days to include (default: 7)
    """
    try:
        unified_service = UnifiedService()
        result = await unified_service.get_unified_dashboard(
            user_id=UUID(current_user_id),
            days=days
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching unified dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/timeline")
async def get_activity_timeline(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get chronological timeline of all activities
    Shows LRG sessions, writing evaluations, and speaking sessions
    
    Query Parameters:
    - limit: Number of items per page (default: 20, max: 100)
    - offset: Pagination offset (default: 0)
    """
    try:
        unified_service = UnifiedService()
        result = await unified_service.get_activity_timeline(
            user_id=UUID(current_user_id),
            limit=limit,
            offset=offset
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching activity timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/progress")
async def get_comprehensive_progress(
    period: Literal["weekly", "monthly", "all_time"] = Query(
        default="weekly",
        description="Time period for progress report"
    ),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get comprehensive progress report across all activities
    Includes performance metrics, engagement, and recommendations
    
    Query Parameters:
    - period: Time period ('weekly', 'monthly', 'all_time')
    """
    try:
        unified_service = UnifiedService()
        result = await unified_service.get_comprehensive_progress(
            user_id=UUID(current_user_id),
            period=period
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching comprehensive progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/comparison")
async def get_week_comparison(
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Compare current week with previous week
    Shows trends and improvements
    """
    try:
        unified_service = UnifiedService()
        
        # Get current week data
        current_week = await unified_service.get_comprehensive_progress(
            user_id=UUID(current_user_id),
            period="weekly"
        )
        
        # TODO: Implement previous week comparison
        # This requires storing historical snapshots or calculating from raw data
        
        return {
            'current_week': current_week,
            'previous_week': {},  # Placeholder
            'changes': {
                'total_activities': 0,
                'total_time_minutes': 0,
                'avg_score': 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching week comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/achievements")
async def get_achievements_summary(
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get summary of all achievements
    Includes badges, streaks, XP, and milestones
    """
    try:
        unified_service = UnifiedService()
        stats = await unified_service.get_unified_stats(UUID(current_user_id))
        
        # Get badges
        badges_result = await unified_service._get_user_badges(UUID(current_user_id))
        
        # Calculate achievements
        achievements = {
            'badges': {
                'earned': len(badges_result),
                'recent': badges_result[:5],
                'categories': {
                    'streaks': len([b for b in badges_result if 'streak' in b['badge_key']]),
                    'performance': len([b for b in badges_result if 'accuracy' in b['badge_key'] or 'perfect' in b['badge_key']]),
                    'volume': len([b for b in badges_result if 'centurion' in b['badge_key'] or 'champion' in b['badge_key']])
                }
            },
            'streaks': {
                'current': stats['current_streak'],
                'longest': stats['longest_streak'],
                'at_risk': stats['current_streak'] > 0  # Simplified, should check last activity date
            },
            'xp': {
                'total': stats['total_xp'],
                'rank': 'Bronze',  # TODO: Calculate actual rank
                'next_rank_at': 1000
            },
            'milestones': {
                'total_activities': stats['lrg_sessions'] + stats['writing_evaluations'] + stats['speaking_sessions'],
                'total_time_hours': stats['lrg_time_sec'] // 3600,
                'languages_practiced': 1  # TODO: Count from sessions
            }
        }
        
        return achievements
        
    except Exception as e:
        logger.error(f"Error fetching achievements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/insights")
async def get_learning_insights(
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get personalized learning insights and recommendations
    Based on activity patterns and performance
    """
    try:
        unified_service = UnifiedService()
        progress = await unified_service.get_comprehensive_progress(
            user_id=UUID(current_user_id),
            period="monthly"
        )
        
        # Generate insights
        insights = {
            'strengths': [],
            'improvements': progress.get('improvements', []),
            'focus_areas': progress.get('areas_for_focus', []),
            'recommendations': [],
            'trends': {
                'consistency': {
                    'score': progress.get('consistency_score', 0),
                    'trend': 'stable'  # TODO: Calculate actual trend
                },
                'performance': {
                    'lrg': progress.get('lrg_avg_accuracy'),
                    'writing': progress.get('writing_avg_score'),
                    'overall_trend': 'improving'  # TODO: Calculate actual trend
                }
            }
        }
        
        # Add recommendations based on data
        if progress.get('consistency_score', 0) < 50:
            insights['recommendations'].append({
                'type': 'consistency',
                'message': 'Try to practice daily for better retention',
                'priority': 'high'
            })
        
        if progress.get('lrg_avg_accuracy') and progress['lrg_avg_accuracy'] < 70:
            insights['recommendations'].append({
                'type': 'performance',
                'message': 'Focus on accuracy over speed in LRG exercises',
                'priority': 'medium'
            })
        
        if progress.get('total_writing_submissions', 0) == 0:
            insights['recommendations'].append({
                'type': 'variety',
                'message': 'Try writing practice to complement your learning',
                'priority': 'low'
            })
        
        return insights
        
    except Exception as e:
        logger.error(f"Error fetching learning insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))