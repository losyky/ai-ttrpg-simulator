"""Daggerheart character and NPC assembly tools (LangChain @tool)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from langchain_core.tools import tool


DH_TRAITS = ["agility", "strength", "finesse", "instinct", "presence", "knowledge"]
DH_TRAIT_LABELS = {
    "agility": "敏捷 (Agility)",
    "strength": "力量 (Strength)",
    "finesse": "灵巧 (Finesse)",
    "instinct": "本能 (Instinct)",
    "presence": "风度 (Presence)",
    "knowledge": "学识 (Knowledge)",
}
DH_CLASSES = [
    "bard", "druid", "guardian", "ranger", "rogue",
    "seraph", "sorcerer", "warrior", "wizard",
]


def _gen_id() -> str:
    return uuid.uuid4().hex[:16]


@tool
def dh_assemble_character(spec_json: str) -> str:
    """Assemble a Daggerheart PC from a JSON specification and save it.

    The spec_json should contain:
    - name (str): character name
    - class (str): one of bard/druid/guardian/ranger/rogue/seraph/sorcerer/warrior/wizard
    - subclass (str): subclass name
    - ancestry (str): ancestry name
    - community (str): community name
    - traits (dict): {"agility": 1, "strength": 2, ...} — modifiers from +2/+1/+1/0/0/-1
    - hp (int): hit points
    - evasion (int): evasion score
    - armor_slots (int): number of armor slots
    - stress_max (int): maximum stress
    - domain_cards (list[str]): names of chosen domain cards
    - experiences (list[str]): two experience descriptions
    - equipment (list[str]): starting equipment names
    - background (str): character background/biography
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return f"JSON 解析失败: {e}"

    name = spec.get("name", "New Hero")
    cls = spec.get("class", "warrior")
    subclass = spec.get("subclass", "")
    ancestry = spec.get("ancestry", "")
    community = spec.get("community", "")
    traits = spec.get("traits", {})

    # Validate trait distribution
    trait_vals = sorted(traits.get(t, 0) for t in DH_TRAITS)
    expected = sorted([-1, 0, 0, 1, 1, 2])
    warnings = []
    if trait_vals != expected:
        warnings.append(f"特质分配应为 +2/+1/+1/+0/+0/-1，当前: {dict(sorted(traits.items()))}")

    actor_id = _gen_id()

    items = []
    for card in spec.get("domain_cards", []):
        items.append({
            "_id": _gen_id(),
            "type": "domainCard",
            "name": card,
            "system": {"description": ""},
        })
    for eq in spec.get("equipment", []):
        items.append({
            "_id": _gen_id(),
            "type": "loot",
            "name": eq,
            "system": {},
        })

    actor = {
        "_id": actor_id,
        "name": name,
        "type": "character",
        "img": "icons/svg/mystery-man.svg",
        "system": {
            "class": cls,
            "subclass": subclass,
            "level": 1,
            "proficiency": 0,
            "heritage": {
                "ancestry": ancestry,
                "community": community,
            },
            "traits": {t: {"value": traits.get(t, 0)} for t in DH_TRAITS},
            "resources": {
                "hitPoints": {"value": spec.get("hp", 10), "max": spec.get("hp", 10)},
                "stress": {"value": 0, "max": spec.get("stress_max", 6)},
                "hope": {"value": 0, "max": 6},
                "armorSlots": {"value": spec.get("armor_slots", 0), "max": spec.get("armor_slots", 0)},
            },
            "evasion": spec.get("evasion", 10),
            "experiences": spec.get("experiences", []),
            "biography": {
                "background": spec.get("background", ""),
            },
            "levelup_log": [],
        },
        "items": items,
        "flags": {"gameSystem": "daggerheart"},
    }

    from app.models.character import parse_fvtt_actor
    from app.routers.characters import _characters, _raw_data
    from app.config import settings

    sheet = parse_fvtt_actor(actor)
    sheet.id = actor_id
    _characters[actor_id] = sheet
    _raw_data[actor_id] = actor

    char_dir = Path(settings.data_dir) / "characters" / "daggerheart"
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / f"{actor_id}.json").write_text(
        json.dumps(actor, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    traits_str = ", ".join(f"{DH_TRAIT_LABELS.get(t, t)} {traits.get(t, 0):+d}" for t in DH_TRAITS)
    warn_str = ("\n警告:\n" + "\n".join(f"  - {w}" for w in warnings)) if warnings else ""

    return (
        f"角色 **{name}** 创建成功！\n"
        f"ID: `{actor_id}`\n"
        f"职业: {cls} / {subclass}\n"
        f"Heritage: {ancestry} ({community})\n"
        f"特质: {traits_str}\n"
        f"HP: {spec.get('hp', 10)}, Evasion: {spec.get('evasion', 10)}, "
        f"Armor Slots: {spec.get('armor_slots', 0)}, Stress Max: {spec.get('stress_max', 6)}\n"
        f"领域卡: {', '.join(spec.get('domain_cards', []))}\n"
        f"经历: {', '.join(spec.get('experiences', []))}"
        + warn_str
    )


@tool
def dh_assemble_npc(spec_json: str) -> str:
    """Assemble a Daggerheart NPC / adversary card from a JSON specification and save it.

    The spec_json should contain:
    - name (str): adversary name
    - tier (int): difficulty tier (1-4)
    - hp (int): hit points
    - stress (int): stress threshold (0 if none)
    - evasion (int): evasion score
    - thresholds (dict): {"minor": N, "major": N, "severe": N} damage thresholds
    - attacks (list[dict]): [{"name": "Claw", "damage": "d8+3", "range": "melee", "description": ""}]
    - features (list[dict]): [{"name": "Ability", "description": "..."}]
    - description (str): narrative description
    - motives (list[str]): adversary motivations
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return f"JSON 解析失败: {e}"

    actor_id = _gen_id()
    name = spec.get("name", "Unknown Adversary")
    tier = spec.get("tier", 1)

    items = []
    for atk in spec.get("attacks", []):
        items.append({
            "_id": _gen_id(),
            "type": "weapon",
            "name": atk.get("name", "Attack"),
            "system": {
                "damage": atk.get("damage", "d6"),
                "range": atk.get("range", "melee"),
                "description": atk.get("description", ""),
            },
        })
    for feat in spec.get("features", []):
        items.append({
            "_id": _gen_id(),
            "type": "feature",
            "name": feat.get("name", "Feature"),
            "system": {
                "description": feat.get("description", ""),
            },
        })

    actor = {
        "_id": actor_id,
        "name": name,
        "type": "npc",
        "img": "icons/svg/mystery-man.svg",
        "system": {
            "tier": tier,
            "resources": {
                "hitPoints": {"value": spec.get("hp", 10), "max": spec.get("hp", 10)},
                "stress": {"value": 0, "max": spec.get("stress", 0)},
            },
            "evasion": spec.get("evasion", 10),
            "thresholds": spec.get("thresholds", {}),
            "description": spec.get("description", ""),
            "motives": spec.get("motives", []),
        },
        "items": items,
        "flags": {"gameSystem": "daggerheart"},
    }

    from app.models.character import parse_fvtt_actor
    from app.routers.characters import _characters, _raw_data
    from app.config import settings

    sheet = parse_fvtt_actor(actor)
    sheet.id = actor_id
    _characters[actor_id] = sheet
    _raw_data[actor_id] = actor

    char_dir = Path(settings.data_dir) / "characters" / "daggerheart"
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / f"{actor_id}.json").write_text(
        json.dumps(actor, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    attacks = spec.get("attacks", [])
    features = spec.get("features", [])
    return (
        f"NPC **{name}** (Tier {tier}) 创建成功！\n"
        f"ID: `{actor_id}`\n"
        f"HP: {spec.get('hp', 10)}, Evasion: {spec.get('evasion', 10)}\n"
        f"攻击: {', '.join(a.get('name', '?') for a in attacks)}\n"
        f"特殊能力: {', '.join(f.get('name', '?') for f in features)}"
    )


CHARBUILDER_TOOLS = [dh_assemble_character]
NPC_TOOLS = [dh_assemble_npc]
ALL_TOOLS = CHARBUILDER_TOOLS + NPC_TOOLS
