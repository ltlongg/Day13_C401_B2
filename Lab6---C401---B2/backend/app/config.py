import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("BASE_URL")
JINA_API_KEY = os.getenv("JINA_API_KEY")
OPENAI_MODEL = "gpt-5.4-mini"
EMBEDDING_MODEL = "jina-embeddings-v5-text-small"
EMBEDDING_DIM = 1024
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FAISS_INDEX_DIR = os.path.join(ROOT_DIR, "data", "faiss_index")
UPLOAD_DIR = os.path.join(ROOT_DIR, "data", "uploads")
DOCUMENTS_META_PATH = os.path.join(ROOT_DIR, "data", "documents_meta.json")
RAG_TOP_K = 5
RAG_RELEVANCE_THRESHOLD = 0.5
