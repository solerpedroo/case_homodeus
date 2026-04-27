"""Semantic search over the Código do Trabalho vector index.

EN:
    Blocking Chroma query wrapped by `asyncio.to_thread` from the agent. Each
    hit becomes a `Source` with title "Código do Trabalho — Artigo N.º". Empty
    index: `ok=True` with message to run `python -m app.retrieval.indexer`.

PT:
    Consulta Chroma bloqueante, invocada via `asyncio.to_thread`. Cada hit vira
    `Source` com título "Código do Trabalho — Artigo N.º". Índice vazio: pede
    para correr o indexer.
"""
from __future__ import annotations

from app.agent.state import Source
from app.agent.tools import ToolResult
from app.retrieval.vector_store import vector_store


def search_labor_code(query: str, k: int = 5) -> ToolResult:
    try:
        hits = vector_store.query(query, k=k)
    except Exception as exc:
        return ToolResult(ok=False, data=[], sources=[], summary="", error=str(exc))

    if not hits:
        return ToolResult(
            ok=True,
            data=[],
            sources=[],
            summary="(Índice vazio. Execute python -m app.retrieval.indexer.)",
            error=None,
        )

    sources: list[Source] = []
    summary_lines: list[str] = []
    for h in hits:
        meta = h.get("metadata", {}) or {}
        article = meta.get("article", "?")
        url = meta.get("url", "")
        text = h.get("text", "")
        title = f"Código do Trabalho — Artigo {article}.º"
        sources.append(
            Source(
                url=url,
                title=title,
                snippet=text[:400],
                domain="portal.act.gov.pt",
                score=h.get("score", 0.0),
                source_type="labor_code_index",
            )
        )
        summary_lines.append(f"[Art. {article}.º] {text[:300]}")

    return ToolResult(
        ok=True,
        data=hits,
        sources=sources,
        summary="\n\n".join(summary_lines),
        error=None,
    )
