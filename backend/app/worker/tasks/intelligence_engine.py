# Module B: Intelligence Engine
from typing import List, Dict, Any, Tuple
import re
from app.services.ner import extract_resume_entities
import os

def create_structured_resume(resume_text, linkedin_data):
    # Use robust NER service (spaCy + regex) to extract candidate entities
    entities = extract_resume_entities(resume_text or "")
    structured = {
        "name": entities.get("name"),
        "email": entities.get("email"),
        "phone": entities.get("phone"),
        "linkedin": entities.get("linkedin"),
        "skills": entities.get("skills", []),
        "locations": entities.get("locations", []),
        "organizations": entities.get("organizations", []),
        "titles": entities.get("titles", []),
        "dates": entities.get("dates", []),
        "education": entities.get("education", []),
        "experience": entities.get("experience", []),
        "raw_text": entities.get("raw_text", resume_text),
    }
    # Preserve only safe LinkedIn signals we can score against
    linkedin_snapshot = {
        "posts": list((linkedin_data or {}).get("posts", []) or []),
        "activity_timestamps": list((linkedin_data or {}).get("activity_timestamps", []) or []),
    }
    structured["linkedin"] = linkedin_snapshot
    return structured

def analyze_text_sentiment(text: str) -> float:
    # Prefer ML-based VADER if available; otherwise fallback to keyword balance
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
        vs = SentimentIntensityAnalyzer()
        s = vs.polarity_scores(text or "")
        # compound is in [-1, 1]
        return float(max(-1.0, min(1.0, s.get('compound', 0.0))))
    except Exception:
        text_l = (text or "").lower()
        pos = sum(text_l.count(w) for w in ["led", "achieved", "improved", "optimized", "success", "delivered", "designed", "built"])
        neg = sum(text_l.count(w) for w in ["failed", "issue", "bug", "problem", "error", "delay", "blocked"])
        total = max(1, pos + neg)
        score = (pos - neg) / total
        return max(-1.0, min(1.0, score))

def compute_activity_score_from_resume(text: str) -> float:
    # Very naive proxy from resume: counts of recent years imply activity
    import datetime
    year = datetime.datetime.now(datetime.UTC).year
    recent_hits = 0
    for y in range(year-2, year+1):
        recent_hits += (text or "").count(str(y))
    return max(0.0, min(1.0, recent_hits / 6.0))


def compute_activity_score(structured_resume: Dict[str, Any]) -> float:
    """Blend LinkedIn activity timestamps with resume heuristics."""
    import datetime

    data = structured_resume.get("linkedin") or {}
    timestamps = data.get("activity_timestamps") or []
    if timestamps:
        recent_count = 0
        now = datetime.datetime.now(datetime.UTC)
        horizon = now - datetime.timedelta(days=60)
        for ts in timestamps:
            try:
                dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                try:
                    dt = datetime.datetime.strptime(ts, "%Y-%m-%d")
                    dt = dt.replace(tzinfo=datetime.UTC)
                except Exception:
                    continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.UTC)
            if dt >= horizon:
                recent_count += 1
        # 8+ recent activities saturate the score, 0 if none
        if recent_count:
            return max(0.0, min(1.0, recent_count / 8.0))
    # Fallback to resume-based proxy
    return compute_activity_score_from_resume(structured_resume.get("raw_text") or "")

def extract_endorsed_skills(_profile: Dict[str, Any]) -> List[str]:
    # LinkedIn endorsements disabled; return empty
    return []

