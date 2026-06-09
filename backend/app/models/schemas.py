"""Pydantic schemas shared across the API."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --------------- LLM configuration ---------------

class LLMConfig(BaseModel):
    api_key: str
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"


# --------------- Game session ---------------

class GamePhase(str, Enum):
    EXPLORATION = "exploration"
    COMBAT = "combat"
    SOCIAL = "social"
    DOWNTIME = "downtime"


class CharacterSummary(BaseModel):
    name: str
    ancestry: str = ""
    character_class: str = ""
    level: int = 1
    hp: int = 0
    max_hp: int = 0
    conditions: list[str] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    llm_config: LLMConfig
    module_id: str | None = None
    system_id: str | None = None
    player_character: CharacterSummary | None = None
    teammate_ids: list[str] = Field(default_factory=list)
    label: str = ""


class SessionState(BaseModel):
    session_id: str
    system_id: str = "pf2e"
    label: str = ""
    created_at: str = ""
    phase: GamePhase = GamePhase.EXPLORATION
    round_number: int = 0
    player: CharacterSummary | None = None
    teammates: list[CharacterSummary] = Field(default_factory=list)
    world_summary: str = ""
    recent_events: list[str] = Field(default_factory=list)
    enabled_doc_ids: list[str] | None = None
    story_points: int = 3
    max_story_points: int = 3


# --------------- Chat ---------------

class ChatMessage(BaseModel):
    role: str  # "user" | "narrator" | "referee" | "teammate" | "system"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list)


class ImageGenConfig(BaseModel):
    api_key: str = ""
    model: str = "nano-banana-2"
    base_url: str = "https://grsaiapi.com/v1/api/generate"
    style_prefix: str = ""
    turns_per_image: int = 5


class ChatRequest(BaseModel):
    session_id: str
    message: str
    llm_config: LLMConfig
    image_gen_config: ImageGenConfig | None = None


class DiceResult(BaseModel):
    expression: str
    rolls: list[int]
    total: int
    detail: str
    success_level: str = ""  # "critical_success" | "success" | "failure" | "critical_failure"
    dc: int = 0
    label: str = ""  # e.g. "感知检定", "攻击检定"
    # Daggerheart duality dice
    duality_outcome: str = ""  # "with_hope" | "with_fear" | "critical_success"
    hope_die: int = 0
    fear_die: int = 0
    # SWADE raises
    raises: int = 0
    # Reroll via story/hero points
    is_reroll: bool = False
    original_total: int | None = None
    # Flexible system-specific extras
    system_info: dict[str, Any] = Field(default_factory=dict)


# --------------- Interactive elements ---------------

class ChoiceOption(BaseModel):
    id: str
    label: str
    description: str = ""
    icon: str = ""  # emoji or icon name


class InteractiveElement(BaseModel):
    """An interactive UI element the narrator sends to the player."""
    element_type: str  # "choices" | "dice_request" | "input_prompt" | "duality_dice_request" | "token_update" | "image_confirm"
    id: str
    prompt: str = ""

    # For choices
    options: list[ChoiceOption] = Field(default_factory=list)
    allow_multiple: bool = False

    # For dice_request / duality_dice_request
    expression: str = ""
    dc: int = 0
    skill_name: str = ""
    modifier: int = 0

    # For duality_dice_request (Daggerheart)
    trait_name: str = ""  # e.g. "Agility", "Presence"
    experience_bonus: bool = False  # +2 from Experience

    # For token_update (Daggerheart Hope/Fear economy)
    token_type: str = ""  # "hope" | "fear"
    token_change: int = 0  # +1 / -1 / -2 etc.
    token_total: int = 0
    token_reason: str = ""

    # For input_prompt
    placeholder: str = ""
    input_type: str = "text"  # "text" | "number" | "name"


# --------------- SSE chunks ---------------

class ChatResponseChunk(BaseModel):
    """A single SSE chunk sent to the frontend."""
    type: str  # "text" | "dice" | "interactive" | "state_update" | "interrupt" | "error" | "done" | "thinking" | "image"
    content: str = ""
    dice: DiceResult | None = None
    state: SessionState | None = None
    interactive: InteractiveElement | None = None
    interrupt_data: dict[str, Any] | None = None
    thinking_step: str = ""  # current processing step label
    image_url: str | None = None  # for type="image"


# --------------- Player dice roll ---------------

class PlayerDiceRequest(BaseModel):
    session_id: str
    expression: str
    dc: int = 0
    label: str = ""
    modifier: int = 0


# --------------- Document upload ---------------

class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    doc_type: str  # "fvtt_json" | "markdown" | "pdf"
    chunk_count: int = 0
