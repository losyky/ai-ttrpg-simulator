"""ChromaDB-backed vector store for rule/module lookups."""

from __future__ import annotations

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

_client: chromadb.ClientAPI | None = None
COLLECTION_NAME = "pf2e_rules"  # default, overridable via get_active_collection_name()


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.Client(
            ChromaSettings(
                persist_directory=settings.chroma_dir,
                anonymized_telemetry=False,
                is_persistent=True,
            )
        )
    return _client


def get_collection() -> chromadb.Collection:
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(chunks: list[dict[str, str]]) -> int:
    """Add parsed text chunks to the vector store. Returns count added."""
    if not chunks:
        return 0

    coll = get_collection()
    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas: list[dict[str, Any]] = [
        {
            "label": c.get("metadata_label", ""),
            "key": c.get("metadata_key", ""),
            "name": c.get("metadata_name", ""),
        }
        for c in chunks
    ]

    coll.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def search(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Semantic search across all ingested rules and modules."""
    coll = get_collection()
    if coll.count() == 0:
        return []

    results = coll.query(query_texts=[query], n_results=n_results)

    hits: list[dict[str, Any]] = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],  # type: ignore
            results["distances"][0],  # type: ignore
        ):
            hits.append({"text": doc, "metadata": meta, "distance": dist})
    return hits
