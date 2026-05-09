"""Session management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.schemas import (
    SessionCreateRequest,
    SessionState,
    CharacterSummary,
)
from app.models.game_state import (
    create_session,
    get_session,
    delete_session,
    get_all_sessions,
    get_all_histories,
    update_session,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _resolve_teammate_ids(ids: list[str]) -> list[CharacterSummary]:
    """Convert character IDs to CharacterSummary objects."""
    from app.routers.characters import _characters
    teammates: list[CharacterSummary] = []
    for cid in ids:
        sheet = _characters.get(cid)
        if sheet:
            teammates.append(CharacterSummary(
                name=sheet.name,
                ancestry=sheet.ancestry,
                character_class=sheet.character_class,
                level=sheet.level,
                hp=sheet.hp,
                max_hp=sheet.max_hp,
                conditions=[],
            ))
    return teammates


class SessionUpdateRequest(BaseModel):
    label: str | None = None


class TeammateUpdateRequest(BaseModel):
    teammate_ids: list[str] = Field(default_factory=list)


@router.get("", response_model=list[dict[str, Any]])
async def list_sessions(system_id: str | None = None):
    """List active sessions, optionally filtered by system_id."""
    sessions = get_all_sessions()
    histories = get_all_histories()
    result = []
    for sid, state in sessions.items():
        if system_id and state.system_id != system_id:
            continue
        history = histories.get(sid, [])
        result.append({
            "session_id": sid,
            "system_id": state.system_id,
            "label": state.label,
            "created_at": state.created_at,
            "phase": state.phase.value if state.phase else "exploration",
            "round_number": state.round_number,
            "player_name": state.player.name if state.player else "",
            "player_class": state.player.character_class if state.player else "",
            "player_level": state.player.level if state.player else 0,
            "teammate_count": len(state.teammates),
            "teammate_names": [t.name for t in state.teammates],
            "message_count": len(history),
        })
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return result


@router.post("", response_model=SessionState)
async def new_session(req: SessionCreateRequest):
    teammates = _resolve_teammate_ids(req.teammate_ids)
    state = create_session(
        player=req.player_character,
        teammates=teammates,
        label=req.label,
        system_id=req.system_id,
    )
    return state


@router.get("/{session_id}", response_model=SessionState)
async def read_session(session_id: str):
    state = get_session(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    return state


@router.patch("/{session_id}", response_model=SessionState)
async def patch_session(session_id: str, req: SessionUpdateRequest):
    state = get_session(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    updates = {}
    if req.label is not None:
        updates["label"] = req.label
    if updates:
        state = update_session(session_id, **updates)
    return state


@router.put("/{session_id}/teammates", response_model=SessionState)
async def set_teammates(session_id: str, req: TeammateUpdateRequest):
    """Set the teammate list for a session from character IDs."""
    state = get_session(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    teammates = _resolve_teammate_ids(req.teammate_ids)
    state = update_session(session_id, teammates=teammates)
    return state


@router.post("/{session_id}/teammates/add")
async def add_teammate(session_id: str, body: dict[str, Any]):
    """Add a single teammate by character ID."""
    state = get_session(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    char_id = body.get("character_id", "")
    if not char_id:
        raise HTTPException(400, "character_id is required")

    from app.routers.characters import _characters
    sheet = _characters.get(char_id)
    if not sheet:
        raise HTTPException(404, f"Character {char_id} not found")

    if any(t.name == sheet.name for t in state.teammates):
        return {"status": "already_added", "teammates": [t.name for t in state.teammates]}

    new_tm = CharacterSummary(
        name=sheet.name, ancestry=sheet.ancestry,
        character_class=sheet.character_class, level=sheet.level,
        hp=sheet.hp, max_hp=sheet.max_hp, conditions=[],
    )
    updated_list = list(state.teammates) + [new_tm]
    state = update_session(session_id, teammates=updated_list)
    return {"status": "added", "teammates": [t.name for t in state.teammates]}


@router.post("/{session_id}/teammates/remove")
async def remove_teammate(session_id: str, body: dict[str, Any]):
    """Remove a teammate by name."""
    state = get_session(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    name = body.get("name", "")
    if not name:
        raise HTTPException(400, "name is required")
    updated_list = [t for t in state.teammates if t.name != name]
    state = update_session(session_id, teammates=updated_list)
    return {"status": "removed", "teammates": [t.name for t in state.teammates]}


@router.delete("/{session_id}")
async def remove_session(session_id: str):
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"deleted": True}
