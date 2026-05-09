"""Encounter Manager – tracks combat initiative, rounds, and creature HP."""

from __future__ import annotations

from typing import Any
from langchain_core.tools import tool

from app.models.game_state import update_session
from app.models.schemas import GamePhase

# Per-session encounter state (keyed by session_id)
_encounters: dict[str, dict[str, Any]] = {}


def _get_enc(session_id: str) -> dict[str, Any]:
    if session_id not in _encounters:
        _encounters[session_id] = {
            "active": False,
            "round": 0,
            "turn_index": 0,
            "combatants": [],
        }
    return _encounters[session_id]


@tool
def start_combat(session_id: str, combatants: list[dict[str, Any]]) -> str:
    """Begin a combat encounter.

    Args:
        session_id: Current game session id.
        combatants: List of combatant dicts, each with
                    {"name": str, "initiative": int, "hp": int, "max_hp": int, "team": "player"|"enemy"}.
    """
    enc = _get_enc(session_id)
    sorted_combatants = sorted(combatants, key=lambda c: c["initiative"], reverse=True)
    enc.update({
        "active": True,
        "round": 1,
        "turn_index": 0,
        "combatants": sorted_combatants,
    })
    update_session(session_id, phase=GamePhase.COMBAT)
    order = "\n".join(
        f"  {i+1}. {c['name']} (先攻 {c['initiative']}, HP {c['hp']}/{c['max_hp']})"
        for i, c in enumerate(sorted_combatants)
    )
    return f"⚔️ 战斗开始！第 1 轮\n先攻顺序:\n{order}\n\n当前行动: {sorted_combatants[0]['name']}"


@tool
def next_turn(session_id: str) -> str:
    """Advance to the next combatant's turn.

    Args:
        session_id: Current game session id.
    """
    enc = _get_enc(session_id)
    if not enc["active"]:
        return "当前没有进行中的战斗。"

    enc["turn_index"] += 1
    if enc["turn_index"] >= len(enc["combatants"]):
        enc["turn_index"] = 0
        enc["round"] += 1

    current = enc["combatants"][enc["turn_index"]]
    return f"第 {enc['round']} 轮 — 轮到 {current['name']} 行动 (HP {current['hp']}/{current['max_hp']})"


@tool
def apply_damage(session_id: str, target_name: str, damage: int) -> str:
    """Apply damage to a combatant.

    Args:
        session_id: Current game session id.
        target_name: Name of the target combatant.
        damage: Amount of damage to apply (positive integer).
    """
    enc = _get_enc(session_id)
    for c in enc["combatants"]:
        if c["name"].lower() == target_name.lower():
            c["hp"] = max(0, c["hp"] - damage)
            status = "倒下！" if c["hp"] <= 0 else f"剩余 HP {c['hp']}/{c['max_hp']}"
            return f"{c['name']} 受到 {damage} 点伤害。{status}"
    return f"未找到名为 {target_name} 的战斗参与者。"


@tool
def end_combat(session_id: str) -> str:
    """End the current combat encounter.

    Args:
        session_id: Current game session id.
    """
    enc = _get_enc(session_id)
    if not enc["active"]:
        return "当前没有进行中的战斗。"
    rounds = enc["round"]
    enc.update({"active": False, "round": 0, "turn_index": 0, "combatants": []})
    update_session(session_id, phase=GamePhase.EXPLORATION)
    return f"战斗结束！共进行了 {rounds} 轮。"


@tool
def get_combat_status(session_id: str) -> str:
    """Get the current combat status overview.

    Args:
        session_id: Current game session id.
    """
    enc = _get_enc(session_id)
    if not enc["active"]:
        return "当前没有进行中的战斗。"

    lines = [f"第 {enc['round']} 轮:"]
    for i, c in enumerate(enc["combatants"]):
        marker = "→ " if i == enc["turn_index"] else "  "
        hp_bar = f"HP {c['hp']}/{c['max_hp']}"
        status = " [倒下]" if c["hp"] <= 0 else ""
        lines.append(f"{marker}{c['name']} ({c['team']}) {hp_bar}{status}")

    return "\n".join(lines)
