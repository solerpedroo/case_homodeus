"""Agent state, source records, and tool-call traces.

EN:
    Pure Pydantic models and a TypedDict describe everything the agent needs to
    serialize to JSON for the API and the evaluation harness.

    - `QuestionCategory`: coarse routing label from the classifier (tax, labor
      code, salary math, etc.). Drives tool hints and web-search domain filters.
    - `Source`: one citation (URL, title, domain, retrieval score, provenance:
      web vs vector index vs calculator).
    - `ToolCallTrace`: audit row for the UI — which tool ran, args, timing,
      success flag, error string.
    - `AgentState`: mutable dict shape accumulated during `LaborAgent.stream`;
      `total=False` means every field is optional until set.

PT:
    Modelos Pydantic puros e um TypedDict descrevem tudo o que o agente precisa
    serializar em JSON para a API e o harness de avaliação.

    - `QuestionCategory`: etiqueta de encaminhamento do classificador (IRS,
      código laboral, cálculos, etc.). Influencia ferramentas e filtros de
      domínio na pesquisa web.
    - `Source`: uma citação (URL, título, domínio, score, origem: web vs
      índice vs calculadora).
    - `ToolCallTrace`: linha de auditoria para a UI — ferramenta, args,
      tempo, sucesso, erro.
    - `AgentState`: dicionário acumulado durante `LaborAgent.stream`;
      `total=False` significa que cada campo é opcional até ser definido.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


QuestionCategory = Literal[
    "tax",  # EN: IRS / withholding — PT: IRS / retenção na fonte
    "social_security",  # EN: TSU / Social Security — PT: TSU / Segurança Social
    "labor_code",  # EN: Código do Trabalho topics — PT: temas do CT
    "salary_calc",  # EN: numeric payroll — PT: cálculos salariais
    "edge_case",  # EN: ambiguous / cross-border — PT: ambíguo / transfronteiriço
    "out_of_scope",  # EN: not PT labor law — PT: fora do âmbito
]


class Source(BaseModel):
    """EN: One citation backing factual claims in the answer.
    PT: Uma citação que sustenta afirmações factuais na resposta."""

    url: str
    title: str = ""
    snippet: str = ""
    domain: str = ""
    score: float = 0.0
    source_type: Literal["web", "labor_code_index", "calculator"] = "web"


class ToolCallTrace(BaseModel):
    """EN: Serializable record of a tool invocation for the chat UI / eval.
    PT: Registo serializável de uma invocação de ferramenta para a UI / eval."""

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    output_summary: str = ""
    duration_ms: int = 0
    success: bool = True
    error: str | None = None


class AgentState(TypedDict, total=False):
    """EN: Full turn state produced by `LaborAgent` (see graph.py).
    PT: Estado completo de um turno produzido pelo `LaborAgent` (ver graph.py)."""

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
