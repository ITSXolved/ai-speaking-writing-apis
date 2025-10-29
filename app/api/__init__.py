"""
API package for Enhanced Multilingual Voice Learning Server
Contains FastAPI routes, schemas, and dependencies
"""

from .main import create_app, app

__all__ = ["create_app", "app"]