"""Build PF2e default databases from extracted pack JSON + Babele translations.

This script:
  1. Reads extracted flat JSON arrays (from extract_fvtt_packs.mjs)
  2. Populates charbuilder.db with ancestries, heritages, backgrounds, classes,
     class-features, feats, spells, equipment
  3. Populates game.db compendium_entries + creatures from Babele translations
  4. Applies Chinese translations to charbuilder.db
  5. Exports both databases as gzipped seed files for built-in shipping

Usage:
  python -m app.systems.pf2e.ingest.build_default_dbs \\
      --packs-dir <extracted_packs_dir> \\
      --translations-dir <babele_compendium_dir> \\
      --output-dir <default_data_output>
"""

import argparse
import gzip
import json
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.config import settings


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


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _load_pack(packs_dir: Path, name: str) -> list[dict]:
    fp = packs_dir / f"{name}.json"
    if not fp.exists():
        print(f"  [WARN] Pack not found: {fp.name}")
        return []
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def _price_to_cp(price: dict) -> int:
    if not isinstance(price, dict):
        return 0
    cp = price.get("cp", 0) or 0
    sp = price.get("sp", 0) or 0
    gp = price.get("gp", 0) or 0
    pp = price.get("pp", 0) or 0
    return int(cp) + int(sp) * 10 + int(gp) * 100 + int(pp) * 1000


EQUIPMENT_TYPES = {"weapon", "armor", "equipment", "consumable", "shield", "treasure", "kit", "backpack"}


