"""
Configuration file for Enhanced Multilingual Voice Learning Server
Contains all constants, settings, and configuration data.
"""

import os
from typing import Optional
import google.genai

# Server Configuration
# MODEL = "gemini-2.0-flash-live-001"
MODEL = "gemini-2.5-flash-native-audio-preview-09-2025"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

# Audio Configuration
SEND_SAMPLE_RATE = int(os.getenv("SEND_SAMPLE_RATE", 16000))
RECEIVE_SAMPLE_RATE = int(os.getenv("RECEIVE_SAMPLE_RATE", 24000))

# Server Network Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8765))
HEALTH_PORT = int(os.getenv("HEALTH_PORT", 8766))
API_PORT = int(os.getenv("API_PORT", 8000))

# Database Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Session Configuration
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", 3600))  # 1 hour
MAX_TURNS_PER_SESSION = int(os.getenv("MAX_TURNS_PER_SESSION", 1000))

# Scoring Configuration
DEFAULT_SCORING_WEIGHTS = {
    "fluency": 0.25,
    "vocabulary": 0.25,
    "grammar": 0.25,
    "pronunciation": 0.25
}

DEFAULT_SCORING_SCALES = {
    "min": 0,
    "max": 5
}

# API Configuration
API_TITLE = "Enhanced Multilingual Voice Learning Server API"
API_VERSION = "2.0.0"  # Updated version for new features
API_DESCRIPTION = """
REST API for managing teaching modes, scenarios, languages, sessions, and conversations
in the Enhanced Multilingual Voice Learning Server.

New Features:
- Email reports for learning progress
- Writing evaluation and improvement
- Pattern analysis for writing skills
"""

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# NEW EMAIL CONFIGURATION
# SMTP Settings for sending emails
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
USE_TLS = os.getenv("USE_TLS", "true").lower() == "true"

# Email credentials
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_EMAIL_PASSWORD = os.getenv("SENDER_EMAIL_PASSWORD")

# Email template configuration
EMAIL_TEMPLATE_PATH = os.getenv("EMAIL_TEMPLATE_PATH", "app/templates/email/")
DEFAULT_EMAIL_LANGUAGE = os.getenv("DEFAULT_EMAIL_LANGUAGE", "english")

# NEW WRITING EVALUATION CONFIGURATION
# Writing evaluation service settings
WRITING_EVALUATION_MODEL = os.getenv("WRITING_EVALUATION_MODEL", "gemini-2.0-flash-live-001")
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))
MIN_TEXT_LENGTH = int(os.getenv("MIN_TEXT_LENGTH", "10"))

# Rate limiting for writing evaluation
EVALUATION_RATE_LIMIT_PER_MINUTE = int(os.getenv("EVALUATION_RATE_LIMIT_PER_MINUTE", "10"))
EVALUATION_RATE_LIMIT_PER_HOUR = int(os.getenv("EVALUATION_RATE_LIMIT_PER_HOUR", "100"))

# Background task configuration
BACKGROUND_TASK_RETRY_ATTEMPTS = int(os.getenv("BACKGROUND_TASK_RETRY_ATTEMPTS", "3"))
EMAIL_SEND_TIMEOUT_SECONDS = int(os.getenv("EMAIL_SEND_TIMEOUT_SECONDS", "30"))

# Optional: Email service provider settings
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

# Database connection pool settings
DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "20"))
DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "30"))

# Feature flags
ENABLE_EMAIL_REPORTS = os.getenv("ENABLE_EMAIL_REPORTS", "true").lower() == "true"
ENABLE_WRITING_EVALUATION = os.getenv("ENABLE_WRITING_EVALUATION", "true").lower() == "true"
ENABLE_PATTERN_ANALYSIS = os.getenv("ENABLE_PATTERN_ANALYSIS", "true").lower() == "true"

# Security settings
EMAIL_RATE_LIMIT_PER_IP = int(os.getenv("EMAIL_RATE_LIMIT_PER_IP", "50"))  # Per hour
WRITING_EVALUATION_RATE_LIMIT_PER_USER = int(os.getenv("WRITING_EVALUATION_RATE_LIMIT_PER_USER", "20"))  # Per hour

# Cache settings for improved performance
REDIS_CACHE_TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "3600"))
ENABLE_RESPONSE_CACHING = os.getenv("ENABLE_RESPONSE_CACHING", "true").lower() == "true"

# Development flags
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
TESTING = os.getenv("TESTING", "false").lower() in ("true", "1", "yes")

# Validation functions
def validate_email_config() -> bool:
    """Validate email configuration"""
    if not ENABLE_EMAIL_REPORTS:
        return True
    
    if not SENDER_EMAIL or not SENDER_EMAIL_PASSWORD:
        return False
    
    return True

def validate_writing_evaluation_config() -> bool:
    """Validate writing evaluation configuration"""
    if not ENABLE_WRITING_EVALUATION:
        return True
    
    if not GEMINI_API_KEY:
        return False
    
    if MIN_TEXT_LENGTH >= MAX_TEXT_LENGTH:
        return False
    
    return True

