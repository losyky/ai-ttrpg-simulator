"""Universal file knowledge base — stores uploaded documents as readable
chunks that AI agents can retrieve on demand.

Unlike the structured rule database (ruledb.py) which handles FVTT
compendium data, this module handles *any* uploaded file (scenarios,
modules, reference PDFs, journal entries, etc.) and stores them as
retrievable text chunks in SQLite.

The design philosophy: don't try to "understand" the document structure.
Just store the raw text in searchable chunks so agents can READ them
when needed, like flipping through a reference book.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.event_log import log_event

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id      TEXT PRIMARY KEY,
            filename    TEXT NOT NULL,
            doc_type    TEXT NOT NULL DEFAULT '',
            title       TEXT NOT NULL DEFAULT '',
            chunk_count INTEGER NOT NULL DEFAULT 0,
            system_id   TEXT NOT NULL DEFAULT 'pf2e',
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS doc_chunks (
            chunk_id    TEXT PRIMARY KEY,
            doc_id      TEXT NOT NULL,
            section     TEXT NOT NULL DEFAULT '',
            content     TEXT NOT NULL DEFAULT '',
            chunk_index INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_doc ON doc_chunks(doc_id);
    """)
    conn.commit()

    # Migrate: add system_id column if missing (existing DBs)
    try:
        conn.execute("SELECT system_id FROM documents LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE documents ADD COLUMN system_id TEXT NOT NULL DEFAULT 'pf2e'")
        conn.commit()

    # FTS table: verify integrity, drop & recreate if malformed
    try:
        conn.execute("SELECT count(*) FROM chunks_fts")
    except sqlite3.DatabaseError:
        conn.execute("DROP TABLE IF EXISTS chunks_fts")
    finally:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                section, content,
                content=doc_chunks,
                content_rowid=rowid
            )
        """)
        conn.commit()


def _strip_html(html: str) -> str:
    text = re.sub(r"<img[^>]*>", "", html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<hr\s*/?>", "\n---\n", text)
    text = re.sub(r"</?(?:p|div|section|aside|h[1-6]|table|thead|tbody|tr|td|th|ul|ol|li)(?:\s[^>]*)?>", "\n", text)
    text = re.sub(r"@UUID\[.*?\]\{(.*?)\}", r"\1", text)
    text = re.sub(r"@UUID\[.*?\]", "", text)
    text = re.sub(r"@(?:Check|Damage|Template|Embed|Localize)\[.*?\]", "", text)
    text = re.sub(r"\[\[/.*?\]\]\{(.*?)\}", r"\1", text)
    text = re.sub(r"\[\[/.*?\]\]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Ingest functions ──

def ingest_fvtt_journal(filepath: str, doc_id: str, filename: str, system_id: str = "pf2e") -> int:
    """Parse a FVTT JournalEntry JSON (pages[] structure)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("name", filename)
    pages = data.get("pages", [])

    if not pages:
        # Fallback: try entries{} format (compendium journals)
        entries = data.get("entries", {})
        if entries:
            return _ingest_entries_journal(entries, data.get("label", title), doc_id, filename, system_id)
        return 0

    conn = _get_conn()
    chunks: list[tuple] = []

    for i, page in enumerate(pages):
        page_name = page.get("name", f"Page {i+1}")
        text_obj = page.get("text", {})
        raw_content = text_obj.get("content", "") if isinstance(text_obj, dict) else ""

        if not raw_content:
            continue

        clean = _strip_html(raw_content)
        if not clean.strip():
            continue

        # Split long pages into ~2000 char chunks
        sub_chunks = _split_text(clean, max_chars=2000)
        for j, chunk_text in enumerate(sub_chunks):
            cid = f"{doc_id}::p{i}::c{j}"
            section = f"{title} > {page_name}" + (f" (part {j+1})" if len(sub_chunks) > 1 else "")
            chunks.append((cid, doc_id, section, chunk_text, len(chunks)))

    if chunks:
        conn.execute(
            "INSERT OR REPLACE INTO documents (doc_id, filename, doc_type, title, chunk_count, system_id) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, filename, "fvtt_journal", title, len(chunks), system_id),
        )
        conn.executemany(
            "INSERT OR REPLACE INTO doc_chunks (chunk_id, doc_id, section, content, chunk_index) VALUES (?, ?, ?, ?, ?)",
            chunks,
        )
        conn.commit()
        _rebuild_chunks_fts(conn)

    return len(chunks)


