import pytest

from app.metrics import percentile, record_error, record_request, reset_metrics, snapshot


@pytest.fixture(autouse=True)
def clean_metrics_state() -> None:
    reset_metrics()
    yield
    reset_metrics()


def test_percentile_basic() -> None:
    assert percentile([100, 200, 300, 400], 50) == 200.0
    assert percentile([100, 200, 300, 400], 95) == 400.0
    assert percentile([], 95) == 0.0


def test_snapshot_defaults_match_contract() -> None:
    assert snapshot() == {
        "traffic": 0,
        "latency_p50": 0.0,
        "latency_p95": 0.0,
        "latency_p99": 0.0,
        "avg_cost_usd": 0.0,
        "total_cost_usd": 0.0,
        "tokens_in_total": 0,
        "tokens_out_total": 0,
        "error_breakdown": {
            "total": 0,
            "rate_pct": 0.0,
            "by_type": {},
        },
        "quality_avg": 0.0,
    }


def test_snapshot_aggregates_requests_and_failed_requests() -> None:
    record_request(latency_ms=100, cost_usd=0.01, tokens_in=100, tokens_out=25, quality_score=0.9)
    record_request(latency_ms=200, cost_usd=0.02, tokens_in=200, tokens_out=50, quality_score=0.8)
    record_request(latency_ms=300, cost_usd=0.03, tokens_in=300, tokens_out=75, quality_score=0.7)
    record_error("TimeoutError")

    metrics = snapshot()

    assert metrics["traffic"] == 4
    assert metrics["latency_p50"] == 200.0
    assert metrics["latency_p95"] == 300.0
    assert metrics["latency_p99"] == 300.0
    assert metrics["avg_cost_usd"] == 0.02
    assert metrics["total_cost_usd"] == 0.06
    assert metrics["tokens_in_total"] == 600
    assert metrics["tokens_out_total"] == 150
    assert metrics["error_breakdown"] == {
        "total": 1,
        "rate_pct": 25.0,
        "by_type": {"TimeoutError": 1},
    }
    assert metrics["quality_avg"] == 0.8
