"""七物语 (SWADE) character builder REST endpoints."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter

router = APIRouter(prefix="/api/swade/charbuilder", tags=["swade-charbuilder"])

SWADE_ATTRIBUTES = [
    {"slug": "agility", "name": "Agility", "name_cn": "灵巧"},
    {"slug": "smarts", "name": "Smarts", "name_cn": "聪慧"},
    {"slug": "spirit", "name": "Spirit", "name_cn": "心魂"},
    {"slug": "strength", "name": "Strength", "name_cn": "力量"},
    {"slug": "vigor", "name": "Vigor", "name_cn": "活力"},
]

SWADE_RACES = [
    {"slug": "human", "name": "Human", "name_cn": "人类", "trait": "+1 自由专长"},
    {"slug": "elf", "name": "Elf", "name_cn": "精灵", "trait": "低光视觉，灵巧 d6 起步"},
    {"slug": "dwarf", "name": "Dwarf", "name_cn": "矮人", "trait": "活力 d6 起步，低光视觉"},
    {"slug": "halfling", "name": "Halfling", "name_cn": "半身人", "trait": "幸运，体型-1"},
    {"slug": "beastkin", "name": "Beastkin", "name_cn": "兽人", "trait": "力量 d6 起步，坚韧+1"},
    {"slug": "dragonborn", "name": "Dragonborn", "name_cn": "龙裔", "trait": "龙息，元素抗性"},
    {"slug": "fairy", "name": "Fairy", "name_cn": "妖精", "trait": "飞行(移速4)，体型-2"},
    {"slug": "undead", "name": "Undead", "name_cn": "亡灵", "trait": "不死者特质"},
    {"slug": "demon", "name": "Demon", "name_cn": "魔族", "trait": "暗元素亲和"},
    {"slug": "angel", "name": "Angel", "name_cn": "天使", "trait": "光元素亲和"},
    {"slug": "construct", "name": "Construct", "name_cn": "人造体", "trait": "不需呼吸/进食"},
]

SWADE_ELEMENTS = [
    {"slug": "fire", "name_cn": "火"},
    {"slug": "ice", "name_cn": "冰"},
    {"slug": "earth", "name_cn": "土"},
    {"slug": "wind", "name_cn": "风"},
    {"slug": "thunder", "name_cn": "雷"},
    {"slug": "light", "name_cn": "光"},
    {"slug": "dark", "name_cn": "暗"},
]

SWADE_RESISTANCE_LEVELS = ["weakness", "normal", "resistance", "immunity"]


@router.get("/attributes")
async def get_attributes():
    return SWADE_ATTRIBUTES


@router.get("/races")
async def get_races():
    from app.services.compendium import list_entries
    return list_entries("swade", "races")


@router.get("/elements")
async def get_elements():
    from app.services.compendium import list_entries
    return list_entries("swade", "elements")


@router.get("/edges")
async def get_edges():
    from app.services.compendium import list_entries
    return list_entries("swade", "edges")


@router.get("/hindrances")
async def get_hindrances():
    from app.services.compendium import list_entries
    return list_entries("swade", "hindrances")


@router.get("/powers")
async def get_powers():
    from app.services.compendium import list_entries
    return list_entries("swade", "powers")


@router.get("/stats")
async def get_stats():
    """Return derived stat calculation info."""
    from app.systems.swade.dice_rules import calc_toughness, calc_parry, calc_mp, calc_ip
    return {
        "toughness_example": calc_toughness(6, 0),
        "parry_example": calc_parry(6),
        "mp_example": calc_mp(0, 6),
        "ip_example": calc_ip(),
        "die_steps": [4, 6, 8, 10, 12],
        "attribute_points": 5,
        "attribute_point_info": "每个属性从 d4 起步，5 点可用于提升（每点升一档：d4→d6→d8→d10→d12）",
        "edge_hindrance_info": "可选负赘获得额外点数：次要负赘=1点，主要负赘=2点。点数可用于提升属性(2)、专长(2)或技能(1)",
    }


@router.post("/assemble")
async def assemble_character(body: dict[str, Any]):
    """Assemble a SWADE character and save it."""
    import json as _json
    from app.systems.swade.charbuilder import swade_assemble_character
    result = swade_assemble_character.invoke({"spec_json": _json.dumps(body)})
    return {"result": result}
