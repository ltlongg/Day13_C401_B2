# intent_classifier.py
from tags_schema import INTENT_TAGS, SAFETY_TAGS


def classify_intent(user_message: str, trace) -> dict:
    """
    Classify câu hỏi + tạo span để trace bước này.
    Trả về dict chứa intent và tags liên quan.
    """
    # Tạo span cho bước này
    span = trace.span(
        name="intent_classification",
        input={"message": user_message}
    )

    # ---- Logic classify đơn giản (bạn thay bằng LLM nếu muốn) ----
    message_lower = user_message.lower()

    if any(kw in message_lower for kw in ["điểm", "kết quả học tập", "điểm thi"]):
        intent = "grade_lookup"
    elif any(kw in message_lower for kw in ["lịch học", "thời khóa biểu", "tkb"]):
        intent = "schedule"
    elif any(kw in message_lower for kw in ["lịch thi", "thi cuối kỳ", "thi giữa kỳ"]):
        intent = "exam_schedule"
    elif any(kw in message_lower for kw in ["học phí", "nợ", "đóng tiền"]):
        intent = "tuition_debt"
    elif any(kw in message_lower for kw in ["bảo lưu", "nghỉ học", "rút môn"]):
        intent = "leave_of_absence"
    else:
        intent = "unknown"

    # Kiểm tra safety
    safety = "safe"
    if any(kw in message_lower for kw in ["ignore", "forget", "system prompt", "jailbreak"]):
        safety = "prompt_injection"

    # Đóng span với output và tags
    span.end(
        output={"intent": intent, "safety": safety},
        metadata={
            "intent_tag": INTENT_TAGS[intent],
            "safety_tag": SAFETY_TAGS[safety],
            "message_length": len(user_message),
        }
    )

    return {
        "intent": intent,
        "intent_tag": INTENT_TAGS[intent],
        "safety": safety,
        "safety_tag": SAFETY_TAGS[safety],
    }