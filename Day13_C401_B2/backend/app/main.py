import os
import uuid
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from structlog.contextvars import bind_contextvars

from app.assistant_graph import run_assistant_turn
from app.auth.sessions import create_session, get_current_user, require_admin
from app.auth.users import authenticate
from app.config import UPLOAD_DIR
from app.documents.metadata_store import (
    add_document,
    get_all_documents as get_all_doc_meta,
    remove_document,
)
from app.documents.pdf_parser import extract_text_from_pdf
from app.logging_config import configure_logging, get_logger
from app.metrics import record_error, record_request
from app.metrics import snapshot as metrics_snapshot
from app.middleware import CorrelationIdMiddleware
from app.mock_data.students import get_all_students
from app.pii import hash_user_id, summarize_text
from app.rag.ingestion import (
    add_document_to_index,
    initialize_index,
    remove_document_from_index,
)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    thread_id: str
    message: str
    student_id: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    sources: list
    tool_used: str
    requires_student_id: bool = False
    student_id: str | None = None


class StudentInfo(BaseModel):
    id: str
    name: str


class LoginResponse(BaseModel):
    username: str
    role: str
    display_name: str
    student_id: str | None = None
    token: str


os.makedirs(UPLOAD_DIR, exist_ok=True)
configure_logging()
logger = get_logger()


def _estimate_tokens(text: str) -> int:
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    # Simple heuristic: ~4 characters/token for mixed VN/EN short prompts.
    return max(1, len(cleaned) // 4)


def _estimate_cost_usd(tokens_in: int, tokens_out: int) -> float:
    # Lab-only approximation so cost panel is non-zero even without provider usage metadata.
    in_rate = 0.000001
    out_rate = 0.000002
    return round(tokens_in * in_rate + tokens_out * out_rate, 6)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing FAISS index...")
    initialize_index()
    print("FAISS index ready. Server started.")
    yield


app = FastAPI(
    title="Student Assistant API",
    description="API trợ lý sinh viên theo kiến trúc LangGraph + RAG + Agent Tools",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    user = authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu")
    return {**user, "token": create_session(user)}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return metrics_snapshot()


@app.get("/students", response_model=list[StudentInfo])
async def list_students(current_user: dict = Depends(require_admin)):
    students = get_all_students()
    return [StudentInfo(id=student["id"], name=student["name"]) for student in students]


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    start = perf_counter()
    effective_student_id = request.student_id
    if current_user["role"] == "student":
        effective_student_id = current_user.get("student_id")
    correlation_id = getattr(getattr(http_request, "state", None), "correlation_id", "")
    request_id = correlation_id or f"req-{uuid.uuid4().hex[:8]}"
    feature = "qa"
    model = os.getenv("MODEL_NAME", "claude-sonnet-4-5")
    session_id = f"s-{request.thread_id[:8]}"
    user_hash = hash_user_id(current_user.get("username", "anonymous"))
    bind_contextvars(
        service="api",
        env=os.getenv("ENV", "dev"),
        correlation_id=request_id,
        user_id_hash=user_hash,
        session_id=session_id,
        feature=feature,
        model=model,
    )

    logger.info(
        "request_received",
        payload={"message_preview": summarize_text(request.message)},
    )

    try:
        result = run_assistant_turn(
            request.thread_id, request.message, student_id=effective_student_id
        )
    except Exception as exc:
        record_error(type(exc).__name__)
        logger.exception(
            "request_failed",
            error_type=type(exc).__name__,
            payload={"message_preview": summarize_text(request.message)},
        )
        raise

    latency_ms = int((perf_counter() - start) * 1000)
    tokens_in = int(result.get("tokens_in", 0) or 0)
    tokens_out = int(result.get("tokens_out", 0) or 0)
    if tokens_in == 0:
        tokens_in = _estimate_tokens(request.message)
    if tokens_out == 0:
        tokens_out = _estimate_tokens(result.get("response", ""))

    cost_usd = float(result.get("cost_usd", 0.0) or 0.0)
    if cost_usd == 0.0:
        cost_usd = _estimate_cost_usd(tokens_in, tokens_out)

    quality_score = float(result.get("quality_score", 0.0) or 0.0)
    if quality_score == 0.0:
        response_text = (result.get("response") or "").strip()
        quality_score = 1.0 if len(response_text) >= 80 else 0.75 if response_text else 0.5
    record_request(
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        quality_score=quality_score,
    )
    logger.info(
        "response_sent",
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        payload={"answer_preview": summarize_text(result.get("response", ""))},
    )

    return ChatResponse(
        thread_id=result["thread_id"],
        response=result["response"],
        sources=result.get("sources", []),
        tool_used=result.get("tool_used", "unknown"),
        requires_student_id=result.get("requires_student_id", False),
        student_id=result.get("student_id"),
    )


@app.get("/admin/documents")
def list_documents(current_user: dict = Depends(require_admin)):
    return get_all_doc_meta()


@app.post("/admin/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(None),
    category: str = Form("general"),
    current_user: dict = Depends(require_admin),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF")

    doc_id = uuid.uuid4().hex[:12]
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")

    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        text, page_count = extract_text_from_pdf(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Không thể đọc file PDF: {e}")

    if not text.strip():
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="File PDF không có nội dung text")

    doc_title = title or os.path.splitext(file.filename)[0]
    chunk_count = add_document_to_index(doc_id, doc_title, category, text)

    doc_meta = add_document(
        doc_id=doc_id,
        filename=file.filename,
        title=doc_title,
        category=category,
        page_count=page_count,
        chunk_count=chunk_count,
        uploaded_by=current_user["username"],
    )

    return doc_meta


@app.delete("/admin/documents/{doc_id}")
def delete_document(doc_id: str, current_user: dict = Depends(require_admin)):
    removed = remove_document(doc_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    remove_document_from_index(doc_id)

    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    if os.path.exists(file_path):
        os.remove(file_path)

    return {"message": "Đã xóa tài liệu", "doc_id": doc_id}
