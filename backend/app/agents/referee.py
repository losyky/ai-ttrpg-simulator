"""Referee agent – handles rules, dice, and mechanical judgments."""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from .compat import SafeChatOpenAI as ChatOpenAI, parse_tool_calls_from_content, extract_text_without_tool_calls

from app.agents.state import AgentState
from app.models.game_state import get_session
from app.tools.dice import dice_roller, roll_dice_raw
from app.systems.registry import get_current_system
from app.tools.encounter import (
    start_combat,
    next_turn,
    apply_damage,
    end_combat,
    get_combat_status,
)
from app.tools.read_material import (
    list_materials,
    browse_material,
    search_material,
    make_session_search_material,
)
from app.services.event_log import log_event
from app.services.memory_store import get_memory_context


@tool
def request_player_roll(
    check_label: str,
    expression: str,
    dc: int = 0,
    skill_name: str = "",
) -> str:
    """Request the PLAYER to roll dice via an interactive button (public roll).

    Use this for most checks: attack rolls, skill checks, saving throws, etc.
    The player will see a button and click to roll. This is the DEFAULT rolling method.

    Args:
        check_label: Clear label for the check, e.g. "运动检定", "反射豁免", "攻击检定"
        expression: Dice expression, e.g. "1d20+7"
        dc: Difficulty class (0 if unknown)
        skill_name: Skill or ability name, e.g. "运动", "巧手", "反射"
    """
    result = {
        "__interactive__": True,
        "element_type": "dice_request",
        "id": f"roll-{uuid.uuid4().hex[:8]}",
        "prompt": check_label,
        "expression": expression,
        "dc": dc,
        "skill_name": skill_name or check_label.replace("检定", "").replace("豁免", ""),
        "modifier": 0,
    }
    return json.dumps(result, ensure_ascii=False)


def _get_referee_tools(session_id: str | None = None):
    system = get_current_system(session_id)
    system_tools = system.get_tools().get("referee", [])
    mat_tool = make_session_search_material(session_id) if session_id else search_material
    return [
        request_player_roll,
        dice_roller,
        *system_tools,
        start_combat,
        next_turn,
        apply_damage,
        end_combat,
        get_combat_status,
        mat_tool,
    ]


