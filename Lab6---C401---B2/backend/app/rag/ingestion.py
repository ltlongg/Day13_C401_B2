import os
import json
import numpy as np
import faiss
from openai import OpenAI

from app.config import JINA_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIM, FAISS_INDEX_DIR

embedding_client = OpenAI(api_key=JINA_API_KEY, base_url="https://api.jina.ai/v1")

_index: faiss.IndexFlatIP | None = None
_metadata: list[dict] = []
_chunks: list[str] = []


def chunk_document(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks by character count, respecting paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(para) > chunk_size:
                words = para.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= chunk_size:
                        current_chunk = f"{current_chunk} {word}" if current_chunk else word
                    else:
                        chunks.append(current_chunk.strip())
                        overlap_words = current_chunk.split()[-overlap // 5 :] if overlap > 0 else []
                        current_chunk = " ".join(overlap_words + [word])
            else:
                overlap_text = current_chunk[-(overlap):] if overlap > 0 and current_chunk else ""
                current_chunk = f"{overlap_text}\n\n{para}" if overlap_text else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed texts one by one (Jina free tier does not allow concurrent/batch requests)."""
    all_embeddings = []
    for text in texts:
        response = embedding_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[text],
        )
        all_embeddings.append(response.data[0].embedding)
    embeddings = np.array(all_embeddings, dtype=np.float32)
    faiss.normalize_L2(embeddings)
    return embeddings


def _save_index():
    """Save FAISS index and metadata to disk."""
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
    faiss.write_index(_index, os.path.join(FAISS_INDEX_DIR, "index.faiss"))
    with open(os.path.join(FAISS_INDEX_DIR, "store.json"), "w", encoding="utf-8") as f:
        json.dump({"chunks": _chunks, "metadata": _metadata}, f, ensure_ascii=False)


def _load_index() -> bool:
    """Try to load existing FAISS index from disk. Returns True if loaded."""
    global _index, _metadata, _chunks
    index_path = os.path.join(FAISS_INDEX_DIR, "index.faiss")
    store_path = os.path.join(FAISS_INDEX_DIR, "store.json")

    if os.path.exists(index_path) and os.path.exists(store_path):
        _index = faiss.read_index(index_path)
        with open(store_path, "r", encoding="utf-8") as f:
            store = json.load(f)
        _chunks = store["chunks"]
        _metadata = store["metadata"]
        print(f"Loaded FAISS index: {_index.ntotal} vectors from disk.")
        return True
    return False


def initialize_index():
    """Load existing FAISS index from disk, or create an empty one."""
    global _index, _metadata, _chunks

    if _index is not None:
        return

    if _load_index():
        return

    _index = faiss.IndexFlatIP(EMBEDDING_DIM)
    _chunks = []
    _metadata = []
    print("Initialized empty FAISS index.")


def add_document_to_index(doc_id: str, title: str, category: str, content: str) -> int:
    """Chunk, embed (one-by-one), and add a document to the FAISS index.

    Returns the number of chunks added.
    """
    global _index, _metadata, _chunks

    if _index is None:
        initialize_index()

    chunks = chunk_document(content)
    if not chunks:
        return 0

    print(f"Embedding {len(chunks)} chunks for '{title}' (one by one)...")
    embeddings = embed_texts(chunks)

    for i, chunk in enumerate(chunks):
        _chunks.append(chunk)
        _metadata.append({
            "doc_id": doc_id,
            "doc_title": title,
            "category": category,
            "chunk_index": i,
            "total_chunks": len(chunks),
        })

    _index.add(embeddings)
    _save_index()
    print(f"Added {len(chunks)} chunks for '{title}' to FAISS index.")
    return len(chunks)


def remove_document_from_index(doc_id: str) -> bool:
    """Remove all chunks for a document and rebuild the FAISS index.

    Reconstructs vectors from the existing index to avoid re-calling Jina API.
    """
    global _index, _metadata, _chunks

    if _index is None:
        return False

    keep_indices = [i for i, m in enumerate(_metadata) if m["doc_id"] != doc_id]
    if len(keep_indices) == len(_metadata):
        return False

    if not keep_indices:
        _index = faiss.IndexFlatIP(EMBEDDING_DIM)
        _chunks = []
        _metadata = []
    else:
        vectors = np.array(
            [_index.reconstruct(i) for i in keep_indices], dtype=np.float32
        )
        new_index = faiss.IndexFlatIP(EMBEDDING_DIM)
        new_index.add(vectors)
        _chunks = [_chunks[i] for i in keep_indices]
        _metadata = [_metadata[i] for i in keep_indices]
        _index = new_index

    _save_index()
    print(f"Removed document {doc_id} from FAISS index.")
    return True


def get_index():
    return _index


def get_chunks():
    return _chunks


def get_metadata():
    return _metadata
