from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import altair as alt
import httpx
import streamlit as st

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

import pandas as pd


DEFAULT_METRICS_URL = "http://127.0.0.1:8000/metrics"
DEFAULT_WINDOW_MINUTES = 60
SLO_FILE = Path("config/slo.yaml")


def load_slo_thresholds() -> dict[str, float]:
    defaults = {
        "latency_p95_ms": 3000.0,
        "error_rate_pct": 2.0,
        "daily_cost_usd": 2.5,
        "quality_score_avg": 0.75,
    }
    if yaml is None or not SLO_FILE.exists():
        return defaults
    raw = yaml.safe_load(SLO_FILE.read_text(encoding="utf-8")) or {}
    slis = raw.get("slis", {})
    for key in defaults:
        value = slis.get(key, {}).get("objective")
        if isinstance(value, (int, float)):
            defaults[key] = float(value)
    return defaults


def fetch_metrics(url: str) -> dict[str, Any]:
    with httpx.Client(timeout=5.0) as client:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Metrics payload must be a JSON object")
        return payload


def to_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def build_row(metrics: dict[str, Any]) -> dict[str, Any]:
    errors = metrics.get("error_breakdown", {})
    total_errors = sum(int(v) for v in errors.values()) if isinstance(errors, dict) else 0
    traffic = max(int(metrics.get("traffic", 0)), 1)
    error_rate_pct = (total_errors / traffic) * 100
    return {
        "ts": datetime.now(timezone.utc),
        "traffic": int(metrics.get("traffic", 0)),
        "latency_p50": to_float(metrics.get("latency_p50")),
        "latency_p95": to_float(metrics.get("latency_p95")),
        "latency_p99": to_float(metrics.get("latency_p99")),
        "total_cost_usd": to_float(metrics.get("total_cost_usd")),
        "avg_cost_usd": to_float(metrics.get("avg_cost_usd")),
        "tokens_in_total": int(metrics.get("tokens_in_total", 0)),
        "tokens_out_total": int(metrics.get("tokens_out_total", 0)),
        "quality_avg": to_float(metrics.get("quality_avg")),
        "error_count": total_errors,
        "error_rate_pct": error_rate_pct,
        "error_breakdown": errors if isinstance(errors, dict) else {},
    }


def render_multi_line_chart(
    data: list[dict[str, Any]],
    y_fields: list[str],
    y_title: str,
    color_domain: list[str],
    color_range: list[str],
) -> alt.Chart:
    df = pd.DataFrame(data)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])

    base = alt.Chart(df).transform_fold(
        y_fields, as_=["series", "value"]
    ).encode(
        x=alt.X("time:T", title="Time"),
        y=alt.Y("value:Q", title=y_title),
        color=alt.Color(
            "series:N",
            scale=alt.Scale(domain=color_domain, range=color_range),
            legend=alt.Legend(title=None, orient="top"),
        ),
    )

    line = base.mark_line(strokeWidth=2.5)
    
    points = base.mark_circle(size=70)
    
    tooltip = [
        alt.Tooltip("time:T", title="Time"),
        alt.Tooltip("series:N", title="Series"),
        alt.Tooltip("value:Q", title="Value", format=",.4f"),
    ]

    return (line + points).encode(tooltip=tooltip).properties(height=250).interactive()


st.set_page_config(page_title="Day 13 Observability Dashboard", layout="wide")
st.title("Day 13 Observability Dashboard")
st.caption("Layer-2 dashboard for Monitoring, Logging, and Observability lab")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("Settings")
    metrics_url = st.text_input("Metrics URL", value=DEFAULT_METRICS_URL)
    if st.button("Refresh now", use_container_width=True):
        st.rerun()
    window_minutes = st.slider(
        "Time range (minutes)",
        min_value=15,
        max_value=240,
        value=DEFAULT_WINDOW_MINUTES,
    )
    st.caption("Default time range is 1 hour to satisfy the dashboard quality bar.")

slo = load_slo_thresholds()

try:
    metrics = fetch_metrics(metrics_url)
    st.session_state.history.append(build_row(metrics))
except Exception as exc:  # pragma: no cover
    st.error(f"Cannot fetch metrics from `{metrics_url}`: {exc}")
    if not st.session_state.history:
        st.stop()

cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
history = [item for item in st.session_state.history if item["ts"] >= cutoff]
st.session_state.history = history

if not history:
    st.warning("No datapoints in selected time range yet. Please wait for the next refresh cycle.")
    st.stop()

latest = history[-1]
initial_ts = history[0]["ts"]
hours_elapsed = max((latest["ts"] - initial_ts).total_seconds() / 3600.0, 1 / 3600.0)
if latest["traffic"] < 2:
    st.info("Traffic hien tai < 2. Dashboard van ve duoc, nhung ban nen gui them request de thay xu huong.")

