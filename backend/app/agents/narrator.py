"""Narrator agent – the main DM that synthesizes everything into narrative."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from .compat import SafeChatOpenAI as ChatOpenAI, parse_tool_calls_from_content, extract_text_without_tool_calls

from app.agents.state import AgentState
from app.agents.prompts import INTENT_ANALYSIS_SYSTEM
from app.systems.registry import get_current_system
from app.models.game_state import get_history
from app.services.knowledge_base import (
    search_documents,
    get_opening_chunks,
    list_documents,
)
from app.services.event_log import log_event
from app.services.memory_store import get_memory_context

log = logging.getLogger(__name__)

_narrator_token_queues: dict[str, asyncio.Queue] = {}


def register_narrator_queue(session_id: str, queue: asyncio.Queue) -> None:
    _narrator_token_queues[session_id] = queue


def unregister_narrator_queue(session_id: str) -> None:
    _narrator_token_queues.pop(session_id, None)


def _build_llm(state: AgentState, temperature: float = 0.8) -> ChatOpenAI:
    return ChatOpenAI(
        model=state["model"],
        api_key=state["api_key"],
        base_url=state["base_url"],
        temperature=temperature,
    )


async def analyze_intent(state: AgentState) -> dict[str, Any]:
    """Determine whether the referee and/or teammates need to act."""
    from app.models.game_state import get_session
    llm = _build_llm(state, temperature=0.0)

    session = get_session(state["session_id"])
    history = get_history(state["session_id"])
    recent = history[-6:] if len(history) > 6 else history

    system = get_current_system(state.get("session_id"))
    context_parts = [
        f"当前规则系统: {system.display_name}",
        f"当前阶段: {state.get('game_phase', 'exploration')}",
    ]
    if session and session.world_summary:
        context_parts.append(f"世界状态: {session.world_summary[:300]}")
    if recent:
        context_parts.append("最近对话:")
        for msg in recent:
            context_parts.append(f"  [{msg['role']}]: {msg['content'][:200]}")

    context = "\n".join(context_parts)

    response = await llm.ainvoke([
        SystemMessage(content=INTENT_ANALYSIS_SYSTEM),
        HumanMessage(content=f"{context}\n\n玩家说: {state['user_message']}"),
    ])

    needs_teammates = False

    try:
        text = response.content
        if isinstance(text, str):
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            parsed = json.loads(text.strip())
            needs_teammates = parsed.get("needs_teammates", False)
    except (json.JSONDecodeError, IndexError):
        pass

    log_event("agent", "intent_analyzed", session_id=state["session_id"],
              agent="narrator",
              detail=f"teammates={needs_teammates}")
    return {
        "needs_teammates": needs_teammates,
    }


def _gather_material_context(state: AgentState) -> str:
    """Gather relevant uploaded material for the narrator.

    Strategy:
    1. If this is early in the conversation (<=3 messages), load opening
       sections of all documents to set the scene.
    2. Search with the user's message.
    3. Also search with key terms from recent conversation history to
       catch broader context.
    """
    history = get_history(state["session_id"])
    is_early_game = len(history) <= 3
    user_msg = state["user_message"]
    all_hits: list[dict] = []
    seen_ids: set[str] = set()

    system = get_current_system(state["session_id"])
    sys_id = system.system_id

    def _add(hits: list[dict]) -> None:
        for h in hits:
            cid = h.get("chunk_id", "")
            if cid not in seen_ids:
                seen_ids.add(cid)
                all_hits.append(h)

    if is_early_game:
        try:
            opening = get_opening_chunks(limit=6, system_id=sys_id)
            _add(opening)
        except Exception:
            pass

    try:
        hits = search_documents(user_msg, limit=3, system_id=sys_id)
        _add(hits)
    except Exception:
        pass

    if len(all_hits) < 4 and history:
        recent_text = " ".join(
            m["content"][:100] for m in history[-4:]
            if m["role"] in ("narrator", "user")
        )
        keywords = _extract_search_terms(recent_text, user_msg)
        for kw in keywords[:3]:
            try:
                hits = search_documents(kw, limit=2, system_id=sys_id)
                _add(hits)
            except Exception:
                pass
            if len(all_hits) >= 6:
                break

    if not all_hits:
        return ""

    parts = []
    for h in all_hits[:6]:
        section = h.get("section", "")
        content = h.get("content", "")[:800]
        parts.append(f"[{section}]\n{content}")

    return "[参考资料 — 请根据以下剧本内容展开叙事]\n" + "\n---\n".join(parts)


def _extract_search_terms(context: str, current_msg: str) -> list[str]:
    """Extract potential search terms from conversation context.

    Simple heuristic: pull proper nouns, location names, character names
    that appear in the text. For Chinese text, extract 2-4 character
    sequences that look like names or terms.
    """
    import re
    terms: list[str] = []

    # English proper nouns (capitalized words)
    en_names = re.findall(r'\b[A-Z][a-z]{2,}\b', context)
    terms.extend(list(set(en_names))[:3])

    # Chinese terms: look for quoted strings or terms after common markers
    cn_quoted = re.findall(r'[「」""《》【】](.{2,8}?)[「」""《》【】]', context)
    terms.extend(cn_quoted[:3])

    # Named entities after common Chinese markers
    cn_names = re.findall(r'(?:在|到|去|叫|是|找|向|位于)(.{2,4})', context)
    terms.extend(list(set(cn_names))[:3])

    return [t for t in terms if t and t != current_msg and len(t) >= 2]


def _load_supplementary_rules(max_chars: int = 3000) -> str:
    """Load supplementary rule files created by the prep AI."""
    from app.config import settings as _settings
    rules_dir = Path(_settings.data_dir) / "supplementary_rules"
    if not rules_dir.exists():
        return ""
    parts: list[str] = []
    total = 0
    for f in sorted(rules_dir.rglob("*.md")):
        try:
            content = f.read_text(encoding="utf-8")
            if total + len(content) > max_chars:
                content = content[:max_chars - total]
            parts.append(f"### {f.stem}\n{content}")
            total += len(content)
            if total >= max_chars:
                break
        except Exception:
            continue
    if not parts:
        return ""
    return "[补充规则 — 由团外助手创建]\n" + "\n\n---\n\n".join(parts)


async def narrate(state: AgentState) -> dict[str, Any]:
    """Generate the final narrative response for the player.

    Uses tool calling to optionally embed interactive elements
    (choices, dice requests, input prompts) in the response.
    Streams tokens to the registered queue for real-time output.
    """
    from langchain_core.messages import ToolMessage, AIMessage
    from app.tools.interactive import (
        INTERACTIVE_TOOLS, DAGGERHEART_INTERACTIVE_TOOLS, SWADE_INTERACTIVE_TOOLS,
        parse_interactive_markers,
    )
    from app.tools.party_manage import PARTY_TOOLS

    session_id = state["session_id"]
    queue = _narrator_token_queues.get(session_id)

    system = get_current_system(session_id)
    system_tools = system.get_tools().get("narrator", [])

    if system.system_id == "daggerheart":
        interactive_tools = DAGGERHEART_INTERACTIVE_TOOLS
    elif system.system_id == "swade":
        interactive_tools = SWADE_INTERACTIVE_TOOLS
    else:
        interactive_tools = INTERACTIVE_TOOLS

    from app.services.tool_registry import load_custom_langchain_tools
    custom_tools = load_custom_langchain_tools(system.system_id)

    all_tools = interactive_tools + PARTY_TOOLS + system_tools + custom_tools
    llm = _build_llm(state)
    llm_with_tools = llm.bind_tools(all_tools)
    tool_map = {t.name: t for t in all_tools}

    context_parts: list[str] = []

    rules_ctx = _load_supplementary_rules()
    if rules_ctx:
        context_parts.append(rules_ctx)

    player_ctx = state.get("player_context", "")
    if player_ctx:
        context_parts.append(player_ctx)

    material_ctx = _gather_material_context(state)
    if material_ctx:
        context_parts.append(material_ctx)

    memory_ctx = get_memory_context(session_id, max_chars=1200)
    if memory_ctx:
        context_parts.append(memory_ctx)

    if state.get("notetaker_output"):
        context_parts.append(f"[世界状态摘要]\n{state['notetaker_output']}")

    referee_out = state.get("referee_output", "")
    if referee_out and referee_out.strip() not in ("", "无需进行检定。", "无需进行检定"):
        context_parts.append(f"[规则判定结果]\n{referee_out}")

    dice_results = state.get("dice_results", [])
    if dice_results:
        dice_text = "\n".join(
            f"🎲 {d['expression']} = {d['total']} ({d['detail']})"
            for d in dice_results
        )
        context_parts.append(f"[骰子结果]\n{dice_text}")

    if state.get("teammate_output"):
        context_parts.append(f"[队友行动]\n{state['teammate_output']}")

    context = "\n\n".join(context_parts)

    NARRATOR_SYSTEM = system.get_prompts()["narrator"]
    msgs: list = [SystemMessage(content=NARRATOR_SYSTEM)]

    history = get_history(session_id)
    recent = history[-12:]
    for msg in recent:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content:
            continue
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role in ("narrator", "referee", "teammate"):
            msgs.append(AIMessage(content=content))

    prompt = state["user_message"]
    if context:
        prompt = f"[以下是本轮的参考资料和状态信息，你必须参考这些剧本资料来推进叙事]\n{context}\n\n---\n玩家说: {state['user_message']}"

    msgs.append(HumanMessage(content=prompt))

    interactive_elements: list[dict] = []
    full_text_parts: list[str] = []
    INTERACTIVE_TOOL_NAMES = {
        "present_choices", "request_dice_roll", "request_player_input",
        "request_duality_roll",
    }
    BLOCKING_ELEMENT_TYPES = {"choices", "dice_request", "input_prompt", "duality_dice_request"}

    async def _push_token(token: str) -> None:
        if queue:
            try:
                queue.put_nowait(token)
            except asyncio.QueueFull:
                pass

    # Phase 1: Use ainvoke with tools for reliable tool-call detection
    needs_final_stream = True
    for iteration in range(3):
        try:
            response = await llm_with_tools.ainvoke(msgs)
        except Exception as exc:
            log.error("[narrator] LLM error iteration=%d: %s", iteration, exc, exc_info=True)
            break

        msgs.append(response)

        tool_calls = response.tool_calls or []
        full_content = str(response.content) if response.content else ""

        if not tool_calls and full_content:
            fallback_calls = parse_tool_calls_from_content(full_content)
            if fallback_calls:
                tool_calls = fallback_calls
                log_event("tool", "narrator_fallback_parse", session_id=session_id,
                          agent="narrator",
                          detail=f"Parsed {len(fallback_calls)} tool call(s) from content")

        if full_content:
            text = full_content
            if tool_calls and not response.tool_calls:
                text = extract_text_without_tool_calls(text)
            clean, elems = parse_interactive_markers(text)
            if clean:
                full_text_parts.append(clean)
                await _push_token(clean)
            interactive_elements.extend(elems)

        if not tool_calls:
            needs_final_stream = False
            break

        for tc in tool_calls:
            has_existing_blocking = any(
                e.get("element_type") in BLOCKING_ELEMENT_TYPES
                for e in interactive_elements
            )
            if tc["name"] in INTERACTIVE_TOOL_NAMES and has_existing_blocking:
                msgs.append(ToolMessage(
                    content="已有一个交互元素，每次回复只允许一个交互操作。请在叙事文本中自然收尾。",
                    tool_call_id=tc["id"],
                ))
                continue

            tool_fn = tool_map.get(tc["name"])
            if tool_fn:
                try:
                    result = await tool_fn.ainvoke(tc["args"])
                    log_event("tool", "narrator_tool_call", session_id=session_id,
                              agent="narrator", detail=f"{tc['name']}: {str(tc['args'])[:100]}")
                    _, elems = parse_interactive_markers(str(result))
                    interactive_elements.extend(elems)
                    msgs.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
                except Exception as e:
                    msgs.append(ToolMessage(content=f"Error: {e}", tool_call_id=tc["id"]))
            else:
                msgs.append(ToolMessage(content="Unknown tool", tool_call_id=tc["id"]))

        has_blocking_interactive = any(
            e.get("element_type") in ("choices", "dice_request", "input_prompt", "duality_dice_request")
            for e in interactive_elements
        )
        if has_blocking_interactive:
            needs_final_stream = True
            break

    # Phase 2: Stream the final narrative text token-by-token (no tools)
    if needs_final_stream:
        if queue:
            try:
                queue.put_nowait({"__thinking__": "生成中..."})
            except asyncio.QueueFull:
                pass
        try:
            stream_content = ""
            async for chunk in llm.astream(msgs):
                if chunk.content:
                    token = str(chunk.content)
                    stream_content += token
                    await _push_token(token)
            if stream_content:
                clean, extra_elems = parse_interactive_markers(stream_content)
                if clean:
                    full_text_parts.append(clean)
                interactive_elements.extend(extra_elems)
        except Exception as exc:
            log.warning("[narrator] streaming fallback error: %s", exc)

    log_event("chat", "narrator_output", session_id=session_id,
              agent="narrator",
              detail="\n\n".join(full_text_parts)[:300],
              data={"interactive_count": len(interactive_elements), "text_length": len("\n\n".join(full_text_parts))})

    return {
        "narrator_response": "\n\n".join(full_text_parts),
        "interactive_elements": interactive_elements,
    }
