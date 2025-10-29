# """
# Voice session management and GenAI integration with service architecture
# Enhanced version with turn-complete conversation logging to prevent fragmented database entries
# """

"""
Voice session management and GenAI integration with service architecture
Enhanced version with turn-complete conversation logging to prevent fragmented database entries
Fixed transcription handling to prevent string indexing errors
"""

import asyncio
import json
import base64
import traceback
from collections import deque
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

import websockets
import structlog
from google import genai
from google.genai import types
from google.genai.types import (
    LiveConnectConfig,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
)

from app.config import (
    MODEL, GEMINI_API_KEY, SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE
)
from app.prompts.teaching_prompts import get_enhanced_system_instruction
from app.services.conversation_service import conversation_service
from app.services.scoring_service import scoring_service
from app.domain.models import ConversationRole

logger = structlog.get_logger(__name__)

# Initialize GenAI client
client = genai.Client(
    http_options=types.HttpOptions(api_version="v1beta"),
    api_key=GEMINI_API_KEY,
)


def create_config(
    scenario_data: dict, 
    mother_language: str, 
    target_language: str, 
    user_level: str, 
    teaching_mode: str = "conversation"
) -> LiveConnectConfig:
    """Create LiveConnectConfig for the session with teaching mode parameters"""
    return LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        speech_config=SpeechConfig(
            voice_config=VoiceConfig( 
                prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Zephyr")
            )
        ),
        system_instruction=get_enhanced_system_instruction(
            scenario_data, 
            mother_language, 
            target_language, 
            user_level, 
            teaching_mode
        ),
        tools=[],
        temperature=0.7,
        max_output_tokens=8192,
    )


def normalize_transcription_text(text: str, language: str = "english") -> str:
    """Post-process transcription text to remove unwanted spaces in words for Latin scripts."""
    import re
    if language.lower() == "english":
        # Collapse multiple spaces, then remove spaces within words (but keep between words)
        # This regex removes spaces between letters, but not between words
        # e.g., "Tha t's fa nta sti c!" -> "That's fantastic!"
        # Step 1: Collapse multiple spaces
        text = re.sub(r"\s+", " ", text)
        # Step 2: Remove spaces between letters (not between words)
        # This will join letters separated by a single space, but not words
        # We'll use a conservative approach: only remove spaces between letters (a-zA-Z)
        text = re.sub(r"(?<=\w) (?=\w)", "", text)
        return text.strip()
    # For other scripts (e.g., Hindi), just collapse multiple spaces
    return re.sub(r"\s+", " ", text).strip()


def safe_extract_text(transcription_obj) -> str:
    """Safely extract text from transcription object, handling various data types."""
    if transcription_obj is None:
        return ""
    
    # If it's already a string, return it
    if isinstance(transcription_obj, str):
        return transcription_obj.strip()
    
    # If it's an object with text attribute
    if hasattr(transcription_obj, 'text'):
        text = transcription_obj.text
        if isinstance(text, str):
            return text.strip()
    
    # If it's a dictionary with text key
    if isinstance(transcription_obj, dict) and 'text' in transcription_obj:
        text = transcription_obj['text']
        if isinstance(text, str):
            return text.strip()
    
    # Try to convert to string as fallback
    try:
        return str(transcription_obj).strip()
    except:
        return ""


class TurnBuffer:
    """Buffer to accumulate transcription fragments during a turn"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset buffer for new turn"""
        self.user_fragments = []
        self.assistant_fragments = []
        self.user_complete_text = ""
        self.assistant_complete_text = ""
        self.turn_evaluation = None
        self.turn_start_time = datetime.utcnow()
        self.has_user_input = False
        self.has_assistant_response = False
    
    def add_user_fragment(self, text: str):
        """Add user transcription fragment"""
        if text and text.strip():
            self.user_fragments.append(text.strip())
            self.has_user_input = True
            # Update complete text by joining fragments
            self.user_complete_text = " ".join(self.user_fragments)
    
    def add_assistant_fragment(self, text: str):
        """Add assistant transcription fragment"""
        if text and text.strip():
            self.assistant_fragments.append(text.strip())
            self.has_assistant_response = True
            # Update complete text by joining fragments
            self.assistant_complete_text = " ".join(self.assistant_fragments)
    
    def set_evaluation(self, evaluation: Dict[str, Any]):
        """Set turn evaluation data"""
        self.turn_evaluation = evaluation
    
    def is_ready_for_logging(self) -> bool:
        """Check if turn has enough data for logging"""
        return (self.has_user_input and 
                len(self.user_complete_text.strip()) > 0)
    
    def get_user_text(self) -> str:
        """Get complete user text"""
        return self.user_complete_text.strip()
    
    def get_assistant_text(self) -> str:
        """Get complete assistant text"""
        return self.assistant_complete_text.strip()
    
    def get_turn_summary(self) -> Dict[str, Any]:
        """Get summary of current turn buffer state"""
        return {
            "user_fragments": len(self.user_fragments),
            "assistant_fragments": len(self.assistant_fragments),
            "user_text_length": len(self.user_complete_text),
            "assistant_text_length": len(self.assistant_complete_text),
            "has_evaluation": self.turn_evaluation is not None,
            "ready_for_logging": self.is_ready_for_logging()
        }


