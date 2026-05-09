"""Compendium management API — view/add/delete/import charbuilder data entries."""

from __future__ import annotations

import json
from typing import Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.services import compendium as comp

router = APIRouter(prefix="/api/compendium", tags=["compendium"])


@router.get("/{system}")
async def get_collections(system: str):
    return {"system": system, "collections": comp.list_collections(system)}


@router.get("/{system}/{collection}")
async def get_entries(system: str, collection: str):
    return comp.list_entries(system, collection)


@router.post("/{system}/{collection}")
async def add_entry(system: str, collection: str, body: dict[str, Any]):
    entry = comp.add_entry(system, collection, body)
    return {"ok": True, "entry": entry}


@router.delete("/{system}/{collection}/{slug}")
async def delete_entry(system: str, collection: str, slug: str):
    ok = comp.delete_entry(system, collection, slug)
    if not ok:
        raise HTTPException(404, "Entry not found or is a built-in default")
    return {"deleted": True}


@router.patch("/{system}/{collection}/{slug}")
async def update_entry(system: str, collection: str, slug: str, body: dict[str, Any]):
    result = comp.update_entry(system, collection, slug, body)
    if result is None:
        raise HTTPException(404, "Custom entry not found")
    return {"ok": True, "entry": result}


@router.post("/{system}/import-fvtt")
async def import_fvtt_json(system: str, file: UploadFile = File(...)):
    """Import entries from a FVTT-exported JSON file into the compendium."""
    try:
        raw = await file.read()
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    counts = comp.import_fvtt_json(system, data)
    total = sum(counts.values())
    return {
        "ok": True,
        "imported": total,
        "by_collection": counts,
        "filename": file.filename,
    }


@router.post("/{system}/import-fvtt-batch")
async def import_fvtt_batch(system: str, files: list[UploadFile] = File(...)):
    """Import entries from multiple FVTT-exported JSON files."""
    total_counts: dict[str, int] = {}
    file_results = []
    for f in files:
        try:
            raw = await f.read()
            data = json.loads(raw.decode("utf-8"))
            counts = comp.import_fvtt_json(system, data)
            for col, cnt in counts.items():
                total_counts[col] = total_counts.get(col, 0) + cnt
            file_results.append({"filename": f.filename, "imported": sum(counts.values()), "by_collection": counts})
        except Exception as e:
            file_results.append({"filename": f.filename, "error": str(e)})

    return {
        "ok": True,
        "total_imported": sum(total_counts.values()),
        "by_collection": total_counts,
        "files": file_results,
    }
