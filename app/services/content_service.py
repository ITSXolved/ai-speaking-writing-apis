"""
Content service for Reading, Listening, Grammar CRUD operations
"""
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from app.db.supabase import SupabaseService
from app.models.content import (
    ReadingCreate, ReadingResponse, ReadingListResponse,
    ListeningPayload, ListeningResponse, ListeningListResponse,
    GrammarCreate, GrammarResponse, GrammarListResponse,
    WritingCreate, WritingResponse, WritingListResponse,
    SpeakingCreate, SpeakingResponse, SpeakingListResponse
)
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


from fastapi.encoders import jsonable_encoder
from datetime import datetime, timezone
from typing import Dict, Any
# content_service.py
from fastapi import UploadFile  # add this
# from app.services.storage_service import LISTENING_BUCKET  # add this

from fastapi import UploadFile, HTTPException
LISTENING_BUCKET = "listening-audio"

class ContentService(SupabaseService):
    """Service for managing content (Reading, Listening, Grammar)"""

    def __init__(self):
        super().__init__(use_admin=True)

    # ==================== READING ====================
    async def create_reading(self, data: "ReadingCreate") -> Dict[str, Any]:
        """Create reading content"""
        try:
            # 1) Model -> JSON-safe dict (datetimes -> ISO strings)
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) Ensure metadata + server timestamp
            meta = data_dict.get("metadata") or {}
            meta.setdefault("uploaded_time", datetime.now(timezone.utc).isoformat())
            data_dict["metadata"] = meta

            # 3) Insert parent row with difficulty level
            reading_result = self.db('readings').insert({
                'day_code': data_dict['day_code'],
                'title': data_dict['title'],
                'passage': data_dict['passage'],
                'difficulty_level': data_dict.get('difficulty_level', 'intermediate'),
                'metadata': data_dict['metadata'],
            }).execute()

            if not reading_result.data:
                raise Exception("Failed to create reading")

            reading = reading_result.data[0]
            reading_id = reading['reading_id']

            # 4) Insert child questions
            questions = data_dict.get('questions', [])
            questions_data = [
                {
                    'reading_id': reading_id,
                    'item_id': q['id'],
                    'prompt': q['q'],
                    'options': q['options'],
                    'correct_answer': q['answer'],
                    'explanation': q.get('explanation'),
                }
                for q in questions
            ]

            if questions_data:
                self.db('reading_questions').insert(questions_data).execute()

            logger.info(f"Created reading content for {data_dict['day_code']}")
            return {
                'reading_id': reading_id,
                'day_code': data_dict['day_code'],
                'difficulty_level': data_dict.get('difficulty_level', 'intermediate'),
            }

        except Exception as e:
            logger.error(f"Error creating reading: {e}")
            raise

    async def get_readings_by_day(self, day_code: str, difficulty_level: Optional[str] = None) -> ReadingListResponse:
        """Get all reading contents for a specific day, optionally filtered by difficulty"""
        try:
            query = self.db('readings').select('*').eq('day_code', day_code)

            if difficulty_level:
                query = query.eq('difficulty_level', difficulty_level)

            reading_result = query.order('created_at', desc=True).execute()

            readings = []
            for reading in reading_result.data:
                # Get questions for this reading
                questions_result = self.db('reading_questions').select('*').eq(
                    'reading_id', reading['reading_id']
                ).order('item_id').execute()

                questions = [
                    {
                        'id': q['item_id'],
                        'q': q['prompt'],
                        'options': q['options'],
                        'answer': q['correct_answer'],
                        'explanation': q['explanation']
                    }
                    for q in questions_result.data
                ]

                readings.append(ReadingResponse(
                    reading_id=reading['reading_id'],
                    day_code=reading['day_code'],
                    title=reading['title'],
                    passage=reading['passage'],
                    questions=questions,
                    difficulty_level=reading.get('difficulty_level'),
                    metadata=reading['metadata'],
                    created_at=reading['created_at']
                ))

            return ReadingListResponse(
                day_code=day_code,
                readings=readings,
                count=len(readings)
            )

        except Exception as e:
            logger.error(f"Error fetching readings: {e}")
            raise

    async def get_reading_by_id(self, reading_id: str) -> Optional[ReadingResponse]:
        """Get a specific reading content by ID"""
        try:
            reading_result = self.db('readings').select('*').eq(
                'reading_id', reading_id
            ).execute()

            if not reading_result.data:
                return None

            reading = reading_result.data[0]

            # Get questions
            questions_result = self.db('reading_questions').select('*').eq(
                'reading_id', reading['reading_id']
            ).order('item_id').execute()

            questions = [
                {
                    'id': q['item_id'],
                    'q': q['prompt'],
                    'options': q['options'],
                    'answer': q['correct_answer'],
                    'explanation': q['explanation']
                }
                for q in questions_result.data
            ]

            return ReadingResponse(
                reading_id=reading['reading_id'],
                day_code=reading['day_code'],
                title=reading['title'],
                passage=reading['passage'],
                questions=questions,
                difficulty_level=reading.get('difficulty_level'),
                metadata=reading['metadata'],
                created_at=reading['created_at']
            )

        except Exception as e:
            logger.error(f"Error fetching reading: {e}")
            raise

    async def update_reading(self, reading_id: str, data: "ReadingCreate") -> Dict[str, Any]:
        """Update reading content by reading_id"""
        try:
            # 1) JSON-safe dict
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) Update metadata timestamp
            meta = data_dict.get("metadata") or {}
            meta["updated_time"] = datetime.now(timezone.utc).isoformat()
            data_dict["metadata"] = meta

            # 3) Update the reading
            reading_result = self.db('readings').update({
                'day_code': data_dict['day_code'],
                'title': data_dict['title'],
                'passage': data_dict['passage'],
                'difficulty_level': data_dict.get('difficulty_level', 'intermediate'),
                'metadata': data_dict['metadata'],
            }).eq('reading_id', reading_id).execute()

            if not reading_result.data:
                raise Exception(f"Reading content not found for ID {reading_id}")

            # 4) Delete old questions
            self.db('reading_questions').delete().eq('reading_id', reading_id).execute()

            # 5) Insert new questions
            questions = data_dict.get('questions', [])
            if questions:
                questions_data = [
                    {
                        'reading_id': reading_id,
                        'item_id': q['id'],
                        'prompt': q['q'],
                        'options': q['options'],
                        'correct_answer': q['answer'],
                        'explanation': q.get('explanation'),
                    }
                    for q in questions
                ]
                self.db('reading_questions').insert(questions_data).execute()

            reading = reading_result.data[0]
            logger.info(f"Updated reading content {reading_id}")
            return {
                'reading_id': reading['reading_id'],
                'day_code': reading['day_code'],
                'difficulty_level': reading.get('difficulty_level'),
            }

        except Exception as e:
            logger.error(f"Error updating reading: {e}")
            raise

    async def delete_reading(self, reading_id: str) -> bool:
        """Delete reading content by reading_id"""
        try:
            # Delete questions first (foreign key)
            self.db('reading_questions').delete().eq('reading_id', reading_id).execute()

            # Delete reading
            result = self.db('readings').delete().eq('reading_id', reading_id).execute()

            if not result.data:
                raise Exception(f"Reading content not found for ID {reading_id}")

            logger.info(f"Deleted reading content {reading_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting reading: {e}")
            raise
    
    # ==================== LISTENING ====================
    
    async def create_listening(self, data: "ListeningPayload", audio_file: UploadFile) -> Dict[str, Any]:
        try:
            # 1) Validate we actually received a file
            if not hasattr(audio_file, "filename"):
                raise HTTPException(status_code=422, detail="audio_file must be a file upload (multipart/form-data)")

            # 2) Make the payload JSON-safe and ensure metadata timestamp
            data_dict = jsonable_encoder(data, exclude_none=True)
            meta = data_dict.get("metadata") or {}
            meta.setdefault("uploaded_time", datetime.now(timezone.utc).isoformat())
            data_dict["metadata"] = meta

            # 3) Read file bytes & infer name/content-type
            filename = audio_file.filename or "audio.mp3"
            content_type = audio_file.content_type or "application/octet-stream"
            file_bytes = await audio_file.read()
            if not file_bytes:
                raise HTTPException(status_code=422, detail="audio_file is empty")

            # 4) Build storage object path
            title_slug = data_dict["title"].lower().replace(" ", "_").replace("/", "_")
            object_path = f"{data_dict['day_code']}/{title_slug}/{filename}"

            # 5) Upload to Supabase Storage (✅ correct client usage)
            # NOTE: self.storage is a SyncStorageClient — do NOT call it like a function.
            self.storage.from_(LISTENING_BUCKET).upload(
                path=object_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            public_url = self.storage.from_(LISTENING_BUCKET).get_public_url(object_path)

            # 6) Insert parent row (store the public URL)
            l_res = self.db("listenings").insert({
                "day_code": data_dict["day_code"],
                "title": data_dict["title"],
                "audio_url": public_url,          # 👈 use the public URL you just got
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
                "metadata": data_dict["metadata"],
            }).execute()
            if not l_res.data:
                raise Exception("Failed to create listening")

            listening_id = l_res.data[0]["listening_id"]

            # 7) Insert child questions
            q_rows = [{
                "listening_id": listening_id,
                "item_id": q["id"],
                "prompt": q["q"],
                "options": q["options"],         # already a dict (jsonable)
                "correct_answer": q["answer"],
                "explanation": q.get("explanation"),
            } for q in data_dict.get("questions", [])]
            if q_rows:
                self.db("listening_questions").insert(q_rows).execute()

            return {
                "listening_id": listening_id,
                "day_code": data_dict["day_code"],
                "audio_url": public_url,          # 👈 return public URL
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating listening: {e}")
            raise
    
    async def get_listening_by_day(self, day_code: str, difficulty_level: Optional[str] = None) -> ListeningListResponse:
        """Get all listening contents for a specific day, optionally filtered by difficulty"""
        try:
            query = self.db('listenings').select('*').eq('day_code', day_code)

            if difficulty_level:
                query = query.eq('difficulty_level', difficulty_level)

            listening_result = query.order('created_at', desc=True).execute()

            listenings = []
            for listening in listening_result.data:
                # Get questions for this listening
                questions_result = self.db('listening_questions').select('*').eq(
                    'listening_id', listening['listening_id']
                ).order('item_id').execute()

                questions = [
                    {
                        'id': q['item_id'],
                        'q': q['prompt'],
                        'options': q['options'],
                        'answer': q['correct_answer'],
                        'explanation': q['explanation']
                    }
                    for q in questions_result.data
                ]

                listenings.append(ListeningResponse(
                    listening_id=listening['listening_id'],
                    day_code=listening['day_code'],
                    title=listening['title'],
                    audio_url=listening['audio_url'],
                    questions=questions,
                    difficulty_level=listening.get('difficulty_level'),
                    metadata=listening['metadata'],
                    created_at=listening['created_at']
                ))

            return ListeningListResponse(
                day_code=day_code,
                listenings=listenings,
                count=len(listenings)
            )

        except Exception as e:
            logger.error(f"Error fetching listenings: {e}")
            raise

    async def get_listening_by_id(self, listening_id: str) -> Optional[ListeningResponse]:
        """Get a specific listening content by ID"""
        try:
            listening_result = self.db('listenings').select('*').eq(
                'listening_id', listening_id
            ).execute()

            if not listening_result.data:
                return None

            listening = listening_result.data[0]

            # Get questions
            questions_result = self.db('listening_questions').select('*').eq(
                'listening_id', listening['listening_id']
            ).order('item_id').execute()

            questions = [
                {
                    'id': q['item_id'],
                    'q': q['prompt'],
                    'options': q['options'],
                    'answer': q['correct_answer'],
                    'explanation': q['explanation']
                }
                for q in questions_result.data
            ]

            return ListeningResponse(
                listening_id=listening['listening_id'],
                day_code=listening['day_code'],
                title=listening['title'],
                audio_url=listening['audio_url'],
                questions=questions,
                difficulty_level=listening.get('difficulty_level'),
                metadata=listening['metadata'],
                created_at=listening['created_at']
            )

        except Exception as e:
            logger.error(f"Error fetching listening: {e}")
            raise

    async def update_listening(self, listening_id: str, data: "ListeningPayload", audio_file: Optional[UploadFile] = None) -> Dict[str, Any]:
        """Update listening content by listening_id"""
        try:
            # 1) JSON-safe dict
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) Update metadata timestamp
            meta = data_dict.get("metadata") or {}
            meta["updated_time"] = datetime.now(timezone.utc).isoformat()
            data_dict["metadata"] = meta

            # 3) Prepare update data
            update_data = {
                "day_code": data_dict["day_code"],
                "title": data_dict["title"],
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
                "metadata": data_dict["metadata"],
            }

            # 4) Handle audio file update if provided
            if audio_file and hasattr(audio_file, "filename"):
                filename = audio_file.filename or "audio.mp3"
                content_type = audio_file.content_type or "application/octet-stream"
                file_bytes = await audio_file.read()

                if file_bytes:
                    # Build storage object path
                    title_slug = data_dict["title"].lower().replace(" ", "_").replace("/", "_")
                    object_path = f"{data_dict['day_code']}/{title_slug}/{filename}"

                    # Upload to Supabase Storage
                    self.storage.from_(LISTENING_BUCKET).upload(
                        path=object_path,
                        file=file_bytes,
                        file_options={"content-type": content_type, "upsert": "true"}
                    )
                    public_url = self.storage.from_(LISTENING_BUCKET).get_public_url(object_path)
                    update_data["audio_url"] = public_url

            # 5) Update the listening
            listening_result = self.db('listenings').update(update_data).eq('listening_id', listening_id).execute()

            if not listening_result.data:
                raise Exception(f"Listening content not found for ID {listening_id}")

            # 6) Delete old questions
            self.db('listening_questions').delete().eq('listening_id', listening_id).execute()

            # 7) Insert new questions
            questions = data_dict.get('questions', [])
            if questions:
                q_rows = [{
                    "listening_id": listening_id,
                    "item_id": q["id"],
                    "prompt": q["q"],
                    "options": q["options"],
                    "correct_answer": q["answer"],
                    "explanation": q.get("explanation"),
                } for q in questions]
                self.db("listening_questions").insert(q_rows).execute()

            listening = listening_result.data[0]
            logger.info(f"Updated listening content {listening_id}")
            return {
                'listening_id': listening['listening_id'],
                'day_code': listening['day_code'],
                'difficulty_level': listening.get('difficulty_level'),
            }

        except Exception as e:
            logger.error(f"Error updating listening: {e}")
            raise

    async def delete_listening(self, listening_id: str) -> bool:
        """Delete listening content by listening_id"""
        try:
            # Delete questions first (foreign key)
            self.db('listening_questions').delete().eq('listening_id', listening_id).execute()

            # Delete listening
            result = self.db('listenings').delete().eq('listening_id', listening_id).execute()

            if not result.data:
                raise Exception(f"Listening content not found for ID {listening_id}")

            logger.info(f"Deleted listening content {listening_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting listening: {e}")
            raise
    
    # ==================== GRAMMAR ====================
    async def create_grammar(self, data: "GrammarCreate") -> Dict[str, Any]:
        """Create grammar content"""
        try:
            # 1) JSON-safe dict
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) metadata with server timestamp if missing
            meta = data_dict.get("metadata") or {}
            meta.setdefault("uploaded_time", datetime.now(timezone.utc).isoformat())
            data_dict["metadata"] = meta

            # 3) parent insert with difficulty level
            g_res = self.db("grammar_sets").insert({
                "day_code": data_dict["day_code"],
                "title": data_dict["title"],
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
                "metadata": data_dict["metadata"],
            }).execute()
            if not g_res.data:
                raise Exception("Failed to create grammar set")

            grammar = g_res.data[0]
            grammar_id = grammar["grammar_id"]

            # 4) child tasks
            tasks = data_dict.get("tasks", [])
            task_rows = []
            for t in tasks:
                row = {
                    "grammar_id": grammar_id,
                    "item_id": t["id"],
                    "task_type": t["type"],
                    "prompt": t["prompt"],
                    "correct_answer": t["answer"],
                    "explanation": t.get("explanation"),
                    "topic": t.get("topic"),
                }
                # options is optional for fill_blank/short_answer
                if "options" in t and t["options"] is not None:
                    row["options"] = t["options"]
                task_rows.append(row)

            if task_rows:
                self.db("grammar_tasks").insert(task_rows).execute()

            logger.info(f"Created grammar content for {data_dict['day_code']}")
            return {
                "grammar_id": grammar_id,
                "day_code": data_dict["day_code"],
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
            }

        except Exception as e:
            logger.error(f"Error creating grammar: {e}")
            raise
    
    # async def create_grammar(self, data: GrammarCreate) -> Dict[str, Any]:
    #     """Create grammar content"""
    #     try:
    #         # Insert into grammar_sets table
    #         grammar_result = self.db('grammar_sets').insert({
    #             'day_code': data.day_code,
    #             'title': data.title,
    #             'metadata': data.metadata.model_dump()
    #         }).execute()
            
    #         if not grammar_result.data:
    #             raise Exception("Failed to create grammar set")
            
    #         grammar = grammar_result.data[0]
    #         grammar_id = grammar['grammar_id']
            
    #         # Insert tasks
    #         tasks_data = [
    #             {
    #                 'grammar_id': grammar_id,
    #                 'item_id': t.id,
    #                 'task_type': t.type,
    #                 'prompt': t.prompt,
    #                 'options': t.options.model_dump() if t.options else None,
    #                 'correct_answer': t.answer,
    #                 'explanation': t.explanation
    #             }
    #             for t in data.tasks
    #         ]
            
    #         self.db('grammar_tasks').insert(tasks_data).execute()
            
    #         logger.info(f"Created grammar content for {data.day_code}")
    #         return grammar
            
    #     except Exception as e:
    #         logger.error(f"Error creating grammar: {e}")
    #         raise
    
    async def get_grammar_by_day(self, day_code: str, difficulty_level: Optional[str] = None) -> GrammarListResponse:
        """Get all grammar contents for a specific day, optionally filtered by difficulty"""
        try:
            query = self.db('grammar_sets').select('*').eq('day_code', day_code)

            if difficulty_level:
                query = query.eq('difficulty_level', difficulty_level)

            grammar_result = query.order('created_at', desc=True).execute()

            grammar_sets = []
            for grammar in grammar_result.data:
                # Get tasks for this grammar set
                tasks_result = self.db('grammar_tasks').select('*').eq(
                    'grammar_id', grammar['grammar_id']
                ).order('item_id').execute()

                tasks = [
                    {
                        'id': t['item_id'],
                        'type': t['task_type'],
                        'prompt': t['prompt'],
                        'options': t['options'],
                        'answer': t['correct_answer'],
                        'explanation': t['explanation'],
                        'topic': t.get('topic')
                    }
                    for t in tasks_result.data
                ]

                grammar_sets.append(GrammarResponse(
                    grammar_id=grammar['grammar_id'],
                    day_code=grammar['day_code'],
                    title=grammar['title'],
                    tasks=tasks,
                    difficulty_level=grammar.get('difficulty_level'),
                    metadata=grammar['metadata'],
                    created_at=grammar['created_at']
                ))

            return GrammarListResponse(
                day_code=day_code,
                grammar_sets=grammar_sets,
                count=len(grammar_sets)
            )

        except Exception as e:
            logger.error(f"Error fetching grammar sets: {e}")
            raise

    async def get_grammar_by_id(self, grammar_id: str) -> Optional[GrammarResponse]:
        """Get a specific grammar content by ID"""
        try:
            grammar_result = self.db('grammar_sets').select('*').eq(
                'grammar_id', grammar_id
            ).execute()

            if not grammar_result.data:
                return None

            grammar = grammar_result.data[0]

            # Get tasks
            tasks_result = self.db('grammar_tasks').select('*').eq(
                'grammar_id', grammar['grammar_id']
            ).order('item_id').execute()

            tasks = [
                {
                    'id': t['item_id'],
                    'type': t['task_type'],
                    'prompt': t['prompt'],
                    'options': t['options'],
                    'answer': t['correct_answer'],
                    'explanation': t['explanation'],
                    'topic': t.get('topic')
                }
                for t in tasks_result.data
            ]

            return GrammarResponse(
                grammar_id=grammar['grammar_id'],
                day_code=grammar['day_code'],
                title=grammar['title'],
                tasks=tasks,
                difficulty_level=grammar.get('difficulty_level'),
                metadata=grammar['metadata'],
                created_at=grammar['created_at']
            )

        except Exception as e:
            logger.error(f"Error fetching grammar: {e}")
            raise

    async def update_grammar(self, grammar_id: str, data: "GrammarCreate") -> Dict[str, Any]:
        """Update grammar content by grammar_id"""
        try:
            # 1) JSON-safe dict
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) Update metadata timestamp
            meta = data_dict.get("metadata") or {}
            meta["updated_time"] = datetime.now(timezone.utc).isoformat()
            data_dict["metadata"] = meta

            # 3) Update the grammar set
            grammar_result = self.db('grammar_sets').update({
                'day_code': data_dict['day_code'],
                'title': data_dict['title'],
                'difficulty_level': data_dict.get('difficulty_level', 'intermediate'),
                'metadata': data_dict['metadata'],
            }).eq('grammar_id', grammar_id).execute()

            if not grammar_result.data:
                raise Exception(f"Grammar content not found for ID {grammar_id}")

            # 4) Delete old tasks
            self.db('grammar_tasks').delete().eq('grammar_id', grammar_id).execute()

            # 5) Insert new tasks
            tasks = data_dict.get('tasks', [])
            if tasks:
                task_rows = []
                for t in tasks:
                    row = {
                        "grammar_id": grammar_id,
                        "item_id": t["id"],
                        "task_type": t["type"],
                        "prompt": t["prompt"],
                        "correct_answer": t["answer"],
                        "explanation": t.get("explanation"),
                        "topic": t.get("topic"),
                    }
                    if "options" in t and t["options"] is not None:
                        row["options"] = t["options"]
                    task_rows.append(row)

                self.db('grammar_tasks').insert(task_rows).execute()

            grammar = grammar_result.data[0]
            logger.info(f"Updated grammar content {grammar_id}")
            return {
                'grammar_id': grammar['grammar_id'],
                'day_code': grammar['day_code'],
                'difficulty_level': grammar.get('difficulty_level'),
            }

        except Exception as e:
            logger.error(f"Error updating grammar: {e}")
            raise

    async def delete_grammar(self, grammar_id: str) -> bool:
        """Delete grammar content by grammar_id"""
        try:
            # Delete tasks first (foreign key)
            self.db('grammar_tasks').delete().eq('grammar_id', grammar_id).execute()

            # Delete grammar set
            result = self.db('grammar_sets').delete().eq('grammar_id', grammar_id).execute()

            if not result.data:
                raise Exception(f"Grammar content not found for ID {grammar_id}")

            logger.info(f"Deleted grammar content {grammar_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting grammar: {e}")
            raise

    # ==================== WRITING ====================
    async def create_writing(self, data: "WritingCreate") -> Dict[str, Any]:
        """Create writing content"""
        try:
            # 1) JSON-safe dict
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) metadata with server timestamp if missing
            meta = data_dict.get("metadata") or {}
            meta.setdefault("uploaded_time", datetime.now(timezone.utc).isoformat())
            data_dict["metadata"] = meta

            # 3) Insert into writings table
            writing_result = self.db("writings").insert({
                "day_code": data_dict["day_code"],
                "title": data_dict["title"],
                "prompts": data_dict["prompts"],  # Now stores array of prompts
                "word_limit": data_dict.get("word_limit"),
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
                "metadata": data_dict["metadata"],
            }).execute()

            if not writing_result.data:
                raise Exception("Failed to create writing")

            writing = writing_result.data[0]
            writing_id = writing["writing_id"]

            logger.info(f"Created writing content for {data_dict['day_code']}")
            return {
                "writing_id": writing_id,
                "day_code": data_dict["day_code"],
            }

        except Exception as e:
            logger.error(f"Error creating writing: {e}")
            raise

    async def get_writings_by_day(self, day_code: str, difficulty_level: Optional[str] = None) -> WritingListResponse:
        """Get all writing contents for a specific day, optionally filtered by difficulty"""
        try:
            query = self.db("writings").select("*").eq("day_code", day_code)

            if difficulty_level:
                query = query.eq("difficulty_level", difficulty_level)

            writing_result = query.order("created_at", desc=True).execute()

            writings = [
                WritingResponse(
                    writing_id=w["writing_id"],
                    day_code=w["day_code"],
                    title=w["title"],
                    prompts=w["prompts"],  # Now returns array of prompts
                    word_limit=w.get("word_limit"),
                    difficulty_level=w.get("difficulty_level"),
                    metadata=w["metadata"],
                    created_at=w["created_at"]
                )
                for w in writing_result.data
            ]

            return WritingListResponse(
                day_code=day_code,
                writings=writings,
                count=len(writings)
            )

        except Exception as e:
            logger.error(f"Error fetching writings: {e}")
            raise

    async def get_writing_by_id(self, writing_id: str) -> Optional[WritingResponse]:
        """Get a specific writing content by ID"""
        try:
            writing_result = self.db("writings").select("*").eq(
                "writing_id", writing_id
            ).execute()

            if not writing_result.data:
                return None

            writing = writing_result.data[0]

            return WritingResponse(
                writing_id=writing["writing_id"],
                day_code=writing["day_code"],
                title=writing["title"],
                prompts=writing["prompts"],  # Now returns array of prompts
                word_limit=writing.get("word_limit"),
                difficulty_level=writing.get("difficulty_level"),
                metadata=writing["metadata"],
                created_at=writing["created_at"]
            )

        except Exception as e:
            logger.error(f"Error fetching writing: {e}")
            raise

    async def update_writing(self, writing_id: str, data: "WritingCreate") -> Dict[str, Any]:
        """Update writing content by writing_id"""
        try:
            # 1) JSON-safe dict
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) Update metadata timestamp
            meta = data_dict.get("metadata") or {}
            meta["updated_time"] = datetime.now(timezone.utc).isoformat()
            data_dict["metadata"] = meta

            # 3) Update the writing
            writing_result = self.db("writings").update({
                "day_code": data_dict["day_code"],
                "title": data_dict["title"],
                "prompts": data_dict["prompts"],  # Now updates array of prompts
                "word_limit": data_dict.get("word_limit"),
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
                "metadata": data_dict["metadata"],
            }).eq("writing_id", writing_id).execute()

            if not writing_result.data:
                raise Exception(f"Writing content not found for ID {writing_id}")

            writing = writing_result.data[0]

            logger.info(f"Updated writing content {writing_id}")
            return {
                "writing_id": writing["writing_id"],
                "day_code": writing["day_code"],
            }

        except Exception as e:
            logger.error(f"Error updating writing: {e}")
            raise

    async def delete_writing(self, writing_id: str) -> bool:
        """Delete writing content by writing_id"""
        try:
            result = self.db("writings").delete().eq(
                "writing_id", writing_id
            ).execute()

            if not result.data:
                raise Exception(f"Writing content not found for ID {writing_id}")

            logger.info(f"Deleted writing content {writing_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting writing: {e}")
            raise

    # ==================== SPEAKING ====================
    async def create_speaking(self, data: "SpeakingCreate") -> Dict[str, Any]:
        """Create speaking topic"""
        try:
            # 1) JSON-safe dict
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) metadata with server timestamp if missing
            meta = data_dict.get("metadata") or {}
            meta.setdefault("uploaded_time", datetime.now(timezone.utc).isoformat())
            data_dict["metadata"] = meta

            # 3) Insert into speaking_topics table
            speaking_result = self.db("speaking_topics").insert({
                "day_code": data_dict["day_code"],
                "teaching_mode_id": data_dict["teaching_mode_id"],
                "teaching_mode_code": data_dict["teaching_mode_code"],
                "title": data_dict["title"],
                "topic": data_dict["topic"],
                "context": data_dict.get("context"),
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
                "metadata": data_dict["metadata"],
            }).execute()

            if not speaking_result.data:
                raise Exception("Failed to create speaking topic")

            speaking = speaking_result.data[0]
            speaking_id = speaking["speaking_id"]

            logger.info(f"Created speaking topic for {data_dict['day_code']}")
            return {
                "speaking_id": speaking_id,
                "day_code": data_dict["day_code"],
                "teaching_mode_code": data_dict["teaching_mode_code"],
            }

        except Exception as e:
            logger.error(f"Error creating speaking topic: {e}")
            raise

    async def get_speaking_by_day(self, day_code: str, difficulty_level: Optional[str] = None) -> SpeakingListResponse:
        """Get all speaking topics for a specific day, optionally filtered by difficulty"""
        try:
            query = self.db("speaking_topics").select("*").eq("day_code", day_code)

            if difficulty_level:
                query = query.eq("difficulty_level", difficulty_level)

            speaking_result = query.order("created_at", desc=True).execute()

            topics = [
                SpeakingResponse(
                    speaking_id=s["speaking_id"],
                    day_code=s["day_code"],
                    teaching_mode_id=s["teaching_mode_id"],
                    teaching_mode_code=s["teaching_mode_code"],
                    title=s["title"],
                    topic=s["topic"],
                    context=s.get("context"),
                    difficulty_level=s.get("difficulty_level"),
                    metadata=s["metadata"],
                    created_at=s["created_at"]
                )
                for s in speaking_result.data
            ]

            return SpeakingListResponse(
                day_code=day_code,
                topics=topics,
                count=len(topics)
            )

        except Exception as e:
            logger.error(f"Error fetching speaking topics: {e}")
            raise

    async def get_speaking_by_id(self, speaking_id: str) -> Optional[SpeakingResponse]:
        """Get a specific speaking topic by ID"""
        try:
            speaking_result = self.db("speaking_topics").select("*").eq(
                "speaking_id", speaking_id
            ).execute()

            if not speaking_result.data:
                return None

            s = speaking_result.data[0]

            return SpeakingResponse(
                speaking_id=s["speaking_id"],
                day_code=s["day_code"],
                teaching_mode_id=s["teaching_mode_id"],
                teaching_mode_code=s["teaching_mode_code"],
                title=s["title"],
                topic=s["topic"],
                context=s.get("context"),
                difficulty_level=s.get("difficulty_level"),
                metadata=s["metadata"],
                created_at=s["created_at"]
            )

        except Exception as e:
            logger.error(f"Error fetching speaking topic: {e}")
            raise

    async def update_speaking(self, speaking_id: str, data: "SpeakingCreate") -> Dict[str, Any]:
        """Update speaking topic by speaking_id"""
        try:
            # 1) JSON-safe dict
            data_dict = jsonable_encoder(data, exclude_none=True)

            # 2) Update metadata timestamp
            meta = data_dict.get("metadata") or {}
            meta["updated_time"] = datetime.now(timezone.utc).isoformat()
            data_dict["metadata"] = meta

            # 3) Update the speaking topic
            speaking_result = self.db("speaking_topics").update({
                "day_code": data_dict["day_code"],
                "teaching_mode_id": data_dict["teaching_mode_id"],
                "teaching_mode_code": data_dict["teaching_mode_code"],
                "title": data_dict["title"],
                "topic": data_dict["topic"],
                "context": data_dict.get("context"),
                "difficulty_level": data_dict.get("difficulty_level", "intermediate"),
                "metadata": data_dict["metadata"],
            }).eq("speaking_id", speaking_id).execute()

            if not speaking_result.data:
                raise Exception(f"Speaking topic not found for ID {speaking_id}")

            speaking = speaking_result.data[0]

            logger.info(f"Updated speaking topic {speaking_id}")
            return {
                "speaking_id": speaking["speaking_id"],
                "day_code": speaking["day_code"],
                "teaching_mode_code": speaking["teaching_mode_code"],
            }

        except Exception as e:
            logger.error(f"Error updating speaking topic: {e}")
            raise

    async def delete_speaking(self, speaking_id: str) -> bool:
        """Delete speaking topic by speaking_id"""
        try:
            result = self.db("speaking_topics").delete().eq(
                "speaking_id", speaking_id
            ).execute()

            if not result.data:
                raise Exception(f"Speaking topic not found for ID {speaking_id}")

            logger.info(f"Deleted speaking topic {speaking_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting speaking topic: {e}")
            raise