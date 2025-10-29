"""
CBT-based Evaluation Service
Evaluates language learning questions and provides Cognitive Behavioral Therapy-inspired suggestions
"""

import logging
from typing import Dict, Optional, List
import google.generativeai as genai
from datetime import datetime

from app.config import GEMINI_API_KEY, MODEL

logger = logging.getLogger(__name__)


class CBTEvaluationService:
    """Service for evaluating questions and providing CBT-based suggestions"""

    def __init__(self):
        """Initialize the CBT evaluation service"""
        self.api_key = GEMINI_API_KEY
        # Use gemini-2.5-flash for text evaluation (not the audio preview model)
        self.model_name = "gemini-2.5-flash"

        # Configure the API
        genai.configure(api_key=self.api_key)

        # Initialize the model
        self.model = genai.GenerativeModel(self.model_name)

    async def evaluate_question(
        self,
        question: str,
        answer: str,
        skill_type: str,
        options: Optional[List[str]] = None
    ) -> Dict:
        """
        Evaluate a question/answer and provide CBT-based suggestions

        Args:
            question: The question or prompt
            answer: The student's answer
            skill_type: Type of skill (speaking, writing, listening, reading, grammar)
            options: Optional multiple choice options

        Returns:
            Dictionary containing evaluation and CBT suggestion
        """
        try:
            # Build the evaluation prompt
            prompt = self._build_evaluation_prompt(question, answer, skill_type, options)

            # Call Gemini API using the pre-configured model
            response = self.model.generate_content(prompt)

            # Parse response
            result = self._parse_response(response.text, skill_type)

            return result

        except Exception as e:
            logger.error(f"Error in CBT evaluation: {str(e)}")
            raise Exception(f"Failed to evaluate question: {str(e)}")

    def _build_evaluation_prompt(
        self,
        question: str,
        answer: str,
        skill_type: str,
        options: Optional[List[str]] = None
    ) -> str:
        """Build the prompt for Gemini evaluation"""

        options_text = ""
        if options:
            options_text = "\n\nAnswer Options:\n" + "\n".join([f"- {opt}" for opt in options])

        prompt = f"""You are a compassionate language learning evaluator with expertise in Cognitive Behavioral Therapy (CBT).

Task: Evaluate the following {skill_type} exercise and provide a brief CBT-based suggestion.

Question: {question}{options_text}

Student's Answer: {answer}

Provide your response in this exact format:

EVALUATION: [2-3 sentences evaluating the answer quality, accuracy, and skill demonstration]

CBT_SUGGESTION: 1 sentence of encouraging, CBT-based advice that helps reframe negative thoughts, builds confidence, and promotes a growth mindset]

CONFIDENCE: [A number between 0 and 1 representing your confidence in this evaluation]

Guidelines:
- For EVALUATION: Be constructive, specific, and fair
- For CBT_SUGGESTION: Focus on reframing negative thoughts, celebrating progress, normalizing mistakes as learning opportunities, and encouraging self-compassion
- Keep it concise and actionable
- Be warm and supportive in tone
"""

        return prompt

    def _parse_response(self, response_text: str, skill_type: str) -> Dict:
        """Parse the Gemini response into structured data"""

        try:
            # Initialize defaults
            evaluation = ""
            cbt_suggestion = ""
            confidence = 0.75

            # Parse the response
            lines = response_text.strip().split("\n")
            current_section = None

            for line in lines:
                line = line.strip()

                if line.startswith("EVALUATION:"):
                    current_section = "evaluation"
                    evaluation = line.replace("EVALUATION:", "").strip()
                elif line.startswith("CBT_SUGGESTION:"):
                    current_section = "cbt_suggestion"
                    cbt_suggestion = line.replace("CBT_SUGGESTION:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    current_section = "confidence"
                    try:
                        confidence_str = line.replace("CONFIDENCE:", "").strip()
                        confidence = float(confidence_str)
                    except ValueError:
                        confidence = 0.75
                elif line and current_section:
                    # Continue building the current section
                    if current_section == "evaluation":
                        evaluation += " " + line
                    elif current_section == "cbt_suggestion":
                        cbt_suggestion += " " + line

            # Fallback if parsing fails
            if  not cbt_suggestion:
                evaluation = response_text[:200] if len(response_text) > 200 else response_text
                cbt_suggestion = "Remember that every mistake is a learning opportunity. Be patient with yourself and celebrate your progress, no matter how small."

            return {
                "skill_type": skill_type,
                "cbt_suggestion": cbt_suggestion.strip(),
                "confidence_score": confidence,
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            # Return a safe default
            return {
                "skill_type": skill_type,
                "evaluation": "Unable to fully evaluate the answer due to processing error.",
                "cbt_suggestion": "Learning a language is a journey. Be kind to yourself and remember that progress isn't always linear. Keep practicing!",
                "confidence_score": 0.5,
                "timestamp": datetime.now()
            }


# Singleton instance
_cbt_service = None


def get_cbt_evaluation_service() -> CBTEvaluationService:
    """Get or create the CBT evaluation service singleton"""
    global _cbt_service
    if _cbt_service is None:
        _cbt_service = CBTEvaluationService()
    return _cbt_service
