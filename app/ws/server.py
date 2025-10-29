"""
WebSocket server for voice learning with service integration
Adapted from the original server.py with new service architecture
"""

import asyncio
import websockets
import json
import base64
import traceback
import logging
from typing import Dict
from datetime import datetime
from uuid import UUID

import structlog

from app.config import SERVER_HOST, SERVER_PORT
from app.services.teaching_service import teaching_service
from app.services.session_service import session_service
from app.services.conversation_service import conversation_service
from app.services.redis_client import session_manager
from app.domain.models import ConversationRole
from app.voice_session import VoiceSession

# Configure logging
logger = structlog.get_logger(__name__)

# Store active WebSocket sessions
active_websocket_sessions: Dict[str, VoiceSession] = {}


async def handle_websocket(websocket, path=None):
    """WebSocket handler with service integration"""
    session_id = f"session_{id(websocket)}"
    try:
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if websocket.remote_address else "unknown"
    except:
        client_info = "unknown"
    
    logger.info("New WebSocket connection", session_id=session_id, client_info=client_info)
    
    try:
        # Get supported data from services
        teaching_modes = await teaching_service.get_teaching_modes()
        supported_languages = await teaching_service.get_languages()
        default_scenarios = await teaching_service.get_scenarios()
        
        # Convert to the format expected by the client
        teaching_modes_dict = {mode.code: {
            "name": mode.name,
            "description": mode.description or "",
            "focus": mode.description or "",
            "icon": "🎯"  # Default icon
        } for mode in teaching_modes}
        
        supported_languages_dict = {lang.code: {
            "name": lang.label,
            "code": lang.code
        } for lang in supported_languages}
        
        default_scenarios_dict = {f"scenario_{i}": {
            "name": scenario.title,
            "description": scenario.prompt[:100] + "..." if len(scenario.prompt) > 100 else scenario.prompt,
            "level": "intermediate",  # Default level
            "context": scenario.prompt,
            "learning_objectives": ["General conversation practice"]
        } for i, scenario in enumerate(default_scenarios)}
        
        # Send welcome message
        welcome_message = {
            "type": "welcome",
            "message": "Connected to Enhanced Multilingual Voice Learning Server",
            "session_id": session_id,
            "supported_languages": supported_languages_dict,
            "default_scenarios": default_scenarios_dict,
            "teaching_modes": teaching_modes_dict
        }
        
        await websocket.send(json.dumps(welcome_message))
        logger.info("Welcome message sent", session_id=session_id)
        
        voice_session = None
        learning_session_id = None
        
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get("type")
                
                logger.debug("Received message", session_id=session_id, message_type=message_type)
                
                if message_type == "start_session":
                    # Extract parameters
                    mother_language = data.get("mother_language", "english").lower()
                    target_language = data.get("target_language", "english").lower()
                    user_level = data.get("user_level", "beginner").lower()
                    teaching_mode = data.get("teaching_mode", "conversation").lower()
                    user_external_id = data.get("user_external_id", f"user_{session_id}")
                    
                    # Validate languages and modes exist
                    source_lang = await teaching_service.get_language_by_code(mother_language)
                    target_lang = await teaching_service.get_language_by_code(target_language)
                    mode = await teaching_service.get_mode_by_code(teaching_mode)
                    
                    if not source_lang:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Mother language '{mother_language}' not supported"
                        }))
                        continue
                        
                    if not target_lang:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Target language '{target_language}' not supported"
                        }))
                        continue
                    
                    if not mode:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Teaching mode '{teaching_mode}' not supported"
                        }))
                        continue
                    
                    # Get scenario data (simplified)
                    scenario_id = data.get("scenario_id", "default")
                    scenario_data = {
                        "name": "General Conversation",
                        "context": "Practice general conversation skills",
                        "learning_objectives": ["Fluency", "Vocabulary", "Grammar"]
                    }
                    
                    # Close existing sessions
                    if voice_session:
                        await voice_session.close()
                        if hasattr(voice_session, '_listen_task') and voice_session._listen_task:
                            voice_session._listen_task.cancel()
                    
                    if learning_session_id:
                        # Close the learning session in services
                        try:
                            await session_service.close_session(learning_session_id)
                        except Exception as e:
                            logger.warning("Error closing previous learning session", 
                                         session_id=learning_session_id,
                                         error=str(e))
                    
                    # Create new learning session in services
                    learning_session = await session_service.create_session(
                        user_external_id=user_external_id,
                        mode_code=teaching_mode,
                        language_code=target_language,
                        metadata={
                            "mother_language": mother_language,
                            "user_level": user_level,
                            "scenario": scenario_data,
                            "websocket_session_id": session_id
                        }
                    )
                    
                    if not learning_session:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Failed to create learning session"
                        }))
                        continue
                    
                    learning_session_id = learning_session.id
                    
                    # Create voice session with learning session context
                    voice_session = VoiceSession(
                        websocket=websocket, 
                        scenario_data=scenario_data, 
                        mother_language=mother_language, 
                        target_language=target_language, 
                        user_level=user_level,
                        teaching_mode=teaching_mode,
                        learning_session_id=learning_session_id
                    )
                    active_websocket_sessions[session_id] = voice_session
                    
                    # Initialize voice session
                    if await voice_session.initialize():
                        # Start listening for responses
                        voice_session._listen_task = asyncio.create_task(voice_session.listen_for_responses())
                        
                        # Send confirmation
                        await websocket.send(json.dumps({
                            "type": "session_started",
                            "scenario": scenario_data,
                            "mother_language": mother_language,
                            "target_language": target_language,
                            "user_level": user_level,
                            "teaching_mode": teaching_mode,
                            "learning_session_id": str(learning_session_id),
                            "mode_info": teaching_modes_dict.get(teaching_mode, {})
                        }))
                        
                        logger.info("Voice session started", 
                                  session_id=session_id,
                                  learning_session_id=learning_session_id,
                                  teaching_mode=teaching_mode)
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Failed to initialize voice session"
                        }))
                
                elif message_type == "audio" and voice_session:
                    # Process incoming audio
                    audio_b64 = data.get("data")
                    if audio_b64:
                        try:
                            audio_data = base64.b64decode(audio_b64)
                            await voice_session.process_audio(audio_data)
                        except Exception as e:
                            logger.error("Error processing audio", error=str(e))
                
                elif message_type == "get_teaching_modes":
                    await websocket.send(json.dumps({
                        "type": "teaching_modes",
                        "data": teaching_modes_dict
                    }))
                
                elif message_type == "get_languages":
                    await websocket.send(json.dumps({
                        "type": "languages",
                        "data": supported_languages_dict
                    }))
                
                elif message_type == "get_scenarios":
                    await websocket.send(json.dumps({
                        "type": "scenarios",
                        "data": default_scenarios_dict
                    }))
                
                elif message_type == "end_session":
                    # End the sessions
                    if voice_session:
                        await voice_session.close()
                        if hasattr(voice_session, '_listen_task') and voice_session._listen_task:
                            voice_session._listen_task.cancel()
                        voice_session = None
                    
                    if learning_session_id:
                        # Close learning session and generate summary
                        summary = await session_service.close_session(learning_session_id)
                        
                        response = {
                            "type": "session_ended",
                            "message": "Session ended successfully"
                        }
                        
                        if summary:
                            response["summary"] = summary
                        
                        await websocket.send(json.dumps(response))
                        learning_session_id = None
                    else:
                        await websocket.send(json.dumps({
                            "type": "session_ended",
                            "message": "Session ended successfully"
                        }))
                    
                    if session_id in active_websocket_sessions:
                        del active_websocket_sessions[session_id]
                    
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON received", session_id=session_id, error=str(e))
                try:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except:
                    break
            except Exception as e:
                logger.error("Error handling message", session_id=session_id, error=str(e))
                try:
                    await websocket.send(json.dumps({
                        "type": "error", 
                        "message": "Internal server error"
                    }))
                except:
                    break
    
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
        logger.error("WebSocket traceback", traceback=traceback.format_exc())
    finally:
        # Cleanup
        try:
            if session_id in active_websocket_sessions:
                voice_session = active_websocket_sessions[session_id]
                if voice_session:
                    if hasattr(voice_session, '_listen_task') and voice_session._listen_task:
                        voice_session._listen_task.cancel()
                    await voice_session.close()
                del active_websocket_sessions[session_id]
            
            # Close learning session if still active
            if learning_session_id:
                try:
                    await session_service.close_session(learning_session_id)
                except Exception as e:
                    logger.warning("Error closing learning session during cleanup", 
                                 session_id=learning_session_id,
                                 error=str(e))
            
            logger.info("Cleaned up WebSocket session", session_id=session_id)
        except Exception as e:
            logger.error("Error during WebSocket cleanup", session_id=session_id, error=str(e))


