"""Game system registry — manages available game system modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.systems.base import GameSystem

_systems: dict[str, "GameSystem"] = {}
_default_system_id: str = "pf2e"


def _settings_path() -> Path:
    from app.config import settings
    return Path(settings.data_dir) / "system_settings.json"


def _load_persisted_system() -> str | None:
    p = _settings_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("default_system_id")
        except Exception:
            pass
    return None


def _persist_system(system_id: str) -> None:
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"default_system_id": system_id}), encoding="utf-8")


def register(system: "GameSystem") -> None:
    """Register a game system module."""
    _systems[system.system_id] = system


def _init_default() -> None:
    """Load persisted system selection on first access."""
    global _default_system_id
    saved = _load_persisted_system()
    if saved and saved in _systems:
        _default_system_id = saved


def get_system(system_id: str) -> "GameSystem":
    """Get a registered game system by ID."""
    if system_id not in _systems:
        raise KeyError(f"Game system '{system_id}' is not registered. Available: {list(_systems.keys())}")
    return _systems[system_id]


def get_default_system() -> "GameSystem":
    """Get the default game system (used when no session-specific system is set)."""
    return get_system(_default_system_id)


def set_default_system(system_id: str) -> None:
    """Set the default game system ID."""
    global _default_system_id
    if system_id not in _systems:
        raise KeyError(f"Game system '{system_id}' is not registered.")
    _default_system_id = system_id
    _persist_system(system_id)


def list_systems() -> list[dict[str, str]]:
    """List all registered game systems."""
    return [
        {"system_id": s.system_id, "display_name": s.display_name}
        for s in _systems.values()
    ]


def iter_systems():
    """Iterate over all registered game system instances."""
    return _systems.values()


def get_current_system(session_id: str | None = None) -> "GameSystem":
    """Get the game system for the current context.

    Looks up the session's system_id if a session exists; otherwise falls
    back to the default system.
    """
    if session_id:
        from app.models.game_state import get_session
        state = get_session(session_id)
        if state and state.system_id and state.system_id in _systems:
            return _systems[state.system_id]
    return get_default_system()
