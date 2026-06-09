"""LangChain tool for scene/portrait image generation with per-session rate limiting."""

from __future__ import annotations

from langchain_core.tools import tool

# Turn counter keyed by session_id; reset on each new graph run via init_turn_counter()
_session_image_turns: dict[str, int] = {}  # session_id -> turns since last generation


def init_turn_counter(session_id: str) -> None:
    """Called at the start of each new conversation turn (in run_graph)."""
    _session_image_turns.setdefault(session_id, 0)
    _session_image_turns[session_id] += 1


def reset_turn_counter(session_id: str) -> None:
    """Reset counter to 0 after a successful generation."""
    _session_image_turns[session_id] = 0


def get_turn_counter(session_id: str) -> int:
    return _session_image_turns.get(session_id, 0)


# Sentinel prefix returned when the rate limit is not yet met
_CONFIRM_PREFIX = "__IMAGE_CONFIRM__:"


def make_image_gen_tool(
    session_id: str,
    api_key: str,
    model: str,
    base_url: str,
    style_prefix: str,
    turns_per_image: int,
    *,
    force: bool = False,
):
    """Return a bound LangChain tool that generates images for *session_id*.

    If the per-session turn counter has not yet reached *turns_per_image*,
    the tool returns a ``__IMAGE_CONFIRM__:`` sentinel with the prompt so the
    narrator node can convert it into an ``image_confirm`` interactive chunk
    instead of blocking until a real generation completes.

    Args:
        force: If True, bypass the rate limit (used when the player confirmed).
    """

    @tool
    async def generate_scene_image(prompt: str) -> str:
        """Generate an image for the current scene, NPC, or location.

        Use this tool at key narrative moments such as:
        - When a new scene or location is first described
        - When an important NPC appears for the first time
        - After a significant battle or story beat

        The prompt should be a vivid visual description in English, e.g.:
        "a misty mountain pass at dawn, ruined stone gate, fantasy art, cinematic"

        Args:
            prompt: Visual description of the scene or character in English.
        """
        turns = get_turn_counter(session_id)
        if not force and turns_per_image > 0 and turns < turns_per_image:
            # Not enough turns yet — return sentinel for player confirmation
            return f"{_CONFIRM_PREFIX}{prompt}"

        # Enough turns or forced — generate for real
        from app.services.image_gen import generate_image
        try:
            local_url = await generate_image(
                prompt,
                api_key=api_key,
                session_id=session_id,
                style_prefix=style_prefix,
                model=model,
                base_url=base_url,
            )
            reset_turn_counter(session_id)
            return f"__IMAGE_URL__:{local_url}"
        except Exception as exc:
            return f"图片生成失败：{exc}"

    return generate_scene_image


def is_image_url_result(result: str) -> tuple[bool, str]:
    """Return (True, url) if result is an image URL sentinel."""
    if result.startswith("__IMAGE_URL__:"):
        return True, result[len("__IMAGE_URL__:"):]
    return False, ""


def is_image_confirm_result(result: str) -> tuple[bool, str]:
    """Return (True, prompt) if result is an image-confirm sentinel."""
    if result.startswith(_CONFIRM_PREFIX):
        return True, result[len(_CONFIRM_PREFIX):]
    return False, ""
