"""REST API for the tool registry."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.tool_registry import (
    list_all_tools,
    get_tool,
    create_custom_tool,
    update_custom_tool,
    delete_custom_tool,
    TOOL_CATEGORIES,
)

router = APIRouter(prefix="/api/tools", tags=["tools"])


class CreateToolRequest(BaseModel):
    tool_id: str
    name: str
    description: str
    parameters: dict[str, str] | None = None
    instructions: str = ""
    category: str = "custom"
    shared: bool = False


class UpdateToolRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    parameters: dict[str, str] | None = None
    instructions: str | None = None
    category: str | None = None


@router.get("")
async def list_tools(system_id: str | None = None) -> list[dict[str, Any]]:
    return list_all_tools(system_id=system_id)


@router.get("/categories")
async def get_categories() -> dict[str, str]:
    return TOOL_CATEGORIES


@router.get("/{tool_id}")
async def read_tool(tool_id: str, system_id: str | None = None) -> dict[str, Any]:
    tool = get_tool(tool_id, system_id=system_id)
    if tool is None:
        raise HTTPException(404, "Tool not found")
    return tool


@router.post("", status_code=201)
async def create_tool(req: CreateToolRequest, system_id: str | None = None) -> dict[str, Any]:
    try:
        return create_custom_tool(
            tool_id=req.tool_id,
            name=req.name,
            description=req.description,
            parameters=req.parameters,
            instructions=req.instructions,
            category=req.category,
            system_id=system_id,
            shared=req.shared,
        )
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.put("/{tool_id}")
async def update_tool(tool_id: str, req: UpdateToolRequest, system_id: str | None = None) -> dict[str, Any]:
    try:
        updates = req.model_dump(exclude_none=True)
        result = update_custom_tool(tool_id, updates, system_id=system_id)
        if result is None:
            raise HTTPException(404, "Custom tool not found")
        return result
    except ValueError as e:
        raise HTTPException(403, str(e))


@router.delete("/{tool_id}")
async def remove_tool(tool_id: str, system_id: str | None = None):
    try:
        ok = delete_custom_tool(tool_id, system_id=system_id)
        if not ok:
            raise HTTPException(404, "Custom tool not found")
        return {"status": "deleted", "tool_id": tool_id}
    except ValueError as e:
        raise HTTPException(403, str(e))