class VoiceSession:
    """Manages a voice learning session with GenAI integration and turn-complete logging"""
    
    def __init__(
        self, 
        websocket, 
        scenario_data=None, 
        mother_language="english", 
        target_language="english", 
        user_level="beginner", 
        teaching_mode="conversation",
        learning_session_id: Optional[UUID] = None
    ):
        self.websocket = websocket
        self.scenario_data = scenario_data or self._get_default_scenario()
        self.mother_language = mother_language
        self.target_language = target_language
        self.user_level = user_level
        self.teaching_mode = teaching_mode
        self.learning_session_id = learning_session_id
        
        # GenAI session management
        self.session = None
        self.session_manager = None
        self.is_active = False
        self._listen_task = None
        
        # Configuration
        self.config = create_config(
            self.scenario_data, 
            mother_language, 
            target_language, 
            user_level, 
            teaching_mode
        )
        
        # Audio buffering
        self.audio_buffer = deque(maxlen=10)
        
        # Session statistics
        self.restart_count = 0
        self.max_restarts = 3
        self.session_active_time = 0
        self.turn_count = 0
        
        # Service integration
        self.conversation_service = conversation_service
        self.scoring_service = scoring_service
        
        # Turn buffering for complete logging
        self.turn_buffer = TurnBuffer()
        self.last_sent_user_text = ""
        self.last_sent_assistant_text = ""
        
    def _get_default_scenario(self) -> Dict[str, Any]:
        """Get default scenario data"""
        return {
            "name": "General Conversation",
            "context": "General conversation practice with friendly guidance",
            "learning_objectives": ["Fluency", "Vocabulary", "Grammar", "Pronunciation"]
        }
        
    async def initialize(self):
        """Initialize the GenAI session with persistent connection"""
        try:
            logger.info("Initializing voice session", 
                       scenario=self.scenario_data['name'],
                       mother_language=self.mother_language,
                       target_language=self.target_language,
                       teaching_mode=self.teaching_mode,
                       learning_session_id=self.learning_session_id)
            
            # Test API key
            if not GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY is not set")
                return False
                
            logger.info("Testing GenAI API connection...")
            
            # Create session manager
            self.session_manager = client.aio.live.connect(model=MODEL, config=self.config)
            self.session = await self.session_manager.__aenter__()
            self.is_active = True
            self.restart_count = 0
            self.session_active_time = asyncio.get_event_loop().time()
            
            logger.info("Voice session initialized successfully", 
                       teaching_mode=self.teaching_mode,
                       learning_session_id=self.learning_session_id)
            
            # Send any buffered audio
            if self.audio_buffer:
                logger.info("Sending buffered audio", chunks=len(self.audio_buffer))
                for audio_data in list(self.audio_buffer):
                    try:
                        await self.session.send_realtime_input(
                            media={
                                "data": audio_data,
                                "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                            }
                        )
                        await asyncio.sleep(0.01)  # Small delay between chunks
                    except Exception as e:
                        logger.error("Error sending buffered audio", error=str(e))
                        break
                self.audio_buffer.clear()
                        
            return True
        except Exception as e:
            logger.error("Failed to initialize voice session", error=str(e))
            traceback.print_exc()
            self.is_active = False
            return False
    
    async def process_audio(self, audio_data):
        """Send audio data to GenAI with session management"""
        # Always buffer recent audio for potential restart
        self.audio_buffer.append(audio_data)
        
        if not self.is_active or not self.session:
            logger.warning("Session not active during audio processing - buffering audio")
            return
            
        try:
            await self.session.send_realtime_input(
                media={
                    "data": audio_data,
                    "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                }
            )
            
            # If listener task is done, restart it
            if self._listen_task and self._listen_task.done():
                logger.info("Response listener stopped - restarting...")
                self._listen_task = asyncio.create_task(self.listen_for_responses())
                
        except Exception as e:
            logger.error("Error processing audio", error=str(e))
            await asyncio.sleep(0.1)
    
    async def listen_for_responses(self):
        """Listen for responses from GenAI and handle turn-complete conversation logging"""
        if not self.session or not self.is_active:
            return
            
        logger.info("Starting response listener for voice session with turn-complete logging", 
                   teaching_mode=self.teaching_mode,
                   learning_session_id=self.learning_session_id)
        
        while self.is_active:
            try:
                async for response in self.session.receive():
                    if not self.is_active:
                        logger.info("Session marked inactive - stopping listener")
                        break
                    
                    # Debug logging for response structure
                    logger.debug("Raw response received", 
                                response_type=type(response).__name__,
                                has_server_content=hasattr(response, 'server_content'))
                    
                    # Handle server content (audio, transcriptions, etc.)
                    server_content = response.server_content if hasattr(response, 'server_content') else None
                    
                    if server_content and hasattr(server_content, 'model_turn') and server_content.model_turn:
                        # Process audio output
                        for part in server_content.model_turn.parts:
                            if hasattr(part, 'inline_data') and part.inline_data and self.is_active:
                                try:
                                    audio_b64 = base64.b64encode(part.inline_data.data).decode()
                                    await self.websocket.send_text(json.dumps({
                                        "type": "audio",
                                        "data": audio_b64,
                                        "sample_rate": RECEIVE_SAMPLE_RATE
                                    }))
                                except websockets.exceptions.ConnectionClosed:
                                    logger.info("WebSocket closed during audio send")
                                    self.is_active = False
                                    return
                                except Exception as e:
                                    logger.error("Error sending audio", error=str(e))
                                    continue
                    
                    # Handle output transcriptions (assistant responses) - BUFFER ONLY
                    if (self.is_active and server_content and 
                        hasattr(server_content, 'output_transcription') and 
                        server_content.output_transcription):
                        
                        try:
                            assistant_text = safe_extract_text(server_content.output_transcription)
                            
                            if assistant_text:  # Only process if we have text
                                # Add to turn buffer instead of logging immediately
                                self.turn_buffer.add_assistant_fragment(assistant_text)
                                
                                # Send transcription to client only if it's new content
                                current_complete_text = self.turn_buffer.get_assistant_text()
                                if current_complete_text != self.last_sent_assistant_text:
                                    await self.websocket.send_text(json.dumps({
                                        "type": "transcription",
                                        "text": current_complete_text,
                                        "source": "assistant"
                                    }))
                                    self.last_sent_assistant_text = current_complete_text
                                
                                logger.debug("Buffered assistant transcription fragment", 
                                           fragment=assistant_text,
                                           total_length=len(current_complete_text))
                            
                        except websockets.exceptions.ConnectionClosed:
                            self.is_active = False
                            return
                        except Exception as e:
                            logger.error("Error handling assistant transcription", error=str(e))
                            logger.debug("Assistant transcription debug info",
                                        transcription_type=type(server_content.output_transcription),
                                        transcription_value=str(server_content.output_transcription)[:100])
                    
                    # Handle input transcriptions (user speech) - BUFFER ONLY
                    if (self.is_active and server_content and
                        hasattr(server_content, 'input_transcription') and 
                        server_content.input_transcription):
                        
                        try:
                            user_text = safe_extract_text(server_content.input_transcription)
                            
                            if user_text:  # Only process if we have text
                                # Add to turn buffer instead of logging immediately
                                self.turn_buffer.add_user_fragment(user_text)
                                
                                # Send transcription to client only if it's new content
                                current_complete_text = self.turn_buffer.get_user_text()
                                if current_complete_text != self.last_sent_user_text:
                                    await self.websocket.send_text(json.dumps({
                                        "type": "transcription", 
                                        "text": current_complete_text,
                                        "source": "user"
                                    }))
                                    self.last_sent_user_text = current_complete_text
                                
                                logger.debug("Buffered user transcription fragment", 
                                           fragment=user_text,
                                           total_length=len(current_complete_text))
                            
                        except websockets.exceptions.ConnectionClosed:
                            self.is_active = False
                            return
                        except Exception as e:
                            logger.error("Error handling user transcription", error=str(e))
                            logger.debug("User transcription debug info",
                                        transcription_type=type(server_content.input_transcription),
                                        transcription_value=str(server_content.input_transcription)[:100])
                        
                    # Handle turn completion - LOG COMPLETE TURN HERE
                    if self.is_active and server_content and hasattr(server_content, 'turn_complete') and server_content.turn_complete:
                        try:
                            await self.websocket.send_text(json.dumps({
                                "type": "turn_complete"
                            }))
                            
                            self.turn_count += 1
                            
                            # Log the complete turn to database now
                            await self._log_complete_turn()
                            
                            logger.info("Turn completed and logged", 
                                       turn_count=self.turn_count,
                                       learning_session_id=self.learning_session_id,
                                       buffer_summary=self.turn_buffer.get_turn_summary())
                            
                            # Reset buffers and tracking for next turn
                            self.turn_buffer.reset()
                            self.last_sent_user_text = ""
                            self.last_sent_assistant_text = ""
                            
                            # Clear audio buffer after successful turn but keep session active
                            self.audio_buffer.clear()
                            
                            # Update session active time
                            self.session_active_time = asyncio.get_event_loop().time()
                            
                        except websockets.exceptions.ConnectionClosed:
                            self.is_active = False
                            return
                        except Exception as e:
                            logger.error("Error processing turn complete", error=str(e))
                            logger.debug("Turn complete debug info",
                                        server_content_type=type(server_content),
                                        has_turn_complete=hasattr(server_content, 'turn_complete'))
                
                # Continue listening
                if self.is_active:
                    await asyncio.sleep(0.1)
                else:
                    break
                    
            except asyncio.CancelledError:
                logger.info("Response listener cancelled")
                raise
            except websockets.exceptions.ConnectionClosedOK:
                logger.info("GenAI session closed normally")
                break
            except websockets.exceptions.ConnectionClosed:
                logger.info("GenAI session connection lost")
                break
            except Exception as e:
                logger.error("Error in response listener", error=str(e))
                logger.error("Response listener traceback", traceback=traceback.format_exc())
                if self.is_active:
                    logger.info("Error occurred but session still active - continuing...")
                    await asyncio.sleep(0.5)
                else:
                    break
                
        logger.info("Response listener stopped completely")
    
    async def _log_complete_turn(self):
        """Log the complete turn to conversation service"""
        if not self.learning_session_id or not self.turn_buffer.is_ready_for_logging():
            logger.debug("Skipping turn logging - no session ID or insufficient data",
                        has_session_id=bool(self.learning_session_id),
                        buffer_ready=self.turn_buffer.is_ready_for_logging())
            return
        
        try:
            # Get complete texts from buffer
            user_text = self.turn_buffer.get_user_text()
            assistant_text = self.turn_buffer.get_assistant_text()

            # Post-process texts before logging
            user_text = normalize_transcription_text(user_text, self.target_language)
            assistant_text = normalize_transcription_text(assistant_text, self.target_language)
            
            if not user_text:
                logger.debug("Skipping turn logging - no user text")
                return
            
            # Log user turn with scoring
            logger.info("Logging complete user turn", 
                       user_text_length=len(user_text),
                       session_id=self.learning_session_id)
            
            user_turn_result = await self.conversation_service.add_turn(
                session_id=self.learning_session_id,
                role=ConversationRole.USER,
                text=user_text
            )
            
            if user_turn_result:
                logger.info("User turn logged successfully", 
                           conversation_id=user_turn_result.get("conversation_id"),
                           turn_index=user_turn_result.get("turn_index"),
                           scored=bool(user_turn_result.get("evaluation")))
                
                # Send scoring feedback if available
                if user_turn_result.get("evaluation"):
                    await self.websocket.send_text(json.dumps({
                        "type": "feedback",
                        "data": {
                            "total_score": user_turn_result["evaluation"]["total_score"],
                            "metrics": user_turn_result["evaluation"]["metrics"],
                            "teaching_mode": self.teaching_mode,
                            "turn_index": user_turn_result["turn_index"]
                        }
                    }))
            else:
                logger.warning("Failed to log user turn",
                             session_id=self.learning_session_id)
            
            # Log assistant turn if we have assistant text
            if assistant_text:
                logger.info("Logging complete assistant turn", 
                           assistant_text_length=len(assistant_text),
                           session_id=self.learning_session_id)
                
                assistant_turn_result = await self.conversation_service.add_turn(
                    session_id=self.learning_session_id,
                    role=ConversationRole.ASSISTANT,
                    text=assistant_text
                )
                
                if assistant_turn_result:
                    logger.info("Assistant turn logged successfully", 
                               conversation_id=assistant_turn_result.get("conversation_id"),
                               turn_index=assistant_turn_result.get("turn_index"))
                else:
                    logger.warning("Failed to log assistant turn",
                                 session_id=self.learning_session_id)
            
        except Exception as e:
            logger.error("Error logging complete turn", 
                        session_id=self.learning_session_id,
                        error=str(e))
    
    async def close(self):
        """Close the session gracefully"""
        logger.info("Closing voice session", 
                   learning_session_id=self.learning_session_id,
                   turn_count=self.turn_count)
        self.is_active = False
        
        # Cancel listening task first
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await asyncio.wait_for(self._listen_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        # Close session manager
        try:
            if self.session_manager and self.session:
                await self.session_manager.__aexit__(None, None, None)
                logger.info("GenAI session closed properly")
        except Exception as e:
            logger.error("Error closing GenAI session", error=str(e))
        finally:
            self.session = None
            self.session_manager = None
    
    async def restart_session(self):
        """Restart the session if needed (for error recovery)"""
        if self.restart_count >= self.max_restarts:
            logger.error("Maximum restart attempts reached", 
                        restart_count=self.restart_count,
                        max_restarts=self.max_restarts)
            return False
            
        logger.info("Restarting voice session", 
                   attempt=self.restart_count + 1,
                   max_attempts=self.max_restarts)
        
        # Close current session
        await self.close()
        
        # Wait a moment before restarting
        await asyncio.sleep(1.0)
        
        # Increment restart count
        self.restart_count += 1
        
        # Try to initialize again
        return await self.initialize()
    
    def get_session_info(self):
        """Get current session information"""
        return {
            "session_active": self.is_active,
            "teaching_mode": self.teaching_mode,
            "scenario": self.scenario_data,
            "mother_language": self.mother_language,
            "target_language": self.target_language,
            "user_level": self.user_level,
            "learning_session_id": str(self.learning_session_id) if self.learning_session_id else None,
            "restart_count": self.restart_count,
            "session_active_time": self.session_active_time,
            "audio_buffer_size": len(self.audio_buffer),
            "turn_count": self.turn_count,
            "turn_buffer_summary": self.turn_buffer.get_turn_summary(),
            "service_integration": {
                "conversation_logging": bool(self.learning_session_id),
                "automatic_scoring": bool(self.learning_session_id),
                "session_persistence": bool(self.learning_session_id),
                "turn_complete_logging": True
            }
        }
    
    async def get_session_statistics(self):
        """Get session statistics from services"""
        if not self.learning_session_id:
            return None
        
        try:
            stats = await self.scoring_service.calculate_session_statistics(
                self.learning_session_id
            )
            return stats
        except Exception as e:
            logger.error("Error getting session statistics", 
                        learning_session_id=self.learning_session_id,
                        error=str(e))
            return None
# import asyncio
# import json
# import base64
# import traceback
# from collections import deque
# from datetime import datetime
# from typing import Optional, Dict, Any
# from uuid import UUID

# import websockets
# import structlog
# from google import genai
# from google.genai import types
# from google.genai.types import (
#     LiveConnectConfig,
#     SpeechConfig,
#     VoiceConfig,
#     PrebuiltVoiceConfig,
# )

# from app.config import (
#     MODEL, GEMINI_API_KEY, SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE
# )
# from app.prompts.teaching_prompts import get_enhanced_system_instruction
# from app.services.conversation_service import conversation_service
# from app.services.scoring_service import scoring_service
# from app.domain.models import ConversationRole

# logger = structlog.get_logger(__name__)

# # Initialize GenAI client
# client = genai.Client(
#     http_options=types.HttpOptions(api_version="v1beta"),
#     api_key=GEMINI_API_KEY,
# )


# def create_config(
#     scenario_data: dict, 
#     mother_language: str, 
#     target_language: str, 
#     user_level: str, 
#     teaching_mode: str = "conversation"
# ) -> LiveConnectConfig:
#     """Create LiveConnectConfig for the session with teaching mode parameters"""
#     return LiveConnectConfig(
#         response_modalities=["AUDIO"],
#         output_audio_transcription={},
#         input_audio_transcription={},
#         speech_config=SpeechConfig(
#             voice_config=VoiceConfig( 
#                 prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Zephyr")
#             )
#         ),
#         system_instruction=get_enhanced_system_instruction(
#             scenario_data, 
#             mother_language, 
#             target_language, 
#             user_level, 
#             teaching_mode
#         ),
#         tools=[],
#         temperature=0.7,
#         max_output_tokens=8192,
#     )


# def normalize_transcription_text(text: str, language: str = "english") -> str:
#     """Post-process transcription text to remove unwanted spaces in words for Latin scripts."""
#     import re
#     if language.lower() == "english":
#         # Collapse multiple spaces, then remove spaces within words (but keep between words)
#         # This regex removes spaces between letters, but not between words
#         # e.g., "Tha t's fa nta sti c!" -> "That's fantastic!"
#         # Step 1: Collapse multiple spaces
#         text = re.sub(r"\s+", " ", text)
#         # Step 2: Remove spaces between letters (not between words)
#         # This will join letters separated by a single space, but not words
#         # We'll use a conservative approach: only remove spaces between letters (a-zA-Z)
#         text = re.sub(r"(?<=\w) (?=\w)", "", text)
#         return text.strip()
#     # For other scripts (e.g., Hindi), just collapse multiple spaces
#     return re.sub(r"\s+", " ", text).strip()


# class TurnBuffer:
#     """Buffer to accumulate transcription fragments during a turn"""
    
#     def __init__(self):
#         self.reset()
    
#     def reset(self):
#         """Reset buffer for new turn"""
#         self.user_fragments = []
#         self.assistant_fragments = []
#         self.user_complete_text = ""
#         self.assistant_complete_text = ""
#         self.turn_evaluation = None
#         self.turn_start_time = datetime.utcnow()
#         self.has_user_input = False
#         self.has_assistant_response = False
    
#     def add_user_fragment(self, text: str):
#         """Add user transcription fragment"""
#         if text and text.strip():
#             self.user_fragments.append(text.strip())
#             self.has_user_input = True
#             # Update complete text by joining fragments
#             self.user_complete_text = " ".join(self.user_fragments)
    
#     def add_assistant_fragment(self, text: str):
#         """Add assistant transcription fragment"""
#         if text and text.strip():
#             self.assistant_fragments.append(text.strip())
#             self.has_assistant_response = True
#             # Update complete text by joining fragments
#             self.assistant_complete_text = " ".join(self.assistant_fragments)
    
#     def set_evaluation(self, evaluation: Dict[str, Any]):
#         """Set turn evaluation data"""
#         self.turn_evaluation = evaluation
    
#     def is_ready_for_logging(self) -> bool:
#         """Check if turn has enough data for logging"""
#         return (self.has_user_input and 
#                 len(self.user_complete_text.strip()) > 0)
    
#     def get_user_text(self) -> str:
#         """Get complete user text"""
#         return self.user_complete_text.strip()
    
#     def get_assistant_text(self) -> str:
#         """Get complete assistant text"""
#         return self.assistant_complete_text.strip()
    
#     def get_turn_summary(self) -> Dict[str, Any]:
#         """Get summary of current turn buffer state"""
#         return {
#             "user_fragments": len(self.user_fragments),
#             "assistant_fragments": len(self.assistant_fragments),
#             "user_text_length": len(self.user_complete_text),
#             "assistant_text_length": len(self.assistant_complete_text),
#             "has_evaluation": self.turn_evaluation is not None,
#             "ready_for_logging": self.is_ready_for_logging()
#         }


# class VoiceSession:
#     """Manages a voice learning session with GenAI integration and turn-complete logging"""
    
#     def __init__(
#         self, 
#         websocket, 
#         scenario_data=None, 
#         mother_language="english", 
#         target_language="english", 
#         user_level="beginner", 
#         teaching_mode="conversation",
#         learning_session_id: Optional[UUID] = None
#     ):
#         self.websocket = websocket
#         self.scenario_data = scenario_data or self._get_default_scenario()
#         self.mother_language = mother_language
#         self.target_language = target_language
#         self.user_level = user_level
#         self.teaching_mode = teaching_mode
#         self.learning_session_id = learning_session_id
        
#         # GenAI session management
#         self.session = None
#         self.session_manager = None
#         self.is_active = False
#         self._listen_task = None
        
#         # Configuration
#         self.config = create_config(
#             self.scenario_data, 
#             mother_language, 
#             target_language, 
#             user_level, 
#             teaching_mode
#         )
        
#         # Audio buffering
#         self.audio_buffer = deque(maxlen=10)
        
#         # Session statistics
#         self.restart_count = 0
#         self.max_restarts = 3
#         self.session_active_time = 0
#         self.turn_count = 0
        
#         # Service integration
#         self.conversation_service = conversation_service
#         self.scoring_service = scoring_service
        
#         # Turn buffering for complete logging
#         self.turn_buffer = TurnBuffer()
#         self.last_sent_user_text = ""
#         self.last_sent_assistant_text = ""
        
#     def _get_default_scenario(self) -> Dict[str, Any]:
#         """Get default scenario data"""
#         return {
#             "name": "General Conversation",
#             "context": "General conversation practice with friendly guidance",
#             "learning_objectives": ["Fluency", "Vocabulary", "Grammar", "Pronunciation"]
#         }
        
#     async def initialize(self):
#         """Initialize the GenAI session with persistent connection"""
#         try:
#             logger.info("Initializing voice session", 
#                        scenario=self.scenario_data['name'],
#                        mother_language=self.mother_language,
#                        target_language=self.target_language,
#                        teaching_mode=self.teaching_mode,
#                        learning_session_id=self.learning_session_id)
            
#             # Create session manager
#             self.session_manager = client.aio.live.connect(model=MODEL, config=self.config)
#             self.session = await self.session_manager.__aenter__()
#             self.is_active = True
#             self.restart_count = 0
#             self.session_active_time = asyncio.get_event_loop().time()
            
#             logger.info("Voice session initialized successfully", 
#                        teaching_mode=self.teaching_mode,
#                        learning_session_id=self.learning_session_id)
            
#             # Send any buffered audio
#             if self.audio_buffer:
#                 logger.info("Sending buffered audio", chunks=len(self.audio_buffer))
#                 for audio_data in list(self.audio_buffer):
#                     try:
#                         await self.session.send_realtime_input(
#                             media={
#                                 "data": audio_data,
#                                 "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}",
#                             }
#                         )
#                         await asyncio.sleep(0.01)  # Small delay between chunks
#                     except Exception as e:
#                         logger.error("Error sending buffered audio", error=str(e))
#                         break
#                 self.audio_buffer.clear()
                        
#             return True
#         except Exception as e:
#             logger.error("Failed to initialize voice session", error=str(e))
#             traceback.print_exc()
#             self.is_active = False
#             return False
    
#     async def process_audio(self, audio_data):
#         """Send audio data to GenAI with session management"""
#         # Always buffer recent audio for potential restart
#         self.audio_buffer.append(audio_data)
        
#         if not self.is_active or not self.session:
#             logger.warning("Session not active during audio processing - buffering audio")
#             return
            
#         try:
#             await self.session.send_realtime_input(
#                 media={
#                     "data": audio_data,
#                     "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}",
#                 }
#             )
            
#             # If listener task is done, restart it
#             if self._listen_task and self._listen_task.done():
#                 logger.info("Response listener stopped - restarting...")
#                 self._listen_task = asyncio.create_task(self.listen_for_responses())
                
#         except Exception as e:
#             logger.error("Error processing audio", error=str(e))
#             await asyncio.sleep(0.1)
    
#     async def listen_for_responses(self):
#         """Listen for responses from GenAI and handle turn-complete conversation logging"""
#         if not self.session or not self.is_active:
#             return
            
#         logger.info("Starting response listener for voice session with turn-complete logging", 
#                    teaching_mode=self.teaching_mode,
#                    learning_session_id=self.learning_session_id)
        
#         while self.is_active:
#             try:
#                 async for response in self.session.receive():
#                     if not self.is_active:
#                         logger.info("Session marked inactive - stopping listener")
#                         break
                    
#                     # Handle server content (audio, transcriptions, etc.)
#                     server_content = response.server_content
                    
#                     if server_content and server_content.model_turn:
#                         # Process audio output
#                         for part in server_content.model_turn.parts:
#                             if part.inline_data and self.is_active:
#                                 try:
#                                     audio_b64 = base64.b64encode(part.inline_data.data).decode()
#                                     await self.websocket.send(json.dumps({
#                                         "type": "audio",
#                                         "data": audio_b64,
#                                         "sample_rate": RECEIVE_SAMPLE_RATE
#                                     }))
#                                 except websockets.exceptions.ConnectionClosed:
#                                     logger.info("WebSocket closed during audio send")
#                                     self.is_active = False
#                                     return
#                                 except Exception as e:
#                                     logger.error("Error sending audio", error=str(e))
#                                     continue
                    
#                     # Handle output transcriptions (assistant responses) - BUFFER ONLY
#                     if (self.is_active and 
#                         hasattr(server_content, 'output_transcription') and 
#                         server_content.output_transcription and 
#                         server_content.output_transcription.text.strip()):
                        
#                         try:
#                             assistant_text = server_content.output_transcription.text.strip()
                            
#                             # Add to turn buffer instead of logging immediately
#                             self.turn_buffer.add_assistant_fragment(assistant_text)
                            
#                             # Send transcription to client only if it's new content
#                             current_complete_text = self.turn_buffer.get_assistant_text()
#                             if current_complete_text != self.last_sent_assistant_text:
#                                 await self.websocket.send(json.dumps({
#                                     "type": "transcription",
#                                     "text": current_complete_text,
#                                     "source": "assistant"
#                                 }))
#                                 self.last_sent_assistant_text = current_complete_text
                            
#                             logger.debug("Buffered assistant transcription fragment", 
#                                        fragment=assistant_text,
#                                        total_length=len(current_complete_text))
                            
#                         except websockets.exceptions.ConnectionClosed:
#                             self.is_active = False
#                             return
#                         except Exception as e:
#                             logger.error("Error handling assistant transcription", error=str(e))
                    
#                     # Handle input transcriptions (user speech) - BUFFER ONLY
#                     if (self.is_active and 
#                         hasattr(server_content, 'input_transcription') and 
#                         server_content.input_transcription and 
#                         server_content.input_transcription.text.strip()):
                        
#                         try:
#                             user_text = server_content.input_transcription.text.strip()
                            
#                             # Add to turn buffer instead of logging immediately
#                             self.turn_buffer.add_user_fragment(user_text)
                            
#                             # Send transcription to client only if it's new content
#                             current_complete_text = self.turn_buffer.get_user_text()
#                             if current_complete_text != self.last_sent_user_text:
#                                 await self.websocket.send(json.dumps({
#                                     "type": "transcription", 
#                                     "text": current_complete_text,
#                                     "source": "user"
#                                 }))
#                                 self.last_sent_user_text = current_complete_text
                            
#                             logger.debug("Buffered user transcription fragment", 
#                                        fragment=user_text,
#                                        total_length=len(current_complete_text))
                            
#                         except websockets.exceptions.ConnectionClosed:
#                             self.is_active = False
#                             return
#                         except Exception as e:
#                             logger.error("Error handling user transcription", error=str(e))
                        
#                     # Handle turn completion - LOG COMPLETE TURN HERE
#                     if self.is_active and server_content and server_content.turn_complete:
#                         try:
#                             await self.websocket.send(json.dumps({
#                                 "type": "turn_complete"
#                             }))
                            
#                             self.turn_count += 1
                            
#                             # Log the complete turn to database now
#                             await self._log_complete_turn()
                            
#                             logger.info("Turn completed and logged", 
#                                        turn_count=self.turn_count,
#                                        learning_session_id=self.learning_session_id,
#                                        buffer_summary=self.turn_buffer.get_turn_summary())
                            
#                             # Reset buffers and tracking for next turn
#                             self.turn_buffer.reset()
#                             self.last_sent_user_text = ""
#                             self.last_sent_assistant_text = ""
                            
#                             # Clear audio buffer after successful turn but keep session active
#                             self.audio_buffer.clear()
                            
#                             # Update session active time
#                             self.session_active_time = asyncio.get_event_loop().time()
                            
#                         except websockets.exceptions.ConnectionClosed:
#                             self.is_active = False
#                             return
#                         except Exception as e:
#                             logger.error("Error processing turn complete", error=str(e))
                
#                 # Continue listening
#                 if self.is_active:
#                     await asyncio.sleep(0.1)
#                 else:
#                     break
                    
#             except asyncio.CancelledError:
#                 logger.info("Response listener cancelled")
#                 raise
#             except websockets.exceptions.ConnectionClosedOK:
#                 logger.info("GenAI session closed normally")
#                 break
#             except websockets.exceptions.ConnectionClosed:
#                 logger.info("GenAI session connection lost")
#                 break
#             except Exception as e:
#                 logger.error("Error in response listener", error=str(e))
#                 if self.is_active:
#                     logger.info("Error occurred but session still active - continuing...")
#                     await asyncio.sleep(0.5)
#                 else:
#                     break
                
#         logger.info("Response listener stopped completely")
    
#     async def _log_complete_turn(self):
#         """Log the complete turn to conversation service"""
#         if not self.learning_session_id or not self.turn_buffer.is_ready_for_logging():
#             logger.debug("Skipping turn logging - no session ID or insufficient data",
#                         has_session_id=bool(self.learning_session_id),
#                         buffer_ready=self.turn_buffer.is_ready_for_logging())
#             return
        
#         try:
#             # Get complete texts from buffer
#             user_text = self.turn_buffer.get_user_text()
#             assistant_text = self.turn_buffer.get_assistant_text()

#             # Post-process texts before logging
#             user_text = normalize_transcription_text(user_text, self.target_language)
#             assistant_text = normalize_transcription_text(assistant_text, self.target_language)
            
#             if not user_text:
#                 logger.debug("Skipping turn logging - no user text")
#                 return
            
#             # Log user turn with scoring
#             logger.info("Logging complete user turn", 
#                        user_text_length=len(user_text),
#                        session_id=self.learning_session_id)
            
#             user_turn_result = await self.conversation_service.add_turn(
#                 session_id=self.learning_session_id,
#                 role=ConversationRole.USER,
#                 text=user_text
#             )
            
#             if user_turn_result:
#                 logger.info("User turn logged successfully", 
#                            conversation_id=user_turn_result.get("conversation_id"),
#                            turn_index=user_turn_result.get("turn_index"),
#                            scored=bool(user_turn_result.get("evaluation")))
                
#                 # Send scoring feedback if available
#                 if user_turn_result.get("evaluation"):
#                     await self.websocket.send(json.dumps({
#                         "type": "feedback",
#                         "data": {
#                             "total_score": user_turn_result["evaluation"]["total_score"],
#                             "metrics": user_turn_result["evaluation"]["metrics"],
#                             "teaching_mode": self.teaching_mode,
#                             "turn_index": user_turn_result["turn_index"]
#                         }
#                     }))
#             else:
#                 logger.warning("Failed to log user turn",
#                              session_id=self.learning_session_id)
            
#             # Log assistant turn if we have assistant text
#             if assistant_text:
#                 logger.info("Logging complete assistant turn", 
#                            assistant_text_length=len(assistant_text),
#                            session_id=self.learning_session_id)
                
#                 assistant_turn_result = await self.conversation_service.add_turn(
#                     session_id=self.learning_session_id,
#                     role=ConversationRole.ASSISTANT,
#                     text=assistant_text
#                 )
                
#                 if assistant_turn_result:
#                     logger.info("Assistant turn logged successfully", 
#                                conversation_id=assistant_turn_result.get("conversation_id"),
#                                turn_index=assistant_turn_result.get("turn_index"))
#                 else:
#                     logger.warning("Failed to log assistant turn",
#                                  session_id=self.learning_session_id)
            
#         except Exception as e:
#             logger.error("Error logging complete turn", 
#                         session_id=self.learning_session_id,
#                         error=str(e))
    
#     async def close(self):
#         """Close the session gracefully"""
#         logger.info("Closing voice session", 
#                    learning_session_id=self.learning_session_id,
#                    turn_count=self.turn_count)
#         self.is_active = False
        
#         # Cancel listening task first
#         if self._listen_task and not self._listen_task.done():
#             self._listen_task.cancel()
#             try:
#                 await asyncio.wait_for(self._listen_task, timeout=2.0)
#             except (asyncio.CancelledError, asyncio.TimeoutError):
#                 pass
        
#         # Close session manager
#         try:
#             if self.session_manager and self.session:
#                 await self.session_manager.__aexit__(None, None, None)
#                 logger.info("GenAI session closed properly")
#         except Exception as e:
#             logger.error("Error closing GenAI session", error=str(e))
#         finally:
#             self.session = None
#             self.session_manager = None
    
#     async def restart_session(self):
#         """Restart the session if needed (for error recovery)"""
#         if self.restart_count >= self.max_restarts:
#             logger.error("Maximum restart attempts reached", 
#                         restart_count=self.restart_count,
#                         max_restarts=self.max_restarts)
#             return False
            
#         logger.info("Restarting voice session", 
#                    attempt=self.restart_count + 1,
#                    max_attempts=self.max_restarts)
        
#         # Close current session
#         await self.close()
        
#         # Wait a moment before restarting
#         await asyncio.sleep(1.0)
        
#         # Increment restart count
#         self.restart_count += 1
        
#         # Try to initialize again
#         return await self.initialize()
    
#     def get_session_info(self):
#         """Get current session information"""
#         return {
#             "session_active": self.is_active,
#             "teaching_mode": self.teaching_mode,
#             "scenario": self.scenario_data,
#             "mother_language": self.mother_language,
#             "target_language": self.target_language,
#             "user_level": self.user_level,
#             "learning_session_id": str(self.learning_session_id) if self.learning_session_id else None,
#             "restart_count": self.restart_count,
#             "session_active_time": self.session_active_time,
#             "audio_buffer_size": len(self.audio_buffer),
#             "turn_count": self.turn_count,
#             "turn_buffer_summary": self.turn_buffer.get_turn_summary(),
#             "service_integration": {
#                 "conversation_logging": bool(self.learning_session_id),
#                 "automatic_scoring": bool(self.learning_session_id),
#                 "session_persistence": bool(self.learning_session_id),
#                 "turn_complete_logging": True
#             }
#         }
    
#     async def get_session_statistics(self):
#         """Get session statistics from services"""
#         if not self.learning_session_id:
#             return None
        
#         try:
#             stats = await self.scoring_service.calculate_session_statistics(
#                 self.learning_session_id
#             )
#             return stats
#         except Exception as e:
#             logger.error("Error getting session statistics", 
#                         learning_session_id=self.learning_session_id,
#                         error=str(e))
#             return None

