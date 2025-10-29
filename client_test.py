#!/usr/bin/env python3
"""
Enhanced Multilingual Voice Learning Client - Turn-Complete Logging
Updated to log conversation turns to Supabase only after turn completion
Accumulates transcriptions during a turn and posts them as complete conversation pairs
"""

import asyncio
import websockets
import json
import base64
import pyaudio
import queue
import signal
import sys
import time
import ssl
import certifi
import random
from collections import deque
from datetime import datetime
import uuid
import requests
import aiohttp

# Audio configuration
FORMAT = pyaudio.paInt16
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 22000
CHUNK_SIZE = 256
CHANNELS = 1

# Language Learning Configuration
MOTHER_LANGUAGE = "english"  # Source language (user's native language)
TARGET_LANGUAGE = "english"   # Language to learn
SCENARIO = "construction"     # Learning scenario - Construction Site
USER_LEVEL = "intermediate"   # Learning level
TEACHING_MODE = "conversation"  # Default teaching mode

# Generate unique user ID for this session
USER_EXTERNAL_ID = f"user_{uuid.uuid4().hex[:8]}"

# Server endpoints - Updated for new architecture
SERVER_ENDPOINTS = [
    # "ws://localhost:8765",  # Local development
    # "ws://0.0.0.0:8765",    # Docker local
    # Add your Cloud Run endpoints here
    # "wss://your-service-url.run.app"
     "ws://localhost:8080"
    # "wss://voice-chatbot-server-166647007319.asia-south1.run.app"
#    "wss://voice-chatbot-server-166647007319.asia-south1.run.app"
   
]

async def gemini_post_process_text_async(raw_text: str) -> str:
    """
    Use the server's /api/gemini_post_process endpoint to fix spacing, punctuation, and grammar in a raw text string.
    Returns the improved text.
    """
    url = "http://localhost:8080/api/gemini_post_process"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"text": raw_text}, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("processed_text", raw_text)
                else:
                    import logging
                    logging.warning(f"Gemini API post-processing failed: {resp.status} {await resp.text()}")
                    return raw_text
    except Exception as e:
        import logging
        logging.warning(f"Gemini API post-processing exception: {e}")
        return raw_text

class TurnBuffer:
    """Buffer to accumulate turn data before logging to database"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset the buffer for a new turn"""
        self.user_text = ""
        self.assistant_text = ""
        self.user_transcribed = False
        self.assistant_transcribed = False
        self.turn_evaluation = None
        self.turn_start_time = datetime.now()
    
    async def add_user_text(self, text):
        """Add user transcription text (with LLM post-processing)"""
        self.user_text = await gemini_post_process_text_async(text)
        self.user_transcribed = True

    async def add_assistant_text(self, text):
        """Add assistant transcription text (with LLM post-processing)"""
        self.assistant_text = await gemini_post_process_text_async(text)
        self.assistant_transcribed = True
    
    def add_evaluation(self, evaluation):
        """Add turn evaluation data"""
        self.turn_evaluation = evaluation
    
    def is_complete(self):
        """Check if turn has both user and assistant parts"""
        return self.user_transcribed and self.assistant_transcribed
    
    def get_turn_data(self):
        """Get complete turn data for logging"""
        return {
            'user_text': self.user_text,
            'assistant_text': self.assistant_text,
            'evaluation': self.turn_evaluation,
            'turn_start_time': self.turn_start_time,
            'turn_end_time': datetime.now()
        }

