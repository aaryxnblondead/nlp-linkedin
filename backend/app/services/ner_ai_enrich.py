from __future__ import annotations

from typing import Dict, List, Any
import json


LABELS = [
    "SKILL",
    "TITLE",
    "ORG",
    "GPE",
    "EDU_DEGREE",
    "EDU_FIELD",
]


def _prompt_for_classification(snippets: List[str]) -> str:
    items = "\n".join(f"- {s}" for s in snippets)
    labels = ", ".join(LABELS)
    return (
        "You are helping extract entities from resume text. "
        "For each line below, choose the best label from the set: " + labels + ".\n"
        "Return a single compact JSON object where each key is the original line "
        "and each value is one of the labels above. If unsure, omit that line.\n\n"
        f"Lines:\n{items}\n\nJSON:"
    )


def classify_snippets(snippets: List[str]) -> Dict[str, str]:
    """Classify small snippets to labels via LLM. Safe no-op if generator unavailable.

    Returns mapping {snippet: label} for a subset of inputs.
    """
    out: Dict[str, str] = {}
    if not snippets:
        return out
    try:
        from app.core import config
        if not getattr(config, "USE_LLM_NER_ENRICH", False):
            return out
    except Exception:
        return out

    try:
        from app.services.generation import generate
        uniq = list(dict.fromkeys([s.strip() for s in snippets if s and s.strip()]))
        # Limit batch size
        from app.core import config
        limit = int(getattr(config, "NER_ENRICH_MAX_SNIPPETS", 40) or 40)
        batch = uniq[:limit]
        if not batch:
            return out
        prompt = _prompt_for_classification(batch)
        resp = generate(prompt, [])
        if not resp:
            return out
        data = json.loads(resp)
        for k, v in data.items():
            ks = str(k).strip()
            vs = str(v).strip().upper()
            if ks and vs in LABELS:
                out[ks] = vs
    except Exception:
        return {}
    return out
