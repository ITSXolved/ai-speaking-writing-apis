"""
Unified service for aggregating data across LRG, Writing, and Speaking
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from collections import defaultdict
import logging

from app.db.supabase import SupabaseService
from app.models.unified import (
    UnifiedUserStats, UnifiedDailyActivity, UnifiedDashboardSummary,
    ActivityTimelineItem, WritingEvaluationSummary, SpeakingSessionSummary,
    ComprehensiveProgress
)

logger = logging.getLogger(__name__)


class UnifiedService(SupabaseService):
    """Service for unified activity data across all learning types"""
    
    def __init__(self):
        super().__init__(use_admin=False)
    
    async def get_unified_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get combined statistics across all activities"""
        try:
            # Use the unified view
            result = self.db('unified_user_activity').select('*').eq(
                'user_id', str(user_id)
            ).execute()
            
            if not result.data:
                return self._empty_stats(user_id)
            
            stats = result.data[0]
            
            return {
                'user_id': stats['user_id'],
                'display_name': stats.get('display_name'),
                'email': stats.get('email'),
                'skill_level': stats.get('skill_level'),
                'target_language': stats.get('target_language'),
                'lrg_sessions': stats.get('lrg_sessions', 0),
                'lrg_time_sec': stats.get('lrg_time_sec', 0),
                'lrg_avg_score': stats.get('lrg_avg_score'),
                'writing_evaluations': stats.get('writing_evaluations', 0),
                'writing_avg_score': stats.get('writing_avg_score'),
                'speaking_sessions': stats.get('speaking_sessions', 0),
                'current_streak': stats.get('current_streak', 0),
                'longest_streak': stats.get('longest_streak', 0),
                'total_xp': stats.get('total_xp', 0),
                'last_activity': stats.get('last_activity')
            }
            
        except Exception as e:
            logger.error(f"Error getting unified stats: {e}")
            raise
    
    async def get_unified_dashboard(
        self,
        user_id: UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get complete unified dashboard"""
        try:
            start_date = date.today() - timedelta(days=days)
            
            # Get overall stats
            stats = await self.get_unified_stats(user_id)
            
            # Get LRG specific data
            lrg_stats = await self._get_lrg_summary(user_id, start_date)
            
            # Get writing data
            writing_stats = await self._get_writing_summary(user_id, start_date)
            
            # Get speaking data
            speaking_stats = await self._get_speaking_summary(user_id, start_date)
            
            # Get daily activities
            daily_activities = await self._get_daily_activities(user_id, start_date)
            
            # Get badges
            badges = await self._get_user_badges(user_id)
            
            # Calculate totals
            total_time = (
                lrg_stats['total_time_sec'] +
                writing_stats.get('total_time_sec', 0) +
                speaking_stats.get('total_time_sec', 0)
            )
            
            total_activities = (
                lrg_stats['session_count'] +
                writing_stats['evaluation_count'] +
                speaking_stats['session_count']
            )
            
            return {
                'user_id': str(user_id),
                'as_of': datetime.utcnow().isoformat(),
                'period_days': days,
                'total_activities': total_activities,
                'total_time_minutes': total_time // 60,
                'current_streak': stats['current_streak'],
                'total_xp': stats['total_xp'],
                'lrg_stats': lrg_stats,
                'writing_stats': writing_stats,
                'speaking_stats': speaking_stats,
                'recent_activities': daily_activities,
                'badges': badges,
                'next_milestone': self._calculate_next_milestone(stats)
            }
            
        except Exception as e:
            logger.error(f"Error getting unified dashboard: {e}")
            raise
    
    async def get_activity_timeline(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get chronological timeline of all activities"""
        try:
            timeline_items = []
            
            # Get LRG sessions
            lrg_sessions = self.db('lrg_sessions').select('*').eq(
                'user_id', str(user_id)
            ).not_.is_('completed_at', 'null').order(
                'completed_at', desc=True
            ).limit(limit).execute()
            
            for session in lrg_sessions.data:
                timeline_items.append({
                    'timestamp': session['completed_at'],
                    'activity_type': session['modality'],
                    'title': f"{session['modality'].title()} - {session['day_code']}",
                    'score': session.get('score_pct'),
                    'duration_sec': session.get('duration_sec'),
                    'details': {
                        'session_id': session['session_id'],
                        'xp_earned': session.get('xp_earned', 0)
                    }
                })
            
            # Get writing evaluations
            writing_evals = self.db('writing_evaluations').select('*').eq(
                'user_id', str(user_id)
            ).order('created_at', desc=True).limit(limit).execute()
            
            for eval in writing_evals.data:
                timeline_items.append({
                    'timestamp': eval['created_at'],
                    'activity_type': 'writing',
                    'title': f"Writing Evaluation - {eval.get('writing_type', 'general').title()}",
                    'score': eval.get('overall_score'),
                    'duration_sec': None,
                    'details': {
                        'evaluation_id': eval['id'],
                        'language': eval.get('language'),
                        'feedback_summary': eval.get('feedback_summary', '')[:100]
                    }
                })
            
            # Get speaking sessions
            speaking_sessions = self.db('sessions').select('*').eq(
                'user_id', str(user_id)
            ).eq('mode_code', 'speaking').not_.is_(
                'closed_at', 'null'
            ).order('closed_at', desc=True).limit(limit).execute()
            
            for session in speaking_sessions.data:
                duration = None
                if session.get('started_at') and session.get('closed_at'):
                    start = datetime.fromisoformat(session['started_at'])
                    end = datetime.fromisoformat(session['closed_at'])
                    duration = int((end - start).total_seconds())
                
                timeline_items.append({
                    'timestamp': session['closed_at'],
                    'activity_type': 'speaking',
                    'title': f"Speaking Session - {session.get('language_code', 'unknown')}",
                    'score': None,
                    'duration_sec': duration,
                    'details': {
                        'session_id': session['id'],
                        'language': session.get('language_code')
                    }
                })
            
            # Sort by timestamp
            timeline_items.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Paginate
            paginated_items = timeline_items[offset:offset + limit]
            
            return {
                'user_id': str(user_id),
                'items': paginated_items,
                'total_count': len(timeline_items),
                'page': (offset // limit) + 1,
                'page_size': limit
            }
            
        except Exception as e:
            logger.error(f"Error getting activity timeline: {e}")
            raise
    
    async def get_comprehensive_progress(
        self,
        user_id: UUID,
        period: str = 'weekly'
    ) -> Dict[str, Any]:
        """Get comprehensive progress report"""
        try:
            # Determine date range
            if period == 'weekly':
                start_date = date.today() - timedelta(days=7)
            elif period == 'monthly':
                start_date = date.today() - timedelta(days=30)
            else:  # all_time
                start_date = date(2020, 1, 1)
            
            # Get all activities in period
            lrg_sessions = await self._get_lrg_sessions_in_period(user_id, start_date)
            writing_evals = await self._get_writing_in_period(user_id, start_date)
            speaking_sessions = await self._get_speaking_in_period(user_id, start_date)
            
            # Calculate metrics
            total_time = sum(s.get('duration_sec', 0) for s in lrg_sessions)
            lrg_count = len(lrg_sessions)
            
            # LRG accuracy
            lrg_avg_accuracy = None
            if lrg_count > 0:
                scores = [s.get('score_pct', 0) for s in lrg_sessions if s.get('score_pct')]
                lrg_avg_accuracy = sum(scores) / len(scores) if scores else None
            
            # Writing average
            writing_avg = None
            if writing_evals:
                scores = [w.get('overall_score', 0) for w in writing_evals]
                writing_avg = sum(scores) / len(scores) if scores else None
            
            # Active days
            active_dates = set()
            for s in lrg_sessions:
                if s.get('completed_at'):
                    active_dates.add(datetime.fromisoformat(s['completed_at']).date())
            for w in writing_evals:
                if w.get('created_at'):
                    active_dates.add(datetime.fromisoformat(w['created_at']).date())
            for sp in speaking_sessions:
                if sp.get('closed_at'):
                    active_dates.add(datetime.fromisoformat(sp['closed_at']).date())
            
            active_days = len(active_dates)
            
            # Get streak
            stats = await self.get_unified_stats(user_id)
            
            # Get concept mastery
            concepts_mastered = await self._count_mastered_concepts(user_id)
            
            # Calculate consistency score
            days_in_period = (date.today() - start_date).days
            consistency_score = (active_days / days_in_period * 100) if days_in_period > 0 else 0
            
            # Identify improvements and focus areas
            improvements, focus_areas = await self._analyze_progress(user_id, period)
            
            return {
                'user_id': str(user_id),
                'report_period': period,
                'total_time_minutes': total_time // 60,
                'avg_session_minutes': (total_time / (lrg_count or 1)) // 60,
                'total_lrg_sessions': lrg_count,
                'total_writing_submissions': len(writing_evals),
                'total_speaking_sessions': len(speaking_sessions),
                'lrg_avg_accuracy': round(lrg_avg_accuracy, 2) if lrg_avg_accuracy else None,
                'writing_avg_score': round(writing_avg, 2) if writing_avg else None,
                'speaking_evaluation_avg': None,  # TODO: Calculate from evaluations
                'active_days': active_days,
                'current_streak': stats['current_streak'],
                'consistency_score': round(consistency_score, 2),
                'total_xp': stats['total_xp'],
                'badges_earned': await self._count_badges(user_id),
                'concepts_mastered': concepts_mastered,
                'improvements': improvements,
                'areas_for_focus': focus_areas
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive progress: {e}")
            raise
    
    # ==================== HELPER METHODS ====================
    
    async def _get_lrg_summary(
        self,
        user_id: UUID,
        start_date: date
    ) -> Dict[str, Any]:
        """Get LRG activity summary"""
        try:
            result = self.db('lrg_sessions').select('*').eq(
                'user_id', str(user_id)
            ).gte(
                'completed_at', f"{start_date}T00:00:00Z"
            ).not_.is_('completed_at', 'null').execute()
            
            sessions = result.data
            
            return {
                'session_count': len(sessions),
                'total_time_sec': sum(s.get('duration_sec', 0) for s in sessions),
                'avg_score': sum(s.get('score_pct', 0) for s in sessions) / len(sessions) if sessions else None,
                'by_modality': {
                    'reading': len([s for s in sessions if s['modality'] == 'reading']),
                    'listening': len([s for s in sessions if s['modality'] == 'listening']),
                    'grammar': len([s for s in sessions if s['modality'] == 'grammar'])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting LRG summary: {e}")
            return {'session_count': 0, 'total_time_sec': 0, 'avg_score': None, 'by_modality': {}}
    
    async def _get_writing_summary(
        self,
        user_id: UUID,
        start_date: date
    ) -> Dict[str, Any]:
        """Get writing activity summary"""
        try:
            result = self.db('writing_evaluations').select('*').eq(
                'user_id', str(user_id)
            ).gte(
                'created_at', f"{start_date}T00:00:00Z"
            ).execute()
            
            evals = result.data
            
            return {
                'evaluation_count': len(evals),
                'avg_score': sum(e.get('overall_score', 0) for e in evals) / len(evals) if evals else None,
                'total_time_sec': 0,  # Not tracked in writing_evaluations
                'recent_feedback': [e.get('feedback_summary', '')[:100] for e in evals[:3]]
            }
            
        except Exception as e:
            logger.error(f"Error getting writing summary: {e}")
            return {'evaluation_count': 0, 'avg_score': None, 'total_time_sec': 0, 'recent_feedback': []}
    
    async def _get_speaking_summary(
        self,
        user_id: UUID,
        start_date: date
    ) -> Dict[str, Any]:
        """Get speaking activity summary"""
        try:
            result = self.db('sessions').select('*').eq(
                'user_id', str(user_id)
            ).eq('mode_code', 'speaking').gte(
                'started_at', f"{start_date}T00:00:00Z"
            ).not_.is_('closed_at', 'null').execute()
            
            sessions = result.data
            
            total_time = 0
            for s in sessions:
                if s.get('started_at') and s.get('closed_at'):
                    start = datetime.fromisoformat(s['started_at'])
                    end = datetime.fromisoformat(s['closed_at'])
                    total_time += int((end - start).total_seconds())
            
            return {
                'session_count': len(sessions),
                'total_time_sec': total_time,
                'languages': list(set(s.get('language_code') for s in sessions if s.get('language_code')))
            }
            
        except Exception as e:
            logger.error(f"Error getting speaking summary: {e}")
            return {'session_count': 0, 'total_time_sec': 0, 'languages': []}
    
    async def _get_daily_activities(
        self,
        user_id: UUID,
        start_date: date
    ) -> List[Dict[str, Any]]:
        """Get daily activity breakdown"""
        try:
            result = self.db('unified_daily_activity').select('*').eq(
                'user_id', str(user_id)
            ).gte('activity_date', start_date.isoformat()).order(
                'activity_date', desc=True
            ).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting daily activities: {e}")
            return []
    
    async def _get_user_badges(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get user's earned badges"""
        try:
            result = self.db('user_badges').select(
                '*, badges_catalog(*)'
            ).eq('user_id', str(user_id)).order(
                'earned_at', desc=True
            ).execute()
            
            return [
                {
                    'badge_key': b['badge_key'],
                    'title': b['badges_catalog']['title'] if b.get('badges_catalog') else b['badge_key'],
                    'earned_at': b['earned_at']
                }
                for b in result.data
            ]
            
        except Exception as e:
            logger.error(f"Error getting badges: {e}")
            return []
    
    async def _get_lrg_sessions_in_period(
        self,
        user_id: UUID,
        start_date: date
    ) -> List[Dict[str, Any]]:
        """Get LRG sessions in period"""
        result = self.db('lrg_sessions').select('*').eq(
            'user_id', str(user_id)
        ).gte('completed_at', f"{start_date}T00:00:00Z").not_.is_(
            'completed_at', 'null'
        ).execute()
        return result.data
    
    async def _get_writing_in_period(
        self,
        user_id: UUID,
        start_date: date
    ) -> List[Dict[str, Any]]:
        """Get writing evaluations in period"""
        result = self.db('writing_evaluations').select('*').eq(
            'user_id', str(user_id)
        ).gte('created_at', f"{start_date}T00:00:00Z").execute()
        return result.data
    
    async def _get_speaking_in_period(
        self,
        user_id: UUID,
        start_date: date
    ) -> List[Dict[str, Any]]:
        """Get speaking sessions in period"""
        result = self.db('sessions').select('*').eq(
            'user_id', str(user_id)
        ).eq('mode_code', 'speaking').gte(
            'started_at', f"{start_date}T00:00:00Z"
        ).not_.is_('closed_at', 'null').execute()
        return result.data
    
    async def _count_mastered_concepts(self, user_id: UUID) -> int:
        """Count concepts with high mastery score"""
        try:
            result = self.db('concept_mastery').select('id').eq(
                'user_id', str(user_id)
            ).gte('mastery_score', 0.8).execute()
            return len(result.data)
        except:
            return 0
    
    async def _count_badges(self, user_id: UUID) -> int:
        """Count earned badges"""
        try:
            result = self.db('user_badges').select('badge_key').eq(
                'user_id', str(user_id)
            ).execute()
            return len(result.data)
        except:
            return 0
    
    async def _analyze_progress(
        self,
        user_id: UUID,
        period: str
    ) -> tuple:
        """Analyze improvements and focus areas"""
        improvements = []
        focus_areas = []
        
        # Simple analysis - can be expanded
        try:
            stats = await self.get_unified_stats(user_id)
            
            if stats['lrg_avg_score'] and stats['lrg_avg_score'] >= 80:
                improvements.append("Strong LRG performance")
            elif stats['lrg_avg_score'] and stats['lrg_avg_score'] < 60:
                focus_areas.append("Practice more LRG exercises")
            
            if stats['current_streak'] >= 7:
                improvements.append("Excellent consistency")
            elif stats['current_streak'] < 3:
                focus_areas.append("Build daily practice habit")
            
            if stats['writing_evaluations'] == 0:
                focus_areas.append("Try writing practice")
            
        except Exception as e:
            logger.error(f"Error analyzing progress: {e}")
        
        return improvements, focus_areas
    
    def _calculate_next_milestone(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate next milestone"""
        # XP milestones
        xp_milestones = [100, 500, 1000, 2000, 5000, 10000]
        next_xp = next((m for m in xp_milestones if m > stats['total_xp']), 10000)
        
        # Streak milestones
        streak_milestones = [3, 7, 14, 30, 60, 90]
        next_streak = next((m for m in streak_milestones if m > stats['current_streak']), 90)
        
        return {
            'type': 'xp' if (next_xp - stats['total_xp']) < 100 else 'streak',
            'target': next_xp if (next_xp - stats['total_xp']) < 100 else next_streak,
            'current': stats['total_xp'] if (next_xp - stats['total_xp']) < 100 else stats['current_streak']
        }
    
    def _empty_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Return empty stats structure"""
        return {
            'user_id': str(user_id),
            'display_name': None,
            'email': None,
            'skill_level': None,
            'target_language': None,
            'lrg_sessions': 0,
            'lrg_time_sec': 0,
            'lrg_avg_score': None,
            'writing_evaluations': 0,
            'writing_avg_score': None,
            'speaking_sessions': 0,
            'current_streak': 0,
            'longest_streak': 0,
            'total_xp': 0,
            'last_activity': None
        }