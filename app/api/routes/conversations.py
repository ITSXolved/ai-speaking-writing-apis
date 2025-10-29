"""
API routes for conversation management
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from app.api.schemas import (
    ConversationTurnRequest, ConversationTurnResponse, ConversationHistoryResponse,
    PaginationParams, ConversationSearchParams, ErrorResponse
)
from app.api.deps import (
    get_conversation_service, get_request_logger, get_pagination_params,
    validate_session_exists, get_session_service
)
from app.services.conversation_service import ConversationService
from app.domain.models import ConversationRole

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["conversations"])


class ConversationCreateRequest(ConversationTurnRequest):
    """Legacy request payload that includes session_id"""
    session_id: UUID


@router.post(
    "/conversations",
    response_model=ConversationTurnResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        400: {"model": ErrorResponse, "description": "Invalid turn data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def add_conversation_turn_legacy(
    turn_data: ConversationCreateRequest,
    conversation_svc: ConversationService = Depends(get_conversation_service),
    session_svc = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Legacy endpoint for adding a conversation turn.

    This handler mirrors the older `/api/v1/conversations` API that accepted the
    session_id in the request body. It delegates to the newer implementation so
    notebooks and tests that still use the legacy route continue to work.
    """
    try:
        # Validate session exists
        session = await session_svc.get_session(turn_data.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {turn_data.session_id} not found"
            )

        request_logger.info(
            "Adding conversation turn (legacy endpoint)",
            session_id=str(turn_data.session_id),
            role=turn_data.role.value,
            text_length=len(turn_data.text)
        )

        result = await conversation_svc.add_turn(
            session_id=turn_data.session_id,
            role=turn_data.role,
            text=turn_data.text
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add conversation turn"
            )

        response_data = ConversationTurnResponse(
            conversation_id=result["conversation_id"],
            turn_index=result["turn_index"],
            role=ConversationRole(result["role"]),
            text=result["text"],
            created_at=result.get("created_at")
        )

        if result.get("evaluation"):
            from app.api.schemas import EvaluationResponse
            response_data.evaluation = EvaluationResponse(
                total_score=result["evaluation"]["total_score"],
                metrics=result["evaluation"]["metrics"],
                evaluation_id=result["evaluation"]["evaluation_id"]
            )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        request_logger.error(
            "Error adding conversation turn (legacy endpoint)",
            session_id=str(turn_data.session_id),
            role=turn_data.role.value,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/conversations",
    response_model=ConversationHistoryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_session_conversations_legacy(
    session_id: UUID = Query(..., description="Session ID to filter conversations"),
    pagination: PaginationParams = Depends(get_pagination_params),
    conversation_svc: ConversationService = Depends(get_conversation_service),
    session_svc = Depends(get_session_service),
    request_logger = Depends(get_request_logger)
):
    """
    Legacy endpoint for retrieving conversations by session ID.

    Keeps backward compatibility for `/api/v1/conversations?session_id=...`
    requests by delegating to the newer service interactions.
    """
    try:
        session = await session_svc.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        request_logger.debug(
            "Getting session conversations (legacy endpoint)",
            session_id=str(session_id),
            page=pagination.page,
            page_size=pagination.page_size
        )

        conversations = await conversation_svc.get_session_conversations(
            session_id=session_id,
            limit=pagination.limit,
            offset=pagination.offset
        )
        total_count = await conversation_svc.get_conversation_count(session_id)

        response_conversations = []
        for conv in conversations:
            conv_response = ConversationTurnResponse(
                conversation_id=conv["id"],
                turn_index=conv["turn_index"],
                role=ConversationRole(conv["role"]),
                text=conv["text"],
                created_at=conv.get("created_at")
            )

            if conv.get("evaluation"):
                from app.api.schemas import EvaluationResponse
                conv_response.evaluation = EvaluationResponse(
                    total_score=conv["evaluation"]["total_score"],
                    metrics=conv["evaluation"]["metrics"],
                    evaluation_id=conv["evaluation"]["id"]
                )

            response_conversations.append(conv_response)

        return ConversationHistoryResponse(
            conversations=response_conversations,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size
        )

    except HTTPException:
        raise
    except Exception as e:
        request_logger.error(
            "Error getting session conversations (legacy endpoint)",
            session_id=str(session_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/sessions/{session_id}/turns",
    response_model=ConversationTurnResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        400: {"model": ErrorResponse, "description": "Invalid turn data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def add_conversation_turn(
    turn_data: ConversationTurnRequest,
    session_id: UUID = Depends(validate_session_exists),
    conversation_svc: ConversationService = Depends(get_conversation_service),
    request_logger = Depends(get_request_logger)
):
    """
    Add a conversation turn to a session
    
    Adds a new conversation turn (user or assistant) to the specified session.
    
    For user turns:
    - The turn will be automatically scored based on the session's teaching mode
    - Evaluation metrics will be included in the response
    - Turn index will be incremented atomically
    
    For assistant turns:
    - No scoring is performed
    - Turn is logged for conversation history
    
    The turn index is managed automatically and incremented for each turn in the session.
    """
    try:
        request_logger.info("Adding conversation turn", 
                          session_id=session_id,
                          role=turn_data.role.value,
                          text_length=len(turn_data.text))
        
        # Add the turn
        result = await conversation_svc.add_turn(
            session_id=session_id,
            role=turn_data.role,
            text=turn_data.text
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add conversation turn"
            )
        
        request_logger.info("Conversation turn added successfully", 
                          session_id=session_id,
                          conversation_id=result["conversation_id"],
                          turn_index=result["turn_index"],
                          scored=bool(result.get("evaluation")))
        
        # Build response
        response_data = ConversationTurnResponse(
            conversation_id=result["conversation_id"],
            turn_index=result["turn_index"],
            role=ConversationRole(result["role"]),
            text=result["text"],
            created_at=result.get("created_at")
        )
        
        # Add evaluation data if present
        if result.get("evaluation"):
            from app.api.schemas import EvaluationResponse
            response_data.evaluation = EvaluationResponse(
                total_score=result["evaluation"]["total_score"],
                metrics=result["evaluation"]["metrics"],
                evaluation_id=result["evaluation"]["evaluation_id"]
            )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error adding conversation turn", 
                           session_id=session_id,
                           role=turn_data.role.value,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/sessions/{session_id}/turns",
    response_model=ConversationHistoryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_session_conversations(
    session_id: UUID = Depends(validate_session_exists),
    pagination: PaginationParams = Depends(get_pagination_params),
    conversation_svc: ConversationService = Depends(get_conversation_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get conversation history for a session
    
    Retrieves a paginated list of conversation turns for the specified session,
    ordered by turn index. Includes evaluation data for user turns when available.
    
    Use pagination parameters to control the number of turns returned and to
    navigate through long conversation histories.
    """
    try:
        request_logger.debug("Getting session conversations", 
                           session_id=session_id,
                           page=pagination.page,
                           page_size=pagination.page_size)
        
        # Get conversations
        conversations = await conversation_svc.get_session_conversations(
            session_id=session_id,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
        # Get total count
        total_count = await conversation_svc.get_conversation_count(session_id)
        
        # Convert to response format
        response_conversations = []
        for conv in conversations:
            conv_response = ConversationTurnResponse(
                conversation_id=conv["id"],
                turn_index=conv["turn_index"],
                role=ConversationRole(conv["role"]),
                text=conv["text"],
                created_at=conv.get("created_at")
            )
            
            # Add evaluation if present
            if conv.get("evaluation"):
                from app.api.schemas import EvaluationResponse
                conv_response.evaluation = EvaluationResponse(
                    total_score=conv["evaluation"]["total_score"],
                    metrics=conv["evaluation"]["metrics"],
                    evaluation_id=conv["evaluation"]["id"]
                )
            
            response_conversations.append(conv_response)
        
        return ConversationHistoryResponse(
            conversations=response_conversations,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting session conversations", 
                           session_id=session_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/conversations/search",
    response_model=ConversationHistoryResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid search parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def search_conversations(
    user_external_id: Optional[str] = Query(None, description="Filter by user external ID"),
    session_id: Optional[UUID] = Query(None, description="Filter by session ID"),
    text_search: Optional[str] = Query(None, min_length=2, description="Search in text content"),
    role_filter: Optional[ConversationRole] = Query(None, description="Filter by role"),
    pagination: PaginationParams = Depends(get_pagination_params),
    conversation_svc: ConversationService = Depends(get_conversation_service),
    request_logger = Depends(get_request_logger)
):
    """
    Search conversations with various filters
    
    Search through conversations using multiple criteria:
    - User external ID: Find conversations for a specific user
    - Session ID: Find conversations in a specific session
    - Text search: Search within conversation text content
    - Role filter: Filter by user or assistant turns
    
    All filters can be combined. Results are paginated and ordered by creation time (newest first).
    """
    try:
        request_logger.debug("Searching conversations", 
                           user_external_id=user_external_id,
                           session_id=session_id,
                           text_search=text_search,
                           role_filter=role_filter.value if role_filter else None)
        
        # Convert user_external_id to user_id if provided
        user_id = None
        if user_external_id:
            from app.services.session_service import session_service
            user = await session_service._get_user_by_external_id(user_external_id)
            if user:
                user_id = user.id
            else:
                # Return empty results if user not found
                return ConversationHistoryResponse(
                    conversations=[],
                    total_count=0,
                    page=pagination.page,
                    page_size=pagination.page_size
                )
        
        # Search conversations
        conversations = await conversation_svc.search_conversations(
            user_id=user_id,
            session_id=session_id,
            text_search=text_search,
            role_filter=role_filter,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
        # Convert to response format
        response_conversations = []
        for conv in conversations:
            conv_response = ConversationTurnResponse(
                conversation_id=conv["id"],
                turn_index=conv["turn_index"],
                role=ConversationRole(conv["role"]),
                text=conv["text"],
                created_at=conv.get("created_at")
            )
            response_conversations.append(conv_response)
        
        return ConversationHistoryResponse(
            conversations=response_conversations,
            total_count=len(response_conversations),  # Simplified; in production get actual total
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error searching conversations", 
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/users/{user_external_id}/conversations/recent",
    response_model=ConversationHistoryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_user_recent_conversations(
    user_external_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="Number of recent conversations"),
    conversation_svc: ConversationService = Depends(get_conversation_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get recent conversations for a user
    
    Retrieves the most recent conversation turns for a user across all their sessions.
    Useful for getting an overview of recent learning activity.
    
    Results are ordered by creation time (newest first) and include evaluation data
    where available.
    """
    try:
        request_logger.debug("Getting user recent conversations", 
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
        
        # Get recent conversations
        conversations = await conversation_svc.get_user_recent_conversations(
            user_id=user.id,
            limit=limit
        )
        
        # Convert to response format
        response_conversations = []
        for conv in conversations:
            conv_response = ConversationTurnResponse(
                conversation_id=conv["id"],
                turn_index=conv["turn_index"],
                role=ConversationRole(conv["role"]),
                text=conv["text"],
                created_at=conv.get("created_at")
            )
            
            # Add evaluation if present
            if conv.get("evaluation"):
                from app.api.schemas import EvaluationResponse
                conv_response.evaluation = EvaluationResponse(
                    total_score=conv["evaluation"]["total_score"],
                    metrics=conv["evaluation"]["metrics"],
                    evaluation_id=0  # Not provided in this query
                )
            
            response_conversations.append(conv_response)
        
        return ConversationHistoryResponse(
            conversations=response_conversations,
            total_count=len(response_conversations),
            page=1,
            page_size=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting user recent conversations", 
                           user_external_id=user_external_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete(
    "/sessions/{session_id}/conversations",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_session_conversations(
    session_id: UUID = Depends(validate_session_exists),
    conversation_svc: ConversationService = Depends(get_conversation_service),
    request_logger = Depends(get_request_logger)
):
    """
    Delete all conversations for a session
    
    Deletes all conversation turns and associated evaluations for the specified session.
    This is an administrative operation that cannot be undone.
    
    Use with caution as this will permanently remove all conversation data
    and scoring history for the session.
    """
    try:
        request_logger.warning("Deleting session conversations", session_id=session_id)
        
        success = await conversation_svc.delete_session_conversations(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete session conversations"
            )
        
        request_logger.info("Session conversations deleted successfully", session_id=session_id)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error deleting session conversations", 
                           session_id=session_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/sessions/{session_id}/statistics",
    response_model=dict,  # Would use SessionStatistics schema from schemas.py
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_session_statistics(
    session_id: UUID = Depends(validate_session_exists),
    conversation_svc: ConversationService = Depends(get_conversation_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get session conversation statistics
    
    Provides aggregate statistics for a session including:
    - Total number of turns
    - Average scores and trends
    - Strengths and areas for improvement
    - Score distribution
    
    Useful for generating session reports and tracking learning progress.
    """
    try:
        request_logger.debug("Getting session statistics", session_id=session_id)
        
        # Get statistics from scoring service
        from app.services.scoring_service import scoring_service
        stats = await scoring_service.calculate_session_statistics(session_id)
        
        # Add conversation count
        conversation_count = await conversation_svc.get_conversation_count(session_id)
        stats["total_conversations"] = conversation_count
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting session statistics", 
                           session_id=session_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/users/{user_external_id}/progress",
    response_model=dict,  # Would use UserProgressSummary schema
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_user_progress(
    user_external_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent evaluations to analyze"),
    conversation_svc: ConversationService = Depends(get_conversation_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get user progress summary
    
    Provides a summary of the user's learning progress based on recent evaluations:
    - Recent average score
    - Progress trend (improving, declining, stable)
    - Best and most recent scores
    - Total number of evaluations
    
    Useful for tracking learning progress over time and identifying trends.
    """
    try:
        request_logger.debug("Getting user progress", 
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
        
        # Get progress summary from scoring service
        from app.services.scoring_service import scoring_service
        progress = await scoring_service.get_user_progress_summary(user.id, limit)
        
        return progress
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error getting user progress", 
                           user_external_id=user_external_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
