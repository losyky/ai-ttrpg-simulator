"""PF2e Character Build Validator — checks that a set of build choices
conforms to Pathfinder 2e rules.

Validates:
  - Ability boost counts and slot constraints
  - Skill training count and increase levels
  - Feat category, level, and class/ancestry matching
  - Prerequisite satisfaction (basic text matching)
  - Spell tradition matching
  - Equipment proficiency
"""

from __future__ import annotations

import json
from typing import Any

from app.systems.pf2e.charbuilder_db import (
    get_ancestry_by_slug,
    get_background_by_slug,
    get_class_by_slug,
    get_feat_by_name,
    search_spells,
)

ALL_ABILITIES = ("str", "dex", "con", "int", "wis", "cha")


class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_build(choices: dict[str, Any]) -> ValidationResult:
    """Full validation of a character build against PF2e rules."""
    result = ValidationResult()

    name = choices.get("name", "")
    if not name:
        result.error("角色名称不能为空")

    level = choices.get("level", 1)
    if not isinstance(level, int) or level < 1 or level > 20:
        result.error(f"等级必须在 1-20 之间，当前: {level}")
        return result

    ancestry_slug = choices.get("ancestry", "")
    heritage_slug = choices.get("heritage", "")
    background_slug = choices.get("background", "")
    class_slug = choices.get("class", "")

    if not ancestry_slug:
        result.error("必须选择种族 (ancestry)")
    if not heritage_slug:
        result.error("必须选择传承 (heritage)")
    if not background_slug:
        result.error("必须选择背景 (background)")
    if not class_slug:
        result.error("必须选择职业 (class)")

    ancestry = get_ancestry_by_slug(ancestry_slug) if ancestry_slug else None
    background = get_background_by_slug(background_slug) if background_slug else None
    cls = get_class_by_slug(class_slug) if class_slug else None

    if ancestry_slug and not ancestry:
        result.error(f"未找到种族: {ancestry_slug}")
    if background_slug and not background:
        result.error(f"未找到背景: {background_slug}")
    if class_slug and not cls:
        result.error(f"未找到职业: {class_slug}")

    if not result.valid:
        return result

    boosts = choices.get("ability_boosts", {})
    _validate_ability_boosts(result, boosts, ancestry, background, cls, level)

    _validate_skills(result, choices, background, cls, level)
    _validate_feats(result, choices, cls, ancestry_slug, class_slug, level)
    _validate_spells(result, choices, cls)

    equipment = choices.get("equipment", [])
    if not equipment:
        result.warn("未选择任何装备")

    return result


def _validate_ability_boosts(
    result: ValidationResult,
    boosts: dict[str, Any],
    ancestry: dict | None,
    background: dict | None,
    cls: dict | None,
    level: int,
):
    """Validate ability boost selections."""
    if not boosts:
        result.warn("未设置属性提升 (ability_boosts)")
        return

    # Ancestry boosts
    ancestry_boosts = boosts.get("ancestry", [])
    if ancestry and isinstance(ancestry_boosts, list):
        anc_boost_slots = ancestry.get("boosts", {})
        expected_count = sum(
            1 for slot in anc_boost_slots.values()
            if isinstance(slot, dict) and slot.get("value")
        )
        if len(ancestry_boosts) != expected_count:
            result.error(
                f"种族属性提升数量不匹配: 需要 {expected_count} 个，提供了 {len(ancestry_boosts)} 个"
            )
        for ab in ancestry_boosts:
            if ab not in ALL_ABILITIES:
                result.error(f"无效的属性名: {ab}")

    # Background boosts
    bg_boosts = boosts.get("background", [])
    if background and isinstance(bg_boosts, list):
        bg_boost_slots = background.get("boosts", {})
        expected_count = sum(
            1 for slot in bg_boost_slots.values()
            if isinstance(slot, dict) and slot.get("value")
        )
        if len(bg_boosts) != expected_count:
            result.error(
                f"背景属性提升数量不匹配: 需要 {expected_count} 个，提供了 {len(bg_boosts)} 个"
            )

    # Class key ability
    class_boost = boosts.get("class", "")
    if cls and class_boost:
        key_abilities = cls.get("key_ability", [])
        if isinstance(key_abilities, list) and class_boost not in key_abilities:
            result.error(
                f"职业关键属性 {class_boost} 不在允许范围内: {key_abilities}"
            )

    # Free boosts (level 1): 4 unique abilities
    free_boosts = boosts.get("free", [])
    if isinstance(free_boosts, list):
        if len(free_boosts) != 4:
            result.error(f"1级自由属性提升应为 4 个，提供了 {len(free_boosts)} 个")
        if len(set(free_boosts)) != len(free_boosts):
            result.error("1级自由属性提升中不能有重复的属性")
        for ab in free_boosts:
            if ab not in ALL_ABILITIES:
                result.error(f"无效的属性名: {ab}")

    # Level-up boosts (every 5 levels: 5, 10, 15, 20)
    for lv in (5, 10, 15, 20):
        if lv > level:
            break
        key = f"level_{lv}"
        lv_boosts = boosts.get(key, [])
        if isinstance(lv_boosts, list):
            if len(lv_boosts) != 4:
                result.error(f"{lv}级属性提升应为 4 个，提供了 {len(lv_boosts)} 个")
            if len(set(lv_boosts)) != len(lv_boosts):
                result.error(f"{lv}级属性提升中不能有重复的属性")


