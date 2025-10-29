"""
Teaching service for managing teaching modes, scenarios, and supported languages
"""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import structlog

from app.domain.models import TeachingMode, DefaultScenario, SupportedLanguage
from app.services.supabase_client import get_supabase_client

logger = structlog.get_logger(__name__)


class TeachingService:
    """Service for managing teaching metadata (modes, scenarios, languages)"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    # Teaching Modes CRUD
    
    async def create_teaching_mode(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        rubric: Optional[Dict[str, Any]] = None
    ) -> Optional[TeachingMode]:
        """
        Create a new teaching mode
        
        Args:
            code: Unique code for the mode
            name: Display name
            description: Optional description
            rubric: Optional scoring rubric
            
        Returns:
            TeachingMode object if successful, None otherwise
        """
        try:
            mode_data = {
                "code": code,
                "name": name,
                "description": description,
                "rubric": rubric or {}
            }
            
            response = self.supabase.table("teaching_modes").insert(mode_data).execute()
            
            if response.data:
                record = response.data[0]
                logger.info("Teaching mode created", code=code, name=name)
                
                return TeachingMode(
                    id=UUID(record["id"]),
                    code=record["code"],
                    name=record["name"],
                    description=record.get("description"),
                    rubric=record.get("rubric", {}),
                    created_at=record.get("created_at")
                )
            
            return None
            
        except Exception as e:
            logger.error("Error creating teaching mode", 
                        code=code,
                        error=str(e))
            return None
    
    async def get_teaching_modes(self, code_filter: Optional[str] = None) -> List[TeachingMode]:
        """
        Get all teaching modes or filter by code
        
        Args:
            code_filter: Optional code to filter by
            
        Returns:
            List of TeachingMode objects
        """
        try:
            query = self.supabase.table("teaching_modes").select("*")
            
            if code_filter:
                query = query.eq("code", code_filter)
            
            response = query.order("created_at").execute()
            
            modes = []
            for record in response.data:
                mode = TeachingMode(
                    id=UUID(record["id"]),
                    code=record["code"],
                    name=record["name"],
                    description=record.get("description"),
                    rubric=record.get("rubric", {}),
                    created_at=record.get("created_at")
                )
                modes.append(mode)
            
            logger.debug("Retrieved teaching modes", count=len(modes))
            return modes
            
        except Exception as e:
            logger.error("Error getting teaching modes", error=str(e))
            return []
    
    async def update_teaching_mode(
        self,
        code: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rubric: Optional[Dict[str, Any]] = None
    ) -> Optional[TeachingMode]:
        """
        Update a teaching mode
        
        Args:
            code: Mode code to update
            name: New name (optional)
            description: New description (optional)
            rubric: New rubric (optional)
            
        Returns:
            Updated TeachingMode object if successful, None otherwise
        """
        try:
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if rubric is not None:
                update_data["rubric"] = rubric
            
            if not update_data:
                logger.warning("No update data provided", code=code)
                return None
            
            response = self.supabase.table("teaching_modes")\
                .update(update_data)\
                .eq("code", code)\
                .execute()
            
            if response.data:
                record = response.data[0]
                logger.info("Teaching mode updated", code=code)
                
                return TeachingMode(
                    id=UUID(record["id"]),
                    code=record["code"],
                    name=record["name"],
                    description=record.get("description"),
                    rubric=record.get("rubric", {}),
                    created_at=record.get("created_at")
                )
            
            return None
            
        except Exception as e:
            logger.error("Error updating teaching mode", 
                        code=code,
                        error=str(e))
            return None
    
    async def delete_teaching_mode(self, code: str) -> bool:
        """
        Delete a teaching mode (this will cascade to scenarios)
        
        Args:
            code: Mode code to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.supabase.table("teaching_modes")\
                .delete()\
                .eq("code", code)\
                .execute()
            
            if response.data:
                logger.info("Teaching mode deleted", code=code)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error deleting teaching mode", 
                        code=code,
                        error=str(e))
            return False
    
    # Default Scenarios CRUD
    
    async def create_scenario(
        self,
        mode_code: str,
        title: str,
        prompt: str,
        language_code: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[DefaultScenario]:
        """
        Create a new default scenario
        
        Args:
            mode_code: Teaching mode code
            title: Scenario title
            prompt: Scenario prompt text
            language_code: Target language
            metadata: Optional metadata
            
        Returns:
            DefaultScenario object if successful, None otherwise
        """
        try:
            scenario_data = {
                "mode_code": mode_code,
                "title": title,
                "prompt": prompt,
                "language_code": language_code,
                "metadata": metadata or {}
            }
            
            response = self.supabase.table("default_scenarios").insert(scenario_data).execute()
            
            if response.data:
                record = response.data[0]
                logger.info("Scenario created", 
                          title=title,
                          mode_code=mode_code,
                          language_code=language_code)
                
                return DefaultScenario(
                    id=UUID(record["id"]),
                    mode_code=record["mode_code"],
                    title=record["title"],
                    prompt=record["prompt"],
                    language_code=record["language_code"],
                    metadata=record.get("metadata", {}),
                    created_at=record.get("created_at")
                )
            
            return None
            
        except Exception as e:
            logger.error("Error creating scenario", 
                        title=title,
                        mode_code=mode_code,
                        error=str(e))
            return None
    
    async def get_scenarios(
        self,
        mode_code: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> List[DefaultScenario]:
        """
        Get scenarios with optional filters
        
        Args:
            mode_code: Filter by teaching mode
            language_code: Filter by language
            
        Returns:
            List of DefaultScenario objects
        """
        try:
            query = self.supabase.table("default_scenarios").select("*")
            
            if mode_code:
                query = query.eq("mode_code", mode_code)
            
            if language_code:
                query = query.eq("language_code", language_code)
            
            response = query.order("created_at").execute()
            
            scenarios = []
            for record in response.data:
                scenario = DefaultScenario(
                    id=UUID(record["id"]),
                    mode_code=record["mode_code"],
                    title=record["title"],
                    prompt=record["prompt"],
                    language_code=record["language_code"],
                    metadata=record.get("metadata", {}),
                    created_at=record.get("created_at")
                )
                scenarios.append(scenario)
            
            logger.debug("Retrieved scenarios", 
                        count=len(scenarios),
                        mode_code=mode_code,
                        language_code=language_code)
            return scenarios
            
        except Exception as e:
            logger.error("Error getting scenarios", 
                        mode_code=mode_code,
                        language_code=language_code,
                        error=str(e))
            return []
    
    async def update_scenario(
        self,
        scenario_id: UUID,
        title: Optional[str] = None,
        prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[DefaultScenario]:
        """
        Update a scenario
        
        Args:
            scenario_id: Scenario ID to update
            title: New title (optional)
            prompt: New prompt (optional)
            metadata: New metadata (optional)
            
        Returns:
            Updated DefaultScenario object if successful, None otherwise
        """
        try:
            update_data = {}
            if title is not None:
                update_data["title"] = title
            if prompt is not None:
                update_data["prompt"] = prompt
            if metadata is not None:
                update_data["metadata"] = metadata
            
            if not update_data:
                logger.warning("No update data provided", scenario_id=scenario_id)
                return None
            
            response = self.supabase.table("default_scenarios")\
                .update(update_data)\
                .eq("id", str(scenario_id))\
                .execute()
            
            if response.data:
                record = response.data[0]
                logger.info("Scenario updated", scenario_id=scenario_id)
                
                return DefaultScenario(
                    id=UUID(record["id"]),
                    mode_code=record["mode_code"],
                    title=record["title"],
                    prompt=record["prompt"],
                    language_code=record["language_code"],
                    metadata=record.get("metadata", {}),
                    created_at=record.get("created_at")
                )
            
            return None
            
        except Exception as e:
            logger.error("Error updating scenario", 
                        scenario_id=scenario_id,
                        error=str(e))
            return None
    
    async def delete_scenario(self, scenario_id: UUID) -> bool:
        """
        Delete a scenario
        
        Args:
            scenario_id: Scenario ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.supabase.table("default_scenarios")\
                .delete()\
                .eq("id", str(scenario_id))\
                .execute()
            
            if response.data:
                logger.info("Scenario deleted", scenario_id=scenario_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error deleting scenario", 
                        scenario_id=scenario_id,
                        error=str(e))
            return False
    
    # Supported Languages CRUD
    
    async def create_language(
        self,
        code: str,
        label: str,
        level_cefr: Optional[str] = None
    ) -> Optional[SupportedLanguage]:
        """
        Create a new supported language
        
        Args:
            code: Language code (e.g., "en-US", "es-ES")
            label: Display label
            level_cefr: Optional CEFR level
            
        Returns:
            SupportedLanguage object if successful, None otherwise
        """
        try:
            language_data = {
                "code": code,
                "label": label,
                "level_cefr": level_cefr
            }
            
            response = self.supabase.table("supported_languages").insert(language_data).execute()
            
            if response.data:
                record = response.data[0]
                logger.info("Language created", code=code, label=label)
                
                return SupportedLanguage(
                    code=record["code"],
                    label=record["label"],
                    level_cefr=record.get("level_cefr"),
                    created_at=record.get("created_at")
                )
            
            return None
            
        except Exception as e:
            logger.error("Error creating language", 
                        code=code,
                        error=str(e))
            return None
    
    async def get_languages(self) -> List[SupportedLanguage]:
        """
        Get all supported languages
        
        Returns:
            List of SupportedLanguage objects
        """
        try:
            response = self.supabase.table("supported_languages")\
                .select("*")\
                .order("label")\
                .execute()
            
            languages = []
            for record in response.data:
                language = SupportedLanguage(
                    code=record["code"],
                    label=record["label"],
                    level_cefr=record.get("level_cefr"),
                    created_at=record.get("created_at")
                )
                languages.append(language)
            
            logger.debug("Retrieved supported languages", count=len(languages))
            return languages
            
        except Exception as e:
            logger.error("Error getting supported languages", error=str(e))
            return []
    
    async def update_language(
        self,
        code: str,
        label: Optional[str] = None,
        level_cefr: Optional[str] = None
    ) -> Optional[SupportedLanguage]:
        """
        Update a supported language
        
        Args:
            code: Language code to update
            label: New label (optional)
            level_cefr: New CEFR level (optional)
            
        Returns:
            Updated SupportedLanguage object if successful, None otherwise
        """
        try:
            update_data = {}
            if label is not None:
                update_data["label"] = label
            if level_cefr is not None:
                update_data["level_cefr"] = level_cefr
            
            if not update_data:
                logger.warning("No update data provided", code=code)
                return None
            
            response = self.supabase.table("supported_languages")\
                .update(update_data)\
                .eq("code", code)\
                .execute()
            
            if response.data:
                record = response.data[0]
                logger.info("Language updated", code=code)
                
                return SupportedLanguage(
                    code=record["code"],
                    label=record["label"],
                    level_cefr=record.get("level_cefr"),
                    created_at=record.get("created_at")
                )
            
            return None
            
        except Exception as e:
            logger.error("Error updating language", 
                        code=code,
                        error=str(e))
            return None
    
    async def delete_language(self, code: str) -> bool:
        """
        Delete a supported language
        
        Args:
            code: Language code to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.supabase.table("supported_languages")\
                .delete()\
                .eq("code", code)\
                .execute()
            
            if response.data:
                logger.info("Language deleted", code=code)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error deleting language", 
                        code=code,
                        error=str(e))
            return False
    
    # Utility methods
    
    async def get_mode_by_code(self, code: str) -> Optional[TeachingMode]:
        """
        Get a specific teaching mode by code
        
        Args:
            code: Mode code
            
        Returns:
            TeachingMode object if found, None otherwise
        """
        modes = await self.get_teaching_modes(code_filter=code)
        return modes[0] if modes else None
    
    async def get_language_by_code(self, code: str) -> Optional[SupportedLanguage]:
        """
        Get a specific language by code
        
        Args:
            code: Language code
            
        Returns:
            SupportedLanguage object if found, None otherwise
        """
        try:
            response = self.supabase.table("supported_languages")\
                .select("*")\
                .eq("code", code)\
                .limit(1)\
                .execute()
            
            if response.data:
                record = response.data[0]
                return SupportedLanguage(
                    code=record["code"],
                    label=record["label"],
                    level_cefr=record.get("level_cefr"),
                    created_at=record.get("created_at")
                )
            
            return None
            
        except Exception as e:
            logger.error("Error getting language by code", 
                        code=code,
                        error=str(e))
            return None


# Global teaching service instance
teaching_service = TeachingService()