"""
Storage service for handling file uploads to Supabase Storage
"""
import logging
from typing import BinaryIO
from pathlib import Path

from app.db.supabase import SupabaseService
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService(SupabaseService):
    """Service for file storage operations"""
    
    def __init__(self):
        super().__init__(use_admin=True)
    
    async def upload_audio(
        self,
        file: BinaryIO,
        day_code: str,
        filename: str,
        content_type: str = "audio/mpeg"
    ) -> str:
        """
        Upload audio file to Supabase Storage
        
        Args:
            file: File object to upload
            day_code: Day code (e.g., 'day1')
            filename: Original filename
            content_type: MIME type of the file
        
        Returns:
            Public URL of the uploaded file
        """
        try:
            # Create path: day_code/filename
            file_path = f"{day_code}/{filename}"
            
            # Upload to bucket
            bucket = self.storage.from_(settings.STORAGE_BUCKET_LISTENING)
            
            # Read file content
            file_content = file.read()
            
            result = bucket.upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "upsert": "true"  # Overwrite if exists
                }
            )
            
            # Get public URL
            public_url = bucket.get_public_url(file_path)
            
            logger.info(f"Uploaded audio file: {file_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading audio file: {e}")
            raise
    
    async def upload_speaking_audio(
        self,
        file: BinaryIO,
        user_id: str,
        submission_id: str,
        filename: str,
        content_type: str = "audio/webm"
    ) -> str:
        """
        Upload speaking submission audio
        
        Args:
            file: File object to upload
            user_id: User's UUID
            submission_id: Submission UUID
            filename: Original filename
            content_type: MIME type
        
        Returns:
            Public URL of the uploaded file
        """
        try:
            # Create path: user_id/submission_id/filename
            file_path = f"{user_id}/{submission_id}/{filename}"
            
            bucket = self.storage.from_(settings.STORAGE_BUCKET_SPEAKING)
            
            file_content = file.read()
            
            result = bucket.upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "upsert": "true"
                }
            )
            
            public_url = bucket.get_public_url(file_path)
            
            logger.info(f"Uploaded speaking audio: {file_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading speaking audio: {e}")
            raise
    
    async def delete_file(self, bucket_name: str, file_path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            bucket_name: Bucket name
            file_path: Path to the file
        
        Returns:
            True if successful
        """
        try:
            bucket = self.storage.from_(bucket_name)
            bucket.remove([file_path])
            
            logger.info(f"Deleted file: {file_path} from {bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        """Get public URL for a file"""
        bucket = self.storage.from_(bucket_name)
        return bucket.get_public_url(file_path)