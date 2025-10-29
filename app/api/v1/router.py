"""
Main API router - combines all endpoint routers
"""
from fastapi import APIRouter

from app.api.v1 import content, sessions, dashboard, unified, meta, skill_mastery, listening, xp_streaks

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(
    content.router,
    tags=["Content"]
)

api_router.include_router(
    sessions.router,
    tags=["Sessions"]
)

api_router.include_router(
    dashboard.router,
    tags=["Dashboard"]
)

api_router.include_router(
    unified.router,
    tags=["Unified Analytics"]
)

api_router.include_router(
    meta.router,
    tags=["Meta"]
)

api_router.include_router(
    skill_mastery.router,
    tags=["Skill Mastery"]
)

api_router.include_router(
    listening.router,
    tags=["Listening Evaluation"]
)

api_router.include_router(
    xp_streaks.router,
    tags=["XP & Streaks"]
)