async def start_websocket_server():
    """Start the WebSocket server"""
    logger.info("Starting WebSocket server",
               host=SERVER_HOST,
               port=SERVER_PORT)
    
    try:
        # Initialize Redis session manager
        await session_manager.initialize()
        
        # Start WebSocket server
        server = await websockets.serve(
            handle_websocket,
            SERVER_HOST,
            SERVER_PORT
        )
        
        logger.info("WebSocket Server started successfully",
                   host=SERVER_HOST,
                   port=SERVER_PORT)
        logger.info("WebSocket Features enabled",
                   features=[
                       "Real-time voice interaction",
                       "Service-based session management", 
                       "Automatic conversation logging",
                       "Real-time language scoring",
                       "Teaching mode support",
                       "Multi-language support"
                   ])
        
        # Keep server running
        await server.wait_closed()
            
    except Exception as e:
        logger.error("Failed to start WebSocket server", error=str(e))
        logger.error("WebSocket server traceback", traceback=traceback.format_exc())
        raise


async def get_websocket_server_status():
    """Get WebSocket server status for health checks"""
    try:
        active_sessions_count = len(active_websocket_sessions)
        
        # Get some basic statistics
        session_info = []
        for ws_session_id, voice_session in active_websocket_sessions.items():
            if hasattr(voice_session, 'learning_session_id'):
                session_info.append({
                    "websocket_session_id": ws_session_id,
                    "learning_session_id": str(voice_session.learning_session_id) if voice_session.learning_session_id else None,
                    "is_active": voice_session.is_active if hasattr(voice_session, 'is_active') else False,
                    "teaching_mode": voice_session.teaching_mode if hasattr(voice_session, 'teaching_mode') else None
                })
        
        return {
            "status": "running",
            "active_sessions": active_sessions_count,
            "server_host": SERVER_HOST,
            "server_port": SERVER_PORT,
            "session_details": session_info
        }
        
    except Exception as e:
        logger.error("Error getting WebSocket server status", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "active_sessions": 0
        }


if __name__ == "__main__":
    """Run WebSocket server standalone"""
    try:
        asyncio.run(start_websocket_server())
    except KeyboardInterrupt:
        logger.info("WebSocket server stopped by user")
    except Exception as e:
        logger.error("WebSocket server error", error=str(e))
        logger.error("Full traceback", traceback=traceback.format_exc())