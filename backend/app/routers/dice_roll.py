"""Player-initiated dice roll endpoint.

When the narrator requests a dice roll via interactive elements,
the player clicks the dice button and this endpoint handles the
actual roll with proper result calculation.
"""

from __future__ import annotations

import re

from fastapi import APIRouter

from app.models.schemas import PlayerDiceRequest, DiceResult
from app.tools.dice import roll_dice_raw

router = APIRouter(prefix="/api/dice", tags=["dice"])


def _get_system(session_id: str | None = None):
    from app.systems.registry import get_current_system
    return get_current_system(session_id)


def _roll_pf2e(req: PlayerDiceRequest) -> DiceResult:
    result = roll_dice_raw(req.expression)
    natural_20 = 20 in result.rolls
    natural_1 = 1 in result.rolls and len(result.rolls) == 1
    total = result.total + req.modifier
    success_level = ""
    if req.dc > 0:
        system = _get_system(req.session_id)
        success_level = system.determine_success(total, req.dc)
    if natural_20 and success_level:
        levels = ["critical_failure", "failure", "success", "critical_success"]
        idx = levels.index(success_level)
        success_level = levels[min(idx + 1, 3)]
    elif natural_1 and success_level:
        levels = ["critical_failure", "failure", "success", "critical_success"]
        idx = levels.index(success_level)
        success_level = levels[max(idx - 1, 0)]
    return DiceResult(
        expression=req.expression,
        rolls=result.rolls,
        total=total,
        detail=result.detail + (f" + {req.modifier}" if req.modifier else ""),
        success_level=success_level,
        dc=req.dc,
        label=req.label,
    )


def _roll_daggerheart(req: PlayerDiceRequest) -> DiceResult:
    """Daggerheart Duality Dice: 2d12 → Hope die vs Fear die."""
    from app.systems.daggerheart.dice_rules import format_duality_result
    result = roll_dice_raw(req.expression)
    total = result.total + req.modifier
    # Detect duality roll: expression contains "2d12"
    is_duality = bool(re.search(r"2d12", req.expression))
    if is_duality and len(result.rolls) >= 2:
        hope_die = result.rolls[0]
        fear_die = result.rolls[1]
        duality = format_duality_result(hope_die, fear_die, req.modifier)
        outcome = duality["outcome"]
        success_level = "critical_success" if outcome == "critical_success" else "success"
        return DiceResult(
            expression=req.expression,
            rolls=result.rolls,
            total=total,
            detail=result.detail + (f" + {req.modifier}" if req.modifier else ""),
            success_level=success_level,
            dc=req.dc,
            label=req.label,
            duality_outcome=outcome,
            hope_die=hope_die,
            fear_die=fear_die,
            system_info={"description": duality["description"]},
        )
    return DiceResult(
        expression=req.expression,
        rolls=result.rolls,
        total=total,
        detail=result.detail + (f" + {req.modifier}" if req.modifier else ""),
        dc=req.dc,
        label=req.label,
    )


def _is_dual_attribute_expr(expression: str) -> bool:
    """Check if expression looks like a dual-attribute roll, e.g. '1d6+1d8'."""
    dice_parts = re.findall(r"(\d*)d(\d+)", expression)
    if len(dice_parts) >= 2:
        return all(int(count or "1") == 1 for count, _ in dice_parts)
    return False


def _parse_dice_terms(expression: str) -> list[tuple[int, int]]:
    """Parse dice expression into [(count, sides), ...] terms."""
    return [(int(c or "1"), int(s)) for c, s in re.findall(r"(\d*)d(\d+)", expression)]


def _parse_flat_modifier(expression: str) -> int:
    """Extract flat +/- modifiers that are not part of dice terms."""
    cleaned = re.sub(r"\d*d\d+", "", expression)
    return sum(int(x) for x in re.findall(r"[+-]\s*\d+", cleaned.replace(" ", "")))


