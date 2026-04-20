# tracer.py
import os
from datetime import datetime
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()

# Khởi tạo Langfuse client — dùng chung toàn app
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)


def create_trace(user_id: str, session_id: str, user_message: str):
    """
    Tạo 1 Trace mới cho mỗi request của sinh viên.
    Trace = container bọc toàn bộ hành trình xử lý.
    """
    trace = langfuse.trace(
        name="student_chatbot_request",
        user_id=user_id,          # ẩn danh hóa ở tầng trên trước khi truyền vào
        session_id=session_id,    # để group các turn trong 1 cuộc hội thoại
        input=user_message,
        metadata={
            "timestamp": datetime.utcnow().isoformat(),
            "app_version": "1.0.0",
        }
    )
    return trace


def create_span(trace, span_name: str, input_data: dict):
    """
    Tạo 1 Span (bước con) trong Trace.
    Gọi hàm này khi BẮT ĐẦU mỗi bước xử lý.
    """
    span = trace.span(
        name=span_name,
        input=input_data,
    )
    return span


def end_span(span, output_data: dict, tags: dict = None, level: str = "DEFAULT"):
    """
    Kết thúc Span, ghi output và tags.
    level: "DEFAULT" | "WARNING" | "ERROR"
    """
    span.end(
        output=output_data,
        level=level,
        metadata=tags or {},
    )


def update_trace_tags(trace, final_tags: dict, final_output: str, score: float = None):
    """
    Cập nhật tags tổng kết vào Trace sau khi xử lý xong.
    Đây là nơi gắn các tag quan trọng nhất để filter dashboard.
    """
    trace.update(
        output=final_output,
        tags=list(final_tags.values()),   # Langfuse tags là list string
        metadata=final_tags,              # metadata là dict — dùng để filter chi tiết
    )

    # Ghi score nếu có (ví dụ: relevance score từ RAG)
    if score is not None:
        trace.score(
            name="answer_relevance",
            value=score,
            comment="Auto-scored by retrieval confidence"
        )