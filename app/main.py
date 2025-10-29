"""
Main entry point for the Enhanced Multilingual Voice Learning Server
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from app.config import (
    API_PORT, SERVER_HOST, HEALTH_PORT, LOG_LEVEL,
    API_TITLE, API_VERSION, API_DESCRIPTION, CORS_ORIGINS,
    ENABLE_EMAIL_REPORTS, ENABLE_WRITING_EVALUATION, ENABLE_PATTERN_ANALYSIS,
    validate_email_config, validate_writing_evaluation_config, get_feature_status
)
from app.api.main import create_app
from app.ws.server import start_websocket_server
from app.services.supabase_client import get_supabase_client
from app.services.redis_client import get_redis_client


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def validate_new_services():
    """Validate new email and writing evaluation services"""
    validation_results = {}
    
    # Validate email service
    if ENABLE_EMAIL_REPORTS:
        try:
            from app.services.email_service import EmailService
            email_service = EmailService()
            validation_results["email_service"] = "initialized"
            logger.info("Email service initialized successfully")
        except Exception as e:
            validation_results["email_service"] = f"failed: {str(e)}"
            logger.error("Email service initialization failed", error=str(e))
    else:
        validation_results["email_service"] = "disabled"
        logger.info("Email service disabled")
    
    # Validate writing evaluation service
    if ENABLE_WRITING_EVALUATION:
        try:
            from app.services.writing_evaluation_service import WritingEvaluationService
            writing_service = WritingEvaluationService()
            validation_results["writing_evaluation_service"] = "initialized"
            logger.info("Writing evaluation service initialized successfully")
        except Exception as e:
            validation_results["writing_evaluation_service"] = f"failed: {str(e)}"
            logger.error("Writing evaluation service initialization failed", error=str(e))
    else:
        validation_results["writing_evaluation_service"] = "disabled"
        logger.info("Writing evaluation service disabled")
    
    return validation_results


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Enhanced Multilingual Voice Learning Server...")
    
    # Log feature status
    feature_status = get_feature_status()
    logger.info("Feature status", **feature_status)
    
    # Test database connections
    try:
        supabase = get_supabase_client()
        response = supabase.table("teaching_modes").select("count", count="exact").execute()
        logger.info("Supabase connection successful", mode_count=response.count)
    except Exception as e:
        logger.error("Failed to connect to Supabase", error=str(e))
        # Don't raise - allow app to start without Supabase for testing
    
    try:
        redis = await get_redis_client()
        await redis.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        # Don't raise - allow app to start without Redis for testing
    
    # Validate new services
    service_validation = await validate_new_services()
    logger.info("Service validation completed", **service_validation)
    
    # Validate configurations
    if ENABLE_EMAIL_REPORTS and not validate_email_config():
        logger.warning("Email configuration is invalid - email features may not work properly")
    
    if ENABLE_WRITING_EVALUATION and not validate_writing_evaluation_config():
        logger.warning("Writing evaluation configuration is invalid - writing features may not work properly")
    
    # Test database schema for new features
    try:
        supabase = get_supabase_client()
        
        # Check if new tables exist
        if ENABLE_WRITING_EVALUATION:
            try:
                result = supabase.table("writing_evaluations").select("count", count="exact").limit(1).execute()
                logger.info("Writing evaluations table accessible", count=result.count)
            except Exception as e:
                logger.warning("Writing evaluations table not found - may need to run database migrations", error=str(e))
        
        if ENABLE_EMAIL_REPORTS:
            try:
                result = supabase.table("email_reports").select("count", count="exact").limit(1).execute()
                logger.info("Email reports table accessible", count=result.count)
            except Exception as e:
                logger.warning("Email reports table not found - may need to run database migrations", error=str(e))
                
    except Exception as e:
        logger.warning("Could not validate database schema for new features", error=str(e))
    
    # Start WebSocket server (comment out for single-port Cloud Run)
    # ws_server_task = asyncio.create_task(start_websocket_server())
    
    logger.info("Services started successfully")
    logger.info("Available features", 
                email_reports=ENABLE_EMAIL_REPORTS,
                writing_evaluation=ENABLE_WRITING_EVALUATION,
                pattern_analysis=ENABLE_PATTERN_ANALYSIS)
    
    yield
    
    # Cleanup
    logger.info("Shutting down services...")
    # ws_server_task.cancel()
    
    try:
        redis = await get_redis_client()
        await redis.close()
        logger.info("Redis connection closed")
    except Exception:
        pass
    
    logger.info("Shutdown complete")


# Create the FastAPI app at module level for ASGI
app = create_app(lifespan=lifespan)


# Add startup event to log feature information
@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("Enhanced Multilingual Voice Learning Server started")
    logger.info("API Documentation available at /docs")
    logger.info("Server configuration",
                host=SERVER_HOST,
                api_port=API_PORT,
                health_port=HEALTH_PORT,
                log_level=LOG_LEVEL)


# For direct execution
if __name__ == "__main__":
    # Configure logging level
    logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper()))
    
    # Log startup information
    logger.info("Starting Enhanced Multilingual Voice Learning Server")
    logger.info("Version", version=API_VERSION)
    logger.info("Configuration loaded")
    
    # Log enabled features
    features = []
    if ENABLE_EMAIL_REPORTS:
        features.append("Email Reports")
    if ENABLE_WRITING_EVALUATION:
        features.append("Writing Evaluation")
    if ENABLE_PATTERN_ANALYSIS:
        features.append("Pattern Analysis")
    
    logger.info("Enabled features", features=features)
    
    # Validate critical configurations
    config_issues = []
    if ENABLE_EMAIL_REPORTS and not validate_email_config():
        config_issues.append("Email configuration invalid")
    if ENABLE_WRITING_EVALUATION and not validate_writing_evaluation_config():
        config_issues.append("Writing evaluation configuration invalid")
    
    if config_issues:
        logger.warning("Configuration issues detected", issues=config_issues)
        logger.warning("Some features may not work properly")
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", signal=signum)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the server
    logger.info("Starting uvicorn server", host=SERVER_HOST, port=API_PORT)
    uvicorn.run(
        "app.main:app",
        host=SERVER_HOST,
        port=API_PORT,
        log_level=LOG_LEVEL.lower(),
        access_log=True,
        reload=False  # Set to True for development
    )
# """
# Main entry point for the Enhanced Multilingual Voice Learning Server
# """

