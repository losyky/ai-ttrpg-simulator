"""In-memory session store (upgradeable to Redis / SQLite later)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.schemas import GamePhase, SessionState, CharacterSummary
from app.services.event_log import log_event


_sessions: dict[str, SessionState] = {}
_chat_histories: dict[str, list[dict[str, Any]]] = {}


def create_session(
    player: CharacterSummary | None = None,
    teammates: list[CharacterSummary] | None = None,
    label: str = "",
    system_id: str | None = None,
) -> SessionState:
    sid = uuid.uuid4().hex[:12]
    now = datetime.now()

    if not system_id:
        from app.systems.registry import get_default_system
        system_id = get_default_system().system_id

    state = SessionState(
        session_id=sid,
        system_id=system_id,
        label=label or f"冒险 {now.strftime('%m/%d %H:%M')}",
        created_at=now.isoformat(),
        phase=GamePhase.EXPLORATION,
        player=player,
        teammates=teammates or [],
    )
    _sessions[sid] = state
    _chat_histories[sid] = []
    log_event("session", "created", session_id=sid,
              detail=f"Label: {state.label}, Player: {player.name if player else 'none'}")
    return state


def get_session(session_id: str) -> SessionState | None:
    return _sessions.get(session_id)


def update_session(session_id: str, **kwargs: Any) -> SessionState | None:
    state = _sessions.get(session_id)
    if state is None:
        return None
    for k, v in kwargs.items():
        if hasattr(state, k):
            setattr(state, k, v)
    _sessions[session_id] = state
    return state


def get_history(session_id: str) -> list[dict[str, Any]]:
    return _chat_histories.get(session_id, [])


def append_history(session_id: str, message: dict[str, Any]) -> None:
    _chat_histories.setdefault(session_id, []).append(message)


def delete_session(session_id: str) -> bool:
    removed = _sessions.pop(session_id, None)
    _chat_histories.pop(session_id, None)
    return removed is not None


def get_all_sessions() -> dict[str, SessionState]:
    return dict(_sessions)


def get_all_histories() -> dict[str, list[dict[str, Any]]]:
    return dict(_chat_histories)


# ── Save / Load ──

def _saves_dir() -> Path:
    from app.config import settings
    d = Path(settings.data_dir) / "saves"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_session(session_id: str, label: str = "") -> dict[str, Any]:
    """Serialize full session to a JSON save file and return metadata."""
    from app.services.memory_store import get_memories

    state = _sessions.get(session_id)
    if state is None:
        raise ValueError(f"Session {session_id} not found")

    history = _chat_histories.get(session_id, [])
    memories = get_memories(session_id, limit=200)

    now = datetime.now()
    save_id = f"{session_id}_{now.strftime('%Y%m%d_%H%M%S')}"
    save_data = {
        "save_id": save_id,
        "session_id": session_id,
        "label": label or f"Save {now.strftime('%Y-%m-%d %H:%M')}",
        "created_at": now.isoformat(),
        "version": 2,
        "state": state.model_dump(),
        "chat_history": history,
        "memories": memories,
    }

    path = _saves_dir() / f"{save_id}.json"
    path.write_text(json.dumps(save_data, ensure_ascii=False, indent=2), encoding="utf-8")

    log_event("session", "saved", session_id=session_id,
              detail=f"Saved as {save_id}, {len(history)} messages")
    return {
        "save_id": save_id,
        "label": save_data["label"],
        "created_at": save_data["created_at"],
        "session_id": session_id,
        "message_count": len(history),
    }


def list_saves(system_id: str | None = None) -> list[dict[str, Any]]:
    """List available save files, optionally filtered by system_id."""
    saves = []
    for p in sorted(_saves_dir().glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            state_data = data.get("state", {})
            sid = state_data.get("system_id", "pf2e")
            if system_id and sid != system_id:
                continue
            saves.append({
                "save_id": data["save_id"],
                "label": data.get("label", ""),
                "created_at": data.get("created_at", ""),
                "session_id": data.get("session_id", ""),
                "system_id": sid,
                "message_count": len(data.get("chat_history", [])),
                "player_name": state_data.get("player", {}).get("name", "") if state_data.get("player") else "",
                "phase": state_data.get("phase", "exploration"),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return saves


def load_session(save_id: str) -> SessionState:
    """Load a session from a save file, restoring state + history + memories."""
    from app.services.memory_store import bulk_add_memories, clear_session_memories

    path = _saves_dir() / f"{save_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Save file {save_id} not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    state_data = data["state"]
    history = data.get("chat_history", [])
    memories = data.get("memories", [])

    state = SessionState(**state_data)
    sid = state.session_id

    _sessions[sid] = state
    _chat_histories[sid] = history

    # Restore long-term memories
    if memories:
        clear_session_memories(sid)
        bulk_add_memories(sid, memories)

    log_event("session", "loaded", session_id=sid,
              detail=f"Loaded {save_id}, {len(history)} messages, {len(memories)} memories")
    return state


def delete_save(save_id: str) -> bool:
    path = _saves_dir() / f"{save_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def export_log_markdown(session_id: str) -> str:
    """Export full session as a readable Markdown log."""
    state = _sessions.get(session_id)
    history = _chat_histories.get(session_id, [])

    lines: list[str] = []
    lines.append("# AI 跑团模拟器 — 团 Log")
    lines.append("")
    lines.append(f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**会话 ID**: `{session_id}`")
    if state:
        if state.label:
            lines.append(f"**团名称**: {state.label}")
        lines.append(f"**游戏阶段**: {state.phase.value}")
        if state.player:
            p = state.player
            lines.append(f"**玩家角色**: {p.name} ({p.ancestry} {p.character_class} Lv.{p.level})")
        if state.teammates:
            names = ", ".join(t.name for t in state.teammates)
            lines.append(f"**队友**: {names}")
        lines.append(f"**消息总数**: {len(history)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    role_labels = {
        "user": "🧑 玩家",
        "narrator": "📖 讲述者",
        "referee": "⚖️ 裁决者",
        "teammate": "🤝 队友",
        "system": "⚙️ 系统",
    }

    for i, msg in enumerate(history, 1):
        role = msg.get("role", "system")
        label = role_labels.get(role, role)
        content = msg.get("content", "")
        lines.append(f"### {label}")
        lines.append("")
        lines.append(content)
        lines.append("")

    if state and state.world_summary:
        lines.append("---")
        lines.append("")
        lines.append("## 世界状态摘要")
        lines.append("")
        lines.append(state.world_summary)
        lines.append("")

    return "\n".join(lines)


def export_save_file(save_id: str) -> str | None:
    """Return the raw JSON content of a save file for download."""
    path = _saves_dir() / f"{save_id}.json"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None
