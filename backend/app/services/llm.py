"""Factory for creating LLM instances from user-provided config."""

from __future__ import annotations

from functools import lru_cache

from app.agents.compat import SafeChatOpenAI as ChatOpenAI

from app.models.schemas import LLMConfig


def build_chat_model(config: LLMConfig, temperature: float = 0.7) -> ChatOpenAI:
    """Build a ChatOpenAI-compatible model from runtime config.

    Because users can supply arbitrary OpenAI-compatible endpoints (e.g.
    DeepSeek, Anthropic via proxy, local Ollama), we always use ChatOpenAI
    with the caller-provided base_url.
    """
    return ChatOpenAI(
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
        temperature=temperature,
        streaming=True,
    )
