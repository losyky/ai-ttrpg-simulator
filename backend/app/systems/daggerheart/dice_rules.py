"""Daggerheart Duality Dice resolution logic.

Core mechanic: roll 2d12 (Hope die + Fear die).
- If Hope > Fear -> success with Hope (player gains 1 Hope token)
- If Fear > Hope -> success with Fear (GM gains 1 Fear token)
- If Hope == Fear -> Critical Success (player gains Hope + clears 1 Stress)
"""

from __future__ import annotations


def determine_duality(hope_die: int, fear_die: int) -> str:
    """Determine the outcome of a Duality Dice roll.

    Returns one of: 'critical_success', 'with_hope', 'with_fear'.
    """
    if hope_die == fear_die:
        return "critical_success"
    if hope_die > fear_die:
        return "with_hope"
    return "with_fear"


def determine_success(total: int, dc: int, natural: int = 0) -> str:
    """Generic success check for Daggerheart.

    Daggerheart doesn't use DC in the traditional sense — actions succeed
    based on Hope/Fear duality. This is a simplified adapter for the
    GameSystem interface: total >= dc means success.
    """
    if total >= dc:
        return "success"
    return "failure"


def format_duality_result(hope_die: int, fear_die: int, modifier: int = 0) -> dict:
    """Format a full duality roll result for display."""
    total = hope_die + fear_die + modifier
    outcome = determine_duality(hope_die, fear_die)
    return {
        "hope_die": hope_die,
        "fear_die": fear_die,
        "modifier": modifier,
        "total": total,
        "outcome": outcome,
        "description": {
            "critical_success": f"大成功！双骰均为 {hope_die}！获得 1 Hope 并清除 1 Stress。",
            "with_hope": f"以希望成功 (Hope {hope_die} > Fear {fear_die})，总计 {total}。玩家获得 1 Hope。",
            "with_fear": f"以恐惧成功 (Fear {fear_die} > Hope {hope_die})，总计 {total}。GM 获得 1 Fear。",
        }[outcome],
    }
