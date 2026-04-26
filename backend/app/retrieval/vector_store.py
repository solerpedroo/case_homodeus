"""ChromaDB persistent client wrapper.

A single shared client per process — chroma's PersistentClient is thread-safe
for typical query patterns and we want to avoid per-request overhead. The
`labor_code` collection holds chunks of the Portuguese Labor Code; entries can
be (re)ingested via `retrieval/indexer.py`.

Embeddings:
- `local` (default): ChromaDB's bundled ONNX MiniLM-L6-v2. No API key needed,
  ~80MB downloaded on first use, fully offline thereafter. Quality is good
  enough for legal-text retrieval at this scale.
- `openai`: text-embedding-3-small (paid, slightly higher recall).

Switch via `EMBEDDINGS_PROVIDER=openai` if you have an OpenAI key.
"""
from __future__ import annotations

import os
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.config import settings
from app.logging_config import logger


COLLECTION_LABOR = "labor_code"


class VectorStore:
    def __init__(self) -> None:
        self._client: chromadb.api.ClientAPI | None = None
        self._collection: Any = None

    def _embedding_function(self):
        if settings.embeddings_provider == "openai" and settings.openai_api_key:
            logger.info("Using OpenAI embeddings (text-embedding-3-small)")
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name="text-embedding-3-small",
            )
        logger.info("Using local ONNX MiniLM embeddings (no API key required)")
        return embedding_functions.DefaultEmbeddingFunction()

    def ensure_initialized(self) -> None:
        if self._client is not None:
            return
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_LABOR,
            embedding_function=self._embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Vector store ready (path={}, collection={}, count={})",
            settings.chroma_persist_dir,
            COLLECTION_LABOR,
            self._collection.count(),
        )

    @property
    def collection(self) -> Any:
        self.ensure_initialized()
        return self._collection

    def is_empty(self) -> bool:
        try:
            return self.collection.count() == 0
        except Exception:
            return True

    def query(
        self,
        text: str,
        k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            self.ensure_initialized()
        except Exception as exc:
            logger.warning("Vector store unavailable: {}", exc)
            return []
        if self.is_empty():
            return []
        result = self._collection.query(
            query_texts=[text],
            n_results=k,
            where=where,
        )
        out: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        for _id, doc, meta, dist in zip(ids, docs, metas, dists):
            out.append(
                {
                    "id": _id,
                    "text": doc,
                    "metadata": meta or {},
                    "score": float(1.0 - dist),
                }
            )
        return out

    def add_chunks(self, chunks: list[dict[str, Any]]) -> int:
        if not chunks:
            return 0
        self.ensure_initialized()
        ids = [c["id"] for c in chunks]
        docs = [c["text"] for c in chunks]
        metas = [c.get("metadata", {}) for c in chunks]
        self._collection.upsert(ids=ids, documents=docs, metadatas=metas)
        return len(chunks)


vector_store = VectorStore()
