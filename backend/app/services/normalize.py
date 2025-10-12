"""
Normalization utilities for structured resume data.

Responsibilities:
- Enrich and canonicalize skills via dynamic skills_dict and optional LLM.
- Standardize email casing, trim phone, and title-case name/organizations.
- Dedupe list fields (skills, organizations, titles, locations).

Contract:
- normalize_structured_resume(structured: dict) -> dict (mutates and returns the same dict)
"""
from __future__ import annotations

from typing import Dict, Any, List, Tuple
import re


def _title_case_safe(s: str) -> str:
    """Title-case words except those that look like ALLCAPS acronyms or contain digits."""
    if not s:
        return s
    parts = re.split(r"(\s+)", s.strip())
    out: List[str] = []
    for p in parts:
        if not p or p.isspace():
            out.append(p)
            continue
        # Keep acronyms (>=2 letters all caps) as-is
        if re.fullmatch(r"[A-Z0-9&.-]{2,}", p):
            out.append(p)
            continue
        # Common suffixes often capitalized
        lowered = p.lower()
        if lowered in {"llc", "inc", "ltd", "gmbh", "plc"}:
            out.append(lowered.upper())
            continue
        out.append(p[:1].upper() + p[1:].lower())
    return "".join(out)


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items or []:
        t = (it or "").strip()
        key = t.lower()
        if not t or key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def enrich_and_normalize_skills(skills: List[str]) -> List[str]:
    """Map skills to canonical names; optionally call an LLM to learn new aliases and persist them."""
    try:
        from app.services.skills_dict import map_to_canonical, ensure_aliases_for
        canon, mapping = map_to_canonical(skills or [])
        skills_canon = canon
        # Optional: ask LLM to expand aliases for unknowns and remap
        try:
            unknowns = list((mapping or {}).keys())
            added = ensure_aliases_for(unknowns)
            if added:
                skills_canon, _ = map_to_canonical(skills_canon)
        except Exception:
            pass
        return _dedupe_preserve_order(skills_canon)
    except Exception:
        # Best-effort: lowercase and dedupe
        return _dedupe_preserve_order([s.lower() for s in (skills or [])])


def normalize_structured_resume(structured: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(structured, dict):
        return structured

    # Email lowercased
    email = structured.get("email")
    if isinstance(email, str) and email:
        structured["email"] = email.strip().lower()

    # Phone trimmed
    phone = structured.get("phone")
    if isinstance(phone, str):
        structured["phone"] = phone.strip()

    # Name/orgs title-cased
    name = structured.get("name")
    if isinstance(name, str) and name:
        structured["name"] = _title_case_safe(name)

    orgs = structured.get("organizations") or []
    if isinstance(orgs, list):
        structured["organizations"] = [_title_case_safe(str(o)) for o in orgs]

    # Skills enrichment + canonicalization
    skills = structured.get("skills") or []
    if isinstance(skills, list):
        structured["skills"] = enrich_and_normalize_skills([str(s) for s in skills])

    # Dedupe list fields
    for key in ("titles", "locations", "dates"):
        vals = structured.get(key)
        if isinstance(vals, list):
            structured[key] = _dedupe_preserve_order([str(v).strip() for v in vals])

    return structured
