"""
FastAPI application setup and configuration
"""

from contextlib import asynccontextmanager
from typing import Optional, Callable
import structlog

from fastapi import FastAPI, Request, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timezone
from starlette.responses import JSONResponse

from app.config import (
    API_TITLE, API_VERSION, API_DESCRIPTION, CORS_ORIGINS,
    HEALTH_PORT, DEBUG, gemini_post_process_text
)
from app.api.routes import teaching, sessions, conversations, summaries
from app.api.deps import check_database_health, check_redis_health
from app.api.schemas import HealthResponse, StatusResponse, ErrorResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routes import email_reports, writing_evaluation, speaking_evaluation, cbt_evaluation, competency  # New imports

logger = structlog.get_logger(__name__)


# Add this to your imports at the top
from fastapi import FastAPI, Request, status, Body, WebSocket
from .websocket import websocket_handler, get_websocket_server_status

def create_app(lifespan: Optional[Callable] = None) -> FastAPI:
    """
    Create and configure the FastAPI application
    
    Args:
        lifespan: Optional lifespan context manager
        
    Returns:
        Configured FastAPI application
    """
    
    # Create FastAPI app
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        debug=DEBUG,
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(teaching.router)
    app.include_router(conversations.router)
    app.include_router(sessions.router)
    app.include_router(summaries.router)
     # Include new routes
    app.include_router(email_reports.router)
    app.include_router(writing_evaluation.router)
    app.include_router(speaking_evaluation.router)
    app.include_router(cbt_evaluation.router)
    app.include_router(competency.router)
    @app.get("/")
    async def root():
        return {
            "message": "Enhanced Multilingual Voice Learning Server",
            "version": "2.0.0",
            "features": [
                "Voice-based language learning",
                "Session management",
                "Progress tracking",
                "Email reports",  # New
                "Writing evaluation and improvement",  # New
                "Speaking evaluation from conversation data",  # New
                "CBT-based question evaluation",  # New
                "Competency tracking with day codes",  # New
                "Pattern analysis"  # New
            ]
        }
    
    # ADD WEBSOCKET ROUTES
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for voice learning sessions"""
        await websocket_handler(websocket)
    
    @app.websocket("/")
    async def root_websocket_endpoint(websocket: WebSocket):
        """Root WebSocket endpoint for voice learning sessions"""  
        await websocket_handler(websocket)
    
    # Add WebSocket status endpoint for monitoring
    @app.get("/api/websocket/status", tags=["websocket"])
    async def websocket_status():
        """Get WebSocket server status"""
        return await get_websocket_server_status()
    
    # ... rest of your existing exception handlers and middleware code ...
    # Add exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with structured error responses"""
        logger.warning("HTTP exception occurred", 
                      status_code=exc.status_code,
                      detail=str(exc.detail),
                      path=request.url.path)
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=str(exc.detail),
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""
        logger.warning("Validation error occurred",
                      errors=exc.errors(),
                      path=request.url.path)
        
        error_details = []
        for error in exc.errors():
            error_details.append({
                "type": error["type"],
                "message": error["msg"],
                "field": ".".join(str(loc) for loc in error["loc"])
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="Validation error",
                details=error_details,
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        logger.error("Unexpected exception occurred",
                    exception=str(exc),
                    exception_type=type(exc).__name__,
                    path=request.url.path)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal server error",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )
    
    # Add middleware for request logging
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all requests for monitoring and debugging"""
        logger.info("Request started",
                   method=request.method,
                   path=request.url.path,
                   query_params=dict(request.query_params),
                   client_ip=request.client.host if request.client else None)
        
        response = await call_next(request)
        
        logger.info("Request completed",
                   method=request.method,
                   path=request.url.path,
                   status_code=response.status_code)
        
        return response
    
    # Health check endpoints
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        return JSONResponse({
            "status": "ok",
            "time": datetime.now(timezone.utc).isoformat(),  # <-- stringify
            # include anything else you return here, eg:
            # "version": settings.VERSION,
        })
    # async def health_check():
    #     """
    #     Health check endpoint
        
    #     Checks the health of the application and its dependencies:
    #     - Database connectivity (Supabase)
    #     - Redis connectivity
    #     - Basic application status
        
    #     Returns 200 if all services are healthy, 503 if any service is down.
    #     """
    #     from datetime import datetime
        
    #     services = {}
    #     overall_status = "healthy"
        
    #     # Check database
    #     try:
    #         await check_database_health()
    #         services["database"] = "healthy"
    #     except Exception as e:
    #         services["database"] = f"unhealthy: {str(e)}"
    #         overall_status = "unhealthy"
        
    #     # Check Redis
    #     try:
    #         await check_redis_health()
    #         services["redis"] = "healthy"
    #     except Exception as e:
    #         services["redis"] = f"unhealthy: {str(e)}"
    #         overall_status = "unhealthy"
        
    #     response_data = HealthResponse(
    #         status=overall_status,
    #         timestamp=datetime.utcnow(),
    #         services=services,
    #         version=API_VERSION
    #     )
        
    #     status_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        
    #     return JSONResponse(
    #         status_code=status_code,
    #         content=response_data.dict()
    #     )
    
    @app.get("/status", response_model=StatusResponse, tags=["health"])
    async def status_endpoint():
        """
        Application status endpoint
        
        Provides general information about the application:
        - Service name and version
        - Available features
        - Configuration summary
        - Current metrics (if available)
        """
        try:
            # Get some basic metrics
            from app.services.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Count teaching modes
            modes_response = supabase.table("teaching_modes").select("count", count="exact").execute()
            teaching_modes_count = modes_response.count or 0
            
            # Count supported languages
            languages_response = supabase.table("supported_languages").select("count", count="exact").execute()
            languages_count = languages_response.count or 0
            
            # Get active sessions count from Redis (simplified)
            active_sessions = 0  # Would implement proper counting
            
            return StatusResponse(
                service="Enhanced Multilingual Voice Learning Server API",
                status="running",
                version=API_VERSION,
                features=[
                    "Teaching mode management",
                    "Session management with Redis",
                    "Real-time conversation tracking",
                    "Automatic language scoring",
                    "Learning summary generation",
                    "Multi-language support",
                    "WebSocket integration",
                    "RESTful API"
                ],
                active_sessions=active_sessions,
                supported_languages=languages_count,
                teaching_modes=teaching_modes_count
            )
            
        except Exception as e:
            logger.error("Error getting application status", error=str(e))
            return StatusResponse(
                service="Enhanced Multilingual Voice Learning Server API",
                status="running",
                version=API_VERSION,
                features=["Basic API functionality"],
                active_sessions=0,
                supported_languages=0,
                teaching_modes=0
            )
    
    @app.get("/", tags=["root"])
    async def root():
        """
        Root endpoint with API information
        """
        return {
            "service": API_TITLE,
            "version": API_VERSION,
            "description": API_DESCRIPTION,
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "health_url": "/health",
            "status_url": "/status",
            "api_base_url": "/api/v1"
        }
    
    # Add startup event logging
    @app.on_event("startup")
    async def startup_event():
        """Log application startup"""
        logger.info("FastAPI application starting up",
                   title=API_TITLE,
                   version=API_VERSION,
                   debug=DEBUG)
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Log application shutdown"""
        logger.info("FastAPI application shutting down")
    
    logger.info("FastAPI application configured",
               title=API_TITLE,
               version=API_VERSION,
               cors_origins=CORS_ORIGINS,
               debug=DEBUG)
    
    # Define POST endpoint for Gemini text processing
    @app.post("/api/gemini_post_process", tags=["llm"])
    async def gemini_post_process_endpoint(payload: dict = Body(...)):
        """
        LLM post-processing endpoint: Fixes spacing, punctuation, and grammar using Gemini.
        Expects: { "text": "raw text here" }
        Returns: { "processed_text": "cleaned text here" }
        """
        raw_text = payload.get("text", "")
        processed = gemini_post_process_text(raw_text)
        return {"processed_text": processed}
    
    return app


# Create default app instance
app = create_app()

# app/api/main.py - Updated to include new routes
