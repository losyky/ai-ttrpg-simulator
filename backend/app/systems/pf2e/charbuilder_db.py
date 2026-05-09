"""Character Builder Database — indexes PF2e compendium data for AI-driven
character creation.

Stores ancestries, heritages, backgrounds, classes, feats, spells, and
equipment in SQLite with structured fields so the AI can query valid
options, check prerequisites, and assemble legal character sheets.

On first connection, if the database is empty, it is automatically seeded
from the built-in default at  systems/pf2e/default_data/charbuilder.db.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from app.config import settings

_DB_NAME = "charbuilder.db"
_DEFAULT_DB = Path(__file__).resolve().parent / "default_data" / "charbuilder.db"
_conn: sqlite3.Connection | None = None


def _db_path() -> Path:
    return Path(settings.data_dir) / _DB_NAME


def _seed_from_default(target: Path) -> None:
    """Copy the built-in default charbuilder.db if the target is missing or empty."""
    if not _DEFAULT_DB.exists():
        return
    if target.exists() and target.stat().st_size > 4096:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(_DEFAULT_DB), str(target))


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        p = _db_path()
        _seed_from_default(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(p), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        init_tables(_conn)
    return _conn


def init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ancestries (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            slug            TEXT NOT NULL,
            hp              INTEGER NOT NULL DEFAULT 0,
            size            TEXT NOT NULL DEFAULT 'med',
            speed           INTEGER NOT NULL DEFAULT 25,
            vision          TEXT NOT NULL DEFAULT 'normal',
            boosts          TEXT NOT NULL DEFAULT '{}',
            flaws           TEXT NOT NULL DEFAULT '{}',
            languages       TEXT NOT NULL DEFAULT '[]',
            traits          TEXT NOT NULL DEFAULT '[]',
            description     TEXT NOT NULL DEFAULT '',
            name_cn         TEXT NOT NULL DEFAULT '',
            description_cn  TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS heritages (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            slug            TEXT NOT NULL,
            ancestry_slug   TEXT,
            traits          TEXT NOT NULL DEFAULT '[]',
            rules_summary   TEXT NOT NULL DEFAULT '',
            description     TEXT NOT NULL DEFAULT '',
            name_cn         TEXT NOT NULL DEFAULT '',
            description_cn  TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS backgrounds (
            id                  TEXT PRIMARY KEY,
            name                TEXT NOT NULL,
            slug                TEXT NOT NULL,
            boosts              TEXT NOT NULL DEFAULT '{}',
            trained_skills      TEXT NOT NULL DEFAULT '[]',
            lore                TEXT NOT NULL DEFAULT '[]',
            granted_feat_names  TEXT NOT NULL DEFAULT '[]',
            description         TEXT NOT NULL DEFAULT '',
            name_cn             TEXT NOT NULL DEFAULT '',
            description_cn      TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS classes (
            id                      TEXT PRIMARY KEY,
            name                    TEXT NOT NULL,
            slug                    TEXT NOT NULL,
            hp_per_level            INTEGER NOT NULL DEFAULT 0,
            key_ability             TEXT NOT NULL DEFAULT '[]',
            perception_rank         INTEGER NOT NULL DEFAULT 0,
            saves                   TEXT NOT NULL DEFAULT '{}',
            attacks                 TEXT NOT NULL DEFAULT '{}',
            defenses                TEXT NOT NULL DEFAULT '{}',
            trained_skills          TEXT NOT NULL DEFAULT '[]',
            additional_skill_count  INTEGER NOT NULL DEFAULT 0,
            spellcasting            INTEGER NOT NULL DEFAULT 0,
            ancestry_feat_levels    TEXT NOT NULL DEFAULT '[]',
            class_feat_levels       TEXT NOT NULL DEFAULT '[]',
            general_feat_levels     TEXT NOT NULL DEFAULT '[]',
            skill_feat_levels       TEXT NOT NULL DEFAULT '[]',
            skill_increase_levels   TEXT NOT NULL DEFAULT '[]',
            class_features          TEXT NOT NULL DEFAULT '[]',
            description             TEXT NOT NULL DEFAULT '',
            name_cn                 TEXT NOT NULL DEFAULT '',
            description_cn          TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS class_features (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            slug            TEXT NOT NULL,
            level           INTEGER NOT NULL DEFAULT 0,
            class_slug      TEXT NOT NULL DEFAULT '',
            category        TEXT NOT NULL DEFAULT 'classfeature',
            rules_summary   TEXT NOT NULL DEFAULT '',
            description     TEXT NOT NULL DEFAULT '',
            name_cn         TEXT NOT NULL DEFAULT '',
            description_cn  TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS feats (
            id                  TEXT PRIMARY KEY,
            name                TEXT NOT NULL,
            slug                TEXT NOT NULL,
            level               INTEGER NOT NULL DEFAULT 0,
            category            TEXT NOT NULL DEFAULT '',
            action_type         TEXT NOT NULL DEFAULT '',
            traits              TEXT NOT NULL DEFAULT '[]',
            prerequisites       TEXT NOT NULL DEFAULT '[]',
            class_slug          TEXT NOT NULL DEFAULT '',
            ancestry_slug       TEXT NOT NULL DEFAULT '',
            description         TEXT NOT NULL DEFAULT '',
            name_cn             TEXT NOT NULL DEFAULT '',
            description_cn      TEXT NOT NULL DEFAULT '',
            prerequisites_cn    TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS spells (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            slug            TEXT NOT NULL,
            rank            INTEGER NOT NULL DEFAULT 0,
            traditions      TEXT NOT NULL DEFAULT '[]',
            traits          TEXT NOT NULL DEFAULT '[]',
            action_cost     TEXT NOT NULL DEFAULT '',
            range           TEXT NOT NULL DEFAULT '',
            area            TEXT NOT NULL DEFAULT '',
            target          TEXT NOT NULL DEFAULT '',
            duration        TEXT NOT NULL DEFAULT '',
            defense         TEXT NOT NULL DEFAULT '',
            description     TEXT NOT NULL DEFAULT '',
            name_cn         TEXT NOT NULL DEFAULT '',
            description_cn  TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS equipment (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            slug            TEXT NOT NULL,
            item_type       TEXT NOT NULL DEFAULT '',
            category        TEXT NOT NULL DEFAULT '',
            price_cp        INTEGER NOT NULL DEFAULT 0,
            bulk            TEXT NOT NULL DEFAULT '',
            traits          TEXT NOT NULL DEFAULT '[]',
            damage          TEXT NOT NULL DEFAULT '',
            ac_bonus        INTEGER NOT NULL DEFAULT 0,
            dex_cap         INTEGER NOT NULL DEFAULT 99,
            description     TEXT NOT NULL DEFAULT '',
            name_cn         TEXT NOT NULL DEFAULT '',
            description_cn  TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_heritages_ancestry ON heritages(ancestry_slug);
        CREATE INDEX IF NOT EXISTS idx_feats_category ON feats(category);
        CREATE INDEX IF NOT EXISTS idx_feats_class ON feats(class_slug);
        CREATE INDEX IF NOT EXISTS idx_feats_ancestry ON feats(ancestry_slug);
        CREATE INDEX IF NOT EXISTS idx_feats_level ON feats(level);
        CREATE INDEX IF NOT EXISTS idx_spells_rank ON spells(rank);
        CREATE INDEX IF NOT EXISTS idx_equipment_type ON equipment(item_type);
        CREATE INDEX IF NOT EXISTS idx_class_features_class ON class_features(class_slug);
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Insert helpers (used by the ingest script)
# ---------------------------------------------------------------------------

def upsert_ancestry(row: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO ancestries
        (id, name, slug, hp, size, speed, vision, boosts, flaws, languages, traits, description)
        VALUES (:id, :name, :slug, :hp, :size, :speed, :vision, :boosts, :flaws, :languages, :traits, :description)
    """, row)
    conn.commit()


