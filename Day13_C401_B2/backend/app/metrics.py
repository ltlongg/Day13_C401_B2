from __future__ import annotations

from collections import Counter
from math import ceil
from statistics import mean
from threading import Lock
from typing import Any

REQUEST_LATENCIES: list[int] = []
REQUEST_COSTS: list[float] = []
REQUEST_TOKENS_IN: list[int] = []
REQUEST_TOKENS_OUT: list[int] = []
ERRORS: Counter[str] = Counter()
TRAFFIC: int = 0
QUALITY_SCORES: list[float] = []
_LOCK = Lock()


def reset_metrics() -> None:
    """Reset in-memory metrics state for tests and local smoke checks."""
    global TRAFFIC

    with _LOCK:
        REQUEST_LATENCIES.clear()
        REQUEST_COSTS.clear()
        REQUEST_TOKENS_IN.clear()
        REQUEST_TOKENS_OUT.clear()
        ERRORS.clear()
        QUALITY_SCORES.clear()
        TRAFFIC = 0


def record_request(
    latency_ms: int,
    cost_usd: float = 0.0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    quality_score: float | None = None,
) -> None:
    """Record one completed request for the /metrics snapshot."""
    global TRAFFIC

    normalized_latency = max(int(latency_ms), 0)
    normalized_cost = max(float(cost_usd), 0.0)
    normalized_tokens_in = max(int(tokens_in), 0)
    normalized_tokens_out = max(int(tokens_out), 0)
    normalized_quality = None
    if quality_score is not None:
        normalized_quality = min(max(float(quality_score), 0.0), 1.0)

    with _LOCK:
        TRAFFIC += 1
        REQUEST_LATENCIES.append(normalized_latency)
        REQUEST_COSTS.append(normalized_cost)
        REQUEST_TOKENS_IN.append(normalized_tokens_in)
        REQUEST_TOKENS_OUT.append(normalized_tokens_out)
        if normalized_quality is not None:
            QUALITY_SCORES.append(normalized_quality)


def record_error(error_type: str, *, count_request: bool = True) -> None:
    """Record a failed request. By default it also increments traffic."""
    global TRAFFIC

    normalized_type = (error_type or "unknown_error").strip() or "unknown_error"
    with _LOCK:
        if count_request:
            TRAFFIC += 1
        ERRORS[normalized_type] += 1


def percentile(values: list[int], p: int) -> float:
    if not values:
        return 0.0

    percentile_rank = max(1, min(100, int(p)))
    items = sorted(values)
    idx = max(
        0,
        min(len(items) - 1, ceil((percentile_rank / 100) * len(items)) - 1),
    )
    return float(items[idx])


def snapshot() -> dict[str, Any]:
    """Return the JSON contract consumed by dashboard and alert rules."""
    with _LOCK:
        traffic = TRAFFIC
        latencies = list(REQUEST_LATENCIES)
        costs = list(REQUEST_COSTS)
        tokens_in = list(REQUEST_TOKENS_IN)
        tokens_out = list(REQUEST_TOKENS_OUT)
        errors = dict(ERRORS)
        quality_scores = list(QUALITY_SCORES)

    error_total = sum(errors.values())
    error_rate_pct = round((error_total / traffic) * 100, 2) if traffic else 0.0

    return {
        "traffic": traffic,
        "latency_p50": percentile(latencies, 50),
        "latency_p95": percentile(latencies, 95),
        "latency_p99": percentile(latencies, 99),
        "avg_cost_usd": round(mean(costs), 4) if costs else 0.0,
        "total_cost_usd": round(sum(costs), 4),
        "tokens_in_total": sum(tokens_in),
        "tokens_out_total": sum(tokens_out),
        "error_breakdown": {
            "total": error_total,
            "rate_pct": error_rate_pct,
            "by_type": errors,
        },
        "quality_avg": round(mean(quality_scores), 4) if quality_scores else 0.0,
    }
