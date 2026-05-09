"""Parse Markdown documents into section-based text chunks."""

from __future__ import annotations

import re
from pathlib import Path


def parse_markdown(filepath: str) -> list[dict[str, str]]:
    """Split a Markdown file by headings and return text chunks."""
    path = Path(filepath)
    text = path.read_text(encoding="utf-8")

    # Split on headings (any level)
    sections: list[dict[str, str]] = []
    parts = re.split(r"(^#{1,6}\s+.+$)", text, flags=re.MULTILINE)

    current_heading = path.stem
    current_body = ""

    for part in parts:
        heading_match = re.match(r"^#{1,6}\s+(.+)$", part)
        if heading_match:
            if current_body.strip():
                sections.append({
                    "id": f"md::{path.stem}::{current_heading}",
                    "text": f"## {current_heading}\n\n{current_body.strip()}",
                    "metadata_label": "markdown",
                    "metadata_key": path.stem,
                    "metadata_name": current_heading,
                })
            current_heading = heading_match.group(1).strip()
            current_body = ""
        else:
            current_body += part

    if current_body.strip():
        sections.append({
            "id": f"md::{path.stem}::{current_heading}",
            "text": f"## {current_heading}\n\n{current_body.strip()}",
            "metadata_label": "markdown",
            "metadata_key": path.stem,
            "metadata_name": current_heading,
        })

    # If the document has no headings, treat it as one chunk
    if not sections and text.strip():
        sections.append({
            "id": f"md::{path.stem}::full",
            "text": text.strip(),
            "metadata_label": "markdown",
            "metadata_key": path.stem,
            "metadata_name": path.stem,
        })

    return sections
