from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000"
QUERIES = Path("data/sample_queries.jsonl")
DEFAULT_TIMEOUT = 30.0


@dataclass(frozen=True)
class QueryCase:
    name: str
    message: str
    username: str
    password: str
    student_id: str | None = None


@dataclass
class RequestResult:
    case_name: str
    status_code: int | None
    latency_ms: float
    request_id: str
    tool_used: str
    requires_student_id: bool
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent requests")
    parser.add_argument("--repeat", type=int, default=1, help="How many times to replay the query file")
    parser.add_argument("--base-url", default=BASE_URL, help="API base URL")
    parser.add_argument("--queries-file", type=Path, default=QUERIES, help="Path to JSONL query file")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Per-request timeout in seconds")
    return parser.parse_args()


def load_queries(path: Path) -> list[QueryCase]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"No queries found in {path}")

    queries: list[QueryCase] = []
    for line_number, line in enumerate(lines, start=1):
        payload = json.loads(line)
        message = str(payload.get("message", "")).strip()
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", "")).strip()
        if not message or not username or not password:
            raise ValueError(f"Invalid query contract on line {line_number} in {path}")

        queries.append(
            QueryCase(
                name=str(payload.get("name") or f"query_{line_number}"),
                message=message,
                username=username,
                password=password,
                student_id=payload.get("student_id"),
            )
        )
    return queries


def login(base_url: str, username: str, password: str, timeout: float) -> str:
    response = httpx.post(
        f"{base_url.rstrip('/')}/auth/login",
        json={"username": username, "password": password},
        timeout=timeout,
    )
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError(f"Login succeeded but no token returned for user {username}")
    return str(token)


def build_token_cache(queries: list[QueryCase], base_url: str, timeout: float) -> dict[tuple[str, str], str]:
    tokens: dict[tuple[str, str], str] = {}
    for query in queries:
        key = (query.username, query.password)
        if key not in tokens:
            tokens[key] = login(base_url, query.username, query.password, timeout)
    return tokens


def send_request(base_url: str, timeout: float, token: str, query: QueryCase) -> RequestResult:
    payload: dict[str, Any] = {
        "thread_id": str(uuid.uuid4()),
        "message": query.message,
    }
    if query.student_id:
        payload["student_id"] = query.student_id

    headers = {"Authorization": f"Bearer {token}"}
    started = time.perf_counter()
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        request_id = response.headers.get("x-request-id", "MISSING")
        body = _safe_json(response)
        return RequestResult(
            case_name=query.name,
            status_code=response.status_code,
            latency_ms=latency_ms,
            request_id=request_id,
            tool_used=str(body.get("tool_used", "unknown")),
            requires_student_id=bool(body.get("requires_student_id", False)),
            error=None if response.is_success else _extract_error(response, body),
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return RequestResult(
            case_name=query.name,
            status_code=None,
            latency_ms=latency_ms,
            request_id="REQUEST_ERROR",
            tool_used="request_error",
            requires_student_id=False,
            error=str(exc),
        )


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except json.JSONDecodeError:
        return {"detail": response.text}
    return body if isinstance(body, dict) else {"body": body}


def _extract_error(response: httpx.Response, body: dict[str, Any]) -> str:
    detail = body.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail
    text = response.text.strip()
    return text or f"HTTP {response.status_code}"


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, round((p / 100) * len(ordered) + 0.5) - 1))
    return ordered[idx]


def print_result(result: RequestResult) -> None:
    status = result.status_code if result.status_code is not None else "ERR"
    interrupt_suffix = " interrupt" if result.requires_student_id else ""
    error_suffix = f" | error={result.error}" if result.error else ""
    print(
        f"[{status}] {result.request_id} | {result.case_name} | "
        f"{result.tool_used}{interrupt_suffix} | {result.latency_ms:.1f}ms{error_suffix}"
    )


def print_summary(results: list[RequestResult]) -> None:
    latencies = [result.latency_ms for result in results]
    success_count = sum(
        1 for result in results if result.status_code is not None and 200 <= result.status_code < 300
    )
    failure_count = len(results) - success_count
    interrupt_count = sum(1 for result in results if result.requires_student_id)
    tool_counts = Counter(result.tool_used for result in results)

    print("\n--- Load Test Summary ---")
    print(f"Total requests: {len(results)}")
    print(f"Successful responses: {success_count}")
    print(f"Failures / transport errors: {failure_count}")
    print(f"Interrupt responses: {interrupt_count}")
    print(f"Average latency: {statistics.fmean(latencies):.1f}ms")
    print(f"P50 latency: {percentile(latencies, 50):.1f}ms")
    print(f"P95 latency: {percentile(latencies, 95):.1f}ms")
    print(f"P99 latency: {percentile(latencies, 99):.1f}ms")
    print(f"Tool distribution: {dict(tool_counts)}")


def main() -> None:
    args = parse_args()
    queries = load_queries(args.queries_file)
    tokens = build_token_cache(queries, args.base_url, args.timeout)
    scheduled_queries = queries * max(1, args.repeat)

    print(
        f"Loaded {len(queries)} base queries, running {len(scheduled_queries)} total requests "
        f"with concurrency={args.concurrency} against {args.base_url}."
    )

    results: list[RequestResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = [
            executor.submit(
                send_request,
                args.base_url,
                args.timeout,
                tokens[(query.username, query.password)],
                query,
            )
            for query in scheduled_queries
        ]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print_result(result)

    print_summary(results)

    if any(result.error for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
