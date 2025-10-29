"""
Competency Service
Handles saving and retrieving speaking/writing evaluations with day_code tracking
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime

from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class CompetencyService:
    """Service for managing user competency tracking with day codes"""

    def __init__(self):
        """Initialize the competency service"""
        self.supabase = get_supabase_client()

    async def save_speaking_evaluation(
        self,
        user_id: UUID,
        session_id: UUID,
        day_code: str,
        language: str,
        user_level: str,
        total_turns: int,
        scores: Dict[str, int],
        strengths: List[str],
        improvements: List[str],
        suggestions: List[str],
        conversation_summary: str,
        overall_score: int,
        feedback_summary: str,
        fluency_level: str,
        vocabulary_range: str
    ) -> Dict[str, Any]:
        """
        Save speaking evaluation to database with day_code

        Returns:
            Dictionary with evaluation_id and success status
        """
        try:
            data = {
                "user_id": str(user_id),
                "session_id": str(session_id),
                "day_code": day_code,
                "language": language,
                "user_level": user_level,
                "total_turns": total_turns,
                "scores": scores,
                "strengths": strengths,
                "improvements": improvements,
                "suggestions": suggestions,
                "conversation_summary": conversation_summary,
                "overall_score": overall_score,
                "feedback_summary": feedback_summary,
                "fluency_level": fluency_level,
                "vocabulary_range": vocabulary_range,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            response = self.supabase.table("speaking_evaluations").insert(data).execute()

            if response.data:
                evaluation_id = response.data[0]["id"]
                logger.info(f"Saved speaking evaluation {evaluation_id} for user {user_id}, day {day_code}")
                return {
                    "success": True,
                    "evaluation_id": evaluation_id,
                    "day_code": day_code,
                    "overall_score": overall_score
                }
            else:
                raise Exception("No data returned from insert")

        except Exception as e:
            logger.error(f"Error saving speaking evaluation: {str(e)}")
            raise Exception(f"Failed to save speaking evaluation: {str(e)}")

    async def save_writing_evaluation(
        self,
        user_id: str,
        day_code: str,
        original_text: str,
        language: str,
        writing_type: str,
        user_level: str,
        scores: Dict[str, int],
        strengths: List[str],
        improvements: List[str],
        suggestions: List[str],
        improved_version: str,
        overall_score: int,
        feedback_summary: str
    ) -> Dict[str, Any]:
        """
        Save writing evaluation to database with day_code

        Returns:
            Dictionary with evaluation_id and success status
        """
        try:
            data = {
                "user_id": user_id,
                "day_code": day_code,
                "original_text": original_text,
                "language": language,
                "writing_type": writing_type,
                "user_level": user_level,
                "scores": scores,
                "strengths": strengths,
                "improvements": improvements,
                "suggestions": suggestions,
                "improved_version": improved_version,
                "overall_score": overall_score,
                "feedback_summary": feedback_summary,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            response = self.supabase.table("writing_evaluations").insert(data).execute()

            if response.data:
                evaluation_id = response.data[0]["id"]
                logger.info(f"Saved writing evaluation {evaluation_id} for user {user_id}, day {day_code}")
                return {
                    "success": True,
                    "evaluation_id": evaluation_id,
                    "day_code": day_code,
                    "overall_score": overall_score
                }
            else:
                raise Exception("No data returned from insert")

        except Exception as e:
            logger.error(f"Error saving writing evaluation: {str(e)}")
            raise Exception(f"Failed to save writing evaluation: {str(e)}")

    async def get_user_competency(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's competency across all days

        Args:
            user_id: User ID (can be UUID string or text)

        Returns:
            Dictionary with user progress across days
        """
        try:
            # Get all study days
            days_response = self.supabase.table("study_days")\
                .select("day_code")\
                .eq("is_active", True)\
                .order("day_code")\
                .execute()

            all_days = [d["day_code"] for d in days_response.data] if days_response.data else []

            # Try to get speaking evaluations (user_id is UUID in this table)
            # Select ALL fields including scores
            speaking_response = None
            try:
                speaking_response = self.supabase.table("speaking_evaluations")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .execute()
            except Exception as e:
                # If UUID parsing fails, speaking evaluations might not exist for this user
                logger.info(f"No speaking evaluations found for user {user_id}: {str(e)}")
                speaking_response = type('obj', (object,), {'data': None})()

            # Get writing evaluations (user_id is text in this table)
            # Select ALL fields including scores
            writing_response = self.supabase.table("writing_evaluations")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()

            # Build progress by day
            speaking_by_day = {}
            if speaking_response.data:
                for eval in speaking_response.data:
                    day = eval["day_code"]
                    if day not in speaking_by_day or eval["created_at"] > speaking_by_day[day]["created_at"]:
                        speaking_by_day[day] = eval

            writing_by_day = {}
            if writing_response.data:
                for eval in writing_response.data:
                    day = eval["day_code"]
                    if day not in writing_by_day or eval["created_at"] > writing_by_day[day]["created_at"]:
                        writing_by_day[day] = eval

            # Build progress list
            progress_by_day = []
            days_completed = 0
            speaking_scores = []
            writing_scores = []

            for day_code in all_days:
                speaking_eval = speaking_by_day.get(day_code)
                writing_eval = writing_by_day.get(day_code)

                speaking_completed = speaking_eval is not None
                writing_completed = writing_eval is not None

                if speaking_completed and writing_completed:
                    days_completed += 1

                if speaking_eval:
                    speaking_scores.append(speaking_eval["overall_score"])

                if writing_eval:
                    writing_scores.append(writing_eval["overall_score"])

                # Build complete day data with ALL evaluation details
                day_data = {
                    "day_code": day_code,
                    "speaking_completed": speaking_completed,
                    "writing_completed": writing_completed,
                    "speaking_score": speaking_eval["overall_score"] if speaking_eval else None,
                    "writing_score": writing_eval["overall_score"] if writing_eval else None,
                    "speaking_evaluation_id": speaking_eval["id"] if speaking_eval else None,
                    "writing_evaluation_id": writing_eval["id"] if writing_eval else None,
                    "completed_at": max(
                        speaking_eval["created_at"] if speaking_eval else "",
                        writing_eval["created_at"] if writing_eval else ""
                    ) or None
                }

                # Add full speaking evaluation data if exists
                if speaking_eval:
                    day_data["speaking_evaluation"] = {
                        "id": speaking_eval.get("id"),
                        "scores": speaking_eval.get("scores", {}),  # Category scores
                        "overall_score": speaking_eval.get("overall_score"),
                        "strengths": speaking_eval.get("strengths", []),
                        "improvements": speaking_eval.get("improvements", []),
                        "suggestions": speaking_eval.get("suggestions", []),
                        "conversation_summary": speaking_eval.get("conversation_summary"),
                        "feedback_summary": speaking_eval.get("feedback_summary"),
                        "fluency_level": speaking_eval.get("fluency_level"),
                        "vocabulary_range": speaking_eval.get("vocabulary_range"),
                        "total_turns": speaking_eval.get("total_turns"),
                        "language": speaking_eval.get("language"),
                        "user_level": speaking_eval.get("user_level"),
                        "created_at": speaking_eval.get("created_at"),
                        "updated_at": speaking_eval.get("updated_at")
                    }
                else:
                    day_data["speaking_evaluation"] = None

                # Add full writing evaluation data if exists
                if writing_eval:
                    day_data["writing_evaluation"] = {
                        "id": writing_eval.get("id"),
                        "scores": writing_eval.get("scores", {}),  # Category scores
                        "overall_score": writing_eval.get("overall_score"),
                        "strengths": writing_eval.get("strengths", []),
                        "improvements": writing_eval.get("improvements", []),
                        "suggestions": writing_eval.get("suggestions", []),
                        "original_text": writing_eval.get("original_text"),
                        "improved_version": writing_eval.get("improved_version"),
                        "feedback_summary": writing_eval.get("feedback_summary"),
                        "language": writing_eval.get("language"),
                        "writing_type": writing_eval.get("writing_type"),
                        "user_level": writing_eval.get("user_level"),
                        "created_at": writing_eval.get("created_at"),
                        "updated_at": writing_eval.get("updated_at")
                    }
                else:
                    day_data["writing_evaluation"] = None

                progress_by_day.append(day_data)

            return {
                "user_id": user_id,
                "total_days_available": len(all_days),
                "days_completed": days_completed,
                "progress_by_day": progress_by_day,
                "average_speaking_score": sum(speaking_scores) / len(speaking_scores) if speaking_scores else None,
                "average_writing_score": sum(writing_scores) / len(writing_scores) if writing_scores else None
            }

        except Exception as e:
            logger.error(f"Error getting user competency: {str(e)}")
            raise Exception(f"Failed to get user competency: {str(e)}")

    async def get_day_stats(self, day_code: str) -> Dict[str, Any]:
        """
        Get statistics for a specific day across all users

        Args:
            day_code: Day code (e.g., day1, day2)

        Returns:
            Dictionary with day statistics
        """
        try:
            # Get speaking evaluations for this day
            speaking_response = self.supabase.table("speaking_evaluations")\
                .select("user_id, overall_score, created_at")\
                .eq("day_code", day_code)\
                .execute()

            # Get writing evaluations for this day
            writing_response = self.supabase.table("writing_evaluations")\
                .select("user_id, overall_score, created_at")\
                .eq("day_code", day_code)\
                .execute()

            users_attempted = set()
            speaking_scores = []
            writing_scores = []

            if speaking_response.data:
                for eval in speaking_response.data:
                    users_attempted.add(eval["user_id"])
                    speaking_scores.append(eval["overall_score"])

            if writing_response.data:
                for eval in writing_response.data:
                    users_attempted.add(eval["user_id"])
                    writing_scores.append(eval["overall_score"])

            # Get top performers (users who completed both)
            speaking_by_user = {e["user_id"]: e["overall_score"] for e in (speaking_response.data or [])}
            writing_by_user = {e["user_id"]: e["overall_score"] for e in (writing_response.data or [])}

            top_performers = []
            for user_id in users_attempted:
                if user_id in speaking_by_user and user_id in writing_by_user:
                    combined_score = (speaking_by_user[user_id] + writing_by_user[user_id]) / 2
                    top_performers.append({
                        "user_id": user_id,
                        "speaking_score": speaking_by_user[user_id],
                        "writing_score": writing_by_user[user_id],
                        "combined_score": round(combined_score, 2)
                    })

            # Sort by combined score
            top_performers.sort(key=lambda x: x["combined_score"], reverse=True)
            top_performers = top_performers[:10]  # Top 10

            return {
                "day_code": day_code,
                "total_users_attempted": len(users_attempted),
                "speaking_completions": len(speaking_scores),
                "writing_completions": len(writing_scores),
                "average_speaking_score": round(sum(speaking_scores) / len(speaking_scores), 2) if speaking_scores else None,
                "average_writing_score": round(sum(writing_scores) / len(writing_scores), 2) if writing_scores else None,
                "top_performers": top_performers
            }

        except Exception as e:
            logger.error(f"Error getting day stats: {str(e)}")
            raise Exception(f"Failed to get day stats: {str(e)}")


# Singleton instance
_competency_service = None


def get_competency_service() -> CompetencyService:
    """Get or create the competency service singleton"""
    global _competency_service
    if _competency_service is None:
        _competency_service = CompetencyService()
    return _competency_service
