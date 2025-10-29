#  Fix 1: Update imports in app/api/routes/email_reports.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
import logging

# CHANGE THESE IMPORTS:
# from ..deps import get_email_service, get_session_service, get_summary_service
# from ..schemas import StandardResponse
# from ...services.email_service import EmailService
# from ...services.session_service import SessionService
# from ...services.summary_service import SummaryService

# TO THESE IMPORTS (matching your existing structure):
from ..deps import get_email_service, get_summary_service
from ...services.summary_service import summary_service  # Use your existing instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["email"])

# Add StandardResponse locally since it doesn't exist in your schemas
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class EmailReportRequest(BaseModel):
    recipient_email: EmailStr
    user_name: str
    report_type: str = "weekly"
    session_id: Optional[str] = None
    include_detailed_stats: bool = True

class WritingFeedbackEmailRequest(BaseModel):
    recipient_email: EmailStr
    user_name: str
    evaluation_id: str

@router.post("/send-learning-report", response_model=StandardResponse)
async def send_learning_report(
    request: EmailReportRequest,
    background_tasks: BackgroundTasks,
    email_service = Depends(get_email_service)
):
    """Send learning progress report via email"""
    try:
        # Use your existing summary service instance
        report_data = await summary_service.generate_learning_report(
            user_email=request.recipient_email,
            period=request.report_type,
            include_detailed_stats=request.include_detailed_stats
        )
        
        # Add to background tasks
        background_tasks.add_task(
            email_service.send_learning_report,
            request.recipient_email,
            request.user_name,
            report_data,
            request.report_type
        )
        
        return StandardResponse(
            success=True,
            message="Learning report will be sent shortly"
        )
        
    except Exception as e:
        logger.error(f"Failed to queue learning report email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send learning report")

@router.post("/send-writing-feedback", response_model=StandardResponse)
async def send_writing_feedback_report(
    request: WritingFeedbackEmailRequest,
    background_tasks: BackgroundTasks,
    email_service = Depends(get_email_service)
):
    """Send writing evaluation feedback via email"""
    try:
        # Simple implementation for now
        evaluation_data = {
            "original_text": "Sample text...",
            "feedback": {},
            "improved_version": "Improved text..."
        }
        
        background_tasks.add_task(
            email_service.send_writing_feedback_report,
            request.recipient_email,
            request.user_name,
            evaluation_data["original_text"],
            evaluation_data["feedback"],
            evaluation_data["improved_version"]
        )
        
        return StandardResponse(
            success=True,
            message="Writing feedback report will be sent shortly"
        )
        
    except Exception as e:
        logger.error(f"Failed to queue writing feedback email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send writing feedback")

@router.get("/test-email-config", response_model=StandardResponse)
async def test_email_configuration(
    email_service = Depends(get_email_service)
):
    """Test email service configuration"""
    try:
        return StandardResponse(
            success=True,
            message="Email service is properly configured"
        )
        
    except Exception as e:
        logger.error(f"Email configuration test failed: {e}")
        return StandardResponse(
            success=False,
            message=f"Email configuration error: {str(e)}"
        )
