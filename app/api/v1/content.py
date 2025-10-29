"""
Content API endpoints for Reading, Listening, Grammar
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional
import json
import logging

from app.models.content import (
    ReadingCreate, ReadingResponse, ReadingCreateResponse, ReadingListResponse,
    ListeningPayload, ListeningResponse, ListeningCreateResponse, ListeningListResponse,
    GrammarCreate, GrammarResponse, GrammarCreateResponse, GrammarListResponse,
    WritingCreate, WritingResponse, WritingCreateResponse, WritingListResponse,
    SpeakingCreate, SpeakingResponse, SpeakingCreateResponse, SpeakingListResponse
)
from app.services.content_service import ContentService
from app.services.storage_service import StorageService
from app.api.deps import verify_admin_role

logger = logging.getLogger(__name__)

# router = APIRouter()

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
import json
from app.models.content import ListeningPayload, ListeningCreateResponse
from app.services.content_service import ContentService

router = APIRouter()
# ==================== READING ENDPOINTS ====================

@router.post("/reading", response_model=ReadingCreateResponse, status_code=201)
async def create_reading(data: ReadingCreate):
    """Create reading content - multiple readings allowed per day with different difficulty levels"""
    try:
        content_service = ContentService()
        result = await content_service.create_reading(data)

        return ReadingCreateResponse(
            reading_id=result['reading_id'],
            day_code=result['day_code'],
            difficulty_level=result.get('difficulty_level')
        )
    except Exception as e:
        logger.error(f"Error creating reading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reading/day/{day_code}", response_model=ReadingListResponse)
async def get_readings_by_day(
    day_code: str,
    difficulty_level: Optional[str] = None
):
    """Get all reading contents for a specific day, optionally filtered by difficulty level"""
    try:
        content_service = ContentService()
        result = await content_service.get_readings_by_day(day_code, difficulty_level)
        return result

    except Exception as e:
        logger.error(f"Error fetching readings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reading/{reading_id}", response_model=ReadingResponse)
async def get_reading_by_id(reading_id: str):
    """Get a specific reading content by ID"""
    try:
        content_service = ContentService()
        result = await content_service.get_reading_by_id(reading_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Reading content not found for ID {reading_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/reading/{reading_id}", response_model=ReadingCreateResponse)
async def update_reading(reading_id: str, data: ReadingCreate):
    """Update reading content by ID"""
    try:
        content_service = ContentService()
        result = await content_service.update_reading(reading_id, data)

        return ReadingCreateResponse(
            reading_id=result['reading_id'],
            day_code=result['day_code'],
            difficulty_level=result.get('difficulty_level'),
            message="Reading content updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reading: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Reading content not found for ID {reading_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reading/{reading_id}", status_code=204)
async def delete_reading(reading_id: str):
    """Delete reading content by ID"""
    try:
        content_service = ContentService()
        await content_service.delete_reading(reading_id)

    except Exception as e:
        logger.error(f"Error deleting reading: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Reading content not found for ID {reading_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LISTENING ENDPOINTS ====================
# app/api/v1/content.py




@router.post("/listening", response_model=ListeningCreateResponse, status_code=201)
async def create_listening(
    payload: str = Form(...),                 # JSON string field named "payload"
    audio_file: UploadFile = File(...),       # REAL file field named "audio_file"
):
    """Create listening content - multiple listenings allowed per day with different difficulty levels"""
    try:
        payload_dict = json.loads(payload)
        data = ListeningPayload.model_validate(payload_dict)

        svc = ContentService()
        result = await svc.create_listening(data, audio_file)  # pass UploadFile through
        return ListeningCreateResponse(
            listening_id=result["listening_id"],
            day_code=result["day_code"],
            audio_url=result["audio_url"],
            difficulty_level=result.get("difficulty_level")
        )
    except Exception as e:
        logger.error(f"Error creating listening: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/listening", response_model=ListeningCreateResponse, status_code=201)
# async def create_listening(
#     payload: str = Form(..., description="JSON payload with listening data"),
#     audio_file: UploadFile = File(..., description="Audio file (MP3, WAV, etc.)"),
#     # admin_user_id: str = Depends(verify_admin_role)
# ):
#     """
#     Create listening content for a day
#     Accepts multipart form with JSON payload and audio file
#     Requires admin authentication
#     """
#     try:
#         # Parse JSON payload
#         try:
#             payload_data = json.loads(payload)
#             listening_data = ListeningPayload(**payload_data)
#         except json.JSONDecodeError as e:
#             raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")
#         except Exception as e:
#             raise HTTPException(status_code=400, detail=f"Invalid payload format: {e}")
        
