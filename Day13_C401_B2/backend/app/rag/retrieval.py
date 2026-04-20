from dataclasses import dataclass

from app.config import RAG_TOP_K, RAG_RELEVANCE_THRESHOLD
from app.rag.ingestion import embed_texts, get_index, get_chunks, get_metadata


@dataclass
class RetrievedChunk:
    content: str
    doc_title: str
    doc_id: str
    score: float
    chunk_index: int


def retrieve(query: str) -> list[RetrievedChunk]:
    """Retrieve relevant document chunks for a query using FAISS vector search."""
    index = get_index()
    if index is None or index.ntotal == 0:
        return []

    all_chunks = get_chunks()
    all_metadata = get_metadata()

    query_embedding = embed_texts([query])  # Already normalized
    scores, indices = index.search(query_embedding, RAG_TOP_K)

    chunks = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:  # FAISS returns -1 for empty slots
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
    return chunks
