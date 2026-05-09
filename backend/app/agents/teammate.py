"""Teammate agent – simulates other party members."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from .compat import SafeChatOpenAI as ChatOpenAI

from app.agents.state import AgentState
from app.agents.prompts import TEAMMATE_SYSTEM
from app.models.game_state import get_session
from app.services.event_log import log_event
from app.services.memory_store import get_memory_context
from app.systems.registry import get_current_system


def _get_rich_char_context(name: str) -> str:
    """Try to get full character summary from the character store."""
    try:
        from app.routers.characters import _characters
        from app.models.character import character_to_summary
        for sheet in _characters.values():
            if sheet.name == name:
                return character_to_summary(sheet)
    except Exception:
        pass
    return ""


async def teammates_act(state: AgentState) -> dict[str, Any]:
    """Generate actions/dialog from AI teammates."""
    session = get_session(state["session_id"])
    if not session or not session.teammates:
        return {"teammate_output": ""}

    llm = ChatOpenAI(
        model=state["model"],
        api_key=state["api_key"],
        base_url=state["base_url"],
        temperature=0.9,
    )

    mem_ctx = get_memory_context(state["session_id"], max_chars=400)

    outputs: list[str] = []
    for tm in session.teammates:
        rich_ctx = _get_rich_char_context(tm.name)
        if rich_ctx:
            char_context = f"你的角色详细信息:\n{rich_ctx}"
        else:
            char_context = (
                f"你的角色: {tm.name} ({tm.ancestry} {tm.character_class}, Lv.{tm.level})\n"
                f"HP: {tm.hp}/{tm.max_hp}\n"
                f"状态: {', '.join(tm.conditions) if tm.conditions else '正常'}"
            )

        referee = state.get("referee_output", "")
        scene_parts = [f"当前阶段: {state.get('game_phase', 'exploration')}"]

        player_ctx = state.get("player_context", "")
        if player_ctx:
            scene_parts.append(player_ctx)

        if session.world_summary:
            scene_parts.append(f"当前局势:\n{session.world_summary}")
        if mem_ctx:
            scene_parts.append(mem_ctx)
        if session.recent_events:
            scene_parts.append("近期发生:\n" + "\n".join(f"- {e}" for e in session.recent_events[-5:]))
        scene_parts.append(f"玩家说: {state['user_message']}")
        if referee:
            scene_parts.append(f"规则判定结果: {referee}")
        scene_parts.append(f"请以 {tm.name} 的身份简洁回应（1-3句话）。")

        system = get_current_system(state["session_id"])
        system_teammate_prompt = system.get_prompts().get("teammate", TEAMMATE_SYSTEM)

        response = await llm.ainvoke([
            SystemMessage(content=f"{system_teammate_prompt}\n\n{char_context}"),
            HumanMessage(content="\n\n".join(scene_parts)),
        ])
        outputs.append(f"【{tm.name}】{response.content}")

    log_event("agent", "teammates_done", session_id=state["session_id"],
              agent="teammate", detail="\n".join(outputs)[:200],
              data={"teammate_count": len(session.teammates)})
    return {"teammate_output": "\n".join(outputs)}
