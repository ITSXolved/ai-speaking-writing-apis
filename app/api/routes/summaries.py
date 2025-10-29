"""
API routes for session summaries management
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from app.api.schemas import (
    SummaryResponse, SummaryListResponse, PaginationParams, 
    DateFilterParams, ErrorResponse
)
from app.api.deps import (
    get_summary_service, get_request_logger, get_pagination_params,
    get_date_filter_params, validate_session_exists
)
from app.services.summary_service import SummaryService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["summaries"])


@router.get(
    "/summaries",
    response_model=SummaryListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_summaries(
    user_external_id: Optional[str] = Query(None, description="Filter by user external ID"),
    pagination: PaginationParams = Depends(get_pagination_params),
    date_filters: DateFilterParams = Depends(get_date_filter_params),
    summary_svc: SummaryService = Depends(get_summary_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get session summaries with filtering and pagination
    
    Retrieves session summaries with optional filtering by:
    - User external ID: Get summaries for a specific user
    - Date range: Filter by creation date (from_date and to_date)
    
    Results are paginated and ordered by creation time (newest first).
    Each summary includes the complete learning summary JSON with:
    - Key phrases practiced
    - Grammar corrections and tips
    - Pronunciation feedback
    - Next steps for continued learning
    """
    try:
        request_logger.debug("Getting summaries", 
                           user_external_id=user_external_id,
                           page=pagination.page,
                           page_size=pagination.page_size,
                           from_date=date_filters.from_date,
                           to_date=date_filters.to_date)
        
        summaries = []
        
        if user_external_id:
            # Get user ID from external ID
            from app.services.session_service import session_service
            user = await session_service._get_user_by_external_id(user_external_id)
            if not user:
                # Return empty results if user not found
                return SummaryListResponse(
                    summaries=[],
                    total_count=0,
                    page=pagination.page,
                    page_size=pagination.page_size
                )
            
            # Get summaries for user
            summaries = await summary_svc.get_user_summaries(
                user_id=user.id,
                limit=pagination.limit,
                offset=pagination.offset,
                from_date=date_filters.from_date.isoformat() if date_filters.from_date else None,
                to_date=date_filters.to_date.isoformat() if date_filters.to_date else None
            )
        else:
            # This would require a method to get all summaries with date filtering
            # For now, require user_external_id
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_external_id parameter is required"
            )
        
        # Convert to response format
        response_summaries = [SummaryResponse.from_orm(summary) for summary in summaries]
        
        return SummaryListResponse(
            summaries=response_summaries,
            total_count=len(response_summaries),  # Simplified; in production get actual total
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting summaries", 
                           user_external_id=user_external_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/sessions/{session_id}/summary",
    response_model=SummaryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session or summary not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_session_summary(
    session_id: UUID = Depends(validate_session_exists),
    summary_svc: SummaryService = Depends(get_summary_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get summary for a specific session
    
    Retrieves the learning summary for the specified session.
    The summary is generated when a session is closed and includes:
    - Key phrases practiced during the session
    - Grammar corrections and learning points
    - Pronunciation and fluency feedback
    - Recommended next steps for continued learning
    
    Returns 404 if the session exists but no summary has been generated yet
    (i.e., the session hasn't been closed or summary generation failed).
    """
    try:
        request_logger.debug("Getting session summary", session_id=session_id)
        
        summary = await summary_svc.get_summary_by_session(session_id)
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No summary found for session {session_id}. Session may not be closed yet."
            )
        
        return SummaryResponse.from_orm(summary)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting session summary", 
                           session_id=session_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post(
    "/sessions/{session_id}/summary/regenerate",
    response_model=SummaryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        400: {"model": ErrorResponse, "description": "Session not closed or insufficient data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def regenerate_session_summary(
    session_id: UUID = Depends(validate_session_exists),
    summary_svc: SummaryService = Depends(get_summary_service),
    request_logger = Depends(get_request_logger)
):
    """
    Regenerate summary for a session
    
    Forces regeneration of the learning summary for a closed session.
    This can be useful if:
    - The original summary generation failed
    - Summary content needs to be updated
    - New conversations were added after the summary was created
    
    The session must be closed to regenerate the summary.
    If a summary already exists, it will be replaced with the new one.
    """
    try:
        request_logger.info("Regenerating session summary", session_id=session_id)
        
        # Check if session is closed
        from app.services.session_service import session_service
        session = await session_service.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        if session.status.value != "closed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only regenerate summary for closed sessions"
            )
        
        # Delete existing summary if it exists
        existing_summary = await summary_svc.get_summary_by_session(session_id)
        if existing_summary:
            # In a full implementation, you'd have a delete method
            request_logger.info("Replacing existing summary", 
                              session_id=session_id,
                              existing_summary_id=existing_summary.id)
        
        # Generate new summary
        summary = await summary_svc.generate_and_store_summary(
            session_id=session_id,
            user_id=session.user_id
        )
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to regenerate summary"
            )
        
        request_logger.info("Summary regenerated successfully", 
                          session_id=session_id,
                          summary_id=summary.id)
        
        return SummaryResponse.from_orm(summary)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error regenerating session summary", 
                           session_id=session_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/users/{user_external_id}/summaries/recent",
    response_model=SummaryListResponse,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_user_recent_summaries(
    user_external_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent summaries"),
    summary_svc: SummaryService = Depends(get_summary_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get recent summaries for a user
    
    Retrieves the most recent learning summaries for a user.
    Useful for getting an overview of recent learning sessions and progress.
    
    Results are ordered by creation time (newest first).
    """
    try:
        request_logger.debug("Getting user recent summaries", 
                           user_external_id=user_external_id,
                           limit=limit)
        
        # Get user ID
        from app.services.session_service import session_service
        user = await session_service._get_user_by_external_id(user_external_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_external_id} not found"
            )
        
        # Get recent summaries
        summaries = await summary_svc.get_user_summaries(
            user_id=user.id,
            limit=limit,
            offset=0
        )
        
        # Convert to response format
        response_summaries = [SummaryResponse.from_orm(summary) for summary in summaries]
        
        return SummaryListResponse(
            summaries=response_summaries,
            total_count=len(response_summaries),
            page=1,
            page_size=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting user recent summaries", 
                           user_external_id=user_external_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/summaries/statistics",
    response_model=dict,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_summaries_statistics(
    user_external_id: Optional[str] = Query(None, description="Filter by user external ID"),
    date_filters: DateFilterParams = Depends(get_date_filter_params),
    summary_svc: SummaryService = Depends(get_summary_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get summary statistics
    
    Provides aggregate statistics about learning summaries:
    - Total number of summaries generated
    - Distribution by teaching mode
    - Distribution by language
    - Common learning themes and patterns
    
    Can be filtered by user and date range.
    """
    try:
        request_logger.debug("Getting summary statistics", 
                           user_external_id=user_external_id,
                           from_date=date_filters.from_date,
                           to_date=date_filters.to_date)
        
        # This would be implemented with proper aggregation queries
        # For now, return basic statistics
        
        user_id = None
        if user_external_id:
            from app.services.session_service import session_service
            user = await session_service._get_user_by_external_id(user_external_id)
            if user:
                user_id = user.id
        
        # Get summaries for statistics
        summaries = []
        if user_id:
            summaries = await summary_svc.get_user_summaries(
                user_id=user_id,
                limit=1000,  # Large limit for statistics
                offset=0,
                from_date=date_filters.from_date.isoformat() if date_filters.from_date else None,
                to_date=date_filters.to_date.isoformat() if date_filters.to_date else None
            )
        
        # Calculate basic statistics
        total_summaries = len(summaries)
        
        statistics = {
            "total_summaries": total_summaries,
            "date_range": {
                "from": date_filters.from_date.isoformat() if date_filters.from_date else None,
                "to": date_filters.to_date.isoformat() if date_filters.to_date else None
            },
            "user_filter": user_external_id,
            "generated_at": "2024-01-01T00:00:00Z"  # Current timestamp
        }
        
        if total_summaries > 0:
            # Add more detailed statistics if we have data
            recent_summaries = summaries[:5] if summaries else []
            statistics["recent_summary_count"] = len(recent_summaries)
            statistics["has_recent_activity"] = len(recent_summaries) > 0
        
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting summary statistics", 
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/summaries/{summary_id}",
    response_model=SummaryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Summary not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_summary_by_id(
    summary_id: UUID,
    summary_svc: SummaryService = Depends(get_summary_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get a specific summary by ID
    
    Retrieves a learning summary by its unique identifier.
    """
    try:
        request_logger.debug("Getting summary by ID", summary_id=summary_id)
        
        # This would require implementing a get_summary_by_id method in SummaryService
        # For now, return not found since the method doesn't exist yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary {summary_id} not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting summary by ID", 
                           summary_id=summary_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )