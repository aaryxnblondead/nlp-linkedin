from __future__ import annotations

"""
Unified text generation service with provider switching (Google Gemini preferred, HF optional).

API:
    generate(question: str, contexts: list[str], max_new_tokens: int = 256) -> str

Notes:
- Reads GOOGLE_API_KEY for Google provider; model id from GEMINI_MODEL_ID.
- HF provider uses transformers locally when available and HF_MODEL_ID/HUGGINGFACE_HUB_TOKEN.
- Keep dependencies optional and fail fast with clear errors for missing providers.
"""

import os
import logging
from typing import List, Optional

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Preferred provider: Google Generative AI (Gemini)
try:
    import google.generativeai as genai  # type: ignore
except ImportError:
    genai = None  # type: ignore

# Optional fallback: Hugging Face Transformers
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM  # type: ignore
    import torch  # type: ignore
except ImportError:
    AutoTokenizer = None  # type: ignore
    AutoModelForCausalLM = None  # type: ignore
    torch = None  # type: ignore

_HF_TOKENIZER = None
_HF_MODEL = None


def build_prompt(question: str, contexts: List[str], system: Optional[str] = None) -> str:
    system = system or (
        "You are a helpful recruiter assistant. Answer the user's question based only on the provided context."
    )
    context_str = "\n".join(f"- {c.strip()}" for c in contexts if c and c.strip()) or "No context provided."
    return f"{system}\n\nContext:\n{context_str}\n\nQuestion: {question}\nAnswer:"


def _extract_google_text(resp) -> str:
    try:
        return (resp.text or "").strip()
    except Exception:
        try:
            candidate = (resp.candidates or [{}])[0]
            part = (candidate.get("content", {}).get("parts", [{}]))[0]
            return str(part.get("text", "")).strip()
        except (IndexError, AttributeError, KeyError):
            log.warning("Could not extract text from Google response: %s", resp)
            return ""


def _generate_google(question: str, contexts: List[str], max_new_tokens: int = 256) -> str:
    if genai is None:
        raise RuntimeError("google-generativeai is not installed.")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set in the environment.")

    genai.configure(api_key=api_key)
    model_id = os.getenv("GEMINI_MODEL_ID", "gemini-1.5-flash")
    log.info("Using Google Gemini model: %s", model_id)

    model = genai.GenerativeModel(model_id)
    prompt = build_prompt(question, contexts)
    try:
        resp = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_new_tokens},
            request_options={"timeout": 20},
        )
        return _extract_google_text(resp)
    except TypeError:
        # Older client without request_options
        log.warning("google-generativeai client is outdated; proceeding without request_options timeout.")
        resp = model.generate_content(prompt, generation_config={"max_output_tokens": max_new_tokens})
        return _extract_google_text(resp)


def _generate_hf(question: str, contexts: List[str], max_new_tokens: int = 256) -> str:
    global _HF_TOKENIZER, _HF_MODEL
    if not all([AutoTokenizer, AutoModelForCausalLM, torch]):
        raise RuntimeError("transformers/torch not installed for HF provider.")

    model_id = os.getenv("HF_MODEL_ID", "google/gemma-2-2b-it")
    hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
    log.info("Using Hugging Face model: %s", model_id)

    device_map = "auto"
    dtype = torch.float32
    if torch.cuda.is_available():
        if hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported():
            dtype = torch.bfloat16
        else:
            dtype = torch.float16

    if _HF_TOKENIZER is None:
        log.info("Loading HF tokenizer...")
        _HF_TOKENIZER = AutoTokenizer.from_pretrained(model_id, token=hf_token)
    if _HF_MODEL is None:
        log.info("Loading HF model (may take a moment)...")
        _HF_MODEL = AutoModelForCausalLM.from_pretrained(
            model_id,
            token=hf_token,
            torch_dtype=dtype,
            device_map=device_map,
            trust_remote_code=True,
        )

    tokenizer, model = _HF_TOKENIZER, _HF_MODEL
    messages = [
        {"role": "system", "content": "You are a helpful recruiter assistant. Answer based only on the provided context."},
        {"role": "user", "content": build_prompt(question, contexts, system="")},
    ]
    inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(input_ids=inputs, max_new_tokens=max_new_tokens)
    prompt_len = inputs.shape[-1]
    response_text = tokenizer.decode(outputs[0][prompt_len:], skip_special_tokens=True)
    return response_text.strip()


def generate(question: str, contexts: List[str], max_new_tokens: int = 256) -> str:
    """
    Generate an answer from a configured language model provider.

    Provider: GEN_PROVIDER env var: "google" (default) or "hf".
    """
    # Feature gate: allow disabling generator globally
    try:
        from app.core import config
        if not bool(getattr(config, "USE_GENERATOR", True)):
            return ""
    except Exception:
        pass

    provider = os.getenv("GEN_PROVIDER", "google").lower()
    log.info("Generation request: provider='%s'", provider)
    try:
        if provider == "google":
            return _generate_google(question, contexts, max_new_tokens)
        if provider == "hf":
            return _generate_hf(question, contexts, max_new_tokens)
        raise ValueError(f"Invalid GEN_PROVIDER: '{provider}'.")
    except Exception as e:
        log.error("Generation failed for provider '%s': %s", provider, e, exc_info=True)
        # No automatic fallback to avoid surprises; surface an empty string to callers that treat generation as optional.
        return ""
from __future__ import annotations

"""
Unified text generation service with Google Generative AI (Gemini) primary.
- Reads GOOGLE_API_KEY from environment automatically via google-generativeai.
- Optionally supports a minimal HF text-generation fallback if desired later.

Contract:
    generate(prompt: str, messages: list[dict]|list[str]) -> str | None

Notes:
- Keep dependencies minimal and encapsulated.
- Fail gracefully and return None if generation is not available.
"""

from typing import List, Optional, Any

import os


def _use_generator_enabled() -> bool:
    try:
        from app.core import config
        return bool(getattr(config, "USE_GENERATOR", True))
    except Exception:
        return True


def _provider() -> str:
    # GEN_PROVIDER: "google" (default) or "hf"
    prov = os.getenv("GEN_PROVIDER", "google").lower().strip()
    return prov if prov in {"google", "hf"} else "google"


def _generate_google(prompt: str, messages: List[Any]) -> Optional[str]:
    try:
        import google.generativeai as genai
    except Exception:
        return None
    # API key is read from env GOOGLE_API_KEY by the SDK when configured here
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        model_id = os.getenv("GENERATOR_MODEL_ID", os.getenv("GEMMA_MODEL_ID", "gemini-1.5-flash"))
        safety_settings = None
        generation_config = {
            "temperature": float(os.getenv("GEN_TEMPERATURE", "0.2")),
            "max_output_tokens": int(os.getenv("GEN_MAX_TOKENS", "1024")),
        }
        model = genai.GenerativeModel(model_id)
        # Combine messages with prompt into a single content request
        parts: List[Any] = []
        if messages:
            for m in messages:
                if isinstance(m, dict):
                    # Accept {role, content} but only content is used in this simple wrapper
                    c = m.get("content") if isinstance(m.get("content"), str) else str(m)
                    parts.append({"text": c})
                elif isinstance(m, str):
                    parts.append({"text": m})
        parts.append({"text": prompt})
        resp = model.generate_content(parts, safety_settings=safety_settings, generation_config=generation_config)
        txt = None
        if hasattr(resp, "text"):
            txt = resp.text
        elif hasattr(resp, "candidates") and resp.candidates:
            # very defensive; SDK usually exposes .text
            txt = resp.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
        return (txt or "").strip() if txt else None
    except Exception:
        return None


def _generate_hf(prompt: str, messages: List[Any]) -> Optional[str]:
    # Optional: minimal HF fallback via inference endpoints token
    # Avoid importing heavy transformers by default; implement later if needed.
    return None


def generate(prompt: str, messages: List[Any]) -> Optional[str]:
    if not _use_generator_enabled():
        return None
    prov = _provider()
    if prov == "google":
        ans = _generate_google(prompt, messages)
        if ans:
            return ans
        # fall back to HF if available
        return _generate_hf(prompt, messages)
    else:
        ans = _generate_hf(prompt, messages)
        if ans:
            return ans
        return _generate_google(prompt, messages)
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

# Optional fallback: Hugging Face Transformers
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
except ImportError:
    AutoTokenizer = None
    AutoModelForCausalLM = None
    torch = None

# --- Globals ---
_HF_TOKENIZER = None
_HF_MODEL = None


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


