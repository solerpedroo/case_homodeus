"""Async evaluation harness — batch agent runs + scoring + persistence.

EN:
    For each `TestCase`, `_run_one`:
    1. Invokes `LaborAgent.run` with empty history (isolated question).
    2. Extracts answer, sources, tool traces, refusal flag, confidence.
    3. Calls `judge_answer` which either uses the judge LLM or a heuristic
       fallback when no API key is configured.
    4. Returns a dict merged into `results` and then `aggregate`d.

    `run_eval` writes `{version}_results.json` under `evaluation_results/`.
    `run_both` runs v1 and v2 sequentially and writes `v1_vs_v2.json` deltas.

    CLI: `python -m app.evaluation.harness --version v2 --concurrency 4`
    API: POST `/eval/run`

PT:
    Para cada `TestCase`, `_run_one`:
    1. Chama `LaborAgent.run` com histórico vazio (pergunta isolada).
    2. Extrai resposta, fontes, traces, recusa, confiança.
    3. Chama `judge_answer` (LLM juiz ou heurística sem chave).
    4. Devolve dict que entra em `results` e depois em `aggregate`.

    `run_eval` grava `{version}_results.json` em `evaluation_results/`.
    `run_both` corre v1 e v2 e grava deltas em `v1_vs_v2.json`.

    CLI: `python -m app.evaluation.harness --version v2 --concurrency 4`
    API: POST `/eval/run`
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx

from app.agent.graph import LaborAgent
from app.config import settings
from app.evaluation.judge import judge_answer
from app.evaluation.metrics import aggregate, diff_versions
from app.evaluation.test_cases import TEST_CASES, TestCase
from app.logging_config import logger


# EN: `backend/evaluation_results/` — gitignored in real deployments if desired.
# PT: Pasta `backend/evaluation_results/` — pode ir para .gitignore em produção.
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "evaluation_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


async def _run_one(
    case: TestCase,
    agent: LaborAgent,
    sem: asyncio.Semaphore,
) -> dict[str, Any]:
    async with sem:
        # EN: Semaphore caps parallel LLM/tool calls to avoid rate limits.
        # PT: Semáforo limita chamadas paralelas ao LLM/ferramentas (rate limits).
        logger.info("[{}] {} — {}", agent.version, case.id, case.question[:80])
        t0 = time.perf_counter()
        try:
            state = await agent.run(case.question, history=[], conversation_id=f"eval-{case.id}")
            answer = state.get("final_answer", "")
            sources = [s.model_dump() if hasattr(s, "model_dump") else s for s in state.get("sources", [])]
            tool_traces = [t.model_dump() if hasattr(t, "model_dump") else t for t in state.get("tool_traces", [])]
            refused = bool(state.get("refused", False))
            confidence = float(state.get("confidence", 0.0))
        except Exception as exc:
            logger.exception("Case {} failed: {}", case.id, exc)
            answer = f"(erro: {exc})"
            sources = []
            tool_traces = []
            refused = False
            confidence = 0.0

        latency_ms = int((time.perf_counter() - t0) * 1000)
        judge = await judge_answer(case, answer, sources, refused)

        return {
            "case_id": case.id,
            "difficulty": case.difficulty,
            "question": case.question,
            "expected_category": case.expected_category,
            "expected_domains": case.expected_domains,
            "expects_refusal": case.expects_refusal,
            "agent_version": agent.version,
            "answer": answer,
            "refused": refused,
            "confidence": confidence,
            "sources": sources,
            "tool_traces": tool_traces,
            "latency_ms": latency_ms,
            "judge": judge,
        }


async def run_eval(
    http_client: httpx.AsyncClient,
    agent_version: str = "v2",
    limit: int | None = None,
    concurrency: int = 1,
) -> dict[str, Any]:
    cases = TEST_CASES[: limit or len(TEST_CASES)]
    agent = LaborAgent(http_client=http_client, version=agent_version)
    sem = asyncio.Semaphore(max(1, concurrency))

    # EN: `gather` runs all cases concurrently up to the semaphore limit.
    # PT: `gather` executa todos os casos em paralelo até ao limite do semáforo.
    tasks = [_run_one(c, agent, sem) for c in cases]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    results: list[dict[str, Any]] = []
    for c, outcome in zip(cases, gathered, strict=True):
        if isinstance(outcome, BaseException):
            logger.exception(
                "[{}] case {} aborted: {}", agent.version, getattr(c, "id", "?"), outcome
            )
            results.append(
                {
                    "case_id": c.id,
                    "difficulty": c.difficulty,
                    "question": c.question,
                    "expected_category": c.expected_category,
                    "expected_domains": c.expected_domains,
                    "expects_refusal": c.expects_refusal,
                    "agent_version": agent_version,
                    "answer": f"(eval harness erro: {outcome})",
                    "refused": False,
                    "confidence": 0.0,
                    "sources": [],
                    "tool_traces": [],
                    "latency_ms": 0,
                    "judge": {
                        "correctness": 0.0,
                        "coverage": 0.0,
                        "citation_quality": 0.0,
                        "refusal_correct": 0.0,
                        "explanation": f"harness_exc:{type(outcome).__name__}",
                    },
                }
            )
        else:
            results.append(outcome)

    summary = aggregate(results)
    payload = {
        "agent_version": agent_version,
        "provider": settings.llm_provider,
        "model": settings.active_model,
        "judge_model": settings.active_judge_model,
        "n_cases": len(results),
        "summary": summary,
        "cases": results,
        "generated_at": int(time.time()),
    }

    out_path = RESULTS_DIR / f"{agent_version}_results.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote {}", out_path)
    return payload


async def run_both(http_client: httpx.AsyncClient, concurrency: int = 1) -> dict[str, Any]:
    """Run v2 then v1 — v2 uses substantially more tokens per case; on Groq free tier
    running v1 first often exhausts TPM/TPD before v2 completes.
    """
    v2 = await run_eval(http_client, "v2", concurrency=concurrency)
    v1 = await run_eval(http_client, "v1", concurrency=concurrency)
    delta = diff_versions(v1["summary"], v2["summary"])
    delta_path = RESULTS_DIR / "v1_vs_v2.json"
    delta_path.write_text(
        json.dumps({"v1": v1["summary"], "v2": v2["summary"], "delta": delta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"v1": v1, "v2": v2, "delta": delta}


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="HomoDeus eval harness")
    p.add_argument("--version", default="v2", choices=["v1", "v2", "both"])
    p.add_argument("--limit", type=int, default=None)
    p.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help=(
            "Max parallel eval cases (use 1 on Groq free tier TPM limits)."
        ),
    )
    return p


async def _main_async(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0, connect=5.0),
        follow_redirects=True,
        headers={"User-Agent": "HomoDeus-LaborAgent/1.0"},
    ) as http_client:
        if args.version == "both":
            await run_both(http_client, concurrency=args.concurrency)
        else:
            await run_eval(
                http_client,
                agent_version=args.version,
                limit=args.limit,
                concurrency=args.concurrency,
            )


def main() -> None:
    args = _build_arg_parser().parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
