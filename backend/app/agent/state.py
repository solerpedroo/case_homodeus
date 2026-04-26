"""Agent state, source records, and tool-call traces.

Pure data classes / TypedDicts. Kept separate so they can be imported by both
graph nodes and API serializers without pulling in heavy LLM deps.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


QuestionCategory = Literal[
    "tax",  # IRS retention
    "social_security",  # TSU
    "labor_code",  # Código do Trabalho - vacation, dismissal, lay-off, etc.
    "salary_calc",  # numerical computation needed
    "edge_case",  # cross-border, ambiguous, gray area
    "out_of_scope",  # not Portuguese labor law
]


class Source(BaseModel):
    """A citation tied to an answer."""

    url: str
    title: str = ""
    snippet: str = ""
    domain: str = ""
    score: float = 0.0
    source_type: Literal["web", "labor_code_index", "calculator"] = "web"


class ToolCallTrace(BaseModel):
    """Trace of a single tool invocation surfaced to the UI for transparency."""

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    output_summary: str = ""
    duration_ms: int = 0
    success: bool = True
    error: str | None = None


class AgentState(TypedDict, total=False):
    """Agent turn state (serializable). The orchestrator in graph.py is hand-rolled."""

    messages: list[dict[str, Any]]
    user_query: str
    conversation_id: str
    category: QuestionCategory
    plan: list[str]
    sources: list[Source]
    tool_traces: list[ToolCallTrace]
    iterations: int
    confidence: float
    final_answer: str
    refused: bool
    refusal_reason: str
    agent_version: Literal["v1", "v2"]
