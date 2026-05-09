"""FVTT inline markup parser for PF2e descriptions.

Converts @UUID[...], @Check[...], @Damage[...], @Template[...] and
other FVTT-specific markup into clean HTML suitable for frontend rendering.
"""

from __future__ import annotations

import re
from typing import Any

# Damage type translations
_DAMAGE_TYPES = {
    "fire": "火焰", "cold": "寒冷", "electricity": "闪电", "acid": "强酸",
    "sonic": "音波", "force": "力场", "poison": "毒素", "mental": "心灵",
    "bleed": "出血", "spirit": "灵魂", "vitality": "正能量", "void": "负能量",
    "bludgeoning": "钝击", "piercing": "穿刺", "slashing": "挥砍",
    "precision": "精准", "splash": "溅射", "persistent": "持续",
}

# Check type translations  
_CHECK_TYPES = {
    "athletics": "运动", "acrobatics": "体操", "arcana": "奥秘",
    "crafting": "制造", "deception": "欺骗", "diplomacy": "交涉",
    "intimidation": "威吓", "medicine": "医学", "nature": "自然",
    "occultism": "神秘学", "perception": "感知", "performance": "表演",
    "religion": "宗教", "society": "社会", "stealth": "隐匿",
    "survival": "生存", "thievery": "巧手",
    "fortitude": "强韧", "reflex": "反射", "will": "意志",
    "flat": "纯骰",
}

# Template type translations
_TEMPLATE_TYPES = {
    "emanation": "弥漫", "burst": "爆发", "cone": "锥形",
    "line": "直线", "wall": "墙",
}


def _parse_uuid_params(raw: str) -> dict[str, str]:
    """Parse a UUID reference like Compendium.pf2e.feats-srd.Item.Swift Sneak"""
    parts = raw.split(".")
    result = {"raw": raw}
    if len(parts) >= 4:
        result["module"] = parts[1] if len(parts) > 1 else ""
        result["pack"] = parts[2] if len(parts) > 2 else ""
        result["type"] = parts[3] if len(parts) > 3 else ""
        result["name"] = ".".join(parts[4:]) if len(parts) > 4 else ""
    return result


def _parse_check_params(raw: str) -> dict[str, str]:
    """Parse check parameters like type:athletics|dc:20|traits:skill"""
    params: dict[str, str] = {}
    for part in raw.split("|"):
        if ":" in part:
            key, val = part.split(":", 1)
            params[key.strip()] = val.strip()
    return params


def _parse_damage(raw: str) -> str:
    """Parse damage expression like 2d6[fire] or 1d4[persistent,fire]"""
    match = re.match(r"([^[]+)\[([^\]]+)\]", raw)
    if match:
        dice = match.group(1).strip()
        types = match.group(2).strip()
        type_parts = [_DAMAGE_TYPES.get(t.strip(), t.strip()) for t in types.split(",")]
        return f"{dice} {'/'.join(type_parts)}伤害"
    return raw


def render_fvtt_markup(html: str | None) -> str:
    """Convert FVTT inline markup to clean HTML for frontend rendering.
    
    Handles: @UUID, @Check, @Damage, @Template, @Localize, inline rolls [[/r ...]]
    """
    if not html:
        return ""
    
    result = html

    # @UUID[Compendium.pf2e.xxx.Item.Name]{Display Text}
    def _replace_uuid(m: re.Match) -> str:
        uuid_ref = m.group(1)
        display = m.group(2) if m.group(2) else ""
        params = _parse_uuid_params(uuid_ref)
        if not display:
            display = params.get("name", uuid_ref.split(".")[-1])
        pack = params.get("pack", "")
        name = params.get("name", "")
        return f'<span class="pf2e-ref" data-pack="{pack}" data-name="{name}" title="{uuid_ref}">{display}</span>'
    
    result = re.sub(r'@UUID\[([^\]]+)\](?:\{([^}]*)\})?', _replace_uuid, result)

    # @Check[type:athletics|dc:20|...]  
    def _replace_check(m: re.Match) -> str:
        params = _parse_check_params(m.group(1))
        check_type = params.get("type", "")
        dc = params.get("dc", "")
        translated = _CHECK_TYPES.get(check_type, check_type)
        dc_str = f" DC {dc}" if dc else ""
        return f'<span class="pf2e-check" data-type="{check_type}" data-dc="{dc}">{translated}检定{dc_str}</span>'
    
    result = re.sub(r'@Check\[([^\]]+)\]', _replace_check, result)

    # @Damage[2d6[fire]]
    def _replace_damage(m: re.Match) -> str:
        parsed = _parse_damage(m.group(1))
        return f'<span class="pf2e-damage">{parsed}</span>'
    
    result = re.sub(r'@Damage\[([^\]]+)\]', _replace_damage, result)

    # @Template[type:emanation|distance:20]
    def _replace_template(m: re.Match) -> str:
        params = _parse_check_params(m.group(1))
        tmpl_type = params.get("type", "")
        distance = params.get("distance", "")
        translated = _TEMPLATE_TYPES.get(tmpl_type, tmpl_type)
        return f'<span class="pf2e-template">{distance}尺{translated}</span>'
    
    result = re.sub(r'@Template\[([^\]]+)\]', _replace_template, result)

    # @Localize[PF2E.xxx] -> just remove the tag, keep brackets as indicator
    result = re.sub(r'@Localize\[([^\]]+)\]', r'[\1]', result)

    # Inline rolls [[/r 1d6+3]]{display} or [[/r 1d6+3]]
    def _replace_inline_roll(m: re.Match) -> str:
        expr = m.group(1).strip()
        display = m.group(2) if m.group(2) else expr
        return f'<span class="pf2e-roll">{display}</span>'
    
    result = re.sub(r'\[\[/r\s+([^\]]+)\]\](?:\{([^}]*)\})?', _replace_inline_roll, result)
    
    # Clean up any remaining [[...]] 
    result = re.sub(r'\[\[([^\]]*)\]\]', r'\1', result)

    return result


def strip_all_markup(html: str | None) -> str:
    """Strip ALL markup to plain text (for search/indexing)."""
    if not html:
        return ""
    text = render_fvtt_markup(html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<hr\s*/?>", "\n---\n", text)
    text = re.sub(r"</?p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
