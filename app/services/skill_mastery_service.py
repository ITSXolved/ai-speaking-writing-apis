"""
Skill Mastery Service for tracking and calculating skill-level performance
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from collections import defaultdict
import logging

from app.db.supabase import SupabaseService

logger = logging.getLogger(__name__)


class SkillMasteryService(SupabaseService):
    """Service for managing skill mastery tracking and calculations"""

    # Mastery level thresholds
    MASTERY_LEVELS = {
        "beginner": (0, 49),
        "developing": (50, 74),
        "proficient": (75, 89),
        "advanced": (90, 100)
    }

    def __init__(self):
        super().__init__(use_admin=True)

    def calculate_mastery_level(self, mastery_pct: int) -> str:
        """Calculate mastery level based on percentage"""
        for level, (min_pct, max_pct) in self.MASTERY_LEVELS.items():
            if min_pct <= mastery_pct <= max_pct:
                return level
        return "beginner"

    async def record_session_skills(
        self,
        session_id: UUID,
        answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate and record skill breakdown for a session

        Args:
            session_id: Session UUID
            answers: List of answer dictionaries with skill information

        Returns:
            Dictionary with skill breakdown data
        """
        try:
            # Aggregate skills from answers
            skill_stats = defaultdict(lambda: {"correct": 0, "total": 0})

            for answer in answers:
                skill = answer.get("skill")
                if skill:
                    skill_stats[skill]["total"] += 1
                    if answer.get("is_correct", False):
                        skill_stats[skill]["correct"] += 1

            # Calculate mastery and prepare records
            session_skills = []
            for skill, stats in skill_stats.items():
                mastery_pct = int((stats["correct"] / stats["total"]) * 100)
                mastery_level = self.calculate_mastery_level(mastery_pct)

                session_skills.append({
                    "session_id": str(session_id),
                    "skill": skill,
                    "correct": stats["correct"],
                    "total": stats["total"],
                    "mastery_pct": mastery_pct,
                    "mastery_level": mastery_level
                })

            # Insert session skill records
            if session_skills:
                self.db("lrg_session_skills").insert(session_skills).execute()

            logger.info(f"Recorded {len(session_skills)} skills for session {session_id}")

            return {
                "skills_recorded": len(session_skills),
                "skill_breakdown": session_skills
            }

        except Exception as e:
            logger.error(f"Error recording session skills: {e}")
            raise

    async def update_user_skill_mastery(
        self,
        user_id: UUID,
        modality: str,
        session_id: UUID
    ) -> Dict[str, Any]:
        """
        Update cumulative skill mastery for user based on new session

        Args:
            user_id: User UUID
            modality: listening, reading, or grammar
            session_id: Session UUID

        Returns:
            Updated mastery data
        """
        try:
            # Get all session IDs for this user/modality
            sessions_query = self.db("lrg_sessions").select("session_id").eq(
                "user_id", str(user_id)
            ).eq("modality", modality).execute()

            session_ids = [s["session_id"] for s in sessions_query.data or []]

            if not session_ids:
                return {"skills_updated": 0}

            # Get all answers for this user/modality with skills
            answers_result = self.db("lrg_answers").select(
                "skill, is_correct"
            ).in_("session_id", session_ids).not_.is_("skill", "null").execute()

            if not answers_result.data:
                return {"skills_updated": 0}

            # Aggregate all historical data
            skill_stats = defaultdict(lambda: {"correct": 0, "total": 0})
            for answer in answers_result.data:
                skill = answer["skill"]
                skill_stats[skill]["total"] += 1
                if answer["is_correct"]:
                    skill_stats[skill]["correct"] += 1

            # Upsert user skill mastery records
            mastery_records = []
            for skill, stats in skill_stats.items():
                mastery_pct = int((stats["correct"] / stats["total"]) * 100)

                mastery_records.append({
                    "user_id": str(user_id),
                    "modality": modality,
                    "skill": skill,
                    "total_attempts": stats["total"],
                    "correct_attempts": stats["correct"],
                    "mastery_pct": mastery_pct,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                })

            # Use upsert to update existing records or insert new ones
            if mastery_records:
                self.db("lrg_skill_mastery").upsert(
                    mastery_records,
                    on_conflict="user_id,modality,skill"
                ).execute()

            logger.info(
                f"Updated {len(mastery_records)} skill mastery records "
                f"for user {user_id}, modality {modality}"
            )

            return {
                "skills_updated": len(mastery_records),
                "mastery_data": mastery_records
            }

        except Exception as e:
            logger.error(f"Error updating user skill mastery: {e}")
            raise

    async def get_session_mastery(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get skill mastery breakdown for a specific session"""
        try:
            # Get session info
            session_result = self.db("lrg_sessions").select("*").eq(
                "session_id", str(session_id)
            ).execute()

            if not session_result.data:
                return None

            session = session_result.data[0]

            # Get skill breakdown
            skills_result = self.db("lrg_session_skills").select("*").eq(
                "session_id", str(session_id)
            ).execute()

            skills = skills_result.data

            # Count mastery levels
            mastery_levels = {"beginner": 0, "developing": 0, "proficient": 0, "advanced": 0}
            for skill in skills:
                level = skill["mastery_level"]
                mastery_levels[level] += 1

            return {
                "session_id": session_id,
                "modality": session["modality"],
                "day_code": session["day_code"],
                "overall_score_pct": session.get("score_pct", 0),
                "duration_sec": session.get("duration_sec", 0),
                "skills": skills,
                "mastery_levels": mastery_levels
            }

        except Exception as e:
            logger.error(f"Error getting session mastery: {e}")
            raise

    async def get_user_skill_progress(
        self,
        user_id: UUID,
        modality: str,
        from_day: Optional[str] = None,
        to_day: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user's skill progress for a modality, optionally filtered by day range"""
        try:
            # Get current mastery data
            mastery_result = self.db("lrg_skill_mastery").select("*").eq(
                "user_id", str(user_id)
            ).eq("modality", modality).execute()

            if not mastery_result.data:
                return {
                    "modality": modality,
                    "date_range": f"{from_day or 'day1'}-{to_day or 'latest'}",
                    "skills": []
                }

            # Calculate trend (simplified: compare recent vs older sessions)
            skills = []
            for mastery in mastery_result.data:
                # For now, trend is "stable" - can enhance with historical comparison
                skill_detail = {
                    "skill": mastery["skill"],
                    "sessions_practiced": self._count_sessions_with_skill(
                        user_id, modality, mastery["skill"]
                    ),
                    "total_questions": mastery["total_attempts"],
                    "correct_answers": mastery["correct_attempts"],
                    "overall_mastery_pct": mastery["mastery_pct"],
                    "mastery_level": self.calculate_mastery_level(mastery["mastery_pct"]),
                    "trend": "stable"  # TODO: Implement trend analysis
                }
                skills.append(skill_detail)

            return {
                "modality": modality,
                "date_range": f"{from_day or 'day1'}-{to_day or 'latest'}",
                "skills": skills
            }

        except Exception as e:
            logger.error(f"Error getting user skill progress: {e}")
            raise

    def _count_sessions_with_skill(
        self,
        user_id: UUID,
        modality: str,
        skill: str
    ) -> int:
        """Count how many sessions included this skill"""
        try:
            # Get session IDs for this user/modality
            sessions_query = self.db("lrg_sessions").select("session_id").eq(
                "user_id", str(user_id)
            ).eq("modality", modality).execute()

            session_ids = [s["session_id"] for s in sessions_query.data or []]

            if not session_ids:
                return 0

            # Get distinct session IDs with this skill
            result = self.db("lrg_session_skills").select(
                "session_id"
            ).in_("session_id", session_ids).eq("skill", skill).execute()

            return len(result.data) if result.data else 0

        except Exception as e:
            logger.error(f"Error counting sessions with skill: {e}")
            return 0

    async def get_mastery_overview(self, user_id: UUID) -> Dict[str, Any]:
        """Get complete mastery overview across all modalities"""
        try:
            overview = {
                "user_id": user_id,
                "listening": {"overall_mastery_pct": 0, "skills": {}},
                "reading": {"overall_mastery_pct": 0, "skills": {}},
                "grammar": {"overall_mastery_pct": 0, "skills": {}}
            }

            # Get all mastery data for user
            mastery_result = self.db("lrg_skill_mastery").select("*").eq(
                "user_id", str(user_id)
            ).execute()

            if not mastery_result.data:
                return overview

            # Group by modality
            for mastery in mastery_result.data:
                modality = mastery["modality"]
                skill = mastery["skill"]
                mastery_pct = mastery["mastery_pct"]

                overview[modality]["skills"][skill] = mastery_pct

            # Calculate overall mastery per modality
            for modality in ["listening", "reading", "grammar"]:
                skills = overview[modality]["skills"]
                if skills:
                    overview[modality]["overall_mastery_pct"] = int(
                        sum(skills.values()) / len(skills)
                    )

            return overview

        except Exception as e:
            logger.error(f"Error getting mastery overview: {e}")
            raise

    async def get_competencies_by_day(
        self,
        user_id: UUID,
        modality: str,
        day_code: str
    ) -> Dict[str, Any]:
        """
        Get skill competencies for a specific modality and day

        Args:
            user_id: User UUID
            modality: listening, reading, or grammar
            day_code: Specific day (e.g., "day1", "day5")

        Returns:
            Dictionary with skill breakdown for that specific day
        """
        try:
            # Get all sessions for this user/modality/day
            sessions_query = self.db("lrg_sessions").select("session_id").eq(
                "user_id", str(user_id)
            ).eq("modality", modality).eq("day_code", day_code).execute()

            session_ids = [s["session_id"] for s in sessions_query.data or []]

            if not session_ids:
                return {
                    "modality": modality,
                    "date_range": day_code,
                    "skills": []
                }

            # Get all answers for these sessions with skills
            answers_result = self.db("lrg_answers").select(
                "skill, is_correct, time_spent_sec"
            ).in_("session_id", session_ids).not_.is_("skill", "null").execute()

            if not answers_result.data:
                return {
                    "modality": modality,
                    "date_range": day_code,
                    "skills": []
                }

            # Aggregate skill stats for this day
            skill_stats = defaultdict(lambda: {
                "correct": 0,
                "total": 0,
                "total_time": 0,
                "sessions": set()
            })

            for answer in answers_result.data:
                skill = answer["skill"]
                skill_stats[skill]["total"] += 1
                skill_stats[skill]["total_time"] += answer.get("time_spent_sec", 0)
                if answer["is_correct"]:
                    skill_stats[skill]["correct"] += 1

            # Get session count per skill for this day
            for session_id in session_ids:
                skill_result = self.db("lrg_session_skills").select(
                    "skill"
                ).eq("session_id", session_id).execute()

                for skill_record in skill_result.data or []:
                    skill = skill_record["skill"]
                    if skill in skill_stats:
                        skill_stats[skill]["sessions"].add(session_id)

            # Build skill details
            skills = []
            for skill, stats in skill_stats.items():
                mastery_pct = int((stats["correct"] / stats["total"]) * 100) if stats["total"] > 0 else 0
                avg_time = stats["total_time"] / stats["total"] if stats["total"] > 0 else 0

                skill_detail = {
                    "skill": skill,
                    "sessions_practiced": len(stats["sessions"]),
                    "total_questions": stats["total"],
                    "correct_answers": stats["correct"],
                    "overall_mastery_pct": mastery_pct,
                    "mastery_level": self.calculate_mastery_level(mastery_pct),
                    "trend": "stable",  # For single day, trend is always stable
                    "avg_time_per_question": round(avg_time, 1)
                }
                skills.append(skill_detail)

            # Sort by skill name for consistency
            skills.sort(key=lambda x: x["skill"])

            return {
                "modality": modality,
                "date_range": day_code,
                "skills": skills
            }

        except Exception as e:
            logger.error(f"Error getting competencies by day: {e}")
            raise
