"""AI agent tool for reading uploaded reference materials.

Agents use these tools to browse and search the knowledge base —
uploaded modules, scenarios, journal entries, and other reference docs.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.services.knowledge_base import (
    list_documents,
    get_document_toc,
    read_document_section,
    search_documents,
)


@tool
def list_materials(hint: str = "") -> str:
    """List all uploaded reference materials available for reading.

    Returns a list of documents with their IDs and titles. Use the doc_id
    to browse or search within a specific document.
    """
    docs = list_documents()
    if not docs:
        return "当前没有已上传的参考资料。"

    lines = ["已上传的参考资料："]
    for d in docs:
        lines.append(f"  - [{d['doc_id']}] {d['title']} ({d['doc_type']}, {d['chunk_count']} 个片段)")
    return "\n".join(lines)


@tool
def browse_material(doc_id: str, start: int = 0, count: int = 3) -> str:
    """Browse a specific uploaded document by reading its sections sequentially.

    Like flipping pages of a book — start from a section index and read
    a few consecutive sections.

    Args:
        doc_id: Document ID from list_materials.
        start: Starting section index (0-based).
        count: Number of sections to read (1-5).
    """
    count = min(max(count, 1), 5)
    chunks = read_document_section(doc_id, start=start, count=count)
    if not chunks:
        return f"未找到文档 {doc_id} 或已读完所有内容。"

    parts = []
    for c in chunks:
        parts.append(f"=== {c['section']} (index {c['chunk_index']}) ===\n{c['content']}")

    toc = get_document_toc(doc_id)
    total = len(toc) if toc else "?"
    parts.append(f"\n（共 {total} 个片段，当前显示 {chunks[0]['chunk_index']}-{chunks[-1]['chunk_index']}）")
    return "\n\n".join(parts)


@tool
def search_material(query: str, doc_id: str = "") -> str:
    """Search through uploaded reference materials for relevant content.

    Searches across all uploaded documents using full-text search.
    Optionally scope to a specific document.

    Args:
        query: What to search for, e.g. "葬礼竞技", "funeral games", "丁托尼昂".
        doc_id: Optional — limit search to a specific document.
    """
    results = search_documents(query, doc_id=doc_id or None, limit=5)
    if not results:
        return f"未在参考资料中找到与「{query}」相关的内容。"

    parts = [f"搜索「{query}」的结果："]
    for r in results:
        parts.append(f"--- {r['section']} ---\n{r['content'][:800]}")
    return "\n\n".join(parts)


def make_session_search_material(session_id: str):
    """Create a search_material tool scoped to a session's enabled documents."""
    from app.models.game_state import get_session as _get_session

    @tool
    def search_material_scoped(query: str, doc_id: str = "") -> str:
        """Search through uploaded reference materials for relevant content.

        Searches across enabled documents using full-text search.
        Optionally scope to a specific document.

        Args:
            query: What to search for, e.g. "葬礼竞技", "funeral games", "丁托尼昂".
            doc_id: Optional — limit search to a specific document.
        """
        session = _get_session(session_id)
        enabled = session.enabled_doc_ids if session else None
        results = search_documents(query, doc_id=doc_id or None, limit=5, doc_ids=enabled)
        if not results:
            return f"未在参考资料中找到与「{query}」相关的内容。"

        parts = [f"搜索「{query}」的结果："]
        for r in results:
            parts.append(f"--- {r['section']} ---\n{r['content'][:800]}")
        return "\n\n".join(parts)

    search_material_scoped.name = "search_material"
    return search_material_scoped
