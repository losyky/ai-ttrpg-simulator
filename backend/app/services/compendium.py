"""Compendium management service for charbuilder data.

Defaults are loaded from JSON pack files under each system's
``default_packs/processed/`` directory. Custom entries are stored in
``data/compendium/{system}/{collection}.json``.

The service also supports importing entries from FVTT-exported JSON files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings

log = logging.getLogger(__name__)

_custom_cache: dict[str, list[dict[str, Any]]] = {}
_default_cache: dict[str, list[dict[str, Any]]] = {}

# ── System pack directories ──

_SYSTEM_PACK_DIRS: dict[str, Path] = {}


def _register_pack_dir(system: str, pack_dir: Path) -> None:
    _SYSTEM_PACK_DIRS[system] = pack_dir


def _pack_dir(system: str) -> Path | None:
    if system not in _SYSTEM_PACK_DIRS:
        candidates = [
            Path(__file__).resolve().parent.parent / "systems" / system / "default_packs" / "processed",
            Path(__file__).resolve().parent.parent / "systems" / system / "default_packs",
        ]
        for c in candidates:
            if c.exists():
                _SYSTEM_PACK_DIRS[system] = c
                break
    return _SYSTEM_PACK_DIRS.get(system)


# ── Collections registry ──

_SYSTEM_COLLECTIONS: dict[str, list[str]] = {
    "daggerheart": [
        "classes", "subclasses", "domain_cards", "ancestries", "communities",
        "weapons", "armors", "consumables", "loot", "beastforms",
        "ancestry_features", "subclass_features",
    ],
    "swade": ["races", "elements", "edges", "hindrances", "powers"],
    "pf2e": [],
}

_COLLECTION_LABELS: dict[str, str] = {
    "classes": "职业 (Classes)",
    "subclasses": "子职业 (Subclasses)",
    "domain_cards": "领域卡 (Domain Cards)",
    "ancestries": "族裔 (Ancestries)",
    "communities": "社群 (Communities)",
    "weapons": "武器 (Weapons)",
    "armors": "护甲 (Armors)",
    "consumables": "消耗品 (Consumables)",
    "loot": "战利品 (Loot)",
    "beastforms": "兽形 (Beastforms)",
    "ancestry_features": "族裔特性 (Ancestry Features)",
    "subclass_features": "子职业特性 (Subclass Features)",
    "races": "种族 (Races)",
    "elements": "元素 (Elements)",
    "edges": "专长 (Edges)",
    "hindrances": "负赘 (Hindrances)",
    "powers": "异能 (Powers)",
}


# ── Custom data directory ──

def _custom_dir(system: str) -> Path:
    d = Path(settings.data_dir) / "compendium" / system
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Defaults ──

def _load_defaults_from_file(system: str, collection: str) -> list[dict[str, Any]]:
    key = f"{system}/{collection}"
    if key in _default_cache:
        return _default_cache[key]
    pdir = _pack_dir(system)
    if pdir:
        fpath = pdir / f"{collection}.json"
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                _default_cache[key] = data
                return data
            except Exception as e:
                log.warning("Failed to load default pack %s: %s", fpath, e)
    _default_cache[key] = []
    return []


def _get_hardcoded_defaults(system: str, collection: str) -> list[dict[str, Any]]:
    """Fallback to hardcoded constants if no JSON pack files exist."""
    if system == "daggerheart":
        from app.systems.daggerheart.charbuilder_router import (
            DH_CLASSES, DH_DOMAINS, DH_ANCESTRIES, DH_COMMUNITIES,
        )
        mapping = {"classes": DH_CLASSES, "domains": DH_DOMAINS,
                    "ancestries": DH_ANCESTRIES, "communities": DH_COMMUNITIES}
        return mapping.get(collection, [])
    elif system == "swade":
        from app.systems.swade.charbuilder_router import (
            SWADE_RACES, SWADE_ELEMENTS,
        )
        mapping = {"races": SWADE_RACES, "elements": SWADE_ELEMENTS}
        return mapping.get(collection, [])
    return []


def get_defaults(system: str, collection: str) -> list[dict[str, Any]]:
    data = _load_defaults_from_file(system, collection)
    if not data:
        data = _get_hardcoded_defaults(system, collection)
    return data


# ── Custom entries ──

def _load_custom(system: str, collection: str) -> list[dict[str, Any]]:
    key = f"{system}/{collection}"
    if key in _custom_cache:
        return _custom_cache[key]
    fpath = _custom_dir(system) / f"{collection}.json"
    if fpath.exists():
        try:
            _custom_cache[key] = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception:
            _custom_cache[key] = []
    else:
        _custom_cache[key] = []
    return _custom_cache[key]


def _save_custom(system: str, collection: str) -> None:
    key = f"{system}/{collection}"
    items = _custom_cache.get(key, [])
    fpath = _custom_dir(system) / f"{collection}.json"
    fpath.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Public API ──

def list_entries(system: str, collection: str) -> list[dict[str, Any]]:
    defaults = [dict(d, _default=True) for d in get_defaults(system, collection)]
    customs = [dict(c, _default=False) for c in _load_custom(system, collection)]
    return defaults + customs


def add_entry(system: str, collection: str, entry: dict[str, Any]) -> dict[str, Any]:
    items = _load_custom(system, collection)
    slug = entry.get("slug", "")
    if not slug:
        slug = entry.get("name", "custom").lower().replace(" ", "-")
        entry["slug"] = slug
    existing_slugs = {e.get("slug") for e in items}
    existing_slugs.update(d.get("slug") for d in get_defaults(system, collection))
    if slug in existing_slugs:
        base = slug
        i = 2
        while f"{base}-{i}" in existing_slugs:
            i += 1
        slug = f"{base}-{i}"
        entry["slug"] = slug
    items.append(entry)
    _save_custom(system, collection)
    return entry


def add_entries_bulk(system: str, collection: str, entries: list[dict[str, Any]]) -> int:
    """Add multiple custom entries at once. Returns count added."""
    items = _load_custom(system, collection)
    existing_slugs = {e.get("slug") for e in items}
    existing_slugs.update(d.get("slug") for d in get_defaults(system, collection))
    added = 0
    for entry in entries:
        slug = entry.get("slug", "")
        if not slug:
            slug = entry.get("name", "custom").lower().replace(" ", "-")
            entry["slug"] = slug
        if slug in existing_slugs:
            base = slug
            i = 2
            while f"{base}-{i}" in existing_slugs:
                i += 1
            slug = f"{base}-{i}"
            entry["slug"] = slug
        existing_slugs.add(slug)
        items.append(entry)
        added += 1
    if added:
        _save_custom(system, collection)
    return added


def delete_entry(system: str, collection: str, slug: str) -> bool:
    items = _load_custom(system, collection)
    before = len(items)
    items[:] = [e for e in items if e.get("slug") != slug]
    if len(items) < before:
        _save_custom(system, collection)
        return True
    return False


def update_entry(system: str, collection: str, slug: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    items = _load_custom(system, collection)
    for e in items:
        if e.get("slug") == slug:
            e.update(updates)
            _save_custom(system, collection)
            return e
    return None


def list_collections(system: str) -> list[dict[str, str]]:
    """Return the available collection names and labels for a system."""
    cols = _SYSTEM_COLLECTIONS.get(system, [])
    if not cols:
        pdir = _pack_dir(system)
        if pdir:
            cols = [f.stem for f in pdir.glob("*.json") if not f.name.startswith("_")]
    return [{"id": c, "label": _COLLECTION_LABELS.get(c, c)} for c in cols]


def list_collection_ids(system: str) -> list[str]:
    return [c["id"] for c in list_collections(system)]


# ── FVTT JSON Import ──

def _strip_html(html: str) -> str:
    import re
    if not html:
        return ""
    return re.sub(r"<[^>]*>", "", html).replace("&nbsp;", " ").replace("&amp;", "&").strip()


def _classify_fvtt_item(item: dict[str, Any], system_id: str) -> tuple[str, dict[str, Any]] | None:
    """Classify a FVTT document into a (collection, entry) pair."""
    item_type = item.get("type", "")
    name = item.get("name", "")
    sys_data = item.get("system", {})
    fvtt_system = item.get("_stats", {}).get("systemId", "")

    base = {
        "slug": name.lower().replace(" ", "-").replace("'", ""),
        "name": name,
        "fvtt_id": item.get("_id", ""),
        "img": item.get("img", ""),
        "description": _strip_html(sys_data.get("description", {}).get("value", "")
                                    if isinstance(sys_data.get("description"), dict)
                                    else sys_data.get("description", "")),
    }

    # Daggerheart types
    if fvtt_system == "daggerheart" or system_id == "daggerheart":
        if item_type == "class":
            return ("classes", {
                **base,
                "base_hp": sys_data.get("hitPoints", {}).get("base", 6) if isinstance(sys_data.get("hitPoints"), dict) else 6,
                "base_evasion": sys_data.get("evasion", {}).get("base", 8) if isinstance(sys_data.get("evasion"), dict) else 8,
                "base_stress": sys_data.get("stressMax", 6),
                "domains": sys_data.get("domains", []),
                "spellcasting_trait": sys_data.get("spellcastingTrait"),
            })
        elif item_type == "subclass":
            return ("subclasses", {**base, "spellcasting_trait": sys_data.get("spellcastingTrait"), "linked_class": sys_data.get("linkedClass")})
        elif item_type == "domainCard":
            return ("domain_cards", {**base, "domain": sys_data.get("domain", ""), "level": sys_data.get("level", 1), "recall_cost": sys_data.get("recallCost", 0), "card_type": sys_data.get("type", "")})
        elif item_type == "ancestry":
            return ("ancestries", base)
        elif item_type == "community":
            return ("communities", base)
        elif item_type == "weapon":
            atk = sys_data.get("attack", {})
            return ("weapons", {**base, "tier": sys_data.get("tier", 1), "burden": sys_data.get("burden", 1), "damage_die": atk.get("damageDie", ""), "damage_type": atk.get("type", ""), "range": atk.get("range", "")})
        elif item_type == "armor":
            return ("armors", {**base, "tier": sys_data.get("tier", 1), "base_score": sys_data.get("baseScore", 0)})
        elif item_type == "consumable":
            return ("consumables", base)
        elif item_type == "loot":
            return ("loot", base)
        elif item_type == "beastform":
            return ("beastforms", {**base, "tier": sys_data.get("tier", 1), "main_trait": sys_data.get("mainTrait", "")})
        elif item_type == "feature":
            return ("subclass_features", {**base, "type": "feature"})

    # SWADE types
    if fvtt_system == "swade" or system_id == "swade":
        if item_type == "edge":
            return ("edges", {**base, "rank": sys_data.get("rank", "novice"), "isWildcard": sys_data.get("isWildcard", False)})
        elif item_type == "hindrance":
            return ("hindrances", {**base, "major": sys_data.get("major", False)})
        elif item_type == "power":
            return ("powers", {**base, "rank": sys_data.get("rank", "novice"), "pp": sys_data.get("pp", 0)})
        elif item_type in ("race", "ancestry"):
            return ("races", {**base, "trait": base.get("description", "")[:200]})

    # PF2e types
    if fvtt_system == "pf2e" or system_id == "pf2e":
        category = sys_data.get("category", "")
        if item_type == "feat":
            return (category or "feats", {**base, "level": sys_data.get("level", {}).get("value", 1) if isinstance(sys_data.get("level"), dict) else 1, "traits": sys_data.get("traits", {}).get("value", [])})
        elif item_type == "equipment" or item_type == "weapon" or item_type == "armor":
            return ("equipment", {**base, "level": sys_data.get("level", {}).get("value", 0) if isinstance(sys_data.get("level"), dict) else 0})
        elif item_type == "spell":
            return ("spells", {**base, "level": sys_data.get("level", {}).get("value", 0) if isinstance(sys_data.get("level"), dict) else 0, "traditions": sys_data.get("traditions", {}).get("value", [])})
        elif item_type in ("ancestry", "heritage", "background", "class"):
            return (item_type + "s" if not item_type.endswith("s") else item_type, base)

    # Generic fallback
    if item_type and name:
        col = item_type + "s" if not item_type.endswith("s") else item_type
        return (col, base)

    return None


def import_fvtt_json(system: str, data: dict | list) -> dict[str, int]:
    """Import one or more FVTT-exported JSON documents into the compendium.

    Returns a dict of {collection: count_added}.
    """
    docs = data if isinstance(data, list) else [data]
    by_collection: dict[str, list[dict[str, Any]]] = {}

    for doc in docs:
        if not isinstance(doc, dict):
            continue
        # Skip folder entries
        if "system" not in doc and "sorting" in doc:
            continue
        result = _classify_fvtt_item(doc, system)
        if result:
            col, entry = result
            by_collection.setdefault(col, []).append(entry)
        # Handle nested items (e.g. Actor with embedded items)
        for sub_item in doc.get("items", []):
            if isinstance(sub_item, dict):
                sub_result = _classify_fvtt_item(sub_item, system)
                if sub_result:
                    col, entry = sub_result
                    by_collection.setdefault(col, []).append(entry)

    counts: dict[str, int] = {}
    for col, entries in by_collection.items():
        added = add_entries_bulk(system, col, entries)
        if added:
            counts[col] = added
    return counts
