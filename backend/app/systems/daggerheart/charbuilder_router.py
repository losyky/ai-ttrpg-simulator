"""Daggerheart character builder REST endpoints."""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/daggerheart/charbuilder", tags=["daggerheart-charbuilder"])

DH_TRAITS = ["agility", "strength", "finesse", "instinct", "presence", "knowledge"]

DH_CLASSES: list[dict[str, Any]] = [
    {"slug": "bard", "name": "Bard", "name_cn": "吟游诗人", "domains": ["codex", "grace"], "base_hp": 6, "base_evasion": 9, "base_stress": 6, "spellcasting_trait": "presence"},
    {"slug": "druid", "name": "Druid", "name_cn": "德鲁伊", "domains": ["arcana", "sage"], "base_hp": 6, "base_evasion": 8, "base_stress": 6, "spellcasting_trait": "instinct"},
    {"slug": "guardian", "name": "Guardian", "name_cn": "守护者", "domains": ["blade", "valor"], "base_hp": 10, "base_evasion": 7, "base_stress": 6, "spellcasting_trait": None},
    {"slug": "ranger", "name": "Ranger", "name_cn": "游侠", "domains": ["bone", "sage"], "base_hp": 8, "base_evasion": 9, "base_stress": 6, "spellcasting_trait": "instinct"},
    {"slug": "rogue", "name": "Rogue", "name_cn": "游荡者", "domains": ["grace", "midnight"], "base_hp": 6, "base_evasion": 10, "base_stress": 6, "spellcasting_trait": None},
    {"slug": "seraph", "name": "Seraph", "name_cn": "炽天使", "domains": ["splendor", "valor"], "base_hp": 8, "base_evasion": 8, "base_stress": 6, "spellcasting_trait": "presence"},
    {"slug": "sorcerer", "name": "Sorcerer", "name_cn": "术士", "domains": ["arcana", "midnight"], "base_hp": 6, "base_evasion": 8, "base_stress": 6, "spellcasting_trait": "instinct"},
    {"slug": "warrior", "name": "Warrior", "name_cn": "战士", "domains": ["blade", "bone"], "base_hp": 10, "base_evasion": 8, "base_stress": 6, "spellcasting_trait": None},
    {"slug": "wizard", "name": "Wizard", "name_cn": "法师", "domains": ["codex", "splendor"], "base_hp": 6, "base_evasion": 7, "base_stress": 6, "spellcasting_trait": "knowledge"},
]

DH_DOMAINS = [
    {"slug": "arcana", "name": "Arcana", "name_cn": "奥术"},
    {"slug": "blade", "name": "Blade", "name_cn": "利刃"},
    {"slug": "bone", "name": "Bone", "name_cn": "骸骨"},
    {"slug": "codex", "name": "Codex", "name_cn": "典籍"},
    {"slug": "grace", "name": "Grace", "name_cn": "优雅"},
    {"slug": "midnight", "name": "Midnight", "name_cn": "午夜"},
    {"slug": "sage", "name": "Sage", "name_cn": "贤者"},
    {"slug": "splendor", "name": "Splendor", "name_cn": "辉耀"},
    {"slug": "valor", "name": "Valor", "name_cn": "勇气"},
]

DH_ANCESTRIES = [
    {"slug": "clank", "name": "Clank", "name_cn": "铁偶"},
    {"slug": "dwarf", "name": "Dwarf", "name_cn": "矮人"},
    {"slug": "elf", "name": "Elf", "name_cn": "精灵"},
    {"slug": "faerie", "name": "Faerie", "name_cn": "妖精"},
    {"slug": "faun", "name": "Faun", "name_cn": "牧神"},
    {"slug": "firbolg", "name": "Firbolg", "name_cn": "费尔伯格"},
    {"slug": "fungril", "name": "Fungril", "name_cn": "真菌族"},
    {"slug": "galapa", "name": "Galapa", "name_cn": "龟人"},
    {"slug": "giant", "name": "Giant", "name_cn": "巨人"},
    {"slug": "goblin", "name": "Goblin", "name_cn": "地精"},
    {"slug": "halfling", "name": "Halfling", "name_cn": "半身人"},
    {"slug": "human", "name": "Human", "name_cn": "人类"},
    {"slug": "katari", "name": "Katari", "name_cn": "猫人"},
    {"slug": "orc", "name": "Orc", "name_cn": "兽人"},
    {"slug": "ribbet", "name": "Ribbet", "name_cn": "蛙人"},
    {"slug": "simiah", "name": "Simiah", "name_cn": "猴人"},
]

