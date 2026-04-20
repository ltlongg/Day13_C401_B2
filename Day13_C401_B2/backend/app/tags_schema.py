# tags_schema.py

# ===== INTENT TAGS =====
# Phân loại câu hỏi sinh viên hỏi gì
INTENT_TAGS = {
    "grade_lookup":       "intent:grade_lookup",       # tra điểm
    "schedule":           "intent:schedule",            # lịch học
    "exam_schedule":      "intent:exam_schedule",       # lịch thi
    "tuition_debt":       "intent:tuition_debt",        # học phí còn nợ
    "leave_of_absence":   "intent:leave_of_absence",   # bảo lưu
    "rag_policy":         "intent:rag_policy",          # tra cứu nội quy/tài liệu
    "unknown":            "intent:unknown",             # không classify được
}

# ===== RESULT TAGS =====
# Kết quả tìm kiếm có ra không
RESULT_TAGS = {
    "found":              "result:found",
    "not_found":          "result:not_found",
    "partial":            "result:partial",             # tìm được 1 phần
    "db_error":           "result:db_error",
}

# ===== RAG TAGS =====
# Chất lượng retrieval từ tài liệu nội bộ
RAG_TAGS = {
    "rag_hit":            "rag:hit",                   # tìm được tài liệu liên quan
    "rag_miss":           "rag:miss",                  # không tìm được gì
    "rag_low_score":      "rag:low_score",             # tìm được nhưng không liên quan lắm
}

# ===== QUALITY TAGS =====
# Chất lượng câu trả lời
QUALITY_TAGS = {
    "hallucination_low":  "quality:hallucination_low",
    "hallucination_high": "quality:hallucination_high",  # LLM có thể đang bịa
    "grounded":           "quality:grounded",            # trả lời dựa trên nguồn thật
    "no_source":          "quality:no_source",           # trả lời không có nguồn
}

# ===== SAFETY TAGS =====
# Phát hiện câu hỏi nguy hiểm
SAFETY_TAGS = {
    "safe":               "safety:safe",
    "prompt_injection":   "safety:prompt_injection",   # sinh viên thử hack
    "pii_detected":       "safety:pii_detected",       # có MSSV/tên trong câu hỏi
    "out_of_scope":       "safety:out_of_scope",       # hỏi ngoài phạm vi chatbot
}