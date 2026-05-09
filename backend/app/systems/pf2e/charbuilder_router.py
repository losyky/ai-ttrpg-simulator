"""PF2e Character Builder REST API — powers the frontend character creation wizard.

Provides search, detail, validation, and assembly endpoints for
interactive character building.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.systems.pf2e.charbuilder_db import (
    search_ancestries,
    search_heritages,
    search_backgrounds,
    search_classes,
    search_feats,
    search_spells,
    search_equipment,
    get_class_by_slug,
    get_ancestry_by_slug,
    get_background_by_slug,
    get_feat_by_name,
    get_stats,
)
from app.systems.pf2e.build_validator import validate_build, compute_ability_scores
from app.systems.pf2e.markup import render_fvtt_markup

router = APIRouter(prefix="/api/pf2e/charbuilder", tags=["pf2e-charbuilder"])


# ── Search Endpoints ──

@router.get("/ancestries")
async def list_ancestries(q: str = "", lang: str = "cn"):
    """Search ancestries with optional Chinese translations."""
    results = search_ancestries(q)
    if lang == "cn":
        for r in results:
            if r.get("name_cn"):
                r["display_name"] = f"{r['name_cn']} {r['name']}"
            else:
                r["display_name"] = r["name"]
            if r.get("description_cn"):
                r["description_rendered"] = render_fvtt_markup(r["description_cn"])
    return {"count": len(results), "results": results}


@router.get("/ancestries/{slug}")
async def get_ancestry_detail(slug: str, lang: str = "cn"):
    """Get full ancestry details including boosts/flaws."""
    result = get_ancestry_by_slug(slug)
    if not result:
        raise HTTPException(404, f"Ancestry '{slug}' not found")
    if lang == "cn" and result.get("name_cn"):
        result["display_name"] = f"{result['name_cn']} {result['name']}"
    else:
        result["display_name"] = result["name"]
    if result.get("description_cn"):
        result["description_rendered"] = render_fvtt_markup(result["description_cn"])
    elif result.get("description"):
        result["description_rendered"] = result["description"]
    return result


@router.get("/heritages")
async def list_heritages(
    ancestry_slug: str = "",
    q: str = "",
    lang: str = "cn",
):
    """Search heritages, optionally filtered by ancestry."""
    results = search_heritages(ancestry_slug=ancestry_slug)
    if q:
        q_lower = q.lower()
        results = [r for r in results if q_lower in r.get("name", "").lower() or q_lower in r.get("name_cn", "").lower()]
    if lang == "cn":
        for r in results:
            if r.get("name_cn"):
                r["display_name"] = f"{r['name_cn']} {r['name']}"
            else:
                r["display_name"] = r["name"]
    return {"count": len(results), "results": results}


@router.get("/backgrounds")
async def list_backgrounds(q: str = "", skill: str = "", lang: str = "cn"):
    """Search backgrounds."""
    results = search_backgrounds(query=q, skill=skill)
    if lang == "cn":
        for r in results:
            if r.get("name_cn"):
                r["display_name"] = f"{r['name_cn']} {r['name']}"
            else:
                r["display_name"] = r["name"]
    return {"count": len(results), "results": results}


@router.get("/backgrounds/{slug}")
async def get_background_detail(slug: str, lang: str = "cn"):
    """Get full background details."""
    result = get_background_by_slug(slug)
    if not result:
        raise HTTPException(404, f"Background '{slug}' not found")
    if lang == "cn" and result.get("name_cn"):
        result["display_name"] = f"{result['name_cn']} {result['name']}"
    else:
        result["display_name"] = result["name"]
    if result.get("description_cn"):
        result["description_rendered"] = render_fvtt_markup(result["description_cn"])
    return result


@router.get("/classes")
async def list_classes(q: str = "", lang: str = "cn"):
    """Search classes."""
    results = search_classes(q)
    if lang == "cn":
        for r in results:
            if r.get("name_cn"):
                r["display_name"] = f"{r['name_cn']} {r['name']}"
            else:
                r["display_name"] = r["name"]
    return {"count": len(results), "results": results}


@router.get("/classes/{slug}")
async def get_class_detail(slug: str, lang: str = "cn"):
    """Get full class details including progression table."""
    result = get_class_by_slug(slug)
    if not result:
        raise HTTPException(404, f"Class '{slug}' not found")
    if lang == "cn" and result.get("name_cn"):
        result["display_name"] = f"{result['name_cn']} {result['name']}"
    else:
        result["display_name"] = result["name"]
    if result.get("description_cn"):
        result["description_rendered"] = render_fvtt_markup(result["description_cn"])
    return result


@router.get("/feats")
async def list_feats(
    category: str = "",
    level_max: int = 0,
    class_slug: str = "",
    ancestry_slug: str = "",
    q: str = "",
    limit: int = Query(30, ge=1, le=200),
    lang: str = "cn",
):
    """Search feats with multiple filter dimensions."""
    results = search_feats(
        category=category,
        level_max=level_max,
        class_slug=class_slug,
        ancestry_slug=ancestry_slug,
        query=q,
        limit=limit,
    )
    if lang == "cn":
        for r in results:
            if r.get("name_cn"):
                r["display_name"] = f"{r['name_cn']} {r['name']}"
            else:
                r["display_name"] = r["name"]
    return {"count": len(results), "results": results}


@router.get("/spells")
async def list_spells(
    tradition: str = "",
    rank_max: int = 0,
    q: str = "",
    limit: int = Query(30, ge=1, le=200),
    lang: str = "cn",
):
    """Search spells by tradition and rank."""
    results = search_spells(
        tradition=tradition,
        rank_max=rank_max,
        query=q,
        limit=limit,
    )
    if lang == "cn":
        for r in results:
            if r.get("name_cn"):
                r["display_name"] = f"{r['name_cn']} {r['name']}"
            else:
                r["display_name"] = r["name"]
    return {"count": len(results), "results": results}


@router.get("/equipment")
async def list_equipment(
    item_type: str = "",
    category: str = "",
    q: str = "",
    limit: int = Query(30, ge=1, le=200),
    lang: str = "cn",
):
    """Search equipment."""
    results = search_equipment(
        item_type=item_type,
        category=category,
        query=q,
        limit=limit,
    )
    if lang == "cn":
        for r in results:
            if r.get("name_cn"):
                r["display_name"] = f"{r['name_cn']} {r['name']}"
            else:
                r["display_name"] = r["name"]
    return {"count": len(results), "results": results}


@router.get("/skills")
async def list_skills():
    """Return the PF2e skill list with translations."""
    from app.systems.pf2e.system import PF2E_SKILLS
    return {"skills": PF2E_SKILLS}


@router.get("/i18n")
async def get_i18n_labels():
    """Return PF2e UI label translations (abilities, skills, etc.)."""
    return {
        "abilities": {
            "str": "力量", "dex": "敏捷", "con": "体质",
            "int": "智力", "wis": "感知", "cha": "魅力",
        },
        "skills": {
            "acrobatics": "特技", "arcana": "奥法", "athletics": "运动",
            "crafting": "手艺", "deception": "欺骗", "diplomacy": "交涉",
            "intimidation": "威吓", "lore": "学识", "medicine": "医疗",
            "nature": "自然", "occultism": "神秘", "performance": "表演",
            "religion": "宗教", "society": "社群", "stealth": "隐秘",
            "survival": "生存", "thievery": "贼活", "perception": "察觉",
        },
        "sizes": {
            "tiny": "超小型", "sm": "小型", "med": "中型",
            "lg": "大型", "huge": "超大型", "grg": "巨型",
        },
        "rarities": {
            "common": "普通", "uncommon": "非常见",
            "rare": "稀有", "unique": "独特",
        },
        "item_types": {
            "weapon": "武器", "armor": "护甲", "equipment": "装备",
            "consumable": "消耗品", "shield": "盾牌", "treasure": "宝物",
            "kit": "工具包", "backpack": "背包",
        },
        "feat_categories": {
            "ancestry": "族裔专长", "class": "职业专长",
            "skill": "技能专长", "general": "通用专长",
            "archetype": "变体专长", "bonus": "奖励专长",
        },
        "labels": {
            "boost": "属性提升", "flaw": "缺陷", "free": "自由点",
            "hp": "生命值", "speed": "速度", "vision": "视觉",
            "level": "等级", "traits": "特征", "prerequisites": "先决条件",
            "description": "描述", "source": "来源",
        },
    }


@router.get("/stats")
async def get_db_statistics():
    """Get charbuilder database statistics."""
    return get_stats()


# ── Computation Endpoints ──

class ComputeAbilitiesRequest(BaseModel):
    ancestry_boosts: list[str] = []
    ancestry_flaws: list[str] = []
    background_boosts: list[str] = []
    class_boost: str = ""
    free_boosts: list[str] = []
    level_boosts: dict[str, list[str]] = {}
    voluntary_flaws: list[str] = []


@router.post("/compute-abilities")
async def compute_abilities(req: ComputeAbilitiesRequest):
    """Compute final ability scores from boost/flaw selections.
    
    Applies the PF2e half-boost rule (mod >= 4 -> +0.5 instead of +1).
    """
    build = {
        "level": max(int(k) for k in req.level_boosts.keys()) if req.level_boosts else 1,
        "ancestry": req.ancestry_boosts[0] if len(req.ancestry_boosts) == 1 else "",
        "ancestry_boosts": req.ancestry_boosts,
        "ancestry_flaws": req.ancestry_flaws,
        "background_boosts": req.background_boosts,
        "class_boost": req.class_boost,
        "free_boosts": req.free_boosts,
        "voluntary_flaws": req.voluntary_flaws,
    }
    
    # Merge level boosts
    for level_str, boosts in req.level_boosts.items():
        build[f"level_{level_str}_boosts"] = boosts
    
    scores = compute_ability_scores(build)
    return {"abilities": scores}


class ValidateBuildRequest(BaseModel):
    build: dict[str, Any]


@router.post("/validate")
async def validate_character_build(req: ValidateBuildRequest):
    """Validate a character build against PF2e rules."""
    result = validate_build(req.build)
    return {
        "valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
    }


class AssembleBuildRequest(BaseModel):
    build: dict[str, Any]
    name: str = "New Character"
    save: bool = True


@router.post("/assemble")
async def assemble_character(req: AssembleBuildRequest):
    """Assemble a character build into FVTT Actor JSON and optionally save."""
    from app.systems.pf2e.tools import cb_assemble_character
    
    build_json = json.dumps(req.build, ensure_ascii=False)
    result = cb_assemble_character.invoke({"build_json": build_json, "character_name": req.name})
    
    return {"result": result}
