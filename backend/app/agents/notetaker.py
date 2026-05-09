"""Notetaker agent – maintains world state summary and long-term memory."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from .compat import SafeChatOpenAI as ChatOpenAI

from app.agents.state import AgentState
from app.agents.prompts import NOTETAKER_SYSTEM
from app.models.game_state import get_session, update_session
from app.services.event_log import log_event
from app.services.memory_store import (
    extract_and_store_memories,
    get_memory_context,
)


async def update_notes(state: AgentState) -> dict[str, Any]:
    """Summarize the current turn, update world state, and extract long-term memories."""
    session = get_session(state["session_id"])
    prev_summary = session.world_summary if session else ""

    llm = ChatOpenAI(
        model=state["model"],
        api_key=state["api_key"],
        base_url=state["base_url"],
        temperature=0.1,
    )

    # Include long-term memory context for better continuity
    memory_ctx = get_memory_context(state["session_id"], max_chars=600)

    turn_info = (
        f"本轮玩家行动: {state['user_message']}\n"
        f"规则判定结果: {state.get('referee_output', '')}\n"
        f"队友行动: {state.get('teammate_output', '')}\n"
        f"讲述者叙事: {state.get('narrator_response', '')}\n"
    )

    context = f"之前的世界状态:\n{prev_summary}\n\n"
    if memory_ctx:
        context += f"{memory_ctx}\n\n"
    context += turn_info

    response = await llm.ainvoke([
        SystemMessage(content=NOTETAKER_SYSTEM),
        HumanMessage(content=f"请更新世界状态摘要:\n\n{context}"),
    ])

    summary = str(response.content)

    if session:
        event_line = state["user_message"][:100]
        recent = session.recent_events[-9:] + [event_line]
        update_session(
            state["session_id"],
            world_summary=summary,
            recent_events=recent,
        )

    # Extract and store long-term memories from this turn
    try:
        new_count = await extract_and_store_memories(
            state["session_id"],
            turn_info,
            {
                "model": state["model"],
                "api_key": state["api_key"],
                "base_url": state["base_url"],
            },
        )
        if new_count > 0:
            log_event("agent", "memories_extracted", session_id=state["session_id"],
                      agent="notetaker", detail=f"Extracted {new_count} new memories")
    except Exception as e:
        log_event("error", "memory_extraction_error", session_id=state["session_id"],
                  detail=str(e)[:200])

    log_event("agent", "notetaker_done", session_id=state["session_id"],
              agent="notetaker", detail=summary[:200])
    return {"notetaker_output": summary}
