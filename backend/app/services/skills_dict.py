from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Tuple, Iterable
from app.core import config


_CACHE: Dict[str, str] | None = None  # {alias_lower: canonical}

# Built-in canonical seeds for fuzzy/substring repair. Keep small and stable.
# These are lowercase canonical labels we want to gravitate toward.
BUILTIN_CANONICALS: Tuple[str, ...] = (
    # Core langs/frameworks
    "python","java","javascript","typescript","go","rust","php","ruby","c","c++","c#",
    # Web
    "react","angular","vue","next.js","express","express.js","django","flask","fastapi","node.js",
    # Data/ML
    "sql","mysql","postgresql","mongodb","pandas","numpy","scikit-learn","pytorch","tensorflow",
    "machine learning","deep learning","natural language processing",
    # DevOps/Cloud
    "docker","kubernetes","terraform","ansible","jenkins","github actions","aws","azure","google cloud",
    # Messaging/analytics
    "kafka","spark","airflow","tableau","power bi",
)


def _ensure_store_path(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"aliases": {}}, f)


def load_store() -> Dict[str, str]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = config.SKILLS_DYNAMIC_PATH
    _ensure_store_path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        aliases = data.get("aliases", {})
        # normalize keys/values to lowercase trimmed
        store = {}
        for k, v in aliases.items():
            k2 = normalize_skill(k)
            v2 = normalize_skill(v)
            if k2 and v2:
                store[k2] = v2
        _CACHE = store
        return store
    except Exception:
        _CACHE = {}
        return _CACHE


def save_store(store: Dict[str, str]) -> None:
    path = config.SKILLS_DYNAMIC_PATH
    _ensure_store_path(path)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"aliases": store}, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def canonical_pool() -> List[str]:
    """Return the set of canonical targets we prefer, combining dynamic store values and built-ins."""
    st = load_store()
    pool = sorted(set(st.values()) | set(BUILTIN_CANONICALS))
    return pool


def normalize_skill(s: str | None) -> str:
    if not s:
        return ""
    t = s.strip().lower()
    # common punctuation and spacing normalization
    t = re.sub(r"\s+/\s+", "/", t)
    t = re.sub(r"\s+\+\s+", "+", t)
    t = re.sub(r"\s*\-\s*", "-", t)
    t = re.sub(r"\s+", " ", t)
    # canonical forms for popular frameworks/tools
    aliases = {
        "nodejs": "node.js",
        "node": "node.js",
        "reactjs": "react",
        "nextjs": "next.js",
        "expressjs": "express",
        "ts": "typescript",
        "py": "python",
        "postgres": "postgresql",
        "gcp": "google cloud",
        "aws ec2": "ec2",
        "aws s3": "s3",
        "ms sql": "sql server",
        "scikit learn": "scikit-learn",
        "sklearn": "scikit-learn",
        "tf": "tensorflow",
        "nlp": "natural language processing",
        # Common PDF/ocr first-letter drops
        "ensorflow": "tensorflow",
        "xpress": "express",
        "avascript": "javascript",
        "ypescript": "typescript",
        "ython": "python",
        "jango": "django",
        "lask": "flask",
        "ostgresql": "postgresql",
    }
    t = aliases.get(t, t)
    return t


def _first_letter_drop_repair(t: str, candidates: Iterable[str]) -> str | None:
    """If t looks like a first-letter-dropped version of any candidate c (c[1:] == t), repair to c."""
    for c in candidates:
        if len(c) > 3 and c[1:] == t:
            return c
    return None


def _substring_to_canonical(t: str, candidates: Iterable[str]) -> str | None:
    """Map tokens that are a near substring of a canonical candidate.
    Conservative: require t length >= 4, and candidate startswith(t) or endswith(t), length diff <= 2.
    Examples: 'ensorflow' -> 'tensorflow', 'xpress' -> 'express'.
    """
    if len(t) < 4:
        return None
    for c in candidates:
        if c == t:
            return c
        if abs(len(c) - len(t)) <= 2 and (c.endswith(t) or c.startswith(t)) and t in c:
            return c
    return None