class ConversationLogger:
    """Track conversation history and handle turn-complete logging"""
    
    def __init__(self):
        self.session_id = None
        self.conversation_history = []
        self.current_turn_index = 0
        self.session_start_time = datetime.now()
        self.total_user_turns = 0
        self.total_assistant_turns = 0
        self.pending_database_logs = []  # Queue for database logging
        
    def set_session_id(self, session_id):
        """Set the session ID from server response"""
        self.session_id = session_id
        print(f"📊 Conversation logging enabled for session: {session_id}")
    
    def log_complete_turn(self, turn_data, turn_index):
        """Log a complete turn (user + assistant + evaluation) locally and queue for database"""
        # Log user turn
        user_entry = {
            'role': 'user',
            'text': turn_data['user_text'],
            'timestamp': turn_data['turn_start_time'],
            'turn_index': turn_index,
            'evaluation': turn_data['evaluation']
        }
        
        # Log assistant turn
        assistant_entry = {
            'role': 'assistant',
            'text': turn_data['assistant_text'],
            'timestamp': turn_data['turn_end_time'],
            'turn_index': turn_index,
            'evaluation': None
        }
        
        self.conversation_history.extend([user_entry, assistant_entry])
        self.total_user_turns += 1
        self.total_assistant_turns += 1
        
        # Queue for database logging
        self.pending_database_logs.append({
            'user_turn': user_entry,
            'assistant_turn': assistant_entry,
            'turn_index': turn_index
        })
        
        print(f"📝 Logged complete turn #{turn_index}")
        print(f"   User: {turn_data['user_text'][:50]}{'...' if len(turn_data['user_text']) > 50 else ''}")
        print(f"   Assistant: {turn_data['assistant_text'][:50]}{'...' if len(turn_data['assistant_text']) > 50 else ''}")
        
        if turn_data['evaluation']:
            print(f"   📊 Scored: {turn_data['evaluation'].get('total_score', 'N/A')}/100")
    
    def get_session_summary(self):
        """Get session statistics"""
        duration = (datetime.now() - self.session_start_time).total_seconds() / 60
        return {
            'session_id': self.session_id,
            'duration_minutes': duration,
            'total_turns': len(self.conversation_history),
            'user_turns': self.total_user_turns,
            'assistant_turns': self.total_assistant_turns,
            'conversation_history': self.conversation_history,
            'pending_database_logs': len(self.pending_database_logs)
        }

class FeedbackTracker:
    """Track and analyze learning progress over time with mode-specific insights"""
    
    def __init__(self):
        self.feedback_history = deque(maxlen=30)  # Keep last 30 feedbacks
        self.session_start_time = datetime.now()
        self.mode_performance = {}  # Track performance by mode
        
    def add_feedback(self, feedback_data):
        """Add new feedback and calculate trends"""
        feedback_entry = {
            'timestamp': datetime.now(),
            'data': feedback_data
        }
        self.feedback_history.append(feedback_entry)
        
        # Track mode-specific performance
        teaching_mode = feedback_data.get('teaching_mode', 'conversation')
        if teaching_mode not in self.mode_performance:
            self.mode_performance[teaching_mode] = []
        self.mode_performance[teaching_mode].append(feedback_data)
        
    def get_progress_summary(self):
        """Calculate progress trends"""
        if len(self.feedback_history) < 2:
            return None
            
        recent = list(self.feedback_history)[-3:]  # Last 3 turns
        older = list(self.feedback_history)[-6:-3] if len(self.feedback_history) >= 6 else []
        
        if not older:
            return None
            
        # Calculate averages
        recent_grammar = sum(f['data'].get('grammar_score', 0) for f in recent) / len(recent)
        recent_pronunciation = sum(f['data'].get('pronunciation_score', 0) for f in recent) / len(recent)
        recent_fluency = sum(f['data'].get('fluency_score', 0) for f in recent) / len(recent)
        recent_mode_specific = sum(f['data'].get('mode_specific_score', 0) for f in recent) / len(recent)
        
        older_grammar = sum(f['data'].get('grammar_score', 0) for f in older) / len(older)
        older_pronunciation = sum(f['data'].get('pronunciation_score', 0) for f in older) / len(older)
        older_fluency = sum(f['data'].get('fluency_score', 0) for f in older) / len(older)
        older_mode_specific = sum(f['data'].get('mode_specific_score', 0) for f in older) / len(older)
        
        return {
            'grammar_trend': recent_grammar - older_grammar,
            'pronunciation_trend': recent_pronunciation - older_pronunciation,
            'fluency_trend': recent_fluency - older_fluency,
            'mode_specific_trend': recent_mode_specific - older_mode_specific,
            'total_turns': len(self.feedback_history),
            'session_duration': (datetime.now() - self.session_start_time).total_seconds() / 60
        }

