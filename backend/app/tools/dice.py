"""Dice roller tool – uses the `d20` library for real random rolls."""

from __future__ import annotations

import d20
from langchain_core.tools import tool

from app.models.schemas import DiceResult


def roll_dice_raw(expression: str) -> DiceResult:
    """Roll dice using a real RNG. Never let the LLM hallucinate results."""
    result = d20.roll(expression)

    # Extract individual die values from the AST
    rolls: list[int] = []

    def _extract(node: d20.ast.Node) -> None:
        if isinstance(node, d20.Dice):
            for die in node.values:
                if isinstance(die, d20.Die):
                    rolls.append(die.number)
            for die in node.keptset:
                if isinstance(die, d20.Die):
                    if die.number not in rolls:
                        rolls.append(die.number)
        if hasattr(node, "children"):
            for child in node.children:
                _extract(child)

    _extract(result.expr)

    if not rolls:
        rolls = [result.total]

    return DiceResult(
        expression=expression,
        rolls=rolls,
        total=result.total,
        detail=result.result,
    )


@tool
def dice_roller(expression: str, label: str = "") -> str:
    """Roll dice secretly (hidden roll / 暗骰). Only use this for secret checks
    where the player should NOT see the result (e.g. secret Perception, Recall Knowledge).

    For normal checks (attacks, skill checks, saves), use request_player_roll instead.

    Args:
        expression: Dice expression, e.g. "1d20+7", "2d6+3", "4d6kh3".
        label: What check this is for, e.g. "察觉检定", "回忆知识". Required.
    """
    result = roll_dice_raw(expression)
    label_text = f" [{label}]" if label else ""
    return f"🔒 暗骰{label_text} {result.expression} → {result.detail} = {result.total}"
