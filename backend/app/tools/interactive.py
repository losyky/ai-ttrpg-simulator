"""Interactive element tools for the narrator agent.

The narrator can use these tools to present rich interactive UI
elements to the player instead of just text responses.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.tools import tool


@tool
def present_choices(prompt: str, options_json: str) -> str:
    """Present multiple-choice options to the player.

    Use this when the player needs to make a decision, pick a direction,
    choose an action, select a target, etc.

    Args:
        prompt: The question or situation description for the player.
        options_json: A JSON array of options. Each option should have
            "id", "label", and optionally "description" and "icon".
            Example: [{"id":"a","label":"进入洞穴","description":"阴暗潮湿","icon":"🕳️"}]
    """
    try:
        options = json.loads(options_json)
    except json.JSONDecodeError:
        return "Error: Invalid JSON for options"

    # Return a special marker that the graph will parse
    result = {
        "__interactive__": True,
        "element_type": "choices",
        "id": f"choice-{uuid.uuid4().hex[:8]}",
        "prompt": prompt,
        "options": options,
    }
    return json.dumps(result, ensure_ascii=False)


@tool
def request_dice_roll(prompt: str, expression: str, dc: int = 0, skill_name: str = "", modifier: int = 0) -> str:
    """Request the player to roll dice.

    Use this when the player needs to make a check, saving throw,
    attack roll, or any other dice roll. The roll will happen on
    the player's side with animation.

    Args:
        prompt: Why the roll is needed, e.g. "你试图撬开锁，请进行巧手检定"
        expression: Dice expression, e.g. "1d20+7"
        dc: Difficulty class (0 if unknown or not applicable)
        skill_name: Name of the skill/check, e.g. "巧手", "察觉", "攻击"
        modifier: Additional modifier to display
    """
    result = {
        "__interactive__": True,
        "element_type": "dice_request",
        "id": f"roll-{uuid.uuid4().hex[:8]}",
        "prompt": prompt,
        "expression": expression,
        "dc": dc,
        "skill_name": skill_name,
        "modifier": modifier,
    }
    return json.dumps(result, ensure_ascii=False)


@tool
def request_player_input(prompt: str, placeholder: str = "", input_type: str = "text") -> str:
    """Ask the player for text input.

    Use this when you need the player to provide a name, describe
    something, write a message, or any freeform text response.

    Args:
        prompt: What information you need from the player.
        placeholder: Placeholder text for the input field.
        input_type: "text" for general text, "number" for numbers, "name" for character names.
    """
    result = {
        "__interactive__": True,
        "element_type": "input_prompt",
        "id": f"input-{uuid.uuid4().hex[:8]}",
        "prompt": prompt,
        "placeholder": placeholder,
        "input_type": input_type,
    }
    return json.dumps(result, ensure_ascii=False)


@tool
def request_duality_roll(prompt: str, trait_name: str = "", modifier: int = 0, dc: int = 0, experience_bonus: bool = False) -> str:
    """Request a Daggerheart Duality Dice roll (2d12 Hope + Fear).

    Use this ONLY in Daggerheart games when a character needs to make an action roll.
    The two d12s will be visually split into Hope die and Fear die.

    Args:
        prompt: Why the roll is needed, e.g. "你试图说服守卫放行，请投二元骰"
        trait_name: Which trait applies, e.g. "Presence", "Agility"
        modifier: Trait modifier (+2/+1/0/-1) plus any bonuses
        dc: Target number (0 if pure Hope/Fear check)
        experience_bonus: True if a relevant Experience applies (+2)
    """
    total_mod = modifier + (2 if experience_bonus else 0)
    expression = f"2d12+{total_mod}" if total_mod > 0 else f"2d12{total_mod}" if total_mod < 0 else "2d12"
    result = {
        "__interactive__": True,
        "element_type": "duality_dice_request",
        "id": f"duality-{uuid.uuid4().hex[:8]}",
        "prompt": prompt,
        "expression": expression,
        "dc": dc,
        "skill_name": trait_name,
        "modifier": total_mod,
        "trait_name": trait_name,
        "experience_bonus": experience_bonus,
    }
    return json.dumps(result, ensure_ascii=False)


@tool
def announce_token_change(token_type: str, change: int, new_total: int, reason: str = "") -> str:
    """Announce a Hope or Fear token change to the player (Daggerheart).

    Use this to visually inform the player when tokens change hands.
    This is purely display — no mechanical effect. Call it AFTER
    determining the duality roll outcome or spending tokens.

    Args:
        token_type: "hope" or "fear"
        change: How many tokens changed (+1, -1, -2, etc.)
        new_total: Current total after change
        reason: Why the change happened, e.g. "二元骰以希望成功" or "消耗 2 Fear 触发敌人伏击"
    """
    result = {
        "__interactive__": True,
        "element_type": "token_update",
        "id": f"token-{uuid.uuid4().hex[:8]}",
        "prompt": reason or f"{'Hope' if token_type == 'hope' else 'Fear'} 代币变动",
        "token_type": token_type,
        "token_change": change,
        "token_total": new_total,
        "token_reason": reason,
    }
    return json.dumps(result, ensure_ascii=False)


def _make_award_story_point(session_id: str):
    """Create a session-bound award_story_point tool."""

    @tool
    def award_story_point(reason: str = "") -> str:
        """Award 1 story/hero point to the player.

        Use this to reward players at key narrative moments: completing a
        major battle, solving a puzzle, excellent roleplay, or reaching
        a story milestone. The point display will update in the sidebar.

        Args:
            reason: Why the point is being awarded, e.g. "精彩的角色扮演" or "成功解开谜题"
        """
        from app.models.game_state import get_session, update_session
        new_total = 0
        state = get_session(session_id)
        if state:
            new_val = min(state.story_points + 1, state.max_story_points)
            update_session(session_id, story_points=new_val)
            new_total = new_val

        result = {
            "__interactive__": True,
            "element_type": "token_update",
            "id": f"sp-{uuid.uuid4().hex[:8]}",
            "prompt": reason or "获得叙事点",
            "token_type": "story_point",
            "token_change": 1,
            "token_total": new_total,
            "token_reason": reason,
        }
        return json.dumps(result, ensure_ascii=False)

    return award_story_point


INTERACTIVE_TOOLS = [present_choices, request_dice_roll, request_player_input]
DAGGERHEART_INTERACTIVE_TOOLS = [present_choices, request_duality_roll, request_player_input, announce_token_change]
SWADE_INTERACTIVE_TOOLS = [present_choices, request_dice_roll, request_player_input]


def get_interactive_tools(system_id: str = "pf2e", session_id: str = "") -> list:
    """Get interactive tools for a system, with session-bound award tool."""
    if system_id == "daggerheart":
        return DAGGERHEART_INTERACTIVE_TOOLS
    base = SWADE_INTERACTIVE_TOOLS if system_id == "swade" else INTERACTIVE_TOOLS
    if session_id:
        return list(base) + [_make_award_story_point(session_id)]
    return list(base)


def parse_interactive_markers(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Extract interactive element markers from tool output text.

    Returns (clean_text, list_of_interactive_elements).
    """
    elements: list[dict[str, Any]] = []

    # Check if the text itself is a JSON interactive marker
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("__interactive__"):
            data.pop("__interactive__", None)
            elements.append(data)
            return "", elements
    except (json.JSONDecodeError, TypeError):
        pass

    return text, elements
