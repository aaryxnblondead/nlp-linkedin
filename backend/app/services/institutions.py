from __future__ import annotations

import csv
import os
import re
from typing import Dict, List, Optional, Set, Tuple

# Cache
_DB_LOADED = False
_NAMES_NORM: Set[str] = set()
_CANONICAL: Dict[str, str] = {}
_PREFIX: Dict[str, List[str]] = {}

# Files expected at repo root unless INSTITUTION_CSV_DIR is set
CSV_FILES = [
    "University-ALL UNIVERSITIES.csv",
    "College-ALL COLLEGE.csv",
    "Standalone-ALL STANDALONE.csv",
]


def _repo_root() -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    # backend/app/services -> to repo root
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[\u2018\u2019\u201C\u201D]", "'", s)
    s = re.sub(r"[\.,]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


def _index_name(canon: str) -> None:
    n = _norm(canon)
    if not n:
        return
    if n in _NAMES_NORM:
        return
    _NAMES_NORM.add(n)
    _CANONICAL[n] = canon.strip()
    first = n.split(" ")[0]
    if first:
        _PREFIX.setdefault(first, []).append(n)


def _detect_header_row(rows: List[List[str]]) -> Tuple[int, int]:
    """Return (row_index, name_column_index). Tries to find a header with 'Name'."""
    best = (-1, -1)
    for i, row in enumerate(rows[:15]):
        for j, cell in enumerate(row):
            if str(cell).strip().lower() == "name":
                return i, j
            # Try variations
            if re.fullmatch(r"college name|university name|institute name", str(cell).strip().lower()):
                best = (i, j)
    if best[0] >= 0:
        return best
    # Fallback: pick the first non-empty row and second column
    return 0, 1


def _read_csv_file(path: str) -> List[str]:
    names: List[str] = []
    if not os.path.isfile(path):
        return names
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except Exception:
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception:
            return names
    if not rows:
        return names
    hdr_idx, name_idx = _detect_header_row(rows)
    for r in rows[hdr_idx + 1:]:
        if name_idx < len(r):
            nm = str(r[name_idx]).strip()
            if nm and nm.lower() != "name":
                names.append(nm)
    return names


def load_institutions() -> None:
    global _DB_LOADED
    if _DB_LOADED:
        return
    base = os.getenv("INSTITUTION_CSV_DIR") or _repo_root()
    for fname in CSV_FILES:
        path = os.path.join(base, fname)
        for nm in _read_csv_file(path):
            _index_name(nm)
    _DB_LOADED = True


def is_institution(name: str) -> Optional[str]:
    load_institutions()
    n = _norm(name)
    if n in _NAMES_NORM:
        return _CANONICAL.get(n) or name
    return None


INST_SUFFIX_RE = re.compile(r"\b(University|College|Institute|School|Polytechnic)\b", re.I)
IIT_NIT_RE = re.compile(r"\b(?:IIT|NIT)\s+[A-Z][A-Za-z\-\s]{1,50}\b")


def _token_set(s: str) -> Set[str]:
    toks = [t for t in re.split(r"[^A-Za-z]+", s.lower()) if len(t) >= 2]
    return set(toks)


def find_institution_in_text(text: str) -> Optional[str]:
    load_institutions()
    if not text:
        return None
    cands: List[str] = []
    # Prefer after prepositions
    prep = r"(?:from|at|in|of)\s+"
    pat1 = re.compile(prep + r"([A-Z][A-Za-z&\-\.\s]{1,120}?(?:University|College|Institute|School|Polytechnic)(?:,\s*[A-Z][A-Za-z\-\.\s]{1,40})?)")
    pat2 = re.compile(prep + r"((?:IIT|NIT)\s+[A-Z][A-Za-z\-\s]{1,50})")
    for m in pat2.finditer(text):
        cands.append(m.group(1))
    for m in pat1.finditer(text):
        cands.append(m.group(1))
    # Fallback: any capitalized phrase with suffix
    if not cands:
        for m in INST_SUFFIX_RE.finditer(text):
            start = max(0, m.start() - 120)
            chunk = text[start:m.end()]
            # Grab last capitalized span ending at suffix
            m2 = re.search(r"([A-Z][A-Za-z&\-\.\s]{2,120})$", chunk)
            if m2:
                cands.append(m2.group(1))
    best_name = None
    best_score = 0.0
    for c in cands:
        c_norm = _norm(c)
        if c_norm in _NAMES_NORM:
            return _CANONICAL.get(c_norm) or c
        # restrict by prefix
        first = c_norm.split(" ")[0]
        pool = _PREFIX.get(first, []) if first in _PREFIX else list(_NAMES_NORM)
        ct = _token_set(c_norm)
        for pn in pool:
            pt = _token_set(pn)
            if not pt:
                continue
            j = len(ct & pt) / float(len(ct | pt))
            if j > best_score:
                best_score = j
                best_name = _CANONICAL.get(pn) or pn
    if best_score >= 0.6:
        return best_name
    return None
