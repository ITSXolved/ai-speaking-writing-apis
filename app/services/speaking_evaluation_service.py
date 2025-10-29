# app/services/speaking_evaluation_service.py
from typing import Dict, List, Any, Optional
import google.generativeai as genai
import os
import re
import logging
from datetime import datetime
from dataclasses import dataclass
from uuid import UUID

from app.services.conversation_service import conversation_service

logger = logging.getLogger(__name__)

@dataclass
class SpeakingEvaluation:
    """Data class for speaking evaluation results"""
    session_id: str
    total_turns: int
    overall_score: int
    scores: Dict[str, int]  # Category scores out of 100
    suggestions: List[str]

class SpeakingEvaluationService:
    def __init__(self):
        self.genai_api_key = os.getenv("GEMINI_API_KEY")
        if not self.genai_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=self.genai_api_key)

        # Use supported Gemini model
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

        # Configure model settings for optimal performance
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.3,
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048
        )

        # Safety settings to avoid blocking educational content
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ]

        self.conversation_service = conversation_service

    async def evaluate_speaking(
        self,
        session_id: UUID,
        language: str = "english",
        user_level: str = "intermediate"
    ) -> SpeakingEvaluation:
        """
        Comprehensive speaking evaluation using conversation history from a session
        """
        try:
            # Get conversation history for the session
            conversations = await self.conversation_service.get_session_conversations(
                session_id=session_id,
                limit=100  # Get up to 100 turns
            )

            if not conversations:
                logger.warning(f"No conversation data found for session {session_id}")
                return self._create_fallback_evaluation(str(session_id), 0)

            # Extract user turns only (filter by role = 'user')
            user_turns = [
                conv for conv in conversations
                if conv.get('role') == 'user'
            ]

            if not user_turns:
                logger.warning(f"No user turns found in session {session_id}")
                return self._create_fallback_evaluation(str(session_id), len(conversations))

            # Format conversation data for evaluation
            conversation_text = self._format_conversations_for_evaluation(conversations)

            # Generate evaluation prompt
            evaluation_prompt = self._create_evaluation_prompt(
                conversation_text,
                language,
                user_level,
                len(user_turns)
            )

            # Get evaluation from GenAI with safety settings
            response = await self.model.generate_content_async(
                evaluation_prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )

            # Check if response was blocked or empty
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning("Response was blocked or empty, using fallback evaluation")
                return self._create_fallback_evaluation(str(session_id), len(user_turns))

            # Check finish reason
            candidate = response.candidates[0]
            if candidate.finish_reason != 1:  # 1 = STOP (successful completion)
                logger.warning(f"Response finish reason: {candidate.finish_reason}, using fallback")
                return self._create_fallback_evaluation(str(session_id), len(user_turns))

            response_text = candidate.content.parts[0].text
            evaluation_data = self._parse_evaluation_response(response_text)

            # Create evaluation object
            evaluation = SpeakingEvaluation(
                session_id=str(session_id),
                total_turns=len(user_turns),
                overall_score=evaluation_data.get("overall_score", 0),
                scores=evaluation_data.get("scores", {}),
                suggestions=evaluation_data.get("suggestions", [])
            )

            return evaluation

        except Exception as e:
            logger.error(f"Speaking evaluation failed: {str(e)}")
            return self._create_fallback_evaluation(str(session_id), 0)

    def _format_conversations_for_evaluation(self, conversations: List[Dict[str, Any]]) -> str:
        """
        Format conversation history into a readable text format
        """
        formatted_lines = []

        for conv in conversations:
            role = conv.get('role', 'unknown')
            text = conv.get('text', '')
            turn_index = conv.get('turn_index', 0)

            # Format as dialogue
            speaker = "User" if role == 'user' else "Assistant"
            formatted_lines.append(f"[Turn {turn_index}] {speaker}: {text}")

        return "\n".join(formatted_lines)

    def _create_evaluation_prompt(
        self,
        conversation_text: str,
        language: str,
        user_level: str,
        user_turn_count: int
    ) -> str:
        """
        Create evaluation prompt for speaking assessment
        """
        return f"""
        As an experienced {language} language teacher, please evaluate this speaking conversation from a {user_level} level student.

        The student had {user_turn_count} speaking turns in this conversation:

        {conversation_text}

        Please provide the evaluation in this exact structured format:

        OVERALL SCORE: [number 0-100]

        DETAILED SCORES:
        Fluency: [number 0-100]
        Pronunciation: [number 0-100]
        Vocabulary: [number 0-100]
        Grammar: [number 0-100]
        Focus: [number 0-100]
        Understanding: [number 0-100]

        SUGGESTIONS:
        - [suggestion 1]
        - [suggestion 2]
        - [suggestion 3]

        Keep the response concise, constructive, and appropriate for a {user_level} level {language} learner.
        """

    def _parse_evaluation_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse structured text response and extract evaluation data
        """
        try:
            evaluation_data = self._get_default_evaluation_data()
            score_aliases = {
                'fluency': 'fluency',
                'pronunciation': 'pronunciation',
                'vocabulary': 'vocabulary',
                'grammar': 'grammar',
                'focus': 'focus',
                'coherence': 'focus',
                'understanding': 'understanding',
                'comprehension': 'understanding'
            }

            lines = response_text.split('\n')
            current_section = None

            for raw_line in lines:
                line = raw_line.strip()
                if not line:
                    continue

                # Parse overall score
                if line.startswith('OVERALL SCORE:'):
                    score_match = re.search(r'(\d+)', line)
                    if score_match:
                        evaluation_data["overall_score"] = int(score_match.group(1))
                    continue

                # Parse detailed scores
                lower_line = line.lower()
                if any(f"{alias}:" in lower_line for alias in score_aliases):
                    for alias, target in score_aliases.items():
                        if f"{alias}:" in lower_line:
                            score_match = re.search(r'(\d+)', line)
                            if score_match:
                                evaluation_data["scores"][target] = int(score_match.group(1))
                    continue

                # Track suggestions section
                if line.upper().startswith('SUGGESTIONS'):
                    current_section = 'suggestions'
                    evaluation_data["suggestions"] = []
                    continue

                if line.startswith('-') or line.startswith('•'):
                    item = line[1:].strip()
                    if item and current_section == 'suggestions':
                        evaluation_data["suggestions"].append(item)
                    continue

            if not evaluation_data["suggestions"]:
                evaluation_data["suggestions"] = [
                    "Practice speaking daily for short focused sessions",
                    "Review conversation topics to strengthen focus",
                    "Summarize what you understood after each discussion"
                ]

            return evaluation_data

        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            return self._get_default_evaluation_data()

    def _get_default_evaluation_data(self) -> Dict[str, Any]:
        """Get default evaluation data when parsing fails"""
        return {
            "scores": {
                "fluency": 75,
                "pronunciation": 75,
                "vocabulary": 75,
                "grammar": 75,
                "focus": 75,
                "understanding": 75
            },
            "overall_score": 75,
            "suggestions": [
                "Practice speaking daily for short focused sessions",
                "Review conversation topics to strengthen focus",
                "Summarize what you understood after each discussion"
            ]
        }

    def _create_fallback_evaluation(self, session_id: str, turn_count: int) -> SpeakingEvaluation:
        """
        Create a fallback evaluation when API calls fail or no data available
        """
        return SpeakingEvaluation(
            session_id=session_id,
            total_turns=turn_count,
            scores={
                'fluency': 75,
                'pronunciation': 75,
                'vocabulary': 75,
                'grammar': 75,
                'focus': 75,
                'understanding': 75
            },
            suggestions=[
                "Practice speaking daily for short focused sessions",
                "Review conversation topics to strengthen focus",
                "Summarize what you understood after each discussion"
            ],
            overall_score=75
        )

    async def get_speaking_tips(self, language: str = "english", proficiency_level: str = "intermediate") -> List[str]:
        """
        Get general speaking tips for the specified language and proficiency level
        """
        prompt = f"""
        As an expert {language} speaking instructor, provide 8 practical tips for improving speaking skills at the {proficiency_level} level.

        Please list them as:
        1. [tip 1]
        2. [tip 2]
        3. [tip 3]
        etc.

        Focus on actionable advice for {proficiency_level} level {language} speakers.
        """

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=512
                ),
                safety_settings=self.safety_settings
            )

            if response.candidates and response.candidates[0].content.parts:
                response_text = response.candidates[0].content.parts[0].text
                tips = self._extract_tips_from_text(response_text)
                return tips[:10]  # Limit to 10 tips
            else:
                return self._get_default_speaking_tips(language, proficiency_level)

        except Exception as e:
            logger.error(f"Failed to get speaking tips: {e}")
            return self._get_default_speaking_tips(language, proficiency_level)

    def _extract_tips_from_text(self, text: str) -> List[str]:
        """
        Extract tips from numbered or bulleted text
        """
        tips = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            # Match numbered lists, bullet points, or dashes
            if re.match(r'^\d+\.', line) or line.startswith('•') or line.startswith('-'):
                clean_tip = re.sub(r'^\d+\.\s*|^[•-]\s*', '', line).strip()
                if len(clean_tip) > 10:  # Only substantial tips
                    tips.append(clean_tip)

        return tips if tips else self._get_default_speaking_tips("english", "intermediate")

    def _get_default_speaking_tips(self, language: str, proficiency_level: str) -> List[str]:
        """Get default speaking tips when API fails"""
        return [
            f"Practice speaking {language} daily, even if just for 5-10 minutes",
            "Record yourself speaking and listen to identify areas for improvement",
            "Focus on pronunciation by mimicking native speakers",
            "Don't be afraid to make mistakes - they're part of the learning process",
            "Use language learning apps with speaking exercises",
            f"Find a conversation partner or language exchange for {language} practice",
            "Think in the target language to improve fluency",
            "Learn common phrases and expressions used in everyday conversations",
            "Watch movies or shows in the target language with subtitles",
            "Practice speaking about topics you're interested in"
        ]
