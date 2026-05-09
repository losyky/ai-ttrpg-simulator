"""Memory management API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.memory_store import (
    get_memories,
    add_memory,
    delete_memory,
    clear_session_memories,
    MEMORY_CATEGORIES,
)

router = APIRouter(prefix="/api/memories", tags=["memories"])


class AddMemoryRequest(BaseModel):
    session_id: str
    text: str
    category: str = "facts"


@router.get("/{session_id}")
async def list_memories(
    session_id: str,
    category: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    return get_memories(session_id, category=category, limit=limit)


@router.post("")
async def create_memory(req: AddMemoryRequest) -> dict[str, str]:
    key = add_memory(req.session_id, req.text, category=req.category)
    return {"key": key, "status": "ok"}


@router.delete("/{session_id}/{category}/{key}")
async def remove_memory(session_id: str, category: str, key: str):
    ok = delete_memory(session_id, category, key)
    return {"deleted": ok}


@router.delete("/{session_id}")
async def clear_memories(session_id: str):
    count = clear_session_memories(session_id)
    return {"cleared": count}


@router.get("/categories/list")
async def list_categories():
    return list(MEMORY_CATEGORIES)
