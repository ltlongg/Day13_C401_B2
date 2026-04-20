# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- `[GROUP_NAME]`: C401-B2
- `[REPO_URL]`: https://github.com/ltlongg/Day13_C401_B2/tree/main
- `[MEMBERS]`:
  - Member A: Lã Thị Linh | Role: Logging & Security (Middleware + PII)
  - Member B: Trương Anh Long | Role: Tracing & AI Context (Langfuse)
  - Member C: Lê Thành Long | Role: Metrics & Alerting (SLO + Alerting)
  - Member D: Đỗ Xuân Bằng | Role: Test & Incident Response (Load Test + Incidents)
  - Member E: Đỗ Việt Anh | Role: Dashboard & Reporting (Visual & Reporting)

---

## 2. Group Performance (Auto-Verified)
- `[VALIDATE_LOGS_FINAL_SCORE]`: 100/100
- `[TOTAL_TRACES_COUNT]`: 16
- `[PII_LEAKS_FOUND]`: 0

--- 

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- `[EVIDENCE_CORRELATION_ID_SCREENSHOT]`: docs/evidence/logs-correlation-id.png
- `[EVIDENCE_PII_REDACTION_SCREENSHOT]`: docs/evidence/logs-pii-redaction.png
- `[EVIDENCE_TRACE_WATERFALL_SCREENSHOT]`: docs/evidence/trace-waterfall.png
- `[TRACE_WATERFALL_EXPLANATION]`: Span `rag_generate` chiếm latency lớn nhất do sự cố `rag_slow`, giúp xác định nút thắt cổ chai nằm ở bước truy vấn hoặc tạo kết quả từ RAG.

### 3.2 Dashboard & SLOs
- `[DASHBOARD_6_PANELS_SCREENSHOT]`: docs/evidence/dashboard-6-panels-top.png và dashboard-6-panels-bottom.png
- `[SLO_TABLE]`:
  | SLI         | Target     | Window | Current Value        |
  |---|---:|---|---:|
  | Latency P95 | < 3000ms   | 28d    | 2210ms               |
  | Error Rate  | < 2%       | 28d    | 0% (16/16 thành công)|
  | Cost Budget | < $2.5/day | 1d     | $0.001752/trace      |

### 3.3 Alerts & Runbook
- `[ALERT_RULES_SCREENSHOT]`: docs/evidence/alert-rules.png
- `[SAMPLE_RUNBOOK_LINK]`: docs/alerts.md

---

## 4. Incident Response (Group)
- `[SCENARIO_NAME]`: rag_slow
- `[SYMPTOMS_OBSERVED]`: Độ trễ P95 tăng cao, dashboard vượt ngưỡng SLO, trace waterfall cho thấy span RAG chậm bất thường.
- `[ROOT_CAUSE_PROVED_BY]`: Trace ID (Tham chiếu Langfuse) + dòng log sự kiện `incident_enabled` cho thấy sự cố `rag_slow` đang chạy.
- `[FIX_ACTION]`: Tắt incident `rag_slow`, tối ưu hóa prompt và quy trình truy xuất ngữ cảnh, xác nhận độ trễ giảm trên dashboard.
- `[PREVENTIVE_MEASURE]`: Duy trì cảnh báo độ trễ P95, bổ sung runbook thao tác nhanh và kiểm tra trạng thái sự cố qua endpoint `/health` khi demo.

---

## 5. Individual Contributions & Evidence

### Lã Thị Linh
- `[TASKS_COMPLETED]`: Thiết lập `CorrelationIdMiddleware` để đồng nhất mã ID truy vết, bổ sung Regex patterns cho PII (địa chỉ, Passport), đăng ký `scrub_event` vào structlog để tự động ẩn thông tin nhạy cảm.
- `[EVIDENCE_LINK]`: https://github.com/ltlongg/Day13_C401_B2/tree/feature/sprint1

### Trương Anh Long
- `[TASKS_COMPLETED]`: Sử dụng `bind_contextvars` để gắn User/Session ID vào log, triển khai các "Span" trong `agent.py` để tách biệt thời gian RAG và LLM, gắn tags (env, model, feature) vào Langfuse.
- `[EVIDENCE_LINK]`: https://github.com/ltlongg/Day13_C401_B2/tree/sprint-2

### Lê Thành Long
- `[TASKS_COMPLETED]`: Cấu hình chỉ số SLO (Latency < 2s, Error < 1%) trong `slo.yaml`, thiết lập quy tắc cảnh báo trong `alert_rules.yaml` cho các trường hợp hệ thống chậm hoặc vượt ngưỡng ngân sách.
- `[EVIDENCE_LINK]`: https://github.com/ltlongg/Day13_C401_B2/tree/sprint3

### Đỗ Xuân Bằng
- `[TASKS_COMPLETED]`: Thực hiện Load test với các kịch bản concurrency khác nhau, kích hoạt sự cố (incident injection) như `rag_slow` hoặc `llm_fault`, ghi lại minh chứng (Trace ID, Logs) phục vụ báo cáo.
- `[EVIDENCE_LINK]`: https://github.com/ltlongg/Day13_C401_B2/tree/feature/b4 và https://github.com/ltlongg/Day13_C401_B2/tree/sprint_4

### Đỗ Việt Anh
- `[TASKS_COMPLETED]`: Xây dựng Dashboard 6 panels (Latency, Traffic, Errors, Cost, Quality, SLO status), thu thập ảnh minh chứng cho toàn nhóm, hoàn thiện báo cáo Incident Response và nội dung Blueprint.
- `[EVIDENCE_LINK]`: https://github.com/ltlongg/Day13_C401_B2/tree/feature/sprint-5-final

---

## 6. Bonus Items (Optional)
- `[BONUS_COST_OPTIMIZATION]`: Chuyển đổi từ mô hình ước tính chi phí phẳng (flat-rate) sang theo dõi chính xác từng token (Input/Output). Giúp giảm sai số ước tính từ 80% xuống < 5%, hỗ trợ theo dõi ngân sách (Budget SLO) chính xác trên Dashboard.
- `[BONUS_AUDIT_LOGS]`: Triển khai Audit trail có cấu trúc bằng `structlog`. Mỗi hành động của người dùng đều gắn chặt với `user_id_hash`, `session_id` và `correlation_id` xuyên suốt các span, cho phép truy vết lịch sử (Tracing) và tra soát bảo mật (Auditing) ngay cả khi dữ liệu đã được ẩn danh (PII Redacted).
- `[BONUS_CUSTOM_METRIC]`: Xây dựng chỉ số **Quality Proxy Score** tự động đánh giá chất lượng câu trả lời của AI dựa trên kiến trúc Heuristic. Chỉ số này được theo dõi qua Dashboard để phát hiện sớm các trường hợp AI trả lời quá ngắn hoặc không đúng cấu trúc.
