"""Full data backup / restore — packs uploads, characters, skills,
tools, workspace and saves into a single zip archive."""

from __future__ import annotations

import io
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.services.event_log import log_event

router = APIRouter(prefix="/api/backup", tags=["backup"])

_DATA = Path(settings.data_dir)

# Folders to include in backup
_BACKUP_DIRS = [
    ("uploads", _DATA / "uploads"),
    ("characters", _DATA / "characters"),
    ("skills", _DATA / "skills"),
    ("custom_tools", _DATA / "custom_tools"),
    ("saves", _DATA / "saves"),
    ("workspace", _DATA / "workspace"),
]


@router.get("/export")
async def export_backup():
    """Create a zip archive of all user data (uploads, characters,
    skills, tools, workspace, saves)."""

    buf = io.BytesIO()
    manifest: dict[str, Any] = {"version": 1, "folders": {}}

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder_name, folder_path in _BACKUP_DIRS:
            if not folder_path.exists():
                continue
            count = 0
            for root, _dirs, files in os.walk(folder_path):
                for fname in files:
                    full = Path(root) / fname
                    arcname = f"{folder_name}/{full.relative_to(folder_path)}"
                    zf.write(full, arcname)
                    count += 1
            manifest["folders"][folder_name] = count

        # Include the database (game.db) for knowledge base & rules
        db_path = Path(settings.db_path)
        if db_path.exists():
            zf.write(db_path, "game.db")
            manifest["has_db"] = True

        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    buf.seek(0)
    log_event("data", "backup_export", detail=json.dumps(manifest))

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="ttrpg_backup.zip"',
        },
    )


class ImportProgress(BaseModel):
    step: str
    current: int
    total: int
    detail: str = ""


@router.post("/import")
async def import_backup(file: UploadFile = File(...)):
    """Import a backup zip archive, restoring all user data.

    Returns a summary of what was restored.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(400, "File must be a .zip archive")

    content = await file.read()
    if len(content) < 10:
        raise HTTPException(400, "File is empty or too small")

    results: dict[str, Any] = {"restored": {}, "errors": []}

    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            names = zf.namelist()

            for folder_name, folder_path in _BACKUP_DIRS:
                prefix = f"{folder_name}/"
                matching = [n for n in names if n.startswith(prefix) and not n.endswith("/")]
                if not matching:
                    continue

                folder_path.mkdir(parents=True, exist_ok=True)
                count = 0
                for arcname in matching:
                    rel = arcname[len(prefix):]
                    dest = folder_path / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with zf.open(arcname) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                        count += 1
                    except Exception as e:
                        results["errors"].append(f"{arcname}: {e}")

                results["restored"][folder_name] = count

            # Restore game.db if present
            if "game.db" in names:
                db_dest = Path(settings.db_path)
                try:
                    with zf.open("game.db") as src, open(db_dest, "wb") as dst:
                        dst.write(src.read())
                    results["restored"]["game_db"] = True
                except Exception as e:
                    results["errors"].append(f"game.db: {e}")

    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid zip file")

    log_event("data", "backup_import", detail=json.dumps(results))
    return results


@router.get("/stats")
async def backup_stats():
    """Get current data stats for display before backup."""
    stats: dict[str, Any] = {}

    for folder_name, folder_path in _BACKUP_DIRS:
        if folder_path.exists():
            files = list(folder_path.rglob("*"))
            file_list = [f for f in files if f.is_file()]
            stats[folder_name] = {
                "count": len(file_list),
                "size_mb": round(sum(f.stat().st_size for f in file_list) / 1024 / 1024, 2),
            }
        else:
            stats[folder_name] = {"count": 0, "size_mb": 0}

    db_path = Path(settings.db_path)
    if db_path.exists():
        stats["game_db"] = {
            "exists": True,
            "size_mb": round(db_path.stat().st_size / 1024 / 1024, 2),
        }

    return stats
