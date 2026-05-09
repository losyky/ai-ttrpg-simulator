"""Document upload, management and knowledge base API."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.models.schemas import DocumentInfo
from app.parsers.pipeline import ingest_document
from app.services import knowledge_base as kb
from app.services.event_log import log_event

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _detect_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".json":
        return "fvtt_json"
    if ext in (".md", ".markdown"):
        return "markdown"
    if ext == ".pdf":
        return "pdf"
    if ext in (".txt", ".text", ".log", ".csv"):
        return "text"
    raise HTTPException(400, f"Unsupported file type: {ext}")


@router.post("", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...), system_id: str | None = None):
    doc_type = _detect_type(file.filename or "unknown")
    doc_id = uuid.uuid4().hex[:10]
    dest_dir = Path(settings.upload_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{doc_id}_{file.filename}"
    content = await file.read()
    dest.write_bytes(content)

    if not system_id:
        from app.systems.registry import get_default_system
        system_id = get_default_system().system_id

    chunk_count = await ingest_document(str(dest), doc_type, doc_id, system_id=system_id)

    log_event("data", "document_uploaded", detail=f"{file.filename}: {chunk_count} chunks, type={doc_type}", data={"doc_id": doc_id, "filename": file.filename, "doc_type": doc_type, "chunk_count": chunk_count, "system_id": system_id})

    return DocumentInfo(
        doc_id=doc_id,
        filename=file.filename or "unknown",
        doc_type=doc_type,
        chunk_count=chunk_count,
    )


@router.get("")
async def list_documents(system_id: str | None = None):
    """List uploaded documents, optionally filtered by system_id."""
    return kb.list_documents(system_id=system_id)


@router.get("/{doc_id}/toc")
async def get_document_toc(doc_id: str):
    toc = kb.get_document_toc(doc_id)
    if not toc:
        raise HTTPException(404, "Document not found or has no chunks")
    return toc


@router.get("/{doc_id}/read")
async def read_document(
    doc_id: str,
    start: int = Query(0, ge=0),
    count: int = Query(3, ge=1, le=20),
):
    chunks = kb.read_document_section(doc_id, start=start, count=count)
    if not chunks:
        raise HTTPException(404, "No chunks found")
    return chunks


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    doc_id: str | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
    system_id: str | None = Query(None),
):
    """Full-text search across uploaded documents, optionally filtered by system_id."""
    return kb.search_documents(q, doc_id=doc_id, limit=limit, system_id=system_id)


class IngestTextRequest(BaseModel):
    title: str
    content: str
    system_id: str | None = None
    doc_type: str = "creator"


@router.post("/ingest-text")
async def ingest_text(req: IngestTextRequest):
    """Ingest raw text/markdown content directly into the knowledge base."""
    if not req.content.strip():
        raise HTTPException(400, "Content is empty")

    system_id = req.system_id
    if not system_id:
        from app.systems.registry import get_default_system
        system_id = get_default_system().system_id

    doc_id = uuid.uuid4().hex[:10]
    chunk_count = kb.ingest_text_string(
        text=req.content,
        doc_id=doc_id,
        title=req.title,
        system_id=system_id,
        doc_type=req.doc_type,
    )

    log_event("data", "text_ingested", detail=f"{req.title}: {chunk_count} chunks",
              data={"doc_id": doc_id, "title": req.title, "system_id": system_id})

    return DocumentInfo(
        doc_id=doc_id,
        filename=f"{req.title}.md",
        doc_type=req.doc_type,
        chunk_count=chunk_count,
    )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    ok = kb.delete_document(doc_id)
    if not ok:
        raise HTTPException(404, "Document not found")
    log_event("data", "document_deleted", detail=f"doc_id={doc_id}")
    return {"status": "deleted", "doc_id": doc_id}
