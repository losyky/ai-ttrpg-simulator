"""Ingest PF2e compendium data into the character builder SQLite database.

Scans a PF2e FVTT system directory for ancestries, heritages, backgrounds,
classes, class-features, feats, spells, and equipment, extracting the
fields needed for AI-driven character creation.

Data source is configured via:
  - CLI argument:  python -m ... /path/to/pf2e-system/packs/pf2e
  - Env variable:  FVTT_PF2E_PACKS=/path/to/pf2e-system/packs/pf2e
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.systems.pf2e.charbuilder_db import (
    get_conn, init_tables, bulk_insert, get_stats, _db_path,
)


def _resolve_packs_root() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    env = os.environ.get("FVTT_PF2E_PACKS")
    if env:
        return Path(env).resolve()
    print("[ERROR] No PF2e packs path provided.")
    print("  Usage: python -m app.systems.pf2e.ingest.ingest_charbuilder <packs_dir>")
    print("  Or set FVTT_PF2E_PACKS environment variable.")
    sys.exit(1)

PACKS_ROOT = _resolve_packs_root()


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<img[^>]*>", "", html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</?[^>]+>", " ", text)
    text = re.sub(r"@UUID\[.*?\]\{(.*?)\}", r"\1", text)
    text = re.sub(r"@UUID\[.*?\]", "", text)
    text = re.sub(r"@(?:Check|Damage|Template|Embed|Localize)\[.*?\]", "", text)
    text = re.sub(r"\[\[/.*?\]\]\{(.*?)\}", r"\1", text)
    text = re.sub(r"\[\[/.*?\]\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _slug_from_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _load_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _j(obj) -> str:
    """Serialize to JSON string for storage."""
    return json.dumps(obj, ensure_ascii=False)


# ── Ancestry ingestion ──

def ingest_ancestries() -> int:
    d = PACKS_ROOT / "ancestries"
    if not d.exists():
        return 0
    rows = []
    for fp in d.glob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data or data.get("type") != "ancestry":
            continue
        sys_ = data.get("system", {})
        boosts = sys_.get("boosts", {})
        flaws = sys_.get("flaws", {})
        langs = sys_.get("languages", {})
        traits = sys_.get("traits", {})
        desc = _strip_html(sys_.get("description", {}).get("value", ""))
        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "hp": sys_.get("hp", 0),
            "size": sys_.get("size", "med"),
            "speed": sys_.get("speed", 25),
            "vision": sys_.get("vision", "normal"),
            "boosts": _j(boosts),
            "flaws": _j(flaws),
            "languages": _j(langs.get("value", [])),
            "traits": _j(traits.get("value", [])),
            "description": desc[:2000],
        })
    return bulk_insert("ancestries", rows)


# ── Heritage ingestion ──

def ingest_heritages() -> int:
    d = PACKS_ROOT / "heritages"
    if not d.exists():
        return 0
    rows = []
    for fp in d.rglob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data or data.get("type") != "heritage":
            continue
        sys_ = data.get("system", {})
        ancestry_ref = sys_.get("ancestry", None)
        ancestry_slug = None
        if ancestry_ref and isinstance(ancestry_ref, dict):
            ancestry_slug = ancestry_ref.get("slug")
        elif fp.parent.name != "heritages" and fp.parent.name != "versatile-heritages":
            ancestry_slug = fp.parent.name

        traits = sys_.get("traits", {})
        rules = sys_.get("rules", [])
        rules_summary = ", ".join(
            r.get("key", "") for r in rules if isinstance(r, dict)
        )[:200]
        desc = _strip_html(sys_.get("description", {}).get("value", ""))
        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "ancestry_slug": ancestry_slug,
            "traits": _j(traits.get("value", [])),
            "rules_summary": rules_summary,
            "description": desc[:2000],
        })
    return bulk_insert("heritages", rows)


# ── Background ingestion ──

def ingest_backgrounds() -> int:
    d = PACKS_ROOT / "backgrounds"
    if not d.exists():
        return 0
    rows = []
    for fp in d.rglob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data or data.get("type") != "background":
            continue
        sys_ = data.get("system", {})
        boosts = sys_.get("boosts", {})
        ts = sys_.get("trainedSkills", {})
        items = sys_.get("items", {})
        feat_names = [v.get("name", "") for v in items.values() if isinstance(v, dict) and v.get("name")]
        desc = _strip_html(sys_.get("description", {}).get("value", ""))
        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "boosts": _j(boosts),
            "trained_skills": _j(ts.get("value", [])),
            "lore": _j(ts.get("lore", [])),
            "granted_feat_names": _j(feat_names),
            "description": desc[:2000],
        })
    return bulk_insert("backgrounds", rows)


# ── Class ingestion ──

def ingest_classes() -> int:
    d = PACKS_ROOT / "classes"
    if not d.exists():
        return 0
    rows = []
    for fp in d.glob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data or data.get("type") != "class":
            continue
        sys_ = data.get("system", {})

        saves = sys_.get("savingThrows", {})
        attacks_raw = sys_.get("attacks", {})
        attacks = {}
        for k, v in attacks_raw.items():
            if isinstance(v, (int, float)):
                attacks[k] = v
            elif isinstance(v, dict):
                attacks[k] = v
            else:
                attacks[k] = v
        defenses = sys_.get("defenses", {})
        ts = sys_.get("trainedSkills", {})

        items_raw = sys_.get("items", {})
        features = []
        for _key, item in items_raw.items():
            if isinstance(item, dict):
                features.append({
                    "name": item.get("name", ""),
                    "level": item.get("level", 0),
                    "uuid": item.get("uuid", ""),
                })
        features.sort(key=lambda x: x.get("level", 0))

        desc = _strip_html(sys_.get("description", {}).get("value", ""))
        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "hp_per_level": sys_.get("hp", 0),
            "key_ability": _j(sys_.get("keyAbility", {}).get("value", [])),
            "perception_rank": sys_.get("perception", 0),
            "saves": _j(saves),
            "attacks": _j(attacks),
            "defenses": _j(defenses),
            "trained_skills": _j(ts.get("value", [])),
            "additional_skill_count": ts.get("additional", 0),
            "spellcasting": sys_.get("spellcasting", 0),
            "ancestry_feat_levels": _j(sys_.get("ancestryFeatLevels", {}).get("value", [])),
            "class_feat_levels": _j(sys_.get("classFeatLevels", {}).get("value", [])),
            "general_feat_levels": _j(sys_.get("generalFeatLevels", {}).get("value", [])),
            "skill_feat_levels": _j(sys_.get("skillFeatLevels", {}).get("value", [])),
            "skill_increase_levels": _j(sys_.get("skillIncreaseLevels", {}).get("value", [])),
            "class_features": _j(features),
            "description": desc[:2000],
        })
    return bulk_insert("classes", rows)


# ── Class features ingestion ──

def ingest_class_features() -> int:
    d = PACKS_ROOT / "class-features"
    if not d.exists():
        return 0
    rows = []
    for fp in d.rglob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data:
            continue
        sys_ = data.get("system", {})
        cat = sys_.get("category", "classfeature")
        if cat not in ("classfeature", "ancestryfeature"):
            continue
        traits = sys_.get("traits", {}).get("value", [])
        class_slug = ""
        for t in traits:
            if t and t not in ("classfeature",):
                class_slug = t
                break

        rules = sys_.get("rules", [])
        rules_summary = ", ".join(
            r.get("key", "") for r in rules if isinstance(r, dict)
        )[:200]
        desc = _strip_html(sys_.get("description", {}).get("value", ""))
        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "level": sys_.get("level", {}).get("value", 0),
            "class_slug": class_slug,
            "category": cat,
            "rules_summary": rules_summary,
            "description": desc[:2000],
        })
    return bulk_insert("class_features", rows)


# ── Feats ingestion ──

def _infer_class_or_ancestry(fp: Path, data: dict) -> tuple[str, str]:
    """Infer class_slug and ancestry_slug from file path and traits."""
    parts = fp.relative_to(PACKS_ROOT / "feats").parts
    category_dir = parts[0] if parts else ""
    slug_dir = parts[1] if len(parts) > 1 else ""

    class_slug = ""
    ancestry_slug = ""

    if category_dir == "class" and slug_dir:
        class_slug = slug_dir
    elif category_dir == "ancestry" and slug_dir:
        ancestry_slug = slug_dir
    elif category_dir == "archetype" and slug_dir:
        class_slug = slug_dir

    return class_slug, ancestry_slug


def ingest_feats() -> int:
    d = PACKS_ROOT / "feats"
    if not d.exists():
        return 0
    rows = []
    for fp in d.rglob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data or data.get("type") != "feat":
            continue
        sys_ = data.get("system", {})
        cat = sys_.get("category", "")
        if not cat:
            parts = fp.relative_to(PACKS_ROOT / "feats").parts
            if parts:
                cat = parts[0]

        traits = sys_.get("traits", {})
        prereqs = sys_.get("prerequisites", {}).get("value", [])
        prereq_list = [p.get("value", "") for p in prereqs if isinstance(p, dict)]

        action_type = sys_.get("actionType", {}).get("value", "")
        class_slug, ancestry_slug = _infer_class_or_ancestry(fp, data)
        desc = _strip_html(sys_.get("description", {}).get("value", ""))

        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "level": sys_.get("level", {}).get("value", 0),
            "category": cat,
            "action_type": action_type,
            "traits": _j(traits.get("value", [])),
            "prerequisites": _j(prereq_list),
            "class_slug": class_slug,
            "ancestry_slug": ancestry_slug,
            "description": desc[:2000],
        })
    return bulk_insert("feats", rows)


# ── Spells ingestion ──

def ingest_spells() -> int:
    d = PACKS_ROOT / "spells" / "spells"
    if not d.exists():
        d = PACKS_ROOT / "spells"
    if not d.exists():
        return 0
    rows = []
    for fp in d.rglob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data or data.get("type") != "spell":
            continue
        sys_ = data.get("system", {})
        traits = sys_.get("traits", {})
        traditions = traits.get("traditions", [])

        rank_val = sys_.get("level", {}).get("value", 0)
        is_cantrip = "cantrip" in traits.get("value", [])
        if is_cantrip:
            rank_val = 0

        time_data = sys_.get("time", {})
        action_cost = str(time_data.get("value", ""))

        range_val = sys_.get("range", {}).get("value", "") if isinstance(sys_.get("range"), dict) else str(sys_.get("range", ""))
        area_data = sys_.get("area", {})
        area_str = ""
        if area_data and isinstance(area_data, dict) and area_data.get("type"):
            area_str = f"{area_data.get('value', '')} {area_data.get('type', '')}"

        target = sys_.get("target", {}).get("value", "") if isinstance(sys_.get("target"), dict) else str(sys_.get("target", ""))
        duration_data = sys_.get("duration", {})
        duration = ""
        if isinstance(duration_data, dict):
            duration = duration_data.get("value", "")
            if duration_data.get("sustained"):
                duration = f"sustained {duration}" if duration else "sustained"

        defense_data = sys_.get("defense", {})
        defense_str = ""
        if defense_data and isinstance(defense_data, dict):
            save = defense_data.get("save", {})
            if isinstance(save, dict) and save.get("statistic"):
                basic = "basic " if save.get("basic") else ""
                defense_str = f"{basic}{save['statistic']}"

        desc = _strip_html(sys_.get("description", {}).get("value", ""))

        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "rank": rank_val,
            "traditions": _j(traditions),
            "traits": _j(traits.get("value", [])),
            "action_cost": action_cost,
            "range": range_val or "",
            "area": area_str,
            "target": target or "",
            "duration": duration or "",
            "defense": defense_str,
            "description": desc[:2000],
        })
    return bulk_insert("spells", rows)


# ── Focus spells ──

def ingest_focus_spells() -> int:
    d = PACKS_ROOT / "spells" / "focus"
    if not d.exists():
        return 0
    rows = []
    for fp in d.rglob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data or data.get("type") != "spell":
            continue
        sys_ = data.get("system", {})
        traits = sys_.get("traits", {})
        traditions = traits.get("traditions", [])
        rank_val = sys_.get("level", {}).get("value", 0)
        time_data = sys_.get("time", {})
        desc = _strip_html(sys_.get("description", {}).get("value", ""))
        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "rank": rank_val,
            "traditions": _j(traditions),
            "traits": _j(traits.get("value", [])),
            "action_cost": str(time_data.get("value", "")),
            "range": "",
            "area": "",
            "target": "",
            "duration": "",
            "defense": "",
            "description": desc[:2000],
        })
    return bulk_insert("spells", rows)


# ── Equipment ingestion ──

def _price_to_cp(price: dict) -> int:
    """Convert price dict to copper pieces."""
    if not isinstance(price, dict):
        return 0
    cp = price.get("cp", 0) or 0
    sp = price.get("sp", 0) or 0
    gp = price.get("gp", 0) or 0
    pp = price.get("pp", 0) or 0
    return int(cp) + int(sp) * 10 + int(gp) * 100 + int(pp) * 1000


EQUIPMENT_TYPES = {"weapon", "armor", "equipment", "consumable", "shield", "treasure", "kit", "backpack"}


def ingest_equipment() -> int:
    d = PACKS_ROOT / "equipment"
    if not d.exists():
        return 0
    rows = []
    for fp in d.rglob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load_json(fp)
        if not data:
            continue
        itype = data.get("type", "")
        if itype not in EQUIPMENT_TYPES:
            continue
        sys_ = data.get("system", {})
        traits = sys_.get("traits", {})
        price_cp = _price_to_cp(sys_.get("price", {}).get("value", {}))
        bulk_val = sys_.get("bulk", {})
        bulk_str = str(bulk_val.get("value", "")) if isinstance(bulk_val, dict) else str(bulk_val)

        # Weapon-specific
        damage_data = sys_.get("damage", {})
        damage_str = ""
        if isinstance(damage_data, dict) and damage_data.get("die"):
            dice = damage_data.get("dice", 1)
            die = damage_data.get("die", "")
            dtype = damage_data.get("damageType", "")
            damage_str = f"{dice}{die} {dtype}"

        # Armor-specific
        ac_bonus = 0
        dex_cap = 99
        category = sys_.get("category", "")
        if itype == "armor":
            ac_bonus = sys_.get("acBonus", 0) or 0
            dex_cap = sys_.get("dexCap", 99) if sys_.get("dexCap") is not None else 99
        elif itype == "weapon":
            category = sys_.get("category", "")
        elif itype == "shield":
            ac_bonus = sys_.get("acBonus", 0) or 0

        desc = _strip_html(sys_.get("description", {}).get("value", ""))
        rows.append({
            "id": data.get("_id", fp.stem),
            "name": data.get("name", fp.stem),
            "slug": fp.stem,
            "item_type": itype,
            "category": category,
            "price_cp": price_cp,
            "bulk": bulk_str,
            "traits": _j(traits.get("value", [])),
            "damage": damage_str,
            "ac_bonus": ac_bonus,
            "dex_cap": dex_cap,
            "description": desc[:2000],
        })
    return bulk_insert("equipment", rows)


# ── Main ──

def main():
    if not PACKS_ROOT.exists():
        print(f"[ERROR] PF2e packs directory not found: {PACKS_ROOT}")
        sys.exit(1)

    db = _db_path()
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db) + suffix)
        if p.exists():
            p.unlink()
    print(f"[INFO] Database: {db}")

    conn = get_conn()
    init_tables(conn)

    print("[1/8] Ingesting ancestries...")
    n = ingest_ancestries()
    print(f"       {n} ancestries indexed.")

    print("[2/8] Ingesting heritages...")
    n = ingest_heritages()
    print(f"       {n} heritages indexed.")

    print("[3/8] Ingesting backgrounds...")
    n = ingest_backgrounds()
    print(f"       {n} backgrounds indexed.")

    print("[4/8] Ingesting classes...")
    n = ingest_classes()
    print(f"       {n} classes indexed.")

    print("[5/8] Ingesting class features...")
    n = ingest_class_features()
    print(f"       {n} class features indexed.")

    print("[6/8] Ingesting feats...")
    n = ingest_feats()
    print(f"       {n} feats indexed.")

    print("[7/8] Ingesting spells...")
    n = ingest_spells()
    n2 = ingest_focus_spells()
    print(f"       {n + n2} spells indexed ({n} standard + {n2} focus).")

    print("[8/8] Ingesting equipment...")
    n = ingest_equipment()
    print(f"       {n} equipment items indexed.")

    stats = get_stats()
    print("\n============================================")
    print("  Character Builder DB — Ingestion Complete")
    print("============================================")
    for table, count in stats.items():
        print(f"  {table}: {count}")
    print("============================================")


if __name__ == "__main__":
    main()
