"""Centralized event logging for agent interactions and data operations.

Records all inter-agent communications, tool calls, data store changes,
and session events into an in-memory ring buffer that the debug dashboard
can query in real time.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from datetime import datetime
from typing import Any

# Ring buffer — keeps the most recent N events
_MAX_EVENTS = 2000
_events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)

# Per-session event indices for quick filtering
_session_events: dict[str, list[str]] = {}


def log_event(
    category: str,
    action: str,
    *,
    session_id: str = "",
    agent: str = "",
    detail: str = "",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record an event.

    Categories:
      - agent    : agent node execution (analyze_intent, referee, narrate, etc.)
      - tool     : tool invocation (dice_roller, rulebook_search, etc.)
      - llm      : LLM API call (model, tokens, latency)
      - data     : data store operation (db insert, fts rebuild, etc.)
      - session  : session lifecycle (create, delete)
      - chat     : chat message (user input, narrator output)
      - interactive : interactive element sent/received
      - error    : any error
    """
    event = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "ts_unix": time.time(),
        "category": category,
        "action": action,
        "session_id": session_id,
        "agent": agent,
        "detail": detail[:500] if detail else "",
        "data": data or {},
    }
    _events.append(event)

    if session_id:
        _session_events.setdefault(session_id, []).append(event["id"])

    return event


def get_events(
    limit: int = 100,
    offset: int = 0,
    category: str = "",
    session_id: str = "",
    since_ts: float = 0,
) -> list[dict[str, Any]]:
    """Query events with optional filters."""
    filtered = list(_events)

    if since_ts > 0:
        filtered = [e for e in filtered if e["ts_unix"] > since_ts]
    if category:
        filtered = [e for e in filtered if e["category"] == category]
    if session_id:
        filtered = [e for e in filtered if e["session_id"] == session_id]

    # Newest first
    filtered.reverse()
    return filtered[offset : offset + limit]


def get_stats() -> dict[str, Any]:
    """Summary statistics for the debug dashboard."""
    all_events = list(_events)

    category_counts: dict[str, int] = {}
    agent_counts: dict[str, int] = {}
    sessions_seen: set[str] = set()

    for e in all_events:
        cat = e["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if e["agent"]:
            agent_counts[e["agent"]] = agent_counts.get(e["agent"], 0) + 1
        if e["session_id"]:
            sessions_seen.add(e["session_id"])

    return {
        "total_events": len(all_events),
        "max_events": _MAX_EVENTS,
        "category_counts": category_counts,
        "agent_counts": agent_counts,
        "active_sessions": len(sessions_seen),
        "sessions": list(sessions_seen),
    }


def clear_events() -> None:
    _events.clear()
    _session_events.clear()
