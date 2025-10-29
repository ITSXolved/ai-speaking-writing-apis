# app/services/gemini_optimization.py
# Additional helper functions optimized for Gemini 2.0 Flash Live

import json
import logging
import time
from typing import Dict, Any, Optional
import google.generativeai as genai
from functools import wraps

logger = logging.getLogger(__name__)

class GeminiFlashOptimizer:
    """
    Optimization utilities for Gemini 2.0 Flash Live model
    """
    
    def __init__(self):
        self.default_config = genai.types.GenerationConfig(
            temperature=0.3,
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048,
            response_mime_type="application/json"
        )
        
        # Rate limiting tracking
        self._request_times = []
        self._max_requests_per_minute = 60  # Adjust based on your quota
    
    def create_optimized_config(self, task_type: str) -> genai.types.GenerationConfig:
        """
        Create optimized generation config based on task type
        """
        configs = {
            "evaluation": genai.types.GenerationConfig(
                temperature=0.2,  # Very consistent for scoring
                top_p=0.7,
                top_k=30,
                max_output_tokens=1500,
                response_mime_type="application/json"
            ),
            "improvement": genai.types.GenerationConfig(
                temperature=0.4,  # More creative for rewriting
                top_p=0.9,
                top_k=50,
                max_output_tokens=1024
            ),
            "tips": genai.types.GenerationConfig(
                temperature=0.3,
                top_p=0.8,
                max_output_tokens=512,
                response_mime_type="application/json"
            ),
            "analysis": genai.types.GenerationConfig(
                temperature=0.2,  # Consistent analysis
                top_p=0.7,
                max_output_tokens=1200,
                response_mime_type="application/json"
            )
        }
        
        return configs.get(task_type, self.default_config)
    
    def rate_limit_check(self) -> bool:
        """
        Check if we're within rate limits
        """
        current_time = time.time()
        # Remove requests older than 1 minute
        self._request_times = [
            t for t in self._request_times 
            if current_time - t < 60
        ]
        
        if len(self._request_times) >= self._max_requests_per_minute:
            logger.warning("Rate limit approaching, request delayed")
            return False
        
        self._request_times.append(current_time)
        return True
    
    def create_structured_prompt(self, 
                                task: str, 
                                content: str, 
                                schema: Dict[str, Any],
                                context: Optional[Dict[str, str]] = None) -> str:
        """
        Create structured prompts optimized for Gemini 2.0 Flash Live
        """
        context = context or {}
        
        base_prompt = f"""
        Task: {task}

        Content to analyze:
        \"\"\"{content}\"\"\"
        
        Context:
        {self._format_context(context)}
        
        CRITICAL INSTRUCTIONS:
        1. Respond with ONLY valid JSON
        2. No markdown formatting or code blocks
        3. Follow the exact schema provided
        4. Be precise and consistent
        
        Required JSON Schema:
        {json.dumps(schema, indent=2)}
        
        Your response must be valid JSON that matches this schema exactly.
        """
        
        return base_prompt
    
    def _format_context(self, context: Dict[str, str]) -> str:
        """Format context information for prompts"""
        if not context:
            return "No additional context provided."
        
        formatted = []
        for key, value in context.items():
            formatted.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(formatted)
    
    def validate_json_response(self, response_text: str, expected_keys: list = None) -> Dict[str, Any]:
        """
        Validate and parse JSON response with fallback handling
        """
        try:
            # Clean the response text
            cleaned_text = self._clean_response_text(response_text)
            
            # Parse JSON
            data = json.loads(cleaned_text)
            
            # Validate expected keys if provided
            if expected_keys:
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    logger.warning(f"Missing keys in response: {missing_keys}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.debug(f"Raw response: {response_text[:500]}...")
            
            # Attempt to extract JSON from malformed response
            return self._extract_json_from_text(response_text)
    
    def _clean_response_text(self, text: str) -> str:
        """
        Clean response text to ensure valid JSON
        """
        # Remove markdown code block markers
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        # Remove any leading/trailing whitespace
        text = text.strip()
        
        # Find JSON object boundaries
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx + 1]
        
        return text
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Fallback method to extract JSON-like data from malformed responses
        """
        # This is a simplified fallback - implement based on your needs
        return {
            "error": "Failed to parse response",
            "raw_response": text[:200],
            "fallback_used": True
        }

# Decorator for automatic retries with exponential backoff
def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator to retry API calls with exponential backoff
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"API call failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"API call failed after {max_retries} attempts: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator

# Usage example for the writing evaluation service
def create_evaluation_schemas():
    """
    Define JSON schemas for different evaluation types
    """
    return {
        "writing_evaluation": {
            "scores": {
                "grammar": "integer (0-100)",
                "vocabulary": "integer (0-100)",
                "coherence": "integer (0-100)",
                "style": "integer (0-100)",
                "clarity": "integer (0-100)",
                "engagement": "integer (0-100)"
            },
            "overall_score": "integer (0-100)",
            "strengths": ["array of strings"],
            "improvements": ["array of strings"],
            "suggestions": ["array of strings"],
            "summary": "string (2-3 sentences)"
        },
        
        "pattern_analysis": {
            "consistent_strengths": ["array of strings"],
            "recurring_issues": ["array of strings"],
            "progress_indicators": ["array of strings"],
            "personalized_recommendations": ["array of strings"],
            "writing_style_profile": {
                "dominant_style": "string",
                "sentence_complexity": "string",
                "vocabulary_level": "string",
                "common_topics": ["array of strings"]
            }
        },
        
        "writing_tips": ["array of strings (8-10 items)"]
    }