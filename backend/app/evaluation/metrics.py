"""Aggregate metrics from individual case results."""
from __future__ import annotations

import statistics
from typing import Any


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "n": 0,
            "correctness_avg": 0.0,
            "coverage_avg": 0.0,
            "citation_quality_avg": 0.0,
            "refusal_accuracy": 0.0,
            "tool_call_accuracy": 0.0,
            "latency_p50_ms": 0,
            "latency_p95_ms": 0,
            "by_difficulty": {},
        }

    correctness = [r["judge"]["correctness"] for r in results]
    coverage = [r["judge"]["coverage"] for r in results]
    citation = [r["judge"]["citation_quality"] for r in results]
    refusal = [r["judge"]["refusal_correct"] for r in results]
    tool_acc = [_tool_accuracy(r) for r in results]
    latencies = [r.get("latency_ms", 0) for r in results]

    by_diff: dict[str, list[float]] = {}
    for r in results:
        bucket = r.get("difficulty", "unknown")
        by_diff.setdefault(bucket, []).append(r["judge"]["correctness"])

    return {
        "n": len(results),
        "correctness_avg": round(_mean(correctness), 3),
        "coverage_avg": round(_mean(coverage), 3),
        "citation_quality_avg": round(_mean(citation), 3),
        "refusal_accuracy": round(_mean(refusal), 3),
        "tool_call_accuracy": round(_mean(tool_acc), 3),
        "latency_p50_ms": int(_quantile(latencies, 0.5)),
        "latency_p95_ms": int(_quantile(latencies, 0.95)),
        "by_difficulty": {
            bucket: round(_mean(scores), 3) for bucket, scores in by_diff.items()
        },
    }


def _tool_accuracy(r: dict[str, Any]) -> float:
    """A response is "tool-accurate" if at least one source's domain matches an expected domain.

    For refusal cases or cases with no expected domains, we count it as correct
    if the agent did NOT call inappropriate tools (out-of-scope).
    """
    expected = r.get("expected_domains", []) or []
    sources = r.get("sources", []) or []
    if not expected:
        # For refusal cases: success if the agent refused or used few tools
        return 1.0 if r.get("refused") or len(r.get("tool_traces", [])) <= 1 else 0.5
    domains_in_sources: list[str] = []
    for s in sources:
        d = (s.get("domain") or "").lower()
        if d:
            domains_in_sources.append(d)
        url = (s.get("url") or "").lower()
        for ed in expected:
            if ed.lower() in url:
                domains_in_sources.append(ed.lower())
    return 1.0 if any(any(ed.lower() in d for d in domains_in_sources) for ed in expected) else 0.0


def _mean(xs: list[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else 0.0


def _quantile(xs: list[float] | list[int], q: float) -> float:
    if not xs:
        return 0.0
    sorted_xs = sorted(xs)
    pos = (len(sorted_xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_xs) - 1)
    frac = pos - lo
    return sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac


def diff_versions(v1: dict[str, Any], v2: dict[str, Any]) -> dict[str, Any]:
    keys = ["correctness_avg", "coverage_avg", "citation_quality_avg", "refusal_accuracy", "tool_call_accuracy"]
    delta = {}
    for k in keys:
        a = v1.get(k, 0.0)
        b = v2.get(k, 0.0)
        delta[k] = {"v1": a, "v2": b, "delta": round(b - a, 3), "delta_pct": round((b - a) * 100, 1)}
    return delta
