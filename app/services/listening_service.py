"""
Listening Evaluation Service for managing listening sessions and skill tracking
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from collections import defaultdict
import logging

from app.db.supabase import SupabaseService
from app.services.skill_mastery_service import SkillMasteryService
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class ListeningService(SupabaseService):
    """Service for managing listening-specific sessions and evaluation"""

    def __init__(self):
        super().__init__(use_admin=True)
        self.skill_mastery = SkillMasteryService()
        self.analytics = AnalyticsService()

    async def create_listening_session(
        self,
        user_id: UUID,
        day_code: str,
        audio_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new listening test session

        Args:
            user_id: User UUID
            day_code: Day identifier (day1-day90)
            audio_url: Optional URL to audio file

        Returns:
            Created session data
        """
        try:
            session_data = {
                "user_id": str(user_id),
                "modality": "listening",
                "day_code": day_code,
                "started_at": datetime.now(timezone.utc).isoformat()
            }

            result = self.db("lrg_sessions").insert(session_data).execute()

            if not result.data:
                raise Exception("Failed to create listening session")

            session = result.data[0]

            # Store audio URL if provided (could be in separate metadata table)
            if audio_url:
                # TODO: Store in session metadata or separate audio table
                pass

            logger.info(
                f"Created listening session {session['session_id']} "
                f"for user {user_id}, day {day_code}"
            )

            return {
                **session,
                "audio_url": audio_url
            }

        except Exception as e:
            logger.error(f"Error creating listening session: {e}")
            raise

    async def submit_listening_session(
        self,
        session_id: UUID,
        answers: List[Dict[str, Any]],
        duration_sec: int,
        score_pct: int,
        xp_earned: int,
        audio_replay_count: int = 0,
        completed_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Submit completed listening session with answers and analytics

        Args:
            session_id: Session UUID
            answers: List of answer dictionaries
            duration_sec: Total session duration
            score_pct: Overall score percentage
            xp_earned: XP points earned
            audio_replay_count: Number of times audio was replayed
            completed_at: Completion timestamp

        Returns:
            Submission confirmation with analytics
        """
        try:
            if completed_at is None:
                completed_at = datetime.now(timezone.utc)

            # Update session with completion data
            session_update = self.db('lrg_sessions').update({
                'completed_at': completed_at.isoformat(),
                'duration_sec': duration_sec,
                'score_pct': score_pct,
                'xp_earned': xp_earned
            }).eq('session_id', str(session_id)).execute()

            if not session_update.data:
                raise Exception("Session not found")

            session = session_update.data[0]
            user_id = session['user_id']

            # Prepare answers data with listening-specific fields
            answers_data = [
                {
                    'session_id': str(session_id),
                    'item_id': answer.get('item_id'),
                    'user_answer': answer.get('user_answer'),
                    'correct_answer': answer.get('correct_answer'),
                    'is_correct': answer.get('is_correct'),
                    'time_spent_sec': answer.get('time_spent_sec'),
                    'topic': answer.get('topic'),
                    'skill': answer.get('skill')
                }
                for answer in answers
            ]

            # Insert answers
            self.db('lrg_answers').insert(answers_data).execute()

            # Store listening-specific metadata (audio replay count)
            # TODO: Create separate table for listening metadata if needed
            # For now, we can track it in analytics

            # Calculate analytics
            total_items = len(answers)
            correct_items = sum(1 for a in answers if a.get('is_correct', False))
            accuracy = correct_items / total_items if total_items > 0 else 0

            # Create analytics record
            analytics_result = await self.analytics.create_session_analytics(
                session_id=session_id,
                user_id=UUID(user_id),
                modality="listening",
                day_code=session['day_code'],
                total_items=total_items,
                correct_items=correct_items,
                accuracy=accuracy,
                duration_sec=duration_sec,
                completed_at=completed_at
            )

            # Update streaks
            streak_info = await self.analytics.update_streak(
                user_id=UUID(user_id),
                completed_at=completed_at
            )

            # Award XP
            await self.analytics.award_xp(
                user_id=UUID(user_id),
                amount=xp_earned,
                source='listening_session'
            )

            # Check and award badges
            badges = await self.analytics.check_and_award_badges(
                user_id=UUID(user_id),
                session_data={
                    'modality': 'listening',
                    'accuracy': accuracy,
                    'streak': streak_info['current_streak']
                }
            )

            # Record skill mastery data
            await self.skill_mastery.record_session_skills(
                session_id=session_id,
                answers=answers_data
            )

            # Update cumulative user skill mastery for listening
            await self.skill_mastery.update_user_skill_mastery(
                user_id=UUID(user_id),
                modality="listening",
                session_id=session_id
            )

            logger.info(
                f"Listening session {session_id} submitted: "
                f"score={score_pct}%, streak={streak_info['current_streak']}, "
                f"audio_replays={audio_replay_count}"
            )

            return {
                'session_id': session_id,
                'analytics_recorded': True,
                'xp_awarded': xp_earned,
                'badges_awarded': badges,
                'streak_updated': True,
                'current_streak': streak_info['current_streak'],
                'skill_mastery_recorded': True
            }

        except Exception as e:
            logger.error(f"Error submitting listening session: {e}")
            raise

    async def get_listening_session(
        self,
        session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get detailed listening session information"""
        try:
            # Get session
            session_result = self.db('lrg_sessions').select('*').eq(
                'session_id', str(session_id)
            ).eq('modality', 'listening').execute()

            if not session_result.data:
                return None

            session = session_result.data[0]

            # Get answers
            answers_result = self.db('lrg_answers').select('*').eq(
                'session_id', str(session_id)
            ).execute()

            return {
                **session,
                'answers': answers_result.data,
                'audio_replay_count': 0  # TODO: Get from metadata table
            }

        except Exception as e:
            logger.error(f"Error fetching listening session: {e}")
            raise

    async def get_user_listening_progress(
        self,
        user_id: UUID,
        from_day: Optional[str] = None,
        to_day: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user's listening skill progress across sessions

        Args:
            user_id: User UUID
            from_day: Optional start day
            to_day: Optional end day

        Returns:
            Comprehensive listening progress data
        """
        try:
            # Get skill progress from skill mastery service
            skill_progress = await self.skill_mastery.get_user_skill_progress(
                user_id=user_id,
                modality="listening",
                from_day=from_day,
                to_day=to_day
            )

            # Get listening sessions count
            sessions_result = self.db('lrg_sessions').select('*').eq(
                'user_id', str(user_id)
            ).eq('modality', 'listening').not_.is_('completed_at', 'null')

            if from_day:
                sessions_result = sessions_result.gte('day_code', from_day)
            if to_day:
                sessions_result = sessions_result.lte('day_code', to_day)

            sessions = sessions_result.execute().data or []
            total_sessions = len(sessions)

            # Calculate overall mastery
            overall_mastery = 0
            if skill_progress.get('skills'):
                overall_mastery = int(
                    sum(s['overall_mastery_pct'] for s in skill_progress['skills']) /
                    len(skill_progress['skills'])
                )

            # Calculate average time per question
            for skill in skill_progress.get('skills', []):
                if skill['total_questions'] > 0:
                    # Get listening session IDs for this user
                    sessions_query = self.db('lrg_sessions').select('session_id').eq(
                        'user_id', str(user_id)
                    ).eq('modality', 'listening').execute()

                    session_ids = [s['session_id'] for s in sessions_query.data or []]

                    if session_ids:
                        # Get total time spent on this skill
                        time_result = self.db('lrg_answers').select('time_spent_sec').eq(
                            'skill', skill['skill']
                        ).in_('session_id', session_ids).execute()

                        total_time = sum(
                            a.get('time_spent_sec', 0) for a in time_result.data or []
                        )
                        skill['avg_time_per_question'] = (
                            total_time / skill['total_questions']
                            if skill['total_questions'] > 0 else 0
                        )
                    else:
                        skill['avg_time_per_question'] = 0
                else:
                    skill['avg_time_per_question'] = 0

            return {
                'modality': 'listening',
                'date_range': f"{from_day or 'day1'}-{to_day or 'latest'}",
                'overall_mastery_pct': overall_mastery,
                'total_sessions': total_sessions,
                'total_audio_replay_count': 0,  # TODO: Calculate from metadata
                'skills': skill_progress.get('skills', [])
            }

        except Exception as e:
            logger.error(f"Error getting listening progress: {e}")
            raise

    async def get_listening_analytics(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get comprehensive listening analytics for a user"""
        try:
            # Get all completed listening sessions
            sessions_result = self.db('lrg_sessions').select('*').eq(
                'user_id', str(user_id)
            ).eq('modality', 'listening').not_.is_('completed_at', 'null').execute()

            sessions = sessions_result.data or []

            if not sessions:
                return {
                    'user_id': user_id,
                    'total_sessions': 0,
                    'avg_score_pct': 0,
                    'total_duration_sec': 0,
                    'total_audio_replays': 0,
                    'strongest_skill': None,
                    'weakest_skill': None,
                    'improvement_rate': 0
                }

            # Calculate basic stats
            total_sessions = len(sessions)
            avg_score = sum(s.get('score_pct', 0) for s in sessions) / total_sessions
            total_duration = sum(s.get('duration_sec', 0) for s in sessions)

            # Get skill mastery to find strongest/weakest
            mastery_result = self.db('lrg_skill_mastery').select('*').eq(
                'user_id', str(user_id)
            ).eq('modality', 'listening').execute()

            masteries = mastery_result.data or []
            strongest_skill = max(masteries, key=lambda x: x['mastery_pct'])['skill'] if masteries else None
            weakest_skill = min(masteries, key=lambda x: x['mastery_pct'])['skill'] if masteries else None

            # Calculate improvement rate
            if len(sessions) > 1:
                first_score = sessions[-1].get('score_pct', 0)
                latest_score = sessions[0].get('score_pct', 0)
                improvement_rate = ((latest_score - first_score) / first_score * 100) if first_score > 0 else 0
            else:
                improvement_rate = 0

            return {
                'user_id': user_id,
                'total_sessions': total_sessions,
                'avg_score_pct': avg_score,
                'total_duration_sec': total_duration,
                'total_audio_replays': 0,  # TODO: Get from metadata
                'strongest_skill': strongest_skill,
                'weakest_skill': weakest_skill,
                'improvement_rate': improvement_rate
            }

        except Exception as e:
            logger.error(f"Error getting listening analytics: {e}")
            raise
