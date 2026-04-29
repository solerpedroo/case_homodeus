"""Ingestion script: download the Código do Trabalho PDF and index article chunks.

EN:
    One-off (or CI) job — not executed per chat request. Steps:
    1. `download_pdf` caches bytes under `data/cache/`.
    2. `extract_pages` uses pypdf to pull text per page.
    3. `split_by_article` regex-splits on "Artigo N.º" headers so each vector
       row maps to a citeable article; long articles are sub-split by length.
    4. `vector_store.add_chunks` upserts ids + documents + metadata.

    Article-aware chunking beats generic splitters: legal answers need stable
    "Art. X.º CT" references.

PT:
    Job pontual (ou CI) — não corre por pedido de chat. Passos:
    1. `download_pdf` guarda o PDF em `data/cache/`.
    2. `extract_pages` extrai texto por página com pypdf.
    3. `split_by_article` divide por marcadores "Artigo N.º" para cada vetor
       corresponder a um artigo citável; artigos longos são subdivididos.
    4. `vector_store.add_chunks` faz upsert.

    Chunking por artigo evita cortar cláusulas ao meio e perder o número do artigo.

Run / Executar:
    python -m app.retrieval.indexer
"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import httpx
from pypdf import PdfReader

from app.config import settings
from app.logging_config import logger
from app.retrieval.vector_store import vector_store


CACHE_DIR = Path(settings.chroma_persist_dir).parent / "cache"
PDF_PATH = CACHE_DIR / "codigo_trabalho.pdf"
ARTICLE_RE = re.compile(r"(Artigo\s+\d+\.\s*[º°ªo]?[A-Z]?)", re.IGNORECASE)
MAX_CHUNK_CHARS = 2500


async def download_pdf(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        logger.info("PDF already cached at {}", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading Código do Trabalho from {}", url)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(60.0), follow_redirects=True
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    logger.info("Saved PDF ({} bytes) to {}", len(r.content), dest)
    return dest


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            pages.append((i + 1, text))
    return pages


def split_by_article(pages: list[tuple[int, str]]) -> list[dict]:
    """Split combined text into article-scoped chunks.

    A chunk corresponds to one article. Long articles are sub-split on
    paragraph boundaries to stay under the token budget for embedding.
    """
    full_text = "\n".join(t for _, t in pages)
    page_for_offset: list[int] = []
    for page_num, text in pages:
        page_for_offset.extend([page_num] * (len(text) + 1))

    chunks: list[dict] = []
    parts = ARTICLE_RE.split(full_text)

    if len(parts) <= 1:
        for i in range(0, len(full_text), MAX_CHUNK_CHARS):
            piece = full_text[i : i + MAX_CHUNK_CHARS].strip()
            if piece:
                chunks.append(
                    {
                        "id": f"raw-{i}",
                        "text": piece,
                        "metadata": {"source": "codigo_trabalho", "article": "unknown"},
                    }
                )
        return chunks

    cursor = 0
    for idx in range(1, len(parts), 2):
        header = parts[idx].strip()
        body = parts[idx + 1] if idx + 1 < len(parts) else ""
        article_match = re.search(r"\d+", header)
        article_num = article_match.group(0) if article_match else "unknown"
        text_block = (header + " " + body).strip()
        cursor += len(text_block)
        page_num = page_for_offset[min(cursor, len(page_for_offset) - 1)] if page_for_offset else 0

        for sub_i in range(0, len(text_block), MAX_CHUNK_CHARS):
            piece = text_block[sub_i : sub_i + MAX_CHUNK_CHARS].strip()
            if not piece:
                continue
            chunks.append(
                {
                    "id": f"art-{article_num}-{sub_i}",
                    "text": piece,
                    "metadata": {
                        "source": "codigo_trabalho",
                        "article": article_num,
                        "page": page_num,
                        "url": settings.labor_code_pdf_url,
                    },
                }
            )

    return chunks


async def index_labor_code(force: bool = False) -> int:
    """Returns number of chunks indexed."""
    if not settings.chromadb_enabled:
        logger.error(
            "CHROMADB_ENABLED=false — vector store is off; cannot index the Labor Code."
        )
        return 0
    vector_store.ensure_initialized()
    if not force and not vector_store.is_empty():
        existing = vector_store.collection.count()
        logger.info("Labor code already indexed ({} chunks). Skipping.", existing)
        return existing

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        await download_pdf(settings.labor_code_pdf_url, PDF_PATH)
    except Exception as exc:
        logger.error("Could not download Labor Code PDF: {}", exc)
        return 0

    if not PDF_PATH.exists():
        logger.error("PDF missing after download attempt; aborting indexing.")
        return 0

    pages = extract_pages(PDF_PATH)
    logger.info("Extracted {} pages of text", len(pages))
    chunks = split_by_article(pages)
    logger.info("Built {} article-scoped chunks", len(chunks))

    BATCH = 64
    total = 0
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        total += vector_store.add_chunks(batch)
        logger.info("Indexed {}/{}", total, len(chunks))
    return total


def main() -> None:
    if settings.embeddings_provider == "openai" and not settings.openai_api_key:
        logger.error(
            "EMBEDDINGS_PROVIDER=openai but OPENAI_API_KEY is not set. "
            "Either set OPENAI_API_KEY or switch to EMBEDDINGS_PROVIDER=local."
        )
        raise SystemExit(1)
    asyncio.run(index_labor_code(force=False))


if __name__ == "__main__":
    main()
