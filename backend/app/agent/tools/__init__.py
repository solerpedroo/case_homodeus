"""Agent tools.

All tools share the same return shape:
    {
        "ok": bool,
        "data": Any,
        "sources": list[Source],   # citation records
        "summary": str,            # short text summary for the LLM context
        "error": str | None,
    }

This uniformity simplifies the tool executor and the trace surfaced to
the UI.
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
