"""Parse PDF documents into text chunks."""

from __future__ import annotations

from pathlib import Path

import pdfplumber


def parse_pdf(filepath: str, max_chars_per_chunk: int = 2000) -> list[dict[str, str]]:
    """Extract text from a PDF and split into roughly even chunks."""
    path = Path(filepath)
    full_text = ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            full_text += page_text + "\n\n"

    full_text = full_text.strip()
    if not full_text:
        return []

    # Split into paragraphs, then group into chunks
    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    chunks: list[dict[str, str]] = []
    current = ""
    chunk_idx = 0

    for para in paragraphs:
        if len(current) + len(para) > max_chars_per_chunk and current:
            chunks.append({
                "id": f"pdf::{path.stem}::{chunk_idx}",
                "text": current.strip(),
                "metadata_label": "pdf",
                "metadata_key": path.stem,
                "metadata_name": f"{path.stem} (part {chunk_idx + 1})",
            })
            chunk_idx += 1
            current = para + "\n\n"
        else:
            current += para + "\n\n"

    if current.strip():
        chunks.append({
            "id": f"pdf::{path.stem}::{chunk_idx}",
            "text": current.strip(),
            "metadata_label": "pdf",
            "metadata_key": path.stem,
            "metadata_name": f"{path.stem} (part {chunk_idx + 1})",
        })

    return chunks
