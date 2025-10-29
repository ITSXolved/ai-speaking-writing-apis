"""
Pydantic models for content (Reading, Listening, Grammar)
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_serializer
from typing import Optional, Dict, List, Literal
from datetime import datetime

class Metadata(BaseModel):
    uploaded_by: str
    company_name: str
    uploaded_time: Optional[datetime] = None

    @field_serializer("uploaded_time")
    def _ser_uploaded_time(self, v: Optional[datetime], _info):
        return v.isoformat() if v else None

class QAItem(BaseModel):
    id: str
    q: str
    options: Dict[str, str]
    answer: Literal["a","b","c","d"]
    explanation: Optional[str] = None
    topic: Optional[str] = None



class OptionMap(BaseModel):
    """Multiple choice options"""
    a: str
    b: str
    c: str
    d: str


class QuestionBase(BaseModel):
    """Base question model"""
    id: str = Field(..., description="Unique question ID within the day")
    q: str = Field(..., description="Question text")
    options: OptionMap
    answer: Literal["a", "b", "c", "d"]
    explanation: Optional[str] = None
    topic: Optional[str] = Field(None, description="Topic/category for analytics")


class ContentMetadata(BaseModel):
    """Metadata for content uploads"""
    uploaded_by: str
    company_name: str = "AILT"
    uploaded_time: datetime = Field(default_factory=datetime.utcnow)
    additional_info: Optional[Dict[str, Any]] = None


# ==================== READING ====================

# class ReadingCreate(BaseModel):
#     """Create reading content"""
#     day_code: str = Field(..., pattern=r"^day\d+$")
#     title: str = Field(..., min_length=1, max_length=200)
#     passage: str = Field(..., min_length=10)
#     questions: List[QuestionBase] = Field(..., min_items=1)
#     metadata: ContentMetadata
    
#     @field_validator('questions')
#     @classmethod
#     def validate_unique_ids(cls, questions):
#         ids = [q.id for q in questions]
#         if len(ids) != len(set(ids)):
#             raise ValueError("Question IDs must be unique")
#         return questions
class ReadingCreate(BaseModel):
    day_code: str = Field(..., pattern=r"^day\d+$")
    title: str = Field(..., min_length=1, max_length=200)
    passage: str = Field(..., min_length=10)
    questions: List[QAItem] = Field(..., min_items=1)
    difficulty_level: Optional[str] = Field("intermediate", description="beginner, intermediate, advanced")
    metadata: Metadata

class ReadingResponse(BaseModel):
    """Reading content response"""
    reading_id: UUID
    day_code: str
    title: str
    passage: str
    questions: List[QuestionBase]
    difficulty_level: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class ReadingListResponse(BaseModel):
    """List of reading contents for a day"""
    day_code: str
    readings: List[ReadingResponse]
    count: int


class ReadingCreateResponse(BaseModel):
    """Response after creating reading"""
    reading_id: UUID
    day_code: str
    difficulty_level: Optional[str]
    message: str = "Reading content created successfully"


# ==================== LISTENING ====================
# 🔧 change ListeningPayload to use Metadata (not ContentMetadata)
class ListeningPayload(BaseModel):
    day_code: str = Field(..., pattern=r"^day\d+$")
    title: str = Field(..., min_length=1, max_length=200)
    questions: List[QuestionBase] = Field(..., min_items=1)
    difficulty_level: Optional[str] = Field("intermediate", description="beginner, intermediate, advanced")
    metadata: Metadata


class ListeningResponse(BaseModel):
    """Listening content response"""
    listening_id: UUID
    day_code: str
    title: str
    audio_url: str
    questions: List[QuestionBase]
    difficulty_level: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class ListeningListResponse(BaseModel):
    """List of listening contents for a day"""
    day_code: str
    listenings: List[ListeningResponse]
    count: int


class ListeningCreateResponse(BaseModel):
    """Response after creating listening"""
    listening_id: UUID
    day_code: str
    audio_url: str
    difficulty_level: Optional[str]
    message: str = "Listening content created successfully"


# ==================== GRAMMAR ====================

class GrammarTask(BaseModel):
    """Grammar task/question"""
    id: str = Field(..., description="Unique task ID within the day")
    type: Literal["mcq", "fill_blank", "short_answer"]
    prompt: str = Field(..., min_length=1)
    options: Optional[OptionMap] = Field(None, description="Required for MCQ")
    answer: str = Field(..., description="Correct answer")
    explanation: Optional[str] = None
    topic: Optional[str] = Field(None, description="Grammar topic for analytics")
    
    @field_validator('options')
    @classmethod
    def validate_mcq_options(cls, options, info):
        if info.data.get('type') == 'mcq' and not options:
            raise ValueError("MCQ type requires options")
        return options


# class GrammarCreate(BaseModel):
#     """Create grammar content"""
#     day_code: str = Field(..., pattern=r"^day\d+$")
#     title: str = Field(..., min_length=1, max_length=200)
#     tasks: List[GrammarTask] = Field(..., min_items=1)
#     metadata: ContentMetadata
    
#     @field_validator('tasks')
#     @classmethod
#     def validate_unique_ids(cls, tasks):
#         ids = [t.id for t in tasks]
#         if len(ids) != len(set(ids)):
#             raise ValueError("Task IDs must be unique")
#         return tasks
class GrammarCreate(BaseModel):
    day_code: str = Field(..., pattern=r"^day\d+$")
    title: str = Field(..., min_length=1, max_length=200)
    tasks: List[GrammarTask] = Field(..., min_items=1)
    difficulty_level: Optional[str] = Field("intermediate", description="beginner, intermediate, advanced")
    metadata: Metadata


class GrammarResponse(BaseModel):
    """Grammar content response"""
    grammar_id: UUID
    day_code: str
    title: str
    tasks: List[GrammarTask]
    difficulty_level: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class GrammarListResponse(BaseModel):
    """List of grammar contents for a day"""
    day_code: str
    grammar_sets: List[GrammarResponse]
    count: int


class GrammarCreateResponse(BaseModel):
    """Response after creating grammar"""
    grammar_id: UUID
    day_code: str
    difficulty_level: Optional[str]
    message: str = "Grammar content created successfully"


# ==================== WRITING ====================

class WritingCreate(BaseModel):
    """Create writing content"""
    day_code: str = Field(..., pattern=r"^day\d+$")
    title: str = Field(..., min_length=1, max_length=200)
    prompts: List[str] = Field(..., min_items=1, description="List of writing prompts/task descriptions")
    word_limit: Optional[int] = Field(None, description="Recommended word count")
    difficulty_level: Optional[str] = Field("intermediate", description="beginner, intermediate, advanced")
    metadata: Metadata

    @field_validator('prompts')
    @classmethod
    def validate_prompts(cls, prompts):
        for prompt in prompts:
            if len(prompt) < 10:
                raise ValueError("Each prompt must be at least 10 characters long")
        return prompts


class WritingResponse(BaseModel):
    """Writing content response"""
    writing_id: UUID
    day_code: str
    title: str
    prompts: List[str]
    word_limit: Optional[int]
    difficulty_level: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class WritingListResponse(BaseModel):
    """List of writing contents for a day"""
    day_code: str
    writings: List[WritingResponse]
    count: int


class WritingCreateResponse(BaseModel):
    """Response after creating writing"""
    writing_id: UUID
    day_code: str
    difficulty_level: Optional[str]
    message: str = "Writing content created successfully"


# ==================== SPEAKING ====================

class SpeakingCreate(BaseModel):
    """Create speaking topic"""
    day_code: str = Field(..., pattern=r"^day\d+$")
    teaching_mode_id: str = Field(..., description="Teaching mode UUID from speaking service")
    teaching_mode_code: str = Field(..., description="Teaching mode code (e.g., 'conversation', 'grammar')")
    title: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=10, description="Speaking topic/prompt description")
    context: Optional[str] = Field(None, description="Additional context or scenario")
    difficulty_level: Optional[str] = Field("intermediate", description="beginner, intermediate, advanced")
    metadata: Metadata


class SpeakingResponse(BaseModel):
    """Speaking topic response"""
    speaking_id: UUID
    day_code: str
    teaching_mode_id: str
    teaching_mode_code: str
    title: str
    topic: str
    context: Optional[str]
    difficulty_level: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class SpeakingListResponse(BaseModel):
    """List of speaking topics for a day"""
    day_code: str
    topics: List[SpeakingResponse]
    count: int


class SpeakingCreateResponse(BaseModel):
    """Response after creating speaking topic"""
    speaking_id: UUID
    day_code: str
    teaching_mode_code: str
    message: str = "Speaking topic created successfully"