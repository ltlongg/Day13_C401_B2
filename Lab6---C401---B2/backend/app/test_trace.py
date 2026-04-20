# test_trace.py
import os
from dotenv import load_dotenv
from langfuse import Langfuse
from app.agents.executor import execute_and_respond

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

print(f"Auth check: {langfuse.auth_check()}")

test_cases = [
    {"query": "Điểm môn Toán kỳ 1 của tôi?",        "student_id": "SV001"},
    {"query": "Lịch học tuần này của tôi?",           "student_id": "SV001"},
    {"query": "Tôi còn nợ bao nhiêu học phí?",        "student_id": "SV002"},
    {"query": "Lịch thi cuối kỳ của tôi?",            "student_id": "SV003"},
]

mock_tool_calls = {
    "Điểm môn Toán kỳ 1 của tôi?":  [{"name": "get_grades",   "arguments": {}}],
    "Lịch học tuần này của tôi?":    [{"name": "get_schedule", "arguments": {}}],
    "Tôi còn nợ bao nhiêu học phí?": [{"name": "get_tuition",  "arguments": {}}],
    "Lịch thi cuối kỳ của tôi?":     [{"name": "get_exam",     "arguments": {}}],
}

for case in test_cases:
    query      = case["query"]
    student_id = case["student_id"]

    print(f"\n{'='*50}")
    print(f"[Q] {query}")

    with langfuse.start_as_current_span(
        name="student_chatbot_request",
        input={"message": query, "student_id": student_id},
    ) as span:

        result = execute_and_respond(
            tool_calls=mock_tool_calls[query],
            query=query,
            student_id=student_id,
            trace=span,
        )

        span.update(
            output={"response": result["response"][:300], "tool_used": result["tool_used"]}
        )

    trace_id = langfuse.get_current_trace_id()
    print(f"[A] {result['response'][:150]}")
    print(f"[Tools] {result['tool_used']}")
    if trace_id:
        print(f"[URL] {langfuse.get_trace_url(trace_id=trace_id)}")

langfuse.flush()
print("\n✅ Xong!")