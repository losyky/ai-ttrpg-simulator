"""七物语 (SWADE-based) dice resolution logic.

Core mechanics:
- Dual-attribute check: roll primary die + secondary die (capped at d12), take higher
- Ace (exploding): if a die rolls its max, re-roll and add
- Raise: every 4 points above DC is one Raise
- Damage vs Toughness: >= Toughness = Shaken, each Raise = +1 Wound
"""

from __future__ import annotations

import random

VALID_DIE_SIDES = (4, 6, 8, 10, 12)


def ace_roll(sides: int) -> int:
    """Roll a single die with Acing (exploding on max)."""
    if sides < 4:
        sides = 4
    total = 0
    while True:
        roll = random.randint(1, sides)
        total += roll
        if roll < sides:
            break
    return total


def dual_attribute_check(primary_sides: int, secondary_sides: int, modifier: int = 0) -> dict:
    """Perform a dual-attribute check (七物语 style).

    Roll primary die + secondary die (secondary capped at d12), take the higher result.
    Both dice can Ace.
    """
    secondary_sides = min(secondary_sides, 12)
    primary_result = ace_roll(primary_sides)
    secondary_result = ace_roll(secondary_sides)
    best = max(primary_result, secondary_result) + modifier
    return {
        "primary_roll": primary_result,
        "primary_sides": primary_sides,
        "secondary_roll": secondary_result,
        "secondary_sides": secondary_sides,
        "modifier": modifier,
        "total": best,
        "used": "primary" if primary_result >= secondary_result else "secondary",
    }


def determine_success(total: int, dc: int, natural: int = 0) -> str:
    """Determine success level for a 七物语 check.

    Returns: 'failure', 'success', 'success_with_raise', 'success_with_N_raises'
    """
    if total < dc:
        return "failure"
    margin = total - dc
    raises = margin // 4
    if raises == 0:
        return "success"
    if raises == 1:
        return "success_with_raise"
    return f"success_with_{raises}_raises"


def calc_damage_result(damage_total: int, toughness: int, already_shaken: bool = False) -> dict:
    """Calculate wound/shaken result from damage vs toughness.

    Returns dict with 'shaken', 'wounds', 'description'.
    """
    if damage_total < toughness:
        return {"shaken": False, "wounds": 0, "description": "未命中坚韧值，无效果。"}

    margin = damage_total - toughness
    raises = margin // 4
    wounds = raises
    if already_shaken and damage_total >= toughness:
        wounds += 1

    if wounds == 0:
        return {"shaken": True, "wounds": 0, "description": "目标进入动摇状态。"}

    wounds = min(wounds, 3)
    return {
        "shaken": True,
        "wounds": wounds,
        "description": f"目标受到 {wounds} 点损伤并进入动摇状态。" + (
            " 已达3点损伤上限，重伤！" if wounds >= 3 else ""
        ),
    }


def calc_toughness(vigor_die_sides: int, armor: int = 0) -> int:
    """Calculate Toughness: 2 + vigor_die_sides/2 + armor."""
    return 2 + vigor_die_sides // 2 + armor


def calc_parry(agility_die_sides: int) -> int:
    """Calculate Parry: 2 + agility_die_sides/2."""
    return 2 + agility_die_sides // 2


def calc_mp(level: int, spirit_die_sides: int) -> int:
    """Calculate max MP: level*2 + spirit_die_sides*5."""
    return level * 2 + spirit_die_sides * 5


def calc_ip() -> int:
    """Calculate base IP (always 6)."""
    return 6
