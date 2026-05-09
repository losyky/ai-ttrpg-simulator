"""Debug / monitoring API endpoints.

Exposes agent interaction logs, data store stats, session details,
character cards, document info, memory state, and reasoning strategy
for the debug dashboard.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from app.config import settings
from app.services.event_log import get_events, get_stats, clear_events
from app.models.game_state import get_all_sessions, get_all_histories

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/events")
async def list_events(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: str = Query(""),
    session_id: str = Query(""),
    since: float = Query(0),
) -> list[dict[str, Any]]:
    return get_events(
        limit=limit, offset=offset,
        category=category, session_id=session_id,
        since_ts=since,
    )


@router.get("/stats")
async def overview_stats() -> dict[str, Any]:
    return get_stats()


@router.get("/sessions")
async def list_sessions() -> list[dict[str, Any]]:
    sessions = get_all_sessions()
    histories = get_all_histories()
    result = []
    for sid, state in sessions.items():
        history = histories.get(sid, [])
        result.append({
            "session_id": sid,
            "label": state.label,
            "phase": state.phase.value if state.phase else "exploration",
            "round_number": state.round_number,
            "player": state.player.model_dump() if state.player else None,
            "teammate_count": len(state.teammates),
            "message_count": len(history),
            "world_summary": state.world_summary[:200] if state.world_summary else "",
        })
    return result


@router.get("/sessions/{session_id}/history")
async def session_history(session_id: str) -> list[dict[str, Any]]:
    histories = get_all_histories()
    return histories.get(session_id, [])


@router.get("/sessions/prep")
async def list_prep_sessions() -> list[dict[str, Any]]:
    from app.agents.prep_agent import _prep_histories
    result = []
    for sid, history in _prep_histories.items():
        result.append({
            "session_id": sid,
            "message_count": len(history),
            "last_message": history[-1] if history else None,
        })
    return result


@router.get("/data/summary")
async def data_summary() -> dict[str, Any]:
    db_path = Path(settings.db_path)
    result: dict[str, Any] = {
        "db_exists": db_path.exists(),
        "db_size_mb": round(db_path.stat().st_size / 1024 / 1024, 2) if db_path.exists() else 0,
    }

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()

            table_stats = {}
            for (tname,) in tables:
                try:
                    count = conn.execute(f"SELECT count(*) FROM [{tname}]").fetchone()[0]
                    table_stats[tname] = count
                except Exception:
                    table_stats[tname] = -1

            result["tables"] = table_stats
            conn.close()
        except Exception as e:
            result["db_error"] = str(e)

    upload_dir = Path(settings.upload_dir)
    if upload_dir.exists():
        files = list(upload_dir.iterdir())
        result["uploads"] = {
            "file_count": len(files),
            "total_size_mb": round(sum(f.stat().st_size for f in files if f.is_file()) / 1024 / 1024, 2),
        }

    skills_dir = Path(settings.data_dir) / "skills"
    if skills_dir.exists():
        result["skills_count"] = len(list(skills_dir.glob("*.md")))

    tools_dir = Path(settings.data_dir) / "custom_tools"
    if tools_dir.exists():
        result["custom_tools_count"] = len(list(tools_dir.glob("*.json")))

    chroma_dir = Path(settings.chroma_dir)
    result["chroma_exists"] = chroma_dir.exists()

    saves_dir = Path(settings.data_dir) / "saves"
    if saves_dir.exists():
        result["saves_count"] = len(list(saves_dir.glob("*.json")))

    ws_dir = Path(settings.workspace_dir)
    if ws_dir.exists():
        ws_files = list(ws_dir.rglob("*"))
        result["workspace_files"] = len([f for f in ws_files if f.is_file()])

    return result


@router.get("/characters")
async def list_characters() -> list[dict[str, Any]]:
    from app.routers.characters import _characters
    result = []
    for cid, sheet in _characters.items():
        result.append({
            "id": cid,
            "name": sheet.name,
            "level": sheet.level,
            "ancestry": sheet.ancestry,
            "character_class": sheet.character_class,
            "hp": sheet.hp,
            "max_hp": sheet.max_hp,
        })
    return result


@router.get("/documents")
async def list_documents() -> list[dict[str, Any]]:
    from app.services import knowledge_base as kb
    return kb.list_documents()


@router.get("/memories/{session_id}")
async def list_memories(session_id: str) -> dict[str, Any]:
    from app.services.memory_store import get_all_memories
    memories = get_all_memories(session_id)
    return {
        "session_id": session_id,
        "total": sum(len(v) for v in memories.values()),
        "categories": {k: len(v) for k, v in memories.items()},
        "items": memories,
    }


@router.get("/reasoning-strategy")
async def reasoning_strategy() -> dict[str, str]:
    from app.agents.compat import get_reasoning_strategy
    return {"strategy": get_reasoning_strategy()}


@router.get("/checkpoints/{session_id}")
async def get_checkpoint(session_id: str) -> dict[str, Any]:
    from app.agents.graph import get_graph_checkpoint
    cp = await get_graph_checkpoint(session_id)
    if cp is None:
        return {"session_id": session_id, "checkpoint": None}
    return {"session_id": session_id, "checkpoint": cp}


@router.delete("/events")
async def purge_events():
    clear_events()
    return {"status": "cleared"}
