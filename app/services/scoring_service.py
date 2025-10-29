"""
Scoring service for language evaluation and assessment
"""

from typing import Dict, Any, Optional
from uuid import UUID
import structlog

from app.domain.models import ScoringResult, ScoringRubric, ScoringWeights, Evaluation
from app.domain.evaluation import language_evaluator
from app.services.supabase_client import get_supabase_client
from app.config import DEFAULT_SCORING_WEIGHTS, DEFAULT_SCORING_SCALES

logger = structlog.get_logger(__name__)


class ScoringService:
    """Service for language scoring and evaluation storage"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.evaluator = language_evaluator
    
    async def score_conversation_turn(
        self, 
        conversation_id: int,
        session_id: UUID,
        user_id: UUID,
        text: str,
        mode_code: str,
        custom_rubric: Optional[Dict[str, Any]] = None
    ) -> Optional[Evaluation]:
        """
        Score a conversation turn and store the evaluation
        
        Args:
            conversation_id: ID of the conversation turn
            session_id: Session UUID
            user_id: User UUID
            text: Text content to evaluate
            mode_code: Teaching mode code
            custom_rubric: Optional custom scoring rubric
            
        Returns:
            Evaluation object if successful, None otherwise
        """
        try:
            # Get teaching mode rubric if not provided
            rubric = None
            if custom_rubric:
                rubric = self._parse_rubric(custom_rubric)
            else:
                rubric = await self._get_mode_rubric(mode_code)
            
            # Perform evaluation
            scoring_result = self.evaluator.evaluate_text(text, rubric, mode_code)
            
            # Prepare metrics for storage
            metrics_dict = {
                "fluency": scoring_result.metrics.fluency,
                "vocabulary": scoring_result.metrics.vocabulary,
                "grammar": scoring_result.metrics.grammar,
                "pronunciation": scoring_result.metrics.pronunciation,
                "feedback": scoring_result.feedback,
                "mode_adjustments": scoring_result.mode_specific_adjustments
            }
            
            # Store evaluation in database
            evaluation_data = {
                "conversation_id": conversation_id,
                "session_id": str(session_id),
                "user_id": str(user_id),
                "mode_code": mode_code,
                "metrics": metrics_dict,
                "total_score": scoring_result.total_score
            }
            
            response = self.supabase.table("evaluations").insert(evaluation_data).execute()
            
            if response.data:
                evaluation_record = response.data[0]
                logger.info("Evaluation stored successfully", 
                          conversation_id=conversation_id,
                          total_score=scoring_result.total_score,
                          mode_code=mode_code)
                
                # Convert to domain model
                return Evaluation(
                    id=evaluation_record["id"],
                    conversation_id=conversation_id,
                    session_id=session_id,
                    user_id=user_id,
                    mode_code=mode_code,
                    metrics=metrics_dict,
                    total_score=scoring_result.total_score,
                    created_at=evaluation_record.get("created_at")
                )
            else:
                logger.error("Failed to store evaluation - no data returned",
                           conversation_id=conversation_id)
                return None
                
        except Exception as e:
            logger.error("Error scoring conversation turn", 
                        conversation_id=conversation_id,
                        error=str(e))
            return None
    
    async def get_session_evaluations(self, session_id: UUID) -> list[Evaluation]:
        """
        Get all evaluations for a session
        
        Args:
            session_id: Session UUID
            
        Returns:
            List of Evaluation objects
        """
        try:
            response = self.supabase.table("evaluations")\
                .select("*")\
                .eq("session_id", str(session_id))\
                .order("created_at")\
                .execute()
            
            evaluations = []
            for record in response.data:
                evaluation = Evaluation(
                    id=record["id"],
                    conversation_id=record["conversation_id"],
                    session_id=UUID(record["session_id"]),
                    user_id=UUID(record["user_id"]),
                    mode_code=record["mode_code"],
                    metrics=record["metrics"],
                    total_score=record["total_score"],
                    created_at=record.get("created_at")
                )
                evaluations.append(evaluation)
            
            logger.debug("Retrieved session evaluations", 
                        session_id=session_id,
                        count=len(evaluations))
            return evaluations
            
        except Exception as e:
            logger.error("Error retrieving session evaluations", 
                        session_id=session_id,
                        error=str(e))
            return []
    
    async def calculate_session_statistics(self, session_id: UUID) -> Dict[str, Any]:
        """
        Calculate aggregate statistics for a session
        
        Args:
            session_id: Session UUID
            
        Returns:
            Dictionary with session statistics
        """
        try:
            evaluations = await self.get_session_evaluations(session_id)
            
            if not evaluations:
                return {
                    "total_turns": 0,
                    "average_score": 0.0,
                    "score_trend": "stable",
                    "strengths": [],
                    "areas_for_improvement": []
                }
            
            # Calculate averages
            total_score = sum(eval.total_score for eval in evaluations)
            avg_score = total_score / len(evaluations)
            
            # Calculate metric averages
            fluency_scores = [eval.metrics.get("fluency", 0) for eval in evaluations]
            vocabulary_scores = [eval.metrics.get("vocabulary", 0) for eval in evaluations]
            grammar_scores = [eval.metrics.get("grammar", 0) for eval in evaluations]
            pronunciation_scores = [eval.metrics.get("pronunciation", 0) for eval in evaluations]
            
            avg_fluency = sum(fluency_scores) / len(fluency_scores)
            avg_vocabulary = sum(vocabulary_scores) / len(vocabulary_scores)
            avg_grammar = sum(grammar_scores) / len(grammar_scores)
            avg_pronunciation = sum(pronunciation_scores) / len(pronunciation_scores)
            
            # Determine score trend
            if len(evaluations) >= 3:
                recent_scores = [eval.total_score for eval in evaluations[-3:]]
                early_scores = [eval.total_score for eval in evaluations[:3]]
                recent_avg = sum(recent_scores) / len(recent_scores)
                early_avg = sum(early_scores) / len(early_scores)
                
                if recent_avg > early_avg + 5:
                    trend = "improving"
                elif recent_avg < early_avg - 5:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
            
            # Identify strengths and weaknesses
            metric_scores = {
                "fluency": avg_fluency,
                "vocabulary": avg_vocabulary,
                "grammar": avg_grammar,
                "pronunciation": avg_pronunciation
            }
            
            sorted_metrics = sorted(metric_scores.items(), key=lambda x: x[1], reverse=True)
            strengths = [metric for metric, score in sorted_metrics[:2] if score >= 3.0]
            areas_for_improvement = [metric for metric, score in sorted_metrics[-2:] if score < 3.0]
            
            return {
                "total_turns": len(evaluations),
                "average_score": round(avg_score, 2),
                "score_trend": trend,
                "metric_averages": {
                    "fluency": round(avg_fluency, 2),
                    "vocabulary": round(avg_vocabulary, 2),
                    "grammar": round(avg_grammar, 2),
                    "pronunciation": round(avg_pronunciation, 2)
                },
                "strengths": strengths,
                "areas_for_improvement": areas_for_improvement,
                "score_distribution": {
                    "excellent": len([e for e in evaluations if e.total_score >= 80]),
                    "good": len([e for e in evaluations if 60 <= e.total_score < 80]),
                    "fair": len([e for e in evaluations if 40 <= e.total_score < 60]),
                    "needs_work": len([e for e in evaluations if e.total_score < 40])
                }
            }
            
        except Exception as e:
            logger.error("Error calculating session statistics", 
                        session_id=session_id,
                        error=str(e))
            return {
                "total_turns": 0,
                "average_score": 0.0,
                "score_trend": "error",
                "error": str(e)
            }
    
    async def _get_mode_rubric(self, mode_code: str) -> Optional[ScoringRubric]:
        """
        Get scoring rubric for a teaching mode
        
        Args:
            mode_code: Teaching mode code
            
        Returns:
            ScoringRubric if found, None otherwise
        """
        try:
            response = self.supabase.table("teaching_modes")\
                .select("rubric")\
                .eq("code", mode_code)\
                .execute()
            
            if response.data:
                rubric_data = response.data[0]["rubric"]
                return self._parse_rubric(rubric_data)
            else:
                # Return default rubric
                return ScoringRubric(
                    weights=ScoringWeights(**DEFAULT_SCORING_WEIGHTS),
                    scales=DEFAULT_SCORING_SCALES
                )
                
        except Exception as e:
            logger.error("Error getting mode rubric", 
                        mode_code=mode_code,
                        error=str(e))
            # Return default rubric on error
            return ScoringRubric(
                weights=ScoringWeights(**DEFAULT_SCORING_WEIGHTS),
                scales=DEFAULT_SCORING_SCALES
            )
    
    def _parse_rubric(self, rubric_data: Dict[str, Any]) -> ScoringRubric:
        """
        Parse rubric data into ScoringRubric object
        
        Args:
            rubric_data: Raw rubric data from database
            
        Returns:
            ScoringRubric object
        """
        try:
            weights_data = rubric_data.get("weights", DEFAULT_SCORING_WEIGHTS)
            scales_data = rubric_data.get("scales", DEFAULT_SCORING_SCALES)
            guidelines_data = rubric_data.get("guidelines", {})
            
            weights = ScoringWeights(**weights_data)
            
            return ScoringRubric(
                weights=weights,
                scales=scales_data,
                guidelines=guidelines_data
            )
            
        except Exception as e:
            logger.error("Error parsing rubric data", error=str(e))
            # Return default rubric on parsing error
            return ScoringRubric(
                weights=ScoringWeights(**DEFAULT_SCORING_WEIGHTS),
                scales=DEFAULT_SCORING_SCALES
            )
    
    async def get_user_progress_summary(self, user_id: UUID, limit: int = 10) -> Dict[str, Any]:
        """
        Get progress summary for a user across recent sessions
        
        Args:
            user_id: User UUID
            limit: Number of recent evaluations to consider
            
        Returns:
            User progress summary
        """
        try:
            response = self.supabase.table("evaluations")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            if not response.data:
                return {
                    "user_id": str(user_id),
                    "total_evaluations": 0,
                    "recent_average": 0.0,
                    "progress_trend": "no_data"
                }
            
            evaluations = response.data
            scores = [eval["total_score"] for eval in evaluations]
            recent_avg = sum(scores) / len(scores)
            
            # Calculate trend
            if len(scores) >= 5:
                recent_half = scores[:len(scores)//2]
                older_half = scores[len(scores)//2:]
                recent_score_avg = sum(recent_half) / len(recent_half)
                older_score_avg = sum(older_half) / len(older_half)
                
                if recent_score_avg > older_score_avg + 5:
                    trend = "improving"
                elif recent_score_avg < older_score_avg - 5:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
            
            return {
                "user_id": str(user_id),
                "total_evaluations": len(evaluations),
                "recent_average": round(recent_avg, 2),
                "progress_trend": trend,
                "best_score": max(scores),
                "most_recent_score": scores[0] if scores else 0
            }
            
        except Exception as e:
            logger.error("Error getting user progress summary", 
                        user_id=user_id,
                        error=str(e))
            return {
                "user_id": str(user_id),
                "error": str(e)
            }


# Global scoring service instance
scoring_service = ScoringService()