def upsert_heritage(row: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO heritages
        (id, name, slug, ancestry_slug, traits, rules_summary, description)
        VALUES (:id, :name, :slug, :ancestry_slug, :traits, :rules_summary, :description)
    """, row)
    conn.commit()


def upsert_background(row: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO backgrounds
        (id, name, slug, boosts, trained_skills, lore, granted_feat_names, description)
        VALUES (:id, :name, :slug, :boosts, :trained_skills, :lore, :granted_feat_names, :description)
    """, row)
    conn.commit()


def upsert_class(row: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO classes
        (id, name, slug, hp_per_level, key_ability, perception_rank,
         saves, attacks, defenses, trained_skills, additional_skill_count,
         spellcasting, ancestry_feat_levels, class_feat_levels,
         general_feat_levels, skill_feat_levels, skill_increase_levels,
         class_features, description)
        VALUES (:id, :name, :slug, :hp_per_level, :key_ability, :perception_rank,
                :saves, :attacks, :defenses, :trained_skills, :additional_skill_count,
                :spellcasting, :ancestry_feat_levels, :class_feat_levels,
                :general_feat_levels, :skill_feat_levels, :skill_increase_levels,
                :class_features, :description)
    """, row)
    conn.commit()


def upsert_class_feature(row: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO class_features
        (id, name, slug, level, class_slug, category, rules_summary, description)
        VALUES (:id, :name, :slug, :level, :class_slug, :category, :rules_summary, :description)
    """, row)
    conn.commit()