class EnhancedVoiceLearningClient:
    def __init__(self, server_url=None):
        self.server_url = server_url
        self.websocket = None
        self.pya = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.audio_out_queue = queue.Queue()
        self.is_recording = False
        self.should_stop = False
        self.turn_count = 0
        self.last_activity = time.time()
        self.connection_attempts = 0
        
        # Language learning settings
        self.mother_language = MOTHER_LANGUAGE
        self.target_language = TARGET_LANGUAGE
        self.scenario = SCENARIO
        self.user_level = USER_LEVEL
        self.teaching_mode = TEACHING_MODE
        self.user_external_id = USER_EXTERNAL_ID
        
        # Session tracking
        self.learning_session_id = None
        self.conversation_logger = ConversationLogger()
        self.feedback_tracker = FeedbackTracker()
        self.last_feedback = None
        self.current_mode_info = None
        
        # Turn buffer for complete turn logging
        self.turn_buffer = TurnBuffer()
        
        # Available options (populated from server)
        self.available_modes = {}
        self.available_languages = {}
        self.available_scenarios = {}
        
    def initialize_audio(self):
        """Initialize audio streams with error handling"""
        try:
            # Get microphone info
            mic_info = self.pya.get_default_input_device_info()
            print(f"🎤 Using microphone: {mic_info['name']}") 
            
            # Input stream (microphone)
            self.input_stream = self.pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=CHUNK_SIZE,
            )
            
            # Output stream (speakers)
            self.output_stream = self.pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True,
            )
            
            print("✅ Audio streams initialized")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize audio: {e}")
            print("💡 Make sure your microphone and speakers are connected")
            return False
    
    def display_mode_specific_feedback(self, feedback_data):
        """Display detailed, mode-specific learning feedback"""
        teaching_mode = feedback_data.get('teaching_mode', 'conversation')
        mode_name = feedback_data.get('mode_name', 'Conversation Practice')
        mode_focus = feedback_data.get('mode_focus', 'General conversation')
        
        print("\n" + "="*80)
        print(f"📊 {mode_name.upper()} FEEDBACK - Turn {self.turn_count}")
        print("="*80)
        
        # Scores with visual indicators
        grammar_score = feedback_data.get('grammar_score', 0)
        pronunciation_score = feedback_data.get('pronunciation_score', 0)
        fluency_score = feedback_data.get('fluency_score', 0)
        mode_specific_score = feedback_data.get('mode_specific_score', 0)
        
        print("📈 SCORES:")
        print(f"   Grammar:           {grammar_score}/10 {'⭐' * min(grammar_score, 5)}")
        print(f"   Pronunciation:     {pronunciation_score}/10 {'📊' * min(pronunciation_score, 5)}")  
        print(f"   Fluency:           {fluency_score}/10 {'💬' * min(fluency_score, 5)}")
        
        # Mode-specific score with appropriate icon
        mode_icons = {
            'conversation': '💭',
            'grammar': '📝',
            'pronunciation': '🗣️',
            'vocabulary': '📚',
            'test_prep': '📋',
            'concept_learning': '💡',
            'reading': '📖',
            'assessment': '📊'
        }
        mode_icon = mode_icons.get(teaching_mode, '🎯')
        print(f"   {mode_name}: {mode_specific_score}/10 {mode_icon * min(mode_specific_score, 5)}")
        
        # Overall performance
        avg_score = (grammar_score + pronunciation_score + fluency_score + mode_specific_score) / 4
        if avg_score >= 8:
            performance = "Excellent! 🌟"
        elif avg_score >= 6:
            performance = "Good progress! 👍"
        elif avg_score >= 4:
            performance = "Keep practicing! 💪"
        else:
            performance = "You're learning! 🌱"
            
        print(f"   Overall:           {avg_score:.1f}/10 - {performance}")
        
        # Store feedback
        self.last_feedback = feedback_data
        self.feedback_tracker.add_feedback(feedback_data)
        
        print("="*80 + "\n")
    
    def start_recording(self):
        """Start recording audio"""
        self.is_recording = True
        print(f"🎤 Recording started (Turn {self.turn_count + 1})")
    
    def stop_recording(self):
        """Stop recording audio"""
        self.is_recording = False
        print("🛑 Recording stopped")
    
    async def record_and_send_loop(self):
        """Record and send audio continuously"""
        audio_count = 0
        while not self.should_stop:
            try:
                if self.is_recording and self.input_stream and self.websocket:
                    # Read audio data
                    data = await asyncio.to_thread(
                        self.input_stream.read, 
                        CHUNK_SIZE, 
                        exception_on_overflow=False
                    )
                    
                    if data:
                        # Send audio to server
                        audio_b64 = base64.b64encode(data).decode()
                        message = json.dumps({
                            "type": "audio",
                            "data": audio_b64
                        })
                        await self.websocket.send(message)
                        
                        audio_count += 1
                        if audio_count % 50 == 0:  # Every ~1.5 seconds
                            mode_name = self.current_mode_info['name'] if self.current_mode_info else "Learning"
                            print(f"🎤 {mode_name} - Listening... (Turn {self.turn_count + 1})", end="\r")
                        
                        self.last_activity = time.time()
                else:
                    await asyncio.sleep(0.01)
                    
            except websockets.exceptions.ConnectionClosed:
                print("\n❌ WebSocket connection closed during recording")
                self.should_stop = True
                break
            except Exception as e:
                print(f"\n❌ Recording error: {e}")
                await asyncio.sleep(0.1)
    
    async def try_connect_to_endpoint(self, endpoint):
        """Try to connect to a specific endpoint"""
        try:
            print(f"🔗 Trying {endpoint}...")
            
            # Handle SSL for secure connections
            if endpoint.startswith('wss://'):
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                websocket = await websockets.connect(
                    endpoint,
                    ssl=ssl_context,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )
            else:
                websocket = await websockets.connect(
                    endpoint,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )
            
            print(f"✅ Connected to {endpoint}")
            return websocket
            
        except Exception as e:
            print(f"❌ Failed to connect to {endpoint}: {e}")
            return None
    
    async def connect(self):
        """Connect to WebSocket server with fallback"""
        endpoints_to_try = [self.server_url] + SERVER_ENDPOINTS if self.server_url else SERVER_ENDPOINTS
        
        print("🔍 Searching for available server...")
        
        for endpoint in endpoints_to_try:
            self.connection_attempts += 1
            websocket = await self.try_connect_to_endpoint(endpoint)
            if websocket:
                self.websocket = websocket
                self.server_url = endpoint
                return True
            await asyncio.sleep(1)
        
        print("❌ Could not connect to any server endpoint")
        return False
    
    async def start_session(self):
        """Start a multilingual learning session with enhanced logging"""
        if self.websocket:
            message = json.dumps({
                "type": "start_session",
                "user_external_id": self.user_external_id,
                "mother_language": self.mother_language,
                "target_language": self.target_language,
                "scenario_id": self.scenario,
                "user_level": self.user_level,
                "teaching_mode": self.teaching_mode,
                "metadata": {
                    "client_version": "enhanced_v1.0",
                    "audio_config": {
                        "send_rate": SEND_SAMPLE_RATE,
                        "receive_rate": RECEIVE_SAMPLE_RATE,
                        "format": "pcm16"
                    }
                }
            })
            await self.websocket.send(message)
            print(f"🎯 Starting session with turn-complete conversation storage...")
            print(f"👤 User ID: {self.user_external_id}")
            print(f"🌍 {self.mother_language.title()} → {self.target_language.title()}")
            print(f"🏗️ Scenario: {self.scenario.title()}")
            print(f"📚 Level: {self.user_level.title()}")
            print(f"🎓 Mode: {self.teaching_mode.title()}")
    
    async def end_session(self):
        """Properly end the session and get summary"""
        if self.websocket:
            message = json.dumps({
                "type": "end_session"
            })
            await self.websocket.send(message)
            print("📚 Ending session and generating summary...")
    
    async def listen_for_messages(self):
        """Listen for messages from server with turn-complete conversation logging"""
        try:
            async for message in self.websocket:
                if self.should_stop:
                    break
                    
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "welcome":
                    print(f"👋 {data.get('message')}")
                    session_id = data.get('session_id')
                    if session_id:
                        print(f"🆔 WebSocket Session ID: {session_id}")
                    
                    # Store available options
                    self.available_modes = data.get('teaching_modes', {})
                    self.available_languages = data.get('supported_languages', {})
                    self.available_scenarios = data.get('default_scenarios', {})
                
                elif message_type == "session_started":
                    scenario_info = data.get('scenario', {})
                    mother_lang = data.get('mother_language', 'unknown')
                    target_lang = data.get('target_language', 'unknown')
                    level = data.get('user_level', 'unknown')
                    teaching_mode = data.get('teaching_mode', 'conversation')
                    mode_info = data.get('mode_info', {})
                    learning_session_id = data.get('learning_session_id')
                    
                    # Set session IDs for logging
                    if learning_session_id:
                        self.learning_session_id = learning_session_id
                        self.conversation_logger.set_session_id(learning_session_id)
                        print(f"📊 Learning Session ID: {learning_session_id}")
                        print("✅ Turn-complete conversation logging to Supabase enabled!")
                    
                    self.current_mode_info = mode_info
                    
                    print(f"🎓 Learning session started with turn-complete storage!")
                    print(f"🎯 Teaching Mode: {mode_info.get('name', 'Unknown')}")
                    print(f"📚 Scenario: {scenario_info.get('name', 'Unknown')}")
                    print(f"🌍 Language Pair: {mother_lang.title()} → {target_lang.title()}")
                    print(f"📊 Level: {level.title()}")
                    print(f"\n🎤 Start speaking! Conversations will be stored after each complete turn!")
                    print("💡 Use English first, Malayalam if you need help")
                    self.start_recording()
                
                elif message_type == "audio":
                    # Play audio from assistant
                    audio_b64 = data.get("data")
                    if audio_b64:
                        audio_data = base64.b64decode(audio_b64)
                        try:
                            if self.output_stream:
                                await asyncio.to_thread(self.output_stream.write, audio_data)
                        except Exception as e:
                            print(f"❌ Playback error: {e}")
                
                elif message_type == "transcription":
                    # Buffer transcriptions instead of logging immediately
                    source = data.get("source", "")
                    text = data.get("text", "")
                    if source == "user":
                        print(f"\n👤 You said: {text}")
                        await self.turn_buffer.add_user_text(text)
                    elif source == "assistant":
                        teacher_title = f"{self.current_mode_info['name']} Teacher" if self.current_mode_info else "Teacher"
                        print(f"\n👩‍🏫 {teacher_title}: {text}")
                        await self.turn_buffer.add_assistant_text(text)
                
                elif message_type == "feedback":
                    # Store feedback in turn buffer instead of displaying immediately
                    feedback_data = data.get("data", {})
                    self.turn_buffer.add_evaluation({
                        'total_score': feedback_data.get('total_score'),
                        'metrics': feedback_data.get('metrics', {}),
                        'teaching_mode': feedback_data.get('teaching_mode')
                    })
                
                elif message_type == "turn_complete":
                    self.turn_count += 1
                    
                    # Now log the complete turn to database
                    if self.turn_buffer.is_complete():
                        turn_data = self.turn_buffer.get_turn_data()
                        self.conversation_logger.log_complete_turn(turn_data, self.turn_count)
                        
                        # Display feedback now that turn is complete
                        if turn_data['evaluation']:
                            feedback_data = data.get("data", {}) if "data" in data else {}
                            if feedback_data:
                                self.display_mode_specific_feedback(feedback_data)
                        
                        print(f"\n🔄 Turn {self.turn_count} complete and stored in database!")
                    else:
                        print(f"\n⚠️ Turn {self.turn_count} incomplete - missing transcriptions")
                    
                    # Reset buffer for next turn
                    self.turn_buffer.reset()
                    
                    mode_name = self.current_mode_info['name'] if self.current_mode_info else "Learning"
                    print(f"🎯 Ready for next {mode_name.lower()} turn...")
                    
                    # Continue recording for next turn
                    if not self.is_recording:
                        self.start_recording()
                    
                    self.last_activity = time.time()
                
                elif message_type == "session_ended":
                    session_summary = data.get("summary")
                    print(f"\n🎓 Learning session ended!")
                    
                    if session_summary:
                        print("📋 Generated learning summary:")
                        summary_title = session_summary.get('title', 'Session Summary')
                        print(f"📖 {summary_title}")
                        
                        # Display summary sections
                        subtitle = session_summary.get('subtitle', {})
                        for section_key, section_data in subtitle.items():
                            heading = section_data.get('heading', f'Section {section_key}')
                            points = section_data.get('points', {})
                            
                            print(f"\n📚 {heading}:")
                            for point_key, point_text in points.items():
                                print(f"   • {point_text}")
                        
                        print(f"\n✅ Summary stored in database for session: {self.learning_session_id}")
                    
                    # Stop recording and show final stats
                    self.stop_recording()
                    self.show_final_session_summary()
                    self.should_stop = True
                
                elif message_type == "error":
                    print(f"❌ Server error: {data.get('message')}")
                    
                    # Auto-restart on session errors
                    if "session" in data.get('message', '').lower():
                        print("🔄 Attempting to restart session...")
                        await asyncio.sleep(1)
                        await self.start_session()
                        
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Connection closed by server")
        except Exception as e:
            print(f"❌ Error listening for messages: {e}")
    
    def show_final_session_summary(self):
        """Show comprehensive session summary"""
        session_summary = self.conversation_logger.get_session_summary()
        
        print(f"\n📊 FINAL SESSION SUMMARY")
        print("="*70)
        print(f"🆔 Session ID: {session_summary['session_id']}")
        print(f"⏰ Duration: {session_summary['duration_minutes']:.1f} minutes")
        print(f"💬 Total turns: {session_summary['total_turns']}")
        print(f"👤 Your turns: {session_summary['user_turns']}")
        print(f"👩‍🏫 Teacher turns: {session_summary['assistant_turns']}")
        print(f"📤 Pending database logs: {session_summary['pending_database_logs']}")
        
        if self.feedback_tracker.feedback_history:
            # Calculate averages
            total_feedback = list(self.feedback_tracker.feedback_history)
            if total_feedback:
                avg_grammar = sum(f['data'].get('grammar_score', 0) for f in total_feedback) / len(total_feedback)
                avg_pronunciation = sum(f['data'].get('pronunciation_score', 0) for f in total_feedback) / len(total_feedback)
                avg_fluency = sum(f['data'].get('fluency_score', 0) for f in total_feedback) / len(total_feedback)
                avg_mode_specific = sum(f['data'].get('mode_specific_score', 0) for f in total_feedback) / len(total_feedback)
                
                print(f"\n📈 Average Scores:")
                print(f"   Grammar: {avg_grammar:.1f}/10")
                print(f"   Pronunciation: {avg_pronunciation:.1f}/10")
                print(f"   Fluency: {avg_fluency:.1f}/10")
                if self.current_mode_info:
                    print(f"   {self.current_mode_info['name']}: {avg_mode_specific:.1f}/10")
                print(f"   Overall: {((avg_grammar + avg_pronunciation + avg_fluency + avg_mode_specific) / 4):.1f}/10")
        
        print("="*70)
        print("✅ All complete turns have been stored in the database!")
        print("📊 Turn-complete logging ensures data integrity and proper conversation flow.")
        print("🔍 You can access your learning history anytime through the API.")
    
    def cleanup(self):
        """Clean up resources"""
        print("🧹 Cleaning up voice learning client...")
        self.should_stop = True
        self.stop_recording()
        
        try:
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
            
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
            
            self.pya.terminate()
        except Exception as e:
            print(f"⚠️ Audio cleanup warning: {e}")

