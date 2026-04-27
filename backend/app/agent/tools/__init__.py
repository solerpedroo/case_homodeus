"""Agent tools — shared contract for every callable capability.

EN:
    Every tool returns a `ToolResult` dict with the same keys so
    `LaborAgent._execute_tool_named` can treat web search, PDF index, HTTP
    fetch, and calculators uniformly:

    - `ok`: whether the operation succeeded (timeouts / missing API key → False).
    - `data`: raw payload (hits, HTML text, numeric breakdown) for debugging.
    - `sources`: list of `Source` models the LLM must cite in the answer.
    - `summary`: short natural-language digest injected into the chat context.
    - `error`: human-readable failure reason when `ok` is False.

    Keeping this shape stable avoids special cases in tracing and SSE events.

PT:
    Cada ferramenta devolve um dict `ToolResult` com as mesmas chaves para o
    `LaborAgent._execute_tool_named` tratar pesquisa web, índice PDF, fetch
    HTTP e calculadoras de forma uniforme:

    - `ok`: se a operação teve sucesso (timeouts / chave em falta → False).
    - `data`: payload bruto (hits, texto HTML, números) para debug.
    - `sources`: lista de `Source` que o LLM deve citar na resposta.
    - `summary`: resumo curto injetado no contexto do chat.
    - `error`: mensagem de falha quando `ok` é False.

    Manter esta forma estável evita casos especiais no tracing e nos eventos SSE.
"""
from __future__ import annotations

from typing import Any, TypedDict

from app.agent.state import Source


class ToolResult(TypedDict, total=False):
    ok: bool
    data: Any
    sources: list[Source]
    summary: str
    error: str | None
