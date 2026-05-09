"""Dice interrupt node — uses LangGraph interrupt() to pause execution
and wait for the player to roll dice on the frontend.

When the referee determines a check is needed, it sets `pending_dice`
in the state. This node sees the pending request, interrupts the graph,
and waits for the frontend to resume with the roll result via Command.
"""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from app.agents.state import AgentState
from app.services.event_log import log_event


async def dice_interrupt_node(state: AgentState) -> dict[str, Any]:
    """If the referee output contains a pending dice check marker,
    pause the graph and wait for the player's roll.

    The interrupt payload tells the frontend what dice to show.
    The resume value should contain the actual roll result.
    """
    pending = state.get("pending_dice_request")
    if not pending:
        return {}

    log_event("interactive", "dice_interrupt",
              session_id=state["session_id"],
              detail=f"Waiting for player dice: {pending}")

    # interrupt() pauses here — the frontend receives the interrupt payload
    # and resumes the graph with Command(resume={roll result})
    roll_result = interrupt(pending)

    log_event("interactive", "dice_resumed",
              session_id=state["session_id"],
              detail=f"Player rolled: {roll_result}")

    dice_results = []
    if isinstance(roll_result, dict):
        dice_results.append(roll_result)

    return {
        "dice_results": dice_results,
        "pending_dice_request": None,
    }
