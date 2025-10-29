"""
Domain models and data classes for the voice learning application
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"


class ConversationRole(str, Enum):
    """Conversation role enumeration"""
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class User:
    """User domain model"""
    id: UUID
    external_id: str
    display_name: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class TeachingMode:
    """Teaching mode domain model"""
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    rubric: Dict[str, Any] = None
    created_at: Optional[datetime] = None


@dataclass
class SupportedLanguage:
    """Supported language domain model"""
    code: str
    label: str
    level_cefr: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class DefaultScenario:
    """Default scenario domain model"""
    id: UUID
    mode_code: str
    title: str
    prompt: str
    language_code: str
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None


@dataclass
class Session:
    """Session domain model"""
    id: UUID
    user_id: UUID
    mode_code: str
    language_code: str
    started_at: datetime
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    status: SessionStatus = SessionStatus.ACTIVE


@dataclass
class Conversation:
    """Conversation turn domain model"""
    id: int
    session_id: UUID
    user_id: UUID
    role: ConversationRole
    turn_index: int
    text: str
    created_at: Optional[datetime] = None


@dataclass
class Evaluation:
    """Evaluation domain model"""
    id: int
    conversation_id: int
    session_id: UUID
    user_id: UUID
    mode_code: str
    metrics: Dict[str, Any]
    total_score: float
    created_at: Optional[datetime] = None


@dataclass
class SessionSummary:
    """Session summary domain model"""
    id: UUID
    session_id: UUID
    user_id: UUID
    summary_json: Dict[str, Any]
    created_at: Optional[datetime] = None


class ScoringMetrics(BaseModel):
    """Scoring metrics model"""
    fluency: float = Field(ge=0, le=5, description="Fluency score (0-5)")
    vocabulary: float = Field(ge=0, le=5, description="Vocabulary score (0-5)")
    grammar: float = Field(ge=0, le=5, description="Grammar score (0-5)")
    pronunciation: float = Field(ge=0, le=5, description="Pronunciation score (0-5)")


class ScoringWeights(BaseModel):
    """Scoring weights configuration"""
    fluency: float = Field(ge=0, le=1, description="Fluency weight")
    vocabulary: float = Field(ge=0, le=1, description="Vocabulary weight")
    grammar: float = Field(ge=0, le=1, description="Grammar weight")
    pronunciation: float = Field(ge=0, le=1, description="Pronunciation weight")
    
    def validate_sum(self) -> bool:
        """Validate that weights sum to 1.0"""
        total = self.fluency + self.vocabulary + self.grammar + self.pronunciation
        return abs(total - 1.0) < 0.001


class ScoringRubric(BaseModel):
    """Complete scoring rubric"""
    weights: ScoringWeights
    scales: Dict[str, float] = Field(default={"min": 0, "max": 5})
    guidelines: Dict[str, str] = Field(default_factory=dict)


class SessionSummarySchema(BaseModel):
    """Session summary schema for consistent JSON structure"""
    title: str
    subtitle: Dict[str, Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Session abc123 Study Notes — Spanish (Beginner Guided)",
                "subtitle": {
                    "0": {
                        "heading": "Key Phrases Practiced",
                        "points": {
                            "0": "Hola, me llamo... (Hello, my name is...)",
                            "1": "¿Cómo estás? (How are you?)",
                            "2": "Mucho gusto (Nice to meet you)"
                        }
                    },
                    "1": {
                        "heading": "Grammar & Corrections",
                        "points": {
                            "0": "Use 'estar' for temporary states: 'Estoy bien'",
                            "1": "Remember gender agreement: 'la casa blanca'",
                            "2": "Verb conjugation: 'yo hablo' not 'yo habla'"
                        }
                    },
                    "2": {
                        "heading": "Pronunciation / Fluency Tips",
                        "points": {
                            "0": "Roll your 'rr' in 'carro' and 'perro'",
                            "1": "Practice the 'ñ' sound in 'niño'",
                            "2": "Work on vowel clarity - Spanish vowels are pure"
                        }
                    },
                    "3": {
                        "heading": "Next Steps",
                        "points": {
                            "0": "Practice daily greetings with native speakers",
                            "1": "Study present tense verb conjugations",
                            "2": "Listen to Spanish podcasts for beginners"
                        }
                    }
                }
            }
        }


@dataclass
class ScoringResult:
    """Result of a scoring operation"""
    metrics: ScoringMetrics
    total_score: float
    mode_specific_adjustments: Dict[str, Any] = None
    feedback: Optional[str] = None


@dataclass
class SessionContext:
    """Complete session context for operations"""
    session: Session
    teaching_mode: TeachingMode
    language: SupportedLanguage
    user: User
    scenario: Optional[DefaultScenario] = None