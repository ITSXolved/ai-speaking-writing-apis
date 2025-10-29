"""
Utility functions for the Enhanced Multilingual Voice Learning Server
Contains helper functions and shared utilities adapted for service architecture
"""

import socket
import logging
from datetime import datetime
from aiohttp import web
from typing import Dict, Any, Optional
from uuid import UUID
import json

import structlog
from app.config import (
    SERVER_HOST, SERVER_PORT, HEALTH_PORT
)

logger = structlog.get_logger(__name__)


async def health_check(request, active_sessions_count=0):
    """Enhanced health check endpoint with service diagnostics"""
    try:
        # Test WebSocket server responsiveness
        websocket_status = "healthy"
        try:
            # Simple connection test
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1.0)
            result = test_socket.connect_ex((SERVER_HOST, SERVER_PORT))
            test_socket.close()
            if result != 0:
                websocket_status = "port_unreachable"
        except Exception as e:
            websocket_status = f"test_failed: {str(e)}"
        
        # Test service health
        service_status = {}
        
        # Test database
        try:
            from app.services.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            response = supabase.table("teaching_modes").select("count", count="exact").execute()
            service_status["database"] = "healthy"
            teaching_modes_count = response.count or 0
        except Exception as e:
            service_status["database"] = f"unhealthy: {str(e)}"
            teaching_modes_count = 0
        
        # Test Redis
        try:
            from app.services.redis_client import session_manager
            await session_manager.initialize()
            if await session_manager.health_check():
                service_status["redis"] = "healthy"
            else:
                service_status["redis"] = "unhealthy: failed health check"
        except Exception as e:
            service_status["redis"] = f"unhealthy: {str(e)}"
        
        # Test supported languages count
        try:
            from app.services.teaching_service import teaching_service
            languages = await teaching_service.get_languages()
            languages_count = len(languages)
            service_status["teaching_service"] = "healthy"
        except Exception as e:
            service_status["teaching_service"] = f"unhealthy: {str(e)}"
            languages_count = 0
            
        return web.json_response({
            "status": "healthy",
            "service": "enhanced-multilingual-voice-learning-server",
            "websocket_status": websocket_status,
            "service_status": service_status,
            "active_sessions": active_sessions_count,
            "supported_languages": languages_count,
            "teaching_modes": teaching_modes_count,
            "server_port": SERVER_PORT,
            "features": [
                "Service-based architecture",
                "REST API with FastAPI", 
                "WebSocket voice integration",
                "Redis session management",
                "Supabase data persistence",
                "Real-time language scoring",
                "Learning summary generation",
                "Multi-language support"
            ],
            "timestamp": datetime.now().isoformat(),
            "cloud_run_optimized": True
        })
    except Exception as e:
        logger.error("Health check error", error=str(e))
        return web.json_response({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def status_handler(request, active_sessions_count=0):
    """Status endpoint handler with service information"""
    try:
        # Get service statistics
        from app.services.teaching_service import teaching_service
        from app.services.supabase_client import get_supabase_client
        
        teaching_modes = await teaching_service.get_teaching_modes()
        languages = await teaching_service.get_languages()
        scenarios = await teaching_service.get_scenarios()
        
        # Get session statistics
        supabase = get_supabase_client()
        sessions_response = supabase.table("sessions").select("count", count="exact").execute()
        total_sessions = sessions_response.count or 0
        
        # Get active sessions from Redis
        from app.services.redis_client import session_manager
        await session_manager.initialize()
        redis_healthy = await session_manager.health_check()
        
        return web.json_response({
            "service": "Enhanced Multilingual Voice Learning Server",
            "websocket_url": f"ws://{request.host.split(':')[0]}:{SERVER_PORT}/",
            "rest_api_url": f"http://{request.host}/api/v1",
            "status": "running",
            "cloud_run_optimized": True,
            "architecture": "microservices",
            "features": [
                "Service-based architecture with dependency injection",
                "REST API for teaching metadata management", 
                "Session lifecycle management with Redis",
                "Real-time conversation logging and scoring",
                "Automatic learning summary generation",
                "WebSocket integration for voice sessions",
                "Multi-language support with dynamic configuration",
                "Structured logging and monitoring"
            ],
            "active_sessions": active_sessions_count,
            "statistics": {
                "total_teaching_modes": len(teaching_modes),
                "total_languages": len(languages),
                "total_scenarios": len(scenarios),
                "total_sessions_created": total_sessions,
                "redis_healthy": redis_healthy
            },
            "available_modes": {mode.code: {
                "name": mode.name,
                "description": mode.description or "No description",
                "focus": mode.description or f"{mode.name} practice"
            } for mode in teaching_modes},
            "supported_languages_list": [lang.code for lang in languages],
            "api_endpoints": {
                "teaching_modes": "/api/v1/teaching-modes",
                "scenarios": "/api/v1/scenarios", 
                "languages": "/api/v1/languages",
                "sessions": "/api/v1/sessions",
                "conversations": "/api/v1/sessions/{session_id}/turns",
                "summaries": "/api/v1/summaries"
            }
        })
    except Exception as e:
        logger.error("Error getting status", error=str(e))
        return web.json_response({
            "service": "Enhanced Multilingual Voice Learning Server",
            "status": "running",
            "error": f"Error getting full status: {str(e)}",
            "basic_info": True
        })


def validate_session_parameters(data):
    """Validate session parameters with service integration"""
    mother_language = data.get("mother_language", "english").lower()
    target_language = data.get("target_language", "english").lower()
    teaching_mode = data.get("teaching_mode", "conversation").lower()
    
    # Note: In the service-based architecture, validation happens at the service level
    # This function is kept for backward compatibility but should use service validation
    
    return None  # No error - let services handle validation


def get_scenario_data(data):
    """Extract and validate scenario data from request"""
    scenario_id = data.get("scenario_id")
    custom_scenario = data.get("custom_scenario")
    
    if custom_scenario:
        # Validate custom scenario has required fields
        required_fields = ["name", "context", "learning_objectives"]
        if all(field in custom_scenario for field in required_fields):
            return custom_scenario
        else:
            return None  # Invalid custom scenario
    elif scenario_id:
        # Return identifier for service lookup
        return {"scenario_id": scenario_id}
    else:
        return {
            "name": "General Practice",
            "context": "General language practice session",
            "learning_objectives": ["Conversation skills", "Vocabulary", "Grammar"]
        }


def validate_custom_scenario(custom_scenario, scenario_id):
    """Validate custom scenario data"""
    if not custom_scenario or not scenario_id:
        return {
            "type": "error",
            "message": "Both scenario_id and scenario data are required"
        }
    
    required_fields = ["name", "context", "learning_objectives"]
    if not all(field in custom_scenario for field in required_fields):
        return {
            "type": "error",
            "message": f"Custom scenario must include: {required_fields}"
        }
    
    return None  # No error


def log_client_info(websocket, session_id):
    """Log client connection information"""
    try:
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if websocket.remote_address else "unknown"
        logger.info("WebSocket client connected", session_id=session_id, client_info=client_info)
        return client_info
    except Exception as e:
        logger.warning("Could not get client info", session_id=session_id, error=str(e))
        return "unknown"


def create_welcome_message(session_id, services_data: Optional[Dict[str, Any]] = None):
    """Create welcome message for new WebSocket connections with service data"""
    base_message = {
        "type": "welcome",
        "message": "Connected to Enhanced Multilingual Voice Learning Server",
        "session_id": session_id,
        "server_info": {
            "cloud_run_optimized": True,
            "architecture": "service-based",
            "supported_features": [
                "audio_streaming", 
                "real_time_feedback", 
                "multilingual", 
                "session_persistence",
                "automatic_scoring",
                "learning_summaries"
            ]
        }
    }
    
    if services_data:
        base_message.update(services_data)
    
    return base_message


def create_session_started_message(
    scenario_data, 
    mother_language, 
    target_language, 
    user_level, 
    teaching_mode,
    learning_session_id: Optional[UUID] = None,
    mode_info: Optional[Dict[str, Any]] = None
):
    """Create session started confirmation message with service integration"""
    message = {
        "type": "session_started",
        "scenario": scenario_data,
        "mother_language": mother_language,
        "target_language": target_language,
        "user_level": user_level,
        "teaching_mode": teaching_mode,
        "mode_info": mode_info or {},
        "session_management": {
            "redis_session": True,
            "database_persistence": True,
            "automatic_scoring": True,
            "learning_summary": True
        }
    }
    
    if learning_session_id:
        message["learning_session_id"] = str(learning_session_id)
    
    return message


def validate_websocket_headers(websocket):
    """Validate WebSocket upgrade headers"""
    try:
        if not hasattr(websocket, 'request_headers'):
            return False, "Missing WebSocket headers"
            
        # Check for required WebSocket upgrade headers
        upgrade_header = websocket.request_headers.get('upgrade', '').lower()
        connection_header = websocket.request_headers.get('connection', '').lower()
        
        if upgrade_header != 'websocket' or 'upgrade' not in connection_header:
            return False, "Invalid WebSocket upgrade headers"
        
        return True, "Valid headers"
    except Exception as e:
        logger.warning("Error validating WebSocket headers", error=str(e))
        return False, f"Header validation error: {str(e)}"


def is_message_too_large(message, max_size=10 * 1024 * 1024):
    """Check if message exceeds size limit (default 10MB)"""
    try:
        return len(message) > max_size
    except TypeError:
        # Handle case where message is not a string/bytes
        try:
            return len(str(message)) > max_size
        except:
            return False


def format_error_response(error_message: str, error_type: str = "error", details: Optional[Dict[str, Any]] = None):
    """Format standardized error response"""
    response = {
        "type": error_type,
        "message": error_message,
        "timestamp": datetime.now().isoformat()
    }
    
    if details:
        response["details"] = details
    
    return response


def format_success_response(data: Any, message_type: str = "success", message: Optional[str] = None):
    """Format standardized success response"""
    response = {
        "type": message_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    
    if message:
        response["message"] = message
    
    return response


async def get_service_statistics():
    """Get comprehensive service statistics"""
    try:
        from app.services.teaching_service import teaching_service
        from app.services.redis_client import session_manager
        from app.services.supabase_client import get_supabase_client
        
        # Initialize services
        await session_manager.initialize()
        supabase = get_supabase_client()
        
        # Get teaching data
        teaching_modes = await teaching_service.get_teaching_modes()
        languages = await teaching_service.get_languages()
        scenarios = await teaching_service.get_scenarios()
        
        # Get session statistics
        sessions_response = supabase.table("sessions").select("count", count="exact").execute()
        conversations_response = supabase.table("conversations").select("count", count="exact").execute()
        summaries_response = supabase.table("session_summaries").select("count", count="exact").execute()
        
        # Get service health
        redis_healthy = await session_manager.health_check()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "service_health": {
                "database": "healthy",  # If we got here, database is working
                "redis": "healthy" if redis_healthy else "unhealthy"
            },
            "data_counts": {
                "teaching_modes": len(teaching_modes),
                "supported_languages": len(languages),
                "available_scenarios": len(scenarios),
                "total_sessions": sessions_response.count or 0,
                "total_conversations": conversations_response.count or 0,
                "total_summaries": summaries_response.count or 0
            },
            "features_enabled": [
                "REST API",
                "WebSocket support",
                "Real-time scoring",
                "Session persistence",
                "Learning summaries",
                "Multi-language support"
            ]
        }
        
    except Exception as e:
        logger.error("Error getting service statistics", error=str(e))
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "service_health": {
                "status": "error"
            }
        }


def create_conversation_context(
    session_data: Dict[str, Any],
    turn_history: Optional[list] = None
) -> Dict[str, Any]:
    """Create conversation context for voice sessions"""
    context = {
        "session_id": session_data.get("session_id"),
        "user_level": session_data.get("user_level", "beginner"),
        "teaching_mode": session_data.get("teaching_mode", "conversation"),
        "target_language": session_data.get("target_language", "english"),
        "mother_language": session_data.get("mother_language", "english"),
        "scenario": session_data.get("scenario", {}),
        "turn_count": len(turn_history) if turn_history else 0,
        "last_turn_index": session_data.get("last_turn_index", 0)
    }
    
    if turn_history:
        # Add recent conversation context
        recent_turns = turn_history[-5:] if len(turn_history) > 5 else turn_history
        context["recent_conversation"] = recent_turns
    
    return context


def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input for safety and consistency"""
    if not text:
        return ""
    
    # Remove excessive whitespace and limit length
    sanitized = text.strip()[:max_length]
    
    # Remove any potential script tags or dangerous content
    import re
    sanitized = re.sub(r'<script.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized


def generate_session_id() -> str:
    """Generate a unique session identifier"""
    from uuid import uuid4
    return str(uuid4())


def parse_language_code(language_input: str) -> str:
    """Parse and normalize language code input"""
    # Convert common language names to codes
    language_mapping = {
        "english": "en",
        "spanish": "es", 
        "french": "fr",
        "german": "de",
        "italian": "it",
        "portuguese": "pt",
        "chinese": "zh",
        "japanese": "ja",
        "korean": "ko",
        "arabic": "ar",
        "russian": "ru",
        "hindi": "hi"
    }
    
    normalized = language_input.lower().strip()
    return language_mapping.get(normalized, normalized)


def calculate_session_duration(start_time: datetime, end_time: Optional[datetime] = None) -> Dict[str, Any]:
    """Calculate session duration and statistics"""
    if end_time is None:
        end_time = datetime.now()
    
    duration = end_time - start_time
    duration_seconds = duration.total_seconds()
    
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "duration_minutes": round(duration_seconds / 60, 2),
        "duration_formatted": str(duration).split('.')[0]  # Remove microseconds
    }