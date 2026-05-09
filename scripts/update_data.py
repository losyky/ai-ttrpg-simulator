"""Universal data updater CLI for all game systems.

Updates game system data from external FVTT sources or resets to built-in defaults.

Usage:
  # Reset PF2e to defaults (no external data needed)
  python scripts/update_data.py --reset pf2e

  # Update PF2e from external FVTT system directory
  python scripts/update_data.py --system pf2e --packs /path/to/pf2e --translations /path/to/babele/compendium

  # Update Daggerheart from FVTT system directory
  python scripts/update_data.py --system daggerheart --packs /path/to/daggerheart

  # Update SWADE from FVTT system directory
  python scripts/update_data.py --system swade --packs /path/to/swade

  # Show current data status
  python scripts/update_data.py --status
"""

import argparse
import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

sys.path.insert(0, str(BACKEND_DIR))


def show_status():
    from app.config import settings

    print("=" * 60)
    print("  Game System Data Status")
    print("=" * 60)

    # PF2e
    cb_path = Path(settings.data_dir) / "charbuilder.db"
    rules_path = Path(settings.db_path)
    default_cb = BACKEND_DIR / "app" / "systems" / "pf2e" / "default_data" / "charbuilder.db"
    default_seed = BACKEND_DIR / "app" / "systems" / "pf2e" / "default_data" / "rules_seed.json.gz"

    print("\n[PF2e]")
    print(f"  charbuilder.db:  {'OK' if cb_path.exists() else 'MISSING'} ({cb_path.stat().st_size // 1024} KB)" if cb_path.exists() else f"  charbuilder.db:  MISSING")
    print(f"  game.db (rules): {'OK' if rules_path.exists() else 'MISSING'} ({rules_path.stat().st_size // 1024} KB)" if rules_path.exists() else f"  game.db (rules): MISSING")
    print(f"  Default charbuilder.db: {'YES' if default_cb.exists() else 'NO'}")
    print(f"  Default rules_seed.gz:  {'YES' if default_seed.exists() else 'NO'}")

    if cb_path.exists():
        conn = sqlite3.connect(str(cb_path))
        for t in ["ancestries", "heritages", "backgrounds", "classes", "feats", "spells", "equipment"]:
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"    {t}: {cnt}")
            except Exception:
                print(f"    {t}: (error)")
        conn.close()

    # DH
    dh_dir = BACKEND_DIR / "app" / "systems" / "daggerheart" / "default_packs" / "processed"
    print("\n[Daggerheart]")
    if dh_dir.exists():
        packs = [f for f in dh_dir.glob("*.json") if f.name != "_index.json"]
        print(f"  Default packs: {len(packs)} files")
    else:
        print("  Default packs: MISSING")

    # SWADE
    swade_dir = BACKEND_DIR / "app" / "systems" / "swade" / "default_packs" / "processed"
    print("\n[SWADE/七物语]")
    if swade_dir.exists():
        packs = [f for f in swade_dir.glob("*.json") if f.name != "_index.json"]
        print(f"  Default packs: {len(packs)} files")
    else:
        print("  Default packs: MISSING")

    print()


def reset_pf2e():
    from app.config import settings

    default_data = BACKEND_DIR / "app" / "systems" / "pf2e" / "default_data"

    # Reset charbuilder.db
    cb_default = default_data / "charbuilder.db"
    cb_target = Path(settings.data_dir) / "charbuilder.db"
    if cb_default.exists():
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(cb_target) + suffix)
            if p.exists():
                p.unlink()
        shutil.copy2(str(cb_default), str(cb_target))
        print(f"  charbuilder.db reset ({cb_default.stat().st_size // 1024} KB)")
    else:
        print("  [ERROR] Default charbuilder.db not found!")

    # Reset rules
    seed_path = default_data / "rules_seed.json.gz"
    if seed_path.exists():
        db_path = Path(settings.db_path)
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        # Re-create and seed
        from app.systems.pf2e.ruledb import get_conn
        from app.systems.pf2e import ruledb
        ruledb._conn = None
        get_conn()
        print("  game.db rules reset from seed")
    else:
        print("  [WARN] Default rules_seed.json.gz not found")


