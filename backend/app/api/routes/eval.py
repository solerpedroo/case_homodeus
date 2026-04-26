"""Evaluation endpoints.

- GET  /eval/cases       — list test cases
- POST /eval/run         — run the harness for a given version (v1|v2)
- GET  /eval/results     — fetch the latest persisted results from disk
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.evaluation.harness import RESULTS_DIR, run_eval
from app.evaluation.test_cases import TEST_CASES


router = APIRouter()


class EvalRunRequest(BaseModel):
    agent_version: str = "v2"
    limit: int | None = None
    concurrency: int = 4


@router.get("/cases")
async def list_cases() -> list[dict[str, Any]]:
    return [c.model_dump() for c in TEST_CASES]


@router.post("/run")
async def run_eval_endpoint(req: EvalRunRequest, request: Request) -> dict[str, Any]:
    return await run_eval(
        http_client=request.app.state.http_client,
        agent_version=req.agent_version,
        limit=req.limit,
        concurrency=req.concurrency,
    )


@router.get("/results")
async def get_results(version: str | None = Query(default=None)) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for v in ([version] if version else ["v1", "v2"]):
        path = Path(RESULTS_DIR) / f"{v}_results.json"
        if path.exists():
            out[v] = json.loads(path.read_text(encoding="utf-8"))
        else:
            out[v] = None
    if version and out.get(version) is None:
        raise HTTPException(status_code=404, detail=f"No results for {version}")
    return out
