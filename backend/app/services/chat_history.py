"""Persistent chat history store for prep and creator agents.

Histories are kept in-memory for speed and backed by JSON files in
``data/chat_histories/{agent_type}/{session_id}.json`` for persistence
across server restarts.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from app.config import settings

log = logging.getLogger(__name__)

_histories: dict[str, dict[str, list[dict[str, str]]]] = {}
_metadata: dict[str, dict[str, dict[str, Any]]] = {}


def _dir(agent_type: str) -> Path:
    d = Path(settings.data_dir) / "chat_histories" / agent_type
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path(agent_type: str) -> Path:
    return _dir(agent_type) / "_meta.json"


def _load_meta(agent_type: str) -> dict[str, dict[str, Any]]:
    if agent_type in _metadata:
        return _metadata[agent_type]
    p = _meta_path(agent_type)
    if p.exists():
        try:
            _metadata[agent_type] = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            _metadata[agent_type] = {}
    else:
        _metadata[agent_type] = {}
    return _metadata[agent_type]


def _save_meta(agent_type: str) -> None:
    p = _meta_path(agent_type)
    p.write_text(json.dumps(_metadata.get(agent_type, {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _load_history(agent_type: str, session_id: str) -> list[dict[str, str]]:
    store = _histories.setdefault(agent_type, {})
    if session_id in store:
        return store[session_id]
    fpath = _dir(agent_type) / f"{session_id}.json"
    if fpath.exists():
        try:
            store[session_id] = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception:
            store[session_id] = []
    else:
        store[session_id] = []
    return store[session_id]


def _save_history(agent_type: str, session_id: str) -> None:
    store = _histories.get(agent_type, {})
    hist = store.get(session_id, [])
    fpath = _dir(agent_type) / f"{session_id}.json"
    fpath.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")


def get_history(agent_type: str, session_id: str) -> list[dict[str, str]]:
    return _load_history(agent_type, session_id)


def append(agent_type: str, session_id: str, role: str, content: str) -> None:
    hist = _load_history(agent_type, session_id)
    hist.append({"role": role, "content": content})
    _save_history(agent_type, session_id)

    meta = _load_meta(agent_type)
    entry = meta.setdefault(session_id, {"created": time.time()})
    entry["updated"] = time.time()
    entry["count"] = len(hist)
    if content:
        entry["last_message"] = content[:120]
    entry["label"] = entry.get("label", "")
    _save_meta(agent_type)


def list_sessions(agent_type: str) -> list[dict[str, Any]]:
    meta = _load_meta(agent_type)
    d = _dir(agent_type)
    for fpath in d.glob("*.json"):
        if fpath.name.startswith("_"):
            continue
        sid = fpath.stem
        if sid not in meta:
            try:
                hist = json.loads(fpath.read_text(encoding="utf-8"))
                meta[sid] = {
                    "created": fpath.stat().st_mtime,
                    "updated": fpath.stat().st_mtime,
                    "count": len(hist),
                    "last_message": hist[-1]["content"][:120] if hist else "",
                    "label": "",
                }
            except Exception:
                continue
    result = []
    for sid, info in meta.items():
        result.append({"session_id": sid, **info})
    result.sort(key=lambda x: x.get("updated", 0), reverse=True)
    return result


def update_session_label(agent_type: str, session_id: str, label: str) -> None:
    meta = _load_meta(agent_type)
    if session_id in meta:
        meta[session_id]["label"] = label
        _save_meta(agent_type)


def delete_session(agent_type: str, session_id: str) -> bool:
    store = _histories.get(agent_type, {})
    store.pop(session_id, None)
    meta = _load_meta(agent_type)
    meta.pop(session_id, None)
    _save_meta(agent_type)
    fpath = _dir(agent_type) / f"{session_id}.json"
    if fpath.exists():
        fpath.unlink()
        return True
    return False