def update_pf2e(packs_path: str | None, translations_path: str | None):
    if not packs_path:
        print("[ERROR] --packs is required for PF2e update")
        sys.exit(1)

    packs = Path(packs_path).resolve()
    if not packs.exists():
        print(f"[ERROR] Packs path not found: {packs}")
        sys.exit(1)

    has_leveldb = False
    packs_subdir = packs / "packs"
    if packs_subdir.exists():
        for d in packs_subdir.iterdir():
            if d.is_dir() and (d / "CURRENT").exists():
                has_leveldb = True
                break

    if has_leveldb:
        print("[1] Extracting LevelDB packs...")
        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.run(
                ["node", str(SCRIPTS_DIR / "extract_fvtt_packs.mjs"), str(packs), tmpdir],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            )
            if proc.returncode != 0:
                print(f"  [ERROR] Extraction failed:\n{proc.stderr}")
                sys.exit(1)
            print(f"  Extracted to temp dir")

            print("[2] Building charbuilder.db...")
            _build_cb(Path(tmpdir), translations_path)
    else:
        json_dir = packs_subdir if packs_subdir.exists() else packs
        print("[1] Building charbuilder.db from JSON packs...")
        _build_cb(json_dir, translations_path)

    if translations_path:
        trans = Path(translations_path).resolve()
        if trans.exists():
            print("[3] Importing Babele rules...")
            _import_rules(trans)


def _build_cb(packs_dir: Path, translations_path: str | None):
    from app.config import settings
    from app.systems.pf2e.ingest.build_default_dbs import build_charbuilder, apply_translations

    cb_target = Path(settings.data_dir) / "charbuilder.db"
    build_charbuilder(packs_dir, cb_target)
    if translations_path:
        t = Path(translations_path).resolve()
        if t.exists():
            apply_translations(cb_target, t)


def _import_rules(compendium_dir: Path):
    from app.systems.pf2e.ruledb import ingest_compendium_file, rebuild_fts, get_conn

    conn = get_conn()
    conn.execute("DELETE FROM compendium_entries")
    conn.execute("DELETE FROM creatures")
    conn.commit()

    for fp in sorted(compendium_dir.glob("*.json")):
        try:
            n = ingest_compendium_file(str(fp))
            if n > 0:
                print(f"    + {fp.name}: {n}")
        except Exception as e:
            print(f"    X {fp.name}: {e}")

    rebuild_fts()
    print("  Rules import complete")


def update_dh_swade(system_id: str, packs_path: str):
    packs = Path(packs_path).resolve()
    if not packs.exists():
        print(f"[ERROR] System path not found: {packs}")
        sys.exit(1)

    output_dir = BACKEND_DIR / "app" / "systems" / system_id / "default_packs"
    print(f"Extracting {system_id} packs...")

    proc = subprocess.run(
        ["node", str(SCRIPTS_DIR / "extract_fvtt_packs.mjs"), str(packs), str(output_dir)],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"[ERROR] Extraction failed:\n{proc.stderr}")
        sys.exit(1)

    # Run post-processing if applicable
    if system_id == "daggerheart":
        apply_cn_script = SCRIPTS_DIR / "apply_dh_cn.mjs"
        if apply_cn_script.exists():
            print("Applying DH Chinese translations...")
            proc2 = subprocess.run(
                ["node", str(apply_cn_script)],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            )
            if proc2.returncode == 0:
                print("  DH translations applied")
            else:
                print(f"  [WARN] DH translation failed: {proc2.stderr[:200]}")

    print(f"{system_id} data updated successfully")


def main():
    parser = argparse.ArgumentParser(description="Game System Data Updater")
    parser.add_argument("--status", action="store_true", help="Show current data status")
    parser.add_argument("--reset", metavar="SYSTEM", help="Reset system to built-in defaults (pf2e)")
    parser.add_argument("--system", metavar="ID", help="System to update (pf2e, daggerheart, swade)")
    parser.add_argument("--packs", metavar="PATH", help="Path to FVTT system directory")
    parser.add_argument("--translations", metavar="PATH", help="Path to Babele translations (PF2e only)")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.reset:
        if args.reset == "pf2e":
            print("Resetting PF2e to built-in defaults...")
            reset_pf2e()
            print("Done!")
        else:
            print(f"Reset not yet supported for: {args.reset}")
        return

    if args.system:
        if args.system == "pf2e":
            update_pf2e(args.packs, args.translations)
        elif args.system in ("daggerheart", "swade"):
            if not args.packs:
                print(f"[ERROR] --packs is required for {args.system} update")
                sys.exit(1)
            update_dh_swade(args.system, args.packs)
        else:
            print(f"Unknown system: {args.system}")
            sys.exit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
