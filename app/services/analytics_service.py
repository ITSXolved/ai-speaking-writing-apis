"""
Analytics service for XP, streaks, badges, and metrics
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
import logging
import math

from app.db.supabase import SupabaseService

logger = logging.getLogger(__name__)


# XP Configuration
XP_CONFIG = {
    "base_session_xp": 20,
    "accuracy_bonus_threshold": 0.80,
    "accuracy_bonus_xp": 10,
    "perfect_score_bonus": 25,  # 100% accuracy
    "first_session_bonus": 15,
    "speed_bonus_max": 10,
    "streak_bonus_per_day": 2,
    "streak_bonus_max": 30,
    "perfect_day_bonus": 50,  # All 3 modalities
    "daily_xp_goal": 100
}

# Level System Configuration
LEVEL_CONFIG = {
    "xp_per_level_base": 100,
    "xp_multiplier": 1.5,  # Exponential growth
    "level_names": {
        range(1, 6): "Beginner",
        range(6, 11): "Intermediate",
        range(11, 21): "Advanced",
        range(21, 36): "Expert",
        range(36, 100): "Master"
    }
}


class AnalyticsService(SupabaseService):
    """Service for analytics, XP, streaks, and badges"""
    
    def __init__(self):
        super().__init__(use_admin=True)  # Must be True
    
    # ==================== SESSION ANALYTICS ====================
    
    async def create_session_analytics(
        self,
        session_id: UUID,
        user_id: UUID,
        modality: str,
        day_code: str,
        total_items: int,
        correct_items: int,
        accuracy: float,
        duration_sec: int,
        completed_at: datetime
    ) -> Dict[str, Any]:
        """Create analytics record for a session"""
        try:
            payload = {
                'session_id': str(session_id),
                'user_id': str(user_id),
                'modality': modality,
                'day_code': day_code,
                'total_items': total_items,
                'correct_items': correct_items,
                'accuracy': round(accuracy, 4),
                'duration_sec': duration_sec,
                'completed_at': completed_at.isoformat()
            }

            # Ensure analytics creation is idempotent when the endpoint is retried.
            existing = self.db('lrg_analytics_sessions').select('session_id').eq(
                'session_id', str(session_id)
            ).limit(1).execute()

            if existing.data:
                result = self.db('lrg_analytics_sessions').update(payload).eq(
                    'session_id', str(session_id)
                ).execute()
            else:
                result = self.db('lrg_analytics_sessions').insert(payload).execute()

            if not result.data:
                raise Exception("Failed to upsert analytics")

            return result.data[0]

        except Exception as e:
            logger.error(f"Error creating analytics: {e}")
            raise
    
    # ==================== XP MANAGEMENT ====================
    
    async def award_xp(
        self,
        user_id: UUID,
        amount: int,
        source: str = 'session'
    ) -> Dict[str, Any]:
        """Award XP to user"""
        try:
            result = self.db('xp_ledger').insert({
                'user_id': str(user_id),
                'source': source,
                'amount': amount,
                'occurred_at': datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"Awarded {amount} XP to user {user_id} (source: {source})")
            return result.data[0] if result.data else {}
            
        except Exception as e:
            logger.error(f"Error awarding XP: {e}")
            raise
    
    async def get_user_xp(self, user_id: UUID) -> Dict[str, int]:
        """Get user's total and today's XP"""
        try:
            # Total XP
            total_result = self.db('xp_ledger').select(
                'amount'
            ).eq('user_id', str(user_id)).execute()
            
            total_xp = sum(row['amount'] for row in total_result.data)
            
            # Today's XP
            today = date.today()
            today_result = self.db('xp_ledger').select(
                'amount'
            ).eq('user_id', str(user_id)).gte(
                'occurred_at', f"{today}T00:00:00Z"
            ).execute()
            
            today_xp = sum(row['amount'] for row in today_result.data)
            
            return {'total': total_xp, 'today': today_xp}
            
        except Exception as e:
            logger.error(f"Error getting user XP: {e}")
            raise
    
    # ==================== STREAK MANAGEMENT ====================
    
    async def update_streak(
        self,
        user_id: UUID,
        completed_at: datetime
    ) -> Dict[str, int]:
        """Update user's streak based on completion date"""
        try:
            completion_date = completed_at.date()
            
            # Get current streak info
            streak_result = self.db('streaks').select('*').eq(
                'user_id', str(user_id)
            ).execute()
            
            if not streak_result.data:
                # First time user - create streak record
                new_streak = self.db('streaks').insert({
                    'user_id': str(user_id),
                    'current_streak': 1,
                    'longest_streak': 1,
                    'last_active_date': completion_date.isoformat()
                }).execute()
                
                return {
                    'current_streak': 1,
                    'longest_streak': 1
                }
            
            streak = streak_result.data[0]
            last_active = datetime.fromisoformat(
                streak['last_active_date']
            ).date() if streak['last_active_date'] else None
            
            current_streak = streak['current_streak']
            longest_streak = streak['longest_streak']
            
            # Calculate new streak
            if last_active:
                days_diff = (completion_date - last_active).days
                
                if days_diff == 0:
                    # Same day - no change
                    pass
                elif days_diff == 1:
                    # Consecutive day - increment streak
                    current_streak += 1
                    longest_streak = max(longest_streak, current_streak)
                else:
                    # Streak broken - reset to 1
                    current_streak = 1
            else:
                current_streak = 1
            
            # Update streak record
            self.db('streaks').update({
                'current_streak': current_streak,
                'longest_streak': longest_streak,
                'last_active_date': completion_date.isoformat()
            }).eq('user_id', str(user_id)).execute()
            
            logger.info(f"Updated streak for user {user_id}: {current_streak} days")
            
            return {
                'current_streak': current_streak,
                'longest_streak': longest_streak
            }
            
        except Exception as e:
            logger.error(f"Error updating streak: {e}")
            raise
    
    # ==================== BADGE MANAGEMENT ====================
    
    async def check_and_award_badges(
        self,
        user_id: UUID,
        session_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check criteria and award eligible badges"""
        badges_awarded = []
        
        try:
            # Get existing badges
            existing_result = self.db('user_badges').select(
                'badge_key'
            ).eq('user_id', str(user_id)).execute()
            
            existing_badges = {
                row['badge_key'] for row in existing_result.data
            }
            
            # Check streak badges
            streak = session_data.get('streak', 0)
            streak_badges = [
                ('streak_3', 3),
                ('streak_7', 7),
                ('streak_30', 30)
            ]
            
            for badge_key, required_streak in streak_badges:
                if streak >= required_streak and badge_key not in existing_badges:
                    await self._award_badge(user_id, badge_key)
                    badges_awarded.append({
                        'badge_key': badge_key,
                        'title': f'{required_streak} Day Streak',
                        'earned_at': datetime.utcnow()
                    })
            
            # Check accuracy badges
            accuracy = session_data.get('accuracy', 0)
            if accuracy >= 0.80 and 'accuracy_master_80' not in existing_badges:
                # Check last 3 sessions for consistent 80%+
                recent = await self._get_recent_accuracy(user_id, limit=3)
                if len(recent) >= 3 and all(a >= 0.80 for a in recent):
                    await self._award_badge(user_id, 'accuracy_master_80')
                    badges_awarded.append({
                        'badge_key': 'accuracy_master_80',
                        'title': 'Accuracy Master',
                        'earned_at': datetime.utcnow()
                    })
            
            # Check perfect day (R, L, G all completed)
            if await self._check_perfect_day(user_id):
                if 'perfect_day' not in existing_badges:
                    await self._award_badge(user_id, 'perfect_day')
                    badges_awarded.append({
                        'badge_key': 'perfect_day',
                        'title': 'Perfect Day',
                        'earned_at': datetime.utcnow()
                    })
            
            # Check centurion (100 questions)
            total_questions = await self._get_total_questions(user_id)
            if total_questions >= 100 and 'centurion' not in existing_badges:
                await self._award_badge(user_id, 'centurion')
                badges_awarded.append({
                    'badge_key': 'centurion',
                    'title': 'Centurion',
                    'earned_at': datetime.utcnow()
                })
            
            return badges_awarded
            
        except Exception as e:
            logger.error(f"Error checking badges: {e}")
            return badges_awarded
    
    async def _award_badge(self, user_id: UUID, badge_key: str):
        """Award a badge to user"""
        try:
            self.db('user_badges').insert({
                'user_id': str(user_id),
                'badge_key': badge_key,
                'earned_at': datetime.utcnow().isoformat()
            }).execute()
            
            # Award bonus XP for badge
            await self.award_xp(user_id, 50, source=f'badge_{badge_key}')
            
        except Exception as e:
            logger.error(f"Error awarding badge: {e}")
    
    async def _get_recent_accuracy(
        self,
        user_id: UUID,
        limit: int = 3
    ) -> List[float]:
        """Get recent session accuracies"""
        try:
            result = self.db('analytics_sessions').select(
                'accuracy'
            ).eq('user_id', str(user_id)).order(
                'completed_at', desc=True
            ).limit(limit).execute()
            
            return [row['accuracy'] for row in result.data]
            
        except Exception as e:
            logger.error(f"Error getting recent accuracy: {e}")
            return []
    
    async def _check_perfect_day(self, user_id: UUID) -> bool:
        """Check if user completed R, L, G today"""
        try:
            today = date.today()
            
            result = self.db('sessions').select(
                'modality'
            ).eq('user_id', str(user_id)).gte(
                'completed_at', f"{today}T00:00:00Z"
            ).not_.is_('completed_at', 'null').execute()
            
            modalities = {row['modality'] for row in result.data}
            return {'reading', 'listening', 'grammar'}.issubset(modalities)
            
        except Exception as e:
            logger.error(f"Error checking perfect day: {e}")
            return False
    
    async def _get_total_questions(self, user_id: UUID) -> int:
        """Get total questions answered by user"""
        try:
            result = self.db('analytics_sessions').select(
                'total_items'
            ).eq('user_id', str(user_id)).execute()

            return sum(row['total_items'] for row in result.data)

        except Exception as e:
            logger.error(f"Error getting total questions: {e}")
            return 0

    # ==================== ENHANCED XP CALCULATION ====================

    def calculate_session_xp(
        self,
        accuracy: float,
        duration_sec: int,
        expected_duration_sec: int,
        current_streak: int,
        is_first_session_today: bool,
        is_perfect_day: bool
    ) -> Dict[str, int]:
        """
        Calculate XP with bonuses

        Returns:
            Dictionary with XP breakdown and total
        """
        breakdown = {
            "base_xp": XP_CONFIG["base_session_xp"],
            "accuracy_bonus": 0,
            "speed_bonus": 0,
            "streak_bonus": 0,
            "perfect_score_bonus": 0,
            "first_of_day_bonus": 0,
            "perfect_day_bonus": 0
        }

        # Accuracy bonus (≥80%)
        if accuracy >= XP_CONFIG["accuracy_bonus_threshold"]:
            breakdown["accuracy_bonus"] = XP_CONFIG["accuracy_bonus_xp"]

        # Perfect score bonus (100%)
        if accuracy >= 1.0:
            breakdown["perfect_score_bonus"] = XP_CONFIG["perfect_score_bonus"]

        # Speed bonus (completed faster than expected)
        if duration_sec < expected_duration_sec:
            time_saved_pct = (expected_duration_sec - duration_sec) / expected_duration_sec
            breakdown["speed_bonus"] = min(
                int(time_saved_pct * XP_CONFIG["speed_bonus_max"]),
                XP_CONFIG["speed_bonus_max"]
            )

        # Streak bonus (2 XP per day, max 30)
        if current_streak > 0:
            breakdown["streak_bonus"] = min(
                current_streak * XP_CONFIG["streak_bonus_per_day"],
                XP_CONFIG["streak_bonus_max"]
            )

        # First session bonus
        if is_first_session_today:
            breakdown["first_of_day_bonus"] = XP_CONFIG["first_session_bonus"]

        # Perfect day bonus (all 3 modalities)
        if is_perfect_day:
            breakdown["perfect_day_bonus"] = XP_CONFIG["perfect_day_bonus"]

        breakdown["total_xp"] = sum(breakdown.values())

        return breakdown

    # ==================== LEVEL SYSTEM ====================

    def calculate_level(self, total_xp: int) -> Dict[str, Any]:
        """Calculate user level from total XP"""
        level = 1
        xp_for_current_level = 0

        while True:
            xp_for_next = self._xp_required_for_level(level + 1)
            if total_xp < xp_for_next:
                break
            xp_for_current_level = xp_for_next
            level += 1

        xp_for_next_level = self._xp_required_for_level(level + 1)
        xp_in_current_level = total_xp - xp_for_current_level
        xp_to_next_level = xp_for_next_level - total_xp

        level_name = self._get_level_name(level)

        progress_pct = int(
            (xp_in_current_level / (xp_for_next_level - xp_for_current_level)) * 100
        )

        return {
            "current_level": level,
            "level_name": level_name,
            "total_xp": total_xp,
            "xp_for_current_level": xp_for_current_level,
            "xp_for_next_level": xp_for_next_level,
            "xp_to_next_level": xp_to_next_level,
            "progress_pct": progress_pct
        }

    def _xp_required_for_level(self, level: int) -> int:
        """Calculate total XP required to reach a level"""
        if level == 1:
            return 0

        base = LEVEL_CONFIG["xp_per_level_base"]
        multiplier = LEVEL_CONFIG["xp_multiplier"]

        # Exponential growth: XP = base * (multiplier ^ (level - 1))
        return int(base * (multiplier ** (level - 1)))

    def _get_level_name(self, level: int) -> str:
        """Get level name based on level number"""
        for level_range, name in LEVEL_CONFIG["level_names"].items():
            if level in level_range:
                return name
        return "Master"

    # ==================== DAILY PROGRESS ====================

    async def get_daily_progress(self, user_id: UUID) -> Dict[str, Any]:
        """Get user's progress for today"""
        try:
            today = date.today()

            # Get today's sessions
            sessions_result = self.db('lrg_sessions').select('*').eq(
                'user_id', str(user_id)
            ).gte(
                'completed_at', f"{today}T00:00:00Z"
            ).not_.is_('completed_at', 'null').execute()

            sessions = sessions_result.data or []

            # Get today's XP
            xp_result = self.db('xp_ledger').select('amount').eq(
                'user_id', str(user_id)
            ).gte(
                'occurred_at', f"{today}T00:00:00Z"
            ).execute()

            xp_today = sum(row['amount'] for row in xp_result.data or [])

            # Calculate stats
            modalities_completed = list(set(s['modality'] for s in sessions))
            time_spent = sum(s.get('duration_sec', 0) for s in sessions) // 60

            is_perfect_day = {'listening', 'reading', 'grammar'}.issubset(
                set(modalities_completed)
            )

            # Goals
            xp_goal = XP_CONFIG["daily_xp_goal"]
            session_goal = 3

            goals = [
                {
                    "goal_type": "xp",
                    "target": xp_goal,
                    "current": xp_today,
                    "is_completed": xp_today >= xp_goal
                },
                {
                    "goal_type": "sessions",
                    "target": session_goal,
                    "current": len(sessions),
                    "is_completed": len(sessions) >= session_goal
                },
                {
                    "goal_type": "perfect_day",
                    "target": 1,
                    "current": 1 if is_perfect_day else 0,
                    "is_completed": is_perfect_day
                }
            ]

            return {
                "user_id": user_id,
                "date": today,
                "xp_earned": xp_today,
                "xp_goal": xp_goal,
                "sessions_completed": len(sessions),
                "session_goal": session_goal,
                "time_spent_minutes": time_spent,
                "modalities_completed": modalities_completed,
                "goals": goals,
                "is_perfect_day": is_perfect_day
            }

        except Exception as e:
            logger.error(f"Error getting daily progress: {e}")
            raise

    # ==================== STREAK CALENDAR ====================

    async def get_streak_calendar(
        self,
        user_id: UUID,
        month: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get calendar view of user's activity"""
        try:
            if month is None:
                today = date.today()
                month = today.strftime("%Y-%m")

            # Parse month
            year, month_num = map(int, month.split("-"))

            # Get sessions for the month
            start_date = date(year, month_num, 1)
            if month_num == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month_num + 1, 1)

            sessions_result = self.db('lrg_sessions').select('*').eq(
                'user_id', str(user_id)
            ).gte(
                'completed_at', start_date.isoformat()
            ).lt(
                'completed_at', end_date.isoformat()
            ).not_.is_('completed_at', 'null').execute()

            sessions = sessions_result.data or []

            # Group by date
            from collections import defaultdict
            days_data = defaultdict(lambda: {
                "sessions": 0,
                "modalities": set(),
                "xp": 0
            })

            for session in sessions:
                completed = datetime.fromisoformat(session['completed_at']).date()
                days_data[completed]["sessions"] += 1
                days_data[completed]["modalities"].add(session['modality'])
                days_data[completed]["xp"] += session.get('xp_earned', 0)

            # Get streak info
            streak_result = self.db('streaks').select('current_streak').eq(
                'user_id', str(user_id)
            ).execute()

            current_streak = 0
            if streak_result.data:
                current_streak = streak_result.data[0]['current_streak']

            # Format days
            days = []
            perfect_days = 0
            streak_day = current_streak

            for day in range(1, 32):
                try:
                    curr_date = date(year, month_num, day)
                    if curr_date >= end_date:
                        break

                    data = days_data[curr_date]
                    is_perfect = len(data["modalities"]) == 3
                    if is_perfect:
                        perfect_days += 1

                    days.append({
                        "date": curr_date,
                        "sessions_completed": data["sessions"],
                        "modalities_completed": list(data["modalities"]),
                        "total_xp_earned": data["xp"],
                        "streak_day": streak_day if data["sessions"] > 0 else 0
                    })

                except ValueError:
                    break

            return {
                "user_id": user_id,
                "current_month": month,
                "days": days,
                "current_streak": current_streak,
                "perfect_days": perfect_days
            }

        except Exception as e:
            logger.error(f"Error getting streak calendar: {e}")
            raise
