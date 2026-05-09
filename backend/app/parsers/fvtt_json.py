"""Parse FVTT PF2e compendium JSON files into text chunks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _strip_html(html: str) -> str:
    """Rough HTML-to-text conversion for FVTT descriptions."""
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<hr\s*/?>", "\n---\n", text)
    text = re.sub(r"<p>", "", text)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"@UUID\[.*?\]\{(.*?)\}", r"\1", text)
    text = re.sub(r"@UUID\[.*?\]", "", text)
    text = re.sub(r"@Check\[.*?\]", "[检定]", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _flatten_entry(key: str, entry: dict[str, Any], label: str) -> dict[str, str]:
    """Turn a single compendium entry into a flat text chunk."""
    name = entry.get("name", key)
    desc = _strip_html(entry.get("description", ""))

    parts = [f"【{label}】{name}"]

    if prereqs := entry.get("prerequisites"):
        req_text = ", ".join(p.get("value", "") for p in prereqs)
        parts.append(f"前置条件: {req_text}")

    if desc:
        parts.append(desc)

    return {
        "id": f"{label}::{key}",
        "text": "\n".join(parts),
        "metadata_label": label,
        "metadata_key": key,
        "metadata_name": name,
    }


def parse_fvtt_json(filepath: str) -> list[dict[str, str]]:
    """Parse a FVTT compendium JSON and return a list of text chunk dicts."""
    path = Path(filepath)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    label = data.get("label", path.stem)
    entries = data.get("entries", {})

    chunks: list[dict[str, str]] = []
    for key, entry in entries.items():
        if isinstance(entry, dict) and ("description" in entry or "name" in entry):
            chunks.append(_flatten_entry(key, entry, label))

    return chunks
