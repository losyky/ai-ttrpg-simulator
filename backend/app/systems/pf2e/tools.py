"""PF2e AI Tools — merged charbuilder + rulebook tools for AI agents.

Character Builder tools enable AI agents to query PF2e options,
validate builds, and assemble complete character sheets.

Rulebook tools provide structured DB lookup with vector search fallback.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.tools import tool

from app.systems.pf2e import charbuilder_db as db
from app.systems.pf2e.build_validator import validate_build as _validate, compute_ability_scores
from app.systems.pf2e.ruledb import (
    lookup_by_name,
    lookup_creature,
    fulltext_search,
)
from app.services.vectorstore import search as vector_search


# ===========================================================================
# Rulebook tools
# ===========================================================================

def _format_entry(e: dict) -> str:
    parts = [f"【{e.get('category', '')}】{e.get('name_zh', '')} ({e.get('name_en', '')})"]
    if e.get("prerequisites"):
        parts.append(f"前置条件: {e['prerequisites']}")
    if e.get("duration"):
        parts.append(f"持续时间: {e['duration']}")
    if e.get("target"):
        parts.append(f"目标: {e['target']}")
    if e.get("cost"):
        parts.append(f"花费: {e['cost']}")
    if e.get("description"):
        parts.append(e["description"][:1000])
    return "\n".join(parts)


def _format_creature(c: dict) -> str:
    parts = [f"【生物】{c.get('name_zh', '')} ({c.get('name_en', '')})"]
    if c.get("public_notes"):
        parts.append(c["public_notes"][:1000])
    return "\n".join(parts)


@tool
def rulebook_search(query: str, category: str = "") -> str:
    """Search the PF2e rulebook for rules, feats, spells, conditions, creatures, etc.

    Uses the structured database for precise lookups. Falls back to
    semantic search if no exact match is found.

    Args:
        query: The name or description to search for, e.g. "惊惧", "Fireball", "抓取规则".
        category: Optional filter — one of: feat, spell, action, condition,
                  equipment, creature, ancestry, class, heritage, archetype,
                  background, deity, hazard, effect, or empty for all.
    """
    results: list[str] = []

    # Layer 1: Exact / prefix name match
    cat = category if category else None
    entries = lookup_by_name(query, category=cat, limit=5)
    creatures = lookup_creature(query, limit=3) if not cat or cat == "creature" else []

    if entries:
        results.extend(_format_entry(e) for e in entries)
    if creatures:
        results.extend(_format_creature(c) for c in creatures)

    if results:
        return "\n\n---\n\n".join(results)

    # Layer 2: Full-text search (SQLite FTS5)
    fts_hits = fulltext_search(query, category=cat, limit=5)
    if fts_hits:
        results.extend(_format_entry(e) for e in fts_hits)
        return "\n\n---\n\n".join(results)

    # Layer 3: Semantic vector search (fallback)
    vec_hits = vector_search(query, n_results=4)
    if vec_hits:
        for hit in vec_hits:
            name = hit["metadata"].get("name", "")
            label = hit["metadata"].get("label", "")
            header = f"[{label}] {name}" if name else "搜索结果"
            results.append(f"--- {header} ---\n{hit['text'][:800]}")
        return "\n\n".join(results)

    return "未找到相关规则。请确认搜索词或尝试不同的表述。"


@tool
def rulebook_lookup(name: str) -> str:
    """Look up a specific PF2e rule entry by its exact name (Chinese or English).

    Use this when you know the exact name of a feat, spell, condition, etc.

    Args:
        name: Exact name to look up, e.g. "惊惧", "Shield Block", "火球术".
    """
    entries = lookup_by_name(name, limit=3)
    creatures = lookup_creature(name, limit=2)

    results: list[str] = []
    if entries:
        results.extend(_format_entry(e) for e in entries)
    if creatures:
        results.extend(_format_creature(c) for c in creatures)

    if results:
        return "\n\n---\n\n".join(results)
    return f"未找到名为「{name}」的规则条目。"


# ===========================================================================
# Character Builder query tools
# ===========================================================================

@tool
def cb_search_ancestries(query: str = "") -> str:
    """Search PF2e ancestries (种族) for character creation.

    Returns a list of available ancestries with HP, size, speed, vision,
    and ability boost/flaw summary.

    Args:
        query: Optional search term to filter by name.
    """
    rows = db.search_ancestries(query)
    if not rows:
        return "未找到匹配的种族。"

    lines = [f"找到 {len(rows)} 个种族：\n"]
    for r in rows:
        boosts = r.get("boosts", {})
        flaws = r.get("flaws", {})
        boost_summary = _summarize_boosts(boosts)
        flaw_summary = _summarize_flaws(flaws)
        traits = ", ".join(r.get("traits", []))

        line = (
            f"- **{r['name']}** (`{r['slug']}`): "
            f"HP {r['hp']}, 速度 {r['speed']}, 体型 {r['size']}, "
            f"视觉 {r['vision']}"
        )
        if boost_summary:
            line += f", 提升 {boost_summary}"
        if flaw_summary:
            line += f", 缺陷 {flaw_summary}"
        if traits:
            line += f", 特性 [{traits}]"
        lines.append(line)

    return "\n".join(lines)


@tool
def cb_search_heritages(ancestry_slug: str) -> str:
    """Search PF2e heritages (传承) available for a given ancestry.

    Also includes versatile heritages that can apply to any ancestry.

    Args:
        ancestry_slug: The slug of the ancestry (e.g., "human", "elf").
    """
    rows = db.search_heritages(ancestry_slug, include_versatile=True)
    if not rows:
        return f"未找到 {ancestry_slug} 的传承。"

    specific = [r for r in rows if r.get("ancestry_slug")]
    versatile = [r for r in rows if not r.get("ancestry_slug")]

    lines = []
    if specific:
        lines.append(f"**{ancestry_slug} 专属传承** ({len(specific)} 个)：")
        for r in specific:
            desc_preview = r.get("description", "")[:100]
            lines.append(f"- **{r['name']}** (`{r['slug']}`): {desc_preview}...")

    if versatile:
        lines.append(f"\n**通用传承** ({len(versatile)} 个)：")
        for r in versatile[:10]:
            desc_preview = r.get("description", "")[:80]
            lines.append(f"- **{r['name']}** (`{r['slug']}`): {desc_preview}...")
        if len(versatile) > 10:
            lines.append(f"  ...及其他 {len(versatile) - 10} 个")

    return "\n".join(lines)


@tool
def cb_search_backgrounds(query: str = "", skill: str = "") -> str:
    """Search PF2e backgrounds (背景) for character creation.

    Args:
        query: Optional search term to filter by name.
        skill: Optional skill slug to find backgrounds that train it.
    """
    rows = db.search_backgrounds(query, skill)
    if not rows:
        return "未找到匹配的背景。"

    lines = [f"找到 {len(rows)} 个背景：\n"]
    for r in rows[:30]:
        boost_summary = _summarize_boosts(r.get("boosts", {}))
        skills = r.get("trained_skills", [])
        lore = r.get("lore", [])
        feats = r.get("granted_feat_names", [])

        line = f"- **{r['name']}** (`{r['slug']}`)"
        if boost_summary:
            line += f": 提升 {boost_summary}"
        if skills:
            line += f", 技能 {', '.join(skills)}"
        if lore:
            line += f", 学识 {', '.join(lore)}"
        if feats:
            line += f", 专长 {', '.join(feats)}"
        lines.append(line)

    if len(rows) > 30:
        lines.append(f"\n...共 {len(rows)} 个结果，显示前 30 个")

    return "\n".join(lines)


@tool
def cb_search_classes(query: str = "") -> str:
    """Search PF2e classes (职业) for character creation.

    Returns key class features: HP/level, key ability, spellcasting, etc.

    Args:
        query: Optional search term to filter by name.
    """
    rows = db.search_classes(query)
    if not rows:
        return "未找到匹配的职业。"

    lines = [f"找到 {len(rows)} 个职业：\n"]
    for r in rows:
        key_ab = ", ".join(r.get("key_ability", []))
        saves = r.get("saves", {})
        save_str = ", ".join(
            f"{k}={v}" for k, v in saves.items() if isinstance(v, (int, float))
        )
        casting = "有" if r.get("spellcasting") else "无"
        ts = r.get("trained_skills", [])
        additional = r.get("additional_skill_count", 0)

        line = (
            f"- **{r['name']}** (`{r['slug']}`): "
            f"HP/级 {r['hp_per_level']}, 关键属性 [{key_ab}], "
            f"察觉 {r['perception_rank']}, 施法 {casting}"
        )
        if save_str:
            line += f", 豁免 [{save_str}]"
        if ts:
            line += f", 固定技能 {', '.join(ts)}"
        line += f", 额外技能 {additional}"
        lines.append(line)

    return "\n".join(lines)


@tool
def cb_search_feats(
    category: str = "",
    level_max: int = 0,
    class_slug: str = "",
    ancestry_slug: str = "",
    query: str = "",
) -> str:
    """Search PF2e feats (专长) with filters.

    Args:
        category: Feat category — "ancestry", "class", "general", "skill", or "" for all.
        level_max: Maximum feat level to include (0 = no limit).
        class_slug: Filter by class slug (e.g., "fighter").
        ancestry_slug: Filter by ancestry slug (e.g., "human").
        query: Search text in feat name or description.
    """
    rows = db.search_feats(
        category=category,
        level_max=level_max,
        class_slug=class_slug,
        ancestry_slug=ancestry_slug,
        query=query,
        limit=30,
    )
    if not rows:
        return "未找到匹配的专长。"

    lines = [f"找到专长（最多显示 30 个）：\n"]
    for r in rows:
        traits = r.get("traits", [])
        prereqs = r.get("prerequisites", [])
        action = r.get("action_type", "")

        line = f"- **{r['name']}** (Lv.{r['level']}, {r['category']})"
        if action and action != "passive":
            line += f" [{action}]"
        if traits:
            line += f" 特性: {', '.join(traits[:5])}"
        if prereqs:
            line += f" | 先决: {'; '.join(prereqs[:3])}"
        desc = r.get("description", "")[:80]
        if desc:
            line += f" — {desc}..."
        lines.append(line)

    return "\n".join(lines)


@tool
def cb_search_spells(
    tradition: str = "",
    rank_max: int = 0,
    query: str = "",
) -> str:
    """Search PF2e spells (法术) with filters.

    Args:
        tradition: Spell tradition — "arcane", "divine", "occult", "primal", or "" for all.
        rank_max: Maximum spell rank (0 = cantrips only if combined with query).
        query: Search text in spell name or description.
    """
    rows = db.search_spells(tradition=tradition, rank_max=rank_max, query=query, limit=30)
    if not rows:
        return "未找到匹配的法术。"

    lines = [f"找到法术（最多显示 30 个）：\n"]
    for r in rows:
        traditions = ", ".join(r.get("traditions", []))
        traits = r.get("traits", [])[:5]

        rank_label = f"环位 {r['rank']}" if r['rank'] > 0 else "戏法"
        line = f"- **{r['name']}** ({rank_label}, {traditions})"
        if r.get("action_cost"):
            line += f" [{r['action_cost']}动作]"
        if r.get("range"):
            line += f" 距离:{r['range']}"
        if r.get("defense"):
            line += f" 豁免:{r['defense']}"
        if traits:
            line += f" 特性: {', '.join(traits)}"
        desc = r.get("description", "")[:60]
        if desc:
            line += f" — {desc}..."
        lines.append(line)

    return "\n".join(lines)


@tool
def cb_search_equipment(
    item_type: str = "",
    category: str = "",
    query: str = "",
) -> str:
    """Search PF2e equipment (装备) for character creation.

    Args:
        item_type: Item type — "weapon", "armor", "shield", "equipment", "consumable", "kit", or "" for all.
        category: Sub-category — "simple"/"martial" for weapons, "light"/"medium"/"heavy" for armor, or "".
        query: Search text in item name.
    """
    rows = db.search_equipment(item_type=item_type, category=category, query=query, limit=30)
    if not rows:
        return "未找到匹配的装备。"

    lines = [f"找到装备（最多显示 30 个）：\n"]
    for r in rows:
        price = _format_price(r.get("price_cp", 0))
        line = f"- **{r['name']}** (`{r['slug']}`, {r['item_type']}"
        if r.get("category"):
            line += f"/{r['category']}"
        line += f") 价格: {price}"
        if r.get("damage"):
            line += f", 伤害: {r['damage']}"
        if r.get("ac_bonus"):
            line += f", AC+{r['ac_bonus']}"
        if r.get("dex_cap", 99) < 99:
            line += f", 敏捷上限+{r['dex_cap']}"
        if r.get("bulk"):
            line += f", 负重: {r['bulk']}"
        lines.append(line)

    return "\n".join(lines)


@tool
def cb_get_class_progression(class_slug: str, target_level: int = 1) -> str:
    """Get the full level-by-level progression for a PF2e class.

    Shows what the class gains at each level and what choices the player
    needs to make (feat slots, skill increases, etc.).

    Args:
        class_slug: The class slug (e.g., "fighter", "wizard").
        target_level: Show progression from level 1 to this level (1-20).
    """
    cls = db.get_class_by_slug(class_slug)
    if not cls:
        return f"未找到职业: {class_slug}"

    target_level = max(1, min(20, target_level))

    ancestry_feat_lvls = set(cls.get("ancestry_feat_levels", []))
    class_feat_lvls = set(cls.get("class_feat_levels", []))
    general_feat_lvls = set(cls.get("general_feat_levels", []))
    skill_feat_lvls = set(cls.get("skill_feat_levels", []))
    skill_inc_lvls = set(cls.get("skill_increase_levels", []))

    features = cls.get("class_features", [])
    features_by_level: dict[int, list[str]] = {}
    for f in features:
        lv = f.get("level", 0)
        features_by_level.setdefault(lv, []).append(f.get("name", ""))

    lines = [
        f"**{cls['name']}** 进阶表 (1-{target_level}级)",
        f"HP/级: {cls['hp_per_level']}, 关键属性: {cls.get('key_ability', [])}",
        "",
    ]

    for lv in range(1, target_level + 1):
        parts = []

        feats_at_level = features_by_level.get(lv, [])
        if feats_at_level:
            parts.append(f"职业特性: {', '.join(feats_at_level)}")

        choices = []
        if lv in ancestry_feat_lvls:
            choices.append("种族专长")
        if lv in class_feat_lvls:
            choices.append("职业专长")
        if lv in general_feat_lvls:
            choices.append("一般专长")
        if lv in skill_feat_lvls:
            choices.append("技能专长")
        if lv in skill_inc_lvls:
            choices.append("技能提升")
        if lv in (5, 10, 15, 20):
            choices.append("属性提升x4")

        if choices:
            parts.append(f"选择: {', '.join(choices)}")

        if parts:
            lines.append(f"**Lv.{lv}**: {' | '.join(parts)}")
        else:
            lines.append(f"**Lv.{lv}**: (无额外选择)")

    return "\n".join(lines)


# ===========================================================================
# Character Builder build tools
# ===========================================================================

@tool
def cb_get_build_requirements(
    class_slug: str,
    ancestry_slug: str,
    background_slug: str,
    level: int = 1,
) -> str:
    """Get a checklist of all choices required to build a character.

    Args:
        class_slug: Class slug (e.g., "fighter").
        ancestry_slug: Ancestry slug (e.g., "human").
        background_slug: Background slug (e.g., "acolyte").
        level: Target character level (1-20).
    """
    cls = db.get_class_by_slug(class_slug)
    ancestry = db.get_ancestry_by_slug(ancestry_slug)
    background = db.get_background_by_slug(background_slug)

    if not cls:
        return f"未找到职业: {class_slug}"
    if not ancestry:
        return f"未找到种族: {ancestry_slug}"
    if not background:
        return f"未找到背景: {background_slug}"

    level = max(1, min(20, level))
    lines = [
        f"## {ancestry['name']} {cls['name']} Lv.{level} (背景: {background['name']}) 建卡清单\n",
    ]

    # 1. Heritage
    lines.append("### 1. 传承 (Heritage)")
    lines.append(f"   从 {ancestry_slug} 的传承中选择一个\n")

    # 2. Ability boosts
    lines.append("### 2. 属性提升 (Ability Boosts)")
    anc_boosts = ancestry.get("boosts", {})
    anc_boost_count = sum(1 for s in anc_boosts.values() if isinstance(s, dict) and s.get("value"))
    anc_flaws = ancestry.get("flaws", {})
    flaw_list = []
    for slot in anc_flaws.values():
        if isinstance(slot, dict):
            flaw_list.extend(slot.get("value", []))

    lines.append(f"   - 种族提升: {anc_boost_count} 个选择")
    for idx, (k, slot) in enumerate(sorted(anc_boosts.items())):
        if isinstance(slot, dict) and slot.get("value"):
            opts = slot["value"]
            if len(opts) == 6:
                lines.append(f"     槽{idx}: 自由选择")
            else:
                lines.append(f"     槽{idx}: 从 {', '.join(opts)} 中选择")
    if flaw_list:
        lines.append(f"   - 种族缺陷: {', '.join(flaw_list)} (自动应用)")

    bg_boosts = background.get("boosts", {})
    bg_boost_count = sum(1 for s in bg_boosts.values() if isinstance(s, dict) and s.get("value"))
    lines.append(f"   - 背景提升: {bg_boost_count} 个选择")
    for idx, (k, slot) in enumerate(sorted(bg_boosts.items())):
        if isinstance(slot, dict) and slot.get("value"):
            opts = slot["value"]
            if len(opts) == 6:
                lines.append(f"     槽{idx}: 自由选择")
            else:
                lines.append(f"     槽{idx}: 从 {', '.join(opts)} 中选择")

    key_abs = cls.get("key_ability", [])
    lines.append(f"   - 职业关键属性: 从 {', '.join(key_abs)} 中选择")
    lines.append("   - 1级自由提升: 4 个不重复属性")

    for lv in (5, 10, 15, 20):
        if lv <= level:
            lines.append(f"   - {lv}级属性提升: 4 个不重复属性")

    # 3. Skills
    lines.append("\n### 3. 技能训练 (Skills)")
    cls_skills = cls.get("trained_skills", [])
    bg_skills = background.get("trained_skills", [])
    additional = cls.get("additional_skill_count", 0)
    lines.append(f"   - 职业固定技能: {', '.join(cls_skills) if cls_skills else '无'}")
    lines.append(f"   - 背景固定技能: {', '.join(bg_skills) if bg_skills else '无'}")
    bg_lore = background.get("lore", [])
    if bg_lore:
        lines.append(f"   - 背景学识: {', '.join(bg_lore)}")
    lines.append(f"   - 额外自选受训技能: {additional} 个")

    skill_inc_levels = cls.get("skill_increase_levels", [])
    inc_at = [lv for lv in skill_inc_levels if lv <= level]
    if inc_at:
        lines.append(f"   - 技能提升等级: {', '.join(str(l) for l in inc_at)}")

    # 4. Feats
    lines.append("\n### 4. 专长 (Feats)")
    for cat_name, cat_key in [
        ("种族专长", "ancestry_feat_levels"),
        ("职业专长", "class_feat_levels"),
        ("一般专长", "general_feat_levels"),
        ("技能专长", "skill_feat_levels"),
    ]:
        levels = [lv for lv in cls.get(cat_key, []) if lv <= level]
        if levels:
            lines.append(f"   - {cat_name}: 在等级 {', '.join(str(l) for l in levels)} 各选一个")

    # 5. Granted feats
    bg_feats = background.get("granted_feat_names", [])
    if bg_feats:
        lines.append(f"\n   背景自动授予专长: {', '.join(bg_feats)}")

    # 6. Spells
    if cls.get("spellcasting"):
        lines.append("\n### 5. 法术 (Spells)")
        lines.append("   该职业可施法，需要选择已知法术/准备法术")

    # 7. Equipment
    lines.append("\n### 6. 装备 (Equipment)")
    lines.append("   选择起始武器、护甲和冒险者套装")

    # 8. Details
    lines.append("\n### 7. 角色细节 (Details)")
    lines.append("   名字、性别、年龄、信仰、背景故事")

    return "\n".join(lines)


@tool
def cb_validate_build(build_choices_json: str) -> str:
    """Validate a character build against PF2e rules.

    Checks ability boosts, skill training, feat legality, prerequisites,
    spell traditions, and more.

    Args:
        build_choices_json: JSON string of the build choices object.
    """
    try:
        choices = json.loads(build_choices_json)
    except json.JSONDecodeError as e:
        return f"JSON 解析失败: {e}"

    result = _validate(choices)
    lines = []

    if result.valid:
        lines.append("**构建合法** — 所有规则检查通过。")
    else:
        lines.append("**构建不合法** — 发现以下错误：")

    if result.errors:
        lines.append("\n**错误 (必须修复)：**")
        for err in result.errors:
            lines.append(f"  - {err}")

    if result.warnings:
        lines.append("\n**警告 (建议检查)：**")
        for w in result.warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)


@tool
def cb_assemble_character(build_choices_json: str) -> str:
    """Assemble a complete FVTT-format character from build choices and save it.

    First validates the build, then creates a full Actor JSON and saves
    it to the character library.

    Args:
        build_choices_json: JSON string of the build choices object.
            Required fields: name, level, ancestry, heritage, background,
            class, key_ability, ability_boosts.
            Optional: trained_skills, skill_increases, ancestry_feats,
            class_feats, general_feats, skill_feats, spells, equipment, details.
    """
    try:
        choices = json.loads(build_choices_json)
    except json.JSONDecodeError as e:
        return f"JSON 解析失败: {e}"

    # Validate first
    validation = _validate(choices)
    if not validation.valid:
        error_text = "\n".join(f"  - {e}" for e in validation.errors)
        return f"构建不合法，无法组装角色卡：\n{error_text}"

    # Compute ability scores
    mods = compute_ability_scores(choices)

    # Look up source data
    ancestry_slug = choices.get("ancestry", "")
    background_slug = choices.get("background", "")
    class_slug = choices.get("class", "")
    heritage_slug = choices.get("heritage", "")
    level = choices.get("level", 1)

    ancestry = db.get_ancestry_by_slug(ancestry_slug) or {}
    background = db.get_background_by_slug(background_slug) or {}
    cls = db.get_class_by_slug(class_slug) or {}

    # Build the FVTT Actor JSON
    actor_id = str(uuid.uuid4())[:16].replace("-", "")
    details = choices.get("details", {})

    # Compute HP
    ancestry_hp = ancestry.get("hp", 0)
    class_hp = cls.get("hp_per_level", 0)
    con_mod = mods.get("con", 0)
    total_hp = ancestry_hp + (class_hp + con_mod) * level

    # Build trained skills set
    cls_skills = set(cls.get("trained_skills", []))
    bg_skills = set(background.get("trained_skills", []))
    user_skills = set(choices.get("trained_skills", []))
    all_trained = cls_skills | bg_skills | user_skills

    # Build FVTT items array
    items = []

    # Ancestry item
    items.append({
        "type": "ancestry",
        "name": ancestry.get("name", ancestry_slug),
        "_id": _gen_id(),
        "system": {
            "hp": ancestry.get("hp", 0),
            "size": ancestry.get("size", "med"),
            "speed": ancestry.get("speed", 25),
            "vision": ancestry.get("vision", "normal"),
            "boosts": ancestry.get("boosts", {}),
            "flaws": ancestry.get("flaws", {}),
            "languages": {"value": ancestry.get("languages", [])},
            "traits": {"rarity": "common", "value": ancestry.get("traits", [])},
        },
    })

    # Heritage item
    items.append({
        "type": "heritage",
        "name": heritage_slug.replace("-", " ").title(),
        "_id": _gen_id(),
        "system": {
            "ancestry": {"slug": ancestry_slug},
        },
    })

    # Background item
    items.append({
        "type": "background",
        "name": background.get("name", background_slug),
        "_id": _gen_id(),
        "system": {
            "boosts": background.get("boosts", {}),
            "trainedSkills": {
                "value": list(bg_skills),
                "lore": background.get("lore", []),
            },
        },
    })

    # Class item
    items.append({
        "type": "class",
        "name": cls.get("name", class_slug),
        "_id": _gen_id(),
        "system": {
            "hp": cls.get("hp_per_level", 0),
            "keyAbility": {
                "value": cls.get("key_ability", []),
                "selected": choices.get("key_ability", ""),
            },
            "perception": cls.get("perception_rank", 0),
            "savingThrows": cls.get("saves", {}),
            "attacks": cls.get("attacks", {}),
            "defenses": cls.get("defenses", {}),
            "trainedSkills": {
                "value": list(cls_skills),
                "additional": cls.get("additional_skill_count", 0),
            },
            "spellcasting": cls.get("spellcasting", 0),
        },
    })

    # Feat items
    for feat_key in ("ancestry_feats", "class_feats", "general_feats", "skill_feats"):
        feats_dict = choices.get(feat_key, {})
        if isinstance(feats_dict, dict):
            for _lv, fname in feats_dict.items():
                feat_data = db.get_feat_by_name(fname)
                items.append({
                    "type": "feat",
                    "name": fname,
                    "_id": _gen_id(),
                    "system": {
                        "category": feat_data.get("category", "") if feat_data else feat_key.replace("_feats", ""),
                        "level": {"value": feat_data.get("level", 0) if feat_data else 0},
                        "traits": {"value": feat_data.get("traits", []) if feat_data else []},
                        "description": {"value": feat_data.get("description", "") if feat_data else ""},
                    },
                })

    # Lore skills from background
    for lore_name in background.get("lore", []):
        items.append({
            "type": "lore",
            "name": lore_name,
            "_id": _gen_id(),
            "system": {
                "proficient": {"value": 1},
            },
        })

    # Equipment items
    for eq_slug in choices.get("equipment", []):
        eq_rows = db.search_equipment(query=eq_slug, limit=1)
        if eq_rows:
            eq = eq_rows[0]
            items.append({
                "type": eq["item_type"],
                "name": eq["name"],
                "_id": _gen_id(),
                "system": {
                    "quantity": 1,
                    "description": {"value": eq.get("description", "")[:200]},
                },
            })
        else:
            items.append({
                "type": "equipment",
                "name": eq_slug,
                "_id": _gen_id(),
                "system": {"quantity": 1},
            })

    # Assemble the full Actor
    actor = {
        "_id": actor_id,
        "name": choices.get("name", "New Character"),
        "type": "character",
        "img": "icons/svg/mystery-man.svg",
        "system": {
            "details": {
                "level": {"value": level},
                "keyability": {"value": choices.get("key_ability", "")},
                "biography": {
                    "backstory": details.get("backstory", ""),
                },
                "age": {"value": details.get("age", "")},
                "gender": {"value": details.get("gender", "")},
                "deity": {"value": details.get("deity", "")},
            },
            "attributes": {
                "hp": {
                    "value": total_hp,
                    "max": total_hp,
                    "temp": 0,
                },
                "speed": {"value": ancestry.get("speed", 25)},
            },
            "abilities": {
                ab: {"mod": val} for ab, val in mods.items()
            },
            "resources": {
                "heroPoints": {"value": 1},
            },
            "build": {
                "attributes": {
                    "boosts": _build_boosts_map(choices),
                },
            },
        },
        "items": items,
    }

    # Save to character store
    from app.models.character import parse_fvtt_actor
    from app.routers.characters import _characters, _raw_data
    import json as _json
    from pathlib import Path
    from app.config import settings

    sheet = parse_fvtt_actor(actor)
    sheet.id = actor_id
    _characters[actor_id] = sheet
    _raw_data[actor_id] = actor

    char_dir = Path(settings.data_dir) / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / f"{actor_id}.json").write_text(
        _json.dumps(actor, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    warnings_text = ""
    if validation.warnings:
        warnings_text = "\n警告:\n" + "\n".join(f"  - {w}" for w in validation.warnings)

    return (
        f"角色 **{choices.get('name', 'New Character')}** 创建成功！\n"
        f"ID: `{actor_id}`\n"
        f"等级 {level} {ancestry.get('name', '')} {cls.get('name', '')}\n"
        f"HP: {total_hp}, 力{mods['str']} 敏{mods['dex']} 体{mods['con']} "
        f"智{mods['int']} 感{mods['wis']} 魅{mods['cha']}\n"
        f"受训技能: {', '.join(sorted(all_trained))}"
        + warnings_text
    )


# ===========================================================================
# Helpers
# ===========================================================================

def _gen_id() -> str:
    return uuid.uuid4().hex[:16]


def _summarize_boosts(boosts: dict) -> str:
    if not isinstance(boosts, dict):
        return ""
    parts = []
    for _k, slot in sorted(boosts.items()):
        if not isinstance(slot, dict):
            continue
        value = slot.get("value", [])
        if not value:
            continue
        if len(value) == 6:
            parts.append("自由")
        else:
            parts.append("/".join(value))
    return ", ".join(parts) if parts else ""


def _summarize_flaws(flaws: dict) -> str:
    if not isinstance(flaws, dict):
        return ""
    all_flaws = []
    for slot in flaws.values():
        if isinstance(slot, dict):
            all_flaws.extend(slot.get("value", []))
    return ", ".join(all_flaws) if all_flaws else ""


def _format_price(cp: int) -> str:
    if cp <= 0:
        return "—"
    if cp >= 100:
        gp = cp // 100
        remainder = cp % 100
        if remainder:
            return f"{gp} gp {remainder // 10} sp" if remainder >= 10 else f"{gp} gp {remainder} cp"
        return f"{gp} gp"
    if cp >= 10:
        return f"{cp // 10} sp"
    return f"{cp} cp"


def _build_boosts_map(choices: dict) -> dict:
    """Build the system.build.attributes.boosts map for FVTT Actor JSON."""
    boosts = choices.get("ability_boosts", {})
    result = {}

    free = boosts.get("free", [])
    if free:
        result["0"] = free

    for lv in (5, 10, 15, 20):
        key = f"level_{lv}"
        lv_boosts = boosts.get(key, [])
        if lv_boosts:
            result[str(lv)] = lv_boosts

    return result


# ===========================================================================
# NPC / Monster creation tools
# ===========================================================================

@tool
def cb_search_creatures(query: str = "", level: int | None = None, limit: int = 10) -> str:
    """Search the PF2e bestiary / NPC gallery for creatures to use as reference templates.

    Args:
        query: Name or keyword to search.
        level: Optional level filter.
        limit: Max results.
    """
    from app.systems.pf2e import ruledb
    rows = ruledb.search_rules(query=query, category="creature", limit=limit)
    if level is not None:
        rows = [r for r in rows if r.get("level") == level]
    if not rows:
        return f"未找到匹配 '{query}' 的生物。"
    lines = []
    for r in rows[:limit]:
        lines.append(f"- **{r.get('name_cn') or r['name']}** (Lv.{r.get('level', '?')}): {(r.get('description') or '')[:120]}")
    return "\n".join(lines)


@tool
def cb_assemble_npc(spec_json: str) -> str:
    """Assemble a PF2e NPC / monster card from a JSON specification and save it.

    The spec_json should contain:
    - name (str): NPC name
    - level (int): creature level
    - traits (list[str]): e.g. ["humanoid", "evil"]
    - hp (int): hit points
    - ac (int): armor class
    - abilities (dict): {"str": mod, "dex": mod, ...}
    - speeds (dict): {"land": 25, "fly": 40} etc.
    - attacks (list[dict]): [{"name": "Claw", "bonus": 12, "damage": "2d6+5 slashing"}]
    - specials (list[dict]): [{"name": "Ability Name", "description": "..."}]
    - perception (int): perception modifier
    - saves (dict): {"fortitude": 10, "reflex": 8, "will": 12}
    - skills (dict): {"athletics": 10, "stealth": 8}
    - description (str): optional
    """
    import json as _json
    try:
        spec = _json.loads(spec_json)
    except _json.JSONDecodeError as e:
        return f"JSON 解析失败: {e}"

    actor_id = uuid.uuid4().hex[:16]
    name = spec.get("name", "Unknown NPC")
    level = spec.get("level", 1)

    abilities_raw = spec.get("abilities", {})
    abilities = {}
    for ab in ("str", "dex", "con", "int", "wis", "cha"):
        abilities[ab] = {"mod": abilities_raw.get(ab, 0)}

    saves_raw = spec.get("saves", {})
    attacks = spec.get("attacks", [])
    specials = spec.get("specials", [])

    items = []
    for atk in attacks:
        items.append({
            "_id": _gen_id(),
            "type": "melee",
            "name": atk.get("name", "Attack"),
            "system": {
                "bonus": {"value": atk.get("bonus", 0)},
                "damageRolls": {"main": {"damage": atk.get("damage", "1d6"), "damageType": atk.get("type", "untyped")}},
                "traits": {"value": atk.get("traits", [])},
            },
        })
    for sp in specials:
        items.append({
            "_id": _gen_id(),
            "type": "action",
            "name": sp.get("name", "Special"),
            "system": {
                "description": {"value": sp.get("description", "")},
                "actionType": {"value": sp.get("action_type", "passive")},
            },
        })

    actor = {
        "_id": actor_id,
        "name": name,
        "type": "npc",
        "img": "icons/svg/mystery-man.svg",
        "system": {
            "details": {
                "level": {"value": level},
                "blurb": spec.get("description", ""),
            },
            "traits": {"value": spec.get("traits", [])},
            "attributes": {
                "hp": {"value": spec.get("hp", 10), "max": spec.get("hp", 10)},
                "ac": {"value": spec.get("ac", 15)},
                "speed": spec.get("speeds", {"value": 25}),
            },
            "abilities": abilities,
            "saves": {
                "fortitude": {"value": saves_raw.get("fortitude", 0)},
                "reflex": {"value": saves_raw.get("reflex", 0)},
                "will": {"value": saves_raw.get("will", 0)},
            },
            "perception": {"mod": spec.get("perception", 0)},
            "skills": {
                slug: {"base": mod} for slug, mod in spec.get("skills", {}).items()
            },
        },
        "items": items,
    }

    from app.models.character import parse_fvtt_actor
    from app.routers.characters import _characters, _raw_data
    from pathlib import Path
    from app.config import settings

    sheet = parse_fvtt_actor(actor)
    sheet.id = actor_id
    _characters[actor_id] = sheet
    _raw_data[actor_id] = actor

    char_dir = Path(settings.data_dir) / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / f"{actor_id}.json").write_text(
        _json.dumps(actor, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    return (
        f"NPC **{name}** (Lv.{level}) 创建成功！\n"
        f"ID: `{actor_id}`\n"
        f"HP: {spec.get('hp', 10)}, AC: {spec.get('ac', 15)}\n"
        f"攻击: {', '.join(a.get('name', '?') for a in attacks)}\n"
        f"特殊能力: {', '.join(s.get('name', '?') for s in specials)}"
    )


NPC_TOOLS = [cb_search_creatures, cb_assemble_npc]


# ===========================================================================
# Tool groupings for agent binding
# ===========================================================================

RULEBOOK_TOOLS = [rulebook_search, rulebook_lookup]

CHARBUILDER_QUERY_TOOLS = [
    cb_search_ancestries,
    cb_search_heritages,
    cb_search_backgrounds,
    cb_search_classes,
    cb_search_feats,
    cb_search_spells,
    cb_search_equipment,
    cb_get_class_progression,
    cb_get_build_requirements,
]

CHARBUILDER_BUILD_TOOLS = [
    cb_validate_build,
    cb_assemble_character,
]

CHARBUILDER_ALL_TOOLS = CHARBUILDER_QUERY_TOOLS + CHARBUILDER_BUILD_TOOLS
