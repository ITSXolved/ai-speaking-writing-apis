"""
Evaluation and scoring logic for language learning
"""

import re
from typing import Dict, List, Any, Optional
import structlog

from app.domain.models import ScoringMetrics, ScoringWeights, ScoringRubric, ScoringResult
from app.config import DEFAULT_SCORING_WEIGHTS, DEFAULT_SCORING_SCALES

logger = structlog.get_logger(__name__)


class LanguageEvaluator:
    """Core language evaluation engine"""
    
    def __init__(self):
        self.default_weights = ScoringWeights(**DEFAULT_SCORING_WEIGHTS)
        self.default_scales = DEFAULT_SCORING_SCALES
    
    def evaluate_text(self, text: str, rubric: Optional[ScoringRubric] = None, 
                     mode_code: str = "conversation") -> ScoringResult:
        """
        Evaluate a text input and return scoring metrics
        
        Args:
            text: The text to evaluate
            rubric: Custom scoring rubric (optional)
            mode_code: Teaching mode for mode-specific adjustments
            
        Returns:
            ScoringResult with metrics and total score
        """
        if not text or not text.strip():
            return ScoringResult(
                metrics=ScoringMetrics(fluency=0, vocabulary=0, grammar=0, pronunciation=0),
                total_score=0.0,
                feedback="No text provided for evaluation"
            )
        
        # Use provided rubric or create default
        if rubric is None:
            rubric = ScoringRubric(
                weights=self.default_weights,
                scales=self.default_scales
            )
        
        # Evaluate each metric
        fluency_score = self._evaluate_fluency(text)
        vocabulary_score = self._evaluate_vocabulary(text)
        grammar_score = self._evaluate_grammar(text)
        pronunciation_score = self._evaluate_pronunciation(text)
        
        # Create metrics object
        metrics = ScoringMetrics(
            fluency=fluency_score,
            vocabulary=vocabulary_score,
            grammar=grammar_score,
            pronunciation=pronunciation_score
        )
        
        # Calculate weighted total score
        total_score = self._calculate_total_score(metrics, rubric.weights)
        
        # Apply mode-specific adjustments
        mode_adjustments = self._apply_mode_adjustments(
            metrics, total_score, mode_code
        )
        
        if mode_adjustments:
            total_score = mode_adjustments.get("adjusted_score", total_score)
        
        # Normalize score to 0-100 scale
        normalized_score = (total_score / rubric.scales["max"]) * 100
        
        return ScoringResult(
            metrics=metrics,
            total_score=round(normalized_score, 2),
            mode_specific_adjustments=mode_adjustments,
            feedback=self._generate_feedback(metrics, mode_code)
        )
    
    def _evaluate_fluency(self, text: str) -> float:
        """
        Evaluate fluency based on text characteristics
        Considers: sentence structure, flow, hesitation markers
        """
        text_clean = text.strip().lower()
        
        # Basic fluency indicators
        sentence_count = len([s for s in re.split(r'[.!?]+', text_clean) if s.strip()])
        word_count = len(text_clean.split())
        
        if word_count == 0:
            return 0.0
        
        # Check for hesitation markers
        hesitation_patterns = ['um', 'uh', 'er', 'like', '...', 'uhm']
        hesitations = sum(text_clean.count(marker) for marker in hesitation_patterns)
        hesitation_ratio = hesitations / word_count
        
        # Check for incomplete sentences
        incomplete_markers = ['...', 'uh', 'um']
        incomplete_count = sum(text_clean.count(marker) for marker in incomplete_markers)
        
        # Base score calculation
        base_score = 3.0  # Start with middle score
        
        # Adjust for sentence structure
        if sentence_count > 0:
            words_per_sentence = word_count / sentence_count
            if 5 <= words_per_sentence <= 20:  # Good sentence length
                base_score += 0.5
            elif words_per_sentence < 3:  # Too short/fragmentary
                base_score -= 1.0
        
        # Adjust for hesitations
        if hesitation_ratio < 0.1:  # Less than 10% hesitations
            base_score += 1.0
        elif hesitation_ratio > 0.3:  # More than 30% hesitations
            base_score -= 1.5
        
        # Adjust for completeness
        if incomplete_count == 0:
            base_score += 0.5
        
        return max(0.0, min(5.0, base_score))
    
    def _evaluate_vocabulary(self, text: str) -> float:
        """
        Evaluate vocabulary usage and variety
        """
        words = text.lower().split()
        
        if not words:
            return 0.0
        
        # Calculate vocabulary metrics
        unique_words = set(words)
        vocabulary_diversity = len(unique_words) / len(words) if words else 0
        
        # Check for advanced vocabulary (simple heuristic)
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall'
        }
        
        advanced_words = unique_words - common_words
        advanced_ratio = len(advanced_words) / len(unique_words) if unique_words else 0
        
        # Base score calculation
        base_score = 2.0
        
        # Adjust for vocabulary diversity
        if vocabulary_diversity > 0.8:  # High diversity
            base_score += 1.5
        elif vocabulary_diversity > 0.6:  # Good diversity
            base_score += 1.0
        elif vocabulary_diversity < 0.3:  # Low diversity
            base_score -= 1.0
        
        # Adjust for advanced vocabulary usage
        if advanced_ratio > 0.4:  # Good use of advanced words
            base_score += 1.0
        elif advanced_ratio > 0.2:  # Some advanced words
            base_score += 0.5
        
        # Adjust for total vocabulary size
        if len(unique_words) > 20:
            base_score += 0.5
        elif len(unique_words) < 5:
            base_score -= 0.5
        
        return max(0.0, min(5.0, base_score))
    
    def _evaluate_grammar(self, text: str) -> float:
        """
        Evaluate grammar correctness (simplified heuristic approach)
        """
        if not text.strip():
            return 0.0
        
        # Basic grammar checks
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        base_score = 3.5  # Start optimistic
        
        # Check for basic sentence structure
        grammar_issues = 0
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check for capitalization at start
            if sentence and not sentence[0].isupper():
                grammar_issues += 1
            
            # Check for basic subject-verb patterns (very simple)
            words = sentence_lower.split()
            if len(words) > 0:
                # Look for common grammatical patterns
                has_verb = any(word in ['is', 'are', 'was', 'were', 'have', 'has', 'had', 
                                      'do', 'does', 'did', 'can', 'will', 'would', 'could', 
                                      'should', 'may', 'might'] for word in words)
                
                if len(words) > 2 and not has_verb:
                    # Might be missing auxiliary verbs
                    grammar_issues += 0.5
        
        # Check for repeated words (might indicate confusion)
        words = text.lower().split()
        repeated_sequences = 0
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                repeated_sequences += 1
        
        if repeated_sequences > 2:
            grammar_issues += 1
        
        # Adjust score based on issues found
        issue_penalty = grammar_issues * 0.5
        final_score = base_score - issue_penalty
        
        return max(0.0, min(5.0, final_score))
    
    def _evaluate_pronunciation(self, text: str) -> float:
        """
        Evaluate pronunciation based on text transcription quality
        (In a real system, this would use audio analysis)
        """
        if not text.strip():
            return 0.0
        
        # For text-based evaluation, we look at transcription quality indicators
        words = text.split()
        
        # Check for unclear transcription indicators
        unclear_markers = ['[unclear]', '[inaudible]', '???', '[pause]', '[silence]']
        unclear_count = sum(text.lower().count(marker) for marker in unclear_markers)
        
        # Check for pronunciation-related transcription issues
        pronunciation_issues = 0
        
        # Look for repeated letters (might indicate unclear pronunciation)
        repeated_letter_pattern = re.compile(r'(.)\1{2,}')
        repeated_matches = repeated_letter_pattern.findall(text.lower())
        pronunciation_issues += len(repeated_matches)
        
        # Check for very short responses (might indicate pronunciation difficulty)
        if len(words) < 3 and len(text.strip()) < 10:
            pronunciation_issues += 1
        
        # Base score
        base_score = 4.0  # Start optimistic for pronunciation
        
        # Adjust for clarity issues
        if unclear_count == 0:
            base_score += 0.5
        else:
            base_score -= unclear_count * 0.5
        
        # Adjust for pronunciation issues
        base_score -= pronunciation_issues * 0.3
        
        return max(0.0, min(5.0, base_score))
    
    def _calculate_total_score(self, metrics: ScoringMetrics, weights: ScoringWeights) -> float:
        """
        Calculate weighted total score from individual metrics
        """
        total = (
            metrics.fluency * weights.fluency +
            metrics.vocabulary * weights.vocabulary +
            metrics.grammar * weights.grammar +
            metrics.pronunciation * weights.pronunciation
        )
        
        return total
    
    def _apply_mode_adjustments(self, metrics: ScoringMetrics, total_score: float, 
                              mode_code: str) -> Optional[Dict[str, Any]]:
        """
        Apply teaching mode-specific adjustments to scoring
        """
        adjustments = {}
        adjusted_score = total_score
        
        if mode_code == "grammar":
            # Weight grammar more heavily in grammar mode
            grammar_boost = (metrics.grammar - 2.5) * 0.3  # Boost/penalty from middle
            adjusted_score += grammar_boost
            adjustments["grammar_focus_adjustment"] = grammar_boost
            
        elif mode_code == "pronunciation":
            # Weight pronunciation more heavily
            pronunciation_boost = (metrics.pronunciation - 2.5) * 0.3
            adjusted_score += pronunciation_boost
            adjustments["pronunciation_focus_adjustment"] = pronunciation_boost
            
        elif mode_code == "vocabulary":
            # Weight vocabulary more heavily
            vocabulary_boost = (metrics.vocabulary - 2.5) * 0.3
            adjusted_score += vocabulary_boost
            adjustments["vocabulary_focus_adjustment"] = vocabulary_boost
            
        elif mode_code == "conversation":
            # Weight fluency more heavily in conversation mode
            fluency_boost = (metrics.fluency - 2.5) * 0.2
            adjusted_score += fluency_boost
            adjustments["fluency_focus_adjustment"] = fluency_boost
        
        if adjustments:
            adjustments["adjusted_score"] = max(0.0, min(5.0, adjusted_score))
            adjustments["original_score"] = total_score
            return adjustments
        
        return None
    
    def _generate_feedback(self, metrics: ScoringMetrics, mode_code: str) -> str:
        """
        Generate textual feedback based on scoring metrics
        """
        feedback_parts = []
        
        # Overall performance
        avg_score = (metrics.fluency + metrics.vocabulary + metrics.grammar + metrics.pronunciation) / 4
        
        if avg_score >= 4.0:
            feedback_parts.append("Excellent work!")
        elif avg_score >= 3.0:
            feedback_parts.append("Good progress!")
        elif avg_score >= 2.0:
            feedback_parts.append("Keep practicing!")
        else:
            feedback_parts.append("More practice needed.")
        
        # Specific areas
        if metrics.fluency < 2.5:
            feedback_parts.append("Focus on speaking more smoothly.")
        
        if metrics.vocabulary < 2.5:
            feedback_parts.append("Try using more varied vocabulary.")
        
        if metrics.grammar < 2.5:
            feedback_parts.append("Pay attention to grammar rules.")
        
        if metrics.pronunciation < 2.5:
            feedback_parts.append("Work on pronunciation clarity.")
        
        # Mode-specific feedback
        if mode_code == "grammar" and metrics.grammar >= 4.0:
            feedback_parts.append("Great grammar usage!")
        elif mode_code == "pronunciation" and metrics.pronunciation >= 4.0:
            feedback_parts.append("Clear pronunciation!")
        elif mode_code == "vocabulary" and metrics.vocabulary >= 4.0:
            feedback_parts.append("Rich vocabulary usage!")
        elif mode_code == "conversation" and metrics.fluency >= 4.0:
            feedback_parts.append("Very natural conversation flow!")
        
        return " ".join(feedback_parts)


# Global evaluator instance
language_evaluator = LanguageEvaluator()