def extract_projects(_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    # LinkedIn projects disabled; return empty
    return []

def _parse_date_token(tok: str) -> Tuple[int, int] | None:
    # Returns (year, month) or None
    if not tok:
        return None
    tok = tok.strip()
    months = {
        'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'sept':9,'oct':10,'nov':11,'dec':12
    }
    m = re.match(r"(?i)^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+(\d{4})$", tok)
    if m:
        return int(m.group(2)), months[m.group(1).lower()]
    y = re.match(r"^(\d{4})$", tok)
    if y:
        return int(y.group(1)), 6
    if re.match(r"(?i)^(present|current)$", tok):
        import datetime
        now = datetime.datetime.now(datetime.UTC)
        return now.year, now.month
    return None

def estimate_experience_years(structured_resume: Dict[str, Any]) -> int:
    # Prefer computing from extracted experience date ranges, merging overlaps and excluding internships
    exp = structured_resume.get("experience") or []
    spans: List[Tuple[Tuple[int,int], Tuple[int,int]]] = []
    for e in exp:
        title = (str(e.get("title") or "").lower())
        if any(k in title for k in ["intern", "internship", "trainee"]):
            continue  # exclude internships
        s = _parse_date_token(str(e.get("start") or ""))
        t = _parse_date_token(str(e.get("end") or ""))
        if s and t:
            # normalize order
            if (t[0] < s[0]) or (t[0] == s[0] and t[1] < s[1]):
                s, t = t, s
            spans.append((s, t))
    # Merge overlapping spans
    if spans:
        spans.sort(key=lambda x: (x[0][0], x[0][1]))
        merged: List[Tuple[Tuple[int,int], Tuple[int,int]]] = []
        cur_s, cur_t = spans[0]
        for s, t in spans[1:]:
            # if s <= cur_t (month compare)
            if (s[0] < cur_t[0]) or (s[0] == cur_t[0] and s[1] <= cur_t[1]):
                # extend if t is later
                if (t[0] > cur_t[0]) or (t[0] == cur_t[0] and t[1] > cur_t[1]):
                    cur_t = t
            else:
                merged.append((cur_s, cur_t))
                cur_s, cur_t = s, t
        merged.append((cur_s, cur_t))
        total_months = 0
        for (sy, sm), (ey, em) in merged:
            months = (ey - sy) * 12 + (em - sm)
            if months > 0:
                total_months += months
        return max(0, min(40, round(total_months / 12)))
    # Fallback: parse from raw text patterns like "X years"
    text = structured_resume.get("raw_text") or ""
    m = re.search(r"(\d{1,2})\s+years", text.lower())
    if m:
        try:
            return max(0, min(40, int(m.group(1))))
        except Exception:
            pass
    jobs = re.findall(r"\b(\d{4})\b", text)
    years = len(set(jobs)) // 2
    return max(0, min(40, years))

def _skill_depth_and_breadth(skills: List[str]) -> Tuple[int, int]:
    if not skills:
        return 0, 0
    sset = {s.lower().strip() for s in skills if s}
    breadth = len(sset)
    advanced = {
        'kubernetes','terraform','pytorch','tensorflow','spark','airflow','kafka','kotlin','scala','rust',
        'opentelemetry','prometheus','grafana','elasticsearch','snowflake','databricks','gcp','aws','azure'
    }
    depth = len(sset & advanced)
    return breadth, depth

def _project_quality_from_resume(text: str) -> float:
    """Heuristic score 0..1 based on action verbs and quantified outcomes in resume text."""
    t = (text or "").lower()
    verbs = ["built","led","designed","implemented","optimized","deployed","architected","migrated","automated"]
    outcomes = ["%","percent","x","times","reduced","increased","decreased","improved","latency","throughput","cost","reliability"]
    v_hits = sum(t.count(v) for v in verbs)
    o_hits = sum(t.count(w) for w in outcomes)
    # normalize: cap at reasonable counts
    v_norm = min(1.0, v_hits / 12.0)
    o_norm = min(1.0, o_hits / 10.0)
    return max(0.0, min(1.0, 0.6 * v_norm + 0.4 * o_norm))

def _ownership_keywords_score(text: str) -> float:
    t = (text or "").lower()
    kws = ["led","owned","ownership","spearheaded","drove","architected","delivered","initiated","managed","mentored","orchestrated","championed"]
    hits = sum(t.count(k) for k in kws)
    return max(0.0, min(1.0, hits / 12.0))

def analyze_confidence_tone(text: str) -> float:
    """Return 0..1 confidence/ownership tone.
    Uses Gemini via our generate() service to estimate positivity; falls back to ownership keywords.
    """
    return _ownership_keywords_score(text)

def _extract_project_bullets(text: str) -> List[str]:
    """Extract bullet-like lines that likely describe projects."""
    lines = (text or "").splitlines()
    picks: List[str] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        lower = s.lower()
        if s.startswith(("-", "*", "•", "•")) or ("project" in lower) or any(v in lower for v in ["built","designed","implemented","optimized","migrated","deployed","architected"]):
            picks.append(s)
    # Deduplicate and limit
    seen = set()
    out = []
    for p in picks:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= 40:
            break
    return out

def _metrics_boost(line: str) -> float:
    """Score 0..1 for explicit metrics like percentages, multipliers, or time deltas indicating outcomes."""
    l = (line or "").lower()
    score = 0.0
    # Percent improvements
    import re
    if re.search(r"\b(\d{1,3})\s?%\b|\bpercent\b", l):
        score += 0.5
    # Multipliers like 2x, 3x
    if re.search(r"\b(\d+)x\b", l):
        score += 0.3
    # Time deltas with improvement verbs
    if re.search(r"\b(reduc|decreas|cut|improv|optimiz)\w*\b", l) and re.search(r"\b(weeks?|months?|days?)\b", l):
        score += 0.3
    # Cost/reliability/latency specific
    if re.search(r"\b(cost|latency|throughput|reliability|p95|p99)\b", l):
        score += 0.2
    return max(0.0, min(1.0, score))

def _seniority_score(titles: List[str]) -> float:
    if not titles:
        return 0.0
    t = "|".join([str(x).lower() for x in titles])
    score = 0.0
    if re.search(r"\b(principal|staff|architect|head|director)\b", t):
        score = 1.0
    elif re.search(r"\b(senior|lead|manager|tech lead|engineering manager)\b", t):
        score = 0.7
    elif re.search(r"\b(mid|software engineer|developer)\b", t):
        score = 0.45
    elif re.search(r"\b(intern|junior|entry)\b", t):
        score = 0.2
    return score

def _education_score(education: List[Dict[str, Any]]) -> float:
    if not education:
        return 0.0
    best = 0.0
    top_insts = re.compile(r"\b(MIT|Stanford|Carnegie Mellon|IIT|NIT|Berkeley|Oxford|Cambridge)\b", re.I)
    for e in education:
        deg = (e.get("degree") or "").lower()
        inst = str(e.get("institution") or "")
        base = 0.0
        if any(k in deg for k in ["phd","doctor","ph.d"]):
            base = 1.0
        elif any(k in deg for k in ["m.s","msc","master","m.tech","mtech"]):
            base = 0.8
        elif any(k in deg for k in ["b.s","bsc","bachelor","b.tech","btech", "b.e.", "bachelor of engineering"]):
            base = 0.6
        elif deg:
            base = 0.4
        if top_insts.search(inst):
            base = min(1.0, base + 0.1)
        best = max(best, base)
    return best

def _role_weight_profile(role: str | None) -> Dict[str, float] | None:
    if not role:
        return None
    r = role.lower()
    # Example role profiles; weights sum to 1 when used
    if r in ("ml engineer", "data scientist", "ai engineer"):
        return {"experience": 0.22, "seniority": 0.12, "skills": 0.30, "education": 0.12, "activity": 0.07, "sentiment": 0.10, "eproj": 0.07, "consistency": 0.00}
    if r in ("frontend", "frontend engineer", "react"):
        return {"experience": 0.20, "seniority": 0.10, "skills": 0.30, "education": 0.05, "activity": 0.15, "sentiment": 0.10, "eproj": 0.05, "consistency": 0.05}
    if r in ("devops", "sre", "platform"):
        return {"experience": 0.25, "seniority": 0.15, "skills": 0.25, "education": 0.05, "activity": 0.10, "sentiment": 0.10, "eproj": 0.05, "consistency": 0.05}
    return None


def generate_candidate_insights(structured_resume: Dict[str, Any], role: str | None = None, weights_override: Dict[str, float] | None = None):
    skills = structured_resume.get("skills", [])
    titles = structured_resume.get("titles", [])
    education = structured_resume.get("education", [])
    resume_text = str(structured_resume.get("raw_text") or "")
    linkedin_snapshot = structured_resume.get("linkedin") or {}
    linkedin_posts = [str(p) for p in (linkedin_snapshot.get("posts") or []) if p]
    sentiment_source = resume_text
    if linkedin_posts:
        sentiment_source = f"{resume_text}\n" + "\n".join(linkedin_posts)
    sentiment = analyze_text_sentiment(sentiment_source)
    activity = compute_activity_score(structured_resume)
    confidence_tone = analyze_confidence_tone(resume_text)
    experience_years = estimate_experience_years(structured_resume)

    consistency_flags: List[str] = []

    breadth, depth = _skill_depth_and_breadth(skills)
    skills_score = min(1.0, (min(breadth, 15) / 15.0) * 0.6 + (min(depth, 10) / 10.0) * 0.4)
    experience_score = min(1.0, experience_years / 12.0)
    seniority_score = _seniority_score(titles)
    education_score = _education_score(education)
    sentiment_score_norm = (sentiment + 1.0) / 2.0
    endorsements: List[str] = []
    projects = _extract_project_bullets(resume_text)
    pq_text = _project_quality_from_resume(resume_text)
    if projects:
        metrics_scores = [_metrics_boost(line) for line in projects]
        metrics_avg = sum(metrics_scores) / len(metrics_scores)
    else:
        metrics_avg = 0.0
    endorsements_projects_score = max(0.0, min(1.0, 0.5 * pq_text + 0.3 * metrics_avg + 0.2 * confidence_tone))

    base_weights = {
        "experience": 0.30,
        "seniority": 0.15,
        "skills": 0.25,
        "education": 0.10,
        "activity": 0.08,
        "sentiment": 0.12,
        "eproj": 0.12,
        "consistency": 0.00,
    }
    role_weights = base_weights.copy()
    rp = _role_weight_profile(role)
    if rp:
        role_weights.update(rp)
    if weights_override:
        role_weights.update(weights_override)

    penalty = 0.0

    def _weighted_sum(weights: Dict[str, float]) -> float:
        return (
            experience_score * weights["experience"] +
            seniority_score * weights["seniority"] +
            skills_score * weights["skills"] +
            education_score * weights["education"] +
            activity * weights["activity"] +
            sentiment_score_norm * weights["sentiment"] +
            endorsements_projects_score * weights["eproj"]
        )

    base_sum = _weighted_sum(base_weights)
    weighted_sum = _weighted_sum(role_weights)
    if rp or weights_override:
        weighted_sum = max(weighted_sum, base_sum - 0.05)

    resilience_bonus = 0.0
    if skills_score >= 0.7 and (experience_score >= 0.6 or seniority_score >= 0.7):
        resilience_bonus = 0.08

    overall = max(0.0, weighted_sum - penalty * role_weights["consistency"]) + resilience_bonus
    overall = max(0.0, min(1.0, overall)) * 100.0
    rating_int = int(round(min(100.0, max(0.0, overall))))

    if rating_int >= 90:
        rating_label = "Outstanding"
    elif rating_int >= 75:
        rating_label = "Strong"
    elif rating_int >= 60:
        rating_label = "Good"
    elif rating_int >= 40:
        rating_label = "Fair"
    else:
        rating_label = "Needs improvement"

    summary_bullets = [
        f"Skills ({breadth}/{depth}): {', '.join(skills[:10])}",
        f"Experience: {experience_years} years (non-overlapping, internships excluded)",
        f"Seniority: {rating_label}",
        f"Education score: {education_score:.2f}",
        f"Resume sentiment: {sentiment:.2f}",
        f"Project quality (resume): {endorsements_projects_score:.2f}",
        f"Confidence tone: {confidence_tone:.2f}",
        f"Recent activity (blended): {activity:.2f}",
    ]
    summary = " | ".join(summary_bullets)

    breakdown = {
        "weights": role_weights,
        "subscores": {
            "experience_score": round(experience_score, 3),
            "seniority_score": round(seniority_score, 3),
            "skills_score": round(skills_score, 3),
            "education_score": round(education_score, 3),
            "activity_score": round(activity, 3),
            "sentiment_score_norm": round(sentiment_score_norm, 3),
            "endorsements_projects_score": round(endorsements_projects_score, 3),
            "penalty": round(penalty, 3),
            "resilience_bonus": round(resilience_bonus, 3),
        },
    }

    return {
        "rating": rating_int,
        "rating_label": rating_label,
        "summary": summary,
        "sentiment_score": float(sentiment),
        "activity_score": float(activity),
        "experience_years": int(experience_years),
        "consistency_flags": consistency_flags,
        "top_endorsed_skills": endorsements,
        "projects": projects,
        "scoring_breakdown": breakdown,
    }