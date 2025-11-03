from typing import List, Optional
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import SecretStr
from app.core import config
import os

# Optional providers
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore
except Exception:  # pragma: no cover
    GoogleGenerativeAIEmbeddings = None  # type: ignore
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore
except Exception:  # pragma: no cover
    HuggingFaceEmbeddings = None  # type: ignore

_embeddings = None

def get_embedder():
    global _embeddings
    if _embeddings is None:
        # Offline first if requested or no Google key
        use_offline = (os.getenv("USE_OFFLINE_EMBEDDINGS", "false").lower() == "true")
        api_key = os.getenv("GOOGLE_API_KEY")
        if use_offline or not api_key or GoogleGenerativeAIEmbeddings is None:
            if HuggingFaceEmbeddings is None:
                raise RuntimeError("Offline embeddings requested but langchain-community HuggingFaceEmbeddings not available.")
            model_name = os.getenv("HF_EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            _embeddings = HuggingFaceEmbeddings(model_name=model_name)
        else:
            _embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=SecretStr(api_key))
    return _embeddings


def get_embedder_backend() -> str:
    """Return 'google' or 'offline' indicating which embedding backend is active/selected."""
    use_offline = (os.getenv("USE_OFFLINE_EMBEDDINGS", "false").lower() == "true")
    api_key = os.getenv("GOOGLE_API_KEY")
    if use_offline or not api_key or GoogleGenerativeAIEmbeddings is None:
        return "offline"
    return "google"


def get_collection_count(name: str) -> int:
    """Return count of vectors in a Chroma collection by name, 0 on error."""
    try:
        import chromadb  # type: ignore
        client = chromadb.PersistentClient(path=config.CHROMA_DIR)
        coll = client.get_or_create_collection(name)
        return int(coll.count())
    except Exception:
        return 0


def get_corpus_count() -> int:
    return get_collection_count(CORPUS_COLLECTION)


def get_namespace_count(namespace: str) -> int:
    return get_collection_count(namespace)


def chunk_texts(texts: List[str]) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks: List[str] = []
    for t in texts:
        if not t:
            continue
        chunks.extend([c.page_content for c in splitter.create_documents([t])])
    return chunks


def upsert_applicant_kb(applicant_id: int, chunks: List[str]) -> str:
    # Chroma collection names must be 3-512 chars, [a-zA-Z0-9._-], start/end alphanumeric
    namespace = f"applicant_{applicant_id}"
    embedder = get_embedder()
    Chroma.from_texts(chunks, embedder, persist_directory=config.CHROMA_DIR, collection_name=namespace)
    return namespace


def query_kb(namespace: str, question: str) -> str:
    embedder = get_embedder()
    vs = Chroma(persist_directory=config.CHROMA_DIR, collection_name=namespace, embedding_function=embedder)
    docs = vs.similarity_search(question, k=3)
    if not docs:
        return ""
    return "\n".join(d.page_content for d in docs)

def retrieve_kb_texts(namespace: str, question: str, k: int = 5) -> List[str]:
    embedder = get_embedder()
    vs = Chroma(persist_directory=config.CHROMA_DIR, collection_name=namespace, embedding_function=embedder)
    docs = vs.similarity_search(question, k=k)
    return [d.page_content for d in docs] if docs else []


# ----- Global resume corpus helpers -----
CORPUS_COLLECTION = "resume_corpus"

def upsert_corpus_chunks(chunks: List[str], metadatas: Optional[List[dict]] = None) -> str:
    embedder = get_embedder()
    # If metadatas not provided or length mismatch, ignore them
    if metadatas and len(metadatas) == len(chunks):
        Chroma.from_texts(chunks, embedder, persist_directory=config.CHROMA_DIR, collection_name=CORPUS_COLLECTION, metadatas=metadatas)
    else:
        Chroma.from_texts(chunks, embedder, persist_directory=config.CHROMA_DIR, collection_name=CORPUS_COLLECTION)
    return CORPUS_COLLECTION

def query_corpus(question: str, k: int = 5):
    embedder = get_embedder()
    vs = Chroma(persist_directory=config.CHROMA_DIR, collection_name=CORPUS_COLLECTION, embedding_function=embedder)
    return vs.similarity_search(question, k=k)

def retrieve_corpus_texts(question: str, k: int = 5) -> List[str]:
    embedder = get_embedder()
    vs = Chroma(persist_directory=config.CHROMA_DIR, collection_name=CORPUS_COLLECTION, embedding_function=embedder)
    docs = vs.similarity_search(question, k=k)
    return [d.page_content for d in docs] if docs else []

def similar_to_text(text: str, k: int = 5):
    # Similarity search using a temporary vector store call: pass the text as a query
    embedder = get_embedder()
    vs = Chroma(persist_directory=config.CHROMA_DIR, collection_name=CORPUS_COLLECTION, embedding_function=embedder)
    return vs.similarity_search(text, k=k)

def get_corpus_vs():
    embedder = get_embedder()
    return Chroma(persist_directory=config.CHROMA_DIR, collection_name=CORPUS_COLLECTION, embedding_function=embedder)

def add_corpus_texts(texts: List[str], metadatas: Optional[List[dict]] = None):
    vs = get_corpus_vs()
    vs.add_texts(texts=texts, metadatas=metadatas)

def reset_corpus_collection():
    try:
        import chromadb
        client = chromadb.PersistentClient(path=config.CHROMA_DIR)
        try:
            client.delete_collection(CORPUS_COLLECTION)
        except Exception:
            pass
    except Exception:
        # If chromadb not available or another error occurs, ignore reset.
        pass
