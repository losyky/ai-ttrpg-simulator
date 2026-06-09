"""Tools for the narrator to manage the party and request prep agent work.

These tools let the narrator:
  - List available character cards that could be teammates
  - Suggest adding a teammate (with player approval via interactive choice)
    Supports both pre-imported characters and inline NPC data.
  - Send a request to the prep agent for content creation
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from langchain_core.tools import tool

log = logging.getLogger(__name__)


@tool
def list_available_characters(hint: str = "") -> str:
    """List all imported character cards that could serve as teammates.

    Returns a summary of each character including name, ancestry, class, and level.
    Use this to know which characters are available before suggesting teammates.
    """
    from app.routers.characters import _characters

    if not _characters:
        return "当前没有已导入的角色卡。请建议玩家在「团外准备」中导入角色卡。"

    lines = [f"共 {len(_characters)} 张角色卡:\n"]
    for sheet in _characters.values():
        lines.append(f"- **{sheet.name}** (ID: {sheet.id})")
        lines.append(f"  {sheet.ancestry} {sheet.character_class} Lv.{sheet.level} | HP {sheet.hp}/{sheet.max_hp}")
    return "\n".join(lines)


def _create_npc_from_data(npc: dict[str, Any], system_id: str) -> str | None:
    """Create and store an NPC character card from inline data. Returns the new
    character ID on success, or None on failure."""
    from app.models.character import parse_fvtt_actor
    from app.routers.characters import _characters, _raw_data
    from app.config import settings
    from pathlib import Path

    actor_id = uuid.uuid4().hex[:16]
    name = npc.get("name", "Unknown NPC")

    if system_id == "swade":
        from app.systems.swade.charbuilder import SWADE_ATTRIBUTES, ELEMENTS
        from app.systems.swade.dice_rules import calc_toughness, calc_parry, calc_mp, calc_ip

        attrs_raw = npc.get("attributes", {})
        attrs = {}
        for a in SWADE_ATTRIBUTES:
            v = attrs_raw.get(a, 4)
            if isinstance(v, str):
                v = int(v.replace("d", "")) if v.startswith("d") else 4
            attrs[a] = v

        wildcard = npc.get("wildcard", False)
        toughness = npc.get("toughness") or calc_toughness(attrs.get("vigor", 4), npc.get("armor", 0))
        parry = npc.get("parry") or calc_parry(attrs.get("dexterity", attrs.get("agility", 4)))
        pace = npc.get("pace", 6)
        level = npc.get("level", 0)
        mp_max = npc.get("mp") or calc_mp(level, attrs.get("spirit", 4))
        ip_max = npc.get("ip") or calc_ip()

        items = []
        for atk in npc.get("attacks", []):
            items.append({
                "_id": uuid.uuid4().hex[:16], "type": "weapon",
                "name": atk.get("name", "Attack"),
                "system": {
                    "damage": atk.get("damage", "d6"),
                    "notes": atk.get("notes", ""),
                },
            })
        for edge in npc.get("edges", []):
            edge_data = edge if isinstance(edge, dict) else {"name": edge}
            items.append({
                "_id": uuid.uuid4().hex[:16], "type": "edge",
                "name": edge_data.get("name", "Edge"),
                "system": {"description": edge_data.get("description", "")},
            })
        for sa in npc.get("special_abilities", []):
            sa_data = sa if isinstance(sa, dict) else {"name": sa}
            items.append({
                "_id": uuid.uuid4().hex[:16], "type": "ability",
                "name": sa_data.get("name", "Special"),
                "system": {"description": sa_data.get("description", "")},
            })
        for hind in npc.get("hindrances", []):
            hind_data = hind if isinstance(hind, dict) else {"name": hind}
            items.append({
                "_id": uuid.uuid4().hex[:16], "type": "hindrance",
                "name": hind_data.get("name", hind_data) if isinstance(hind_data, dict) else str(hind_data),
                "system": {"description": hind_data.get("description", "") if isinstance(hind_data, dict) else ""},
            })

        elem_resist = {}
        overrides = npc.get("elemental_resistances", {})
        for el in ELEMENTS:
            elem_resist[el] = overrides.get(el, "normal")

        actor = {
            "_id": actor_id, "name": name, "type": "npc",
            "img": "icons/svg/mystery-man.svg",
            "system": {
                "wildcard": wildcard,
                "details": {"species": npc.get("race", "")},
                "attributes": {
                    a: {"die": {"sides": attrs.get(a, 4), "modifier": 0}}
                    for a in SWADE_ATTRIBUTES
                },
                "stats": {
                    "toughness": {"value": toughness, "armor": npc.get("armor", 0)},
                    "parry": {"value": parry},
                    "speed": {"value": pace},
                },
                "resources": {
                    "mp": {"value": mp_max, "max": mp_max},
                    "ip": {"value": ip_max, "max": ip_max},
                },
                "wounds": {"value": 0, "max": npc.get("hp_wounds_max", 3 if wildcard else 1)},
                "advances": {"value": level},
                "elementalResistances": elem_resist,
                "description": npc.get("description", ""),
            },
            "items": items,
            "flags": {"gameSystem": "swade"},
        }
        sub_dir = "swade"

    elif system_id == "daggerheart":
        from app.systems.daggerheart.charbuilder import DH_TRAITS

        traits = npc.get("traits", {})
        hp = npc.get("hp", 10)
        actor = {
            "_id": actor_id, "name": name, "type": "npc",
            "img": "icons/svg/mystery-man.svg",
            "system": {
                "class": npc.get("class", ""),
                "subclass": npc.get("subclass", ""),
                "level": npc.get("level", 1),
                "heritage": {"ancestry": npc.get("ancestry", ""), "community": npc.get("community", "")},
                "traits": {t: {"value": traits.get(t, 0)} for t in DH_TRAITS},
                "resources": {
                    "hitPoints": {"value": hp, "max": hp},
                    "stress": {"value": 0, "max": npc.get("stress_max", 6)},
                    "hope": {"value": 0, "max": 6},
                    "armorSlots": {"value": npc.get("armor_slots", 0), "max": npc.get("armor_slots", 0)},
                },
                "evasion": npc.get("evasion", 10),
                "description": npc.get("description", ""),
            },
            "items": [],
            "flags": {"gameSystem": "daggerheart"},
        }
        sub_dir = "daggerheart"

    else:
        log.warning("Inline NPC creation not supported for system %s", system_id)
        return None

    try:
        sheet = parse_fvtt_actor(actor)
        sheet.id = actor_id
        _characters[actor_id] = sheet
        _raw_data[actor_id] = actor

        char_dir = Path(settings.data_dir) / "characters" / sub_dir
        char_dir.mkdir(parents=True, exist_ok=True)
        (char_dir / f"{actor_id}.json").write_text(
            json.dumps(actor, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        log.info("Created inline NPC %s (id=%s) for system %s", name, actor_id, system_id)
        return actor_id
    except Exception:
        log.exception("Failed to create inline NPC %s", name)
        return None


@tool
def suggest_add_teammate(character_name: str, reason: str, npc_data: str = "") -> str:
    """Suggest adding a character as an AI teammate to the current party.

    This presents an interactive choice to the player asking for their approval.
    Only use this when the story genuinely needs more party members.

    Two modes:
    1. **Existing character card**: just pass character_name and reason.
    2. **Inline NPC**: also pass npc_data as a JSON string with the NPC's stats.
       The NPC will be auto-created as a character card before prompting the player.

    Args:
        character_name: The exact name of the character to add.
        reason: Why this character should join the party (1-2 sentences).
        npc_data: (Optional) JSON string with NPC stats. For SWADE, include keys
            like: name, wildcard, attributes (e.g. {"dexterity": "d8", ...}),
            toughness, parry, pace, mp, ip, level, attacks, edges, hindrances,
            special_abilities, elemental_resistances, hp_wounds_max, description.
            For Daggerheart: name, class, subclass, ancestry, traits, hp,
            evasion, armor_slots, stress_max, description.
    """
    created_id: str | None = None

    if npc_data:
        try:
            npc = json.loads(npc_data)
        except json.JSONDecodeError:
            npc = {}

        if npc:
            from app.models.game_state import _sessions
            system_id = "pf2e"
            for s in _sessions.values():
                system_id = s.system_id
                break
            created_id = _create_npc_from_data(npc, system_id)

    meta: dict[str, Any] = {}
    if created_id:
        meta["character_id"] = created_id

    result = {
        "__interactive__": True,
        "element_type": "choices",
        "id": f"add-teammate-{uuid.uuid4().hex[:8]}",
        "prompt": f"💡 **队友建议**: {reason}\n\n是否将 **{character_name}** 加入队伍作为 AI 队友？",
        "options": [
            {"id": f"accept_{character_name}", "label": "欢迎加入",
             "description": f"将 {character_name} 加入队伍", "icon": "✅"},
            {"id": "decline", "label": "暂时不需要",
             "description": "维持当前队伍", "icon": "❌"},
        ],
        "meta": meta,
    }
    return json.dumps(result, ensure_ascii=False)


@tool
def request_prep_work(task_type: str, description: str) -> str:
    """Send a content creation request to the prep agent (团外AI).

    Use this when you need content that doesn't exist yet — such as
    character cards for NPCs, custom skills, special tools, or scenario materials.

    The request will be queued and the prep agent will handle it.

    Args:
        task_type: Type of work: "character" | "skill" | "tool" | "material" | "other"
        description: Detailed description of what needs to be created and why.
    """
    from app.services.event_log import log_event

    request_id = uuid.uuid4().hex[:8]
    log_event("cross_agent", "prep_request", detail=f"[{task_type}] {description[:200]}",
              data={"request_id": request_id, "task_type": task_type})

    return (
        f"已向团外准备助手发送制作请求 (#{request_id}):\n"
        f"类型: {task_type}\n"
        f"内容: {description}\n\n"
        f"请告知玩家：可以切换到「团外准备 → 助手」标签页查看和处理此请求。"
    )


PARTY_TOOLS = [list_available_characters, suggest_add_teammate, request_prep_work]