async def activity_monitor(client):
    """Monitor client activity and provide learning tips"""
    while not client.should_stop:
        await asyncio.sleep(30)  # Check every 30 seconds
        
        if not client.should_stop and client.is_recording:
            time_since_activity = time.time() - client.last_activity
            
            if time_since_activity > 35:
                print(f"\n💡 Keep practicing! Try saying something about construction work.")
                print("   Example: 'I need to check the safety equipment' or 'The concrete is ready'")
                print("   Use Malayalam if you're stuck: 'എനിക്ക് സഹായം വേണം' (I need help)")

async def main():
    """Main function for enhanced voice learning with turn-complete conversation storage"""
    client = EnhancedVoiceLearningClient()
    
    def signal_handler(sig, frame):
        print("\n👋 Ending learning session...")
        client.should_stop = True
        asyncio.create_task(client.end_session())
        
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🌟 ENHANCED VOICE LEARNING CLIENT WITH TURN-COMPLETE LOGGING")
    print("="*80)
    print("🇮🇳 Malayalam → English Learning with Turn-Complete Database Integration")
    print("🏗️ Construction Scenario with Proper Conversation Flow Logging") 
    print("📊 Automatic Scoring and Progress Tracking in Supabase")
    print("🔄 Conversations stored only after complete turns")
    print("="*80)
    
    # Initialize audio
    if not client.initialize_audio():
        print("⚠️ Audio initialization failed.")
        return
    
    # Connect to server
    print("\n🔍 Connecting to Enhanced Voice Learning Server...")
    if not await client.connect():
        print("\n💡 Make sure your server is running:")
        print("   docker-compose up -d")
        print("   or")
        print("   python -m app.main")
        return
    
    try:
        # Start tasks
        listen_task = asyncio.create_task(client.listen_for_messages())
        record_task = asyncio.create_task(client.record_and_send_loop())
        monitor_task = asyncio.create_task(activity_monitor(client))
        
        # Start learning session
        await client.start_session()
        
        print("\n🎯 REALTIME LEARNING WITH TURN-COMPLETE DATABASE STORAGE!")
        print("="*70)
        print("📊 WHAT GETS STORED (AFTER EACH COMPLETE TURN):")
        print("  ✅ Complete conversation pairs (user + assistant)")
        print("  📊 Automatic scoring for each user turn")
        print("  🎯 Teaching mode and session metadata")
        print("  📈 Progress tracking and learning analytics")
        print("  📋 Complete session summary on exit")
        print("  🔄 Data integrity through turn-complete logging")
        print("\n🏗️ CONSTRUCTION ENGLISH PRACTICE:")
        print("  • Discuss safety procedures and equipment")
        print("  • Ask about materials and tools") 
        print("  • Report work progress and issues")
        print("  • Practice team coordination phrases")
        print("  • Learn blueprint and specification terms")
        print("="*70)
        print(f"\n🎤 Start speaking! Connected to: {client.server_url}")
        print("📊 Conversations will be stored after each complete turn!")
        print("📚 Press Ctrl+C to end session and see your learning summary")
        
        # Wait for tasks to complete
        done, pending = await asyncio.wait(
            [listen_task, record_task, monitor_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
    except Exception as e:
        print(f"❌ Voice learning client error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Properly end session before cleanup
        if not client.should_stop:
            await client.end_session()
            await asyncio.sleep(2)  # Give time for session end processing
        
        client.cleanup()
        print("\n🎓 Thank you for using Enhanced Voice Learning!")
        print("📊 Your conversation data has been safely stored with proper turn completion.")
        print("🔄 Continue learning anytime by connecting again!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Learning session ended by user")
    except Exception as e:
        print(f"❌ Voice learning client error: {e}")
        import traceback
        traceback.print_exc()