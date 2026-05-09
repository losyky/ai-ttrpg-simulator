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
    """Build a compact memory context string for injection into agent prompts."""
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

    parts = []
    total = 0
    for cat in MEMORY_CATEGORIES:
        items = grouped.get(cat, [])
        if not items:
            continue
        label = cat_labels.get(cat, cat)
        section = f"【{label}】\n" + "\n".join(f"• {t}" for t in items)
        if total + len(section) > max_chars:
            break
        parts.append(section)
        total += len(section)

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


async def extract_and_store_memories(
    session_id: str,
    turn_info: str,
    llm_config: dict[str, str],
) -> int:
    """Use LLM to extract important facts from this turn and store them.

    Called at the end of each turn by the notetaker.
    """
    from app.agents.compat import SafeChatOpenAI as ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    existing = get_memory_context(session_id, max_chars=800)

    prompt = EXTRACT_PROMPT.format(
        existing=existing or "(暂无)",
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

        text = str(response.content).strip()
        # Extract JSON from possible markdown code blocks
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        memories = json.loads(text)
        if isinstance(memories, list) and memories:
            return bulk_add_memories(session_id, memories)
    except (json.JSONDecodeError, IndexError, Exception) as e:
        log_event("error", "memory_extract_fail", session_id=session_id,
                  detail=str(e)[:200])

    return 0
