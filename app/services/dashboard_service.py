"""
Dashboard service for aggregating metrics and analytics
"""
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, date, timedelta
from collections import defaultdict
import logging

from app.db.supabase import SupabaseService
from app.models.dashboard import (
    DashboardSummary, ModalityDetail,
    WeeklyMinutes, AccuracyPoint, CompletionDay, RecentResult
)
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class DashboardService(SupabaseService):
    """Service for dashboard data aggregation"""
    
    def __init__(self):
        super().__init__(use_admin=False)
        self.analytics = AnalyticsService()
    
    async def get_summary(
        self,
        user_id: UUID,
        window: str = "7d"
    ) -> Dict[str, Any]:
        """Get dashboard summary with configurable time window"""
        try:
            # Parse window
            days = int(window.replace('d', ''))
            start_date = date.today() - timedelta(days=days)
            
            # Get streak info
            streak_result = self.db('streaks').select('*').eq(
                'user_id', str(user_id)
            ).execute()
            
            streak_days = streak_result.data[0]['current_streak'] if streak_result.data else 0
            
            # Get XP
            xp_info = await self.analytics.get_user_xp(user_id)
            
            # Get daily target progress (today's completions)
            today = date.today()
            today_sessions = self.db('lrg_sessions').select(
                'modality'
            ).eq('user_id', str(user_id)).gte(
                'completed_at', f"{today}T00:00:00Z"
            ).not_.is_('completed_at', 'null').execute()
            
            unique_modalities = len({s['modality'] for s in today_sessions.data})
            
            # Get weekly minutes
            weekly_minutes = await self._get_weekly_minutes(user_id, start_date)
            
            # Get accuracy trends
            accuracy_trend = await self._get_accuracy_trend(user_id, start_date)
            
            # Get completion heatmap
            completion_heatmap = await self._get_completion_heatmap(user_id, start_date)
            
            # Get recent results
            recent_results = await self._get_recent_results(user_id, limit=10)
            
            # Get badges
            badges = await self._get_user_badges(user_id)
            
            # Get last activity
            last_activity = await self._get_last_activity(user_id)
            
            # Calculate next reward
            next_reward = await self._get_next_reward(user_id, xp_info['total'], streak_days)
            
            return {
                'user_id': str(user_id),
                'as_of': datetime.utcnow().isoformat(),
                'streak_days': streak_days,
                'xp': xp_info,
                'daily_target': {
                    'target': 3,
                    'completed': unique_modalities
                },
                'last_activity': last_activity,
                'weekly_minutes': weekly_minutes,
                'accuracy_trend': accuracy_trend,
                'completion_heatmap': completion_heatmap,
                'recent_results': recent_results,
                'badges': badges,
                'next_reward': next_reward
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            raise
    
    async def get_modality_detail(
        self,
        user_id: UUID,
        modality: str
    ) -> Dict[str, Any]:
        """Get detailed view for a specific modality"""
        try:
            # Get all sessions for this modality
            sessions = self.db('lrg_analytics_sessions').select('*').eq(
                'user_id', str(user_id)
            ).eq('modality', modality).order(
                'completed_at', desc=False
            ).execute()
            
            if not sessions.data:
                return {
                    'modality': modality,
                    'accuracy_by_day': [],
                    'minutes_by_day': [],
                    'question_breakdown': [],
                    'best_day': None,
                    'best_accuracy': 0.0,
                    'total_time_minutes': 0,
                    'total_questions': 0,
                    'last_session': None
                }
            
            # Aggregate by day
            daily_data = defaultdict(lambda: {
                'accuracy_sum': 0,
                'accuracy_count': 0,
                'duration': 0
            })
            
            for session in sessions.data:
                day = datetime.fromisoformat(session['completed_at']).date()
                daily_data[day]['accuracy_sum'] += session['accuracy']
                daily_data[day]['accuracy_count'] += 1
                daily_data[day]['duration'] += session['duration_sec']
            
            # Build accuracy by day
            accuracy_by_day = [
                {
                    'date': day.isoformat(),
                    'accuracy': data['accuracy_sum'] / data['accuracy_count']
                }
                for day, data in sorted(daily_data.items())
            ]
            
            # Build minutes by day
            minutes_by_day = [
                {
                    'date': day.isoformat(),
                    'minutes': data['duration'] // 60
                }
                for day, data in sorted(daily_data.items())
            ]
            
            # Topic breakdown
            topic_breakdown = await self._get_topic_breakdown(user_id, modality)
            
            # Find best day
            best_day = max(daily_data.items(), key=lambda x: x[1]['accuracy_sum'] / x[1]['accuracy_count'])
            best_accuracy = best_day[1]['accuracy_sum'] / best_day[1]['accuracy_count']
            
            # Totals
            total_time_minutes = sum(s['duration_sec'] for s in sessions.data) // 60
            total_questions = sum(s['total_items'] for s in sessions.data)
            
            # Last session
            last_session_data = sessions.data[-1]
            last_session = {
                'day_code': last_session_data['day_code'],
                'score_pct': int(last_session_data['accuracy'] * 100),
                'duration_sec': last_session_data['duration_sec'],
                'completed_at': last_session_data['completed_at']
            }
            
            return {
                'modality': modality,
                'accuracy_by_day': accuracy_by_day,
                'minutes_by_day': minutes_by_day,
                'question_breakdown': topic_breakdown,
                'best_day': best_day[0].isoformat(),
                'best_accuracy': round(best_accuracy, 4),
                'total_time_minutes': total_time_minutes,
                'total_questions': total_questions,
                'last_session': last_session
            }
            
        except Exception as e:
            logger.error(f"Error getting modality detail: {e}")
            raise
    
    # ==================== HELPER METHODS ====================
    
    async def _get_weekly_minutes(
        self,
        user_id: UUID,
        start_date: date
    ) -> List[Dict[str, Any]]:
        """Get minutes spent per day per modality"""
        try:
            sessions = self.db('lrg_analytics_sessions').select('*').eq(
                'user_id', str(user_id)
            ).gte(
                'completed_at', f"{start_date}T00:00:00Z"
            ).execute()
            
            # Aggregate by date and modality
            daily_minutes = defaultdict(lambda: {
                'listening_min': 0,
                'reading_min': 0,
                'grammar_min': 0
            })
            
            for session in sessions.data:
                day = datetime.fromisoformat(session['completed_at']).date()
                modality = session['modality']
                minutes = session['duration_sec'] // 60
                daily_minutes[day][f"{modality}_min"] = daily_minutes[day].get(
                    f"{modality}_min", 0
                ) + minutes
            
            # Build result for each day in range
            result = []
            current = start_date
            while current <= date.today():
                data = daily_minutes.get(current, {
                    'listening_min': 0,
                    'reading_min': 0,
                    'grammar_min': 0
                })
                result.append({
                    'date': current.isoformat(),
                    **data
                })
                current += timedelta(days=1)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting weekly minutes: {e}")
            return []
    
    async def _get_accuracy_trend(
        self,
        user_id: UUID,
        start_date: date
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get accuracy trend per modality"""
        try:
            sessions = self.db('lrg_analytics_sessions').select('*').eq(
                'user_id', str(user_id)
            ).gte(
                'completed_at', f"{start_date}T00:00:00Z"
            ).order('completed_at').execute()
            
            # Aggregate by modality and date
            trends = {
                'listening': defaultdict(list),
                'reading': defaultdict(list),
                'grammar': defaultdict(list)
            }
            
            for session in sessions.data:
                day = datetime.fromisoformat(session['completed_at']).date()
                modality = session['modality']
                trends[modality][day].append(session['accuracy'])
            
            # Calculate averages per day
            result = {}
            for modality in ['listening', 'reading', 'grammar']:
                result[modality] = [
                    {
                        'date': day.isoformat(),
                        'accuracy': sum(accuracies) / len(accuracies)
                    }
                    for day, accuracies in sorted(trends[modality].items())
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting accuracy trend: {e}")
            return {'listening': [], 'reading': [], 'grammar': []}
    
    async def _get_completion_heatmap(
        self,
        user_id: UUID,
        start_date: date
    ) -> List[Dict[str, Any]]:
        """Get completion heatmap (which modalities completed each day)"""
        try:
            sessions = self.db('lrg_sessions').select(
                'modality, completed_at'
            ).eq('user_id', str(user_id)).gte(
                'completed_at', f"{start_date}T00:00:00Z"
            ).not_.is_('completed_at', 'null').execute()
            
            # Aggregate by date
            completions = defaultdict(set)
            for session in sessions.data:
                day = datetime.fromisoformat(session['completed_at']).date()
                completions[day].add(session['modality'])
            
            # Build heatmap
            result = []
            current = start_date
            while current <= date.today():
                modalities = completions.get(current, set())
                result.append({
                    'date': current.isoformat(),
                    'L': 'listening' in modalities,
                    'R': 'reading' in modalities,
                    'G': 'grammar' in modalities
                })
                current += timedelta(days=1)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting completion heatmap: {e}")
            return []
    
    async def _get_recent_results(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent session results"""
        try:
            sessions = self.db('lrg_sessions').select('*').eq(
                'user_id', str(user_id)
            ).not_.is_('completed_at', 'null').order(
                'completed_at', desc=True
            ).limit(limit).execute()
            
            return [
                {
                    'session_id': s['session_id'],
                    'day_code': s['day_code'],
                    'modality': s['modality'],
                    'score_pct': s['score_pct'],
                    'duration_sec': s['duration_sec'],
                    'completed_at': s['completed_at']
                }
                for s in sessions.data
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent results: {e}")
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
                    'description': b['badges_catalog'].get('description') if b.get('badges_catalog') else None,
                    'earned_at': b['earned_at']
                }
                for b in result.data
            ]
            
        except Exception as e:
            logger.error(f"Error getting badges: {e}")
            return []
    
    async def _get_last_activity(self, user_id: UUID) -> str:
        """Get timestamp of last activity"""
        try:
            result = self.db('lrg_sessions').select(
                'completed_at'
            ).eq('user_id', str(user_id)).not_.is_(
                'completed_at', 'null'
            ).order('completed_at', desc=True).limit(1).execute()
            
            if result.data:
                return result.data[0]['completed_at']
            return None
            
        except Exception as e:
            logger.error(f"Error getting last activity: {e}")
            return None
    
    async def _get_next_reward(
        self,
        user_id: UUID,
        current_xp: int,
        current_streak: int
    ) -> Dict[str, Any]:
        """Calculate next reward milestone"""
        # XP milestones: 500, 1000, 1500, 2000, etc.
        xp_milestones = [500, 1000, 1500, 2000, 2500, 3000, 5000, 10000]
        next_xp = next((m for m in xp_milestones if m > current_xp), xp_milestones[-1])
        
        # Streak milestones
        streak_milestones = [3, 7, 14, 30, 60, 90]
        next_streak = next((m for m in streak_milestones if m > current_streak), None)
        
        # Return closest reward
        if next_streak and (next_streak - current_streak) < 5:
            return {
                'type': 'streak',
                'target': next_streak,
                'current': current_streak
            }
        else:
            return {
                'type': 'xp',
                'target': next_xp,
                'current': current_xp
            }
    
    async def _get_topic_breakdown(
        self,
        user_id: UUID,
        modality: str
    ) -> List[Dict[str, Any]]:
        """Get performance breakdown by topic"""
        try:
            # Get all answers for this modality's sessions
            sessions = self.db('lrg_analytics_sessions').select(
                'session_id'
            ).eq('user_id', str(user_id)).eq(
                'modality', modality
            ).execute()
            
            if not sessions.data:
                return []
            
            session_ids = [s['session_id'] for s in sessions.data]
            
            # Get answers with topics
            answers = self.db('lrg_answers').select('*').in_(
                'session_id', session_ids
            ).not_.is_('topic', 'null').execute()
            
            # Aggregate by topic
            topic_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
            
            for answer in answers.data:
                topic = answer['topic']
                topic_stats[topic]['total'] += 1
                if answer['is_correct']:
                    topic_stats[topic]['correct'] += 1
            
            # Build result
            return [
                {
                    'topic': topic,
                    'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0,
                    'attempts': stats['total']
                }
                for topic, stats in topic_stats.items()
            ]
            
        except Exception as e:
            logger.error(f"Error getting topic breakdown: {e}")
            return []
    # async def _get_lrg_summary(self, user_id: UUID, start_date: date):
    #     try:
    #         result = self.db('lrg_sessions').select('*').eq(  # Changed from 'sessions'
    #             'user_id', str(user_id)
    #         ).gte('completed_at', f"{start_date}T00:00:00Z").not_.is_(
    #             'completed_at', 'null'
    #         ).execute()
    #         return result
    #     except Exception as e:
    #         logger.error(f"Error getting LRG summary: {e}")
    #         return None

    # async def _get_lrg_sessions_in_period(...):
    #         result = self.db('lrg_sessions').select('*').eq(  # Changed
    #             'user_id', str(user_id)
    #         ).gte('completed_at', f"{start_date}T00:00:00Z").not_.is_(
    #             'completed_at', 'null'
    #         ).execute()