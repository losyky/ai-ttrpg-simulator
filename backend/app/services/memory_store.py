"""Long-term memory layer using LangGraph InMemoryStore.

Provides structured persistent memory for game sessions that survives
beyond the notetaker's rolling summary.  Memories are categorized into:

- **facts**     : important world facts (NPC names, locations, lore)
- **decisions** : key player decisions and their consequences
- **quests**    : active/completed quests and objectives
- **npcs**      : NPC attitudes, status, relationships
- **items**     : inventory changes, important objects

Each memory is a dict with at least a `text` field and optional metadata.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from langgraph.store.memory import InMemoryStore

from app.services.event_log import log_event

# Global store instance
_store = InMemoryStore()

MEMORY_CATEGORIES = ("facts", "decisions", "quests", "npcs", "items")


def _ns(session_id: str, category: str = "facts") -> tuple[str, str]:
    return (session_id, category)


# ── Write ──

def add_memory(
    session_id: str,
    text: str,
    category: str = "facts",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Store a single memory fact. Returns the memory key."""
    key = uuid.uuid4().hex[:10]
    value = {"text": text, **(metadata or {})}
    _store.put(_ns(session_id, category), key, value)
    log_event("data", "memory_add", session_id=session_id,
              detail=f"[{category}] {text[:100]}")
    return key


def bulk_add_memories(
    session_id: str,
    memories: list[dict[str, Any]],
) -> int:
    """Add multiple memories at once. Each item needs `text` and optional `category`."""
    count = 0
    for m in memories:
        text = m.get("text", "")
        if not text:
            continue
        cat = m.get("category", "facts")
        if cat not in MEMORY_CATEGORIES:
            cat = "facts"
        add_memory(session_id, text, category=cat, metadata=m.get("metadata"))
        count += 1
    return count


# ── Read ──

def get_memories(
    session_id: str,
    category: str = "",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve memories. If category is empty, search all categories."""
    results = []
    cats = [category] if category else list(MEMORY_CATEGORIES)
    for cat in cats:
        items = _store.search(_ns(session_id, cat), limit=limit)
        for item in items:
            results.append({
                "key": item.key,
                "category": cat,
                **item.value,
            })
    return results[:limit]


def get_memory_context(session_id: str, max_chars: int = 1500) -> str:
    """Build a compact memory context string for injection into agent prompts.

    Iterates through all categories and truncates *individual items*
    within the last fitting category so that every category gets
    representation rather than being entirely cut off.
    """
    all_memories = get_memories(session_id, limit=30)
    if not all_memories:
        return ""

    grouped: dict[str, list[str]] = {}
    for m in all_memories:
        cat = m.get("category", "facts")
        grouped.setdefault(cat, []).append(m.get("text", ""))

    cat_labels = {
        "facts": "世界事实",
        "decisions": "关键决策",
        "quests": "任务目标",
        "npcs": "NPC 记录",
        "items": "物品变动",
    }

    parts: list[str] = []
    total = 0
    for cat in MEMORY_CATEGORIES:
        items = grouped.get(cat, [])
        if not items:
            continue
        label = cat_labels.get(cat, cat)
        header = f"【{label}】"
        header_len = len(header) + 1  # +1 for newline

        if total + header_len > max_chars:
            break

        fitting_items: list[str] = []
        section_len = header_len
        for t in items:
            line = f"• {t}"
            if total + section_len + len(line) + 1 > max_chars:
                break
            fitting_items.append(line)
            section_len += len(line) + 1

        if fitting_items:
            parts.append(header + "\n" + "\n".join(fitting_items))
            total += section_len

    if not parts:
        return ""
    return "[长期记忆]\n" + "\n".join(parts)


# ── Delete ──

def delete_memory(session_id: str, category: str, key: str) -> bool:
    try:
        _store.delete(_ns(session_id, category), key)
        return True
    except Exception:
        return False


def get_all_memories(session_id: str) -> dict[str, list[dict[str, Any]]]:
    """Return all memories for a session, grouped by category."""
    result: dict[str, list[dict[str, Any]]] = {}
    for cat in MEMORY_CATEGORIES:
        items = _store.search(_ns(session_id, cat), limit=100)
        if items:
            result[cat] = [{"key": item.key, **item.value} for item in items]
    return result


def clear_session_memories(session_id: str) -> int:
    count = 0
    for cat in MEMORY_CATEGORIES:
        items = _store.search(_ns(session_id, cat), limit=100)
        for item in items:
            _store.delete(_ns(session_id, cat), item.key)
            count += 1
    return count


# ── Memory extraction (called by notetaker) ──

EXTRACT_PROMPT = """\
从以下本轮对话信息中，提取需要长期记住的重要事实。
只提取**新出现的**、**具体的**信息，不要重复已有记忆中的内容。
如果本轮没有值得记录的新信息，返回空数组。

已有记忆:
{existing}

本轮信息:
{turn_info}

请以 JSON 数组格式返回，每项包含 text（简洁描述）和 category（facts/decisions/quests/npcs/items）：
```json
[{{"text": "...", "category": "..."}}, ...]
```
如果没有新信息，返回: []
"""


def _extract_json_array(text: str) -> list[dict]:
    """Robustly extract a JSON array from LLM output.

    Handles: bare JSON, ```json fenced blocks, stray text before/after.
    """
    import re

    text = text.strip()

    # Try bare parse first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try extracting from fenced code block (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        try:
            parsed = json.loads(fence_match.group(1).strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Last resort: find the first [ ... ] substring
    bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
    if bracket_match:
        try:
            parsed = json.loads(bracket_match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    return []


async def extract_and_store_memories(
    session_id: str,
    turn_info: str,
    llm_config: dict[str, str],
    existing_ctx: str | None = None,
) -> int:
    """Use LLM to extract important facts from this turn and store them.

    Args:
        existing_ctx: Pre-fetched memory context string.  When supplied
            the function skips an extra ``get_memory_context`` call.
    """
    from app.agents.compat import SafeChatOpenAI as ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    if existing_ctx is None:
        existing_ctx = get_memory_context(session_id, max_chars=800)

    prompt = EXTRACT_PROMPT.format(
        existing=existing_ctx or "(暂无)",
        turn_info=turn_info[:2000],
    )

    llm = ChatOpenAI(
        model=llm_config.get("model", "gpt-4o"),
        api_key=llm_config.get("api_key", ""),
        base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
        temperature=0.0,
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content="你是一个信息提取助手。只输出 JSON 数组。"),
            HumanMessage(content=prompt),
        ])

        memories = _extract_json_array(str(response.content))
        if memories:
            return bulk_add_memories(session_id, memories)
    except Exception as e:
        log_event("error", "memory_extract_fail", session_id=session_id,
                  detail=str(e)[:200])

    return 0
