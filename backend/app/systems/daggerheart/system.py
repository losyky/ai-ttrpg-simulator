"""Daggerheart game system implementation."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from app.systems.base import GameSystem, CharacterSheet

if TYPE_CHECKING:
    from fastapi import APIRouter


DH_ABILITIES = ["agility", "strength", "finesse", "instinct", "presence", "knowledge"]


class DaggerheartSystem(GameSystem):
    system_id = "daggerheart"
    display_name = "Daggerheart (匕首之心)"
    has_turn_based_combat = False

    def get_prompts(self) -> dict[str, str]:
        from app.systems.daggerheart.prompts import (
            NARRATOR_DAGGERHEART, REFEREE_DAGGERHEART,
            TEAMMATE_DAGGERHEART, COMBAT_DAGGERHEART,
            PREP_DAGGERHEART, CREATOR_DAGGERHEART,
        )
        return {
            "narrator": NARRATOR_DAGGERHEART,
            "referee": REFEREE_DAGGERHEART,
            "teammate": TEAMMATE_DAGGERHEART,
            "combat": COMBAT_DAGGERHEART,
            "prep": PREP_DAGGERHEART,
            "creator": CREATOR_DAGGERHEART,
        }

    def get_tools(self) -> dict[str, list]:
        from app.systems.daggerheart.charbuilder import ALL_TOOLS, NPC_TOOLS, CHARBUILDER_TOOLS
        from app.tools.interactive import request_duality_roll, announce_token_change
        return {
            "narrator": NPC_TOOLS,
            "referee": [request_duality_roll, announce_token_change],
            "prep": ALL_TOOLS,
            "combat": [],
        }

    def get_npc_builder_tools(self) -> list:
        from app.systems.daggerheart.charbuilder import NPC_TOOLS
        return NPC_TOOLS

    def get_builtin_tool_metadata(self) -> list[dict[str, Any]]:
        return [
            {
                "tool_id": "dh_assemble_character",
                "name": "Daggerheart 角色创建",
                "name_en": "Daggerheart Character Builder",
                "description": "创建 Daggerheart PC 角色卡。",
                "category": "charbuilder",
                "builtin": True,
                "parameters": {"spec_json": "角色规格 JSON"},
            },
            {
                "tool_id": "dh_assemble_npc",
                "name": "Daggerheart NPC 创建",
                "name_en": "Daggerheart NPC Builder",
                "description": "创建 Daggerheart NPC / 敌人卡。",
                "category": "charbuilder",
                "builtin": True,
                "parameters": {"spec_json": "NPC 规格 JSON"},
            },
        ]

    def determine_success(self, total: int, dc: int, natural: int = 0) -> str:
        from app.systems.daggerheart.dice_rules import determine_success
        return determine_success(total, dc, natural)

    def parse_character(self, raw_json: dict) -> CharacterSheet:
        return CharacterSheet({
            "id": raw_json.get("_id", ""),
            "name": raw_json.get("name", ""),
            "level": raw_json.get("system", {}).get("tier", 1),
            "raw": raw_json,
        })

    def character_to_summary(self, sheet: Any) -> dict[str, Any]:
        if isinstance(sheet, CharacterSheet):
            raw = sheet.raw
        else:
            raw = getattr(sheet, "fvtt_raw", {}) or {}
        system = raw.get("system", {})
        traits = system.get("traits", {})
        resources = system.get("resources", {})
        return {
            "name": raw.get("name", getattr(sheet, "name", "")),
            "class": system.get("class", ""),
            "subclass": system.get("subclass", ""),
            "heritage": system.get("heritage", {}),
            "traits": {k: v.get("value", 0) if isinstance(v, dict) else v for k, v in traits.items()},
            "hp": resources.get("hitPoints", {}).get("value", 0),
            "max_hp": resources.get("hitPoints", {}).get("max", 0),
            "stress": resources.get("stress", {}).get("value", 0),
            "evasion": system.get("evasion", 0),
        }

    def render_markup(self, html: str) -> str:
        return html

    def get_charbuilder_router(self) -> "APIRouter | None":
        from app.systems.daggerheart.charbuilder_router import router
        return router

    def get_rules_router(self) -> "APIRouter | None":
        return None

    def get_skill_list(self) -> list[dict[str, str]]:
        return []

    def get_ability_list(self) -> list[str]:
        return DH_ABILITIES
