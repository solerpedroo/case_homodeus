"""LLM-as-judge for the eval harness.

Provider-agnostic: uses Groq (default, free) or OpenAI depending on
`LLM_PROVIDER`. Judging is a different skill than answering, but with Llama
3.3 70B on Groq the same model is good enough for both — and it's free.

The judge returns:
- correctness: 0.0–1.0
- coverage: 0.0–1.0   (did it cover the ground_truth_facts?)
- citation_quality: 0.0–1.0
- refusal_correct: 0/1 (only when expects_refusal=True or out-of-scope)
- explanation: short textual reasoning
"""
from __future__ import annotations

import json
from typing import Any

from app.evaluation.test_cases import TestCase
from app.llm_client import get_judge_client, is_configured, supports_json_mode
from app.logging_config import logger


JUDGE_SYSTEM = """És um juiz independente que avalia respostas de um agente de
IA sobre direito laboral português. És rigoroso, justo e objetivo. Avalia em
três dimensões e devolve estritamente JSON válido."""


JUDGE_USER_TEMPLATE = """Avalia a resposta abaixo.

PERGUNTA:
{question}

DIFICULDADE: {difficulty}
CATEGORIA ESPERADA: {category}
ESPERA-SE RECUSA? {expects_refusal}

FACTOS QUE A RESPOSTA DEVERIA COBRIR:
{facts}

DOMÍNIOS OFICIAIS ESPERADOS COMO FONTE:
{domains}

RESPOSTA DO AGENTE:
{answer}

FONTES CITADAS PELO AGENTE:
{sources}

O AGENTE RECUSOU EXPLICITAMENTE? {refused}

Pontua de 0.0 a 1.0:
- correctness: a resposta é factualmente correta? (penaliza erros, números errados, artigos errados)
- coverage: cobre os factos esperados? (0.0 se não cobre nada, 1.0 se cobre todos)
- citation_quality: cita fontes oficiais portuguesas? URLs válidos? Domínios certos?
- refusal_correct: 1.0 se a recusa estava certa (esperada e feita, ou não esperada e não feita); 0.0 caso contrário.

Devolve APENAS um objeto JSON com chaves: correctness, coverage, citation_quality, refusal_correct, explanation. Sem markdown, sem prefixos."""


async def judge_answer(
    case: TestCase,
    answer: str,
    sources: list[dict[str, Any]],
    refused: bool,
) -> dict[str, Any]:
    if not is_configured():
        return _fallback(case, answer, sources, refused)

    src_lines = "\n".join(
        f"- {s.get('title','(sem título)')} | {s.get('url','')}" for s in sources
    ) or "(nenhuma)"
    facts_lines = "\n".join(f"- {f}" for f in case.ground_truth_facts) or "(N/A)"
    domains_lines = ", ".join(case.expected_domains) or "(N/A)"

    judge = get_judge_client()
    create_kwargs: dict[str, Any] = {
        "model": judge.model,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {
                "role": "user",
                "content": JUDGE_USER_TEMPLATE.format(
                    question=case.question,
                    difficulty=case.difficulty,
                    category=case.expected_category,
                    expects_refusal=case.expects_refusal,
                    facts=facts_lines,
                    domains=domains_lines,
                    answer=answer[:4000],
                    sources=src_lines[:2000],
                    refused=refused,
                ),
            },
        ],
    }
    if supports_json_mode():
        create_kwargs["response_format"] = {"type": "json_object"}

    try:
        completion = await judge.client.chat.completions.create(**create_kwargs)
        raw = completion.choices[0].message.content or "{}"
        data = _parse_json_loose(raw)
        return {
            "correctness": _clamp(data.get("correctness", 0.0)),
            "coverage": _clamp(data.get("coverage", 0.0)),
            "citation_quality": _clamp(data.get("citation_quality", 0.0)),
            "refusal_correct": _clamp(data.get("refusal_correct", 0.0)),
            "explanation": str(data.get("explanation", ""))[:1000],
        }
    except Exception as exc:
        logger.warning("Judge failed for {}: {} — falling back to heuristic.", case.id, exc)
        return _fallback(case, answer, sources, refused)


def _parse_json_loose(raw: str) -> dict[str, Any]:
    """Tolerate models that wrap JSON in ```json fences or add prefix text."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)


def _clamp(v: Any) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def _fallback(
    case: TestCase,
    answer: str,
    sources: list[dict[str, Any]],
    refused: bool,
) -> dict[str, Any]:
    """Heuristic fallback when no judge LLM is available."""
    a = answer.lower()
    fact_hits = sum(
        1
        for f in case.ground_truth_facts
        if any(token in a for token in f.lower().split() if len(token) > 4)
    )
    coverage = (fact_hits / max(1, len(case.ground_truth_facts))) if case.ground_truth_facts else 0.5

    domain_hits = sum(
        1 for s in sources if any(d in (s.get("domain") or s.get("url", "")) for d in case.expected_domains)
    )
    citation = min(1.0, domain_hits / max(1, len(case.expected_domains))) if case.expected_domains else (0.7 if sources else 0.0)

    correctness = round(0.6 * coverage + 0.4 * citation, 3)

    if case.expects_refusal:
        refusal_correct = 1.0 if refused else 0.0
    else:
        refusal_correct = 0.0 if refused else 1.0

    return {
        "correctness": correctness,
        "coverage": coverage,
        "citation_quality": citation,
        "refusal_correct": refusal_correct,
        "explanation": "Heuristic fallback (no judge LLM).",
    }