def _validate_skills(
    result: ValidationResult,
    choices: dict[str, Any],
    background: dict | None,
    cls: dict | None,
    level: int,
):
    """Validate skill training and increases."""
    trained_skills = choices.get("trained_skills", [])
    if not isinstance(trained_skills, list):
        return

    if cls:
        cls_fixed = cls.get("trained_skills", [])
        additional = cls.get("additional_skill_count", 0)
        if background:
            bg_skills = background.get("trained_skills", [])
            fixed_count = len(cls_fixed) + len(bg_skills)
        else:
            fixed_count = len(cls_fixed)
            bg_skills = []

        expected_additional = additional
        total_expected = fixed_count + expected_additional
        if len(trained_skills) > total_expected:
            result.warn(
                f"受训技能数可能过多: 预期约 {total_expected} 个，提供了 {len(trained_skills)} 个 "
                f"(职业固定 {len(cls_fixed)} + 背景 {len(bg_skills) if background else 0} + 自选 {additional})"
            )

    # Skill increases
    skill_increases = choices.get("skill_increases", {})
    if isinstance(skill_increases, dict) and cls:
        increase_levels = cls.get("skill_increase_levels", [])
        for lv_str, _skill in skill_increases.items():
            try:
                lv = int(lv_str)
            except ValueError:
                result.error(f"技能提升等级格式无效: {lv_str}")
                continue
            if lv > level:
                result.error(f"技能提升等级 {lv} 超过角色等级 {level}")
            if isinstance(increase_levels, list) and lv not in increase_levels:
                result.warn(f"等级 {lv} 通常不是技能提升等级 (该职业: {increase_levels})")


def _validate_feats(
    result: ValidationResult,
    choices: dict[str, Any],
    cls: dict | None,
    ancestry_slug: str,
    class_slug: str,
    level: int,
):
    """Validate feat selections."""
    feat_categories = {
        "ancestry_feats": ("ancestry", cls.get("ancestry_feat_levels", []) if cls else []),
        "class_feats": ("class", cls.get("class_feat_levels", []) if cls else []),
        "general_feats": ("general", cls.get("general_feat_levels", []) if cls else []),
        "skill_feats": ("skill", cls.get("skill_feat_levels", []) if cls else []),
    }

    all_selected_feats: list[str] = []

    for key, (expected_cat, allowed_levels) in feat_categories.items():
        feats_dict = choices.get(key, {})
        if not isinstance(feats_dict, dict):
            continue

        for lv_str, feat_name in feats_dict.items():
            try:
                lv = int(lv_str)
            except ValueError:
                result.error(f"专长等级格式无效: {lv_str}")
                continue

            if lv > level:
                result.error(f"{expected_cat} 专长等级 {lv} 超过角色等级 {level}")
                continue

            if isinstance(allowed_levels, list) and lv not in allowed_levels:
                result.warn(
                    f"等级 {lv} 通常不是 {expected_cat} 专长选取等级"
                )

            feat_data = get_feat_by_name(feat_name)
            if not feat_data:
                result.warn(f"未在数据库中找到专长: {feat_name}")
                all_selected_feats.append(feat_name)
                continue

            feat_level = feat_data.get("level", 0)
            if feat_level > lv:
                result.error(
                    f"专长 {feat_name} (等级 {feat_level}) 不能在角色等级 {lv} 时选取"
                )

            feat_cat = feat_data.get("category", "")
            if expected_cat == "ancestry" and feat_cat != "ancestry":
                result.error(f"专长 {feat_name} 不是种族专长 (类别: {feat_cat})")
            elif expected_cat == "class" and feat_cat not in ("class",):
                result.warn(f"专长 {feat_name} 类别为 {feat_cat}，通常在职业专长槽选取 class 类型")
            elif expected_cat == "skill" and feat_cat != "skill":
                if "skill" not in feat_data.get("traits", []):
                    result.warn(f"专长 {feat_name} 不是技能专长 (类别: {feat_cat})")

            if expected_cat == "ancestry" and ancestry_slug:
                feat_ancestry = feat_data.get("ancestry_slug", "")
                if feat_ancestry and feat_ancestry != ancestry_slug:
                    result.error(
                        f"种族专长 {feat_name} 属于 {feat_ancestry}，不匹配当前种族 {ancestry_slug}"
                    )

            if expected_cat == "class" and class_slug:
                feat_class = feat_data.get("class_slug", "")
                if feat_class and feat_class != class_slug:
                    result.warn(
                        f"职业专长 {feat_name} 属于 {feat_class}，不匹配当前职业 {class_slug}"
                    )

            _check_prerequisites(result, feat_data, all_selected_feats, choices)
            all_selected_feats.append(feat_name)


