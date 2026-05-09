"""Load Babele Chinese translations and merge into charbuilder_db.

Translation files are in pf2e_compendium_chn/compendium/pf2e.*.json.
Each file has: { "entries": { "English Name": { "name": "中文名 English Name", "description": "..." } } }

Join key: English item `name` == Babele entries object key (exact string match).
"""

import json
import re
import sys
from pathlib import Path

# Map Babele files to charbuilder DB tables
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
    """Extract Chinese portion from bilingual name like '半蛛人 Anadi' -> '半蛛人'.

    If no Chinese found, returns the original name.
    """
    if not name:
        return ""
    # Match Chinese characters at the start, followed by space and ASCII letter
    match = re.match(r'^([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2000-\u206f\u300a\u300b\u201c\u201d\u2018\u2019\u3001\u3002\uff0c\uff1b\uff01\uff1f「」『』【】〔〕（）\s\-·]+?)\s+[A-Z\[\(]', name)
    if match:
        return match.group(1).strip()
    # If name is entirely CJK
    if re.match(r'^[\u4e00-\u9fff]+$', name):
        return name
    return name


def load_babele_file(filepath: Path) -> dict[str, dict]:
    """Load a single Babele translation file.

    Returns: { "English Name": { "name_cn": "中文名", "description_cn": "...", ... } }
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

    entries = data.get("entries", {})
    result = {}

    for english_name, entry in entries.items():
        if not isinstance(entry, dict):
            continue

        raw_name = entry.get("name", "")
        cn_name = split_bilingual_name(raw_name) if raw_name else ""

        translated = {
            "name_cn": cn_name,
            "description_cn": entry.get("description", ""),
        }

        # Some entries have extra translated fields
        if "prerequisites" in entry:
            prereqs = entry["prerequisites"]
            if isinstance(prereqs, list):
                translated["prerequisites_cn"] = json.dumps(prereqs, ensure_ascii=False)
        if "duration" in entry:
            translated["duration_cn"] = entry["duration"]
        if "target" in entry:
            translated["target_cn"] = entry["target"]
        if "cost" in entry:
            translated["cost_cn"] = entry["cost"]

        result[english_name] = translated

    return result


def load_all_translations(compendium_dir: Path) -> dict[str, dict[str, dict]]:
    """Load all Babele translations.

    Returns: { "table_name": { "English Name": { "name_cn": ..., "description_cn": ... } } }
    """
    all_translations = {}

    for filename, table in BABELE_TABLE_MAP.items():
        filepath = compendium_dir / filename
        if filepath.exists():
            translations = load_babele_file(filepath)
            all_translations[table] = translations
            print(f"  Loaded {len(translations)} translations for {table} from {filename}")
        else:
            print(f"  [WARN] Translation file not found: {filepath}")
            all_translations[table] = {}

    return all_translations


def apply_translations_to_db(translations: dict[str, dict[str, dict]]) -> dict[str, int]:
    """Apply translations to the charbuilder database.

    Adds name_cn and description_cn columns if they don't exist,
    then updates rows by matching English name.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
    from app.systems.pf2e.charbuilder_db import get_conn

    conn = get_conn()

    # Ensure CN columns exist on all tables
    tables_with_cn = [
        "ancestries", "heritages", "backgrounds", "classes",
        "class_features", "feats", "spells", "equipment",
    ]
    for table in tables_with_cn:
        for col in ["name_cn", "description_cn"]:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
            except Exception:
                pass  # Column already exists

    # Also add prerequisites_cn for feats
    try:
        conn.execute("ALTER TABLE feats ADD COLUMN prerequisites_cn TEXT NOT NULL DEFAULT '[]'")
    except Exception:
        pass

    conn.commit()

    stats = {}

    for table, entries in translations.items():
        if not entries:
            stats[table] = 0
            continue

        updated = 0
        for english_name, fields in entries.items():
            name_cn = fields.get("name_cn", "")
            desc_cn = fields.get("description_cn", "")

            if not name_cn and not desc_cn:
                continue

            # Try matching by name
            extra_sets = []
            extra_params = []

            if table == "feats" and "prerequisites_cn" in fields:
                extra_sets.append("prerequisites_cn = ?")
                extra_params.append(fields["prerequisites_cn"])

            set_clause = "name_cn = ?, description_cn = ?"
            if extra_sets:
                set_clause += ", " + ", ".join(extra_sets)

            params = [name_cn, desc_cn] + extra_params + [english_name]

            cursor = conn.execute(
                f"UPDATE {table} SET {set_clause} WHERE name = ?",
                params,
            )
            updated += cursor.rowcount

        conn.commit()
        stats[table] = updated

    return stats


def main():
    """Run translation merge as standalone script.

    Usage:
      python -m app.systems.pf2e.ingest.translations <translations_dir>
      Or set FVTT_PF2E_TRANSLATIONS environment variable.
    """
    import os

    compendium_dir = None
    if len(sys.argv) > 1:
        compendium_dir = Path(sys.argv[1]).resolve()
    else:
        env = os.environ.get("FVTT_PF2E_TRANSLATIONS")
        if env:
            compendium_dir = Path(env).resolve()

    if compendium_dir is None or not compendium_dir.exists():
        print("[ERROR] No PF2e translation directory provided or directory not found.")
        print("  Usage: python -m app.systems.pf2e.ingest.translations <translations_dir>")
        print("  Or set FVTT_PF2E_TRANSLATIONS environment variable.")
        if compendium_dir:
            print(f"  Provided path: {compendium_dir}")
        sys.exit(1)

    print(f"  Found translations at: {compendium_dir}")

    print("Loading Babele translations...")
    translations = load_all_translations(compendium_dir)

    print("\nApplying translations to charbuilder database...")
    stats = apply_translations_to_db(translations)

    print("\n============================================")
    print("  Translation Merge Complete")
    print("============================================")
    total = 0
    for table, count in stats.items():
        print(f"  {table}: {count} entries translated")
        total += count
    print(f"  Total: {total} translations applied")
    print("============================================")


if __name__ == "__main__":
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
    main()