plot_history = history
if len(plot_history) == 1:
    seed = dict(plot_history[0])
    seed["ts"] = seed["ts"] - timedelta(seconds=1)
    plot_history = [seed, plot_history[0]]

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Traffic (requests)", latest["traffic"])
col_b.metric("Latency P95 (ms)", f"{latest['latency_p95']:.1f}")
col_c.metric("Error Rate (%)", f"{latest['error_rate_pct']:.2f}")
col_d.metric("Total Cost (USD)", f"${latest['total_cost_usd']:.4f}")

chart_1 = [
    {
        "time": item["ts"],
        "p50": item["latency_p50"],
        "p95": item["latency_p95"],
        "p99": item["latency_p99"],
        "slo_p95": slo["latency_p95_ms"],
    }
    for item in plot_history
]
chart_2 = [
    {"time": item["ts"], "traffic": item["traffic"], "qps_est": item["traffic"] / (window_minutes * 60.0)}
    for item in plot_history
]
error_keys: set[str] = set()
for item in plot_history:
    error_keys.update(item["error_breakdown"].keys())
chart_3 = []
for item in plot_history:
    row = {"time": item["ts"], "error_rate_pct": item["error_rate_pct"], "error_rate_slo": slo["error_rate_pct"]}
    for err in sorted(error_keys):
        row[f"err_{err}"] = item["error_breakdown"].get(err, 0)
    chart_3.append(row)

cost_budget_per_hour = slo["daily_cost_usd"] / 24.0
chart_4 = [
    {
        "time": item["ts"],
        "total_cost_usd": item["total_cost_usd"],
        "hourly_cost_est": item["total_cost_usd"] / hours_elapsed,
        "hourly_budget": cost_budget_per_hour,
    }
    for item in plot_history
]
chart_5 = [
    {
        "time": item["ts"],
        "tokens_in_total": item["tokens_in_total"],
        "tokens_out_total": item["tokens_out_total"],
    }
    for item in plot_history
]
chart_6 = [
    {"time": item["ts"], "quality_avg": item["quality_avg"], "quality_slo": slo["quality_score_avg"]}
    for item in plot_history
]

row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    st.subheader("1) Latency P50 / P95 / P99 (ms)")
    st.altair_chart(
        render_multi_line_chart(
            chart_1,
            y_fields=["p50", "p95", "p99", "slo_p95"],
            y_title="Milliseconds",
            color_domain=["p50", "p95", "p99", "slo_p95"],
            color_range=["#22c55e", "#3b82f6", "#ef4444", "#f59e0b"],
        ),
        use_container_width=True,
    )
with row1_col2:
    st.subheader("2) Traffic (Requests + QPS estimate)")
    st.altair_chart(
        render_multi_line_chart(
            chart_2,
            y_fields=["traffic", "qps_est"],
            y_title="Requests / QPS",
            color_domain=["traffic", "qps_est"],
            color_range=["#06b6d4", "#a855f7"],
        ),
        use_container_width=True,
    )

row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    st.subheader("3) Error Rate (%) + Breakdown")
    st.altair_chart(
        render_multi_line_chart(
            chart_3,
            y_fields=["error_rate_pct", "error_rate_slo"],
            y_title="Percent",
            color_domain=["error_rate_pct", "error_rate_slo"],
            color_range=["#ef4444", "#f59e0b"],
        ),
        use_container_width=True,
    )
    if error_keys:
        latest_breakdown = latest["error_breakdown"]
        breakdown_rows = [{"error_type": k, "count": v} for k, v in latest_breakdown.items()]
        breakdown_chart = (
            alt.Chart(alt.Data(values=breakdown_rows))
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#f97316")
            .encode(
                x=alt.X("error_type:N", title="Error Type"),
                y=alt.Y("count:Q", title="Count"),
                tooltip=["error_type:N", "count:Q"],
            )
            .properties(height=160)
        )
        st.altair_chart(breakdown_chart, use_container_width=True)
with row2_col2:
    st.subheader("4) Cost Over Time (USD)")
    st.altair_chart(
        render_multi_line_chart(
            chart_4,
            y_fields=["total_cost_usd", "hourly_cost_est", "hourly_budget"],
            y_title="USD",
            color_domain=["total_cost_usd", "hourly_cost_est", "hourly_budget"],
            color_range=["#14b8a6", "#0ea5e9", "#f59e0b"],
        ),
        use_container_width=True,
    )

row3_col1, row3_col2 = st.columns(2)
with row3_col1:
    st.subheader("5) Tokens In / Out")
    st.altair_chart(
        render_multi_line_chart(
            chart_5,
            y_fields=["tokens_in_total", "tokens_out_total"],
            y_title="Tokens",
            color_domain=["tokens_in_total", "tokens_out_total"],
            color_range=["#6366f1", "#e11d48"],
        ),
        use_container_width=True,
    )
with row3_col2:
    st.subheader("6) Quality Proxy")
    st.altair_chart(
        render_multi_line_chart(
            chart_6,
            y_fields=["quality_avg", "quality_slo"],
            y_title="Score",
            color_domain=["quality_avg", "quality_slo"],
            color_range=["#10b981", "#f59e0b"],
        ),
        use_container_width=True,
    )

with st.expander("Latest raw metrics payload"):
    st.json(metrics if "metrics" in locals() else latest)
