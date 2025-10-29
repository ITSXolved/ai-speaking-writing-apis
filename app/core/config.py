"""
Application configuration and settings
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # Storage Configuration
    STORAGE_BUCKET_LISTENING: str = "listening-audio"
    STORAGE_BUCKET_SPEAKING: str = "speaking-audio"
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Ziya LRG API"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "*"
    ]
    
    # Time Configuration
    TIMEZONE: str = "Asia/Kolkata"
    
    # XP & Rewards Configuration
    BASE_XP_PER_SESSION: int = 20
    ACCURACY_BONUS_THRESHOLD: float = 0.80
    ACCURACY_BONUS_XP: int = 10
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()