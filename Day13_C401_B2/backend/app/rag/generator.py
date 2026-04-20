from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL, BASE_URL
from app.rag.retrieval import RetrievedChunk
from app.system_prompts import RAG_SYSTEM_PROMPT
from app.text_utils import clean_response_text

client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)


def prepare_rag_context(query: str, chunks: list[RetrievedChunk]) -> dict | None:
    """Prepare RAG messages and source metadata for a grounded response."""
    if not chunks:
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

    return {
        "messages": messages,
        "sources": sources,
        "tool_used": "rag",
    }


def generate_rag_response(query: str, chunks: list[RetrievedChunk]) -> dict | None:
    """Generate a response grounded in retrieved document chunks with citations."""
    prepared = prepare_rag_context(query, chunks)
    if not prepared:
        return None

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=prepared["messages"],
        temperature=0.3,
        max_completion_tokens=1000,
    )

    return {
        "response": clean_response_text(response.choices[0].message.content),
        "sources": prepared["sources"],
        "tool_used": "rag",
        "chunks_used": len(chunks),
    }
