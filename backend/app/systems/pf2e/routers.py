"""Rule lookup API – exposes the structured PF2e database to the frontend."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.systems.pf2e.ruledb import (
    lookup_by_name,
    lookup_creature,
    fulltext_search,
    list_categories,
    get_stats,
)

router = APIRouter(prefix="/api/pf2e/rules", tags=["pf2e-rules"])


@router.get("/search")
async def search_rules(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    category: str = Query("", description="分类筛选"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search PF2e rules by name or full-text."""
    cat = category if category else None

    # Try exact name match first
    results = lookup_by_name(q, category=cat, limit=limit)
    source = "name_match"

    if not results:
        results = fulltext_search(q, category=cat, limit=limit)
        source = "fulltext"

    return {"source": source, "count": len(results), "results": results}


@router.get("/creatures")
async def search_creatures(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
):
    """Search creatures / NPCs by name."""
    results = lookup_creature(q, limit=limit)
    return {"count": len(results), "results": results}


@router.get("/categories")
async def get_categories():
    """List all available categories and their entry counts."""
    return list_categories()


@router.get("/stats")
async def get_db_stats():
    """Get database statistics."""
    return get_stats()