async def referee_judge(state: AgentState) -> dict[str, Any]:
    """Let the referee assess the situation and make mechanical rulings."""
    from app.tools.interactive import parse_interactive_markers

    llm = ChatOpenAI(
        model=state["model"],
        api_key=state["api_key"],
        base_url=state["base_url"],
        temperature=0.0,
    )
    REFEREE_TOOLS = _get_referee_tools(state["session_id"])
    llm_with_tools = llm.bind_tools(REFEREE_TOOLS)

    session = get_session(state["session_id"])
    game_phase = state.get("game_phase", "exploration")
    context_parts = [f"当前游戏阶段: {game_phase}"]

    player_ctx = state.get("player_context", "")
    if player_ctx:
        context_parts.append(player_ctx)

    if session:
        if session.world_summary:
            context_parts.append(f"世界状态摘要:\n{session.world_summary}")
        if session.recent_events:
            context_parts.append("近期事件:\n" + "\n".join(f"- {e}" for e in session.recent_events[-5:]))
    mem_ctx = get_memory_context(state["session_id"], max_chars=600)
    if mem_ctx:
        context_parts.append(mem_ctx)

    if game_phase == "combat":
        combat_status = get_combat_status.invoke({"session_id": state["session_id"]})
        if combat_status and "没有进行中的战斗" not in combat_status:
            context_parts.append(f"当前战况:\n{combat_status}")

    from app.agents.narrator import _load_supplementary_rules
    rules_ctx = _load_supplementary_rules(max_chars=1500)
    if rules_ctx:
        context_parts.append(rules_ctx)

    context_parts.append(f"玩家行动: {state['user_message']}")

    if game_phase == "combat":
        context_parts.append(
            '当前处于战斗阶段。你可以使用遭遇管理工具（start_combat, next_turn, apply_damage, end_combat, get_combat_status）来追踪战斗状态。'
            '当需要玩家行动或掷骰时，必须使用工具请求玩家操作，而不是自己决定结果。'
            '每次只处理当前一步（一个回合或一次检定），然后等待玩家下一条消息。'
        )
    else:
        context_parts.append('请独立判断当前情况是否需要进行检定。如果需要，必须使用掷骰工具请求玩家掷骰，绝不可以自己描述或编造骰子结果。如果不需要检定，回复"无需进行检定"。')

    system = get_current_system(state["session_id"])
    REFEREE_SYSTEM = system.get_prompts()["referee"]
    msgs = [
        SystemMessage(content=REFEREE_SYSTEM),
        HumanMessage(content="\n\n".join(context_parts)),
    ]

    log_event("agent", "referee_start", session_id=state["session_id"],
              agent="referee", detail=state["user_message"][:200])

    response = await llm_with_tools.ainvoke(msgs)

    tool_map = {t.name: t for t in REFEREE_TOOLS}
    outputs: list[str] = []
    dice_results: list[dict[str, Any]] = []
    interactive_elements: list[dict] = []

    _tool_calls = response.tool_calls if hasattr(response, "tool_calls") and response.tool_calls else []

    if not _tool_calls and response.content:
        _tool_calls = parse_tool_calls_from_content(str(response.content))
        if _tool_calls:
            log_event("tool", "referee_fallback_parse", session_id=state["session_id"],
                      agent="referee",
                      detail=f"Parsed {len(_tool_calls)} tool call(s) from content")

    if _tool_calls:
        for tc in _tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            if tool_name == "request_player_roll":
                result_str = request_player_roll.invoke(tool_args)
                _, elems = parse_interactive_markers(result_str)
                interactive_elements.extend(elems)
                label = tool_args.get("check_label", "检定")
                dc = tool_args.get("dc", 0)
                expr = tool_args.get("expression", "1d20")
                dc_text = f" (DC {dc})" if dc > 0 else ""
                outputs.append(f"📋 {label}: 请玩家掷 {expr}{dc_text}")
                log_event("tool", "player_roll_requested", session_id=state["session_id"],
                          agent="referee", detail=f"{label}: {expr}{dc_text}")

            elif tool_name == "request_duality_roll":
                from app.tools.interactive import request_duality_roll as _duality_tool
                result_str = _duality_tool.invoke(tool_args)
                _, elems = parse_interactive_markers(result_str)
                interactive_elements.extend(elems)
                trait = tool_args.get("trait_name", "")
                prompt_text = tool_args.get("prompt", "二元骰检定")
                outputs.append(f"🎭 {prompt_text}" + (f" ({trait})" if trait else "") + ": 请玩家掷二元骰")
                log_event("tool", "duality_roll_requested", session_id=state["session_id"],
                          agent="referee", detail=f"{prompt_text} ({trait})")

            elif tool_name == "announce_token_change":
                tool_fn = tool_map.get(tool_name)
                if tool_fn:
                    result_str = await tool_fn.ainvoke(tool_args)
                    _, elems = parse_interactive_markers(str(result_str))
                    interactive_elements.extend(elems)
                    outputs.append(str(result_str))

            elif tool_name == "dice_roller":
                # Secret/hidden roll — automatic
                expr = tool_args.get("expression", "1d20")
                label = tool_args.get("label", "暗骰")
                result = roll_dice_raw(expr)
                dice_results.append({
                    "expression": result.expression,
                    "rolls": result.rolls,
                    "total": result.total,
                    "detail": result.detail,
                    "label": f"🔒 {label}",
                    "dc": 0,
                })
                log_event("tool", "secret_dice_rolled", session_id=state["session_id"],
                          agent="referee", detail=f"[暗骰] {result.expression} = {result.total} ({result.detail})")
                outputs.append(f"🔒 暗骰 {result.expression} → 已暗中判定")
            elif tool_name in tool_map:
                tool_fn = tool_map[tool_name]
                if "session_id" in tool_args:
                    pass
                elif hasattr(tool_fn, "args_schema") and "session_id" in tool_fn.args_schema.model_fields:
                    tool_args["session_id"] = state["session_id"]
                result_text = await tool_fn.ainvoke(tool_args)
                outputs.append(str(result_text))

    text_content = str(response.content) if response.content else ""
    if text_content:
        if _tool_calls and not (hasattr(response, "tool_calls") and response.tool_calls):
            text_content = extract_text_without_tool_calls(text_content)
        if text_content.strip():
            outputs.append(text_content)

    referee_output = "\n".join(outputs) if outputs else "无需进行检定。"
    log_event("agent", "referee_done", session_id=state["session_id"],
              agent="referee", detail=referee_output[:200],
              data={"dice_count": len(dice_results), "tool_calls": len(outputs),
                    "interactive_count": len(interactive_elements)})
    return {
        "referee_output": referee_output,
        "dice_results": dice_results,
        "interactive_elements": interactive_elements,
    }
