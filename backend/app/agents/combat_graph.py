"""Combat subgraph — encapsulates the turn-based combat loop
as a standalone LangGraph StateGraph that can be embedded in the
main orchestration graph.

System-aware: uses the active GameSystem's combat prompt.
For narrative-combat systems (e.g. Daggerheart), the main graph
should NOT route here — those systems handle combat via the
referee + narrator narrative flow.

Combat flow:
  1. assess_combat  → analyze the combat situation
  2. route           → decide if combat continues or ends
  3. resolve_round  → execute one round (rolls, actions, damage)
  4. loop back to assess_combat
  5. summarize      → produce final combat summary when done
"""

from __future__ import annotations

import operator
import re
from typing import Annotated, Any, TypedDict

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from .compat import SafeChatOpenAI as ChatOpenAI

from app.agents.state import AgentState
from app.models.game_state import get_session
from app.tools.dice import roll_dice_raw
from app.tools.encounter import (
    start_combat,
    next_turn,
    apply_damage,
    end_combat,
    get_combat_status,
)
from app.services.event_log import log_event


class CombatState(TypedDict, total=False):
    session_id: str
    api_key: str
    model: str
    base_url: str
    user_message: str

    combatants: list[dict[str, Any]]
    round_number: int
    combat_log: Annotated[list[str], operator.add]
    dice_results: Annotated[list[dict[str, Any]], operator.add]
    combat_active: bool
    combat_summary: str


def _get_combat_prompts(session_id: str) -> tuple[str, str, str]:
    """Return (system_label, assess_prompt_template, resolve_prompt_template)
    based on the active game system."""
    from app.systems.registry import get_current_system
    system = get_current_system(session_id)
    combat_prompt = system.get_prompts().get("combat", "")

    if system.system_id == "swade":
        label = "七物语战斗裁判"
        assess = (
            f"你是{label}。根据以下战况，判断本轮需要执行的行动。\n"
            f"{combat_prompt}\n\n"
            "战况:\n{status}\n\n玩家消息: {user_msg}\n\n"
            "请简洁描述本轮战斗情况和需要做的检定。\n"
            '如果战斗应该结束（所有敌人被击败、撤退、或其他原因），回答 "COMBAT_END" 并说明原因。'
        )
        resolve = (
            f"你是{label}。根据评估结果执行本轮战斗:\n"
            "1. 为每个参战者掷骰（攻击、技能检定等）\n"
            "2. 计算伤害并应用（注意爆骰机制）\n"
            "3. 检查动摇和损伤状态\n\n"
            "评估结果: {assessment}\n\n"
            "请描述本轮战斗的详细过程。用 DICE: XdY+Z 格式标注需要的骰子，"
            "用 DAMAGE: XdY+Z 标注伤害骰。"
        )
    else:
        label = "PF2e 战斗裁判"
        assess = (
            f"你是{label}。根据以下战况，判断本轮需要执行的行动。\n\n"
            "战况:\n{status}\n\n玩家消息: {user_msg}\n\n"
            "请简洁描述本轮战斗情况和需要做的检定。\n"
            '如果战斗应该结束（所有敌人被击败、撤退、或其他原因），回答 "COMBAT_END" 并说明原因。'
        )
        resolve = (
            f"你是{label}。根据评估结果执行本轮战斗:\n"
            "1. 为每个参战者掷骰（攻击、技能检定等）\n"
            "2. 计算伤害并应用\n"
            "3. 检查状态变化\n\n"
            "评估结果: {assessment}\n\n"
            "请描述本轮战斗的详细过程。用 DICE: 1d20+X 格式标注需要的骰子，"
            "用 DAMAGE: XdY+Z 标注伤害骰。"
        )

    return label, assess, resolve


async def assess_combat(state: CombatState) -> dict[str, Any]:
    """Assess the current combat situation."""
    llm = ChatOpenAI(
        model=state["model"],
        api_key=state["api_key"],
        base_url=state["base_url"],
        temperature=0.1,
    )

    session = get_session(state["session_id"])
    status = ""
    if session and session.recent_events:
        status = "\n".join(session.recent_events[-5:])

    label, assess_template, _ = _get_combat_prompts(state["session_id"])

    prompt = assess_template.format(
        status=status or "战斗刚开始",
        user_msg=state.get("user_message", ""),
    )

    response = await llm.ainvoke([
        SystemMessage(content=f"你是{label}，精确且公正。"),
        HumanMessage(content=prompt),
    ])

    assessment = str(response.content)
    should_end = "COMBAT_END" in assessment.upper()

    log_event("agent", "combat_assess", session_id=state["session_id"],
              detail=assessment[:200])

    return {
        "combat_summary": assessment,
        "combat_active": not should_end,
        "combat_log": [f"[评估] {assessment[:200]}"],
    }


