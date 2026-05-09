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


def _roll_swade(req: PlayerDiceRequest) -> DiceResult:
    """SWADE dual-attribute roll: roll two dice, take higher, with Acing."""
    from app.systems.swade.dice_rules import determine_success as swade_success
    result = roll_dice_raw(req.expression)
    total = result.total + req.modifier
    raises = 0
    success_level = ""
    if req.dc > 0:
        success_level = swade_success(total, req.dc)
        if total >= req.dc:
            raises = (total - req.dc) // 4
    acing = any(r >= 4 and r % 4 == 0 for r in result.rolls)
    return DiceResult(
        expression=req.expression,
        rolls=result.rolls,
        total=total,
        detail=result.detail + (f" + {req.modifier}" if req.modifier else ""),
        success_level=success_level,
        dc=req.dc,
        label=req.label,
        raises=raises,
        system_info={"acing": acing},
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
