"""Fetch and parse a URL into clean text.

EN:
    `fetch_and_parse` is the second hop after `search_web`: given an official
    URL, download HTML, whitelist the host against `_ALLOWED`, strip scripts /
    nav / footer via BeautifulSoup, and return up to `_MAX_CHARS` of main text.
    A `Source` row is always attached so the answer can cite the exact page.

    Non-HTML content types fail fast — we don't parse PDFs here (CT PDF is
    indexed offline by `indexer.py`).

PT:
    `fetch_and_parse` é o segundo salto depois de `search_web`: dado um URL
    oficial, descarrega HTML, valida o host em `_ALLOWED`, remove ruído com
    BeautifulSoup e devolve texto até `_MAX_CHARS`. Gera sempre um `Source`
    para citação.

    Tipos não-HTML falham de propósito — PDFs não são tratados aqui (o CT é
    indexado offline pelo `indexer.py`).
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.agent.state import Source
from app.agent.tools import ToolResult
from app.config import settings
from app.logging_config import logger


_ALLOWED = {
    "portal.act.gov.pt",
    "act.gov.pt",
    "info.portaldasfinancas.gov.pt",
    "portaldasfinancas.gov.pt",
    "diariodarepublica.pt",
    "dre.pt",
    "cite.gov.pt",
    "seg-social.pt",
    "www.seg-social.pt",
}

_MAX_CHARS = 8000


def _is_allowed(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host.endswith(d) for d in _ALLOWED)


def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n", strip=True) if main else ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for ln in lines:
        if ln in seen and len(ln) < 80:
            continue
        seen.add(ln)
        deduped.append(ln)
    return "\n".join(deduped)[:_MAX_CHARS]


async def fetch_and_parse(url: str, http_client: httpx.AsyncClient) -> ToolResult:
    if not _is_allowed(url):
        return ToolResult(
            ok=False,
            data=None,
            sources=[],
            summary="",
            error=f"URL not in allowed official domains: {url}",
        )

    try:
        r = await http_client.get(url)
        r.raise_for_status()
    except (httpx.HTTPError, asyncio.TimeoutError) as exc:
        logger.warning("fetch_and_parse failed for {}: {}", url, exc)
        return ToolResult(ok=False, data=None, sources=[], summary="", error=str(exc))

    content_type = r.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return ToolResult(
            ok=False,
            data=None,
            sources=[],
            summary="",
            error=f"Unsupported content-type: {content_type}",
        )

    text = _clean_html(r.text)
    title = ""
    try:
        soup = BeautifulSoup(r.text, "lxml")
        title = (soup.title.string or "").strip() if soup.title else ""
    except Exception:
        pass

    source = Source(
        url=url,
        title=title or url,
        snippet=text[:400],
        domain=urlparse(url).netloc,
        score=1.0,
        source_type="web",
    )
    return ToolResult(
        ok=True,
        data=text,
        sources=[source],
        summary=f"Fetched {len(text)} chars from {urlparse(url).netloc}",
        error=None,
    )
