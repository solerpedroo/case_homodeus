"""Retrieval layer — vector index over Código do Trabalho + ingestion.

EN:
    `vector_store` wraps ChromaDB persistence; `indexer` downloads the official
    CT PDF (or uses a configured URL), chunks it, and upserts embeddings.
    At query time the agent calls `search_labor_code` which delegates here.

PT:
    `vector_store` envolve a persistência ChromaDB; `indexer` descarrega o PDF
    oficial do CT (ou URL configurada), divide em chunks e faz upsert dos
    embeddings. Em tempo de consulta o agente chama `search_labor_code`, que
    delega para aqui.
"""