#         # Validate audio file type
#         allowed_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg']
#         if audio_file.content_type not in allowed_types:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Invalid audio type. Allowed: {', '.join(allowed_types)}"
#             )
        
#         # Upload audio file
#         storage_service = StorageService()
#         audio_url = await storage_service.upload_audio(
#             file=audio_file.file,
#             day_code=listening_data.day_code,
#             filename=audio_file.filename,
#             content_type=audio_file.content_type
#         )
        
#         # Create listening content
#         content_service = ContentService()
#         result = await content_service.create_listening(listening_data, audio_url)
        
#         return ListeningCreateResponse(
#             listening_id=result['listening_id'],
#             day_code=result['day_code'],
#             audio_url=audio_url
#         )
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error creating listening: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


@router.get("/listening/day/{day_code}", response_model=ListeningListResponse)
async def get_listening_by_day(
    day_code: str,
    difficulty_level: Optional[str] = None
):
    """Get all listening contents for a specific day, optionally filtered by difficulty level"""
    try:
        content_service = ContentService()
        result = await content_service.get_listening_by_day(day_code, difficulty_level)
        return result

    except Exception as e:
        logger.error(f"Error fetching listenings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listening/{listening_id}", response_model=ListeningResponse)
async def get_listening_by_id(listening_id: str):
    """Get a specific listening content by ID"""
    try:
        content_service = ContentService()
        result = await content_service.get_listening_by_id(listening_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Listening content not found for ID {listening_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching listening: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/listening/{listening_id}", response_model=ListeningCreateResponse)
async def update_listening(
    listening_id: str,
    payload: str = Form(...),
    audio_file: Optional[UploadFile] = File(None)
):
    """Update listening content by ID - audio file is optional"""
    try:
        payload_dict = json.loads(payload)
        data = ListeningPayload.model_validate(payload_dict)

        content_service = ContentService()
        result = await content_service.update_listening(listening_id, data, audio_file)

        return ListeningCreateResponse(
            listening_id=result['listening_id'],
            day_code=result['day_code'],
            audio_url=result['audio_url'],
            difficulty_level=result.get('difficulty_level'),
            message="Listening content updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating listening: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Listening content not found for ID {listening_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/listening/{listening_id}", status_code=204)
async def delete_listening(listening_id: str):
    """Delete listening content by ID"""
    try:
        content_service = ContentService()
        await content_service.delete_listening(listening_id)

    except Exception as e:
        logger.error(f"Error deleting listening: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Listening content not found for ID {listening_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GRAMMAR ENDPOINTS ====================

@router.post("/grammar", response_model=GrammarCreateResponse, status_code=201)
async def create_grammar(data: GrammarCreate):
    """Create grammar content - multiple grammar sets allowed per day with different difficulty levels"""
    try:
        svc = ContentService()
        result = await svc.create_grammar(data)
        return GrammarCreateResponse(
            grammar_id=result["grammar_id"],
            day_code=result["day_code"],
            difficulty_level=result.get("difficulty_level")
        )
    except Exception as e:
        logger.error(f"Error creating grammar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grammar/day/{day_code}", response_model=GrammarListResponse)
async def get_grammar_by_day(
    day_code: str,
    difficulty_level: Optional[str] = None
):
    """Get all grammar contents for a specific day, optionally filtered by difficulty level"""
    try:
        content_service = ContentService()
        result = await content_service.get_grammar_by_day(day_code, difficulty_level)
        return result

    except Exception as e:
        logger.error(f"Error fetching grammar sets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grammar/{grammar_id}", response_model=GrammarResponse)
async def get_grammar_by_id(grammar_id: str):
    """Get a specific grammar content by ID"""
    try:
        content_service = ContentService()
        result = await content_service.get_grammar_by_id(grammar_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Grammar content not found for ID {grammar_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching grammar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/grammar/{grammar_id}", response_model=GrammarCreateResponse)
async def update_grammar(grammar_id: str, data: GrammarCreate):
    """Update grammar content by ID"""
    try:
        content_service = ContentService()
        result = await content_service.update_grammar(grammar_id, data)

        return GrammarCreateResponse(
            grammar_id=result['grammar_id'],
            day_code=result['day_code'],
            difficulty_level=result.get('difficulty_level'),
            message="Grammar content updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating grammar: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Grammar content not found for ID {grammar_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/grammar/{grammar_id}", status_code=204)
async def delete_grammar(grammar_id: str):
    """Delete grammar content by ID"""
    try:
        content_service = ContentService()
        await content_service.delete_grammar(grammar_id)

    except Exception as e:
        logger.error(f"Error deleting grammar: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Grammar content not found for ID {grammar_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WRITING ENDPOINTS ====================

@router.post("/writing", response_model=WritingCreateResponse, status_code=201)
async def create_writing(data: WritingCreate):
    """Create writing content - multiple writings allowed per day"""
    try:
        svc = ContentService()
        result = await svc.create_writing(data)
        return WritingCreateResponse(
            writing_id=result["writing_id"],
            day_code=result["day_code"],
            difficulty_level=result.get("difficulty_level")
        )
    except Exception as e:
        logger.error(f"Error creating writing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/writing/day/{day_code}", response_model=WritingListResponse)
async def get_writings_by_day(
    day_code: str,
    difficulty_level: Optional[str] = None
):
    """Get all writing contents for a specific day, optionally filtered by difficulty level"""
    try:
        content_service = ContentService()
        result = await content_service.get_writings_by_day(day_code, difficulty_level)
        return result

    except Exception as e:
        logger.error(f"Error fetching writings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/writing/{writing_id}", response_model=WritingResponse)
async def get_writing_by_id(writing_id: str):
    """Get a specific writing content by ID"""
    try:
        content_service = ContentService()
        result = await content_service.get_writing_by_id(writing_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Writing content not found for ID {writing_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching writing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/writing/{writing_id}", response_model=WritingCreateResponse)
async def update_writing(writing_id: str, data: WritingCreate):
    """Update writing content by ID"""
    try:
        content_service = ContentService()
        result = await content_service.update_writing(writing_id, data)

        return WritingCreateResponse(
            writing_id=result["writing_id"],
            day_code=result["day_code"],
            difficulty_level=result.get("difficulty_level"),
            message="Writing content updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating writing: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Writing content not found for ID {writing_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/writing/{writing_id}", status_code=204)
async def delete_writing(writing_id: str):
    """Delete writing content by ID"""
    try:
        content_service = ContentService()
        await content_service.delete_writing(writing_id)

    except Exception as e:
        logger.error(f"Error deleting writing: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Writing content not found for ID {writing_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SPEAKING ENDPOINTS ====================

@router.post("/speaking", response_model=SpeakingCreateResponse, status_code=201)
async def create_speaking(data: SpeakingCreate):
    """Create speaking topic - multiple topics allowed per day"""
    try:
        svc = ContentService()
        result = await svc.create_speaking(data)
        return SpeakingCreateResponse(
            speaking_id=result["speaking_id"],
            day_code=result["day_code"],
            teaching_mode_code=result["teaching_mode_code"],
        )
    except Exception as e:
        logger.error(f"Error creating speaking topic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/speaking/day/{day_code}", response_model=SpeakingListResponse)
async def get_speaking_by_day(
    day_code: str,
    difficulty_level: Optional[str] = None
):
    """Get all speaking topics for a specific day, optionally filtered by difficulty level"""
    try:
        content_service = ContentService()
        result = await content_service.get_speaking_by_day(day_code, difficulty_level)
        return result

    except Exception as e:
        logger.error(f"Error fetching speaking topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/speaking/{speaking_id}", response_model=SpeakingResponse)
async def get_speaking_by_id(speaking_id: str):
    """Get a specific speaking topic by ID"""
    try:
        content_service = ContentService()
        result = await content_service.get_speaking_by_id(speaking_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Speaking topic not found for ID {speaking_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching speaking topic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/speaking/{speaking_id}", response_model=SpeakingCreateResponse)
async def update_speaking(speaking_id: str, data: SpeakingCreate):
    """Update speaking topic by ID"""
    try:
        content_service = ContentService()
        result = await content_service.update_speaking(speaking_id, data)

        return SpeakingCreateResponse(
            speaking_id=result["speaking_id"],
            day_code=result["day_code"],
            teaching_mode_code=result["teaching_mode_code"],
            message="Speaking topic updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating speaking topic: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Speaking topic not found for ID {speaking_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/speaking/{speaking_id}", status_code=204)
async def delete_speaking(speaking_id: str):
    """Delete speaking topic by ID"""
    try:
        content_service = ContentService()
        await content_service.delete_speaking(speaking_id)

    except Exception as e:
        logger.error(f"Error deleting speaking topic: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Speaking topic not found for ID {speaking_id}")
        raise HTTPException(status_code=500, detail=str(e))