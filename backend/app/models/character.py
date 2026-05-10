"""PF2e character data model — mirrors FVTT Actor format.

Stores characters in FVTT-native JSON so they can be round-tripped:
  FVTT export → import here → use in game → export back to FVTT

The structured Pydantic models are for type-safe access in the agent
layer; the raw FVTT JSON is always preserved in `_raw`.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


# ── Lightweight view models (used by agents and frontend) ──

class AbilityScores(BaseModel):
    str_: int = Field(0, alias="str")
    dex: int = 0
    con: int = 0
    int_: int = Field(0, alias="int")
    wis: int = 0
    cha: int = 0

    model_config = {"populate_by_name": True}


SKILL_SLUGS = [
    "acrobatics", "arcana", "athletics", "crafting", "deception",
    "diplomacy", "intimidation", "medicine", "nature", "occultism",
    "performance", "religion", "society", "stealth", "survival", "thievery",
]

RANK_LABEL = {0: "未受训", 1: "受训", 2: "专家", 3: "大师", 4: "传奇"}


class SkillEntry(BaseModel):
    slug: str
    rank: int = 0
    label: str = ""


class SaveEntry(BaseModel):
    slug: str  # fortitude / reflex / will
    rank: int = 0


class FeatEntry(BaseModel):
    name: str
    item_type: str = "feat"
    category: str = ""
    description: str = ""


class SpellEntry(BaseModel):
    name: str
    rank: int = 0
    tradition: str = ""
    description: str = ""


class ItemEntry(BaseModel):
    name: str
    item_type: str = ""
    quantity: int = 1
    description: str = ""


class CharacterSheet(BaseModel):
    """Structured view of a PF2e character — derived from FVTT JSON."""

    # Identity
    id: str = ""
    name: str = ""
    player_controlled: bool = True

    # Core
    level: int = 1
    ancestry: str = ""
    heritage: str = ""
    background: str = ""
    character_class: str = ""
    key_ability: str = ""
    deity: str = ""

    # Vitals
    hp: int = 0
    max_hp: int = 0
    temp_hp: int = 0
    hero_points: int = 1

    # Abilities
    abilities: AbilityScores = Field(default_factory=AbilityScores)

    # Proficiencies
    skills: list[SkillEntry] = Field(default_factory=list)
    saves: list[SaveEntry] = Field(default_factory=list)
    perception_rank: int = 0

    # Character content
    feats: list[FeatEntry] = Field(default_factory=list)
    spells: list[SpellEntry] = Field(default_factory=list)
    inventory: list[ItemEntry] = Field(default_factory=list)
    lore_skills: list[SkillEntry] = Field(default_factory=list)

    # Biography
    backstory: str = ""
    age: str = ""
    gender: str = ""

    # Raw FVTT data (preserved for round-trip)
    fvtt_raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


# ── FVTT JSON parser ──

def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"@UUID\[.*?\]\{(.*?)\}", r"\1", text)
    text = re.sub(r"@UUID\[.*?\]", "", text)
    return text.strip()


def _collect_boosts(items: list[dict[str, Any]], build: dict[str, Any]) -> dict[str, int]:
    """Compute ability modifiers by counting boosts/flaws from all sources.

    PF2e v13 stores ability boosts across multiple locations:
      - ancestry item: system.boosts.{0,1,2...}.selected
      - ancestry item: system.flaws.{0,...}.value (list of auto-applied flaws)
      - background item: system.boosts.{0,1}.selected
      - class item: system.keyAbility.selected
      - free boosts: system.build.attributes.boosts.{level} (list of ability keys)
    Each boost gives +1 to the modifier (which corresponds to +2 to the score in PF2e).
    """
    counts: dict[str, int] = {a: 0 for a in ("str", "dex", "con", "int", "wis", "cha")}

    for item in items:
        isys = item.get("system", {})
        itype = item.get("type", "")

        # Ancestry / Background boosts
        if itype in ("ancestry", "background"):
            boosts = isys.get("boosts", {})
            if isinstance(boosts, dict):
                for slot in boosts.values():
                    sel = slot.get("selected")
                    if sel and sel in counts:
                        counts[sel] += 1

            # Ancestry flaws (auto-applied from value list)
            if itype == "ancestry":
                flaws = isys.get("flaws", {})
                if isinstance(flaws, dict):
                    for slot in flaws.values():
                        for flaw_ab in slot.get("value", []):
                            if flaw_ab in counts:
                                counts[flaw_ab] -= 1

        # Class key ability
        if itype == "class":
            ka = isys.get("keyAbility", {})
            sel = ka.get("selected")
            if sel and sel in counts:
                counts[sel] += 1

    # Free boosts from build system (level-up + initial)
    build_boosts = build.get("attributes", {}).get("boosts", {})
    if isinstance(build_boosts, dict):
        for _lvl, abilities in build_boosts.items():
            if isinstance(abilities, list):
                for ab in abilities:
                    if ab in counts:
                        counts[ab] += 1

    return counts


def parse_fvtt_actor(data: dict[str, Any]) -> CharacterSheet:
    """Parse a FVTT PF2e Actor JSON into a CharacterSheet.

    Supports both legacy format (system.abilities/skills/saves as dicts)
    and PF2e v13 remaster format (computed from boosts/items/build).
    """
    system = data.get("system", {})
    details = system.get("details", {})
    attrs = system.get("attributes", {})
    items = data.get("items", [])

    sheet = CharacterSheet(
        id=data.get("_id", ""),
        name=data.get("name", "Unknown"),
        fvtt_raw=data,
    )

    # Level & key ability
    sheet.level = details.get("level", {}).get("value", 1)
    sheet.key_ability = details.get("keyability", {}).get("value", "")

    # HP
    hp_data = attrs.get("hp", {})
    sheet.hp = hp_data.get("value", 0)
    sheet.max_hp = hp_data.get("max", hp_data.get("value", 0))
    sheet.temp_hp = hp_data.get("temp", 0)

    # Hero points
    resources = system.get("resources", {})
    sheet.hero_points = resources.get("heroPoints", {}).get("value", 1)

    # ── Abilities ──
    # Try legacy format first (system.abilities as dict with mod values)
    abilities_data = system.get("abilities")
    if abilities_data and isinstance(abilities_data, dict):
        sheet.abilities = AbilityScores(
            str=abilities_data.get("str", {}).get("mod", 0),
            dex=abilities_data.get("dex", {}).get("mod", 0),
            con=abilities_data.get("con", {}).get("mod", 0),
            int=abilities_data.get("int", {}).get("mod", 0),
            wis=abilities_data.get("wis", {}).get("mod", 0),
            cha=abilities_data.get("cha", {}).get("mod", 0),
        )
    else:
        # v13 format: compute from boosts across all sources
        build = system.get("build", {})
        mods = _collect_boosts(items, build)
        sheet.abilities = AbilityScores(
            str=mods["str"], dex=mods["dex"], con=mods["con"],
            int=mods["int"], wis=mods["wis"], cha=mods["cha"],
        )

    # ── Extract class/background data for skills/saves/perception ──
    class_item: dict[str, Any] = {}
    bg_item: dict[str, Any] = {}
    trained_skills: set[str] = set()

    for item in items:
        itype = item.get("type", "")
        isys = item.get("system", {})

        if itype == "class":
            class_item = isys
            # Skills trained by class
            cls_trained = isys.get("trainedSkills", {})
            for s in cls_trained.get("value", []):
                trained_skills.add(s)
        elif itype == "background":
            bg_item = isys
            # Skills trained by background
            bg_trained = isys.get("trainedSkills", {})
            for s in bg_trained.get("value", []):
                trained_skills.add(s)
            # Lore from background
            for lore_name in bg_trained.get("lore", []):
                sheet.lore_skills.append(SkillEntry(slug=lore_name, rank=1))

    # Also check build.skills for player-chosen skill training
    build_skills = system.get("build", {}).get("skills", {})
    if isinstance(build_skills, dict):
        for _key, skill_list in build_skills.items():
            if isinstance(skill_list, list):
                for s in skill_list:
                    if isinstance(s, str):
                        trained_skills.add(s)

    # ── Skills ──
    # Try legacy format first (system.skills as dict with rank)
    skills_data = system.get("skills", {})
    has_legacy_skills = any(
        isinstance(skills_data.get(s), dict) and "rank" in skills_data.get(s, {})
        for s in SKILL_SLUGS
    )

    for slug in SKILL_SLUGS:
        if has_legacy_skills:
            rank = skills_data.get(slug, {}).get("rank", 0)
        else:
            rank = 1 if slug in trained_skills else 0
        sheet.skills.append(SkillEntry(slug=slug, rank=rank, label=RANK_LABEL.get(rank, "")))

    # ── Saves ──
    # Try legacy format (system.saves)
    saves_data = system.get("saves", {})
    has_legacy_saves = any(
        isinstance(saves_data.get(s), dict) and "rank" in saves_data.get(s, {})
        for s in ("fortitude", "reflex", "will")
    )

    if has_legacy_saves:
        for slug in ("fortitude", "reflex", "will"):
            rank = saves_data.get(slug, {}).get("rank", 0)
            sheet.saves.append(SaveEntry(slug=slug, rank=rank))
    else:
        # v13: saves from class item
        cls_saves = class_item.get("savingThrows", {})
        for slug in ("fortitude", "reflex", "will"):
            rank = cls_saves.get(slug, 0) if isinstance(cls_saves, dict) else 0
            sheet.saves.append(SaveEntry(slug=slug, rank=rank))

    # ── Perception ──
    # Try legacy format
    if has_legacy_skills and "perception" in skills_data:
        sheet.perception_rank = skills_data.get("perception", {}).get("rank", 0)
    else:
        # v13: perception from class item
        sheet.perception_rank = class_item.get("perception", 0)

    # Biography — may be a dict (PF2e FVTT) or a plain string (SWADE)
    bio = details.get("biography", {})
    if isinstance(bio, str):
        sheet.backstory = _strip_html(bio)
    else:
        sheet.backstory = _strip_html(bio.get("backstory", ""))
    sheet.age = details.get("age", {}).get("value", "")
    sheet.gender = details.get("gender", {}).get("value", "")
    sheet.deity = details.get("deity", {}).get("value", "")

    # ── Parse embedded items (feats, spells, equipment, etc.) ──
    for item in items:
        itype = item.get("type", "")
        iname = item.get("name", "")
        isys = item.get("system", {})

        if itype == "ancestry":
            sheet.ancestry = iname
        elif itype == "heritage":
            sheet.heritage = iname
        elif itype == "background":
            sheet.background = iname
        elif itype == "class":
            sheet.character_class = iname
        elif itype == "feat":
            desc = _strip_html(isys.get("description", {}).get("value", ""))
            cat = isys.get("category", "")
            sheet.feats.append(FeatEntry(
                name=iname, item_type=itype, category=cat,
                description=desc[:300],
            ))
        elif itype == "spell":
            tradition = ""
            loc = isys.get("location", {}).get("value", "")
            for other in items:
                if other.get("type") == "spellcastingEntry" and other.get("_id") == loc:
                    tradition = other.get("system", {}).get("tradition", {}).get("value", "")
                    break
            desc = _strip_html(isys.get("description", {}).get("value", ""))
            sheet.spells.append(SpellEntry(
                name=iname, tradition=tradition, description=desc[:200],
            ))
        elif itype == "lore":
            rank = isys.get("proficient", {}).get("value", 0)
            if rank == 0:
                rank = 1
            sheet.lore_skills.append(SkillEntry(slug=iname, rank=rank))
        elif itype in ("weapon", "armor", "equipment", "consumable", "treasure", "shield", "backpack"):
            qty = isys.get("quantity", 1)
            desc = _strip_html(isys.get("description", {}).get("value", ""))
            sheet.inventory.append(ItemEntry(
                name=iname, item_type=itype, quantity=qty, description=desc[:200],
            ))

    return sheet


def character_to_summary(sheet: CharacterSheet) -> str:
    """Produce a concise text summary of a character for agent consumption."""
    lines = [
        f"【{sheet.name}】",
        f"  {sheet.ancestry} ({sheet.heritage}) {sheet.character_class} Lv.{sheet.level}",
        f"  HP: {sheet.hp}/{sheet.max_hp}  英雄点: {sheet.hero_points}",
    ]

    if any(v != 0 for v in [sheet.abilities.str_, sheet.abilities.dex]):
        a = sheet.abilities
        lines.append(f"  力{a.str_} 敏{a.dex} 体{a.con} 智{a.int_} 感{a.wis} 魅{a.cha}")

    trained = [s for s in sheet.skills if s.rank > 0]
    if trained:
        lines.append(f"  受训技能: {', '.join(s.slug for s in trained)}")

    if sheet.lore_skills:
        lines.append(f"  学识: {', '.join(s.slug for s in sheet.lore_skills)}")

    if sheet.feats:
        feat_names = [f.name for f in sheet.feats if f.category != "classfeature"]
        if feat_names:
            lines.append(f"  专长: {', '.join(feat_names[:10])}")

    if sheet.spells:
        lines.append(f"  法术: {', '.join(s.name for s in sheet.spells[:10])}")

    weapons = [i for i in sheet.inventory if i.item_type == "weapon"]
    if weapons:
        lines.append(f"  武器: {', '.join(w.name for w in weapons)}")

    if sheet.backstory:
        lines.append(f"  背景故事: {sheet.backstory[:150]}...")

    return "\n".join(lines)