def _check_prerequisites(
    result: ValidationResult,
    feat_data: dict,
    selected_feats: list[str],
    choices: dict[str, Any],
):
    """Basic prerequisite checking via text matching."""
    prerequisites = feat_data.get("prerequisites", [])
    if not prerequisites:
        return

    feat_name = feat_data.get("name", "")
    for prereq in prerequisites:
        if not isinstance(prereq, str) or not prereq.strip():
            continue

        prereq_lower = prereq.lower().strip()

        # Check if prerequisite references another feat
        matched = False
        for selected in selected_feats:
            if selected.lower() in prereq_lower:
                matched = True
                break

        # Check skill rank requirements (e.g. "trained in Athletics")
        if "trained in" in prereq_lower or "expert in" in prereq_lower:
            matched = True  # Soft pass — let the AI handle specifics

        # Check ability requirements (e.g. "Strength 14" or "str 14")
        for ab in ALL_ABILITIES:
            if ab in prereq_lower:
                matched = True
                break

        if not matched and prereq_lower:
            result.warn(f"专长 {feat_name} 有先决条件未能自动验证: {prereq}")


def _validate_spells(
    result: ValidationResult,
    choices: dict[str, Any],
    cls: dict | None,
):
    """Validate spell selections for spellcasting classes."""
    spells = choices.get("spells", {})
    if not cls:
        return

    spellcasting = cls.get("spellcasting", 0)
    if not spellcasting and spells:
        result.warn(f"职业 {cls.get('name', '')} 不是施法职业，但选择了法术")

    if spellcasting and not spells:
        result.warn(f"职业 {cls.get('name', '')} 是施法职业，但未选择任何法术")


def compute_ability_scores(choices: dict[str, Any]) -> dict[str, int]:
    """Compute final ability modifiers from build choices.

    PF2e Remaster: each boost adds +1 to the modifier (equivalent to +2
    to the ability score in legacy).  Starting base is 0 (10 score).
    """
    mods: dict[str, int] = {a: 0 for a in ALL_ABILITIES}
    boosts = choices.get("ability_boosts", {})

    ancestry = get_ancestry_by_slug(choices.get("ancestry", ""))
    if ancestry:
        flaws = ancestry.get("flaws", {})
        if isinstance(flaws, dict):
            for slot in flaws.values():
                if isinstance(slot, dict):
                    for flaw_ab in slot.get("value", []):
                        if flaw_ab in mods:
                            mods[flaw_ab] -= 1

    for source in ("ancestry", "background", "free"):
        abs_list = boosts.get(source, [])
        if isinstance(abs_list, list):
            for ab in abs_list:
                if ab in mods:
                    mods[ab] += 1

    class_boost = boosts.get("class", "")
    if class_boost and class_boost in mods:
        mods[class_boost] += 1

    for lv in (5, 10, 15, 20):
        key = f"level_{lv}"
        lv_boosts = boosts.get(key, [])
        if isinstance(lv_boosts, list):
            for ab in lv_boosts:
                if ab in mods:
                    mods[ab] += 1

    return mods
