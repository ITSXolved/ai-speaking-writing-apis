
# """
# Summary service for generating and storing session learning summaries
# Enhanced with email reports and writing evaluation integration
# """


"""
Summary service for generating and storing session learning summaries
Enhanced with skill scores and email reports
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from collections import Counter
import structlog

from app.domain.models import SessionSummary, SessionSummarySchema
from app.services.supabase_client import get_supabase_client
from app.services.conversation_service import conversation_service
from app.services.scoring_service import scoring_service

logger = structlog.get_logger(__name__)


class SummaryService:
    """Service for generating and managing session summaries"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.conversation_service = conversation_service
        self.scoring_service = scoring_service
    
    async def generate_and_store_summary(
        self,
        session_id: UUID,
        user_id: UUID
    ) -> Optional[SessionSummary]:
        """
        Generate a learning summary for a session and store it
        
        Args:
            session_id: Session UUID
            user_id: User UUID
            
        Returns:
            SessionSummary object if successful, None otherwise
        """
        try:
            # Get session information
            session_info = await self._get_session_info(session_id)
            if not session_info:
                logger.error("Session not found for summary generation", session_id=session_id)
                return None
            
            # Get conversation history
            conversations = await self.conversation_service.get_session_conversations(
                session_id=session_id,
                limit=1000  # Get all conversations
            )
            
            # Get scoring statistics
            session_stats = await self.scoring_service.calculate_session_statistics(session_id)
            
            # Generate summary content with skill scores
            summary_json = await self._generate_summary_content(
                session_info=session_info,
                conversations=conversations,
                session_stats=session_stats
            )
            
            # Store summary in database
            summary_data = {
                "session_id": str(session_id),
                "user_id": str(user_id),
                "summary_json": summary_json
            }
            
            response = self.supabase.table("session_summaries").insert(summary_data).execute()
            
            if response.data:
                summary_record = response.data[0]
                logger.info("Session summary generated and stored", 
                          session_id=session_id,
                          summary_id=summary_record["id"])
                
                return SessionSummary(
                    id=UUID(summary_record["id"]),
                    session_id=session_id,
                    user_id=user_id,
                    summary_json=summary_json,
                    created_at=summary_record.get("created_at")
                )
            else:
                logger.error("Failed to store session summary", session_id=session_id)
                return None
                
        except Exception as e:
            logger.error("Error generating session summary", 
                        session_id=session_id,
                        error=str(e))
            return None
    
    async def _generate_summary_content(
        self,
        session_info: Dict[str, Any],
        conversations: List[Dict[str, Any]],
        session_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate the actual summary content following the required schema with skill scores
        
        Args:
            session_info: Session information
            conversations: List of conversation turns
            session_stats: Session statistics
            
        Returns:
            Summary JSON following SessionSummarySchema with skill scores
        """
        try:
            # Extract session details
            mode_info = session_info.get("teaching_modes", {})
            language_info = session_info.get("supported_languages", {})
            mode_name = mode_info.get("name", "Unknown Mode")
            language_label = language_info.get("label", "Unknown Language")
            
            # Create title
            session_short_id = str(session_info["id"])[:8]
            title = f"Session {session_short_id} Study Notes — {language_label} ({mode_name})"
            
            # Extract user conversations (for content analysis)
            user_conversations = [
                conv for conv in conversations 
                if conv["role"] == "user" and conv["text"].strip()
            ]
            
            # Calculate skill scores (convert from 5-point scale to 100-point scale)
            skill_scores = self._calculate_skill_scores(session_stats, user_conversations)
            
            # Generate content sections
            key_phrases = self._extract_key_phrases(user_conversations)
            grammar_corrections = self._extract_grammar_points(
                user_conversations, session_stats
            )
            pronunciation_tips = self._generate_pronunciation_tips(
                user_conversations, session_stats, language_label
            )
            next_steps = self._generate_next_steps(
                session_stats, mode_name, language_label
            )
            
            # Build summary according to required schema with skill scores
            summary = {
                "title": title,
                "skill_scores": skill_scores,  # NEW: Add skill scores
                "subtitle": {
                    "0": {
                        "heading": "Key Phrases Practiced",
                        "points": {str(i): phrase for i, phrase in enumerate(key_phrases)}
                    },
                    "1": {
                        "heading": "Grammar & Corrections",
                        "points": {str(i): correction for i, correction in enumerate(grammar_corrections)}
                    },
                    "2": {
                        "heading": "Pronunciation / Fluency Tips",
                        "points": {str(i): tip for i, tip in enumerate(pronunciation_tips)}
                    },
                    "3": {
                        "heading": "Next Steps",
                        "points": {str(i): step for i, step in enumerate(next_steps)}
                    }
                }
            }
            
            # Validate against schema
            validated_summary = SessionSummarySchema(**summary)
            return validated_summary.dict()
            
        except Exception as e:
            logger.error("Error generating summary content", error=str(e))
            # Return minimal valid summary on error
            return {
                "title": "Session Summary",
                "skill_scores": {
                    "pronunciation": 75,
                    "grammar": 75,
                    "vocabulary": 75,
                    "comprehension": 75
                },
                "subtitle": {
                    "0": {
                        "heading": "Session Completed",
                        "points": {"0": "Thank you for practicing!"}
                    }
                }
            }
    
    def _calculate_skill_scores(
        self, 
        session_stats: Dict[str, Any], 
        user_conversations: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Calculate skill scores as percentages (0-100) based on session performance
        
        Args:
            session_stats: Session statistics from scoring service
            user_conversations: User conversation data
            
        Returns:
            Dictionary with skill scores out of 100
        """
        try:
            # Get metric averages (assuming 1-5 scale from scoring service)
            metric_averages = session_stats.get("metric_averages", {})
            
            # Convert 5-point scale to 100-point scale
            def convert_to_percentage(score: float, max_score: float = 5.0) -> int:
                """Convert score to percentage and round to nearest integer"""
                if score <= 0:
                    return 0
                percentage = (score / max_score) * 100
                return min(100, max(0, round(percentage)))
            
            # Calculate individual skill scores
            pronunciation_score = convert_to_percentage(
                metric_averages.get("pronunciation", 3.0)
            )
            
            grammar_score = convert_to_percentage(
                metric_averages.get("grammar", 3.0)
            )
            
            vocabulary_score = convert_to_percentage(
                metric_averages.get("vocabulary", 3.0)
            )
            
            # Calculate comprehension score based on multiple factors
            comprehension_factors = [
                metric_averages.get("comprehension", 3.0),
                metric_averages.get("fluency", 3.0),
                min(5.0, len(user_conversations) / 2.0)  # Engagement factor (normalize to ~5 scale)
            ]
            avg_comprehension = sum(comprehension_factors) / len(comprehension_factors)
            comprehension_score = convert_to_percentage(avg_comprehension)
            
            # Apply minimum thresholds to encourage learners
            skill_scores = {
                "pronunciation": max(50, pronunciation_score),  # Minimum 50%
                "grammar": max(50, grammar_score),
                "vocabulary": max(50, vocabulary_score), 
                "comprehension": max(50, comprehension_score)
            }
            
            logger.debug("Calculated skill scores", 
                        session_stats=metric_averages,
                        skill_scores=skill_scores)
            
            return skill_scores
            
        except Exception as e:
            logger.error("Error calculating skill scores", error=str(e))
            # Return default encouraging scores
            return {
                "pronunciation": 75,
                "grammar": 75,
                "vocabulary": 75,
                "comprehension": 75
            }
    
    def _calculate_skill_scores(
        self, 
        session_stats: Dict[str, Any], 
        user_conversations: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Calculate skill scores as percentages (0-100) based on session performance
        
        Args:
            session_stats: Session statistics from scoring service
            user_conversations: User conversation data
            
        Returns:
            Dictionary with skill scores out of 100
        """
        try:
            # Get metric averages (assuming 1-5 scale from scoring service)
            metric_averages = session_stats.get("metric_averages", {})
            
            # Convert 5-point scale to 100-point scale
            def convert_to_percentage(score: float, max_score: float = 5.0) -> int:
                """Convert score to percentage and round to nearest integer"""
                if score <= 0:
                    return 0
                percentage = (score / max_score) * 100
                return min(100, max(0, round(percentage)))
            
            # Calculate individual skill scores
            pronunciation_score = convert_to_percentage(
                metric_averages.get("pronunciation", 3.0)
            )
            
            grammar_score = convert_to_percentage(
                metric_averages.get("grammar", 3.0)
            )
            
            vocabulary_score = convert_to_percentage(
                metric_averages.get("vocabulary", 3.0)
            )
            
            # Calculate comprehension score based on multiple factors
            comprehension_factors = [
                metric_averages.get("comprehension", 3.0),
                metric_averages.get("fluency", 3.0),
                len(user_conversations) / 10.0  # Engagement factor (normalize to ~5 scale)
            ]
            avg_comprehension = sum(comprehension_factors) / len(comprehension_factors)
            comprehension_score = convert_to_percentage(min(5.0, avg_comprehension))
            
            # Apply minimum thresholds to encourage learners
            skill_scores = {
                "pronunciation": max(50, pronunciation_score),  # Minimum 50%
                "grammar": max(50, grammar_score),
                "vocabulary": max(50, vocabulary_score), 
                "comprehension": max(50, comprehension_score)
            }
            
            logger.debug("Calculated skill scores", 
                        session_stats=metric_averages,
                        skill_scores=skill_scores)
            
            return skill_scores
            
        except Exception as e:
            logger.error("Error calculating skill scores", error=str(e))
            # Return default encouraging scores
            return {
                "pronunciation": 75,
                "grammar": 75,
                "vocabulary": 75,
                "comprehension": 75
            }
    
    def _extract_key_phrases(self, user_conversations: List[Dict[str, Any]]) -> List[str]:
        """Extract key phrases from user conversations"""
        phrases = []
        
        # Simple extraction of phrases from user input
        for conv in user_conversations[:10]:  # Limit to first 10 turns
            text = conv["text"].strip()
            if len(text) > 5:  # Meaningful phrases only
                # Clean up and add
                cleaned_text = text.replace('\n', ' ').strip()
                if len(cleaned_text) <= 100:  # Not too long
                    phrases.append(cleaned_text)
        
        # Ensure we have at least some content
        if not phrases:
            phrases = ["Great job practicing your conversation skills!"]
        
        # Limit to 5 key phrases
        return phrases[:5]
    
    def _extract_grammar_points(
        self, 
        user_conversations: List[Dict[str, Any]], 
        session_stats: Dict[str, Any]
    ) -> List[str]:
        """Extract grammar learning points based on conversations and stats"""
        grammar_points = []
        
        # Use session statistics to identify areas needing work
        metric_averages = session_stats.get("metric_averages", {})
        grammar_score = metric_averages.get("grammar", 3.0)
        
        if grammar_score < 3.0:
            grammar_points.extend([
                "Focus on subject-verb agreement in sentences",
                "Practice using correct verb tenses",
                "Review basic sentence structure patterns"
            ])
        elif grammar_score < 4.0:
            grammar_points.extend([
                "Good progress with basic grammar rules",
                "Continue practicing complex sentence structures",
                "Work on using connecting words effectively"
            ])
        else:
            grammar_points.extend([
                "Excellent grammar usage demonstrated",
                "Continue practicing advanced structures",
                "Focus on nuanced grammar patterns"
            ])
        
        # Add general encouragement
        if not grammar_points:
            grammar_points = ["Keep practicing grammar patterns in context"]
        
        return grammar_points[:5]
    
    def _generate_pronunciation_tips(
        self,
        user_conversations: List[Dict[str, Any]],
        session_stats: Dict[str, Any],
        language_label: str
    ) -> List[str]:
        """Generate pronunciation and fluency tips"""
        tips = []
        
        # Use session statistics
        metric_averages = session_stats.get("metric_averages", {})
        pronunciation_score = metric_averages.get("pronunciation", 3.0)
        fluency_score = metric_averages.get("fluency", 3.0)
        
        # Language-specific tips
        language_tips = {
            "Spanish": [
                "Practice rolling your 'rr' sounds",
                "Focus on clear vowel pronunciation",
                "Work on Spanish rhythm and stress patterns"
            ],
            "French": [
                "Practice nasal sounds (an, en, in, on)",
                "Work on the French 'r' sound",
                "Focus on liaison between words"
            ],
            "German": [
                "Practice the 'ü' and 'ö' sounds",
                "Work on consonant clusters",
                "Focus on word stress patterns"
            ],
            "English": [
                "Practice th sounds (think, that)",
                "Work on vowel distinctions",
                "Focus on stress-timed rhythm"
            ]
        }
        
        # Add language-specific tips if available
        if language_label in language_tips:
            tips.extend(language_tips[language_label][:2])
        
        # Add score-based tips
        if pronunciation_score < 3.0:
            tips.append("Focus on speaking more clearly and slowly")
        
        if fluency_score < 3.0:
            tips.append("Practice speaking without long pauses")
        
        # General tips
        tips.extend([
            "Listen to native speakers and repeat",
            "Record yourself to monitor progress"
        ])
        
        return tips[:5]
    
    def _generate_next_steps(
        self,
        session_stats: Dict[str, Any],
        mode_name: str,
        language_label: str
    ) -> List[str]:
        """Generate next steps based on session performance"""
        next_steps = []
        
        # Get areas for improvement
        areas_for_improvement = session_stats.get("areas_for_improvement", [])
        strengths = session_stats.get("strengths", [])
        
        # Add specific recommendations based on areas needing work
        for area in areas_for_improvement[:2]:
            if area == "fluency":
                next_steps.append("Practice daily conversation for 10-15 minutes")
            elif area == "vocabulary":
                next_steps.append("Learn 5 new words each day in context")
            elif area == "grammar":
                next_steps.append("Review grammar rules and practice exercises")
            elif area == "pronunciation":
                next_steps.append("Listen to audio materials and practice pronunciation")
        
        # Add mode-specific recommendations
        if "conversation" in mode_name.lower():
            next_steps.append("Find conversation partners to practice with")
        elif "grammar" in mode_name.lower():
            next_steps.append("Complete grammar exercises regularly")
        
        # Add general encouragement and next session suggestion
        next_steps.append(f"Continue practicing {language_label} regularly")
        next_steps.append("Schedule your next practice session soon")
        
        return next_steps[:5]

    # Keep all existing methods for user summaries, session retrieval, etc.
    async def get_user_summaries(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[SessionSummary]:
        """Get session summaries for a user"""
        try:
            query = self.supabase.table("session_summaries")\
                .select("*")\
                .eq("user_id", str(user_id))
            
            # Apply date filters if provided
            if from_date:
                query = query.gte("created_at", from_date)
            if to_date:
                query = query.lte("created_at", to_date)
            
            response = query.order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            summaries = []
            for record in response.data:
                summary = SessionSummary(
                    id=UUID(record["id"]),
                    session_id=UUID(record["session_id"]),
                    user_id=UUID(record["user_id"]),
                    summary_json=record["summary_json"],
                    created_at=record.get("created_at")
                )
                summaries.append(summary)
            
            logger.debug("Retrieved user summaries", 
                        user_id=user_id,
                        count=len(summaries))
            
            return summaries
            
        except Exception as e:
            logger.error("Error getting user summaries", 
                        user_id=user_id,
                        error=str(e))
            return []
    
    async def get_summary_by_session(self, session_id: UUID) -> Optional[SessionSummary]:
        """Get summary for a specific session"""
        try:
            response = self.supabase.table("session_summaries")\
                .select("*")\
                .eq("session_id", str(session_id))\
                .limit(1)\
                .execute()
            
            if response.data:
                record = response.data[0]
                return SessionSummary(
                    id=UUID(record["id"]),
                    session_id=UUID(record["session_id"]),
                    user_id=UUID(record["user_id"]),
                    summary_json=record["summary_json"],
                    created_at=record.get("created_at")
                )
            
            return None
            
        except Exception as e:
            logger.error("Error getting summary by session", 
                        session_id=session_id,
                        error=str(e))
            return None

    async def _get_session_info(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get session information including mode and language details"""
        try:
            # Get session details with related data
            response = self.supabase.table("sessions")\
                .select("""
                    *,
                    teaching_modes(code, name, description),
                    supported_languages(code, label)
                """)\
                .eq("id", str(session_id))\
                .limit(1)\
                .execute()
            
            if response.data:
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error("Error getting session info", 
                        session_id=session_id,
                        error=str(e))
            return None


# Global summary service instance
summary_service = SummaryService()

# from typing import Dict, Any, List, Optional
# from uuid import UUID
# from datetime import datetime, timedelta
# from collections import Counter
# import structlog

# from app.domain.models import SessionSummary, SessionSummarySchema
# from app.services.supabase_client import get_supabase_client
# from app.services.conversation_service import conversation_service
# from app.services.scoring_service import scoring_service

# logger = structlog.get_logger(__name__)


# class SummaryService:
#     """Service for generating and managing session summaries"""
    
#     def __init__(self):
#         self.supabase = get_supabase_client()
#         self.conversation_service = conversation_service
#         self.scoring_service = scoring_service
    
#     async def generate_and_store_summary(
#         self,
#         session_id: UUID,
#         user_id: UUID
#     ) -> Optional[SessionSummary]:
#         """
#         Generate a learning summary for a session and store it
        
#         Args:
#             session_id: Session UUID
#             user_id: User UUID
            
#         Returns:
#             SessionSummary object if successful, None otherwise
#         """
#         try:
#             # Get session information
#             session_info = await self._get_session_info(session_id)
#             if not session_info:
#                 logger.error("Session not found for summary generation", session_id=session_id)
#                 return None
            
#             # Get conversation history
#             conversations = await self.conversation_service.get_session_conversations(
#                 session_id=session_id,
#                 limit=1000  # Get all conversations
#             )
            
#             # Get scoring statistics
#             session_stats = await self.scoring_service.calculate_session_statistics(session_id)
            
#             # Generate summary content
#             summary_json = await self._generate_summary_content(
#                 session_info=session_info,
#                 conversations=conversations,
#                 session_stats=session_stats
#             )
            
#             # Store summary in database
#             summary_data = {
#                 "session_id": str(session_id),
#                 "user_id": str(user_id),
#                 "summary_json": summary_json
#             }
            
#             response = self.supabase.table("session_summaries").insert(summary_data).execute()
            
#             if response.data:
#                 summary_record = response.data[0]
#                 logger.info("Session summary generated and stored", 
#                           session_id=session_id,
#                           summary_id=summary_record["id"])
                
#                 return SessionSummary(
#                     id=UUID(summary_record["id"]),
#                     session_id=session_id,
#                     user_id=user_id,
#                     summary_json=summary_json,
#                     created_at=summary_record.get("created_at")
#                 )
#             else:
#                 logger.error("Failed to store session summary", session_id=session_id)
#                 return None
                
#         except Exception as e:
#             logger.error("Error generating session summary", 
#                         session_id=session_id,
#                         error=str(e))
#             return None
    
#     async def get_user_summaries(
#         self,
#         user_id: UUID,
#         limit: int = 20,
#         offset: int = 0,
#         from_date: Optional[str] = None,
#         to_date: Optional[str] = None
#     ) -> List[SessionSummary]:
#         """
#         Get session summaries for a user
        
#         Args:
#             user_id: User UUID
#             limit: Maximum number of summaries
#             offset: Pagination offset
#             from_date: Start date filter (ISO format)
#             to_date: End date filter (ISO format)
            
#         Returns:
#             List of SessionSummary objects
#         """
#         try:
#             query = self.supabase.table("session_summaries")\
#                 .select("*")\
#                 .eq("user_id", str(user_id))
            
#             # Apply date filters if provided
#             if from_date:
#                 query = query.gte("created_at", from_date)
#             if to_date:
#                 query = query.lte("created_at", to_date)
            
#             response = query.order("created_at", desc=True)\
#                 .range(offset, offset + limit - 1)\
#                 .execute()
            
#             summaries = []
#             for record in response.data:
#                 summary = SessionSummary(
#                     id=UUID(record["id"]),
#                     session_id=UUID(record["session_id"]),
#                     user_id=UUID(record["user_id"]),
#                     summary_json=record["summary_json"],
#                     created_at=record.get("created_at")
#                 )
#                 summaries.append(summary)
            
#             logger.debug("Retrieved user summaries", 
#                         user_id=user_id,
#                         count=len(summaries))
            
#             return summaries
            
#         except Exception as e:
#             logger.error("Error getting user summaries", 
#                         user_id=user_id,
#                         error=str(e))
#             return []
    
#     async def get_summary_by_session(self, session_id: UUID) -> Optional[SessionSummary]:
#         """
#         Get summary for a specific session
        
#         Args:
#             session_id: Session UUID
            
#         Returns:
#             SessionSummary if found, None otherwise
#         """
#         try:
#             response = self.supabase.table("session_summaries")\
#                 .select("*")\
#                 .eq("session_id", str(session_id))\
#                 .limit(1)\
#                 .execute()
            
#             if response.data:
#                 record = response.data[0]
#                 return SessionSummary(
#                     id=UUID(record["id"]),
#                     session_id=UUID(record["session_id"]),
#                     user_id=UUID(record["user_id"]),
#                     summary_json=record["summary_json"],
#                     created_at=record.get("created_at")
#                 )
            
#             return None
            
#         except Exception as e:
#             logger.error("Error getting summary by session", 
#                         session_id=session_id,
#                         error=str(e))
#             return None

#     # NEW METHODS FOR EMAIL REPORTS AND WRITING EVALUATION INTEGRATION

#     async def generate_learning_report(
#         self,
#         user_email: str,
#         period: str = "weekly",
#         include_detailed_stats: bool = True
#     ) -> Dict[str, Any]:
#         """
#         Generate comprehensive learning report for email functionality
#         Integrates both session and writing evaluation data
#         """
#         try:
#             # Calculate date range based on period
#             end_date = datetime.now()
#             if period == "weekly":
#                 start_date = end_date - timedelta(days=7)
#             elif period == "monthly":
#                 start_date = end_date - timedelta(days=30)
#             elif period == "daily":
#                 start_date = end_date - timedelta(days=1)
#             else:
#                 start_date = end_date - timedelta(days=7)  # Default to weekly

#             # Get session statistics
#             session_stats = await self._get_session_statistics(
#                 user_email, start_date, end_date
#             )

#             # Get writing evaluation statistics
#             writing_stats = await self._get_writing_statistics(
#                 user_email, start_date, end_date
#             )

#             # Combine all statistics
#             report_data = {
#                 "period": period,
#                 "start_date": start_date.isoformat(),
#                 "end_date": end_date.isoformat(),
                
#                 # Session data
#                 "total_study_time": session_stats.get("total_minutes", 0),
#                 "time_improvement": self._calculate_improvement_percentage(
#                     session_stats.get("total_minutes", 0),
#                     session_stats.get("previous_period_minutes", 0)
#                 ),
#                 "total_conversations": session_stats.get("session_count", 0),
#                 "avg_session_length": session_stats.get("avg_session_length", 0),
                
#                 # Writing evaluation data
#                 "writing_evaluations": writing_stats.get("evaluation_count", 0),
#                 "skill_scores": {
#                     **session_stats.get("speaking_scores", {}),
#                     **writing_stats.get("avg_scores", {})
#                 },
                
#                 # Combined achievements and insights
#                 "achievements": self._generate_combined_achievements(session_stats, writing_stats),
#                 "improvement_areas": self._combine_improvement_areas(
#                     session_stats.get("improvement_areas", []),
#                     writing_stats.get("improvement_areas", [])
#                 ),
#                 "strengths": self._combine_strengths(
#                     session_stats.get("strengths", []),
#                     writing_stats.get("strengths", [])
#                 )
#             }

#             return report_data

#         except Exception as e:
#             logger.error(f"Failed to generate learning report: {e}")
#             return self._get_fallback_report(period)

#     async def _get_session_statistics(
#         self, 
#         user_email: str, 
#         start_date: datetime, 
#         end_date: datetime
#     ) -> Dict[str, Any]:
#         """
#         Get session statistics for the period
#         """
#         try:
#             # Get sessions for the period
#             result = await self.supabase.table("sessions")\
#                 .select("*")\
#                 .eq("user_email", user_email)\
#                 .gte("created_at", start_date.isoformat())\
#                 .lte("created_at", end_date.isoformat())\
#                 .execute()

#             sessions = result.data or []
            
#             if not sessions:
#                 return {
#                     "session_count": 0,
#                     "total_minutes": 0,
#                     "avg_session_length": 0,
#                     "previous_period_minutes": 0,
#                     "speaking_scores": {},
#                     "improvement_areas": [],
#                     "strengths": []
#                 }

#             # Calculate session metrics
#             total_minutes = sum(s.get("duration_minutes", 0) for s in sessions)
#             session_count = len(sessions)
#             avg_length = round(total_minutes / session_count, 1) if session_count > 0 else 0

#             # Get previous period for comparison
#             previous_start = start_date - (end_date - start_date)
#             previous_result = await self.supabase.table("sessions")\
#                 .select("duration_minutes")\
#                 .eq("user_email", user_email)\
#                 .gte("created_at", previous_start.isoformat())\
#                 .lt("created_at", start_date.isoformat())\
#                 .execute()

#             previous_minutes = sum(
#                 s.get("duration_minutes", 0) 
#                 for s in (previous_result.data or [])
#             )

#             # Get speaking performance scores from session summaries
#             speaking_scores = await self._get_speaking_scores_from_sessions(sessions)

#             return {
#                 "session_count": session_count,
#                 "total_minutes": total_minutes,
#                 "avg_session_length": avg_length,
#                 "previous_period_minutes": previous_minutes,
#                 "speaking_scores": speaking_scores,
#                 "improvement_areas": await self._extract_session_improvement_areas(sessions),
#                 "strengths": await self._extract_session_strengths(sessions)
#             }

#         except Exception as e:
#             logger.error(f"Failed to get session statistics: {e}")
#             return {
#                 "session_count": 0,
#                 "total_minutes": 0,
#                 "avg_session_length": 0,
#                 "previous_period_minutes": 0,
#                 "speaking_scores": {},
#                 "improvement_areas": [],
#                 "strengths": []
#             }

#     async def _get_writing_statistics(
#         self, 
#         user_email: str, 
#         start_date: datetime, 
#         end_date: datetime
#     ) -> Dict[str, Any]:
#         """
#         Get writing evaluation statistics with safe JSONB handling
#         """
#         try:
#             # Get writing evaluations for the period
#             result = await self.supabase.table("writing_evaluations")\
#                 .select("*")\
#                 .eq("user_id", user_email)\
#                 .gte("created_at", start_date.isoformat())\
#                 .lte("created_at", end_date.isoformat())\
#                 .execute()

#             evaluations = result.data or []

#             if not evaluations:
#                 return {
#                     "evaluation_count": 0,
#                     "avg_scores": {},
#                     "improvement_areas": [],
#                     "strengths": []
#                 }

#             # Calculate average scores with safe JSONB handling
#             valid_evaluations = [e for e in evaluations if e.get("scores")]
#             evaluation_count = len(evaluations)

#             if not valid_evaluations:
#                 return {
#                     "evaluation_count": evaluation_count,
#                     "avg_scores": {},
#                     "improvement_areas": [],
#                     "strengths": []
#                 }

#             # Calculate averages safely
#             avg_scores = {}
#             score_categories = ["grammar", "vocabulary", "coherence", "style", "clarity", "engagement"]
            
#             for category in score_categories:
#                 scores = []
#                 for eval_data in valid_evaluations:
#                     scores_dict = eval_data.get("scores", {})
#                     if isinstance(scores_dict, dict) and category in scores_dict:
#                         try:
#                             score = scores_dict[category]
#                             if isinstance(score, (int, float)):
#                                 scores.append(float(score))
#                             elif isinstance(score, str) and score.isdigit():
#                                 scores.append(float(score))
#                         except (ValueError, TypeError):
#                             continue
                
#                 if scores:
#                     avg_scores[category] = round(sum(scores) / len(scores), 1)

#             # Calculate overall average
#             overall_scores = [e.get("overall_score", 0) for e in valid_evaluations if e.get("overall_score")]
#             if overall_scores:
#                 avg_scores["overall"] = round(sum(overall_scores) / len(overall_scores), 1)

#             return {
#                 "evaluation_count": evaluation_count,
#                 "avg_scores": avg_scores,
#                 "improvement_areas": await self._extract_writing_improvement_areas(evaluations),
#                 "strengths": await self._extract_writing_strengths(evaluations)
#             }

#         except Exception as e:
#             logger.error(f"Failed to get writing statistics: {e}")
#             return {
#                 "evaluation_count": 0,
#                 "avg_scores": {},
#                 "improvement_areas": [],
#                 "strengths": []
#             }

#     async def _get_speaking_scores_from_sessions(self, sessions: List[Dict[str, Any]]) -> Dict[str, float]:
#         """Extract speaking performance scores from sessions"""
#         try:
#             all_scores = {"fluency": [], "vocabulary": [], "grammar": [], "pronunciation": []}
            
#             for session in sessions:
#                 session_id = session.get("id")
#                 if session_id:
#                     # Get scoring statistics for this session
#                     session_stats = await self.scoring_service.calculate_session_statistics(UUID(session_id))
#                     metric_averages = session_stats.get("metric_averages", {})
                    
#                     for metric in all_scores.keys():
#                         if metric in metric_averages:
#                             all_scores[metric].append(metric_averages[metric])
            
#             # Calculate averages
#             avg_scores = {}
#             for metric, scores in all_scores.items():
#                 if scores:
#                     avg_scores[f"speaking_{metric}"] = round(sum(scores) / len(scores), 1)
            
#             return avg_scores
            
#         except Exception as e:
#             logger.error(f"Failed to extract speaking scores: {e}")
#             return {}

#     async def _extract_session_improvement_areas(self, sessions: List[Dict[str, Any]]) -> List[str]:
#         """Extract improvement areas from session data"""
#         improvement_areas = []
        
#         try:
#             for session in sessions[:5]:  # Check recent sessions
#                 session_id = session.get("id")
#                 if session_id:
#                     session_stats = await self.scoring_service.calculate_session_statistics(UUID(session_id))
#                     areas = session_stats.get("areas_for_improvement", [])
#                     improvement_areas.extend(areas)
            
#             # Count frequency and return most common
#             if improvement_areas:
#                 area_counts = Counter(improvement_areas)
#                 return [area for area, count in area_counts.most_common(3)]
            
#         except Exception as e:
#             logger.error(f"Failed to extract session improvement areas: {e}")
        
#         return ["Continue practicing speaking skills"]

#     async def _extract_session_strengths(self, sessions: List[Dict[str, Any]]) -> List[str]:
#         """Extract strengths from session data"""
#         strengths = []
        
#         try:
#             for session in sessions[:5]:  # Check recent sessions
#                 session_id = session.get("id")
#                 if session_id:
#                     session_stats = await self.scoring_service.calculate_session_statistics(UUID(session_id))
#                     session_strengths = session_stats.get("strengths", [])
#                     strengths.extend(session_strengths)
            
#             # Count frequency and return most common
#             if strengths:
#                 strength_counts = Counter(strengths)
#                 return [strength for strength, count in strength_counts.most_common(3)]
            
#         except Exception as e:
#             logger.error(f"Failed to extract session strengths: {e}")
        
#         return ["Good engagement in practice sessions"]

#     async def _extract_writing_improvement_areas(self, evaluations: List[Dict[str, Any]]) -> List[str]:
#         """Extract common improvement suggestions from writing evaluations"""
#         try:
#             all_improvements = []
#             for evaluation in evaluations:
#                 improvements = evaluation.get("improvements", [])
#                 if isinstance(improvements, list):
#                     all_improvements.extend(improvements)

#             # Count frequency and return most common
#             if all_improvements:
#                 improvement_counts = Counter(all_improvements)
#                 return [imp for imp, count in improvement_counts.most_common(3)]

#         except Exception as e:
#             logger.error(f"Failed to extract writing improvements: {e}")

#         return ["Continue practicing writing skills"]

#     async def _extract_writing_strengths(self, evaluations: List[Dict[str, Any]]) -> List[str]:
#         """Extract common strengths from writing evaluations"""
#         try:
#             all_strengths = []
#             for evaluation in evaluations:
#                 strengths = evaluation.get("strengths", [])
#                 if isinstance(strengths, list):
#                     all_strengths.extend(strengths)

#             # Count frequency and return most common
#             if all_strengths:
#                 strength_counts = Counter(all_strengths)
#                 return [strength for strength, count in strength_counts.most_common(3)]

#         except Exception as e:
#             logger.error(f"Failed to extract writing strengths: {e}")

#         return ["Good effort in writing practice"]

#     def _generate_combined_achievements(
#         self, 
#         session_stats: Dict[str, Any], 
#         writing_stats: Dict[str, Any]
#     ) -> List[str]:
#         """Generate achievement messages combining session and writing data"""
#         achievements = []
        
#         # Session achievements
#         session_count = session_stats.get("session_count", 0)
#         if session_count >= 10:
#             achievements.append(f"Completed {session_count} speaking practice sessions!")
#         elif session_count >= 5:
#             achievements.append("Consistent speaking practice habit!")
#         elif session_count >= 1:
#             achievements.append("Great start with speaking practice!")

#         # Writing achievements
#         eval_count = writing_stats.get("evaluation_count", 0)
#         if eval_count >= 5:
#             achievements.append(f"Submitted {eval_count} pieces for writing evaluation!")
#         elif eval_count >= 1:
#             achievements.append("Active in writing skill development!")

#         # Combined skill achievements
#         writing_scores = writing_stats.get("avg_scores", {})
#         speaking_scores = session_stats.get("speaking_scores", {})
        
#         overall_writing = writing_scores.get("overall", 0)
#         if overall_writing >= 80:
#             achievements.append("Strong writing skills demonstrated!")
        
#         if speaking_scores and any(score >= 4.0 for score in speaking_scores.values()):
#             achievements.append("Excellent speaking performance!")

#         # Multi-skill achievement
#         if session_count > 0 and eval_count > 0:
#             achievements.append("Well-rounded language practice across speaking and writing!")

#         return achievements[:5]  # Limit to 5 achievements

#     def _combine_improvement_areas(self, session_areas: List[str], writing_areas: List[str]) -> List[str]:
#         """Combine and prioritize improvement areas from both skills"""
#         combined = session_areas + writing_areas
#         if combined:
#             # Count frequency and return most common
#             area_counts = Counter(combined)
#             return [area for area, count in area_counts.most_common(5)]
#         return ["Continue practicing both speaking and writing skills"]

#     def _combine_strengths(self, session_strengths: List[str], writing_strengths: List[str]) -> List[str]:
#         """Combine and prioritize strengths from both skills"""
#         combined = session_strengths + writing_strengths
#         if combined:
#             # Count frequency and return most common
#             strength_counts = Counter(combined)
#             return [strength for strength, count in strength_counts.most_common(5)]
#         return ["Consistent effort in language learning"]

#     def _calculate_improvement_percentage(
#         self, 
#         current_value: float, 
#         previous_value: float
#     ) -> float:
#         """Calculate percentage improvement"""
#         if previous_value == 0:
#             return 100.0 if current_value > 0 else 0.0
        
#         return round(((current_value - previous_value) / previous_value) * 100, 1)

#     def _get_fallback_report(self, period: str) -> Dict[str, Any]:
#         """Fallback report when data retrieval fails"""
#         return {
#             "period": period,
#             "total_study_time": 0,
#             "time_improvement": 0,
#             "total_conversations": 0,
#             "avg_session_length": 0,
#             "writing_evaluations": 0,
#             "skill_scores": {},
#             "achievements": ["Welcome to your learning journey!"],
#             "improvement_areas": ["Continue practicing to see detailed insights"],
#             "strengths": ["Every step forward is progress"],
#             "note": "Complete more sessions and evaluations to see detailed statistics"
#         }
    
#     # EXISTING METHODS (keeping all original functionality)
    
#     async def _get_session_info(self, session_id: UUID) -> Optional[Dict[str, Any]]:
#         """
#         Get session information including mode and language details
        
#         Args:
#             session_id: Session UUID
            
#         Returns:
#             Session information dictionary
#         """
#         try:
#             # Get session details with related data
#             response = self.supabase.table("sessions")\
#                 .select("""
#                     *,
#                     teaching_modes(code, name, description),
#                     supported_languages(code, label)
#                 """)\
#                 .eq("id", str(session_id))\
#                 .limit(1)\
#                 .execute()
            
#             if response.data:
#                 return response.data[0]
            
#             return None
            
#         except Exception as e:
#             logger.error("Error getting session info", 
#                         session_id=session_id,
#                         error=str(e))
#             return None
    
#     async def _generate_summary_content(
#         self,
#         session_info: Dict[str, Any],
#         conversations: List[Dict[str, Any]],
#         session_stats: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """
#         Generate the actual summary content following the required schema
        
#         Args:
#             session_info: Session information
#             conversations: List of conversation turns
#             session_stats: Session statistics
            
#         Returns:
#             Summary JSON following SessionSummarySchema
#         """
#         try:
#             # Extract session details
#             mode_info = session_info.get("teaching_modes", {})
#             language_info = session_info.get("supported_languages", {})
#             mode_name = mode_info.get("name", "Unknown Mode")
#             language_label = language_info.get("label", "Unknown Language")
            
#             # Create title
#             session_short_id = str(session_info["id"])[:8]
#             title = f"Session {session_short_id} Study Notes – {language_label} ({mode_name})"
            
#             # Extract user conversations (for content analysis)
#             user_conversations = [
#                 conv for conv in conversations 
#                 if conv["role"] == "user" and conv["text"].strip()
#             ]
            
#             # Generate key phrases section
#             key_phrases = self._extract_key_phrases(user_conversations)
            
#             # Generate grammar corrections section
#             grammar_corrections = self._extract_grammar_points(
#                 user_conversations, session_stats
#             )
            
#             # Generate pronunciation tips section
#             pronunciation_tips = self._generate_pronunciation_tips(
#                 user_conversations, session_stats, language_label
#             )
            
#             # Generate next steps section
#             next_steps = self._generate_next_steps(
#                 session_stats, mode_name, language_label
#             )
            
#             # Build summary according to required schema
#             summary = {
#                 "title": title,
#                 "subtitle": {
#                     "0": {
#                         "heading": "Key Phrases Practiced",
#                         "points": {str(i): phrase for i, phrase in enumerate(key_phrases)}
#                     },
#                     "1": {
#                         "heading": "Grammar & Corrections",
#                         "points": {str(i): correction for i, correction in enumerate(grammar_corrections)}
#                     },
#                     "2": {
#                         "heading": "Pronunciation / Fluency Tips",
#                         "points": {str(i): tip for i, tip in enumerate(pronunciation_tips)}
#                     },
#                     "3": {
#                         "heading": "Next Steps",
#                         "points": {str(i): step for i, step in enumerate(next_steps)}
#                     }
#                 }
#             }
            
#             # Validate against schema
#             validated_summary = SessionSummarySchema(**summary)
#             return validated_summary.dict()
            
#         except Exception as e:
#             logger.error("Error generating summary content", error=str(e))
#             # Return minimal valid summary on error
#             return {
#                 "title": "Session Summary",
#                 "subtitle": {
#                     "0": {
#                         "heading": "Session Completed",
#                         "points": {"0": "Thank you for practicing!"}
#                     }
#                 }
#             }
    
#     def _extract_key_phrases(self, user_conversations: List[Dict[str, Any]]) -> List[str]:
#         """Extract key phrases from user conversations"""
#         phrases = []
        
#         # Simple extraction of phrases from user input
#         for conv in user_conversations[:10]:  # Limit to first 10 turns
#             text = conv["text"].strip()
#             if len(text) > 5:  # Meaningful phrases only
#                 # Clean up and add
#                 cleaned_text = text.replace('\n', ' ').strip()
#                 if len(cleaned_text) <= 100:  # Not too long
#                     phrases.append(cleaned_text)
        
#         # Ensure we have at least some content
#         if not phrases:
#             phrases = ["Great job practicing your conversation skills!"]
        
#         # Limit to 5 key phrases
#         return phrases[:5]
    
#     def _extract_grammar_points(
#         self, 
#         user_conversations: List[Dict[str, Any]], 
#         session_stats: Dict[str, Any]
#     ) -> List[str]:
#         """Extract grammar learning points based on conversations and stats"""
#         grammar_points = []
        
#         # Use session statistics to identify areas needing work
#         metric_averages = session_stats.get("metric_averages", {})
#         grammar_score = metric_averages.get("grammar", 3.0)
        
#         if grammar_score < 3.0:
#             grammar_points.extend([
#                 "Focus on subject-verb agreement in sentences",
#                 "Practice using correct verb tenses",
#                 "Review basic sentence structure patterns"
#             ])
#         elif grammar_score < 4.0:
#             grammar_points.extend([
#                 "Good progress with basic grammar rules",
#                 "Continue practicing complex sentence structures",
#                 "Work on using connecting words effectively"
#             ])
#         else:
#             grammar_points.extend([
#                 "Excellent grammar usage demonstrated",
#                 "Continue practicing advanced structures",
#                 "Focus on nuanced grammar patterns"
#             ])
        
#         # Add general encouragement
#         if not grammar_points:
#             grammar_points = ["Keep practicing grammar patterns in context"]
        
#         return grammar_points[:5]
    
#     def _generate_pronunciation_tips(
#         self,
#         user_conversations: List[Dict[str, Any]],
#         session_stats: Dict[str, Any],
#         language_label: str
#     ) -> List[str]:
#         """Generate pronunciation and fluency tips"""
#         tips = []
        
#         # Use session statistics
#         metric_averages = session_stats.get("metric_averages", {})
#         pronunciation_score = metric_averages.get("pronunciation", 3.0)
#         fluency_score = metric_averages.get("fluency", 3.0)
        
#         # Language-specific tips
#         language_tips = {
#             "Spanish": [
#                 "Practice rolling your 'rr' sounds",
#                 "Focus on clear vowel pronunciation",
#                 "Work on Spanish rhythm and stress patterns"
#             ],
#             "French": [
#                 "Practice nasal sounds (an, en, in, on)",
#                 "Work on the French 'r' sound",
#                 "Focus on liaison between words"
#             ],
#             "German": [
#                 "Practice the 'ü' and 'ö' sounds",
#                 "Work on consonant clusters",
#                 "Focus on word stress patterns"
#             ],
#             "English": [
#                 "Practice th sounds (think, that)",
#                 "Work on vowel distinctions",
#                 "Focus on stress-timed rhythm"
#             ]
#         }
        
#         # Add language-specific tips if available
#         if language_label in language_tips:
#             tips.extend(language_tips[language_label][:2])
        
#         # Add score-based tips
#         if pronunciation_score < 3.0:
#             tips.append("Focus on speaking more clearly and slowly")
        
#         if fluency_score < 3.0:
#             tips.append("Practice speaking without long pauses")
        
#         # General tips
#         tips.extend([
#             "Listen to native speakers and repeat",
#             "Record yourself to monitor progress"
#         ])
        
#         return tips[:5]
    
#     def _generate_next_steps(
#         self,
#         session_stats: Dict[str, Any],
#         mode_name: str,
#         language_label: str
#     ) -> List[str]:
#         """Generate next steps based on session performance"""
#         next_steps = []
        
#         # Get areas for improvement
#         areas_for_improvement = session_stats.get("areas_for_improvement", [])
#         strengths = session_stats.get("strengths", [])
        
#         # Add specific recommendations based on areas needing work
#         for area in areas_for_improvement[:2]:
#             if area == "fluency":
#                 next_steps.append("Practice daily conversation for 10-15 minutes")
#             elif area == "vocabulary":
#                 next_steps.append("Learn 5 new words each day in context")
#             elif area == "grammar":
#                 next_steps.append("Review grammar rules and practice exercises")
#             elif area == "pronunciation":
#                 next_steps.append("Listen to audio materials and practice pronunciation")
        
#         # Add mode-specific recommendations
#         if "conversation" in mode_name.lower():
#             next_steps.append("Find conversation partners to practice with")
#         elif "grammar" in mode_name.lower():
#             next_steps.append("Complete grammar exercises regularly")
        
#         # Add general encouragement and next session suggestion
#         next_steps.append(f"Continue practicing {language_label} regularly")
#         next_steps.append("Schedule your next practice session soon")
        
#         return next_steps[:5]


# # Global summary service instance
# summary_service = SummaryService()
