"""Structured SQLite database for PF2e compendium data.

The FVTT compendium is already a well-structured database. Blindly
vectorizing it throws away that structure. This module stores entries
in proper relational tables so agents can do precise lookups:
  - exact name match
  - filter by category (feat / spell / condition / action / equipment / creature)
  - filter by source book
  - full-text search on descriptions

The vector store is reserved as a semantic fallback only.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from app.config import settings

_DB_PATH = Path(settings.db_path)
_conn: sqlite3.Connection | None = None


def _strip_html(html: str) -> str:
    """Convert FVTT rich-text HTML to plain text for storage and FTS."""
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<hr\s*/?>", "\n---\n", text)
    text = re.sub(r"</?p>", "\n", text)
    text = re.sub(r"@UUID\[.*?\]\{(.*?)\}", r"\1", text)
    text = re.sub(r"@UUID\[.*?\]", "", text)
    text = re.sub(r"@Check\[.*?\]", "[检定]", text)
    text = re.sub(r"@Damage\[.*?\]", "[伤害]", text)
    text = re.sub(r"@Template\[.*?\]", "[模板]", text)
    text = re.sub(r"\[\[/r\s+.*?\]\]\{(.*?)\}", r"\1", text)
    text = re.sub(r"\[\[/.*?\]\]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS compendium_entries (
            id          TEXT PRIMARY KEY,
            key         TEXT NOT NULL,
            name_zh     TEXT NOT NULL DEFAULT '',
            name_en     TEXT NOT NULL DEFAULT '',
            category    TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL DEFAULT '',
            source_label TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            description_raw TEXT NOT NULL DEFAULT '',
            prerequisites TEXT NOT NULL DEFAULT '',
            duration    TEXT NOT NULL DEFAULT '',
            target      TEXT NOT NULL DEFAULT '',
            cost        TEXT NOT NULL DEFAULT '',
            extra_json  TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_category ON compendium_entries(category);
        CREATE INDEX IF NOT EXISTS idx_name_zh  ON compendium_entries(name_zh);
        CREATE INDEX IF NOT EXISTS idx_name_en  ON compendium_entries(name_en);

        -- Creature / NPC stats (bestiary)
        CREATE TABLE IF NOT EXISTS creatures (
            id          TEXT PRIMARY KEY,
            key         TEXT NOT NULL,
            name_zh     TEXT NOT NULL DEFAULT '',
            name_en     TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL DEFAULT '',
            public_notes TEXT NOT NULL DEFAULT '',
            items_json  TEXT NOT NULL DEFAULT '{}',
            extra_json  TEXT NOT NULL DEFAULT '{}'
        );
    """)
    conn.commit()

    # FTS table: verify integrity, drop & recreate if malformed
    try:
        conn.execute("SELECT count(*) FROM entries_fts")
    except sqlite3.DatabaseError:
        conn.execute("DROP TABLE IF EXISTS entries_fts")
    finally:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                name_zh, name_en, description, category,
                content=compendium_entries,
                content_rowid=rowid
            )
        """)
        conn.commit()


# ── Category detection from filename ──

_CATEGORY_MAP: list[tuple[str, str]] = [
    ("feats-srd", "feat"),
    ("feats", "feat"),
    ("spells-srd", "spell"),
    ("spells", "spell"),
    ("focus-spells", "spell"),
    ("equipment-srd", "equipment"),
    ("equipment", "equipment"),
    ("actionspf2e", "action"),
    ("actions", "action"),
    ("conditionitems", "condition"),
    ("ancestries", "ancestry"),
    ("ancestryfeatures", "ancestry_feature"),
    ("heritages", "heritage"),
    ("backgrounds", "background"),
    ("classes", "class"),
    ("classfeatures", "class_feature"),
    ("archetypes", "archetype"),
    ("deities", "deity"),
    ("domains", "domain"),
    ("familiar-abilities", "familiar"),
    ("hazards", "hazard"),
    ("vehicles", "vehicle"),
    ("bestiary", "creature"),
    ("monster-core", "creature"),
    ("npc-gallery", "creature"),
    ("effects", "effect"),
    ("features", "feature"),
    ("adventures", "adventure"),
    ("journals", "journal"),
]


def detect_category(filename: str) -> str:
    stem = Path(filename).stem.lower()
    for pattern, cat in _CATEGORY_MAP:
        if pattern in stem:
            return cat
    return "other"


# ── Bulk insert ──

import json


def _parse_name(entry: dict[str, Any], key: str) -> tuple[str, str]:
    """Split 'name' field like '灵活脚步 Agile Feet' into (zh, en)."""
    raw = entry.get("name", key)
    parts = re.split(r"\s+(?=[A-Z])", raw, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return raw, key


def ingest_compendium_file(filepath: str) -> int:
    """Parse a single FVTT compendium JSON into the SQLite database.

    Returns the number of entries inserted.
    """
    path = Path(filepath)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    label = data.get("label", path.stem)
    entries = data.get("entries", {})
    category = detect_category(path.name)
    conn = get_conn()

    is_creature = category == "creature"
    count = 0

    rows_main: list[tuple] = []
    rows_creature: list[tuple] = []

    for key, entry in entries.items():
        if not isinstance(entry, dict):
            continue

        name_zh, name_en = _parse_name(entry, key)
        entry_id = f"{path.stem}::{key}"

        if is_creature:
            public_notes = _strip_html(entry.get("publicNotes", entry.get("description", "")))
            items_json = json.dumps(entry.get("items", {}), ensure_ascii=False)
            extras = {k: v for k, v in entry.items()
                      if k not in ("name", "publicNotes", "description", "items", "data", "prototypeToken")}
            rows_creature.append((
                entry_id, key, name_zh, name_en, path.name,
                public_notes, items_json, json.dumps(extras, ensure_ascii=False),
            ))
        else:
            desc_raw = entry.get("description", "")
            desc = _strip_html(desc_raw)
            prereqs = ", ".join(
                p.get("value", "") for p in entry.get("prerequisites", [])
            ) if "prerequisites" in entry else ""
            duration = entry.get("duration", "")
            target = entry.get("target", "")
            cost = entry.get("cost", "")
            extras = {k: v for k, v in entry.items()
                      if k not in ("name", "description", "prerequisites",
                                   "duration", "target", "cost")}
            rows_main.append((
                entry_id, key, name_zh, name_en, category, path.name, label,
                desc, desc_raw, prereqs, duration, target, cost,
                json.dumps(extras, ensure_ascii=False),
            ))

        count += 1

    if rows_main:
        conn.executemany("""
            INSERT OR REPLACE INTO compendium_entries
            (id, key, name_zh, name_en, category, source_file, source_label,
             description, description_raw, prerequisites, duration, target, cost, extra_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_main)

    if rows_creature:
        conn.executemany("""
            INSERT OR REPLACE INTO creatures
            (id, key, name_zh, name_en, source_file,
             public_notes, items_json, extra_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_creature)

    conn.commit()
    return count


def rebuild_fts() -> None:
    """Rebuild the FTS5 full-text search index.

    Call this ONCE after all batch ingestion is done, not per-file.
    Handles corrupted FTS tables gracefully by dropping and recreating.
    """
    conn = get_conn()
    try:
        conn.execute("DELETE FROM entries_fts")
    except sqlite3.DatabaseError:
        conn.execute("DROP TABLE IF EXISTS entries_fts")
        conn.execute("""
            CREATE VIRTUAL TABLE entries_fts USING fts5(
                name_zh, name_en, description, category,
                content=compendium_entries,
                content_rowid=rowid
            )
        """)
    conn.execute("""
        INSERT INTO entries_fts(rowid, name_zh, name_en, description, category)
        SELECT rowid, name_zh, name_en, description, category
        FROM compendium_entries
    """)
    conn.commit()


# ── Query API ──

def lookup_by_name(name: str, category: str | None = None, limit: int = 5) -> list[dict]:
    """Exact or prefix match on name (zh or en)."""
    conn = get_conn()
    pattern = f"%{name}%"
    if category:
        rows = conn.execute(
            "SELECT * FROM compendium_entries WHERE category = ? AND (name_zh LIKE ? OR name_en LIKE ?) LIMIT ?",
            (category, pattern, pattern, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM compendium_entries WHERE name_zh LIKE ? OR name_en LIKE ? LIMIT ?",
            (pattern, pattern, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def lookup_creature(name: str, limit: int = 5) -> list[dict]:
    """Search creatures by name."""
    conn = get_conn()
    pattern = f"%{name}%"
    rows = conn.execute(
        "SELECT * FROM creatures WHERE name_zh LIKE ? OR name_en LIKE ? LIMIT ?",
        (pattern, pattern, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def fulltext_search(query: str, category: str | None = None, limit: int = 8) -> list[dict]:
    """Full-text search across names and descriptions."""
    conn = get_conn()
    fts_query = query.replace('"', '""')
    if category:
        rows = conn.execute("""
            SELECT ce.* FROM entries_fts fts
            JOIN compendium_entries ce ON ce.rowid = fts.rowid
            WHERE entries_fts MATCH ? AND ce.category = ?
            ORDER BY rank LIMIT ?
        """, (fts_query, category, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT ce.* FROM entries_fts fts
            JOIN compendium_entries ce ON ce.rowid = fts.rowid
            WHERE entries_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (fts_query, limit)).fetchall()
    return [dict(r) for r in rows]


def list_categories() -> list[dict]:
    """Return distinct categories and their counts."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM compendium_entries GROUP BY category ORDER BY cnt DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict[str, int]:
    """Return database statistics."""
    conn = get_conn()
    main_count = conn.execute("SELECT COUNT(*) FROM compendium_entries").fetchone()[0]
    creature_count = conn.execute("SELECT COUNT(*) FROM creatures").fetchone()[0]
    return {"entries": main_count, "creatures": creature_count, "total": main_count + creature_count}
