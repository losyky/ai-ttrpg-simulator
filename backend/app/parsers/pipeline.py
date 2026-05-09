"""Document ingestion pipeline.

- FVTT compendium JSON (entries{} format) → structured SQLite database
- FVTT JournalEntry JSON (pages[] format) → knowledge base (readable chunks)
- Markdown / PDF / plain text → knowledge base
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.ruledb import ingest_compendium_file, rebuild_fts
from app.services.knowledge_base import (
    ingest_fvtt_journal,
    ingest_text_document,
    ingest_pdf_document,
)
from app.services.vectorstore import add_chunks
from app.parsers.markdown_parser import parse_markdown


def _is_fvtt_journal(filepath: str) -> bool:
    """Detect whether a JSON file is a JournalEntry (pages[]) vs compendium (entries{})."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return isinstance(data.get("pages"), list) and len(data.get("pages", [])) > 0
    except Exception:
        return False


def _is_fvtt_compendium(filepath: str) -> bool:
    """Detect whether a JSON file has the compendium entries{} format."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", {})
        return isinstance(entries, dict) and len(entries) > 0
    except Exception:
        return False


async def ingest_document(filepath: str, doc_type: str, doc_id: str, system_id: str = "pf2e") -> int:
    """Parse a document and ingest into the appropriate store.

    Returns the number of entries/chunks created.
    """
    filename = Path(filepath).name

    if doc_type == "fvtt_json":
        if _is_fvtt_journal(filepath):
            return ingest_fvtt_journal(filepath, doc_id, filename, system_id=system_id)
        if _is_fvtt_compendium(filepath):
            count = ingest_compendium_file(filepath)
            if count > 0:
                rebuild_fts()
            return count
        return ingest_text_document(filepath, doc_id, filename, system_id=system_id)

    if doc_type == "markdown":
        return ingest_text_document(filepath, doc_id, filename, system_id=system_id)

    if doc_type == "pdf":
        return ingest_pdf_document(filepath, doc_id, filename, system_id=system_id)

    if doc_type == "text":
        return ingest_text_document(filepath, doc_id, filename, system_id=system_id)

    return 0
