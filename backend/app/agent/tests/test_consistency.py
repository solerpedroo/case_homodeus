"""Regression tests for consistency of the agent's refusal & scoring logic.

These tests guarantee that an answerable question with official sources never
flips between "answer" and "refusal" across retries — the user-visible
flakiness this module was created to prevent.

The tests are intentionally framework-free: they run with plain
``python -m app.agent.tests.test_consistency`` from the ``backend`` folder so
they work without adding a pytest dependency. They are also discoverable by
pytest if installed.
"""
from __future__ import annotations

import asyncio
import sys
import traceback
from typing import Any

from app.agent.graph import LaborAgent
from app.agent.state import AgentState, Source, ToolCallTrace
from app.config import settings


# ---------- Test doubles ---------- #


class _FailingClient:
    """OpenAI-compatible client whose every call raises.

    Used to force ``_score_confidence`` into its heuristic-only branch so we
    can assert on deterministic behaviour without needing a live LLM.
    """

    class _Chat:
        class _Completions:
            async def create(self, **kwargs: Any) -> Any:
                raise RuntimeError("LLM disabled in tests")

        completions = _Completions()

    chat = _Chat()
    base_url = "test://offline"


def _make_agent() -> LaborAgent:
    agent = LaborAgent.__new__(LaborAgent)  # bypass __init__ (no real LLM)
    agent.version = "v2"
    agent.locale = "pt"
    agent.http = None  # type: ignore[assignment]
    agent.client = _FailingClient()
    agent.model = "test-model"
    agent.provider = "test"
    agent.system_prompt = ""
    agent.tools = []
    agent.max_iterations = 1
    return agent


def _official_source() -> Source:
    return Source(
        url="https://www.act.gov.pt/(pt-PT)/Legislacao/Legislacao_n/Documents/CT.pdf",
        title="Código do Trabalho — Art. 238.º",
        snippet="...",
        domain="act.gov.pt",
        score=1.0,
        source_type="labor_code_index",
    )


# ---------- Test cases ---------- #


def test_score_recognises_domain_citation() -> None:
    """A markdown-style citation with the domain (not the literal URL) must
    still count as a cited source."""
    agent = _make_agent()
    state: AgentState = {
        "user_query": "férias",
        "final_answer": (
            "Em Portugal, o trabalhador tem direito a 22 dias úteis de "
            "férias por ano (Art. 238.º CT). Fonte: act.gov.pt."
        ),
        "sources": [_official_source()],
        "tool_traces": [],
    }
    score = asyncio.run(agent._score_confidence(state))
    assert score >= settings.confidence_threshold, (
        f"expected score >= {settings.confidence_threshold}, got {score}"
    )


def test_score_recognises_title_citation() -> None:
    """When the answer references the source by its title (no URL), we still
    treat it as a citation."""
    agent = _make_agent()
    state: AgentState = {
        "user_query": "férias",
        "final_answer": (
            "Conforme o Código do Trabalho — Art. 238.º, o trabalhador tem "
            "direito a 22 dias úteis de férias remuneradas, com taxa de 100%."
        ),
        "sources": [_official_source()],
        "tool_traces": [],
    }
    score = asyncio.run(agent._score_confidence(state))
    assert score > 0.4, f"title citation should count; got {score}"


def test_should_not_refuse_when_official_source_present() -> None:
    """Even if confidence dipped, an answer with an official source must not
    be replaced by a refusal — that's exactly the flaky behaviour we fix."""
    agent = _make_agent()
    state: AgentState = {
        "user_query": "férias",
        "final_answer": (
            "Em Portugal, o trabalhador tem direito a 22 dias úteis de "
            "férias por ano (Art. 238.º CT)."
        ),
        "sources": [_official_source()],
        "tool_traces": [
            ToolCallTrace(tool_name="search_labor_code", success=True),
        ],
    }
    assert agent._should_refuse(state) is False


def test_should_refuse_when_no_sources_and_short_answer() -> None:
    """If we have no sources and the answer is empty/very short, refusing is
    the right thing — we are not regressing the actual refusal path."""
    agent = _make_agent()
    state: AgentState = {
        "user_query": "qualquer coisa",
        "final_answer": "Não sei.",
        "sources": [],
        "tool_traces": [],
    }
    assert agent._should_refuse(state) is True


def test_should_refuse_when_all_tools_failed_without_sources() -> None:
    agent = _make_agent()
    state: AgentState = {
        "user_query": "qualquer coisa",
        "final_answer": (
            "Resposta longa com algum conteúdo mas sem qualquer fonte oficial "
            "disponível neste momento, em parte porque a pesquisa falhou."
        ),
        "sources": [],
        "tool_traces": [
            ToolCallTrace(tool_name="search_web", success=False, error="boom"),
        ],
    }
    assert agent._should_refuse(state) is True


# ---------- Runner ---------- #


_TESTS = [
    test_score_recognises_domain_citation,
    test_score_recognises_title_citation,
    test_should_not_refuse_when_official_source_present,
    test_should_refuse_when_no_sources_and_short_answer,
    test_should_refuse_when_all_tools_failed_without_sources,
]


def main() -> int:
    failures = 0
    for fn in _TESTS:
        name = fn.__name__
        try:
            fn()
        except Exception:
            failures += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
        else:
            print(f"OK    {name}")
    print()
    print(f"{len(_TESTS) - failures}/{len(_TESTS)} tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
