"""Web search tool — scoped to Portuguese official sources.

EN:
    Async Tavily client with `include_domains` filtered by question category
    (`_DOMAIN_HINTS`). This biases results toward ACT, DRE, Finanças, Segurança
    Social, etc., reducing blog spam.

    Without `TAVILY_API_KEY`, returns `ok=False` — the agent must not invent
    URLs. On HTTP errors, logs and returns the exception string in `error`.

PT:
    Cliente Tavily assíncrono com `include_domains` filtrado pela categoria
    (`_DOMAIN_HINTS`), enviesando para ACT, DRE, Finanças, Seg. Social, etc.

    Sem `TAVILY_API_KEY`, devolve `ok=False` — o agente não deve inventar URLs.
    Em erro HTTP, regista e devolve a mensagem em `error`.
"""
from __future__ import annotations

from typing import Any

from app.agent.state import Source
from app.agent.tools import ToolResult
from app.config import settings
from app.logging_config import logger


OFFICIAL_DOMAINS = [
    "portal.act.gov.pt",
    "act.gov.pt",
    "info.portaldasfinancas.gov.pt",
    "portaldasfinancas.gov.pt",
    "diariodarepublica.pt",
    "dre.pt",
    "cite.gov.pt",
    "seg-social.pt",
    "www.seg-social.pt",
]


_DOMAIN_HINTS: dict[str, list[str]] = {
    "tax": ["info.portaldasfinancas.gov.pt", "portaldasfinancas.gov.pt"],
    # Lei 110/2009 + páginas SS (briefing: código contributivo + TSU).
    "social_security": [
        "diariodarepublica.pt",
        "dre.pt",
        "seg-social.pt",
        "www.seg-social.pt",
    ],
    "labor_code": ["portal.act.gov.pt", "act.gov.pt", "diariodarepublica.pt", "cite.gov.pt"],
    "edge_case": OFFICIAL_DOMAINS,
    # Subsídios/RMMG context — CT (ACT) + DRE + Finanças quando aplicável.
    "salary_calc": [
        "portal.act.gov.pt",
        "act.gov.pt",
        "info.portaldasfinancas.gov.pt",
        "portaldasfinancas.gov.pt",
        "diariodarepublica.pt",
        "dre.pt",
    ],
}


def _domain_of(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc.lower()
    except Exception:
        return ""


async def web_search(query: str, category: str = "edge_case", max_results: int = 5) -> ToolResult:
    if not settings.tavily_api_key:
        return ToolResult(
            ok=False,
            data=[],
            sources=[],
            summary="",
            error="TAVILY_API_KEY is not configured",
        )

    domains = _DOMAIN_HINTS.get(category, OFFICIAL_DOMAINS) or OFFICIAL_DOMAINS

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        result: dict[str, Any] = await client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=domains,
            include_answer=False,
            include_raw_content=False,
        )
    except Exception as exc:
        logger.exception("Tavily search failed: {}", exc)
        return ToolResult(ok=False, data=[], sources=[], summary="", error=str(exc))

    items = result.get("results", []) or []
    sources: list[Source] = []
    summary_lines: list[str] = []
    for it in items:
        url = it.get("url", "")
        title = (it.get("title") or "")[:200]
        snippet = (it.get("content") or "")[:600]
        score = float(it.get("score", 0.0) or 0.0)
        sources.append(
            Source(
                url=url,
                title=title,
                snippet=snippet,
                domain=_domain_of(url),
                score=score,
                source_type="web",
            )
        )
        summary_lines.append(f"- {title} ({_domain_of(url)})\n  {snippet[:200]}")

    return ToolResult(
        ok=True,
        data=items,
        sources=sources,
        summary="\n".join(summary_lines) if summary_lines else "No results.",
        error=None,
    )
