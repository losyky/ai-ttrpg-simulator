"""Character sheet tool — read/update character data within a session.

Reads from both the lightweight session state and the full FVTT-format
character sheet when available.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.models.game_state import get_session, update_session
from app.models.character import character_to_summary
from app.routers.characters import get_loaded_character


@tool
def get_player_info(session_id: str) -> str:
    """Get the current player character's information.

    Args:
        session_id: Current game session id.
    """
    state = get_session(session_id)
    if not state or not state.player:
        return "玩家角色信息尚未设置。"

    p = state.player
    lines = [
        f"角色: {p.name}",
        f"血统: {p.ancestry} | 职业: {p.character_class} | 等级: {p.level}",
        f"HP: {p.hp}/{p.max_hp}",
    ]
    if p.conditions:
        lines.append(f"状态: {', '.join(p.conditions)}")
    return "\n".join(lines)


@tool
def get_full_character_sheet(character_id: str) -> str:
    """Get the full character sheet for a loaded character, including
    abilities, skills, feats, spells, and inventory.

    Args:
        character_id: The character's ID (from the character import system).
    """
    sheet = get_loaded_character(character_id)
    if not sheet:
        return f"未找到 ID 为 {character_id} 的角色。"
    return character_to_summary(sheet)


@tool
def update_player_hp(session_id: str, hp_change: int) -> str:
    """Change the player's current HP by a given amount (negative for damage).

    Args:
        session_id: Current game session id.
        hp_change: Amount to change HP by (positive = heal, negative = damage).
    """
    state = get_session(session_id)
    if not state or not state.player:
        return "玩家角色信息尚未设置。"

    new_hp = max(0, min(state.player.max_hp, state.player.hp + hp_change))
    state.player.hp = new_hp
    update_session(session_id, player=state.player)

    action = "恢复" if hp_change > 0 else "受到"
    amount = abs(hp_change)
    return f"{state.player.name} {action} {amount} 点生命值。当前 HP: {new_hp}/{state.player.max_hp}"


@tool
def add_condition(session_id: str, condition: str) -> str:
    """Add a condition to the player character.

    Args:
        session_id: Current game session id.
        condition: The condition name to add (e.g. "惊惧 1", "中毒").
    """
    state = get_session(session_id)
    if not state or not state.player:
        return "玩家角色信息尚未设置。"

    if condition not in state.player.conditions:
        state.player.conditions.append(condition)
        update_session(session_id, player=state.player)
    return f"{state.player.name} 获得状态: {condition}"


@tool
def remove_condition(session_id: str, condition: str) -> str:
    """Remove a condition from the player character.

    Args:
        session_id: Current game session id.
        condition: The condition name to remove.
    """
    state = get_session(session_id)
    if not state or not state.player:
        return "玩家角色信息尚未设置。"

    if condition in state.player.conditions:
        state.player.conditions.remove(condition)
        update_session(session_id, player=state.player)
        return f"{state.player.name} 移除状态: {condition}"
    return f"{state.player.name} 没有状态 {condition}。"