def get_feature_status() -> dict:
    """Get status of all features"""
    return {
        "email_reports": ENABLE_EMAIL_REPORTS and validate_email_config(),
        "writing_evaluation": ENABLE_WRITING_EVALUATION and validate_writing_evaluation_config(),
        "pattern_analysis": ENABLE_PATTERN_ANALYSIS,
        "response_caching": ENABLE_RESPONSE_CACHING,
        "email_config_valid": validate_email_config(),
        "writing_config_valid": validate_writing_evaluation_config()
    }

def gemini_post_process_text(raw_text: str) -> str:
    """
    Use Gemini LLM to fix spacing, punctuation, and grammar in a raw text string.
    Returns the improved text.
    """
    prompt = (
        "Fix the following text by adding spaces, punctuation, and correcting grammar. "
        "Return only the corrected sentence.\n"
        f"Text: {raw_text}"
    )
    try:
        model = google.genai.GenerativeModel(MODEL, api_key=GEMINI_API_KEY)
        response = model.generate_content(prompt)
        # The response may contain extra whitespace or formatting
        return response.text.strip()
    except Exception as e:
        # If Gemini fails, return the original text
        import logging
        logging.warning(f"Gemini post-processing failed: {e}")
        return raw_text

def get_email_config() -> dict:
    """Get email configuration for services"""
    return {
        "smtp_server": SMTP_SERVER,
        "smtp_port": SMTP_PORT,
        "use_tls": USE_TLS,
        "sender_email": SENDER_EMAIL,
        "sender_password": SENDER_EMAIL_PASSWORD,
        "template_path": EMAIL_TEMPLATE_PATH,
        "default_language": DEFAULT_EMAIL_LANGUAGE,
        "timeout_seconds": EMAIL_SEND_TIMEOUT_SECONDS,
        "retry_attempts": BACKGROUND_TASK_RETRY_ATTEMPTS
    }

def get_writing_evaluation_config() -> dict:
    """Get writing evaluation configuration for services"""
    return {
        "model": WRITING_EVALUATION_MODEL,
        "api_key": GEMINI_API_KEY,
        "max_length": MAX_TEXT_LENGTH,
        "min_length": MIN_TEXT_LENGTH,
        "rate_limit_per_minute": EVALUATION_RATE_LIMIT_PER_MINUTE,
        "rate_limit_per_hour": EVALUATION_RATE_LIMIT_PER_HOUR,
        "rate_limit_per_user": WRITING_EVALUATION_RATE_LIMIT_PER_USER
    }

# """
# Configuration file for Enhanced Multilingual Voice Learning Server
# Contains all constants, settings, and configuration data.
# """

# import os
# from typing import Optional
# import google.genai

# # Server Configuration
# MODEL = "gemini-2.0-flash-live-001"
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# if not GEMINI_API_KEY:
#     raise ValueError("GEMINI_API_KEY environment variable is required")

# # Audio Configuration
# SEND_SAMPLE_RATE = int(os.getenv("SEND_SAMPLE_RATE", 16000))
# RECEIVE_SAMPLE_RATE = int(os.getenv("RECEIVE_SAMPLE_RATE", 24000))

# # Server Network Configuration
# SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
# SERVER_PORT = int(os.getenv("SERVER_PORT", 8765))
# HEALTH_PORT = int(os.getenv("HEALTH_PORT", 8766))
# API_PORT = int(os.getenv("API_PORT", 8000))

# # Database Configuration
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
#     raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required")

# # Redis Configuration
# REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# # Logging Configuration
# LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# # Session Configuration
# SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", 3600))  # 1 hour
# MAX_TURNS_PER_SESSION = int(os.getenv("MAX_TURNS_PER_SESSION", 1000))

# # Scoring Configuration
# DEFAULT_SCORING_WEIGHTS = {
#     "fluency": 0.25,
#     "vocabulary": 0.25,
#     "grammar": 0.25,
#     "pronunciation": 0.25
# }

# DEFAULT_SCORING_SCALES = {
#     "min": 0,
#     "max": 5
# }

# # API Configuration
# API_TITLE = "Enhanced Multilingual Voice Learning Server API"
# API_VERSION = "1.0.0"
# API_DESCRIPTION = """
# REST API for managing teaching modes, scenarios, languages, sessions, and conversations
# in the Enhanced Multilingual Voice Learning Server.
# """

# # CORS Configuration
# CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# # Development flags
# DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
# TESTING = os.getenv("TESTING", "false").lower() in ("true", "1", "yes")

# def gemini_post_process_text(raw_text: str) -> str:
#     """
#     Use Gemini LLM to fix spacing, punctuation, and grammar in a raw text string.
#     Returns the improved text.
#     """
#     prompt = (
#         "Fix the following text by adding spaces, punctuation, and correcting grammar. "
#         "Return only the corrected sentence.\n"
#         f"Text: {raw_text}"
#     )
#     try:
#         model = google.genai.GenerativeModel(MODEL, api_key=GEMINI_API_KEY)
#         response = model.generate_content(prompt)
#         # The response may contain extra whitespace or formatting
#         return response.text.strip()
#     except Exception as e:
#         # If Gemini fails, return the original text
#         import logging
#         logging.warning(f"Gemini post-processing failed: {e}")
#         return raw_text