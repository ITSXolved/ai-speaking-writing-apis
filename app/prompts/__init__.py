# app/prompts/__init__.py
"""
Prompts package for Enhanced Multilingual Voice Learning Server
Contains teaching prompts and system instruction generation
"""

from .teaching_prompts import (
    TeachingPrompts, get_enhanced_system_instruction,
    get_feedback_prompt_for_mode, customize_prompt_for_language_pair
)

__all__ = [
    "TeachingPrompts", "get_enhanced_system_instruction",
    "get_feedback_prompt_for_mode", "customize_prompt_for_language_pair"
]