def _ingest_entries_journal(entries: dict, label: str, doc_id: str, filename: str, system_id: str = "pf2e") -> int:
    """Handle entries{} format (compendium-style journals with pages sub-objects)."""
    conn = _get_conn()
    chunks: list[tuple] = []

    for key, entry in entries.items():
        if not isinstance(entry, dict):
            continue

        entry_name = entry.get("name", key)

        # entries can have pages{} (nested) or direct text/description
        pages = entry.get("pages", {})
        if pages and isinstance(pages, dict):
            for pkey, page in pages.items():
                if not isinstance(page, dict):
                    continue
                page_name = page.get("name", pkey)
                raw = page.get("text", "")
                clean = _strip_html(raw)
                if clean.strip():
                    sub_chunks = _split_text(clean, max_chars=2000)
                    for j, ct in enumerate(sub_chunks):
                        cid = f"{doc_id}::{key}::{pkey}::c{j}"
                        section = f"{label} > {entry_name} > {page_name}"
                        chunks.append((cid, doc_id, section, ct, len(chunks)))
        else:
            raw = entry.get("description", entry.get("text", ""))
            clean = _strip_html(raw)
            if clean.strip():
                cid = f"{doc_id}::{key}"
                chunks.append((cid, doc_id, f"{label} > {entry_name}", clean[:3000], len(chunks)))

    if chunks:
        conn.execute(
            "INSERT OR REPLACE INTO documents (doc_id, filename, doc_type, title, chunk_count, system_id) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, filename, "fvtt_journal", label, len(chunks), system_id),
        )
        conn.executemany(
            "INSERT OR REPLACE INTO doc_chunks (chunk_id, doc_id, section, content, chunk_index) VALUES (?, ?, ?, ?, ?)",
            chunks,
        )
        conn.commit()
        _rebuild_chunks_fts(conn)

    log_event("data", "ingest_journal", detail=f"{filename}: {len(chunks)} chunks",
              data={"doc_id": doc_id, "chunk_count": len(chunks)})
    return len(chunks)


def ingest_text_document(filepath: str, doc_id: str, filename: str, system_id: str = "pf2e") -> int:
    """Ingest a plain text or markdown file."""
    text = Path(filepath).read_text(encoding="utf-8")
    if not text.strip():
        return 0

    title = Path(filename).stem
    sub_chunks = _split_text(text, max_chars=2000)
    conn = _get_conn()

    chunks = [
        (f"{doc_id}::c{i}", doc_id, f"{title} (part {i+1})" if len(sub_chunks) > 1 else title, ct, i)
        for i, ct in enumerate(sub_chunks)
    ]

    conn.execute(
        "INSERT OR REPLACE INTO documents (doc_id, filename, doc_type, title, chunk_count, system_id) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, filename, "text", title, len(chunks), system_id),
    )
    conn.executemany(
        "INSERT OR REPLACE INTO doc_chunks (chunk_id, doc_id, section, content, chunk_index) VALUES (?, ?, ?, ?, ?)",
        chunks,
    )
    conn.commit()
    _rebuild_chunks_fts(conn)
    log_event("data", "ingest_text", detail=f"{filename}: {len(chunks)} chunks",
              data={"doc_id": doc_id, "chunk_count": len(chunks)})
    return len(chunks)


def ingest_text_string(text: str, doc_id: str, title: str, system_id: str = "pf2e", doc_type: str = "creator") -> int:
    """Ingest a plain text string directly into the knowledge base (no file needed)."""
    if not text.strip():
        return 0

    sub_chunks = _split_text(text, max_chars=2000)
    conn = _get_conn()
    filename = f"{title}.md"

    chunks = [
        (f"{doc_id}::c{i}", doc_id, f"{title} (part {i+1})" if len(sub_chunks) > 1 else title, ct, i)
        for i, ct in enumerate(sub_chunks)
    ]

    conn.execute(
        "INSERT OR REPLACE INTO documents (doc_id, filename, doc_type, title, chunk_count, system_id) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, filename, doc_type, title, len(chunks), system_id),
    )
    conn.executemany(
        "INSERT OR REPLACE INTO doc_chunks (chunk_id, doc_id, section, content, chunk_index) VALUES (?, ?, ?, ?, ?)",
        chunks,
    )
    conn.commit()
    _rebuild_chunks_fts(conn)
    log_event("data", "ingest_string", detail=f"{title}: {len(chunks)} chunks",
              data={"doc_id": doc_id, "chunk_count": len(chunks)})
    return len(chunks)


