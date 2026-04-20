# Lab13 Integration Contract For Lab6

Muc tieu cua tai lieu nay la chot cac quy uoc chung de nhom tich hop observability vao `Lab6---C401---B2` ma khong bi lech contract giua cac thanh vien.

## Source Of Truth

- App chinh de tich hop la `Lab6---C401---B2/backend/app`.
- Khong tao chatbot moi cho Lab13.
- Khong copy nguyen `Lab13-Observability/app/agent.py`, `mock_llm.py`, `mock_rag.py` vao Lab6.
- `Lab13-Observability` chi duoc dung lam reference cho observability pattern va script contract.

## Migration Map

### File da co san o Lab6

- `backend/app/main.py`
- `backend/app/logging_config.py`
- `backend/app/pii.py`
- `backend/app/metrics.py`
- `backend/app/tracing.py`
- `backend/app/assistant_graph.py`
- `backend/app/rag/generator.py`
- `backend/app/general/generator.py`
- `backend/app/agents/executor.py`

### File con thieu o Lab6 va can tao moi

- `backend/app/middleware.py`
- `backend/app/incidents.py`
- `data/sample_queries.jsonl`
- `data/incidents.json`

### File khong nen port 1:1

- `Lab13-Observability/app/agent.py`
  Huong xu ly: map tracing/span vao `assistant_graph.py`, `rag/generator.py`, `general/generator.py`, `agents/executor.py`.
- `Lab13-Observability/app/schemas.py`
  Huong xu ly: tiep tuc dung models trong `backend/app/main.py` cua Lab6, chi tach file neu nhom thay can.

## Runtime Contract

### Logging

- Log file mac dinh: `data/logs.jsonl`
- Response header bat buoc: `x-request-id`
- Correlation field trong log: `correlation_id`
- Required log fields:
  - `ts`
  - `level`
  - `service`
  - `event`
  - `correlation_id`
- Optional enrichment fields:
  - `env`
  - `user_id_hash`
  - `session_id`
  - `feature`
  - `model`
  - `latency_ms`
  - `tokens_in`
  - `tokens_out`
  - `cost_usd`
  - `error_type`
  - `tool_name`
  - `payload`

### Metrics

- Endpoint: `GET /metrics`
- `/metrics` phai tra JSON phuc vu dashboard va alerting.
- Metrics keys muc tieu:
  - `traffic`
  - `latency_p50`
  - `latency_p95`
  - `latency_p99`
  - `avg_cost_usd`
  - `total_cost_usd`
  - `tokens_in_total`
  - `tokens_out_total`
  - `error_breakdown`
  - `quality_avg`
- JSON shape chot cho `error_breakdown`:
  - `total`
  - `rate_pct`
  - `by_type`
- Sample `/metrics` response:

```json
{
  "traffic": 18,
  "latency_p50": 182.0,
  "latency_p95": 941.0,
  "latency_p99": 1320.0,
  "avg_cost_usd": 0.0047,
  "total_cost_usd": 0.0846,
  "tokens_in_total": 12480,
  "tokens_out_total": 3188,
  "error_breakdown": {
    "total": 1,
    "rate_pct": 5.56,
    "by_type": {
      "TimeoutError": 1
    }
  },
  "quality_avg": 0.87
}
```

- Dashboard mapping de cross-check voi thanh vien E:
  - Panel 1 Latency: `latency_p50`, `latency_p95`, `latency_p99`
  - Panel 2 Traffic: `traffic`
  - Panel 3 Error rate + breakdown: `error_breakdown.rate_pct`, `error_breakdown.by_type`
  - Panel 4 Cost: `avg_cost_usd`, `total_cost_usd`
  - Panel 5 Tokens: `tokens_in_total`, `tokens_out_total`
  - Panel 6 Quality proxy: `quality_avg`
- Gia tri trong `/metrics` la snapshot in-memory theo process lifetime hien tai cua backend.

### Incident Injection

- Incident names thong nhat:
  - `rag_slow`
  - `tool_fail`
  - `llm_fault`
- Control endpoints:
  - `POST /incidents/{name}/enable`
  - `POST /incidents/{name}/disable`
- `GET /health` nen tra ve state incident hien tai de debug nhanh.

### Chat + Load Test

- App Lab6 van la auth-first app.
- `scripts/load_test.py` phai login lay token truoc khi goi `/chat`.
- Payload chat contract cho load test:
  - `thread_id`
  - `message`
  - `student_id` khi can test luong admin hoac tra cuu ho sinh vien cu the
- `sample_queries.jsonl` khong duoc dung contract cu cua Lab13 (`user_id`, `session_id`, `feature`) neu chua co lop mapping ro rang.

## Ownership Boundaries

- `backend/app/main.py`
  Owner chinh: Thanh vien B
  Ly do: day la diem giao nhau cua logging, tracing, metrics, auth, chat flow.
- `backend/app/middleware.py`
  Owner chinh: Thanh vien A
- `backend/app/incidents.py`
  Owner chinh: Thanh vien D
- `backend/app/metrics.py`
  Owner chinh: Thanh vien C
- `scripts/load_test.py` va `scripts/inject_incident.py`
  Owner chinh: Thanh vien D
- `docs/dashboard-spec.md`, `docs/blueprint-template.md`, `docs/grading-evidence.md`, `docs/alerts.md`
  Owner chinh: Thanh vien E

## Integration Rules

- Khong sua cung luc `main.py` ma khong thong bao cho thanh vien B.
- Khong doi ten incident sau khi da chot contract.
- Khong doi ten metrics keys sau khi thanh vien E bat dau dung dashboard.
- Khi them field log moi, phai cap nhat `config/logging_schema.json` va `scripts/validate_logs.py`.
- Khi thay doi contract script, phai ghi ro trong task board va bao lai nguoi phu trach.

## Recommended Build Order

1. Thanh vien A tao middleware va chot schema logging.
2. Thanh vien D tao incidents va sample data cho script.
3. Thanh vien B noi middleware, logging, tracing vao `main.py` va chat flow.
4. Thanh vien C hoan thien `/metrics`, `slo.yaml`, `alert_rules.yaml`.
5. Thanh vien D chay load test va incident demo.
6. Thanh vien E thu evidence, dashboard, blueprint.

## Review Gates

- Gate 1: backend import duoc, khong vo ngay khi khoi dong.
- Gate 2: `scripts/load_test.py` va `scripts/inject_incident.py` chay dung contract moi.
- Gate 3: `scripts/validate_logs.py` pass khi gui mot lo request mau.
- Gate 4: dashboard doc duoc metrics va report co screenshot that.

## Codex Scope

Codex chi lam cac viec sau:

- so sanh codebase va chot migration map
- chot runtime contract
- chot ownership va build order
- review code cua tung thanh vien
- final integration review truoc khi nop bai

Codex khong lam ho phan implementation chinh cua A, B, C, D, E tru khi nhom yeu cau ro rang sau.