def upsert_feat(row: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO feats
        (id, name, slug, level, category, action_type, traits, prerequisites, class_slug, ancestry_slug, description)
        VALUES (:id, :name, :slug, :level, :category, :action_type, :traits, :prerequisites, :class_slug, :ancestry_slug, :description)
    """, row)
    conn.commit()


def upsert_spell(row: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO spells
        (id, name, slug, rank, traditions, traits, action_cost, range, area, target, duration, defense, description)
        VALUES (:id, :name, :slug, :rank, :traditions, :traits, :action_cost, :range, :area, :target, :duration, :defense, :description)
    """, row)
    conn.commit()


def upsert_equipment(row: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO equipment
        (id, name, slug, item_type, category, price_cp, bulk, traits, damage, ac_bonus, dex_cap, description)
        VALUES (:id, :name, :slug, :item_type, :category, :price_cp, :bulk, :traits, :damage, :ac_bonus, :dex_cap, :description)
    """, row)
    conn.commit()


def bulk_insert(table: str, rows: list[dict[str, Any]]) -> int:
    """Batch insert for performance during ingestion."""
    if not rows:
        return 0
    conn = get_conn()
    cols = list(rows[0].keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    col_names = ", ".join(cols)
    conn.executemany(
        f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Query helpers (used by AI tools)
# ---------------------------------------------------------------------------

def _rows_to_dicts(rows: list) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def _parse_json_fields(row: dict, *fields: str) -> dict:
    """Parse JSON string fields back to Python objects."""
    for f in fields:
        if f in row and isinstance(row[f], str):
            try:
                row[f] = json.loads(row[f])
            except (json.JSONDecodeError, TypeError):
                pass
    return row


def search_ancestries(query: str = "") -> list[dict]:
    conn = get_conn()
    if query:
        rows = conn.execute(
            "SELECT * FROM ancestries WHERE name LIKE ? OR slug LIKE ? OR name_cn LIKE ? ORDER BY name",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM ancestries ORDER BY name").fetchall()
    return [_parse_json_fields(dict(r), "boosts", "flaws", "languages", "traits") for r in rows]


def search_heritages(ancestry_slug: str = "", include_versatile: bool = True) -> list[dict]:
    conn = get_conn()
    if ancestry_slug:
        if include_versatile:
            rows = conn.execute(
                "SELECT * FROM heritages WHERE ancestry_slug = ? OR ancestry_slug IS NULL ORDER BY name",
                (ancestry_slug,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM heritages WHERE ancestry_slug = ? ORDER BY name",
                (ancestry_slug,),
            ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM heritages ORDER BY name").fetchall()
    return [_parse_json_fields(dict(r), "traits") for r in rows]


def search_backgrounds(query: str = "", skill: str = "") -> list[dict]:
    conn = get_conn()
    conditions = []
    params: list = []
    if query:
        conditions.append("(name LIKE ? OR slug LIKE ? OR name_cn LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
    if skill:
        conditions.append("trained_skills LIKE ?")
        params.append(f"%{skill}%")
    where = " AND ".join(conditions) if conditions else "1=1"
    rows = conn.execute(f"SELECT * FROM backgrounds WHERE {where} ORDER BY name", params).fetchall()
    return [_parse_json_fields(dict(r), "boosts", "trained_skills", "lore", "granted_feat_names") for r in rows]


def search_classes(query: str = "") -> list[dict]:
    conn = get_conn()
    if query:
        rows = conn.execute(
            "SELECT * FROM classes WHERE name LIKE ? OR slug LIKE ? OR name_cn LIKE ? ORDER BY name",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM classes ORDER BY name").fetchall()
    result = []
    for r in rows:
        d = _parse_json_fields(
            dict(r), "key_ability", "saves", "attacks", "defenses",
            "trained_skills", "ancestry_feat_levels", "class_feat_levels",
            "general_feat_levels", "skill_feat_levels", "skill_increase_levels",
            "class_features",
        )
        result.append(d)
    return result


def search_feats(
    category: str = "",
    level_max: int = 0,
    class_slug: str = "",
    ancestry_slug: str = "",
    query: str = "",
    limit: int = 30,
) -> list[dict]:
    conn = get_conn()
    conditions = []
    params: list = []
    if category:
        conditions.append("category = ?")
        params.append(category)
    if level_max > 0:
        conditions.append("level <= ?")
        params.append(level_max)
    if class_slug:
        conditions.append("class_slug = ?")
        params.append(class_slug)
    if ancestry_slug:
        conditions.append("ancestry_slug = ?")
        params.append(ancestry_slug)
    if query:
        conditions.append("(name LIKE ? OR slug LIKE ? OR name_cn LIKE ? OR description LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
    where = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)
    rows = conn.execute(
        f"SELECT * FROM feats WHERE {where} ORDER BY level, name LIMIT ?", params,
    ).fetchall()
    return [_parse_json_fields(dict(r), "traits", "prerequisites") for r in rows]


def get_feat_by_name(name: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM feats WHERE name = ? OR slug = ? LIMIT 1",
        (name, name),
    ).fetchone()
    if row:
        return _parse_json_fields(dict(row), "traits", "prerequisites")
    return None


def search_spells(
    tradition: str = "",
    rank_max: int = 0,
    query: str = "",
    limit: int = 30,
) -> list[dict]:
    conn = get_conn()
    conditions = []
    params: list = []
    if tradition:
        conditions.append("traditions LIKE ?")
        params.append(f'%"{tradition}"%')
    if rank_max > 0:
        conditions.append("rank <= ?")
        params.append(rank_max)
    if query:
        conditions.append("(name LIKE ? OR slug LIKE ? OR name_cn LIKE ? OR description LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
    where = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)
    rows = conn.execute(
        f"SELECT * FROM spells WHERE {where} ORDER BY rank, name LIMIT ?", params,
    ).fetchall()
    return [_parse_json_fields(dict(r), "traditions", "traits") for r in rows]


def search_equipment(
    item_type: str = "",
    category: str = "",
    query: str = "",
    limit: int = 30,
) -> list[dict]:
    conn = get_conn()
    conditions = []
    params: list = []
    if item_type:
        conditions.append("item_type = ?")
        params.append(item_type)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if query:
        conditions.append("(name LIKE ? OR slug LIKE ? OR name_cn LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
    where = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)
    rows = conn.execute(
        f"SELECT * FROM equipment WHERE {where} ORDER BY name LIMIT ?", params,
    ).fetchall()
    return [_parse_json_fields(dict(r), "traits") for r in rows]


def get_class_by_slug(slug: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM classes WHERE slug = ?", (slug,)).fetchone()
    if row:
        return _parse_json_fields(
            dict(row), "key_ability", "saves", "attacks", "defenses",
            "trained_skills", "ancestry_feat_levels", "class_feat_levels",
            "general_feat_levels", "skill_feat_levels", "skill_increase_levels",
            "class_features",
        )
    return None


def get_ancestry_by_slug(slug: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM ancestries WHERE slug = ?", (slug,)).fetchone()
    if row:
        return _parse_json_fields(dict(row), "boosts", "flaws", "languages", "traits")
    return None


def get_background_by_slug(slug: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM backgrounds WHERE slug = ?", (slug,)).fetchone()
    if row:
        return _parse_json_fields(dict(row), "boosts", "trained_skills", "lore", "granted_feat_names")
    return None


def get_stats() -> dict[str, int]:
    conn = get_conn()
    tables = ["ancestries", "heritages", "backgrounds", "classes", "class_features", "feats", "spells", "equipment"]
    stats = {}
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        stats[t] = count
    return stats