def ingest_pdf_document(filepath: str, doc_id: str, filename: str, system_id: str = "pf2e") -> int:
    """Ingest a PDF file."""
    from app.parsers.pdf_parser import parse_pdf
    raw_chunks = parse_pdf(filepath, max_chars_per_chunk=2000)
    if not raw_chunks:
        return 0

    title = Path(filename).stem
    conn = _get_conn()

    chunks = [
        (f"{doc_id}::c{i}", doc_id, c.get("metadata_name", f"{title} part {i+1}"), c["text"], i)
        for i, c in enumerate(raw_chunks)
    ]

    conn.execute(
        "INSERT OR REPLACE INTO documents (doc_id, filename, doc_type, title, chunk_count, system_id) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, filename, "pdf", title, len(chunks), system_id),
    )
    conn.executemany(
        "INSERT OR REPLACE INTO doc_chunks (chunk_id, doc_id, section, content, chunk_index) VALUES (?, ?, ?, ?, ?)",
        chunks,
    )
    conn.commit()
    _rebuild_chunks_fts(conn)
    return len(chunks)


def _split_text(text: str, max_chars: int = 2000) -> list[str]:
    """Split text into chunks, preferring paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = para + "\n\n"
        else:
            current += para + "\n\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text[:max_chars]]


def _rebuild_chunks_fts(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("DELETE FROM chunks_fts")
    except sqlite3.DatabaseError:
        conn.execute("DROP TABLE IF EXISTS chunks_fts")
        conn.execute("""
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                section, content,
                content=doc_chunks,
                content_rowid=rowid
            )
        """)
    conn.execute("""
        INSERT INTO chunks_fts(rowid, section, content)
        SELECT rowid, section, content FROM doc_chunks
    """)
    conn.commit()


# ── Query API (for the AI reading tool) ──

def list_documents(system_id: str | None = None, doc_ids: list[str] | None = None) -> list[dict]:
    conn = _get_conn()
    conditions = []
    params: list = []
    if system_id:
        conditions.append("system_id = ?")
        params.append(system_id)
    if doc_ids is not None:
        if not doc_ids:
            return []
        placeholders = ",".join("?" for _ in doc_ids)
        conditions.append(f"doc_id IN ({placeholders})")
        params.extend(doc_ids)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = conn.execute(f"SELECT * FROM documents{where} ORDER BY created_at DESC", params).fetchall()
    return [dict(r) for r in rows]


def get_document_toc(doc_id: str) -> list[dict]:
    """Get the table of contents (section list) for a document."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT chunk_id, section, chunk_index, LENGTH(content) as char_count FROM doc_chunks WHERE doc_id = ? ORDER BY chunk_index",
        (doc_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def read_chunk(chunk_id: str) -> dict | None:
    """Read a specific chunk by ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM doc_chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
    return dict(row) if row else None


def read_document_section(doc_id: str, start: int = 0, count: int = 3) -> list[dict]:
    """Read consecutive chunks from a document."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM doc_chunks WHERE doc_id = ? ORDER BY chunk_index LIMIT ? OFFSET ?",
        (doc_id, count, start),
    ).fetchall()
    return [dict(r) for r in rows]


def search_documents(query: str, doc_id: str | None = None, limit: int = 5, system_id: str | None = None, doc_ids: list[str] | None = None) -> list[dict]:
    """Full-text search across uploaded documents.

    Filters:
        doc_id: scope to a single document
        system_id: scope to a game system
        doc_ids: scope to a specific set of enabled documents (None = all)
    """
    conn = _get_conn()
    if doc_ids is not None and not doc_ids:
        return []

    rows = _fts_search(conn, query, doc_id, limit, system_id, doc_ids)

    if not rows:
        rows = _like_search(conn, query, doc_id, limit, system_id, doc_ids)

    return [dict(r) for r in rows]


