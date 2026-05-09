"""Save / Load / Export session endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from app.models.game_state import (
    save_session,
    list_saves,
    load_session,
    delete_save,
    export_log_markdown,
    export_save_file,
    get_session,
    get_history,
)
from app.models.schemas import SessionState

router = APIRouter(prefix="/api/saves", tags=["saves"])


class SaveRequest(BaseModel):
    session_id: str
    label: str = ""


@router.post("")
async def create_save(req: SaveRequest) -> dict[str, Any]:
    """Save the current session state + chat history."""
    try:
        return save_session(req.session_id, req.label)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("")
async def get_saves(system_id: str | None = None) -> list[dict[str, Any]]:
    """List save files, optionally filtered by system_id."""
    return list_saves(system_id=system_id)


@router.post("/{save_id}/load", response_model=SessionState)
async def load_save(save_id: str):
    """Load a session from a save file. Returns the restored SessionState."""
    try:
        return load_session(save_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get("/{save_id}/history")
async def get_save_history(save_id: str) -> list[dict[str, Any]]:
    """Get the chat history from a save file (without loading it)."""
    raw = export_save_file(save_id)
    if raw is None:
        raise HTTPException(404, "Save not found")
    try:
        data = json.loads(raw)
        return data.get("chat_history", [])
    except json.JSONDecodeError:
        raise HTTPException(500, "Corrupted save file")


@router.delete("/{save_id}")
async def remove_save(save_id: str):
    if not delete_save(save_id):
        raise HTTPException(404, "Save not found")
    return {"deleted": True}


@router.get("/{save_id}/download")
async def download_save(save_id: str):
    """Download a save file as JSON."""
    raw = export_save_file(save_id)
    if raw is None:
        raise HTTPException(404, "Save not found")
    return Response(
        content=raw.encode("utf-8"),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{save_id}.json"',
        },
    )


@router.post("/import")
async def import_save(file: UploadFile = File(...)):
    """Import a save file (previously downloaded JSON)."""
    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid save file format")

    required = {"save_id", "state", "chat_history"}
    if not required.issubset(data.keys()):
        raise HTTPException(400, f"Save file missing required fields: {required - data.keys()}")

    state = load_session(data["save_id"])

    from app.config import settings
    from pathlib import Path
    save_dir = Path(settings.data_dir) / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{data['save_id']}.json"
    if not save_path.exists():
        save_path.write_text(content.decode("utf-8"), encoding="utf-8")

    return {
        "save_id": data["save_id"],
        "session_id": state.session_id,
        "message_count": len(data.get("chat_history", [])),
    }


# ── Export log ──

@router.get("/export/log/{session_id}")
async def export_log(session_id: str):
    """Export the session as a readable Markdown log."""
    s = get_session(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")

    md = export_log_markdown(session_id)
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="session-log-{session_id}.md"',
        },
    )


@router.get("/export/log-preview/{session_id}")
async def export_log_preview(session_id: str):
    """Preview the session log as JSON (for in-app display)."""
    s = get_session(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")

    return {
        "session_id": session_id,
        "markdown": export_log_markdown(session_id),
        "message_count": len(get_history(session_id)),
    }
