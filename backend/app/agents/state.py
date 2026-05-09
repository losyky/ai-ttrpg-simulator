"""Shared state definition for the LangGraph workflow.

Uses Annotated reducers for list fields so that multiple nodes can
append to dice_results / interactive_elements without overwriting
each other.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def _replace(existing: str, new: str) -> str:
    """Reducer that keeps the latest non-empty value."""
    return new if new else existing


class AgentState(TypedDict, total=False):
    """The shared state flowing through the LangGraph nodes."""

    # Core fields
    session_id: str
    user_message: str

    # LLM config (passed per-request)
    api_key: str
    model: str
    base_url: str

    # Game phase routing
    game_phase: str  # exploration | combat | social | downtime

    # Character context (built from session + character store)
    player_context: str

    # Outputs from sub-agents — latest value wins
    referee_output: str
    teammate_output: str
    notetaker_output: str

    # Whether certain agents should be invoked this turn
    needs_referee: bool
    needs_teammates: bool

    # List fields with append-reducers: multiple nodes can add items
    dice_results: Annotated[list[dict[str, Any]], operator.add]
    interactive_elements: Annotated[list[dict[str, Any]], operator.add]

    # Human-in-the-loop: pending dice request for interrupt()
    pending_dice_request: dict[str, Any] | None

    # Final streamed output for the user
    narrator_response: str