def map_to_canonical(skills: List[str]) -> Tuple[List[str], Dict[str, str]]:
    """Return (canonicals, mapping). mapping is alias->canonical."""
    store = load_store()
    out = []
    mapping: Dict[str, str] = {}
    seen = set()
    # Build candidate canonical pool from dynamic store values + builtins
    canon_pool = set(store.values()) | set(BUILTIN_CANONICALS)
    for s in skills:
        ali = normalize_skill(s)
        can = store.get(ali)
        if not can:
            # Try first-letter-drop repair against canonical pool
            repaired = _first_letter_drop_repair(ali, canon_pool)
            if repaired:
                can = repaired
        if not can:
            # Try conservative substring-to-canonical mapping
            repaired = _substring_to_canonical(ali, canon_pool)
            if repaired:
                can = repaired
        if not can:
            can = ali
        if can not in seen and can:
            seen.add(can)
            out.append(can)
        mapping[ali] = can
    return out, mapping


def ensure_aliases_for(mentions: List[str]) -> Dict[str, str]:
    """Use an LLM to expand aliases for unknown mentions and persist them.

    Returns a dict of alias->canonical pairs that were proposed (may be empty).
    Controlled by USE_LLM_SKILLS_ENRICH; safe no-op if generation is unavailable.
    """
    out: Dict[str, str] = {}
    # Quick gate: feature flag
    try:
        from app.core import config as _cfg
        if not getattr(_cfg, 'USE_LLM_SKILLS_ENRICH', False):
            return out
    except Exception:
        return out

    # Determine which mentions look unknown relative to current store and canonical pool
    store = load_store()
    pool = set(canonical_pool())
    unknowns: List[str] = []
    for m in mentions:
        ali = normalize_skill(m)
        if not ali:
            continue
        if ali in store or ali in pool:
            continue
        unknowns.append(ali)
    # Nothing to do
    if not unknowns:
        return out

    # Build a compact prompt and call our generator
    try:
        from app.services.generation import generate
        # Keep prompt small; limit to top N unique unknowns
        uniq = sorted(list(dict.fromkeys(unknowns)))[:60]
        pool_list = ", ".join(sorted(list(pool))[:120])
        mentions_csv = ", ".join(uniq)
        prompt = (
            "You will receive a comma-separated list of skill mentions from resumes. "
            "Map each mention to a canonical technology/product name used by engineers. "
            "Return ONLY a compact JSON object of alias->canonical. Prefer standard labels like 'node.js', 'postgresql', 'scikit-learn', 'google cloud'. "
            "If unsure, omit the key (do not guess).\n\n"
            f"Mentions: {mentions_csv}\n"
            f"Canonical hints (partial list): {pool_list}\n"
            "Canonical mapping JSON:"
        )
        resp = generate(prompt, [])
        import json
        data = json.loads(resp) if resp else {}
        pairs: List[Tuple[str, str]] = []
        for k, v in (data or {}).items():
            ak = normalize_skill(str(k))
            cv = normalize_skill(str(v))
            if ak and cv and ak != cv:
                pairs.append((ak, cv))
                out[ak] = cv
        if pairs:
            update_aliases(pairs)
    except Exception:
        # Silent no-op on failures
        return {}
    return out


def update_aliases(pairs: List[Tuple[str, str]]) -> None:
    """Update the dynamic alias store with (alias, canonical) pairs."""
    store = load_store().copy()
    changed = False
    for alias, canon in pairs:
        a = normalize_skill(alias)
        c = normalize_skill(canon)
        if a and c and store.get(a) != c:
            store[a] = c
            changed = True
    if changed:
        save_store(store)
        # refresh cache
        global _CACHE
        _CACHE = store
