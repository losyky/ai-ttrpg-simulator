"""七物语 (SWADE-based) game system implementation."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from app.systems.base import GameSystem, CharacterSheet

if TYPE_CHECKING:
    from fastapi import APIRouter


SWADE_ABILITIES = ["dexterity", "smarts", "spirit", "strength", "vigor"]


class SWADESystem(GameSystem):
    system_id = "swade"
    display_name = "七物语 (SWADE)"

    def get_prompts(self) -> dict[str, str]:
        from app.systems.swade.prompts import (
            NARRATOR_SWADE, REFEREE_SWADE,
            TEAMMATE_SWADE, COMBAT_SWADE,
            PREP_SWADE, CREATOR_SWADE,
        )
        return {
            "narrator": NARRATOR_SWADE,
            "referee": REFEREE_SWADE,
            "teammate": TEAMMATE_SWADE,
            "combat": COMBAT_SWADE,
            "prep": PREP_SWADE,
            "creator": CREATOR_SWADE,
        }

    def get_tools(self) -> dict[str, list]:
        from app.systems.swade.charbuilder import ALL_TOOLS, NPC_TOOLS
        return {
            "narrator": NPC_TOOLS,
            "referee": [],
            "prep": ALL_TOOLS,
            "combat": [],
        }

    def get_npc_builder_tools(self) -> list:
        from app.systems.swade.charbuilder import NPC_TOOLS
        return NPC_TOOLS

    def get_builtin_tool_metadata(self) -> list[dict[str, Any]]:
        return [
            {
                "tool_id": "swade_assemble_character",
                "name": "七物语角色创建",
                "name_en": "SWADE Character Builder",
                "description": "创建七物语 PC 角色卡（属性、专长、负赘、装备、羁绊）。",
                "category": "charbuilder",
                "builtin": True,
                "parameters": {"spec_json": "角色规格 JSON"},
            },
            {
                "tool_id": "swade_assemble_npc",
                "name": "七物语 NPC 创建",
                "name_en": "SWADE NPC Builder",
                "description": "创建七物语 NPC / 怪物卡。",
                "category": "charbuilder",
                "builtin": True,
                "parameters": {"spec_json": "NPC 规格 JSON"},
            },
        ]

    def determine_success(self, total: int, dc: int, natural: int = 0) -> str:
        from app.systems.swade.dice_rules import determine_success
        return determine_success(total, dc, natural)

    def parse_character(self, raw_json: dict) -> CharacterSheet:
        system = raw_json.get("system", {})
        advances = system.get("advances", {})
        level = advances.get("value", 0) if isinstance(advances, dict) else 0
        return CharacterSheet({
            "id": raw_json.get("_id", ""),
            "name": raw_json.get("name", ""),
            "level": level,
            "raw": raw_json,
        })

    def character_to_summary(self, sheet: Any) -> dict[str, Any]:
        if isinstance(sheet, CharacterSheet):
            raw = sheet.raw
        else:
            raw = getattr(sheet, "fvtt_raw", {}) or {}
        system = raw.get("system", {})
        attrs_raw = system.get("attributes", {})
        stats = system.get("stats", {})
        resources = system.get("resources", {})
        attrs = {}
        for a in SWADE_ABILITIES:
            die_data = attrs_raw.get(a, {})
            # Backward compat: old saves may still use "agility"
            if a == "dexterity" and not die_data:
                die_data = attrs_raw.get("agility", {})
            if isinstance(die_data, dict) and "die" in die_data:
                attrs[a] = f"d{die_data['die'].get('sides', 4)}"
            else:
                attrs[a] = "d4"

        items_raw = raw.get("items", [])
        edges = [i["name"] for i in items_raw if i.get("type") == "edge"]
        hindrances = [i["name"] for i in items_raw if i.get("type") == "hindrance"]

        return {
            "name": raw.get("name", getattr(sheet, "name", "")),
            "race": system.get("details", {}).get("species", ""),
            "attributes": attrs,
            "toughness": stats.get("toughness", {}).get("value", 5),
            "parry": stats.get("parry", {}).get("value", 4),
            "pace": stats.get("speed", {}).get("value", 6),
            "mp": resources.get("mp", {}).get("max", 0),
            "ip": resources.get("ip", {}).get("max", 6),
            "edges": edges,
            "hindrances": hindrances,
            "elemental_resistances": system.get("elementalResistances", {}),
        }

    def render_markup(self, html: str) -> str:
        return html

    def get_charbuilder_router(self) -> "APIRouter | None":
        from app.systems.swade.charbuilder_router import router
        return router

    def get_rules_router(self) -> "APIRouter | None":
        return None

    def get_skill_list(self) -> list[dict[str, str]]:
        return []

    def get_ability_list(self) -> list[str]:
        return SWADE_ABILITIES