def _roll_swade(req: PlayerDiceRequest) -> DiceResult:
    """SWADE dice roll with Ace (exploding) on ALL dice.

    Dual-attribute (take-higher + Acing) activates when BOTH conditions hold:
      1. Expression is two single-die terms (e.g. '1d6+1d8')
      2. A DC is specified (dc > 0) — indicating an attribute check
    Critical detection (dual-attribute only):
      - Both dice aced (first roll == max) → critical_success
      - Both dice rolled 1 → critical_failure

    All other rolls (damage, etc.) still use Ace on every die but sum normally.
    """
    from app.systems.swade.dice_rules import (
        determine_success as swade_success,
        ace_roll_detailed,
    )

    is_dual = _is_dual_attribute_expr(req.expression) and req.dc > 0

    if is_dual:
        dice_parts = re.findall(r"(\d*)d(\d+)", req.expression)
        sides_list = [int(sides) for _, sides in dice_parts[:2]]
        primary_sides, secondary_sides = sides_list[0], min(sides_list[1], 12)

        pri = ace_roll_detailed(primary_sides)
        sec = ace_roll_detailed(secondary_sides)

        best = max(pri["total"], sec["total"]) + req.modifier
        rolls = [pri["total"], sec["total"]]
        used = "primary" if pri["total"] >= sec["total"] else "secondary"
        detail = (
            f"d{primary_sides}→{pri['total']}"
            f"{'💥' if pri['aced'] else ''}"
            f", d{secondary_sides}→{sec['total']}"
            f"{'💥' if sec['aced'] else ''}"
            f" (取高={max(pri['total'], sec['total'])})"
        )
        if req.modifier:
            detail += f" +{req.modifier}"

        both_aced = pri["aced"] and sec["aced"]
        both_ones = pri["natural"] == 1 and sec["natural"] == 1

        raises = 0
        if both_ones:
            success_level = "critical_failure"
        elif both_aced:
            success_level = "critical_success"
            if best >= req.dc:
                raises = (best - req.dc) // 4
        else:
            success_level = swade_success(best, req.dc)
            if best >= req.dc:
                raises = (best - req.dc) // 4

        return DiceResult(
            expression=req.expression,
            rolls=rolls,
            total=best,
            detail=detail,
            success_level=success_level,
            dc=req.dc,
            label=req.label,
            raises=raises,
            system_info={
                "dual_attribute": True,
                "primary_sides": primary_sides,
                "secondary_sides": secondary_sides,
                "used": used,
                "primary_aced": pri["aced"],
                "secondary_aced": sec["aced"],
                "critical": "success" if both_aced else ("failure" if both_ones else None),
            },
        )

    # Non-dual: damage / other rolls — still Ace every die
    terms = _parse_dice_terms(req.expression)
    flat_mod = _parse_flat_modifier(req.expression)

    all_rolls: list[int] = []
    detail_parts: list[str] = []
    for count, sides in terms:
        for _ in range(count):
            info = ace_roll_detailed(sides)
            all_rolls.append(info["total"])
            label = f"d{sides}→{info['total']}"
            if info["aced"]:
                label += "💥"
            detail_parts.append(label)

    dice_total = sum(all_rolls) + flat_mod + req.modifier
    detail_str = ", ".join(detail_parts)
    if flat_mod:
        detail_str += f" +{flat_mod}"
    if req.modifier:
        detail_str += f" +{req.modifier}(mod)"

    raises = 0
    success_level = ""
    if req.dc > 0:
        success_level = swade_success(dice_total, req.dc)
        if dice_total >= req.dc:
            raises = (dice_total - req.dc) // 4

    return DiceResult(
        expression=req.expression,
        rolls=all_rolls,
        total=dice_total,
        detail=detail_str,
        success_level=success_level,
        dc=req.dc,
        label=req.label,
        raises=raises,
        system_info={"dual_attribute": False},
    )


@router.post("/roll")
async def player_roll(req: PlayerDiceRequest) -> DiceResult:
    """Roll dice with system-specific result calculation."""
    system = _get_system(req.session_id)
    system_id = system.system_id

    if system_id == "daggerheart":
        return _roll_daggerheart(req)
    elif system_id == "swade":
        return _roll_swade(req)
    else:
        return _roll_pf2e(req)
