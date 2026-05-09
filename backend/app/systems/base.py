"""Abstract base class for pluggable game systems."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter


class CharacterSheet:
    """Base character sheet representation."""
    def __init__(self, data: dict[str, Any]):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.level: int = data.get("level", 1)
        self.raw: dict[str, Any] = data


class GameSystem(ABC):
    """Abstract base class for a TTRPG rule system module.
    
    Each game system (PF2e, SWADE, etc.) implements this interface
    to provide system-specific rules, tools, prompts, and character handling.
    """

    system_id: str = ""
    display_name: str = ""
    has_turn_based_combat: bool = True
    
    @abstractmethod
    def get_prompts(self) -> dict[str, str]:
        """Return system prompt templates keyed by agent role.
        
        Expected keys: narrator, referee, teammate, combat, notetaker, prep
        """

    @abstractmethod
    def get_tools(self) -> dict[str, list]:
        """Return LangChain tools keyed by agent role.
        
        Expected keys: narrator, referee, prep, combat
        Each value is a list of LangChain tool objects.
        """

    @abstractmethod
    def get_builtin_tool_metadata(self) -> list[dict[str, Any]]:
        """Return metadata for system-specific built-in tools (for tool registry UI)."""

    @abstractmethod
    def determine_success(self, total: int, dc: int, natural: int = 0) -> str:
        """Determine success level from a dice roll result.
        
        Returns: empty string, or system-specific level like 'critical_success'.
        """

    @abstractmethod
    def parse_character(self, raw_json: dict) -> CharacterSheet:
        """Parse a raw character JSON (e.g. FVTT export) into a CharacterSheet."""

    @abstractmethod
    def character_to_summary(self, sheet: Any) -> dict[str, Any]:
        """Convert a character sheet to a summary dict for agent context."""

    @abstractmethod
    def render_markup(self, html: str) -> str:
        """Parse and render system-specific inline markup (e.g. @UUID, @Check)."""

    @abstractmethod
    def get_charbuilder_router(self) -> "APIRouter | None":
        """Return a FastAPI router for character builder API endpoints, or None."""

    @abstractmethod
    def get_rules_router(self) -> "APIRouter | None":
        """Return a FastAPI router for rules lookup API endpoints, or None."""

    @abstractmethod
    def get_skill_list(self) -> list[dict[str, str]]:
        """Return the list of skills: [{slug, name, name_cn, attribute}]."""

    @abstractmethod
    def get_ability_list(self) -> list[str]:
        """Return ability score abbreviations, e.g. ['str','dex','con','int','wis','cha']."""

    def get_npc_builder_tools(self) -> list:
        """Return LangChain tools for NPC/monster creation. Default: empty."""
        return []

    def get_collection_name(self) -> str:
        """Return the vector store collection name for this system."""
        return f"{self.system_id}_rules"
