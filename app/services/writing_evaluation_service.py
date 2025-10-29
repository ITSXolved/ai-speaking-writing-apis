# app/services/writing_evaluation_service.py
from typing import Dict, List, Any, Optional, Tuple
import google.generativeai as genai
import os
import re
import json
import logging
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ErrorHighlight:
    """Data class for error highlighting"""
    error_text: str  # Text with error (red highlight)
    correction: str  # Corrected text (green)
    error_type: str  # Type of error (grammar, spelling, etc.)
    position: int    # Position in original text

@dataclass
class WritingEvaluation:
    """Data class for writing evaluation results"""
    original_text: str
    scores: Dict[str, int]  # Category scores out of 100
    overall_score: int
    improved_version: str  # Plain text improved version
    improved_version_html: str  # HTML version with inline error/correction highlighting
    error_highlights: List[ErrorHighlight]  # Errors with corrections
    # Legacy fields (kept for backward compatibility)
    strengths: List[str] = None
    improvements: List[str] = None
    suggestions: List[str] = None
    feedback_summary: str = None

class WritingEvaluationService:
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

    async def evaluate_writing(
        self,
        text: str,
        language: str = "english",
        writing_type: str = "general",
        user_level: str = "intermediate"
    ) -> WritingEvaluation:
        """
        Comprehensive writing evaluation using Gemini with improved error handling
        """
        try:
            # Generate evaluation prompt (using structured text, not JSON)
            evaluation_prompt = self._create_evaluation_prompt(text, language, writing_type, user_level)
            
            # Get evaluation from GenAI with safety settings
            response = await self.model.generate_content_async(
                evaluation_prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            # Check if response was blocked or empty
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning("Response was blocked or empty, using fallback evaluation")
                return self._create_fallback_evaluation(text)
            
            # Check finish reason
            candidate = response.candidates[0]
            if candidate.finish_reason != 1:  # 1 = STOP (successful completion)
                logger.warning(f"Response finish reason: {candidate.finish_reason}, using fallback")
                return self._create_fallback_evaluation(text)
            
            response_text = candidate.content.parts[0].text
            evaluation_data = self._parse_evaluation_response(response_text)

            # Generate improved version with error highlights
            improved_text, error_highlights = await self._generate_improved_version_with_highlights(
                text, evaluation_data, language, writing_type
            )

            # Generate HTML version with inline highlighting
            improved_html = self._generate_html_with_highlights(text, improved_text, error_highlights)

            # Create evaluation object
            evaluation = WritingEvaluation(
                original_text=text,
                scores=evaluation_data.get("scores", {}),
                overall_score=evaluation_data.get("overall_score", 0),
                improved_version=improved_text,
                improved_version_html=improved_html,
                error_highlights=error_highlights,
                strengths=evaluation_data.get("strengths", []),
                improvements=evaluation_data.get("improvements", []),
                suggestions=evaluation_data.get("suggestions", []),
                feedback_summary=evaluation_data.get("summary", "")
            )

            return evaluation
            
        except Exception as e:
            logger.error(f"Writing evaluation failed: {str(e)}")
            return self._create_fallback_evaluation(text)

    def _create_evaluation_prompt(self, text: str, language: str, writing_type: str, user_level: str) -> str:
        """
        Create evaluation prompt using structured text format (not JSON to avoid safety blocks)
        """
        return f"""
        As an experienced {language} language teacher, please evaluate this {writing_type} text written by a {user_level} level student.

        Text to evaluate: "{text}"

        Please provide a comprehensive assessment in this structured format:

        OVERALL SCORE: [number 0-100]

        DETAILED SCORES:
        Grammar: [number 0-100]
        Vocabulary: [number 0-100]
        Coherence: [number 0-100]
        Style: [number 0-100]
        Clarity: [number 0-100]
        Engagement: [number 0-100]

        STRENGTHS:
        - [strength 1]
        - [strength 2]
        - [strength 3]

        AREAS FOR IMPROVEMENT:
        - [improvement 1]
        - [improvement 2]
        - [improvement 3]

        SPECIFIC SUGGESTIONS:
        - [suggestion 1]
        - [suggestion 2]
        - [suggestion 3]
        - [suggestion 4]
        - [suggestion 5]

        SUMMARY: [2-3 sentences providing overall feedback and encouragement]

        Please be encouraging but provide honest, constructive feedback appropriate for a {user_level} level {language} learner.
        """

    def _parse_evaluation_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse structured text response and extract evaluation data
        """
        try:
            # Initialize with default values
            evaluation_data = {
                "scores": {"grammar": 75, "vocabulary": 75, "coherence": 75, "style": 75, "clarity": 75, "engagement": 75},
                "overall_score": 75,
                "strengths": ["Text provided for evaluation"],
                "improvements": ["Continue practicing"],
                "suggestions": ["Practice regularly", "Read more", "Get feedback"],
                "summary": "Keep up the good work with your language learning!"
            }
            
            lines = response_text.split('\n')
            current_section = None
            items = []
            
            for line in lines:
                line = line.strip()
                
                # Parse overall score
                if line.startswith('OVERALL SCORE:'):
                    score_match = re.search(r'(\d+)', line)
                    if score_match:
                        evaluation_data["overall_score"] = int(score_match.group(1))
                
                # Parse detailed scores
                elif any(category in line.lower() for category in ['grammar:', 'vocabulary:', 'coherence:', 'style:', 'clarity:', 'engagement:']):
                    for category in ['grammar', 'vocabulary', 'coherence', 'style', 'clarity', 'engagement']:
                        if category in line.lower():
                            score_match = re.search(r'(\d+)', line)
                            if score_match:
                                evaluation_data["scores"][category] = int(score_match.group(1))
                
                # Identify sections
                elif line.upper().startswith('STRENGTHS'):
                    current_section = 'strengths'
                    items = []
                elif line.upper().startswith('AREAS FOR IMPROVEMENT') or line.upper().startswith('IMPROVEMENTS'):
                    current_section = 'improvements'
                    items = []
                elif line.upper().startswith('SPECIFIC SUGGESTIONS') or line.upper().startswith('SUGGESTIONS'):
                    current_section = 'suggestions'
                    items = []
                elif line.upper().startswith('SUMMARY'):
                    current_section = 'summary'
                    summary_text = line.replace('SUMMARY:', '').strip()
                    if summary_text:
                        evaluation_data["summary"] = summary_text
                
                # Parse list items
                elif line.startswith('-') or line.startswith('•'):
                    item = line[1:].strip()
                    if item and current_section in ['strengths', 'improvements', 'suggestions']:
                        items.append(item)
                        evaluation_data[current_section] = items
                
                # Continue summary on new lines
                elif current_section == 'summary' and line and not line.startswith(('OVERALL', 'DETAILED', 'STRENGTHS', 'AREAS', 'SPECIFIC')):
                    if 'summary' in evaluation_data:
                        evaluation_data["summary"] += " " + line
                    else:
                        evaluation_data["summary"] = line
            
            # Ensure we have at least some items in each category
            if len(evaluation_data["strengths"]) == 0:
                evaluation_data["strengths"] = ["Clear communication attempt", "Shows learning effort"]
            
            if len(evaluation_data["improvements"]) == 0:
                evaluation_data["improvements"] = ["Continue practicing", "Focus on grammar accuracy"]
            
            if len(evaluation_data["suggestions"]) == 0:
                evaluation_data["suggestions"] = [
                    "Practice writing daily",
                    "Read more in the target language",
                    "Use grammar checking tools",
                    "Get feedback from others"
                ]
            
            return evaluation_data
            
        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            return self._get_default_evaluation_data()

    def _get_default_evaluation_data(self) -> Dict[str, Any]:
        """Get default evaluation data when parsing fails"""
        return {
            "scores": {"grammar": 75, "vocabulary": 75, "coherence": 75, "style": 75, "clarity": 75, "engagement": 75},
            "overall_score": 75,
            "strengths": ["Text submitted for evaluation", "Shows commitment to learning", "Clear attempt at communication"],
            "improvements": ["Continue practicing writing", "Focus on grammar accuracy", "Expand vocabulary usage"],
            "suggestions": [
                "Practice writing daily",
                "Read more in the target language",
                "Use grammar checking tools",
                "Get feedback from teachers or native speakers",
                "Study grammar rules systematically"
            ],
            "summary": "Keep practicing! Every writing attempt helps you improve your language skills."
        }

    async def _generate_improved_version_with_highlights(
        self, text: str, evaluation_data: Dict, language: str, writing_type: str
    ) -> Tuple[str, List[ErrorHighlight]]:
        """
        Generate improved version WITH error highlighting for frontend display
        """
        try:
            improvements = evaluation_data.get("improvements", [])
            improvements_text = ", ".join(improvements[:3])

            prompt = f"""
            As a {language} teacher, analyze this text and identify specific errors with corrections.

            Original text: "{text}"

            Please provide your response in this exact format:

            IMPROVED VERSION:
            [The complete improved text]

            ERROR CORRECTIONS:
            ERROR: [exact text with error] | CORRECTION: [corrected text] | TYPE: [grammar/spelling/punctuation/word choice]
            ERROR: [next error] | CORRECTION: [correction] | TYPE: [type]

            Focus on: {improvements_text}
            """

            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=1000
                ),
                safety_settings=self.safety_settings
            )

            if response.candidates and response.candidates[0].content.parts:
                response_text = response.candidates[0].content.parts[0].text.strip()
                improved_text, error_highlights = self._parse_error_highlights(text, response_text)
                return improved_text, error_highlights
            else:
                return text, []

        except Exception as e:
            logger.error(f"Failed to generate improved version with highlights: {e}")
            return text, []

    def _parse_error_highlights(self, original_text: str, response_text: str) -> Tuple[str, List[ErrorHighlight]]:
        """
        Parse the LLM response to extract improved version and error highlights
        """
        error_highlights = []
        improved_version = ""

        try:
            # Extract improved version
            if "IMPROVED VERSION:" in response_text:
                parts = response_text.split("ERROR CORRECTIONS:")
                improved_section = parts[0].replace("IMPROVED VERSION:", "").strip()
                # Clean up the improved version
                improved_version = improved_section.split('\n')[0].strip()
                if not improved_version:
                    # Try to get multi-line improved version
                    lines = improved_section.split('\n')
                    improved_version = ' '.join([l.strip() for l in lines if l.strip()])

            # Extract error corrections
            if "ERROR CORRECTIONS:" in response_text:
                corrections_section = response_text.split("ERROR CORRECTIONS:")[1]
                correction_lines = corrections_section.strip().split('\n')

                position = 0
                for line in correction_lines:
                    if "ERROR:" in line and "CORRECTION:" in line:
                        try:
                            # Parse: ERROR: text | CORRECTION: text | TYPE: type
                            parts = line.split('|')
                            if len(parts) >= 3:
                                error_text = parts[0].replace('ERROR:', '').strip()
                                correction = parts[1].replace('CORRECTION:', '').strip()
                                error_type = parts[2].replace('TYPE:', '').strip()

                                # Find position in original text
                                pos = original_text.lower().find(error_text.lower())
                                if pos == -1:
                                    pos = position
                                    position += len(error_text)

                                error_highlights.append(ErrorHighlight(
                                    error_text=error_text,
                                    correction=correction,
                                    error_type=error_type,
                                    position=pos
                                ))
                        except Exception as e:
                            logger.warning(f"Failed to parse error line: {line}, error: {e}")
                            continue

            # Use original text if improved version is empty
            if not improved_version:
                improved_version = original_text

        except Exception as e:
            logger.error(f"Failed to parse error highlights: {e}")
            improved_version = original_text

        return improved_version, error_highlights

    def _generate_html_with_highlights(
        self, original_text: str, improved_text: str, error_highlights: List[ErrorHighlight]
    ) -> str:
        """
        Generate HTML version with inline error/correction highlighting
        Shows: [error] -> correction in the improved text
        """
        try:
            if not error_highlights:
                # No errors, return plain improved text
                return f'<p class="improved-text">{improved_text}</p>'

            # Create HTML with inline highlighting
            html_parts = []

            # Add CSS styles inline
            css = """<style>
.improved-text-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.8;
    font-size: 16px;
}
.error-correction {
    display: inline-block;
    margin: 0 2px;
}
.error {
    background-color: #ffebee;
    color: #c62828;
    padding: 2px 6px;
    border-radius: 4px;
    text-decoration: line-through;
    font-weight: 500;
}
.arrow {
    color: #666;
    margin: 0 4px;
    font-weight: bold;
}
.correction {
    background-color: #e8f5e9;
    color: #2e7d32;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 600;
}
.error-label {
    display: inline-block;
    background: #ff9800;
    color: white;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 8px;
    margin-left: 4px;
    vertical-align: super;
}
</style>"""

            html_parts.append(css)
            html_parts.append('<div class="improved-text-container">')

            # Sort errors by position to process sequentially
            sorted_errors = sorted(error_highlights, key=lambda x: x.position)

            current_pos = 0
            processed_text = original_text

            for error in sorted_errors:
                # Find the error in the original text
                error_start = processed_text.lower().find(error.error_text.lower(), current_pos)

                if error_start == -1:
                    continue

                # Add text before error
                if error_start > current_pos:
                    html_parts.append(processed_text[current_pos:error_start])

                # Add error with correction
                html_parts.append(
                    f'<span class="error-correction">'
                    f'<span class="error">{error.error_text}</span>'
                    f'<span class="arrow">→</span>'
                    f'<span class="correction">{error.correction}</span>'
                    # f'<span class="error-label">{error.error_type}</span>'
                    f'</span>'
                )

                current_pos = error_start + len(error.error_text)

            # Add remaining text
            if current_pos < len(processed_text):
                html_parts.append(processed_text[current_pos:])

            html_parts.append('</div>')

            return ''.join(html_parts)

        except Exception as e:
            logger.error(f"Failed to generate HTML highlights: {e}")
            # Fallback to plain text
            return f'<p class="improved-text">{improved_text}</p>'

    async def _generate_improved_version(self, text: str, evaluation_data: Dict, language: str, writing_type: str) -> str:
        """
        Generate improved version with simple, safe prompt (legacy method)
        """
        try:
            improvements = evaluation_data.get("improvements", [])
            improvements_text = ", ".join(improvements[:3])

            prompt = f"""
            Please improve this {language} text by addressing these issues: {improvements_text}

            Original text: "{text}"

            Please provide only the improved version:
            """

            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=500
                ),
                safety_settings=self.safety_settings
            )

            if response.candidates and response.candidates[0].content.parts:
                improved = response.candidates[0].content.parts[0].text.strip()
                # Clean up the response
                improved = improved.replace('Improved version:', '').replace('Here is the improved text:', '').strip()
                return improved if improved else f"Enhanced version: {text}"
            else:
                return f"Revised version: {text}"

        except Exception as e:
            logger.error(f"Failed to generate improved version: {e}")
            return f"Keep practicing! Original: {text}"

    def _create_fallback_evaluation(self, text: str) -> WritingEvaluation:
        """
        Create a fallback evaluation when API calls fail
        """
        fallback_html = f'<p class="improved-text">{text}</p><p><em>Evaluation service temporarily unavailable</em></p>'

        return WritingEvaluation(
            original_text=text,
            scores={
                'grammar': 75,
                'vocabulary': 75,
                'coherence': 75,
                'style': 75,
                'clarity': 75,
                'engagement': 75
            },
            overall_score=75,
            improved_version=f"Keep practicing! Your text: {text}",
            improved_version_html=fallback_html,
            error_highlights=[],
            strengths=[
                "Text submitted for evaluation",
                "Shows effort in language learning",
                "Clear attempt at communication"
            ],
            improvements=[
                "Continue practicing regularly",
                "Focus on grammar accuracy",
                "Expand vocabulary usage"
            ],
            suggestions=[
                "Practice writing daily",
                "Read more in the target language",
                "Use grammar checking tools",
                "Get feedback from others",
                "Study grammar rules systematically"
            ],
            feedback_summary="Evaluation service temporarily unavailable, but keep up the great work with your language learning!"
        )

    async def get_writing_tips(self, language: str = "english", writing_type: str = "general") -> List[str]:
        """
        Get general writing tips for the specified language and type
        """
        prompt = f"""
        As an expert {language} writing instructor, provide 8 practical tips for improving {writing_type} writing.

        Please list them as:
        1. [tip 1]
        2. [tip 2]
        3. [tip 3]
        etc.

        Focus on actionable advice for {writing_type} writing in {language}.
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
                return self._get_default_tips(language, writing_type)
                
        except Exception as e:
            logger.error(f"Failed to get writing tips: {e}")
            return self._get_default_tips(language, writing_type)

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
        
        return tips if tips else self._get_default_tips("english", "general")

    def _get_default_tips(self, language: str, writing_type: str) -> List[str]:
        """Get default writing tips when API fails"""
        return [
            f"Write clear, concise sentences appropriate for {writing_type}",
            "Organize your thoughts before writing", 
            "Use varied sentence structures to maintain interest",
            "Choose precise vocabulary for your intended audience",
            "Proofread for grammar, spelling, and punctuation errors",
            f"Maintain consistent tone throughout your {writing_type} piece",
            "Create smooth transitions between ideas and paragraphs",
            "Support main points with relevant examples or evidence",
            "Read your work aloud to check for clarity and flow",
            "Revise and edit your work multiple times"
        ]

    async def analyze_writing_patterns(self, user_texts: List[str]) -> Dict[str, Any]:
        """
        Analyze writing patterns across multiple texts
        """
        if not user_texts:
            return {"error": "No texts provided for analysis"}
        
        try:
            combined_text = "\n\n---SAMPLE---\n\n".join(user_texts[:5])  # Limit to 5 samples
            
            prompt = f"""
            Analyze these {len(user_texts)} writing samples from the same author and identify patterns:

            {combined_text}

            Please provide analysis in this format:

            CONSISTENT STRENGTHS:
            - [strength 1]
            - [strength 2]

            RECURRING ISSUES:
            - [issue 1]
            - [issue 2]

            PROGRESS INDICATORS:
            - [progress 1]
            - [progress 2]

            RECOMMENDATIONS:
            - [recommendation 1]
            - [recommendation 2]
            - [recommendation 3]

            WRITING STYLE: [describe the dominant style and complexity level]
            """
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1024
                ),
                safety_settings=self.safety_settings
            )
            
            if response.candidates and response.candidates[0].content.parts:
                response_text = response.candidates[0].content.parts[0].text
                return self._parse_pattern_analysis(response_text, len(user_texts))
            else:
                return self._fallback_pattern_analysis(user_texts)
                
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return self._fallback_pattern_analysis(user_texts)

    def _parse_pattern_analysis(self, response_text: str, sample_count: int) -> Dict[str, Any]:
        """Parse pattern analysis response"""
        try:
            analysis = {
                "consistent_strengths": [],
                "recurring_issues": [],
                "progress_indicators": [],
                "personalized_recommendations": [],
                "evaluation_count": sample_count,
                "writing_style_profile": {
                    "dominant_style": "mixed",
                    "sentence_complexity": "developing",
                    "vocabulary_level": "intermediate"
                }
            }
            
            lines = response_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if line.upper().startswith('CONSISTENT STRENGTHS'):
                    current_section = 'consistent_strengths'
                elif line.upper().startswith('RECURRING ISSUES'):
                    current_section = 'recurring_issues'
                elif line.upper().startswith('PROGRESS INDICATORS'):
                    current_section = 'progress_indicators'
                elif line.upper().startswith('RECOMMENDATIONS'):
                    current_section = 'personalized_recommendations'
                elif line.upper().startswith('WRITING STYLE'):
                    style_desc = line.replace('WRITING STYLE:', '').strip()
                    analysis["writing_style_profile"]["dominant_style"] = style_desc
                elif line.startswith('-') and current_section:
                    item = line[1:].strip()
                    if item:
                        analysis[current_section].append(item)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse pattern analysis: {e}")
            return self._fallback_pattern_analysis([])

    def _fallback_pattern_analysis(self, user_texts: List[str]) -> Dict[str, Any]:
        """
        Fallback pattern analysis if main analysis fails
        """
        return {
            "consistent_strengths": [
                "Shows commitment to improving writing skills",
                "Regularly practices writing"
            ],
            "recurring_issues": [
                "Analysis temporarily unavailable"
            ],
            "progress_indicators": [
                f"Submitted {len(user_texts)} samples for analysis"
            ],
            "personalized_recommendations": [
                "Continue practicing regular writing",
                "Focus on one improvement area at a time",
                "Seek feedback from multiple sources"
            ],
            "evaluation_count": len(user_texts),
            "writing_style_profile": {
                "dominant_style": "developing",
                "sentence_complexity": "varies",
                "vocabulary_level": "intermediate"
            }
        }
