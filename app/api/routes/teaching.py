"""
API routes for teaching metadata management (modes, scenarios, languages)
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from app.api.schemas import (
    TeachingModeCreate, TeachingModeUpdate, TeachingModeResponse, TeachingModesListResponse,
    ScenarioCreate, ScenarioUpdate, ScenarioResponse, ScenariosListResponse,
    LanguageCreate, LanguageUpdate, LanguageResponse, LanguagesListResponse,
    ErrorResponse
)
from app.api.deps import get_teaching_service, get_request_logger
from app.services.teaching_service import TeachingService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["teaching"])


# Teaching Modes Endpoints

@router.post(
    "/teaching-modes",
    response_model=TeachingModeResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        409: {"model": ErrorResponse, "description": "Mode code already exists"}
    }
)
async def create_teaching_mode(
    mode_data: TeachingModeCreate,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Create a new teaching mode
    
    Creates a teaching mode with the specified code, name, description, and scoring rubric.
    The code must be unique across all teaching modes.
    """
    try:
        request_logger.info("Creating teaching mode", code=mode_data.code, name=mode_data.name)
        
        # Check if mode already exists
        existing_mode = await teaching_svc.get_mode_by_code(mode_data.code)
        if existing_mode:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Teaching mode with code '{mode_data.code}' already exists"
            )
        
        # Create the mode
        mode = await teaching_svc.create_teaching_mode(
            code=mode_data.code,
            name=mode_data.name,
            description=mode_data.description,
            rubric=mode_data.rubric
        )
        
        if not mode:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create teaching mode"
            )
        
        request_logger.info("Teaching mode created successfully", 
                          mode_id=mode.id, 
                          code=mode.code)
        
        return TeachingModeResponse.from_orm(mode)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error creating teaching mode", 
                           code=mode_data.code,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/teaching-modes",
    response_model=TeachingModesListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_teaching_modes(
    code: Optional[str] = Query(None, description="Filter by mode code"),
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get all teaching modes or filter by code
    
    Returns a list of all available teaching modes. Optionally filter by a specific code.
    """
    try:
        request_logger.debug("Getting teaching modes", code_filter=code)
        
        modes = await teaching_svc.get_teaching_modes(code_filter=code)
        
        response_modes = [TeachingModeResponse.from_orm(mode) for mode in modes]
        
        return TeachingModesListResponse(
            teaching_modes=response_modes,
            total_count=len(response_modes)
        )
        
    except Exception as e:
        request_logger.error("Error getting teaching modes", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put(
    "/teaching-modes/{mode_code}",
    response_model=TeachingModeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Mode not found"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_teaching_mode(
    mode_code: str,
    update_data: TeachingModeUpdate,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Update a teaching mode
    
    Updates the specified fields of an existing teaching mode.
    Only provided fields will be updated.
    """
    try:
        request_logger.info("Updating teaching mode", code=mode_code)
        
        # Check if mode exists
        existing_mode = await teaching_svc.get_mode_by_code(mode_code)
        if not existing_mode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Teaching mode '{mode_code}' not found"
            )
        
        # Update the mode
        updated_mode = await teaching_svc.update_teaching_mode(
            code=mode_code,
            name=update_data.name,
            description=update_data.description,
            rubric=update_data.rubric
        )
        
        if not updated_mode:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update teaching mode"
            )
        
        request_logger.info("Teaching mode updated successfully", code=mode_code)
        
        return TeachingModeResponse.from_orm(updated_mode)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error updating teaching mode", 
                           code=mode_code,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete(
    "/teaching-modes/{mode_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Mode not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_teaching_mode(
    mode_code: str,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Delete a teaching mode
    
    Deletes the specified teaching mode and all associated scenarios.
    This operation cannot be undone.
    """
    try:
        request_logger.info("Deleting teaching mode", code=mode_code)
        
        # Check if mode exists
        existing_mode = await teaching_svc.get_mode_by_code(mode_code)
        if not existing_mode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Teaching mode '{mode_code}' not found"
            )
        
        # Delete the mode
        success = await teaching_svc.delete_teaching_mode(mode_code)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete teaching mode"
            )
        
        request_logger.info("Teaching mode deleted successfully", code=mode_code)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error deleting teaching mode", 
                           code=mode_code,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Scenarios Endpoints

@router.post(
    "/scenarios",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        409: {"model": ErrorResponse, "description": "Scenario already exists"}
    }
)
async def create_scenario(
    scenario_data: ScenarioCreate,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Create a new scenario
    
    Creates a scenario for a specific teaching mode and language.
    The combination of mode_code, title, and language_code must be unique.
    """
    try:
        request_logger.info("Creating scenario", 
                          title=scenario_data.title,
                          mode_code=scenario_data.mode_code,
                          language_code=scenario_data.language_code)
        
        # Validate mode exists
        mode = await teaching_svc.get_mode_by_code(scenario_data.mode_code)
        if not mode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Teaching mode '{scenario_data.mode_code}' not found"
            )
        
        # Validate language exists
        language = await teaching_svc.get_language_by_code(scenario_data.language_code)
        if not language:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language '{scenario_data.language_code}' not supported"
            )
        
        # Create the scenario
        scenario = await teaching_svc.create_scenario(
            mode_code=scenario_data.mode_code,
            title=scenario_data.title,
            prompt=scenario_data.prompt,
            language_code=scenario_data.language_code,
            metadata=scenario_data.metadata
        )
        
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create scenario"
            )
        
        request_logger.info("Scenario created successfully", 
                          scenario_id=scenario.id,
                          title=scenario.title)
        
        return ScenarioResponse.from_orm(scenario)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error creating scenario", 
                           title=scenario_data.title,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/scenarios",
    response_model=ScenariosListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_scenarios(
    mode_code: Optional[str] = Query(None, description="Filter by teaching mode"),
    language_code: Optional[str] = Query(None, description="Filter by language"),
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get scenarios with optional filters
    
    Returns a list of scenarios. Can be filtered by teaching mode and/or language code.
    """
    try:
        request_logger.debug("Getting scenarios", 
                           mode_code=mode_code,
                           language_code=language_code)
        
        scenarios = await teaching_svc.get_scenarios(
            mode_code=mode_code,
            language_code=language_code
        )
        
        response_scenarios = [ScenarioResponse.from_orm(scenario) for scenario in scenarios]
        
        return ScenariosListResponse(
            scenarios=response_scenarios,
            total_count=len(response_scenarios)
        )
        
    except Exception as e:
        request_logger.error("Error getting scenarios", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put(
    "/scenarios/{scenario_id}",
    response_model=ScenarioResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Scenario not found"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_scenario(
    scenario_id: UUID,
    update_data: ScenarioUpdate,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Update a scenario
    
    Updates the specified fields of an existing scenario.
    Only provided fields will be updated.
    """
    try:
        request_logger.info("Updating scenario", scenario_id=scenario_id)
        
        # Update the scenario
        updated_scenario = await teaching_svc.update_scenario(
            scenario_id=scenario_id,
            title=update_data.title,
            prompt=update_data.prompt,
            metadata=update_data.metadata
        )
        
        if not updated_scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario {scenario_id} not found"
            )
        
        request_logger.info("Scenario updated successfully", scenario_id=scenario_id)
        
        return ScenarioResponse.from_orm(updated_scenario)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error updating scenario", 
                           scenario_id=scenario_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete(
    "/scenarios/{scenario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Scenario not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_scenario(
    scenario_id: UUID,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Delete a scenario
    
    Deletes the specified scenario. This operation cannot be undone.
    """
    try:
        request_logger.info("Deleting scenario", scenario_id=scenario_id)
        
        # Delete the scenario
        success = await teaching_svc.delete_scenario(scenario_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario {scenario_id} not found"
            )
        
        request_logger.info("Scenario deleted successfully", scenario_id=scenario_id)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error deleting scenario", 
                           scenario_id=scenario_id,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Languages Endpoints

@router.post(
    "/languages",
    response_model=LanguageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        409: {"model": ErrorResponse, "description": "Language code already exists"}
    }
)
async def create_language(
    language_data: LanguageCreate,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Create a new supported language
    
    Creates a supported language with the specified code and label.
    The language code must be unique.
    """
    try:
        request_logger.info("Creating language", 
                          code=language_data.code,
                          label=language_data.label)
        
        # Check if language already exists
        existing_language = await teaching_svc.get_language_by_code(language_data.code)
        if existing_language:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Language with code '{language_data.code}' already exists"
            )
        
        # Create the language
        language = await teaching_svc.create_language(
            code=language_data.code,
            label=language_data.label,
            level_cefr=language_data.level_cefr
        )
        
        if not language:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create language"
            )
        
        request_logger.info("Language created successfully", 
                          code=language.code,
                          label=language.label)
        
        return LanguageResponse.from_orm(language)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error creating language", 
                           code=language_data.code,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/languages",
    response_model=LanguagesListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_languages(
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Get all supported languages
    
    Returns a list of all supported languages ordered by label.
    """
    try:
        request_logger.debug("Getting supported languages")
        
        languages = await teaching_svc.get_languages()
        
        response_languages = [LanguageResponse.from_orm(language) for language in languages]
        
        return LanguagesListResponse(
            languages=response_languages,
            total_count=len(response_languages)
        )
        
    except Exception as e:
        request_logger.error("Error getting languages", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put(
    "/languages/{language_code}",
    response_model=LanguageResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Language not found"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_language(
    language_code: str,
    update_data: LanguageUpdate,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Update a supported language
    
    Updates the specified fields of an existing language.
    Only provided fields will be updated.
    """
    try:
        request_logger.info("Updating language", code=language_code)
        
        # Check if language exists
        existing_language = await teaching_svc.get_language_by_code(language_code)
        if not existing_language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Language '{language_code}' not found"
            )
        
        # Update the language
        updated_language = await teaching_svc.update_language(
            code=language_code,
            label=update_data.label,
            level_cefr=update_data.level_cefr
        )
        
        if not updated_language:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update language"
            )
        
        request_logger.info("Language updated successfully", code=language_code)
        
        return LanguageResponse.from_orm(updated_language)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error updating language", 
                           code=language_code,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete(
    "/languages/{language_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Language not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_language(
    language_code: str,
    teaching_svc: TeachingService = Depends(get_teaching_service),
    request_logger = Depends(get_request_logger)
):
    """
    Delete a supported language
    
    Deletes the specified language. This operation cannot be undone.
    Note: This will also affect any sessions or scenarios using this language.
    """
    try:
        request_logger.info("Deleting language", code=language_code)
        
        # Check if language exists
        existing_language = await teaching_svc.get_language_by_code(language_code)
        if not existing_language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Language '{language_code}' not found"
            )
        
        # Delete the language
        success = await teaching_svc.delete_language(language_code)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete language"
            )
        
        request_logger.info("Language deleted successfully", code=language_code)
        
    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Error deleting language", 
                           code=language_code,
                           error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )