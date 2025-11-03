from __future__ import annotations
import os
import logging
from typing import List, Optional

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- Provider Imports ---

# Preferred provider: Google Generative AI (Gemini)
try:
    import google.generativeai as genai
except ImportError:
    genai = None


# --- Globals ---
_GOOGLE_MODEL_ID: Optional[str] = None


# --- Prompt Engineering ---
def build_prompt(question: str, contexts: List[str], system: Optional[str] = None) -> str:
    """Builds a structured prompt for the language model."""
    system = system or "You are a helpful recruiter assistant. Answer the user's question based *only* on the context provided. Be concise and professional."
    context_str = "\n".join(f"- {c.strip()}" for c in contexts if c and c.strip())
    if not context_str:
        context_str = "No context provided."
    return f"{system}\n\nContext:\n{context_str}\n\nQuestion: {question}\nAnswer:"


# --- Google Gemini Implementation ---
def _extract_google_text(resp) -> str:
    """Safely extracts text from various Google AI response formats."""
    try:
        return resp.text.strip()
    except Exception:
        try:
            candidate = (resp.candidates or [{}])[0]
            part = (candidate.get("content", {}).get("parts", [{}]))[0]
            return part.get("text", "").strip()
        except (IndexError, AttributeError, KeyError):
            log.warning("Could not extract text from Google response: %s", resp)
            return ""


def _select_google_model_id() -> str:
    """
    Hardcoded to use the user-specified model.
    """
    return "gemini-flash-lite-latest"


def _generate_google(question: str, contexts: List[str], max_new_tokens: int = 256) -> str:
    """Generates a response using Google's Generative AI."""
    if genai is None:
        raise RuntimeError("google-generativeai is not installed. Please add it to requirements.txt.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set in the environment.")

    genai.configure(api_key=api_key)
    global _GOOGLE_MODEL_ID
    if not _GOOGLE_MODEL_ID:
        _GOOGLE_MODEL_ID = _select_google_model_id()
    model_id = _GOOGLE_MODEL_ID
    log.info("Using Google Gemini model: %s", model_id)

    model = genai.GenerativeModel(model_id)
    prompt = build_prompt(question, contexts)

    try:
        # Use a timeout to prevent indefinite hangs
        resp = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_new_tokens},
            request_options={"timeout": 60},
        )
        return _extract_google_text(resp)
    except Exception as e:
        log.error("Google Gemini generation failed: %s", e, exc_info=True)
        raise


# --- Main Generation Service ---
def generate(question: str, contexts: List[str], max_new_tokens: int = 256) -> str:
    """
    Generate an answer using the Google Gemini language model.
    """
    log.info("Generation request received. Provider: 'google'")

    try:
        return _generate_google(question, contexts, max_new_tokens)
    except Exception as e:
        log.error("Core generation failed for provider 'google'. Error: %s", e, exc_info=True)
    # Fail soft: return empty string so optional callers can proceed without hard crashes
    return ""