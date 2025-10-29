"""
API routes package initialization
Exports all route modules for easy importing
"""

from . import teaching, sessions, conversations, summaries

__all__ = ["teaching", "sessions", "conversations", "summaries"]