DH_COMMUNITIES = [
    {"slug": "highborne", "name": "Highborne", "name_cn": "高贵之人"},
    {"slug": "loreborne", "name": "Loreborne", "name_cn": "博学之人"},
    {"slug": "orderborne", "name": "Orderborne", "name_cn": "秩序之人"},
    {"slug": "ridgeborne", "name": "Ridgeborne", "name_cn": "山脊之人"},
    {"slug": "seaborne", "name": "Seaborne", "name_cn": "海洋之人"},
    {"slug": "shadowborne", "name": "Shadowborne", "name_cn": "暗影之人"},
    {"slug": "wanderborne", "name": "Wanderborne", "name_cn": "流浪之人"},
    {"slug": "wildborne", "name": "Wildborne", "name_cn": "荒野之人"},
]


@router.get("/classes")
async def get_classes():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "classes")


@router.get("/domains")
async def get_domains():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "domains")


@router.get("/ancestries")
async def get_ancestries():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "ancestries")


@router.get("/communities")
async def get_communities():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "communities")


@router.get("/subclasses")
async def get_subclasses():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "subclasses")


@router.get("/domain-cards")
async def get_domain_cards():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "domain_cards")


@router.get("/weapons")
async def get_weapons():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "weapons")


@router.get("/armors")
async def get_armors():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "armors")


@router.get("/consumables")
async def get_consumables():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "consumables")


@router.get("/loot")
async def get_loot():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "loot")


@router.get("/beastforms")
async def get_beastforms():
    from app.services.compendium import list_entries
    return list_entries("daggerheart", "beastforms")


@router.get("/traits")
async def get_traits():
    return [
        {"slug": t, "name": t.capitalize(), "name_cn": label}
        for t, label in [
            ("agility", "敏捷"), ("strength", "力量"), ("finesse", "灵巧"),
            ("instinct", "本能"), ("presence", "风度"), ("knowledge", "学识"),
        ]
    ]


CLASS_RECOMMENDED: dict[str, dict[str, Any]] = {
    "bard": {
        "traits": {"presence": 2, "knowledge": 1, "finesse": 1, "agility": 0, "strength": 0, "instinct": -1},
        "primary_weapon": "Longbow", "secondary_weapon": "Rapier",
        "armor": "Leather Armor",
    },
    "druid": {
        "traits": {"instinct": 2, "agility": 1, "knowledge": 1, "finesse": 0, "presence": 0, "strength": -1},
        "primary_weapon": "Staff", "secondary_weapon": "Sickle",
        "armor": "Hide Armor",
    },
    "guardian": {
        "traits": {"strength": 2, "agility": 1, "instinct": 1, "finesse": 0, "knowledge": 0, "presence": -1},
        "primary_weapon": "Longsword", "secondary_weapon": "Shield",
        "armor": "Chainmail",
    },
    "ranger": {
        "traits": {"agility": 2, "instinct": 1, "finesse": 1, "strength": 0, "presence": 0, "knowledge": -1},
        "primary_weapon": "Longbow", "secondary_weapon": "Short Sword",
        "armor": "Leather Armor",
    },
    "rogue": {
        "traits": {"finesse": 2, "agility": 1, "presence": 1, "instinct": 0, "knowledge": 0, "strength": -1},
        "primary_weapon": "Dagger", "secondary_weapon": "Hand Crossbow",
        "armor": "Leather Armor",
    },
    "seraph": {
        "traits": {"presence": 2, "strength": 1, "knowledge": 1, "agility": 0, "instinct": 0, "finesse": -1},
        "primary_weapon": "Mace", "secondary_weapon": "Shield",
        "armor": "Chainmail",
    },
    "sorcerer": {
        "traits": {"instinct": 2, "agility": 1, "finesse": 1, "knowledge": 0, "presence": 0, "strength": -1},
        "primary_weapon": "Wand", "secondary_weapon": "Dagger",
        "armor": "Robes",
    },
    "warrior": {
        "traits": {"strength": 2, "agility": 1, "instinct": 1, "finesse": 0, "knowledge": 0, "presence": -1},
        "primary_weapon": "Greatsword", "secondary_weapon": None,
        "armor": "Chainmail",
    },
    "wizard": {
        "traits": {"knowledge": 2, "presence": 1, "instinct": 1, "finesse": 0, "agility": 0, "strength": -1},
        "primary_weapon": "Staff", "secondary_weapon": "Wand",
        "armor": "Robes",
    },
}