def build_charbuilder(packs_dir: Path, db_path: Path):
    """Build charbuilder.db from extracted pack JSON files."""
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")

    from app.systems.pf2e.charbuilder_db import init_tables
    init_tables(conn)

    def _bulk(table, rows):
        if not rows:
            return 0
        cols = list(rows[0].keys())
        placeholders = ", ".join(f":{c}" for c in cols)
        col_names = ", ".join(cols)
        conn.executemany(f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})", rows)
        conn.commit()
        return len(rows)

    # Ancestries
    rows = []
    for d in _load_pack(packs_dir, "ancestries"):
        if d.get("type") != "ancestry":
            continue
        s = d.get("system", {})
        rows.append({
            "id": d.get("_id", ""), "name": d.get("name", ""),
            "slug": _slug(d.get("name", "")),
            "hp": s.get("hp", 0), "size": s.get("size", "med"),
            "speed": s.get("speed", 25), "vision": s.get("vision", "normal"),
            "boosts": _j(s.get("boosts", {})), "flaws": _j(s.get("flaws", {})),
            "languages": _j(s.get("languages", {}).get("value", [])),
            "traits": _j(s.get("traits", {}).get("value", [])),
            "description": _strip_html(s.get("description", {}).get("value", ""))[:2000],
        })
    n = _bulk("ancestries", rows)
    print(f"  [1/8] ancestries: {n}")

    # Heritages
    rows = []
    for d in _load_pack(packs_dir, "heritages"):
        if d.get("type") != "heritage":
            continue
        s = d.get("system", {})
        anc = s.get("ancestry", None)
        anc_slug = anc.get("slug") if isinstance(anc, dict) else None
        rows.append({
            "id": d.get("_id", ""), "name": d.get("name", ""),
            "slug": _slug(d.get("name", "")),
            "ancestry_slug": anc_slug,
            "traits": _j(s.get("traits", {}).get("value", [])),
            "rules_summary": ", ".join(r.get("key", "") for r in s.get("rules", []) if isinstance(r, dict))[:200],
            "description": _strip_html(s.get("description", {}).get("value", ""))[:2000],
        })
    n = _bulk("heritages", rows)
    print(f"  [2/8] heritages: {n}")

    # Backgrounds
    rows = []
    for d in _load_pack(packs_dir, "backgrounds"):
        if d.get("type") != "background":
            continue
        s = d.get("system", {})
        ts = s.get("trainedSkills", {})
        items = s.get("items", {})
        feat_names = [v.get("name", "") for v in items.values() if isinstance(v, dict) and v.get("name")]
        rows.append({
            "id": d.get("_id", ""), "name": d.get("name", ""),
            "slug": _slug(d.get("name", "")),
            "boosts": _j(s.get("boosts", {})),
            "trained_skills": _j(ts.get("value", [])),
            "lore": _j(ts.get("lore", [])),
            "granted_feat_names": _j(feat_names),
            "description": _strip_html(s.get("description", {}).get("value", ""))[:2000],
        })
    n = _bulk("backgrounds", rows)
    print(f"  [3/8] backgrounds: {n}")

    # Classes
    rows = []
    for d in _load_pack(packs_dir, "classes"):
        if d.get("type") != "class":
            continue
        s = d.get("system", {})
        items_raw = s.get("items", {})
        features = []
        for _k, item in items_raw.items():
            if isinstance(item, dict):
                features.append({"name": item.get("name", ""), "level": item.get("level", 0), "uuid": item.get("uuid", "")})
        features.sort(key=lambda x: x.get("level", 0))
        rows.append({
            "id": d.get("_id", ""), "name": d.get("name", ""),
            "slug": _slug(d.get("name", "")),
            "hp_per_level": s.get("hp", 0),
            "key_ability": _j(s.get("keyAbility", {}).get("value", [])),
            "perception_rank": s.get("perception", 0),
            "saves": _j(s.get("savingThrows", {})),
            "attacks": _j(s.get("attacks", {})),
            "defenses": _j(s.get("defenses", {})),
            "trained_skills": _j(s.get("trainedSkills", {}).get("value", [])),
            "additional_skill_count": s.get("trainedSkills", {}).get("additional", 0),
            "spellcasting": s.get("spellcasting", 0),
            "ancestry_feat_levels": _j(s.get("ancestryFeatLevels", {}).get("value", [])),
            "class_feat_levels": _j(s.get("classFeatLevels", {}).get("value", [])),
            "general_feat_levels": _j(s.get("generalFeatLevels", {}).get("value", [])),
            "skill_feat_levels": _j(s.get("skillFeatLevels", {}).get("value", [])),
            "skill_increase_levels": _j(s.get("skillIncreaseLevels", {}).get("value", [])),
            "class_features": _j(features),
            "description": _strip_html(s.get("description", {}).get("value", ""))[:2000],
        })
    n = _bulk("classes", rows)
    print(f"  [4/8] classes: {n}")

    # Class features
    rows = []
    for d in _load_pack(packs_dir, "classfeatures"):
        s = d.get("system", {})
        cat = s.get("category", "classfeature")
        if cat not in ("classfeature", "ancestryfeature"):
            continue
        traits = s.get("traits", {}).get("value", [])
        class_slug = ""
        for t in traits:
            if t and t != "classfeature":
                class_slug = t
                break
        rows.append({
            "id": d.get("_id", ""), "name": d.get("name", ""),
            "slug": _slug(d.get("name", "")),
            "level": s.get("level", {}).get("value", 0) if isinstance(s.get("level"), dict) else s.get("level", 0),
            "class_slug": class_slug, "category": cat,
            "rules_summary": ", ".join(r.get("key", "") for r in s.get("rules", []) if isinstance(r, dict))[:200],
            "description": _strip_html(s.get("description", {}).get("value", ""))[:2000],
        })
    n = _bulk("class_features", rows)
    print(f"  [5/8] class_features: {n}")

    # Feats
    rows = []
    for d in _load_pack(packs_dir, "feats"):
        if d.get("type") != "feat":
            continue
        s = d.get("system", {})
        cat = s.get("category", "")
        traits = s.get("traits", {})
        prereqs = s.get("prerequisites", {}).get("value", [])
        prereq_list = [p.get("value", "") for p in prereqs if isinstance(p, dict)]
        class_slug = ""
        ancestry_slug = ""
        trait_vals = traits.get("value", [])
        if cat == "class":
            for t in trait_vals:
                if t and t not in ("feat", "class"):
                    class_slug = t
                    break
        elif cat == "ancestry":
            for t in trait_vals:
                if t and t not in ("feat", "ancestry"):
                    ancestry_slug = t
                    break
        rows.append({
            "id": d.get("_id", ""), "name": d.get("name", ""),
            "slug": _slug(d.get("name", "")),
            "level": s.get("level", {}).get("value", 0) if isinstance(s.get("level"), dict) else s.get("level", 0),
            "category": cat,
            "action_type": s.get("actionType", {}).get("value", "") if isinstance(s.get("actionType"), dict) else "",
            "traits": _j(trait_vals),
            "prerequisites": _j(prereq_list),
            "class_slug": class_slug, "ancestry_slug": ancestry_slug,
            "description": _strip_html(s.get("description", {}).get("value", ""))[:2000],
        })
    n = _bulk("feats", rows)
    print(f"  [6/8] feats: {n}")

    # Spells
    rows = []
    for d in _load_pack(packs_dir, "spells"):
        if d.get("type") != "spell":
            continue
        s = d.get("system", {})
        traits = s.get("traits", {})
        traditions = traits.get("traditions", [])
        rank_val = s.get("level", {}).get("value", 0) if isinstance(s.get("level"), dict) else 0
        is_cantrip = "cantrip" in traits.get("value", [])
        if is_cantrip:
            rank_val = 0
        time_data = s.get("time", {})
        action_cost = str(time_data.get("value", "")) if isinstance(time_data, dict) else ""
        range_obj = s.get("range", {})
        range_val = range_obj.get("value", "") if isinstance(range_obj, dict) else str(range_obj or "")
        area_data = s.get("area", {})
        area_str = ""
        if isinstance(area_data, dict) and area_data.get("type"):
            area_str = f"{area_data.get('value', '')} {area_data.get('type', '')}"
        target_obj = s.get("target", {})
        target = target_obj.get("value", "") if isinstance(target_obj, dict) else str(target_obj or "")
        dur = s.get("duration", {})
        duration = ""
        if isinstance(dur, dict):
            duration = dur.get("value", "")
            if dur.get("sustained"):
                duration = f"sustained {duration}" if duration else "sustained"
        defense_data = s.get("defense", {})
        defense_str = ""
        if isinstance(defense_data, dict):
            save = defense_data.get("save", {})
            if isinstance(save, dict) and save.get("statistic"):
                basic = "basic " if save.get("basic") else ""
                defense_str = f"{basic}{save['statistic']}"
        rows.append({
            "id": d.get("_id", ""), "name": d.get("name", ""),
            "slug": _slug(d.get("name", "")),
            "rank": rank_val, "traditions": _j(traditions),
            "traits": _j(traits.get("value", [])),
            "action_cost": action_cost, "range": range_val or "",
            "area": area_str, "target": target or "",
            "duration": duration or "", "defense": defense_str,
            "description": _strip_html(s.get("description", {}).get("value", ""))[:2000],
        })
    n = _bulk("spells", rows)
    print(f"  [7/8] spells: {n}")

    # Equipment
    rows = []
    for d in _load_pack(packs_dir, "equipment"):
        itype = d.get("type", "")
        if itype not in EQUIPMENT_TYPES:
            continue
        s = d.get("system", {})
        traits = s.get("traits", {})
        price_cp = _price_to_cp(s.get("price", {}).get("value", {}))
        bulk_val = s.get("bulk", {})
        bulk_str = str(bulk_val.get("value", "")) if isinstance(bulk_val, dict) else str(bulk_val)
        damage_data = s.get("damage", {})
        damage_str = ""
        if isinstance(damage_data, dict) and damage_data.get("die"):
            damage_str = f"{damage_data.get('dice', 1)}{damage_data.get('die', '')} {damage_data.get('damageType', '')}"
        ac_bonus = 0
        dex_cap = 99
        category = s.get("category", "")
        if itype == "armor":
            ac_bonus = s.get("acBonus", 0) or 0
            dex_cap = s.get("dexCap", 99) if s.get("dexCap") is not None else 99
        elif itype == "shield":
            ac_bonus = s.get("acBonus", 0) or 0
        rows.append({
            "id": d.get("_id", ""), "name": d.get("name", ""),
            "slug": _slug(d.get("name", "")),
            "item_type": itype, "category": category,
            "price_cp": price_cp, "bulk": bulk_str,
            "traits": _j(traits.get("value", [])),
            "damage": damage_str, "ac_bonus": ac_bonus, "dex_cap": dex_cap,
            "description": _strip_html(s.get("description", {}).get("value", ""))[:2000],
        })
    n = _bulk("equipment", rows)
    print(f"  [8/8] equipment: {n}")

    conn.close()
    size_mb = db_path.stat().st_size / 1024 / 1024
    print(f"  charbuilder.db: {size_mb:.1f} MB")


