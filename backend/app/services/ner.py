"""
NER service: spaCy + targeted regex/rules for resumes.

Contract:
- extract_resume_entities(text: str) -> dict with keys:
  - name: str | None
  - email: str | None
  - phone: str | None
  - linkedin: str | None
  - skills: List[str]
  - locations: List[str]
  - organizations: List[str]
  - titles: List[str]
  - dates: List[str]
  - education: List[dict] (degree, field, institution, start, end)
  - experience: List[dict] (title, company, location, start, end, snippet)

Design notes:
- Tries spaCy `en_core_web_sm`; falls back to a lightweight blank('en') + EntityRuler
- Uses PhraseMatcher for skills & titles; regex for email/phone/linkedin/dates
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple, Set
import os
import re
import csv
import json

try:
    import spacy
    from spacy.matcher import PhraseMatcher
    from spacy.pipeline import EntityRuler
except Exception:  # pragma: no cover
    spacy = None
    PhraseMatcher = None
    EntityRuler = None

_NLP = None  # lazy-loaded spaCy model
_SKILL_MATCHER = None
_TITLE_MATCHER = None
_INSTITUTION_DB_LOADED = False
_INSTITUTION_NAMES: Set[str] = set()
_INSTITUTION_CANONICAL: Dict[str, str] = {}
_INSTITUTION_PREFIX_INDEX: Dict[str, List[str]] = {}


SKILLS_DB = [
    # Programming languages
    "python", "java", "c", "c++", "c#", "go", "golang", "rust", "ruby", "php", "scala", "kotlin",
    # Data/ML
    "sql", "mysql", "postgresql", "mongodb", "pandas", "numpy", "scikit-learn", "sklearn", "pytorch", "tensorflow",
    "nlp", "computer vision", "deep learning", "machine learning", "data analysis", "etl",
    # Web/Backend
    "javascript", "typescript", "node", "nodejs", "express", "react", "angular", "vue", "next.js", "nextjs", "django", "flask", "fastapi",
    # Java stack extras
    "spring", "spring boot", "spring mvc", "hibernate", "jpa", "jsp", "servlet",
    # DevOps/Cloud
    "docker", "kubernetes", "helm", "terraform", "ansible", "jenkins", "git", "github actions",
    "aws", "azure", "gcp", "cloudwatch", "lambda", "s3", "ec2",
    # OS / Platform
    "linux", "red hat", "redhat", "red hat linux",
    # Other
    "spark", "hadoop", "airflow", "kafka", "snowflake", "databricks", "tableau", "power bi",
    # Cloud/data extras
    "redshift", "bigquery", "athena", "glue", "emr", "lake formation", "looker",
    # Testing/QA
    "pytest", "unittest", "cypress", "playwright",
    # Messaging/queues
    "rabbitmq", "sqs", "pubsub",
    # Infra/observability
    "prometheus", "grafana", "opentelemetry", "elk", "elasticsearch", "logstash", "kibana",
    # Mobile / Hybrid
    "react native", "flutter", "swift", "kotlin", "ionic", "ionic 3",
    # Security
    "owasp", "burp suite", "metasploit", "nessus", "siem", "splunk", "crowdstrike", "wazuh", "okta", "auth0", "iam",
    # Analytics/BI
    "powerbi", "power bi", "looker studio", "qlik", "superset",
    # Data engineering extras
    "dbt", "airbyte", "fivetran", "delta lake", "iceberg", "hudi",
    # Frontend extras
    "redux", "zustand", "vite", "webpack", "babel",
    # Backend extras
    "spring", "spring boot", "hibernate", "asp.net", ".net core", "laravel", "symfony", "rails",
    # MLOps/Observability
    "mlflow", "tensorboard", "wandb", "seldon", "bentoml", "ray", "ray serve",
    # Messaging extras
    "nats", "mqtt",
    # Data/Stat tooling
    "sas", "proc freq", "proc sql",
    # Misc
    "grpc", "rest", "graphQL", "graphql", "openapi", "swagger",
]

# Normalize SKILLS_DB: remove exact duplicates while preserving order.
# Matching elsewhere lower-cases items, so we use lower-casing to detect duplicates
# but preserve the original token casing/format for display.
_sk_seen = set()
_sk_list = []
for _sk in SKILLS_DB:
    if not _sk:
        continue
    k = _sk.strip()
    if not k:
        continue
    kl = k.lower()
    if kl in _sk_seen:
        continue
    _sk_seen.add(kl)
    _sk_list.append(k)
SKILLS_DB = _sk_list

TITLES_DB = [
    "software engineer", "senior software engineer", "staff software engineer", "principal engineer",
    "data scientist", "senior data scientist", "machine learning engineer", "ml engineer",
    "data engineer", "devops engineer", "site reliability engineer", "sre",
    "product manager", "product owner", "project manager", "program manager", "business analyst", "qa engineer", "test engineer",
    "frontend engineer", "backend engineer", "full stack engineer", "full-stack engineer", "intern", "analyst",
    "data analyst", "research scientist", "solutions architect", "cloud architect", "engineering manager",
    "technical lead", "tech lead", "principal software engineer", "ai engineer", "mlops engineer",
    # Security
    "security engineer", "application security engineer", "soc analyst", "security analyst", "devsecops engineer",
    # Data platform
    "analytics engineer", "data platform engineer",
    # QA variants
    "quality assurance engineer", "sdet", "software development engineer in test",
    # Infra/SRE variants
    "platform engineer", "infrastructure engineer",
]

# Normalize TITLES_DB: remove exact duplicates while preserving order
_t_seen = set()
_t_list = []
for _t in TITLES_DB:
    if not _t:
        continue
    tt = _t.strip()
    if not tt:
        continue
    tl = tt.lower()
    if tl in _t_seen:
        continue
    _t_seen.add(tl)
    _t_list.append(tt)
TITLES_DB = _t_list

# Post-filters to reduce false positives
ORG_STOPWORDS = {
    "computer science", "information technology", "curriculum vitae", "resume", "summary",
}
LOC_STOPWORDS = {
    "remote", "onsite", "hybrid",
}

# Words/phrases that strongly indicate a non-name heading or label near the top of resumes
NAME_HEADING_STOP = {
    "mobile", "mobile no", "phone", "email", "curriculum vitae", "resume", "cv", "profile",
    "product demos", "skills", "technical skills", "education", "experience", "projects", "resume",
    "summary", "objective", "visa status", "java", "html5", "html", "python", "aws", "sas", "azure", 
}

# Explicit role/title phrases that often appear at top and should not be misclassified as names
JOB_TITLE_STOPWORDS = {
    "software engineer", "senior software engineer", "staff software engineer", "principal engineer",
    "team lead", "technical lead", "tech lead", "engineering manager", "project manager", "program manager",
    "data scientist", "data engineer", "ml engineer", "sde", "sdet", "qa engineer",
    "di developer", "actimize ifm", "actimize", "infotech", "sas", "flat", "files", "UI", "web", "web dev", " Project Manager", "Sr Java Developer", "Project Schedule", "Business System Analyst", 
}

# Degree words and tokens that should never be mistaken for names
DEGREE_WORDS = {
    "degree", "bcom", "b.com", "bsc", "b.sc", "ba", "b.a", "be", "b.e", "btech", "b.tech",
    "mcom", "m.com", "msc", "m.sc", "ma", "m.a", "me", "m.e", "mtech", "m.tech", "mba", "phd", "ba", "bachelor", "master", "doctorate", "profile"
}

# Tokens that, if included, make a line implausible as a name
NAME_TECH_NOISE = set([
    "linux", "red", "hat", "redhat", "spring", "hibernate", "jpa", "jsp", "servlet", "proc", "freq",
    "sql", "python", "java", "django", "flask", "react", "node", "kubernetes", "aws", "azure", "gcp", "SAS", "Flat", "Files", "Infotech", "cloud", "cloud watch", "java", "azure", "aws"
])

DEGREE_PATTERNS = r"\b((b\.?s\.?|bsc|ba|be|b\.e\.|beng|b\.eng|bca|m\.?s\.?|msc|ma|me|m\.e\.|meng|m\.eng|mca|m\.?tech|mtech|b\.?tech|btech|ph\.?d\.?|phd|bachelor|master|doctorate)([^\n\r,)]{0,40})?)\b"
INSTITUTION_HINT = r"\b(university|college|institute|school|polytechnic|iit|nit|state|tech)\b"
UNI_COLLEGE_PATTERN = r"\b[A-Z][A-Za-z&\-\.\s]{1,80}(University|College|Institute|School|Polytechnic)\b"
IIT_NIT_PATTERN = r"\b(?:IIT|NIT)\s+[A-Z][A-Za-z\-\s]{1,50}\b"


def _project_root() -> str:
    # This file is backend/app/services/ner.py → go up three levels to repo root
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def _norm_inst_name(s: str) -> str:
    s = (s or "").strip()
    # Normalize whitespace, punctuation, and case; keep ampersands and '.' out
    s = re.sub(r"[\u2018\u2019\u201C\u201D]", "'", s)  # fancy quotes → '
    s = re.sub(r"[\.,]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


def _index_institution_name(canon: str) -> None:
    """Index a canonical institution name for fast prefix filtering."""
    n = _norm_inst_name(canon)
    if not n:
        return
    _INSTITUTION_NAMES.add(n)
    _INSTITUTION_CANONICAL[n] = canon.strip()
    first = n.split(" ")[0]
    if first:
        _INSTITUTION_PREFIX_INDEX.setdefault(first, []).append(n)


def _load_institution_db() -> None:
    global _INSTITUTION_DB_LOADED
    if _INSTITUTION_DB_LOADED:
        return
    base = os.getenv("INSTITUTION_CSV_DIR") or _project_root()
    candidates = [
        os.path.join(base, "University-ALL UNIVERSITIES.csv"),
        os.path.join(base, "College-ALL COLLEGE.csv"),
        os.path.join(base, "Standalone-ALL STANDALONE.csv"),
    ]
    for fp in candidates:
        try:
            if not os.path.exists(fp):
                continue
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                # Use csv.reader to detect the true header row
                rdr = csv.reader(f)
                rows = list(rdr)
                if not rows:
                    continue
                header_idx = None
                for idx, row in enumerate(rows[:20]):  # search first 20 lines for header
                    line = ",".join(row)
                    if re.search(r"\b(Name|University Name)\b", line, flags=re.IGNORECASE):
                        header_idx = idx
                        break
                if header_idx is None:
                    # fallback: assume first non-empty row is header
                    for idx, row in enumerate(rows):
                        if any(cell.strip() for cell in row):
                            header_idx = idx
                            break
                if header_idx is None:
                    continue
                headers = [h.strip() for h in rows[header_idx]]
                # Map of header name lower to index
                hmap = { (h or "").strip().lower(): i for i, h in enumerate(headers) }
                # Candidate name columns in priority
                name_candidates = [
                    "name",
                    "university name",
                    "university",
                    "college name",
                    "institution name",
                    "institute name",
                ]
                name_col_idx = None
                for key in name_candidates:
                    if key in hmap:
                        name_col_idx = hmap[key]
                        break
                # If still not found, attempt heuristic: choose the column with 'college' or 'university' in header
                if name_col_idx is None:
                    for k, i in hmap.items():
                        if any(t in k for t in ["college", "university", "institute", "institution", "school"]):
                            name_col_idx = i
                            break
                # Iterate data rows after header
                for row in rows[header_idx+1:]:
                    if not row or all(not (c and c.strip()) for c in row):
                        continue
                    # Skip preface/banners
                    if name_col_idx is None:
                        # Try to pick a likely cell (first non-code value)
                        cells = [c.strip() for c in row if c and c.strip()]
                        if not cells:
                            continue
                        candidate = None
                        for c in cells:
                            if re.match(r"^[A-Z]-?\d+", c):  # code like C-xxxx or U-xxxx
                                continue
                            candidate = c
                            break
                        name_val = candidate
                    else:
                        name_val = row[name_col_idx].strip() if name_col_idx < len(row) and row[name_col_idx] else None
                    if not name_val:
                        continue
                    if re.match(r"^(ALL\s+|\(As on Date:)", name_val, flags=re.IGNORECASE):
                        continue
                    _index_institution_name(name_val)
        except Exception:
            # Non-fatal: continue with what we could load
            continue
    _INSTITUTION_DB_LOADED = True


def _match_institution_in_text(text: str) -> Optional[str]:
    """Try to find an institution mention in the provided text window using the CSV DB.

    Strategy:
    - Extract capitalized phrases ending with University/College/Institute/School/Polytechnic (and IIT/NIT ...)
    - Normalize and check for exact hit in our DB.
    - If not exact, restrict candidate space by first token and compute a simple token-overlap score; pick best >= 0.6.
    """
    if not text:
        return None
    _load_institution_db()
    # Extract candidates via regex, preferring phrases after prepositions like 'from', 'at', 'in', 'of'
    cands: List[str] = []
    prep = r"(?:from|at|in|of)\s+"
    pat_iitnit = re.compile(prep + r"((?:IIT|NIT)\s+[A-Z][A-Za-z\-\s]{1,50})")
    pat_uni = re.compile(prep + r"([A-Z][A-Za-z&\-\.\s]{1,120}?(?:University|College|Institute|School|Polytechnic)(?:,\s*[A-Z][A-Za-z\-\.\s]{1,40})?)")
    for m in pat_iitnit.finditer(text):
        cands.append(m.group(1))
    for m in pat_uni.finditer(text):
        cands.append(m.group(1))
    # Fallback to generic patterns if nothing captured via prepositions
    if not cands:
        for m in re.finditer(IIT_NIT_PATTERN, text):
            cands.append(m.group(0))
        for m in re.finditer(UNI_COLLEGE_PATTERN, text):
            cands.append(m.group(0))
    best_name = None
    best_score = 0.0

    def _clean_candidate_norm(s: str) -> str:
        # Remove any leading field abbreviations or trailing noise before the institution keyword
        s = s.strip()
        # If prepositions appear before the keyword, keep only the tail after the last preposition
        kw_positions = []
        for kw in (" university", " college", " institute", " school", " polytechnic"):
            i = s.find(kw)
            if i != -1:
                kw_positions.append(i)
        if kw_positions:
            cut = min(kw_positions)
            head = s[:cut]
            tail = s[cut:]
            # In head, find the last occurrence of a preposition and drop everything before it
            last_prep = max([head.rfind(p) for p in [" from ", " in ", " of ", " at "]] + [-1])
            if last_prep != -1:
                head = head[last_prep+1:]
            s = (head + tail).strip()
        # Drop leading field abbreviations
        fields_abbr = {"cse","ece","eee","me","ce","it","cs","mca","bca","mba","bba","m.com","b.com","bsc","msc"}
        toks = s.split()
        while toks and toks[0].lower().strip(".,") in fields_abbr:
            toks.pop(0)
        return " ".join(toks)
    def _expand_acronyms(tokens: Set[str]) -> Set[str]:
        tokens = set(tokens)
        if 'iit' in tokens:
            tokens |= {'indian','institute','of','technology'}
        if 'nit' in tokens:
            tokens |= {'national','institute','of','technology'}
        if 'jntu' in tokens:
            tokens |= {'jawaharlal','nehru','technological','university'}
        if 'jntuk' in tokens:
            tokens |= {'jawaharlal','nehru','technological','university','kakinada'}
        if 'jntua' in tokens:
            tokens |= {'jawaharlal','nehru','technological','university','anantapur'}
        if 'jntuh' in tokens:
            tokens |= {'jawaharlal','nehru','technological','university','hyderabad'}
        return tokens

    for cand in cands:
        norm_c = _norm_inst_name(cand)
        norm_c = _clean_candidate_norm(norm_c)
        if not norm_c:
            continue
        # Direct exact match
        if norm_c in _INSTITUTION_NAMES:
            return _INSTITUTION_CANONICAL.get(norm_c, cand.strip())
        # Prefix-restricted fuzzy match
        first = norm_c.split(" ")[0]
        pool = _INSTITUTION_PREFIX_INDEX.get(first, [])
        if not pool and len(first) > 3:
            # Try second token as backup prefix
            parts = norm_c.split()
            if len(parts) > 1:
                pool = _INSTITUTION_PREFIX_INDEX.get(parts[1], [])
        # Tokenize and expand acronyms
        cand_tokens = set(t for t in re.split(r"[^a-z]+", norm_c) if t)
        cand_tokens = _expand_acronyms(cand_tokens)
        for inst_norm in pool:
            inst_tokens = set(t for t in re.split(r"[^a-z]+", inst_norm) if t)
            if not inst_tokens:
                continue
            inter = len(cand_tokens & inst_tokens)
            union = len(cand_tokens | inst_tokens)
            j = inter / union if union else 0.0
            # Also allow containment boost (substring)
            if norm_c in inst_norm or inst_norm in norm_c:
                j = max(j, 0.9)
            if j > best_score and j >= 0.6:
                best_score = j
                best_name = _INSTITUTION_CANONICAL.get(inst_norm, inst_norm)
    return best_name


def _get_nlp():
    global _NLP, _SKILL_MATCHER, _TITLE_MATCHER
    if _NLP is not None:
        return _NLP
    if spacy is None:
        _NLP = None
        return _NLP
    # Try environment override first
    model = os.getenv("SPACY_MODEL", "en_core_web_sm")
    try:
        _NLP = spacy.load(model, disable=["lemmatizer"])  # lemmatizer not needed for NER
    except Exception:
        # Try auto-download if allowed
        allow_dl = os.getenv("ALLOW_SPACY_DOWNLOAD", "false").lower() == "true"
        if allow_dl:
            try:
                from spacy.cli.download import download as spacy_download
                spacy_download(model)  # type: ignore
                _NLP = spacy.load(model, disable=["lemmatizer"])  # retry
            except Exception:
                _NLP = spacy.blank("en")
        else:
            # Fallback: blank English + basic EntityRuler
            _NLP = spacy.blank("en")
    # Add an EntityRuler for common ORGs and schools regardless of model
    if EntityRuler:
        try:
            ruler = _NLP.add_pipe("entity_ruler", before="ner") if "ner" in _NLP.pipe_names else _NLP.add_pipe("entity_ruler")
        except Exception:
            ruler = _NLP.add_pipe("entity_ruler")
        patterns = [
            # Generic company suffixes
            {"label": "ORG", "pattern": "Inc"},
            {"label": "ORG", "pattern": "LLC"},
            {"label": "ORG", "pattern": "Ltd"},
            # Common tech companies (sample subset)
            {"label": "ORG", "pattern": "Google"},
            {"label": "ORG", "pattern": "Microsoft"},
            {"label": "ORG", "pattern": "Amazon"},
            {"label": "ORG", "pattern": "Meta"},
            {"label": "ORG", "pattern": "Apple"},
            {"label": "ORG", "pattern": "Netflix"},
            # Common universities (sample subset)
            {"label": "ORG", "pattern": "Stanford University"},
            {"label": "ORG", "pattern": "Massachusetts Institute of Technology"},
            {"label": "ORG", "pattern": "MIT"},
            {"label": "ORG", "pattern": "University of California, Berkeley"},
            {"label": "ORG", "pattern": "Carnegie Mellon University"},
            # GPE examples
            {"label": "GPE", "pattern": "United States"},
            {"label": "GPE", "pattern": "India"},
            {"label": "GPE", "pattern": "Canada"},
        ]
        # Add a light pattern for Indian educational suffixes to bias spaCy toward ORG for these
        patterns.extend([
            {"label": "ORG", "pattern": "IIT"},
            {"label": "ORG", "pattern": "NIT"},
            {"label": "ORG", "pattern": "University"},
            {"label": "ORG", "pattern": "College"},
            {"label": "ORG", "pattern": "Institute"},
            {"label": "ORG", "pattern": "Polytechnic"},
        ])
        ruler.add_patterns(patterns)
    # Build PhraseMatchers
    if PhraseMatcher is not None:
        _SKILL_MATCHER = PhraseMatcher(_NLP.vocab, attr="LOWER")
        _SKILL_MATCHER.add("SKILL", [ _NLP.make_doc(s) for s in SKILLS_DB ])
        _TITLE_MATCHER = PhraseMatcher(_NLP.vocab, attr="LOWER")
        _TITLE_MATCHER.add("TITLE", [ _NLP.make_doc(t) for t in TITLES_DB ])
    return _NLP


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or " ").strip()


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?:(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4})(?:\s*(?:x|ext\.?|#)\s*\d{1,6})?",
    re.IGNORECASE,
)
ALT_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{8,}\d")  # permissive international fallback
LINKEDIN_RE = re.compile(r"https?://(www\.)?linkedin\.com/(in|pub|profile)/[A-Za-z0-9-_/%]+", re.IGNORECASE)
DATE_RANGE_RE = re.compile(
    r"\b(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})\s*(?:-|–|to|–>)\s*(?:Present|Current|\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b",
    re.IGNORECASE,
)


def _extract_email(text: str) -> Optional[str]:
    if not text:
        return None
    # 1) Direct match
    m = EMAIL_RE.search(text)
    if m:
        return m.group(0)
    # 2) Deobfuscate common forms like "name (at) domain (dot) com" and spaced separators
    t = text
    # Replace [at]/(at)/ at /{at} → @
    t = re.sub(r"(?i)\[\s*at\s*\]|\(\s*at\s*\)|\{\s*at\s*\}|\s+at\s+|\bat\s*the\s*rate\b", "@", t)
    # Replace [dot]/(dot)/ dot /{dot} → .
    t = re.sub(r"(?i)\[\s*dot\s*\]|\(\s*dot\s*\)|\{\s*dot\s*\}|\s+dot\s+", ".", t)
    # Collapse spaces around @ and .
    t = re.sub(r"\s*([.@])\s*", r"\1", t)
    m = EMAIL_RE.search(t)
    if m:
        return m.group(0)
    # 3) Pattern: user at domain dot tld (optional dot tld2)
    pat = re.compile(r"(?i)\b([A-Za-z0-9._%+-]{1,64})\s*(?:at|\[at\]|\(at\))\s*([A-Za-z0-9.-]{1,255})\s*(?:dot|\[dot\]|\(dot\))\s*([A-Za-z]{2,15})(?:\s*(?:dot|\[dot\]|\(dot\))\s*([A-Za-z]{2,15}))?\b")
    m = pat.search(text)
    if m:
        user = m.group(1)
        domain = m.group(2)
        tld1 = m.group(3)
        tld2 = m.group(4)
        email = f"{user}@{domain}.{tld1}"
        if tld2:
            email = f"{email}.{tld2}"
        return email.lower()
    # 4) As a last attempt, look for patterns like "user@domain com" (space before TLD)
    pat2 = re.compile(r"(?i)\b([A-Za-z0-9._%+-]{1,64})\s*@\s*([A-Za-z0-9.-]{1,255})\s+([A-Za-z]{2,10})(?:\s+([A-Za-z]{2,10}))?\b")
    m = pat2.search(text)
    if m:
        user = m.group(1)
        domain = m.group(2)
        tld1 = m.group(3)
        tld2 = m.group(4)
        email = f"{user}@{domain}.{tld1}"
        if tld2:
            email = f"{email}.{tld2}"
        return email.lower()
    return None


def _extract_phone(text: str) -> Optional[str]:
    m = PHONE_RE.search(text)
    if not m:
        m = ALT_PHONE_RE.search(text)
    if not m:
        return None
    phone = m.group(0)
    # Normalize: remove non-digits except leading + and extension
    ext_m = re.search(r"(x|ext\.?|#)\s*(\d{1,6})", phone, re.IGNORECASE)
    digits = re.sub(r"[^\d+]", "", phone)
    if digits.startswith("+1") and len(digits) > 2:
        core = digits[2:]
    elif digits.startswith("+"):
        core = digits
    elif len(digits) >= 10:
        core = digits[-10:]
    else:
        core = digits
    if core.startswith("+"):
        normalized = core
    elif len(core) == 10:
        normalized = f"({core[0:3]}) {core[3:6]}-{core[6:10]}"
    else:
        normalized = core
    if ext_m:
        normalized = f"{normalized} x{ext_m.group(2)}"
    return normalized


def _extract_linkedin(text: str) -> Optional[str]:
    m = LINKEDIN_RE.search(text)
    return m.group(0) if m else None


def _email_to_name(email: str) -> Optional[str]:
    if not email or "@" not in email:
        return None
    local = email.split("@", 1)[0]
    # Remove common prefixes/suffixes and digits
    local = re.sub(r"\d+", "", local)
    parts = re.split(r"[._-]+", local)
    parts = [p for p in parts if p and p.lower() not in {"mail", "email", "gmail", "yahoo", "outlook", "hotmail"}]
    if not parts:
        return None
    # Keep 2-3 tokens at most
    cand = " ".join(parts[:3])
    cand = " ".join([w.capitalize() for w in cand.split() if w])
    if 3 <= len(cand) <= 80 and len(cand.split()) >= 2:
        return cand
    return None


def _looks_like_bad_name(line: str) -> bool:
    l = (line or "").strip().strip(":-•|")
    ll = l.lower()
    if not l:
        return True
        # Names should not contain underscores or obvious resume keywords
        if "_" in l:
            return True
        if re.search(r"\b(cv|resume)\b", ll):
            return True
    if any(w in ll for w in NAME_HEADING_STOP):
        return True
    if any(w in ll for w in JOB_TITLE_STOPWORDS):
        return True
    if any(w in ll for w in DEGREE_WORDS):
        return True
    # Obvious technology tokens present → not a name
    if any(tok in ll for tok in NAME_TECH_NOISE):
        return True
    # Single token or too many tokens
    words = [w for w in re.split(r"[^A-Za-z]+", l) if w]
    if len(words) == 1:
        return True
    if len(words) > 5:
        return True
    # All caps words or contains digits
    if re.search(r"\d", l):
        return True
    if all(w.isupper() for w in words if w):
        return True
    # Mostly lowercase or camel/techy casing → implausible
    if sum(1 for w in words if w[:1].isupper()) < max(2, len(words)-1):
        return True
    return False


def _is_plausible_name(cand: str) -> bool:
    if not cand:
        return False
    c = _norm_ws(cand)
    if _looks_like_bad_name(c):
        return False
    # Reject if contains degree words or tech noise explicitly
    cl = c.lower()
    if any(w in cl for w in DEGREE_WORDS):
        return False
    if any(w in cl for w in NAME_TECH_NOISE):
        return False
    # Require 2-4 tokens with initial caps (allow small lowercase particles)
    parts = [p for p in re.split(r"[^A-Za-z.'-]", c) if p]
    if not (2 <= len(parts) <= 4):
        return False
    small = {"de","da","del","van","von","bin","al"}
    caps_ok = 0
    for p in parts:
        if p.lower() in small:
            continue
        if p[0].isupper():
            caps_ok += 1
    if caps_ok < 2:
        return False
    return True


def _extract_name(doc, text: str) -> Optional[str]:
    # 0) Look for explicit label: "Name: ..."
    for line in (text or "").splitlines()[:20]:
        m = re.search(r"(?i)\bname\s*[:\-]\s*([A-Za-z ,.'-]{3,80})", line)
        if m:
            cand = _norm_ws(m.group(1))
            if not _looks_like_bad_name(cand):
                return cand

    lines = (text or "").splitlines()
    first_block = "\n".join(lines[:15])

    # 1) spaCy PERSON entity near top
    if doc is not None:
        best = None
        for ent in doc.ents:
            if ent.label_ == "PERSON" and ent.start_char < len(first_block) + 1:
                cand = _norm_ws(ent.text)
                if _is_plausible_name(cand) and 3 <= len(cand) <= 80:
                    best = cand
                    break
        if best:
            return best

    # 2) Heuristic top lines
    for line in lines[:8]:
        if _looks_like_bad_name(line):
            continue
        tokens = [t for t in re.split(r"[^A-Za-z'-]", line) if t]
        if 2 <= len(tokens) <= 4 and sum(1 for t in tokens if t[:1].isupper()) >= max(2, len(tokens)-1):
            cand = _norm_ws(line)
            if 3 <= len(cand) <= 80 and not EMAIL_RE.search(cand) and _is_plausible_name(cand):
                return cand

    # Note: Do not derive name from email local-part; restrict to resume text entities/lines only.

    return None


def _phrase_matches(matcher, doc) -> List[str]:
    if matcher is None or doc is None:
        return []
    seen = set()
    out = []
    for mid, start, end in matcher(doc):
        span = doc[start:end]
        key = span.text.lower()
        if key not in seen:
            seen.add(key)
            out.append(span.text)
    return out


def _collect_sections(text: str) -> Dict[str, str]:
    # Very light section splitter by headers like "SKILLS", "EXPERIENCE", etc.
    sections = {}
    current = "__root__"
    sections[current] = []
    for line in text.splitlines():
        header = line.strip().strip(":").lower()
        if re.fullmatch(r"(summary|skills?|experience|work experience|education|educational background|educational qualifications|education details|academic background|academics|projects?|certifications?)", header):
            current = header
            sections[current] = []
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _extract_skills(doc, text: str, sections: Dict[str, str]) -> List[str]:
    found = set()
    # PhraseMatcher across whole doc
    for s in _phrase_matches(_SKILL_MATCHER, doc):
        found.add(s.lower())
    # Heuristic: skills section comma/pipe-separated
    skills_text = sections.get("skills") or ""
    if skills_text:
        for tok in re.split(r"[,|\u2022\n]+", skills_text.lower()):
            t = tok.strip(r" :\-•\t")
            if not t:
                continue
            if any(t == k or t in k or k in t for k in [k.lower() for k in SKILLS_DB]):
                found.add(t)
    # Return sorted unique
    return sorted(found)


def _extract_education(doc, text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not re.search(DEGREE_PATTERNS, line, re.IGNORECASE) and not re.search(INSTITUTION_HINT, line, re.IGNORECASE):
            continue
        # Look around a window of lines for degree/institution/date
        window = " ".join(lines[max(0, i-1): i+2])
        deg_m = re.search(DEGREE_PATTERNS, window, re.IGNORECASE)
        # Institution: prefer explicit IIT/NIT forms like "IIT Delhi", else generic University/College/etc
        inst_m2 = re.search(IIT_NIT_PATTERN, window)
        inst_m1 = re.search(UNI_COLLEGE_PATTERN, window)
        inst_text = None
        if inst_m2:
            inst_text = inst_m2.group(0)
        elif inst_m1:
            inst_text = inst_m1.group(0)
        # Try CSV-backed institution DB match for higher precision/recall
        db_match = _match_institution_in_text(window)
        if db_match:
            inst_text = db_match
        date_m = DATE_RANGE_RE.search(window)
        item = {
            "degree": _norm_ws(deg_m.group(1)) if deg_m else None,
            "field": None,
            "institution": _norm_ws(inst_text) if inst_text else None,
            "start": None,
            "end": None,
        }
        if date_m:
            item["start"], item["end"] = _split_date_range(date_m.group(0))
        # Basic field extraction: things after degree like in "B.Tech in CSE"
        if item["degree"]:
            fm = re.search(r"in\s+([A-Za-z&/\-\s]{2,40})", window, re.IGNORECASE)
            if fm:
                item["field"] = _norm_ws(fm.group(1))
        if any(item.values()):
            out.append(item)
    return dedupe_dict_list(out)


def _split_date_range(r: str) -> Tuple[Optional[str], Optional[str]]:
    parts = re.split(r"\s*(?:-|–|to|–>)\s*", r, flags=re.IGNORECASE)
    if len(parts) != 2:
        return r, None
    s, e = parts
    return s.strip(), e.strip()


def _extract_experience(doc, text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    lines = [l for l in text.splitlines() if l.strip()]
    header_re = re.compile(r"^(experience|work experience|professional experience|employment history|work history)\b", re.IGNORECASE)
    nlp = _get_nlp()
    for idx, line in enumerate(lines):
        if header_re.search(line.strip()):
            continue  # skip section headers
        # Title via matcher (on the line only)
        title_found = None
        if nlp is not None and PhraseMatcher is not None and _TITLE_MATCHER is not None:
            try:
                doc_line = nlp.make_doc(line)
                matches = _TITLE_MATCHER(doc_line)
                for _, s, e in matches:
                    span = doc_line[s:e]
                    title_found = span.text
                    break
            except Exception:
                pass
        # Org and location via spaCy ORG/GPE in the same line
        org_found = None
        loc_found = None
        start, end = None, None
        snippet = line
        date_m = DATE_RANGE_RE.search(line)
        if not date_m and idx + 1 < len(lines):
            nxt = lines[idx + 1]
            if not header_re.search(nxt.strip()):
                date_m = DATE_RANGE_RE.search(nxt)
        if date_m:
            start, end = _split_date_range(date_m.group(0))
        if doc is not None:
            span_start = text.find(line)
            if span_start != -1:
                span_end = span_start + len(line)
                dl = doc.char_span(span_start, span_end)
                if dl is not None:
                    for ent in dl.ents:
                        if ent.label_ == "ORG" and not org_found:
                            org_found = ent.text
                        if ent.label_ in ("GPE", "LOC") and not loc_found:
                            loc_found = ent.text
        # Require at least a title or a company or a date to minimize noise
        if title_found or org_found or date_m:
            out.append({
                "title": _norm_ws(title_found) if title_found else None,
                "company": _norm_ws(org_found) if org_found else None,
                "location": _norm_ws(loc_found) if loc_found else None,
                "start": start,
                "end": end,
                "snippet": _norm_ws(snippet)[:300],
            })
    return dedupe_dict_list(out)


def dedupe_dict_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = tuple((k, (v.lower() if isinstance(v, str) else v)) for k, v in sorted(it.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


# ---- Local snippet classifier: spaCy -> NLTK -> heuristics -> optional LLM ----
try:
    import nltk  # type: ignore
    from nltk import word_tokenize, pos_tag, ne_chunk  # type: ignore
    _NLTK_AVAILABLE = True
except Exception:
    _NLTK_AVAILABLE = False


def _spacy_classify_one(s: str) -> str | None:
    """Use spaCy NER to classify a single snippet into one of our labels."""
    nlp = _get_nlp()
    if nlp is None or not s:
        return None
    try:
        doc = nlp(s)
        for ent in doc.ents:
            lab = ent.label_
            if lab == "ORG":
                return "ORG"
            if lab in ("GPE", "LOC"):
                return "GPE"
            if lab == "PERSON":
                # PERSON probably isn't interesting here; prefer TITLE/ORG heuristics later
                return None
    except Exception:
        return None
    return None


def _nltk_classify_one(s: str) -> str | None:
    """Basic NLTK-based NE heuristics. Best-effort only."""
    if not _NLTK_AVAILABLE or not s:
        return None
    try:
        toks = word_tokenize(s)
        tags = pos_tag(toks)
        tree = ne_chunk(tags, binary=False)
        for subtree in getattr(tree, 'subtrees', lambda: [])():
            name = getattr(subtree, 'label', lambda: None)()
            if not name:
                continue
            if name == 'GPE':
                return 'GPE'
            if name == 'ORGANIZATION' or name == 'ORGANISATION' or name == 'ORGANIZATION':
                return 'ORG'
    except Exception:
        return None
    return None


def classify_snippets(snippets: List[str]) -> Dict[str, str]:
    """Unified snippet classifier.

    Strategy (best-effort):
    1) Try spaCy entity labels (ORG/GPE)
    2) Try NLTK NE chunking (if available)
    3) Lightweight heuristics: match against skills/titles lists or keywords
    4) If config USE_LLM_NER_ENRICH is enabled, send remaining unlabeled snippets to the LLM

    Returns mapping {snippet: LABEL} for a subset of inputs.
    """
    out: Dict[str, str] = {}
    if not snippets:
        return out

    # 0) quick uniq and cleanup
    uniq = list(dict.fromkeys([s.strip() for s in snippets if s and s.strip()]))

    # 1) spaCy first
    for s in uniq:
        lab = _spacy_classify_one(s)
        if lab:
            out[s] = lab

    # 2) NLTK fallback for unlabeled
    for s in uniq:
        if s in out:
            continue
        lab = _nltk_classify_one(s)
        if lab:
            out[s] = lab

    # 3) Heuristics: match against titles/skills or detect education tokens
    skills_lower = {k.lower() for k in SKILLS_DB}
    titles_lower = {t.lower() for t in TITLES_DB}
    for s in uniq:
        if s in out:
            continue
        sl = s.lower()
        # Titles
        for t in titles_lower:
            if t and t in sl:
                out[s] = 'TITLE'
                break
        if s in out:
            continue
        # Skills
        for k in skills_lower:
            if k and (k in sl or sl in k):
                out[s] = 'SKILL'
                break
        if s in out:
            continue
        # Education cues
        if re.search(INSTITUTION_HINT, s, re.IGNORECASE) or re.search(DEGREE_PATTERNS, s, re.IGNORECASE):
            # Prefer EDU_DEGREE when degree-like, else ORG for institution hints
            if re.search(DEGREE_PATTERNS, s, re.IGNORECASE):
                out[s] = 'EDU_DEGREE'
            else:
                out[s] = 'ORG'

    # 4) Optionally call LLM for rest (respect config flag and batch size)
    remaining = [s for s in uniq if s not in out]
    if remaining:
        try:
            from app.core import config
            if not getattr(config, 'USE_LLM_NER_ENRICH', False):
                return out
            limit = int(getattr(config, 'NER_ENRICH_MAX_SNIPPETS', 40) or 40)
            batch = remaining[:limit]
        except Exception:
            return out

        try:
            from app.services.generation import generate
            # Build prompt inline similar to ner_ai_enrich
            LABELS = ["SKILL","TITLE","ORG","GPE","EDU_DEGREE","EDU_FIELD"]
            items = "\n".join(f"- {b}" for b in batch)
            labels = ", ".join(LABELS)
            prompt = (
                "You are helping extract entities from resume text. For each line below, choose the best label from the set: " + labels + ".\n"
                "Return a single compact JSON object where each key is the original line and each value is one of the labels above. If unsure, omit that line.\n\n"
                f"Lines:\n{items}\n\nJSON:"
            )
            resp = generate(prompt, [])
            if resp:
                try:
                    data = json.loads(resp)
                    for k, v in data.items():
                        ks = str(k).strip()
                        vs = str(v).strip().upper()
                        if ks and vs in LABELS:
                            out[ks] = vs
                except Exception:
                    pass
        except Exception:
            # generation unavailable or failed -> skip
            pass

    return out


def extract_resume_entities(text: str) -> Dict[str, Any]:
    text = text or ""
    nlp = _get_nlp()
    doc = nlp(text) if nlp is not None and text else None
    sections = _collect_sections(text)

    email = _extract_email(text)
    phone = _extract_phone(text)
    linkedin = _extract_linkedin(text)
    # First pass name via rules/spaCy
    name = _extract_name(doc, text)
    # Optional LLM-assisted name disambiguation (top-of-resume few lines)
    try:
        from app.core import config as _cfg
        if not name and getattr(_cfg, 'USE_LLM_NAME', False):
            snippet = "\n".join((text or "").splitlines()[:15])
            from app.services.generation import generate
            prompt = (
                "Extract the candidate's full name (only the name) from the following resume snippet. "
                "If ambiguous or missing, return an empty string.\n\nSnippet:\n" + snippet +
                "\n\nName:"
            )
            ans = generate(prompt, [])
            ans = (ans or "").strip().splitlines()[0].strip()
            if ans and not _looks_like_bad_name(ans):
                name = ans
    except Exception:
        pass

    skills = _extract_skills(doc, text, sections)
    # Normalize skills using dynamic mapping; optionally enrich with LLM
    try:
        from app.services.skills_dict import map_to_canonical, ensure_aliases_for
        canon, mapping = map_to_canonical(skills)
        skills = canon
        try:
            added = ensure_aliases_for(list(mapping.keys()))
            if added:
                skills, _ = map_to_canonical(skills)
        except Exception:
            pass
    except Exception:
        pass

    # Entities for locations/orgs/titles/dates
    locations: List[str] = []
    organizations: List[str] = []
    titles: List[str] = []
    if doc is not None:
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                locations.append(ent.text)
            elif ent.label_ == "ORG":
                organizations.append(ent.text)
        titles.extend(_phrase_matches(_TITLE_MATCHER, doc))
    dates = [m.group(0) for m in DATE_RANGE_RE.finditer(text)]

    education = _extract_education(doc, text)
    experience = _extract_experience(doc, text)

    # Post-filter organizations/locations against skills and stopwords
    skills_lower = {s.lower() for s in skills}
    def _clean_list(items: List[str], stop: set[str]) -> List[str]:
        cleaned = []
        seen = set()
        for it in items:
            t = _norm_ws(it).strip(",;:")
            tl = t.lower()
            if not t:
                continue
            if tl in skills_lower:
                continue
            if any(tl == k or tl in k or k in tl for k in (k.lower() for k in SKILLS_DB)):
                continue
            if tl in stop:
                continue
            if t.lower() in seen:
                continue
            seen.add(t.lower())
            cleaned.append(t)
        return cleaned

    organizations = _clean_list(organizations, ORG_STOPWORDS)
    locations = _clean_list(locations, LOC_STOPWORDS)

    # Optional Stage 2: AI-assisted enrichment for unrecognized text snippets
    try:
        from app.core import config as _cfg
        if getattr(_cfg, 'USE_LLM_NER_ENRICH', False):
            # Collect candidate snippets not already recognized
            def _norm(s: str) -> str:
                return _norm_ws(s).strip(',;:')

            known = set([s.lower() for s in skills]) | set([t.lower() for t in titles]) | set([o.lower() for o in organizations]) | set([l.lower() for l in locations])
            for e in education:
                for k in ("degree", "field", "institution"):
                    v = e.get(k)
                    if v:
                        known.add(str(v).lower())

            # heuristically pick phrases separated by commas/pipes/bullets/newlines
            chunks: List[str] = []
            for raw in re.split(r"[\n\r\t\|,•\u2022]+", text):
                s = _norm(raw)
                if not s or len(s) < 2 or len(s) > 80:
                    continue
                sl = s.lower()
                if sl in known:
                    continue
                if EMAIL_RE.search(s) or LINKEDIN_RE.search(s) or ALT_PHONE_RE.search(s):
                    continue
                # avoid obvious headers
                if sl in {"summary","skills","experience","education","projects","certifications","objective","profile"}:
                    continue
                # skip lines that are mostly punctuation or numeric
                if not re.search(r"[A-Za-z]", s):
                    continue
                # lightly favor capitalized phrases or multi-word tokens
                tokens = [t for t in re.split(r"[^A-Za-z0-9+#.&/-]+", s) if t]
                if len(tokens) == 1 and not tokens[0][0].isupper():
                    continue
                chunks.append(s)

            if chunks:
                ai_labels = classify_snippets(chunks)
                if ai_labels:
                    new_skills: List[str] = []
                    new_titles: List[str] = []
                    new_orgs: List[str] = []
                    new_locs: List[str] = []
                    edu_extra_deg: List[str] = []
                    edu_extra_field: List[str] = []
                    for s, lab in ai_labels.items():
                        if lab == 'SKILL':
                            new_skills.append(s)
                        elif lab == 'TITLE':
                            new_titles.append(s)
                        elif lab == 'ORG':
                            new_orgs.append(s)
                        elif lab == 'GPE':
                            new_locs.append(s)
                        elif lab == 'EDU_DEGREE':
                            edu_extra_deg.append(s)
                        elif lab == 'EDU_FIELD':
                            edu_extra_field.append(s)

                    # Merge deduped
                    def _merge_unique(dst: List[str], src: List[str]) -> List[str]:
                        seen = {d.lower() for d in dst}
                        for it in src:
                            t = _norm(it)
                            if not t:
                                continue
                            if t.lower() in seen:
                                continue
                            seen.add(t.lower())
                            dst.append(t)
                        return dst

                    if new_skills:
                        try:
                            from app.services.skills_dict import map_to_canonical
                            merged = _merge_unique(list(skills), new_skills)
                            canon, _ = map_to_canonical(merged)
                            skills = canon
                        except Exception:
                            skills = sorted(set(skills) | { _norm(s) for s in new_skills })
                    if new_titles:
                        titles = sorted(set(_merge_unique(list(titles), new_titles)))
                    if new_orgs:
                        organizations = sorted(set(_merge_unique(list(organizations), new_orgs)))
                    if new_locs:
                        locations = sorted(set(_merge_unique(list(locations), new_locs)))
                    if edu_extra_deg or edu_extra_field:
                        # Merge into last education item if fields are missing; else append minimal items
                        if not education:
                            education = []
                        if education:
                            last = education[-1]
                            if edu_extra_deg and not last.get('degree'):
                                last['degree'] = _norm(edu_extra_deg[0])
                            if edu_extra_field and not last.get('field'):
                                last['field'] = _norm(edu_extra_field[0])
                        # Append remaining if still any
                        for d in edu_extra_deg[1:] if education and education[-1].get('degree') else edu_extra_deg:
                            education.append({"degree": _norm(d), "field": None, "institution": None, "start": None, "end": None})
                        for f in edu_extra_field[1:] if education and education[-1].get('field') else edu_extra_field:
                            education.append({"degree": None, "field": _norm(f), "institution": None, "start": None, "end": None})
    except Exception:
        # swallow enrichment errors silently
        pass

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "skills": skills,
        "locations": sorted(list({_norm_ws(x) for x in locations})),
        "organizations": sorted(list({_norm_ws(x) for x in organizations})),
        "titles": sorted(list({_norm_ws(x) for x in titles})),
        "dates": sorted(list({d for d in dates})),
        "education": education,
        "experience": experience,
        "raw_text": text,
    }