LEVELUP_TABLE: dict[str, Any] = {
    "tier2": {
        "range": [2, 3, 4],
        "label": "阶位2 (2-4级)",
        "on_enter": "获得一个+2的额外经历，并获得+1熟练。",
        "pick_count": 2,
        "options": [
            {"key": "trait", "label": "属性提升", "desc": "对两个未标记的角色属性获得+1加值并标记它们"},
            {"key": "hitPoint", "label": "生命槽", "desc": "永久获得1个生命槽"},
            {"key": "stress", "label": "压力槽", "desc": "永久获得1个压力槽"},
            {"key": "experience", "label": "经历提升", "desc": "为两个经历额外添加+1加值"},
            {"key": "evasion", "label": "闪避提升", "desc": "永久获得+1闪避加值"},
            {"key": "proficiency", "label": "熟练提升", "desc": "熟练+1"},
            {"key": "subclass", "label": "升级子职业", "desc": "获取升级的子职业卡，然后划掉本阶位的兼职选项"},
            {"key": "multiclass", "label": "兼职", "desc": "为角色选择一个额外职业"},
        ],
        "also_gain_domain_card": True,
    },
    "tier3": {
        "range": [5, 6, 7],
        "label": "阶位3 (5-7级)",
        "on_enter": "获得一个额外经历并清除所有角色属性提升标记。",
        "pick_count": 2,
        "options": [
            {"key": "trait", "label": "属性提升", "desc": "对两个未标记的角色属性获得+1加值并标记它们"},
            {"key": "hitPoint", "label": "生命槽", "desc": "永久获得1个生命槽"},
            {"key": "stress", "label": "压力槽", "desc": "永久获得1个压力槽"},
            {"key": "experience", "label": "经历提升", "desc": "为两个经历额外添加+1加值"},
            {"key": "evasion", "label": "闪避提升", "desc": "永久获得+1闪避加值"},
            {"key": "proficiency", "label": "熟练提升", "desc": "熟练+1"},
            {"key": "subclass", "label": "升级子职业", "desc": "获取升级的子职业卡"},
            {"key": "multiclass", "label": "兼职", "desc": "为角色选择一个额外职业"},
        ],
        "also_gain_domain_card": True,
    },
    "tier4": {
        "range": [8, 9, 10],
        "label": "阶位4 (8-10级)",
        "on_enter": "获得一个额外经历并清除所有角色属性提升标记。",
        "pick_count": 2,
        "options": [
            {"key": "trait", "label": "属性提升", "desc": "对两个未标记的角色属性获得+1加值并标记它们"},
            {"key": "hitPoint", "label": "生命槽", "desc": "永久获得1个生命槽"},
            {"key": "stress", "label": "压力槽", "desc": "永久获得1个压力槽"},
            {"key": "experience", "label": "经历提升", "desc": "为两个经历额外添加+1加值"},
            {"key": "evasion", "label": "闪避提升", "desc": "永久获得+1闪避加值"},
            {"key": "proficiency", "label": "熟练提升", "desc": "熟练+1"},
            {"key": "subclass", "label": "升级子职业", "desc": "获取升级的子职业卡"},
            {"key": "multiclass", "label": "兼职", "desc": "为角色选择一个额外职业"},
        ],
        "also_gain_domain_card": True,
    },
}


