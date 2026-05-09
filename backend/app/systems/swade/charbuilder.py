"""七物语 (SWADE-based) character and NPC assembly tools (LangChain @tool)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from langchain_core.tools import tool

from app.systems.swade.dice_rules import calc_toughness, calc_parry, calc_mp, calc_ip

SWADE_ATTRIBUTES = ["agility", "smarts", "spirit", "strength", "vigor"]
SWADE_ATTR_LABELS = {
    "agility": "灵巧 (Agility)",
    "smarts": "聪慧 (Smarts)",
    "spirit": "心魂 (Spirit)",
    "strength": "力量 (Strength)",
    "vigor": "活力 (Vigor)",
}
ELEMENTS = ["fire", "ice", "earth", "wind", "thunder", "light", "dark"]
ELEMENT_LABELS = {
    "fire": "火", "ice": "冰", "earth": "土", "wind": "风",
    "thunder": "雷", "light": "光", "dark": "暗",
}
RESISTANCE_LEVELS = ["weakness", "normal", "resistance", "immunity"]


def _gen_id() -> str:
    return uuid.uuid4().hex[:16]


@tool
def swade_assemble_character(spec_json: str) -> str:
    """Assemble a 七物语 PC from a JSON specification and save it.

    The spec_json should contain:
    - name (str): character name
    - race (str): race/species name
    - attributes (dict): {"agility": 6, "smarts": 8, ...} — die sides (4/6/8/10/12)
    - edges (list[dict]): [{"name": "Edge Name", "description": "...", "rank": "novice"}]
    - hindrances (list[dict]): [{"name": "Hindrance Name", "description": "...", "major": true/false}]
    - equipment (list[dict]): [{"name": "Item", "damage": "str+d6", "weight": 2, "notes": ""}]
    - armor (int): total armor value from equipment
    - level (int): character level (default 0)
    - bonds (list[dict]): [{"target": "NPC Name", "type": "loyalty", "description": "..."}]
    - elemental_resistances (dict): {"fire": "normal", ...} optional overrides
    - mp_bonus (int): extra MP from rank bonuses (default 0)
    - ip_bonus (int): extra IP from rank bonuses (default 0)
    - toughness_bonus (int): extra toughness from rank bonuses (default 0)
    - pace (int): movement speed in inches (default 6)
    - background (str): character backstory
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return f"JSON 解析失败: {e}"

    name = spec.get("name", "New Character")
    race = spec.get("race", "人类")
    attrs = spec.get("attributes", {})
    level = spec.get("level", 0)
    armor_val = spec.get("armor", 0)

    for a in SWADE_ATTRIBUTES:
        if a not in attrs:
            attrs[a] = 4

    warnings = []
    for a, sides in attrs.items():
        if sides not in (4, 6, 8, 10, 12):
            warnings.append(f"属性 {a} 骰面 d{sides} 不合规，应为 d4/d6/d8/d10/d12")

    toughness = calc_toughness(attrs.get("vigor", 4), armor_val) + spec.get("toughness_bonus", 0)
    parry = calc_parry(attrs.get("agility", 4))
    mp_max = calc_mp(level, attrs.get("spirit", 4)) + spec.get("mp_bonus", 0)
    ip_max = calc_ip() + spec.get("ip_bonus", 0)
    pace = spec.get("pace", 6)

    elem_resist = {}
    overrides = spec.get("elemental_resistances", {})
    for el in ELEMENTS:
        elem_resist[el] = overrides.get(el, "normal")

    actor_id = _gen_id()

    items = []
    for edge in spec.get("edges", []):
        items.append({
            "_id": _gen_id(),
            "type": "edge",
            "name": edge.get("name", "Unnamed Edge"),
            "system": {
                "description": edge.get("description", ""),
                "rank": edge.get("rank", "novice"),
            },
        })
    for hind in spec.get("hindrances", []):
        items.append({
            "_id": _gen_id(),
            "type": "hindrance",
            "name": hind.get("name", "Unnamed Hindrance"),
            "system": {
                "description": hind.get("description", ""),
                "major": hind.get("major", False),
            },
        })
    for eq in spec.get("equipment", []):
        items.append({
            "_id": _gen_id(),
            "type": "gear",
            "name": eq.get("name", "Item"),
            "system": {
                "damage": eq.get("damage", ""),
                "weight": eq.get("weight", 0),
                "notes": eq.get("notes", ""),
            },
        })

    actor = {
        "_id": actor_id,
        "name": name,
        "type": "character",
        "img": "icons/svg/mystery-man.svg",
        "system": {
            "details": {
                "species": race,
                "biography": spec.get("background", ""),
            },
            "attributes": {
                a: {"die": {"sides": attrs.get(a, 4), "modifier": 0}}
                for a in SWADE_ATTRIBUTES
            },
            "stats": {
                "toughness": {"value": toughness, "armor": armor_val},
                "parry": {"value": parry},
                "speed": {"value": pace},
            },
            "resources": {
                "mp": {"value": mp_max, "max": mp_max},
                "ip": {"value": ip_max, "max": ip_max},
            },
            "advances": {"value": level},
            "elementalResistances": elem_resist,
            "bonds": spec.get("bonds", []),
        },
        "items": items,
        "flags": {"gameSystem": "swade"},
    }

    from app.models.character import parse_fvtt_actor
    from app.routers.characters import _characters, _raw_data
    from app.config import settings

    sheet = parse_fvtt_actor(actor)
    sheet.id = actor_id
    _characters[actor_id] = sheet
    _raw_data[actor_id] = actor

    char_dir = Path(settings.data_dir) / "characters" / "swade"
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / f"{actor_id}.json").write_text(
        json.dumps(actor, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    attrs_str = ", ".join(f"{SWADE_ATTR_LABELS.get(a, a)} d{attrs.get(a, 4)}" for a in SWADE_ATTRIBUTES)
    edges_str = ", ".join(e.get("name", "?") for e in spec.get("edges", []))
    hinds_str = ", ".join(h.get("name", "?") for h in spec.get("hindrances", []))
    warn_str = ("\n警告:\n" + "\n".join(f"  - {w}" for w in warnings)) if warnings else ""

    return (
        f"角色 **{name}** 创建成功！\n"
        f"ID: `{actor_id}`\n"
        f"种族: {race}, 级别: {level}\n"
        f"属性: {attrs_str}\n"
        f"坚韧: {toughness} (护甲{armor_val}), 格挡: {parry}, 移速: {pace}\n"
        f"MP: {mp_max}, IP: {ip_max}\n"
        f"专长: {edges_str or '无'}\n"
        f"负赘: {hinds_str or '无'}"
        + warn_str
    )


@tool
def swade_assemble_npc(spec_json: str) -> str:
    """Assemble a 七物语 NPC / monster card from a JSON specification and save it.

    The spec_json should contain:
    - name (str): NPC/monster name
    - wildcard (bool): true = Wildcard (has Bennies, Wild Die), false = Extra
    - attributes (dict): {"agility": 6, ...} die sides for each attribute
    - toughness (int): total toughness value
    - parry (int): parry value
    - pace (int): movement speed
    - attacks (list[dict]): [{"name": "Claw", "damage": "str+d6", "bonus": "+2", "notes": ""}]
    - edges (list[dict]): [{"name": "Edge", "description": "..."}]
    - special_abilities (list[dict]): [{"name": "Ability", "description": "..."}]
    - elemental_resistances (dict): optional
    - hp_wounds_max (int): max wounds (default 3 for Wildcards, 1 for Extras)
    - description (str): narrative description
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return f"JSON 解析失败: {e}"

    actor_id = _gen_id()
    name = spec.get("name", "Unknown NPC")
    wildcard = spec.get("wildcard", False)
    attrs = spec.get("attributes", {})

    items = []
    for atk in spec.get("attacks", []):
        items.append({
            "_id": _gen_id(),
            "type": "weapon",
            "name": atk.get("name", "Attack"),
            "system": {
                "damage": atk.get("damage", "d6"),
                "actions": {"skillMod": atk.get("bonus", "")},
                "notes": atk.get("notes", ""),
            },
        })
    for edge in spec.get("edges", []):
        items.append({
            "_id": _gen_id(),
            "type": "edge",
            "name": edge.get("name", "Edge"),
            "system": {"description": edge.get("description", "")},
        })
    for sa in spec.get("special_abilities", []):
        items.append({
            "_id": _gen_id(),
            "type": "ability",
            "name": sa.get("name", "Special"),
            "system": {"description": sa.get("description", "")},
        })

    elem_resist = {}
    overrides = spec.get("elemental_resistances", {})
    for el in ELEMENTS:
        elem_resist[el] = overrides.get(el, "normal")

    actor = {
        "_id": actor_id,
        "name": name,
        "type": "npc",
        "img": "icons/svg/mystery-man.svg",
        "system": {
            "wildcard": wildcard,
            "attributes": {
                a: {"die": {"sides": attrs.get(a, 4), "modifier": 0}}
                for a in SWADE_ATTRIBUTES
            },
            "stats": {
                "toughness": {"value": spec.get("toughness", 5), "armor": spec.get("armor", 0)},
                "parry": {"value": spec.get("parry", 4)},
                "speed": {"value": spec.get("pace", 6)},
            },
            "wounds": {"value": 0, "max": spec.get("hp_wounds_max", 3 if wildcard else 1)},
            "elementalResistances": elem_resist,
            "description": spec.get("description", ""),
        },
        "items": items,
        "flags": {"gameSystem": "swade"},
    }

    from app.models.character import parse_fvtt_actor
    from app.routers.characters import _characters, _raw_data
    from app.config import settings

    sheet = parse_fvtt_actor(actor)
    sheet.id = actor_id
    _characters[actor_id] = sheet
    _raw_data[actor_id] = actor

    char_dir = Path(settings.data_dir) / "characters" / "swade"
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / f"{actor_id}.json").write_text(
        json.dumps(actor, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    wc_tag = "不羁角色(Wildcard)" if wildcard else "临演(Extra)"
    attacks = spec.get("attacks", [])
    edges = spec.get("edges", [])
    specials = spec.get("special_abilities", [])
    return (
        f"NPC **{name}** [{wc_tag}] 创建成功！\n"
        f"ID: `{actor_id}`\n"
        f"坚韧: {spec.get('toughness', 5)}, 格挡: {spec.get('parry', 4)}, 移速: {spec.get('pace', 6)}\n"
        f"攻击: {', '.join(a.get('name', '?') for a in attacks)}\n"
        f"专长: {', '.join(e.get('name', '?') for e in edges)}\n"
        f"特殊能力: {', '.join(s.get('name', '?') for s in specials)}"
    )


CHARBUILDER_TOOLS = [swade_assemble_character]
NPC_TOOLS = [swade_assemble_npc]
ALL_TOOLS = CHARBUILDER_TOOLS + NPC_TOOLS