def _generate_google(question: str, contexts: List[str], max_new_tokens: int = 256) -> str:
    """Generates a response using Google's Generative AI."""
    if genai is None:
        raise RuntimeError("google-generativeai is not installed. Please add it to requirements.txt.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set in the environment.")

    genai.configure(api_key=api_key)
    model_id = os.getenv("GEMINI_MODEL_ID", "gemini-1.5-flash")
    log.info("Using Google Gemini model: %s", model_id)

    model = genai.GenerativeModel(model_id)
    prompt = build_prompt(question, contexts)

    try:
        # Use a timeout to prevent indefinite hangs
        resp = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_new_tokens},
            request_options={"timeout": 20},
        )
        return _extract_google_text(resp)
    except TypeError:
        # Fallback for older library versions without request_options
        log.warning("google-generativeai client is outdated. Consider upgrading for timeout support.")
        resp = model.generate_content(prompt, generation_config={"max_output_tokens": max_new_tokens})
        return _extract_google_text(resp)
    except Exception as e:
        log.error("Google Gemini generation failed: %s", e, exc_info=True)
        raise


# --- Hugging Face Implementation ---
def _generate_hf(question: str, contexts: List[str], max_new_tokens: int = 256) -> str:
    """Generates a response using a local Hugging Face transformer model."""
    global _HF_TOKENIZER, _HF_MODEL

    if not all([AutoTokenizer, AutoModelForCausalLM, torch]):
        raise RuntimeError("transformers and torch are not installed. Please add them to requirements.txt.")

    model_id = os.getenv("HF_MODEL_ID", "google/gemma-2-2b-it")
    hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
    log.info("Using Hugging Face model: %s", model_id)

    # Determine device and data type for optimal performance
    device_map = "auto"
    dtype = torch.float32
    if torch.cuda.is_available():
        if hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported():
            dtype = torch.bfloat16
        else:
            dtype = torch.float16

    # Lazy-load and cache model/tokenizer to avoid reloading on every request
    if _HF_TOKENIZER is None:
        log.info("Loading HF tokenizer for the first time...")
        _HF_TOKENIZER = AutoTokenizer.from_pretrained(model_id, token=hf_token)
    if _HF_MODEL is None:
        log.info("Loading HF model for the first time (this may take a moment)...")
        _HF_MODEL = AutoModelForCausalLM.from_pretrained(
            model_id,
            token=hf_token,
            torch_dtype=dtype,
            device_map=device_map,
            trust_remote_code=True,  # Required by some models like Gemma
        )

    tokenizer, model = _HF_TOKENIZER, _HF_MODEL

    # Format prompt using the model's chat template
    messages = [
        {"role": "system", "content": "You are a helpful recruiter assistant. Answer based only on the provided context."},
        {"role": "user", "content": build_prompt(question, contexts, system="")},
    ]
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True, return_tensors="pt"
    ).to(model.device)

    # Generate response
    with torch.no_grad():
        outputs = model.generate(input_ids=inputs, max_new_tokens=max_new_tokens)

    # Decode and return the response, skipping the prompt part
    prompt_len = inputs.shape[-1]
    response_text = tokenizer.decode(outputs[0][prompt_len:], skip_special_tokens=True)
    return response_text.strip()


# --- Main Generation Service ---
def generate(question: str, contexts: List[str], max_new_tokens: int = 256) -> str:
    """
    Generate an answer from a configured language model provider.

    The provider is determined by the `GEN_PROVIDER` environment variable.
    - "google": Uses Google Gemini.
    - "hf": Uses a local Hugging Face model.
    Defaults to "google" if not set.
    """
    provider = os.getenv("GEN_PROVIDER", "google").lower()
    log.info("Generation request received. Provider: '%s'", provider)

    try:
        if provider == "google":
            return _generate_google(question, contexts, max_new_tokens)
        elif provider == "hf":
            return _generate_hf(question, contexts, max_new_tokens)
        else:
            raise ValueError(f"Invalid GEN_PROVIDER: '{provider}'. Must be 'google' or 'hf'.")
    except Exception as e:
        log.error("Core generation failed for provider '%s'. Error: %s", provider, e, exc_info=True)
        # Fallback can be added here if desired, but for now, we fail fast.
        # Example:
        # if provider == 'google' and os.getenv("ALLOW_HF_FALLBACK") == "true":
        #     log.warning("Google failed, attempting HF fallback...")
        #     try:
        #         return _generate_hf(question, contexts, max_new_tokens)
        #     except Exception as hf_e:
        #         log.error("HF fallback also failed: %s", hf_e)
        #         raise RuntimeError("All generation providers failed.") from hf_e
        raise RuntimeError(f"Failed to generate response from provider '{provider}'.") from e