@router.get("/recommended/{class_slug}")
async def get_recommended(class_slug: str):
    return CLASS_RECOMMENDED.get(class_slug, {})


@router.get("/levelup-table")
async def get_levelup_table():
    return LEVELUP_TABLE


@router.post("/assemble")
async def assemble_character(body: dict[str, Any]):
    """Assemble a Daggerheart character and save it."""
    from app.systems.daggerheart.charbuilder import dh_assemble_character
    result = dh_assemble_character.invoke({"spec_json": _json.dumps(body)})
    return {"result": result}


@router.post("/levelup/{character_id}")
async def apply_levelup(character_id: str, body: dict[str, Any]):
    """Apply level-up choices to a character.

    body: { level: int, choices: str[], domain_card?: str, experience?: str,
            trait_boosts?: str[], extra?: dict }
    """
    from app.config import settings
    from app.models.character import parse_fvtt_actor
    from app.routers.characters import _characters, _raw_data

    char_dir = Path(settings.data_dir) / "characters" / "daggerheart"
    fpath = char_dir / f"{character_id}.json"
    if not fpath.exists():
        return {"error": "角色不存在"}

    actor = _json.loads(fpath.read_text(encoding="utf-8"))
    sys = actor.setdefault("system", {})
    res = sys.setdefault("resources", {})
    items = actor.setdefault("items", [])

    new_level = body.get("level", 1)
    choices = body.get("choices", [])
    sys["level"] = new_level

    tier = "tier2" if new_level <= 4 else ("tier3" if new_level <= 7 else "tier4")
    tier_data = LEVELUP_TABLE.get(tier, {})
    on_enter_levels = {2: "tier2", 5: "tier3", 8: "tier4"}
    if new_level in on_enter_levels:
        sys.setdefault("proficiency", 0)
        sys["proficiency"] = sys.get("proficiency", 0) + 1

    import uuid
    for choice in choices:
        if choice == "hitPoint":
            hp = res.setdefault("hitPoints", {"value": 6, "max": 6})
            hp["max"] = hp.get("max", 6) + 1
            hp["value"] = hp["max"]
        elif choice == "stress":
            st = res.setdefault("stress", {"value": 0, "max": 6})
            st["max"] = st.get("max", 6) + 1
        elif choice == "evasion":
            sys["evasion"] = sys.get("evasion", 8) + 1
        elif choice == "proficiency":
            sys["proficiency"] = sys.get("proficiency", 0) + 1

    if body.get("domain_card"):
        items.append({
            "_id": uuid.uuid4().hex[:16],
            "type": "domainCard",
            "name": body["domain_card"],
            "system": {"description": ""},
        })

    if body.get("experience"):
        exps = sys.setdefault("experiences", [])
        exps.append(body["experience"])

    for tb in body.get("trait_boosts", []):
        traits = sys.setdefault("traits", {})
        t = traits.setdefault(tb, {"value": 0})
        t["value"] = t.get("value", 0) + 1

    levelup_log = sys.setdefault("levelup_log", [])
    levelup_log.append({"level": new_level, "choices": choices, **{k: v for k, v in body.items() if k not in ("level", "choices")}})

    fpath.write_text(_json.dumps(actor, ensure_ascii=False, indent=2), encoding="utf-8")

    sheet = parse_fvtt_actor(actor)
    sheet.id = character_id
    _characters[character_id] = sheet
    _raw_data[character_id] = actor

    return {"ok": True, "level": new_level}
