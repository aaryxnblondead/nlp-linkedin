from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
try:
	from dotenv import load_dotenv, find_dotenv
	env_path = find_dotenv(usecwd=True)
	if env_path:
		load_dotenv(env_path)
	else:
		load_dotenv()
except Exception:
	pass

from app.api.v1.endpoints import applicants
from app.api.v1.endpoints import auth
from app.core import config as _cfg
from app.services.embeddings import get_embedder_backend, get_corpus_count, get_namespace_count


app = FastAPI()

# Allow CORS for frontend (more permissive for local dev)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").strip()
extra_origins_env = os.getenv("EXTRA_CORS_ORIGINS", "").strip()
extra_origins = [o.strip() for o in extra_origins_env.split(",") if o.strip()] if extra_origins_env else []
default_dev_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
origins = list({frontend_origin, *default_dev_origins, *extra_origins})
cors_regex = os.getenv("CORS_ORIGIN_REGEX")
app.add_middleware(
	CORSMiddleware,
	allow_origins=origins if not cors_regex else [],
	allow_origin_regex=cors_regex if cors_regex else None,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"]
)

# Optional: Add a root endpoint for health check
@app.get("/")
def root():
	return {"status": "ok"}

@app.get("/api/v1/health")
def health():
	# Basic feature flags and DB URL redaction check
	backend = get_embedder_backend()
	grounded = bool(getattr(_cfg, 'CHAT_GROUNDED_ONLY', True))
	use_gen = bool(getattr(_cfg, 'USE_GENERATOR', True))
	corpus = get_corpus_count()
	return {
		"ok": True,
		"embedder": backend,
		"generator": use_gen,
		"grounded_only": grounded,
		"corpus_docs": corpus,
	}

app.include_router(applicants.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")

# Optional: lightweight RAG diagnostics
@app.get("/api/v1/rag/status")
def rag_status(applicant_id: int | None = None):
	ns_count = None
	if applicant_id is not None:
		ns = f"applicant_{applicant_id}"
		try:
			ns_count = get_namespace_count(ns)
		except Exception:
			ns_count = None
	return {
		"embedder": get_embedder_backend(),
		"corpus_docs": get_corpus_count(),
		"applicant_kb_docs": ns_count,
	}
