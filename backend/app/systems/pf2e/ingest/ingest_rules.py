"""Batch-ingest PF2e compendium data into the structured SQLite database.

Unlike blind vectorization, this preserves the full structure of each
compendium entry (name, category, prerequisites, duration, etc.) and
makes them queryable via SQL and full-text search.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.config import settings
from app.systems.pf2e.ruledb import ingest_compendium_file, get_stats, rebuild_fts


def main():
    import os

    compendium_dir = None
    if len(sys.argv) > 1:
        compendium_dir = Path(sys.argv[1]).resolve()
    else:
        env = os.environ.get("FVTT_PF2E_COMPENDIUM")
        if env:
            compendium_dir = Path(env).resolve()

    if compendium_dir is None or not compendium_dir.exists():
        print("[ERROR] No PF2e compendium directory provided or directory not found.")
        print("  Usage: python -m app.systems.pf2e.ingest.ingest_rules <compendium_dir>")
        print("  Or set FVTT_PF2E_COMPENDIUM environment variable.")
        if compendium_dir:
            print(f"  Provided path: {compendium_dir}")
        sys.exit(1)

    # Delete old database to avoid corruption from previous runs
    db_path = Path(settings.db_path)
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()
            print(f"  Deleted old DB file: {p.name}")

    json_files = sorted(compendium_dir.glob("*.json"))
    print(f"\nFound {len(json_files)} compendium files\n")

    total = 0
    errors = 0
    for filepath in json_files:
        try:
            count = ingest_compendium_file(str(filepath))
            total += count
            if count > 0:
                print(f"  + {filepath.name}: {count}")
            else:
                print(f"  - {filepath.name}: (empty)")
        except Exception as exc:
            errors += 1
            print(f"  X {filepath.name}: {exc}")

    # Rebuild FTS index ONCE after all files are ingested
    print("\nBuilding full-text search index...")
    try:
        rebuild_fts()
        print("  FTS index built successfully")
    except Exception as exc:
        print(f"  FTS index error: {exc}")

    stats = get_stats()
    print(f"\nDone! Total: {stats['total']} entries")
    print(f"  Rules (feats/spells/actions/...): {stats['entries']}")
    print(f"  Creatures/NPCs: {stats['creatures']}")
    if errors > 0:
        print(f"  Errors: {errors} files skipped")
    print(f"\nDB supports: exact name lookup / category filter / full-text search")


if __name__ == "__main__":
    main()