# import asyncio
# import logging
# import signal
# import sys
# from contextlib import asynccontextmanager

# import structlog
# import uvicorn
# from fastapi import FastAPI

# from app.config import (
#     API_PORT, SERVER_HOST, HEALTH_PORT, LOG_LEVEL,
#     API_TITLE, API_VERSION, API_DESCRIPTION, CORS_ORIGINS
# )
# from app.api.main import create_app
# from app.ws.server import start_websocket_server
# from app.services.supabase_client import get_supabase_client
# from app.services.redis_client import get_redis_client


# # Configure structured logging
# structlog.configure(
#     processors=[
#         structlog.stdlib.filter_by_level,
#         structlog.stdlib.add_logger_name,
#         structlog.stdlib.add_log_level,
#         structlog.stdlib.PositionalArgumentsFormatter(),
#         structlog.processors.TimeStamper(fmt="iso"),
#         structlog.processors.StackInfoRenderer(),
#         structlog.processors.format_exc_info,
#         structlog.processors.UnicodeDecoder(),
#         structlog.processors.JSONRenderer()
#     ],
#     context_class=dict,
#     logger_factory=structlog.stdlib.LoggerFactory(),
#     wrapper_class=structlog.stdlib.BoundLogger,
#     cache_logger_on_first_use=True,
# )

# logger = structlog.get_logger(__name__)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Application lifespan manager"""
#     logger.info("Starting Enhanced Multilingual Voice Learning Server...")
    
#     # Test database connections
#     try:
#         supabase = get_supabase_client()
#         response = supabase.table("teaching_modes").select("count", count="exact").execute()
#         logger.info("Supabase connection successful", mode_count=response.count)
#     except Exception as e:
#         logger.error("Failed to connect to Supabase", error=str(e))
#         # Don't raise - allow app to start without Supabase for testing
    
#     try:
#         redis = await get_redis_client()
#         await redis.ping()
#         logger.info("Redis connection successful")
#     except Exception as e:
#         logger.error("Failed to connect to Redis", error=str(e))
#         # Don't raise - allow app to start without Redis for testing
    
#     # Start WebSocket server (comment out for single-port Cloud Run)
#     # ws_server_task = asyncio.create_task(start_websocket_server())
    
#     logger.info("Services started")
#     yield
    
#     # Cleanup
#     logger.info("Shutting down services...")
#     # ws_server_task.cancel()
    
#     try:
#         redis = await get_redis_client()
#         await redis.close()
#     except Exception:
#         pass
    
#     logger.info("Shutdown complete")


# # Create the FastAPI app at module level for ASGI
# app = create_app(lifespan=lifespan)


# # For direct execution
# if __name__ == "__main__":
#     # Configure logging level
#     logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper()))
    
#     # Setup signal handlers
#     def signal_handler(signum, frame):
#         logger.info("Received shutdown signal", signal=signum)
#         sys.exit(0)
    
#     signal.signal(signal.SIGINT, signal_handler)
#     signal.signal(signal.SIGTERM, signal_handler)
    
#     # Start the server
#     uvicorn.run(
#         "app.main:app",
#         host=SERVER_HOST,
#         port=API_PORT,
#         log_level=LOG_LEVEL.lower(),
#         access_log=True
#     )

    