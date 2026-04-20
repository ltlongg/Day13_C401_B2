from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
INCIDENTS_PATH = Path("data/incidents.json")


def load_incident_names() -> list[str]:
    if not INCIDENTS_PATH.exists():
        return ["rag_slow", "tool_fail", "llm_fault"]
    data = json.loads(INCIDENTS_PATH.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return sorted(data)
    return ["rag_slow", "tool_fail", "llm_fault"]


def login(base_url: str, timeout: float) -> str:
    response = httpx.post(
        f"{base_url.rstrip('/')}/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=timeout,
    )
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError("Admin login succeeded but no token was returned")
    return str(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=load_incident_names())
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    token = login(args.base_url, timeout=10.0)
    path = f"/incidents/{args.scenario}/disable" if args.disable else f"/incidents/{args.scenario}/enable"
    r = httpx.post(
        f"{args.base_url.rstrip('/')}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    print(r.status_code, r.json())


if __name__ == "__main__":
    main()
