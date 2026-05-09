"""PF2e game system implementation."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from app.systems.base import GameSystem, CharacterSheet

if TYPE_CHECKING:
    from fastapi import APIRouter


PF2E_SKILLS = [
    {"slug": "acrobatics", "name": "Acrobatics", "name_cn": "体操", "attribute": "dex"},
    {"slug": "arcana", "name": "Arcana", "name_cn": "奥秘", "attribute": "int"},
    {"slug": "athletics", "name": "Athletics", "name_cn": "运动", "attribute": "str"},
    {"slug": "crafting", "name": "Crafting", "name_cn": "制造", "attribute": "int"},
    {"slug": "deception", "name": "Deception", "name_cn": "欺骗", "attribute": "cha"},
    {"slug": "diplomacy", "name": "Diplomacy", "name_cn": "交涉", "attribute": "cha"},
    {"slug": "intimidation", "name": "Intimidation", "name_cn": "威吓", "attribute": "cha"},
    {"slug": "medicine", "name": "Medicine", "name_cn": "医学", "attribute": "wis"},
    {"slug": "nature", "name": "Nature", "name_cn": "自然", "attribute": "wis"},
    {"slug": "occultism", "name": "Occultism", "name_cn": "神秘学", "attribute": "int"},
    {"slug": "performance", "name": "Performance", "name_cn": "表演", "attribute": "cha"},
    {"slug": "religion", "name": "Religion", "name_cn": "宗教", "attribute": "wis"},
    {"slug": "society", "name": "Society", "name_cn": "社会", "attribute": "int"},
    {"slug": "stealth", "name": "Stealth", "name_cn": "隐匿", "attribute": "dex"},
    {"slug": "survival", "name": "Survival", "name_cn": "生存", "attribute": "wis"},
    {"slug": "thievery", "name": "Thievery", "name_cn": "巧手", "attribute": "dex"},
]

PF2E_ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]


class PF2eSystem(GameSystem):
    system_id = "pf2e"
    display_name = "Pathfinder 2e"

    def get_prompts(self) -> dict[str, str]:
        from app.systems.pf2e.prompts import (
            NARRATOR_PF2E, REFEREE_PF2E, TEAMMATE_PF2E,
            COMBAT_PF2E, PREP_PF2E, CREATOR_PF2E,
        )
        return {
            "narrator": NARRATOR_PF2E,
            "referee": REFEREE_PF2E,
            "teammate": TEAMMATE_PF2E,
            "combat": COMBAT_PF2E,
            "prep": PREP_PF2E,
            "creator": CREATOR_PF2E,
        }

    def get_tools(self) -> dict[str, list]:
        from app.systems.pf2e.tools import (
            RULEBOOK_TOOLS,
            CHARBUILDER_QUERY_TOOLS,
            CHARBUILDER_BUILD_TOOLS,
            CHARBUILDER_ALL_TOOLS,
            NPC_TOOLS,
        )
        return {
            "narrator": CHARBUILDER_QUERY_TOOLS + CHARBUILDER_BUILD_TOOLS + NPC_TOOLS,
            "referee": RULEBOOK_TOOLS,
            "prep": CHARBUILDER_ALL_TOOLS + NPC_TOOLS,
            "combat": RULEBOOK_TOOLS,
        }

    def get_npc_builder_tools(self) -> list:
        from app.systems.pf2e.tools import NPC_TOOLS
        return NPC_TOOLS

    def get_builtin_tool_metadata(self) -> list[dict[str, Any]]:
        return [
            {
                "tool_id": "rulebook_search",
                "name": "规则书检索",
                "name_en": "Rulebook Search",
                "description": "在 PF2e 规则数据库中检索专长、法术、状态、装备、动作等条目。",
                "category": "core",
                "builtin": True,
                "parameters": {"query": "搜索关键词或名称", "category": "可选分类过滤"},
            },
        ]

    def determine_success(self, total: int, dc: int, natural: int = 0) -> str:
        from app.systems.pf2e.dice_rules import determine_success
        return determine_success(total, dc, natural)

    def parse_character(self, raw_json: dict) -> CharacterSheet:
        from app.systems.pf2e.character import parse_fvtt_actor
        sheet = parse_fvtt_actor(raw_json)
        return CharacterSheet({
            "id": sheet.id,
            "name": sheet.name,
            "level": sheet.level,
            "raw": raw_json,
            "sheet": sheet,
        })

    def character_to_summary(self, sheet: Any) -> dict[str, Any]:
        from app.systems.pf2e.character import character_to_summary
        return character_to_summary(sheet)

    def render_markup(self, html: str) -> str:
        from app.systems.pf2e.markup import render_fvtt_markup
        return render_fvtt_markup(html)

    def get_charbuilder_router(self) -> "APIRouter | None":
        try:
            from app.systems.pf2e.charbuilder_router import router
            return router
        except ImportError:
            return None

    def get_rules_router(self) -> "APIRouter | None":
        from app.systems.pf2e.routers import router
        return router

    def get_skill_list(self) -> list[dict[str, str]]:
        return PF2E_SKILLS

    def get_ability_list(self) -> list[str]:
        return PF2E_ABILITIES