async def resolve_round(state: CombatState) -> dict[str, Any]:
    """Execute one round of combat — dice rolls and resolution."""
    llm = ChatOpenAI(
        model=state["model"],
        api_key=state["api_key"],
        base_url=state["base_url"],
        temperature=0.2,
    )

    label, _, resolve_template = _get_combat_prompts(state["session_id"])

    prompt = resolve_template.format(
        assessment=state.get("combat_summary", ""),
    )

    response = await llm.ainvoke([
        SystemMessage(content=f"你是{label}。根据描述执行战斗。"),
        HumanMessage(content=prompt),
    ])

    text = str(response.content)
    dice_results: list[dict[str, Any]] = []
    combat_log: list[str] = []

    for match in re.finditer(r"DICE:\s*(\d+d\d+(?:[+-]\d+)?)", text):
        expr = match.group(1)
        result = roll_dice_raw(expr)
        dice_results.append({
            "expression": result.expression,
            "rolls": result.rolls,
            "total": result.total,
            "detail": result.detail,
        })
        combat_log.append(f"🎲 {result.expression} → {result.total}")

    for match in re.finditer(r"DAMAGE:\s*(\d+d\d+(?:[+-]\d+)?)", text):
        expr = match.group(1)
        result = roll_dice_raw(expr)
        dice_results.append({
            "expression": result.expression,
            "rolls": result.rolls,
            "total": result.total,
            "detail": f"伤害: {result.detail}",
        })
        combat_log.append(f"💥 伤害 {result.expression} → {result.total}")

    round_num = state.get("round_number", 0) + 1
    combat_log.insert(0, f"--- 第 {round_num} 轮 ---")
    combat_log.append(text[:300])

    log_event("agent", "combat_round", session_id=state["session_id"],
              detail=f"Round {round_num}: {len(dice_results)} dice",
              data={"round": round_num, "dice_count": len(dice_results)})

    return {
        "round_number": round_num,
        "dice_results": dice_results,
        "combat_log": combat_log,
        "combat_summary": text,
    }


async def summarize_combat(state: CombatState) -> dict[str, Any]:
    """Produce a final summary when combat ends."""
    log_entries = state.get("combat_log", [])
    summary = "\n".join(log_entries[-20:])

    log_event("agent", "combat_end", session_id=state["session_id"],
              detail=f"Combat ended after {state.get('round_number', 0)} rounds")

    return {
        "combat_summary": f"战斗结束（共 {state.get('round_number', 0)} 轮）\n{summary}",
        "combat_active": False,
    }


def _route_combat(state: CombatState) -> str:
    if not state.get("combat_active", False):
        return "summarize"
    if state.get("round_number", 0) >= 20:
        return "summarize"
    return "resolve"


def build_combat_subgraph() -> StateGraph:
    """Build the combat subgraph. Can be used as a standalone graph
    or embedded as a node in the main graph."""
    graph = StateGraph(CombatState)

    graph.add_node("assess", assess_combat)
    graph.add_node("resolve", resolve_round)
    graph.add_node("summarize", summarize_combat)

    graph.set_entry_point("assess")

    graph.add_conditional_edges(
        "assess",
        _route_combat,
        {"resolve": "resolve", "summarize": "summarize"},
    )

    # After resolving, go back to assess
    graph.add_edge("resolve", "assess")
    graph.add_edge("summarize", END)

    return graph


# Pre-compiled combat subgraph
combat_subgraph = build_combat_subgraph().compile()


async def run_combat_subgraph(state: AgentState) -> dict[str, Any]:
    """Entry point callable from the main graph — adapts AgentState
    to CombatState, runs the subgraph, and maps results back."""
    combat_input: dict[str, Any] = {
        "session_id": state["session_id"],
        "api_key": state["api_key"],
        "model": state["model"],
        "base_url": state["base_url"],
        "user_message": state["user_message"],
        "round_number": 0,
        "combat_active": True,
        "combat_log": [],
        "dice_results": [],
        "combat_summary": "",
    }

    result = await combat_subgraph.ainvoke(combat_input)

    return {
        "referee_output": result.get("combat_summary", ""),
        "dice_results": result.get("dice_results", []),
    }
