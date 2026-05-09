"""Skills REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.skill_manager import (
    list_skills,
    get_skill,
    create_skill,
    update_skill,
    delete_skill,
)

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillCreateRequest(BaseModel):
    skill_id: str
    title: str
    description: str
    instructions: str
    examples: str = ""
    shared: bool = False


class SkillUpdateRequest(BaseModel):
    content: str


@router.get("")
async def api_list_skills(system_id: str | None = None):
    return list_skills(system_id=system_id)


@router.get("/{skill_id}")
async def api_get_skill(skill_id: str, system_id: str | None = None):
    data = get_skill(skill_id, system_id=system_id)
    if not data:
        raise HTTPException(404, f"Skill '{skill_id}' not found")
    return data


@router.post("")
async def api_create_skill(req: SkillCreateRequest, system_id: str | None = None):
    return create_skill(
        skill_id=req.skill_id,
        title=req.title,
        description=req.description,
        instructions=req.instructions,
        examples=req.examples,
        system_id=system_id,
        shared=req.shared,
    )


@router.put("/{skill_id}")
async def api_update_skill(skill_id: str, req: SkillUpdateRequest, system_id: str | None = None):
    ok = update_skill(skill_id, req.content, system_id=system_id)
    if not ok:
        raise HTTPException(404, f"Skill '{skill_id}' not found")
    return {"status": "updated", "skill_id": skill_id}


@router.delete("/{skill_id}")
async def api_delete_skill(skill_id: str, system_id: str | None = None):
    ok = delete_skill(skill_id, system_id=system_id)
    if not ok:
        raise HTTPException(404, f"Skill '{skill_id}' not found")
    return {"status": "deleted", "skill_id": skill_id}
