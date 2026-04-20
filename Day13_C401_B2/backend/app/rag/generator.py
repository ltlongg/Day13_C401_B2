import time
import os
from dotenv import load_dotenv
from openai import OpenAI
from langfuse import Langfuse

from app.config import OPENAI_API_KEY, OPENAI_MODEL, BASE_URL
from app.rag.retrieval import RetrievedChunk
from app.system_prompts import RAG_SYSTEM_PROMPT
from app.text_utils import clean_response_text

load_dotenv()

client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)


def prepare_rag_context(query: str, chunks: list[RetrievedChunk], trace=None) -> dict | None:
    """Prepare RAG messages and source metadata for a grounded response."""

    span = None
    if trace:
        span = trace.span(
            name="prepare_rag_context",
            input={
                "query": query,
                "chunks_count": len(chunks),
            }
        )

    if not chunks:
        if span:
            span.end(
                output={"result": None},
                level="WARNING",
                metadata={
                    "rag_tag": "rag:miss",
                    "reason": "no_chunks_provided",
                }
            )
        return None

    context_parts = []
    sources_map: dict[str, str] = {}
    for chunk in chunks:
        context_parts.append(
            f"--- Tai lieu: {chunk.doc_title} (phan {chunk.chunk_index + 1}) ---\n{chunk.content}"
        )
        sources_map[chunk.doc_title] = chunk.doc_id

    context = "\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"TAI LIEU THAM KHAO:\n{context}\n\n---\n\nCAU HOI CUA SINH VIEN: {query}",
        },
    ]

    sources = [
        {"title": title, "doc_id": doc_id}
        for title, doc_id in sources_map.items()
    ]

    result = {
        "messages": messages,
        "sources": sources,
        "tool_used": "rag",
    }

    if span:
        span.end(
            output={
                "sources": sources,
                "context_length": len(context),
                "chunks_used": len(chunks),
            },
            level="DEFAULT",
            metadata={
                "rag_tag": "rag:hit",
                "source_docs": [s["title"] for s in sources],
                "chunks_count": len(chunks),
                "avg_chunk_score": round(
                    sum(c.score for c in chunks) / len(chunks), 3
                ),
            }
        )

    return result


def generate_rag_response(query: str, chunks: list[RetrievedChunk], trace=None) -> dict | None:
    """Generate a response grounded in retrieved document chunks with citations."""

    start_time = time.time()

    prepared = prepare_rag_context(query, chunks, trace=trace)
    if not prepared:
        return None

    # ── Generation span — loại đặc biệt để Langfuse track token + cost ──
    generation = None
    if trace:
        generation = trace.generation(
            name="llm_rag_generation",
            model=OPENAI_MODEL,
            input=prepared["messages"],
            metadata={
                "quality_tag": "quality:grounded",   # có nguồn tài liệu thật
                "rag_tag": "rag:hit",
                "chunks_used": len(chunks),
                "temperature": 0.3,
            }
        )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=prepared["messages"],
        temperature=0.3,
        max_completion_tokens=1000,
    )

    answer = clean_response_text(response.choices[0].message.content)
    usage = response.usage
    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    if generation:
        generation.end(
            output=answer,
            usage={
                "input": usage.prompt_tokens,
                "output": usage.completion_tokens,
                "total": usage.total_tokens,
            },
            metadata={
                "quality_tag": "quality:grounded",
                "result_tag": "result:found",
                "hallucination_risk": "low",        # có nguồn → risk thấp
                "generation_time_ms": elapsed_ms,
                "sources_cited": len(prepared["sources"]),
            }
        )

    return {
        "response": answer,
        "sources": prepared["sources"],
        "tool_used": "rag",
        "chunks_used": len(chunks),
    }