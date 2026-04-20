# rag_retrieve.py
import time
from dataclasses import dataclass

from langfuse import Langfuse
import os
from dotenv import load_dotenv

from app.config import RAG_TOP_K, RAG_RELEVANCE_THRESHOLD
from app.rag.ingestion import embed_texts, get_index, get_chunks, get_metadata
from app.tags_schema import RAG_TAGS

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)


@dataclass
class RetrievedChunk:
    content: str
    doc_title: str
    doc_id: str
    score: float
    chunk_index: int


def retrieve(query: str, trace=None) -> list[RetrievedChunk]:
    """Retrieve relevant document chunks for a query using FAISS vector search."""

    # ── Tạo span cho bước RAG ──
    span = None
    if trace:
        span = trace.span(
            name="rag_retrieval",
            input={
                "query": query,
                "top_k": RAG_TOP_K,
                "threshold": RAG_RELEVANCE_THRESHOLD,
            }
        )

    start_time = time.time()

    # ── Logic gốc của bạn, không đổi gì ──
    index = get_index()
    if index is None or index.ntotal == 0:
        if span:
            span.end(
                output={"docs_found": 0, "reason": "index_empty"},
                level="WARNING",
                metadata={
                    "rag_tag": RAG_TAGS["rag_miss"],
                    "rag_miss_reason": "index_empty_or_none",
                    "retrieval_time_ms": round((time.time() - start_time) * 1000, 2),
                }
            )
        return []

    all_chunks = get_chunks()
    all_metadata = get_metadata()

    query_embedding = embed_texts([query])
    scores, indices = index.search(query_embedding, RAG_TOP_K)

    chunks = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        if score < RAG_RELEVANCE_THRESHOLD:
            continue

        meta = all_metadata[idx]
        chunks.append(
            RetrievedChunk(
                content=all_chunks[idx],
                doc_title=meta["doc_title"],
                doc_id=meta["doc_id"],
                score=float(score),
                chunk_index=meta["chunk_index"],
            )
        )

    chunks.sort(key=lambda c: c.score, reverse=True)

    # ── Đóng span với kết quả ──
    if span:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        avg_score = sum(c.score for c in chunks) / len(chunks) if chunks else 0.0

        # Gán tag dựa trên chất lượng kết quả
        if not chunks:
            rag_tag = RAG_TAGS["rag_miss"]
            level = "WARNING"
        elif avg_score < 0.6:
            rag_tag = RAG_TAGS["rag_low_score"]
            level = "WARNING"
        else:
            rag_tag = RAG_TAGS["rag_hit"]
            level = "DEFAULT"

        span.end(
            output={
                "docs_found": len(chunks),
                "top_doc": chunks[0].doc_title if chunks else None,
                "top_score": round(chunks[0].score, 3) if chunks else None,
                "avg_score": round(avg_score, 3),
            },
            level=level,
            metadata={
                "rag_tag": rag_tag,
                "retrieval_time_ms": elapsed_ms,
                "docs_retrieved": len(chunks),
                "avg_relevance_score": round(avg_score, 3),
                "sources": list({c.doc_title for c in chunks}),  # unique doc titles
            }
        )

    return chunks