"""Workspace file browser API — exposes the AI workspace folder
to the frontend for browsing, editing, and management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

_WS_BASE = Path(settings.workspace_dir)


def _ws_root(system_id: str | None = None) -> Path:
    if system_id:
        d = _WS_BASE / system_id
    else:
        d = _WS_BASE
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe(relative: str, system_id: str | None = None) -> Path:
    root = _ws_root(system_id)
    target = (root / relative).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise HTTPException(403, "Path escapes workspace")
    return target


@router.get("/list")
async def list_files(path: str = "", system_id: str | None = None) -> list[dict[str, Any]]:
    root = _ws_root(system_id)
    target = _safe(path, system_id) if path else root
    if not target.exists() or not target.is_dir():
        return []
    result = []
    for item in sorted(target.iterdir()):
        info: dict[str, Any] = {
            "name": item.name,
            "path": str(item.relative_to(root)),
            "is_dir": item.is_dir(),
        }
        if item.is_file():
            info["size"] = item.stat().st_size
        result.append(info)
    return result


@router.get("/read")
async def read_file(path: str, system_id: str | None = None) -> dict[str, Any]:
    target = _safe(path, system_id)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File not found")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "Binary file cannot be read as text")
    return {"path": path, "content": content, "size": len(content)}


class WriteRequest(BaseModel):
    path: str
    content: str
    system_id: str | None = None


@router.post("/write")
async def write_file(req: WriteRequest):
    target = _safe(req.path, req.system_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding="utf-8")
    return {"path": req.path, "size": len(req.content)}


@router.delete("/delete")
async def delete_file(path: str, system_id: str | None = None):
    import shutil
    target = _safe(path, system_id)
    if not target.exists():
        raise HTTPException(404, "Not found")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"deleted": path}


@router.post("/upload")
async def upload_to_workspace(
    path: str = "",
    system_id: str | None = None,
    file: UploadFile = File(...),
):
    """Upload a file directly into the workspace folder."""
    root = _ws_root(system_id)
    dest_dir = _safe(path, system_id) if path else root
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = file.filename or "uploaded_file"
    dest = dest_dir / filename
    content = await file.read()
    dest.write_bytes(content)
    return {"path": str(dest.relative_to(root)), "size": len(content)}
