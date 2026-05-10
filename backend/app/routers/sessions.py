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

    from app.routers.characters import _characters, _raw_data
    sheet = _characters.get(char_id)
    if not sheet:
        raise HTTPException(404, f"Character {char_id} not found")

    if any(t.name == sheet.name for t in state.teammates):
        return {"status": "already_added", "teammates": [t.name for t in state.teammates]}

    from app.agents.graph import _build_character_extras
    extras = _build_character_extras(sheet, state.system_id)

    raw = _raw_data.get(char_id, {})
    raw_sys = raw.get("system", {})

    if state.system_id == "daggerheart":
        res = raw_sys.get("resources", {})
        heritage = raw_sys.get("heritage", {})
        ancestry_name = heritage.get("ancestry", "") if isinstance(heritage, dict) else ""
        new_tm = CharacterSummary(
            name=sheet.name,
            ancestry=ancestry_name,
            character_class=raw_sys.get("class", sheet.character_class),
            level=raw_sys.get("level", sheet.level) or sheet.level,
            hp=res.get("hitPoints", {}).get("value", sheet.hp),
            max_hp=res.get("hitPoints", {}).get("max", sheet.max_hp),
            extras=extras,
        )
    elif state.system_id == "swade":
        new_tm = CharacterSummary(
            name=sheet.name,
            ancestry=raw_sys.get("details", {}).get("species", sheet.ancestry),
            character_class="冒险者",
            level=raw_sys.get("advances", {}).get("value", 0),
            hp=0, max_hp=0,
            extras=extras,
        )
    else:
        new_tm = CharacterSummary(
            name=sheet.name, ancestry=sheet.ancestry,
            character_class=sheet.character_class, level=sheet.level,
            hp=sheet.hp, max_hp=sheet.max_hp,
            extras=extras,
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


class DocumentToggleRequest(BaseModel):
    enabled_doc_ids: list[str] | None = None


@router.get("/{session_id}/documents")
async def get_session_documents(session_id: str):
    """Get the document enable/disable settings for a session."""
    state = get_session(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")

    from app.services.knowledge_base import list_documents
    all_docs = list_documents(system_id=state.system_id)
    enabled = state.enabled_doc_ids

    docs = []
    for d in all_docs:
        docs.append({
            "doc_id": d["doc_id"],
            "title": d.get("title", d.get("filename", "")),
            "filename": d.get("filename", ""),
            "doc_type": d.get("doc_type", ""),
            "chunk_count": d.get("chunk_count", 0),
            "enabled": enabled is None or d["doc_id"] in enabled,
        })
    return {"session_id": session_id, "documents": docs, "mode": "all" if enabled is None else "selective"}


@router.put("/{session_id}/documents")
async def set_session_documents(session_id: str, req: DocumentToggleRequest):
    """Set which documents are enabled for a session.

    Pass enabled_doc_ids=null to enable all documents (default).
    Pass enabled_doc_ids=[] to disable all documents.
    Pass enabled_doc_ids=["id1","id2"] to enable only those.
    """
    state = get_session(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    state = update_session(session_id, enabled_doc_ids=req.enabled_doc_ids)
    return {"session_id": session_id, "enabled_doc_ids": state.enabled_doc_ids}


class StoryPointsRequest(BaseModel):
    delta: int
    reason: str = ""


@router.patch("/{session_id}/story-points")
async def update_story_points(session_id: str, req: StoryPointsRequest):
    """Add or subtract story/hero points for a session."""
    state = get_session(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    new_val = state.story_points + req.delta
    if new_val < 0:
        raise HTTPException(400, "Not enough story points")
    new_val = min(new_val, state.max_story_points)
    state = update_session(session_id, story_points=new_val)
    return {
        "session_id": session_id,
        "story_points": state.story_points,
        "max_story_points": state.max_story_points,
        "delta": req.delta,
        "reason": req.reason,
    }


@router.delete("/{session_id}")
async def remove_session(session_id: str):
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"deleted": True}
