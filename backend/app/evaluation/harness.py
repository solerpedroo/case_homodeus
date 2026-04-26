"""Async evaluation harness.

For each test case, runs the agent (v1 or v2), grades the answer with the
LLM judge, and aggregates metrics. Persists results to disk so the frontend
`/eval` page can render the v1-vs-v2 comparison without re-running.

Run via API (POST /eval/run) or as a script:
    python -m app.evaluation.harness --version v2 --concurrency 4
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


RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "evaluation_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


async def _run_one(
    case: TestCase,
    agent: LaborAgent,
    sem: asyncio.Semaphore,
) -> dict[str, Any]:
    async with sem:
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
    concurrency: int = 4,
) -> dict[str, Any]:
    cases = TEST_CASES[: limit or len(TEST_CASES)]
    agent = LaborAgent(http_client=http_client, version=agent_version)
    sem = asyncio.Semaphore(max(1, concurrency))

    tasks = [_run_one(c, agent, sem) for c in cases]
    results = await asyncio.gather(*tasks)

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


async def run_both(http_client: httpx.AsyncClient, concurrency: int = 4) -> dict[str, Any]:
    v1 = await run_eval(http_client, "v1", concurrency=concurrency)
    v2 = await run_eval(http_client, "v2", concurrency=concurrency)
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
    p.add_argument("--concurrency", type=int, default=4)
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