def apply_translations(db_path: Path, translations_dir: Path):
    """Apply Babele Chinese translations to charbuilder.db."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    BABELE_TABLE_MAP = {
        "pf2e.ancestries.json": "ancestries",
        "pf2e.heritages.json": "heritages",
        "pf2e.backgrounds.json": "backgrounds",
        "pf2e.classes.json": "classes",
        "pf2e.classfeatures.json": "class_features",
        "pf2e.feats-srd.json": "feats",
        "pf2e.spells-srd.json": "spells",
        "pf2e.equipment-srd.json": "equipment",
    }

    def split_bilingual_name(name: str) -> str:
        if not name:
            return ""
        match = re.match(
            r'^([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2000-\u206f'
            r'\u300a\u300b\u201c\u201d\u2018\u2019\u3001\u3002\uff0c'
            r'\uff1b\uff01\uff1f「」『』【】〔〕（）\s\-·]+?)\s+[A-Z\[\(]',
            name,
        )
        if match:
            return match.group(1).strip()
        if re.match(r'^[\u4e00-\u9fff]+$', name):
            return name
        return name

    total = 0
    for filename, table in BABELE_TABLE_MAP.items():
        fp = translations_dir / filename
        if not fp.exists():
            print(f"  [WARN] {filename} not found")
            continue
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", {})
        updated = 0
        for en_name, entry in entries.items():
            if not isinstance(entry, dict):
                continue
            raw_name = entry.get("name", "")
            cn_name = split_bilingual_name(raw_name) if raw_name else ""
            desc_cn = entry.get("description", "")
            if not cn_name and not desc_cn:
                continue
            cursor = conn.execute(
                f"UPDATE {table} SET name_cn = ?, description_cn = ? WHERE name = ?",
                (cn_name, desc_cn, en_name),
            )
            updated += cursor.rowcount
        conn.commit()
        total += updated
        print(f"  {table}: {updated} translations applied")

    conn.close()
    print(f"  Total: {total} translations")


def export_rules_seed(game_db_path: Path, output_path: Path):
    """Export compendium_entries + creatures from game.db as gzipped JSON lines."""
    if not game_db_path.exists():
        print(f"  [WARN] game.db not found at {game_db_path}, skipping rules seed export")
        return

    conn = sqlite3.connect(str(game_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    records = []

    for row in conn.execute("SELECT * FROM compendium_entries"):
        rec = dict(row)
        rec["_table"] = "compendium_entries"
        records.append(rec)

    for row in conn.execute("SELECT * FROM creatures"):
        rec = dict(row)
        rec["_table"] = "creatures"
        records.append(rec)

    conn.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(str(output_path), "wt", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  rules_seed.json.gz: {size_mb:.1f} MB ({len(records)} records)")


def main():
    parser = argparse.ArgumentParser(description="Build PF2e default databases")
    parser.add_argument("--packs-dir", required=True, help="Path to extracted packs JSON directory")
    parser.add_argument("--translations-dir", help="Path to Babele compendium translations directory")
    parser.add_argument("--output-dir", required=True, help="Output directory for default data files")
    parser.add_argument("--game-db", help="Path to existing game.db for rules seed export")
    args = parser.parse_args()

    packs_dir = Path(args.packs_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cb_path = output_dir / "charbuilder.db"

    print("=" * 50)
    print("  Building PF2e Default Databases")
    print("=" * 50)

    print(f"\n[Step 1] Building charbuilder.db from {packs_dir}")
    build_charbuilder(packs_dir, cb_path)

    if args.translations_dir:
        trans_dir = Path(args.translations_dir).resolve()
        if trans_dir.exists():
            print(f"\n[Step 2] Applying Chinese translations from {trans_dir}")
            apply_translations(cb_path, trans_dir)
        else:
            print(f"\n[Step 2] SKIP: translations dir not found: {trans_dir}")
    else:
        print("\n[Step 2] SKIP: no --translations-dir provided")

    if args.game_db:
        game_db = Path(args.game_db).resolve()
        seed_path = output_dir / "rules_seed.json.gz"
        print(f"\n[Step 3] Exporting rules seed from {game_db}")
        export_rules_seed(game_db, seed_path)
    else:
        print("\n[Step 3] SKIP: no --game-db provided")

    print("\n" + "=" * 50)
    print("  Build Complete!")
    print("=" * 50)
    for f in output_dir.iterdir():
        if f.name.startswith("_") or f.is_dir():
            continue
        print(f"  {f.name}: {f.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
