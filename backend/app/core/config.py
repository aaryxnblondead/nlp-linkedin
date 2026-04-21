import os

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV in {"prod", "production"}
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _resolve_backend_path(env_value: str | None, default_rel: str) -> str:
    """Resolve relative paths against backend root and normalize legacy prefixes."""
    raw = (env_value or default_rel or "").strip()
    if not raw:
        raw = default_rel
    if os.path.isabs(raw):
        return raw

    normalized = raw.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    # Backward compatibility for old values like "backend/data/skills_dynamic.json"
    if normalized.startswith("backend/"):
        normalized = normalized[len("backend/"):]
    return os.path.join(BACKEND_ROOT, normalized)

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "12345678")
POSTGRES_DB = os.getenv("POSTGRES_DB", "qualifyai")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    # Heroku-style URLs still appear in some environments.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

# Feature flags / integrations
USE_FIREBASE = os.getenv("USE_FIREBASE", "false").lower() == "true"

# Firebase configuration (used if USE_FIREBASE=true)
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")

# Scraper engine selection
SCRAPER_ENGINE = os.getenv("SCRAPER_ENGINE", "selenium")  # or "playwright"
USE_LINKEDIN_SCRAPE = os.getenv("USE_LINKEDIN_SCRAPE", "false").lower() == "true"

# ChromaDB configuration
CHROMA_DIR = _resolve_backend_path(os.getenv("CHROMA_DIR"), "chroma_db")

# Text generation (Gemma/LLM) configuration — default ON to favor LLM answers
USE_GENERATOR = os.getenv("USE_GENERATOR", "true").lower() == "true"
# Grounded mode: when true, chatbot answers only from available data (DB/KB/Corpus);
# LLM may paraphrase provided context but must not invent answers when no context is available.
CHAT_GROUNDED_ONLY = os.getenv("CHAT_GROUNDED_ONLY", "true").lower() == "true"
# Default to Gemma 2 2B IT; can be overridden
GENERATOR_MODEL_ID = os.getenv("GEMMA_MODEL_ID", os.getenv("GENERATOR_MODEL_ID", "google/gemma-2-2b-it"))

# NLP/NER/LLM assist flags
USE_LLM_NAME = os.getenv("USE_LLM_NAME", "true").lower() == "true"  # Enable LLM for name extraction
USE_LLM_SKILLS_ENRICH = os.getenv("USE_LLM_SKILLS_ENRICH", "false").lower() == "true"
USE_LLM_SCORING = os.getenv("USE_LLM_SCORING", "false").lower() == "true"
USE_LLM_NER_ENRICH = os.getenv("USE_LLM_NER_ENRICH", "false").lower() == "true"

# Dynamic skills dictionary path
SKILLS_DYNAMIC_PATH = _resolve_backend_path(
    os.getenv("SKILLS_DYNAMIC_PATH"),
    os.path.join("data", "skills_dynamic.json"),
)

# Optional: default NER enrichment labels and limits
NER_ENRICH_MAX_SNIPPETS = int(os.getenv("NER_ENRICH_MAX_SNIPPETS", "40"))
NER_ENRICH_MODEL_ID = os.getenv("NER_ENRICH_MODEL_ID", os.getenv("GENERATOR_MODEL_ID", "gemini-1.5-flash"))
