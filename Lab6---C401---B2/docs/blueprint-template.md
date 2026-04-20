# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata

- [GROUP_NAME]:
- [REPO_URL]:
- [MEMBERS]:
  - Member A: [Name] | Role: Logging & PII
  - Member B: [Name] | Role: Tracing & Enrichment
  - Member C: [Name] | Role: SLO & Alerts
  - Member D: Đỗ Xuân Bằng (2A202600044) | Role: Load Test
  - Member E: [Name] | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)

- [VALIDATE_LOGS_FINAL_SCORE]: /100
- [TOTAL_TRACES_COUNT]:
- [PII_LEAKS_FOUND]:

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing

- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: [Path to image]
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: [Path to image]
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: [Path to image]
- [TRACE_WATERFALL_EXPLANATION]: (Briefly explain one interesting span in your trace)

### 3.2 Dashboard & SLOs

- [DASHBOARD_6_PANELS_SCREENSHOT]: [Path to image]
- [SLO_TABLE]:
  | SLI | Target | Window | Current Value |
  |---|---:|---|---:|
  | Latency P95 | < 3000ms | 28d | |
  | Error Rate | < 2% | 28d | |
  | Cost Budget | < $2.5/day | 1d | |

### 3.3 Alerts & Runbook

- [ALERT_RULES_SCREENSHOT]: [Path to image]
- [SAMPLE_RUNBOOK_LINK]: [docs/alerts.md#L...]

---

## 4. Incident Response (Group)

- [SCENARIO_NAME]: `rag_slow` "và `tool_fail`, `llm_fault`"
- [SYMPTOMS_OBSERVED]: Đối với `rag_slow`, p95/p99 latency tăng đột biến (đạt trên 8000ms+ cho 1 request RAG). Đối với `llm_fault` và `tool_fail`, hệ thống ném ra HTTP 500 (Internal Server Error) do graph bị crash khi router hoặc tool được gọi.
- [ROOT_CAUSE_PROVED_BY]: Log ghi nhận rõ ràng event của sự cố. Ví dụ cho `rag_slow`: `{"service": "assistant", "incident": "rag_slow", "event": "incident_triggered", "correlation_id": "req-363c3e71", "level": "warning"}`. Đối với lỗi 500, trace ghi nhận: `RuntimeError: Incident llm_fault triggered during router selection`.
- [FIX_ACTION]: Vô hiệu hóa giả lập lỗi bằng API (chạy script `python scripts/inject_incident.py --scenario [tên_lỗi] --disable`).
- [PREVENTIVE_MEASURE]: Triển khai Fallback/Retry Handler trong LangGraph để xử lý nếu một tool/LLM gặp lỗi, đồng thời thiết lập cảnh báo cho P95 Latency và tỉ lệ HTTP 500 (Error Rate) trên Dashboard.

---

## 5. Individual Contributions & Evidence

### [MEMBER_A_NAME]

- [TASKS_COMPLETED]:
- [EVIDENCE_LINK]: (Link to specific commit or PR)

### [MEMBER_B_NAME]

- [TASKS_COMPLETED]:
- [EVIDENCE_LINK]:

### [MEMBER_C_NAME]

- [TASKS_COMPLETED]:
- [EVIDENCE_LINK]:

### Đỗ Xuân Bằng (2A202600044)

- [TASKS_COMPLETED]:
  - Khởi chạy và kiểm thử hệ thống qua `scripts/load_test.py` với các mức độ concurrency (concurrency=2).
  - Bơm các sự kiện lỗi (`rag_slow`, `llm_fault`, `tool_fail`) bằng `scripts/inject_incident.py` để phá vỡ hệ thống theo kịch bản.
  - Phân tích và ghi nhận bằng chứng (Correlation IDs, Log lines, lỗi crash Exception) khi các lỗi xảy ra.
  - Báo cáo và hoàn thiện phần xử lý Incident cho Group Blueprint.
- [EVIDENCE_LINK]: [Chèn link PR hoặc Commit của bạn tại đây]

### [MEMBER_E_NAME]

- [TASKS_COMPLETED]:
- [EVIDENCE_LINK]:

---

## 6. Bonus Items (Optional)

- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
