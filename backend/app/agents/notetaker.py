"""Notetaker agent – maintains world state summary and long-term memory.

Runs as a **background task** after the narrator finishes, so the SSE
response closes immediately once the narration is streamed.  The two
LLM calls (summary update + memory extraction) execute in parallel
via ``asyncio.gather``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from .compat import SafeChatOpenAI as ChatOpenAI

from app.agents.prompts import NOTETAKER_SYSTEM
from app.models.game_state import get_session, update_session
from app.services.event_log import log_event
from app.services.memory_store import (
    extract_and_store_memories,
    get_memory_context,
)

log = logging.getLogger(__name__)

# Track running background tasks so they aren't garbage-collected
_background_tasks: set[asyncio.Task] = set()


def _build_turn_info(
    user_message: str,
    referee_output: str,
    teammate_output: str,
    narrator_response: str,
) -> str:
    return (
        f"本轮玩家行动: {user_message}\n"
        f"规则判定结果: {referee_output}\n"
        f"队友行动: {teammate_output}\n"
        f"讲述者叙事: {narrator_response}\n"
    )


async def _update_summary(
    session_id: str,
    llm: ChatOpenAI,
    prev_summary: str,
    memory_ctx: str,
    turn_info: str,
) -> str:
    """LLM call 1: generate an updated world-state summary."""
    context = f"之前的世界状态:\n{prev_summary}\n\n"
    if memory_ctx:
        context += f"{memory_ctx}\n\n"
    context += turn_info

    response = await llm.ainvoke([
        SystemMessage(content=NOTETAKER_SYSTEM),
        HumanMessage(content=f"请更新世界状态摘要:\n\n{context}"),
    ])
    return str(response.content)


async def _extract_memories(
    session_id: str,
    turn_info: str,
    llm_config: dict[str, str],
    memory_ctx: str,
) -> int:
    """LLM call 2: extract structured memories from the turn."""
    return await extract_and_store_memories(
        session_id, turn_info, llm_config, existing_ctx=memory_ctx,
    )


async def run_notetaker_background(
    session_id: str,
    user_message: str,
    referee_output: str,
    teammate_output: str,
    narrator_response: str,
    llm_config: dict[str, str],
) -> None:
    """Run both notetaker jobs (summary + memory extraction) in parallel.

    Designed to be launched via ``asyncio.create_task`` so it does not
    block the SSE response.
    """
    t0 = time.monotonic()

    session = get_session(session_id)
    prev_summary = session.world_summary if session else ""

    llm = ChatOpenAI(
        model=llm_config["model"],
        api_key=llm_config["api_key"],
        base_url=llm_config["base_url"],
        temperature=0.1,
    )

    turn_info = _build_turn_info(
        user_message, referee_output, teammate_output, narrator_response,
    )

    # Fetch memory context ONCE and share it between both tasks
    memory_ctx = get_memory_context(session_id, max_chars=800)

    summary_result: str = prev_summary
    memory_count: int = 0

    async def _do_summary():
        nonlocal summary_result
        try:
            summary_result = await _update_summary(
                session_id, llm, prev_summary, memory_ctx, turn_info,
            )
        except Exception as exc:
            log.warning("[notetaker] summary failed: %s", exc, exc_info=True)
            log_event("error", "notetaker_summary_error",
                      session_id=session_id, detail=str(exc)[:200])

    async def _do_memories():
        nonlocal memory_count
        try:
            memory_count = await _extract_memories(
                session_id, turn_info, llm_config, memory_ctx,
            )
        except Exception as exc:
            log.warning("[notetaker] memory extraction failed: %s", exc, exc_info=True)
            log_event("error", "memory_extraction_error",
                      session_id=session_id, detail=str(exc)[:200])

    await asyncio.gather(_do_summary(), _do_memories())

    # Persist summary + recent events
    if session:
        event_line = user_message[:100]
        recent = session.recent_events[-9:] + [event_line]
        update_session(
            session_id,
            world_summary=summary_result,
            recent_events=recent,
        )

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    log_event("agent", "notetaker_done", session_id=session_id,
              agent="notetaker",
              detail=f"summary={len(summary_result)}ch, memories={memory_count}, {elapsed_ms}ms",
              data={"elapsed_ms": elapsed_ms, "memory_count": memory_count})

    if memory_count > 0:
        log_event("agent", "memories_extracted", session_id=session_id,
                  agent="notetaker", detail=f"Extracted {memory_count} new memories")


def schedule_notetaker(
    session_id: str,
    user_message: str,
    referee_output: str,
    teammate_output: str,
    narrator_response: str,
    llm_config: dict[str, str],
) -> None:
    """Fire-and-forget: schedule the notetaker as a background task."""
    task = asyncio.create_task(
        run_notetaker_background(
            session_id=session_id,
            user_message=user_message,
            referee_output=referee_output,
            teammate_output=teammate_output,
            narrator_response=narrator_response,
            llm_config=llm_config,
        ),
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
