"""API router for updating/re-importing game system data from external FVTT sources.

Supports:
  - PF2e:  Import from FVTT LevelDB packs + Babele translations
  - DH:    Import from FVTT LevelDB packs
  - SWADE:  Import from FVTT LevelDB packs

Also provides a "reset to defaults" endpoint that re-seeds databases
from the built-in default data shipped with the application.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/data", tags=["data-updater"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
_PF2E_DIR = _PROJECT_ROOT / "backend" / "app" / "systems" / "pf2e"
_PF2E_DEFAULT_DATA = _PF2E_DIR / "default_data"


class PF2eUpdateRequest(BaseModel):
    packs_path: str | None = None
    translations_path: str | None = None


class ResetRequest(BaseModel):
    system_id: str
    target: str = "all"  # "charbuilder" | "rules" | "all"


class FVTTImportRequest(BaseModel):
    system_id: str
    system_path: str


# ── Status tracking ──

_update_status: dict[str, Any] = {}


@router.get("/update/status")
async def get_update_status():
    return _update_status


# ── PF2e: Reset to defaults ──

@router.post("/pf2e/reset")
async def reset_pf2e_data(req: ResetRequest):
    """Reset PF2e databases to built-in defaults."""
    results = {}

    if req.target in ("charbuilder", "all"):
        cb_default = _PF2E_DEFAULT_DATA / "charbuilder.db"
        cb_target = Path(settings.data_dir) / "charbuilder.db"
        if cb_default.exists():
            for suffix in ("", "-wal", "-shm"):
                p = Path(str(cb_target) + suffix)
                if p.exists():
                    p.unlink()
            shutil.copy2(str(cb_default), str(cb_target))
            results["charbuilder"] = f"Reset ({cb_default.stat().st_size // 1024} KB)"

            # Clear cached connection
            from app.systems.pf2e import charbuilder_db
            charbuilder_db._conn = None
        else:
            results["charbuilder"] = "No default data found"

    if req.target in ("rules", "all"):
        seed_path = _PF2E_DEFAULT_DATA / "rules_seed.json.gz"
        if seed_path.exists():
            db_path = Path(settings.db_path)
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            conn.execute("DELETE FROM compendium_entries")
            conn.execute("DELETE FROM creatures")
            conn.commit()
            conn.close()

            # Re-trigger seed import by resetting module connection
            from app.systems.pf2e import ruledb
            ruledb._conn = None
            ruledb.get_conn()
            results["rules"] = "Reset from seed"
        else:
            results["rules"] = "No seed data found"

    return {"status": "ok", "results": results}


# ── PF2e: Update from external FVTT source ──

@router.post("/pf2e/update")
async def update_pf2e_data(req: PF2eUpdateRequest):
    """Update PF2e data from external FVTT system packs + translations.

    This runs extraction and ingestion in a background task.
    """
    global _update_status
    _update_status = {"system": "pf2e", "status": "running", "steps": []}

    try:
        results = await asyncio.to_thread(_run_pf2e_update, req)
        _update_status["status"] = "completed"
        _update_status["results"] = results
        return {"status": "ok", "results": results}
    except Exception as exc:
        _update_status["status"] = "error"
        _update_status["error"] = str(exc)
        raise HTTPException(500, str(exc))


def _run_pf2e_update(req: PF2eUpdateRequest) -> dict:
    results = {}
    steps = _update_status.get("steps", [])

    if req.packs_path:
        packs_path = Path(req.packs_path).resolve()
        if not packs_path.exists():
            raise ValueError(f"Packs path not found: {packs_path}")

        # Step 1: Extract LevelDB if needed (check if packs contain .ldb files)
        has_leveldb = any(
            (packs_path / "packs" / d).is_dir() and (packs_path / "packs" / d / "CURRENT").exists()
            for d in os.listdir(packs_path / "packs") if (packs_path / "packs" / d).is_dir()
        ) if (packs_path / "packs").exists() else False

        if has_leveldb:
            steps.append("Extracting LevelDB packs...")
            with tempfile.TemporaryDirectory() as tmpdir:
                extract_cmd = [
                    "node", str(_SCRIPTS_DIR / "extract_fvtt_packs.mjs"),
                    str(packs_path), tmpdir,
                ]
                proc = subprocess.run(extract_cmd, capture_output=True, text=True, cwd=str(_PROJECT_ROOT))
                if proc.returncode != 0:
                    raise RuntimeError(f"LevelDB extraction failed: {proc.stderr}")
                steps.append(f"Extracted packs to temp dir")

                # Step 2: Build charbuilder.db
                steps.append("Building charbuilder database...")
                _build_charbuilder_from_packs(Path(tmpdir), req.translations_path)
                results["charbuilder"] = "Updated from LevelDB packs"
        else:
            json_dir = packs_path / "packs" if (packs_path / "packs").exists() else packs_path
            steps.append("Building charbuilder from JSON packs...")
            _build_charbuilder_from_packs(json_dir, req.translations_path)
            results["charbuilder"] = "Updated from JSON packs"

    if req.translations_path:
        trans_path = Path(req.translations_path).resolve()
        if trans_path.exists():
            steps.append("Importing Babele translations for rules...")
            _import_babele_rules(trans_path)
            results["rules"] = "Updated with translations"
        else:
            results["rules"] = f"Translations path not found: {trans_path}"

    return results


def _build_charbuilder_from_packs(packs_dir: Path, translations_path: str | None):
    """Rebuild charbuilder.db from extracted pack data."""
    from app.systems.pf2e.ingest.build_default_dbs import build_charbuilder, apply_translations

    cb_target = Path(settings.data_dir) / "charbuilder.db"
    build_charbuilder(packs_dir, cb_target)

    if translations_path:
        trans_dir = Path(translations_path).resolve()
        if trans_dir.exists():
            apply_translations(cb_target, trans_dir)

    # Reset cached connection
    from app.systems.pf2e import charbuilder_db
    charbuilder_db._conn = None


def _import_babele_rules(compendium_dir: Path):
    """Re-import Babele translation files into game.db rule tables."""
    from app.systems.pf2e.ruledb import get_conn as get_rule_conn, ingest_compendium_file, rebuild_fts

    conn = get_rule_conn()
    conn.execute("DELETE FROM compendium_entries")
    conn.execute("DELETE FROM creatures")
    conn.commit()

    json_files = sorted(compendium_dir.glob("*.json"))
    for fp in json_files:
        try:
            ingest_compendium_file(str(fp))
        except Exception:
            pass

    try:
        rebuild_fts()
    except Exception:
        pass


# ── DH / SWADE: Update from external FVTT source ──

@router.post("/fvtt-import")
async def import_fvtt_packs(req: FVTTImportRequest):
    """Generic FVTT pack import for any system (DH, SWADE, or PF2e).

    Extracts LevelDB packs from the given system path into the
    system's default_packs directory.
    """
    system_path = Path(req.system_path).resolve()
    if not system_path.exists():
        raise HTTPException(400, f"System path not found: {system_path}")

    system_map = {
        "daggerheart": _PROJECT_ROOT / "backend" / "app" / "systems" / "daggerheart" / "default_packs",
        "swade": _PROJECT_ROOT / "backend" / "app" / "systems" / "swade" / "default_packs",
        "pf2e": _PROJECT_ROOT / "backend" / "app" / "systems" / "pf2e" / "default_data",
    }

    output_dir = system_map.get(req.system_id)
    if not output_dir:
        raise HTTPException(400, f"Unknown system: {req.system_id}")

    try:
        result = await asyncio.to_thread(
            _extract_fvtt_packs, system_path, output_dir,
        )
        return {"status": "ok", "system_id": req.system_id, "result": result}
    except Exception as exc:
        raise HTTPException(500, str(exc))


def _extract_fvtt_packs(system_path: Path, output_dir: Path) -> dict:
    extract_cmd = [
        "node", str(_SCRIPTS_DIR / "extract_fvtt_packs.mjs"),
        str(system_path), str(output_dir),
    ]
    proc = subprocess.run(
        extract_cmd, capture_output=True, text=True,
        cwd=str(_PROJECT_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Extraction failed: {proc.stderr}")
    return {"output": proc.stdout[-500:] if len(proc.stdout) > 500 else proc.stdout}


# ── Info: Current data status ──

@router.get("/status")
async def data_status():
    """Return the current state of all system databases."""
    info: dict[str, Any] = {}

    # PF2e
    cb_path = Path(settings.data_dir) / "charbuilder.db"
    rules_path = Path(settings.db_path)
    pf2e_info: dict[str, Any] = {
        "charbuilder_db_exists": cb_path.exists(),
        "charbuilder_db_size_mb": round(cb_path.stat().st_size / 1024 / 1024, 1) if cb_path.exists() else 0,
        "rules_db_exists": rules_path.exists(),
        "rules_db_size_mb": round(rules_path.stat().st_size / 1024 / 1024, 1) if rules_path.exists() else 0,
        "default_charbuilder_exists": _PF2E_DEFAULT_DATA.joinpath("charbuilder.db").exists(),
        "default_rules_seed_exists": _PF2E_DEFAULT_DATA.joinpath("rules_seed.json.gz").exists(),
    }
    if cb_path.exists():
        try:
            conn = sqlite3.connect(str(cb_path))
            tables = ["ancestries", "heritages", "backgrounds", "classes", "feats", "spells", "equipment"]
            counts = {}
            for t in tables:
                try:
                    counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                except Exception:
                    counts[t] = 0
            pf2e_info["charbuilder_counts"] = counts
            conn.close()
        except Exception:
            pass
    info["pf2e"] = pf2e_info

    # DH
    dh_packs = _PROJECT_ROOT / "backend" / "app" / "systems" / "daggerheart" / "default_packs" / "processed"
    info["daggerheart"] = {
        "default_packs_exist": dh_packs.exists(),
        "pack_count": len(list(dh_packs.glob("*.json"))) - 1 if dh_packs.exists() else 0,
    }

    # SWADE
    swade_packs = _PROJECT_ROOT / "backend" / "app" / "systems" / "swade" / "default_packs" / "processed"
    info["swade"] = {
        "default_packs_exist": swade_packs.exists(),
        "pack_count": len(list(swade_packs.glob("*.json"))) - 1 if swade_packs.exists() else 0,
    }

    return info
