"""
Session service for managing test sessions and submissions
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

from app.db.supabase import SupabaseService
from app.models.sessions import SessionStart, SessionSubmit, SessionDetail
from app.services.analytics_service import AnalyticsService
from app.services.skill_mastery_service import SkillMasteryService

logger = logging.getLogger(__name__)
# session_service.py
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timezone




"""
Session service for managing test sessions and submissions
"""
from typing import Dict, Any, Optional, List
logger = logging.getLogger(__name__)


class SessionService(SupabaseService):
    """Service for managing sessions"""
    
    def __init__(self):
        super().__init__(use_admin=True)  # Must be True
        self.analytics = AnalyticsService()
        self.skill_mastery = SkillMasteryService()
        
    async def create_session(self, data: SessionStart) -> Dict[str, Any]:
        """Create a new test session"""
        try:
            payload = jsonable_encoder(data, exclude_none=True)
            payload.setdefault("started_at", datetime.now(timezone.utc).isoformat())

            result = self.db("lrg_sessions").insert({
                "user_id": payload["user_id"],
                "modality": payload["modality"],
                "day_code": payload["day_code"],
                "started_at": payload["started_at"]
            }).execute()
            
            if not result.data:
                raise Exception("Failed to create session")
            
            session = result.data[0]
            logger.info(f"Created session {session['session_id']} for user {data.user_id}")
            
            return session
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    async def submit_session(
        self,
        session_id: UUID,
        data: SessionSubmit
    ) -> Dict[str, Any]:
        """
        Submit completed session with answers
        Triggers analytics, XP, streaks, and badges
        """
        try:
            # Update session with completion data
            session_update = self.db('lrg_sessions').update({
                'completed_at': data.completed_at.isoformat(),
                'duration_sec': data.duration_sec,
                'score_pct': data.score_pct,
                'xp_earned': data.xp_earned
            }).eq('session_id', str(session_id)).execute()
            
            if not session_update.data:
                raise Exception("Session not found")
            
            session = session_update.data[0]
            user_id = session['user_id']
            
            # Insert answers in bulk
            answers_data = [
                {
                    'session_id': str(session_id),
                    'item_id': answer.item_id,
                    'user_answer': answer.user_answer,
                    'correct_answer': answer.correct_answer,
                    'is_correct': answer.is_correct,
                    'time_spent_sec': answer.time_spent_sec,
                    'topic': answer.topic,
                    'skill': answer.skill
                }
                for answer in data.answers
            ]
            
            self.db('lrg_answers').insert(answers_data).execute()
            
            # Calculate analytics
            total_items = len(data.answers)
            correct_items = sum(1 for a in data.answers if a.is_correct)
            accuracy = correct_items / total_items if total_items > 0 else 0
            
            # Create analytics record
            analytics_result = await self.analytics.create_session_analytics(
                session_id=session_id,
                user_id=UUID(user_id),
                modality=session['modality'],
                day_code=session['day_code'],
                total_items=total_items,
                correct_items=correct_items,
                accuracy=accuracy,
                duration_sec=data.duration_sec,
                completed_at=data.completed_at
            )
            
            # Update streaks
            streak_info = await self.analytics.update_streak(
                user_id=UUID(user_id),
                completed_at=data.completed_at
            )
            
            # Award XP
            await self.analytics.award_xp(
                user_id=UUID(user_id),
                amount=data.xp_earned,
                source='session'
            )
            
            # Check and award badges
            badges = await self.analytics.check_and_award_badges(
                user_id=UUID(user_id),
                session_data={
                    'modality': session['modality'],
                    'accuracy': accuracy,
                    'streak': streak_info['current_streak']
                }
            )

            # Record skill mastery data
            await self.skill_mastery.record_session_skills(
                session_id=session_id,
                answers=answers_data
            )

            # Update cumulative user skill mastery
            await self.skill_mastery.update_user_skill_mastery(
                user_id=UUID(user_id),
                modality=session['modality'],
                session_id=session_id
            )

            logger.info(
                f"Session {session_id} submitted: "
                f"score={data.score_pct}%, streak={streak_info['current_streak']}"
            )
            
            return {
                'session_id': session_id,
                'analytics_recorded': True,
                'xp_awarded': data.xp_earned,
                'badges_awarded': badges,
                'streak_updated': True,
                'current_streak': streak_info['current_streak']
            }
            
        except Exception as e:
            logger.error(f"Error submitting session: {e}")
            raise
    
    async def get_session(self, session_id: UUID) -> Optional[SessionDetail]:
        """Get detailed session information"""
        try:
            # Get session
            session_result = self.db('lrg_sessions').select('*').eq(
                'session_id', str(session_id)
            ).execute()
            
            if not session_result.data:
                return None
            
            session = session_result.data[0]
            
            # Get answers
            answers_result = self.db('lrg_answers').select('*').eq(
                'session_id', str(session_id)
            ).execute()
            
            return SessionDetail(
                session_id=session['session_id'],
                user_id=session['user_id'],
                modality=session['modality'],
                day_code=session['day_code'],
                started_at=session['started_at'],
                completed_at=session.get('completed_at'),
                duration_sec=session.get('duration_sec'),
                score_pct=session.get('score_pct'),
                xp_earned=session.get('xp_earned', 0),
                answers=answers_result.data
            )
            
        except Exception as e:
            logger.error(f"Error fetching session: {e}")
            raise
    
    async def get_user_sessions(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's session history"""
        try:
            result = self.db('lrg_sessions').select('*').eq(
                'user_id', str(user_id)
            ).order('started_at', desc=True).range(
                offset, offset + limit - 1
            ).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error fetching user sessions: {e}")
            raise