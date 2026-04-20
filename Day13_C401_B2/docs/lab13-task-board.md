# Lab13 Task Board

Tai lieu nay dung de giao viec nhanh theo thanh vien. Moi task nen di kem commit rieng va evidence ro rang.

## A - Logging And Security

- `A1` Tao `backend/app/middleware.py` voi `CorrelationIdMiddleware`.
- `A2` Bind `correlation_id` vao log context va tra `x-request-id` trong response.
- `A3` Mo rong regex trong `backend/app/pii.py` cho thong tin nhay cam bo sung.
- `A4` Bat `scrub_event` trong `backend/app/logging_config.py`.
- `A5` Cap nhat `config/logging_schema.json` neu can.
- Evidence:
  - log line co `correlation_id`
  - `validate_logs.py` pass phan schema va PII

## B - Tracing And Main Integration

- `B1` Noi `configure_logging()` vao `backend/app/main.py`.
- `B2` Add middleware vao app ma khong pha auth/chat flow hien tai.
- `B3` Bind context cho request log: user, session, feature, model neu co.
- `B4` Them span/tracing trong `assistant_graph.py`, `rag/generator.py`, `general/generator.py`, `agents/executor.py`.
- `B5` Dam bao `GET /health` va `GET /metrics` cho debug va dashboard.
- Evidence:
  - screenshot Langfuse co trace day du
  - log request/response co thong tin context

## C - Metrics, SLO, Alerts

- `C1` Hoan thien `backend/app/metrics.py`.
- `C2` Chot JSON contract cho `GET /metrics`.
- `C3` Cap nhat `config/slo.yaml`.
- `C4` Cap nhat `config/alert_rules.yaml`.
- `C5` Cross-check dashboard metrics keys voi thanh vien E.
- Evidence:
  - sample output cua `/metrics`
  - file SLO va alert khong con placeholder sai contract

## D - Load Test And Incidents

- `D1` Tao `backend/app/incidents.py` voi 3 incidents da chot.
- `D2` Them `data/incidents.json`.
- `D3` Them `data/sample_queries.jsonl` theo contract cua Lab6.
- `D4` Sua `scripts/load_test.py` de login, lay token, va goi `/chat` dung payload.
- `D5` Sua `scripts/inject_incident.py` de goi dung incident endpoints.
- `D6` Noi incident vao flow thuc te de demo `rag_slow`, `tool_fail`, `llm_fault`.
- Evidence:
  - log/trace khi incident duoc bat
  - ket qua load test voi it nhat 2 muc concurrency

## E - Dashboard And Report

- `E1` Dung dashboard theo `docs/dashboard-spec.md`.
- `E2` Thu screenshot logs, traces, alerts, metrics.
- `E3` Hoan thien `docs/grading-evidence.md`.
- `E4` Hoan thien `docs/blueprint-template.md`.
- `E5` Viet incident report trong `docs/alerts.md` hoac blueprint.
- Evidence:
  - dashboard 6 panel
  - khong con `[TODO]`

## Shared Rules

- Thanh vien B giu quyen merge cuoi cho `backend/app/main.py`.
- Khong doi contract da chot trong `docs/lab13-integration-contract.md` neu chua thong nhat ca nhom.
- Moi nguoi update evidence cua minh sau khi xong task.

## Suggested Sequence

1. A1 -> A4
2. D1 -> D3
3. B1 -> B5
4. C1 -> C5
5. D4 -> D6
6. E1 -> E5
7. Codex review cuoi