def _doc_ids_clause(doc_ids: list[str] | None, params: list, table_alias: str = "dc") -> str:
    if doc_ids is None:
        return ""
    placeholders = ",".join("?" for _ in doc_ids)
    params.extend(doc_ids)
    return f" AND {table_alias}.doc_id IN ({placeholders})"


def _fts_search(conn: sqlite3.Connection, query: str, doc_id: str | None, limit: int, system_id: str | None = None, doc_ids: list[str] | None = None) -> list:
    fts_query = query.replace('"', '""')
    try:
        base = """
            SELECT dc.* FROM chunks_fts fts
            JOIN doc_chunks dc ON dc.rowid = fts.rowid
            JOIN documents d ON d.doc_id = dc.doc_id
            WHERE chunks_fts MATCH ?
        """
        params: list = [fts_query]
        if doc_id:
            base += " AND dc.doc_id = ?"
            params.append(doc_id)
        if system_id:
            base += " AND d.system_id = ?"
            params.append(system_id)
        base += _doc_ids_clause(doc_ids, params)
        base += " ORDER BY rank LIMIT ?"
        params.append(limit)
        return conn.execute(base, params).fetchall()
    except Exception:
        return []


def _like_search(conn: sqlite3.Connection, query: str, doc_id: str | None, limit: int, system_id: str | None = None, doc_ids: list[str] | None = None) -> list:
    """LIKE-based fallback: search for each significant token independently."""
    tokens = [t for t in query.strip() if t.strip()]
    if not tokens:
        return []

    like_clauses = []
    params: list = []
    for tok in tokens:
        if len(tok) < 2 and tok.isascii():
            continue
        like_clauses.append("(dc.content LIKE ? OR dc.section LIKE ?)")
        params.extend([f"%{tok}%", f"%{tok}%"])

    like_clauses.insert(0, "(dc.content LIKE ? OR dc.section LIKE ?)")
    params = [f"%{query}%", f"%{query}%"] + params

    if not like_clauses:
        return []

    where = " OR ".join(like_clauses)
    base_conditions = []
    extra_params: list = []
    if doc_id:
        base_conditions.append("dc.doc_id = ?")
        extra_params.append(doc_id)
    if system_id:
        base_conditions.append("d.system_id = ?")
        extra_params.append(system_id)
    if doc_ids is not None:
        placeholders = ",".join("?" for _ in doc_ids)
        base_conditions.append(f"dc.doc_id IN ({placeholders})")
        extra_params.extend(doc_ids)

    sql = "SELECT dc.* FROM doc_chunks dc JOIN documents d ON d.doc_id = dc.doc_id WHERE"
    if base_conditions:
        sql += " " + " AND ".join(base_conditions) + " AND "
    sql += f" ({where}) LIMIT ?"

    return conn.execute(sql, extra_params + params + [limit]).fetchall()


def get_opening_chunks(limit: int = 5, system_id: str | None = None, doc_ids: list[str] | None = None) -> list[dict]:
    """Get the opening sections of uploaded documents.

    Filters:
        system_id: scope to a game system
        doc_ids: scope to a specific set of enabled documents (None = all)
    """
    if doc_ids is not None and not doc_ids:
        return []
    conn = _get_conn()
    conditions = ["dc.chunk_index <= 2"]
    params: list = []
    if system_id:
        conditions.append("d.system_id = ?")
        params.append(system_id)
    if doc_ids is not None:
        placeholders = ",".join("?" for _ in doc_ids)
        conditions.append(f"dc.doc_id IN ({placeholders})")
        params.extend(doc_ids)
    where = " AND ".join(conditions)
    params.append(limit)
    rows = conn.execute(f"""
        SELECT dc.*, d.title as doc_title FROM doc_chunks dc
        JOIN documents d ON d.doc_id = dc.doc_id
        WHERE {where}
        ORDER BY d.created_at DESC, dc.chunk_index ASC
        LIMIT ?
    """, params).fetchall()
    return [dict(r) for r in rows]


def delete_document(doc_id: str) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM doc_chunks WHERE doc_id = ?", (doc_id,))
    result = conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
    conn.commit()
    if result.rowcount > 0:
        _rebuild_chunks_fts(conn)
        return True
    return False
