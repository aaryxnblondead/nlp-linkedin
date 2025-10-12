import os
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.worker.tasks.processing_pipeline import process_applicant_pipeline
from app.models.applicant import Applicant, Resume, LinkedInProfile, Insights
from app.db import SessionLocal
from app.api.v1.endpoints.deps import get_current_user, require_role
from app.services.storage import get_storage_service
from app.models.user import User, UserRole
from app.services.embeddings import similar_to_text
from app.worker.tasks.intelligence_engine import generate_candidate_insights
from fastapi import Body

router = APIRouter()
@router.get("/me/applicant")
def get_my_applicant(current_user=Depends(require_role(UserRole.applicant))):
    db = SessionLocal()
    try:
        # First try by explicit link
        app = db.query(Applicant).filter(Applicant.user_id == getattr(current_user, 'id', None)).first()
        # Fallback: attempt to bind an existing applicant to this user
        if not app:
            uname = (getattr(current_user, 'username', '') or '').strip()
            q = db.query(Applicant)
            # If username looks like an email, match by applicant.email
            if '@' in uname:
                q = q.filter(func.lower(Applicant.email) == uname.lower())
            else:
                q = q.filter(func.lower(Applicant.name).like(f"%{uname.lower()}%"))
            app_to_link = q.order_by(Applicant.created_at.desc()).first()
            
            # If we found an applicant by name/email and it has no user or an orphaned user, link it.
            if app_to_link:
                existing_user_id = getattr(app_to_link, 'user_id', None)
                if existing_user_id is None:
                     should_link = True
                else:
                    # Check if the user_id points to a non-existent user
                    linked_user_exists = db.query(User).filter(User.id == existing_user_id).count() > 0
                    should_link = not linked_user_exists

                if should_link:
                    try:
                        db.query(Applicant).filter(Applicant.id == app_to_link.id).update({'user_id': getattr(current_user, 'id', None)})
                        db.commit()
                        app = app_to_link # The applicant is now linked
                    except Exception:
                        db.rollback()
        if not app:
            return {"exists": False}
        ins = db.query(Insights).filter(Insights.applicant_id == app.id).first()
        # If insights missing or incomplete, recompute now using stored resume -> structure -> normalize
        try:
            # Recompute if insights missing, rating missing, breakdown missing,
            # or breakdown lacks education_score / has zero (to refresh after scoring logic improvements)
            subs = {}
            if ins is not None and getattr(ins, 'scoring_breakdown', None):
                subs = (getattr(ins, 'scoring_breakdown') or {}).get('subscores', {}) or {}
            ed_missing = ('education_score' not in subs)
            ed_zero = (subs.get('education_score', None) == 0)
            need_recompute = (
                (ins is None) or
                (getattr(ins, 'rating', None) is None) or
                (getattr(ins, 'scoring_breakdown', None) is None) or
                ed_missing or ed_zero
            )
            if need_recompute:
                resume = db.query(Resume).filter(Resume.applicant_id == app.id).first()
                sr = None
                if resume and getattr(resume, 'structured_data', None):
                    sr = getattr(resume, 'structured_data')
                else:
                    raw_text = getattr(resume, 'raw_text', None) if resume else None
                    if raw_text:
                        from app.worker.tasks.intelligence_engine import create_structured_resume
                        from app.services.normalize import normalize_structured_resume
                        sr = normalize_structured_resume(create_structured_resume(raw_text, {}))
                    else:
                        rp = getattr(app, 'resume_path', None)
                        if rp:
                            from app.worker.tasks.data_ingestion import process_resume_file
                            from app.worker.tasks.intelligence_engine import create_structured_resume
                            from app.services.normalize import normalize_structured_resume
                            text_now = process_resume_file(rp)
                            sr = normalize_structured_resume(create_structured_resume(text_now, {}))
                if sr is not None:
                    gen = generate_candidate_insights(sr)
                    if ins is None:
                        ins = Insights(applicant_id=app.id)
                        db.add(ins)
                        db.flush()
                    db.query(Insights).filter(Insights.id == ins.id).update({
                        Insights.rating: gen.get('rating'),
                        Insights.summary: gen.get('summary'),
                        Insights.sentiment_score: gen.get('sentiment_score'),
                        Insights.activity_score: gen.get('activity_score'),
                        Insights.top_endorsed_skills: gen.get('top_endorsed_skills'),
                        Insights.projects: gen.get('projects'),
                        Insights.experience_years: gen.get('experience_years'),
                        Insights.scoring_breakdown: gen.get('scoring_breakdown'),
                    })
                    try:
                        db.query(Applicant).filter(Applicant.id == app.id).update({Applicant.status: "processed"})
                    except Exception:
                        pass
                    db.commit()
                    # After commit, refresh the instance to get the latest data
                    db.refresh(ins)
        except Exception:
            # non-fatal for dashboard; continue with whatever data we have
            pass
        # Compute cohort percentile by rating among applicants with overlapping summary keywords
        percentile = None
        improvements = []
        try:
            base_q = db.query(Insights).filter(Insights.rating != None)
            mine = getattr(ins, 'rating', None) if ins else None
            if mine is not None:
                total = base_q.count()
                below = base_q.filter(Insights.rating <= mine).count()
                if total > 0:
                    percentile = round((below / total) * 100)
        except Exception:
            percentile = None
        # Simple improvement tips based on insights
        if ins is not None:
            yrs = getattr(ins, 'experience_years', None)
            summ = (getattr(ins, 'summary', '') or '').lower()
            if yrs is not None and yrs < 3:
                improvements.append("Call out internships, bootcamps, and tangible projects to offset limited years.")
            if 'aws' not in summ and 'azure' not in summ and 'gcp' not in summ:
                improvements.append("Add cloud exposure (AWS/Azure/GCP) and any certifications if relevant.")
            if 'sql' not in summ and 'database' not in summ:
                improvements.append("Highlight SQL/database work with concrete outcomes.")
            if 'react' in summ and 'testing' not in summ:
                improvements.append("Mention testing frameworks (Jest/Cypress) and performance optimizations.")
            if not improvements:
                improvements.append("Include metrics (%, time saved, revenue impact) to quantify achievements.")
        
        education_score = None
        if ins and getattr(ins, 'scoring_breakdown', None):
            education_score = (ins.scoring_breakdown or {}).get('subscores', {}).get('education_score', 0)

        return {
            "exists": True,
            "applicant": {
                "id": app.id,
                "name": app.name,
                "email": app.email,
                "linkedin_url": app.linkedin_url,
                "status": getattr(app, 'status', None),
            },
            "insights": {
                "rating": getattr(ins, 'rating', None) if ins else None,
                "summary": getattr(ins, 'summary', None) if ins else None,
                "experience_years": getattr(ins, 'experience_years', None) if ins else None,
                "education_score": education_score,
            },
            "percentile": percentile,
            "improvements": improvements,
        }
    finally:
        db.close()



@router.post("/applicants/")
def submit_applicant(
    name: str = Form(...),
    email: str = Form(...),
    linkedin_url: str = Form(...),
    resume: UploadFile = File(...),
    current_user=Depends(require_role(UserRole.applicant)),
):
    db = SessionLocal()
    # Save file to disk
    save_dir = "uploaded_resumes"
    os.makedirs(save_dir, exist_ok=True)
    if not resume.filename:
        raise HTTPException(status_code=400, detail="Invalid resume filename")
    storage = get_storage_service()
    file_bytes = resume.file.read()
    saved_path, _ = storage.save(file_bytes, resume.filename)
    # Create applicant
    applicant = Applicant(name=name, email=email, resume_path=saved_path, linkedin_url=linkedin_url)
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    # Try to link to current user if the column exists
    try:
        db.query(Applicant).filter(Applicant.id == applicant.id).update({Applicant.user_id: getattr(current_user, 'id', None)})
        db.commit()
    except Exception:
        db.rollback()
    # Enqueue async processing
    try:
        process_applicant_pipeline.delay(applicant.id, saved_path, linkedin_url)
    except Exception:
        # Fallback to sync if Celery not running
        process_applicant_pipeline(applicant.id, saved_path, linkedin_url)
    db.close()
    return {"status": "submitted", "applicant_id": applicant.id}

@router.get("/applicants/{applicant_id}")
def get_applicant(applicant_id: int, current_user=Depends(get_current_user)):
    db = SessionLocal()
    applicant = db.query(Applicant).filter(Applicant.id == applicant_id).first()
    if not applicant:
        db.close()
        raise HTTPException(status_code=404, detail="Applicant not found")
    resume = db.query(Resume).filter(Resume.applicant_id == applicant_id).first()
    linkedin = db.query(LinkedInProfile).filter(LinkedInProfile.applicant_id == applicant_id).first()
    insights = db.query(Insights).filter(Insights.applicant_id == applicant_id).first()
    # Derive education_score from stored scoring_breakdown if available
    education_score = None
    if insights and getattr(insights, 'scoring_breakdown', None):
        education_score = (insights.scoring_breakdown or {}).get('subscores', {}).get('education_score', 0)
    db.close()
    return {
        "id": applicant.id,
        "name": applicant.name,
        "email": applicant.email,
        "linkedin_url": applicant.linkedin_url,
        "status": getattr(applicant, "status", None),
        "resume": {
            "raw_text": resume.raw_text if resume else None,
            "structured_data": resume.structured_data if resume else None,
        },
        "linkedin": linkedin.profile_data if linkedin else None,
        "insights": {
            "rating": insights.rating if insights else None,
            "summary": insights.summary if insights else None,
            "experience_years": getattr(insights, "experience_years", None) if insights else None,
            "sentiment_score": getattr(insights, "sentiment_score", None) if insights else None,
            "activity_score": getattr(insights, "activity_score", None) if insights else None,
            "top_endorsed_skills": getattr(insights, "top_endorsed_skills", None) if insights else None,
            "projects": getattr(insights, "projects", None) if insights else None,
            # New: provide education_score expected by frontend SummaryCell
            "education_score": education_score,
        },
    }

@router.post("/applicants/{applicant_id}/reprocess")
def reprocess_applicant(applicant_id: int, current_user=Depends(require_role(UserRole.recruiter))):
    """Re-run the full pipeline (resume parse, LinkedIn scrape, insights, embeddings) for this applicant."""
    db = SessionLocal()
    try:
        app = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Applicant not found")
        try:
            db.query(Applicant).filter(Applicant.id == applicant_id).update({Applicant.status: "processing"})
            db.commit()
        except Exception:
            db.rollback()
        try:
            process_applicant_pipeline.delay(applicant_id, getattr(app, 'resume_path', ''), getattr(app, 'linkedin_url', ''))
            return {"status": "queued"}
        except Exception:
            # Fallback to synchronous run if Celery is not running
            ok = process_applicant_pipeline(applicant_id, getattr(app, 'resume_path', ''), getattr(app, 'linkedin_url', ''))
            return {"status": "done" if ok else "failed"}
    finally:
        db.close()

@router.post("/applicants/{applicant_id}/linkedin/import")
def import_linkedin_json(applicant_id: int, payload: dict = Body(...), current_user=Depends(require_role(UserRole.recruiter))):
    """Accept LinkedIn profile JSON pasted by a user and regenerate insights and KB."""
    db = SessionLocal()
    try:
        app = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Applicant not found")
        resume = db.query(Resume).filter(Resume.applicant_id == applicant_id).first()
        # Merge new LinkedIn JSON into structured resume and recompute insights
        raw_text = getattr(resume, 'raw_text', '') if resume else ''
        from app.worker.tasks.intelligence_engine import create_structured_resume
        structured = create_structured_resume(raw_text, payload)
        insights = generate_candidate_insights(structured)
        # Update DB records using update() to appease static typing
        if resume:
            db.query(Resume).filter(Resume.id == resume.id).update({
                Resume.structured_data: structured
            })
        else:
            db.add(Resume(applicant_id=applicant_id, raw_text=raw_text, structured_data=structured))
        li = db.query(LinkedInProfile).filter(LinkedInProfile.applicant_id == applicant_id).first()
        if li:
            db.query(LinkedInProfile).filter(LinkedInProfile.id == li.id).update({
                LinkedInProfile.profile_data: payload
            })
        else:
            db.add(LinkedInProfile(applicant_id=applicant_id, profile_data=payload))
        ins = db.query(Insights).filter(Insights.applicant_id == applicant_id).first()
        if not ins:
            ins = Insights(applicant_id=applicant_id)
            db.add(ins)
            db.flush()
        db.query(Insights).filter(Insights.id == ins.id).update({
            Insights.rating: insights.get('rating'),
            Insights.summary: insights.get('summary'),
            Insights.sentiment_score: insights.get('sentiment_score'),
            Insights.activity_score: insights.get('activity_score'),
            Insights.top_endorsed_skills: insights.get('top_endorsed_skills'),
            Insights.projects: insights.get('projects'),
            Insights.experience_years: insights.get('experience_years'),
            Insights.scoring_breakdown: insights.get('scoring_breakdown'),
        })
        # Update embeddings KB
        from app.services.embeddings import chunk_texts, upsert_applicant_kb, add_corpus_texts
        # Include a compact insights doc in addition to raw/structured/profile blobs
        insights_doc = ''
        safe_texts = [raw_text or '', str(payload), str(structured), insights_doc or '']
        chunks = chunk_texts(safe_texts)
        namespace = upsert_applicant_kb(applicant_id, chunks)
        db.query(Insights).filter(Insights.id == ins.id).update({Insights.kb_namespace: namespace})
        try:
            metas = [{"source": app.resume_path, "applicant_id": applicant_id, "kind": "resume_or_structured_or_insights"} for _ in chunks]
            add_corpus_texts(chunks, metas)
        except Exception:
            pass
        db.commit()
        return {"status": "imported"}
    finally:
        db.close()

@router.post("/applicants/{applicant_id}/linkedin/scrape_test")
def test_scrape_linkedin(applicant_id: int, current_user=Depends(get_current_user)):
    """Trigger a LinkedIn scrape for this applicant and return the raw JSON for testing.
    Recruiters can run this for any applicant; applicants can only run it for themselves.
    Requires env vars LINKEDIN_EMAIL and LINKEDIN_PASSWORD.
    """
    db = SessionLocal()
    try:
        app = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Applicant not found")
        role = getattr(current_user, 'role', None)
        user_id = getattr(current_user, 'id', None)
        if role == UserRole.recruiter:
            pass
        elif role == UserRole.applicant:
            if getattr(app, 'user_id', None) != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to test scrape for this applicant")
        else:
            raise HTTPException(status_code=403, detail="Not authorized")

        from app.worker.tasks.data_ingestion import scrape_linkedin_profile
        data = scrape_linkedin_profile(getattr(app, 'linkedin_url', '') or '')
        return {"ok": True, "data": data}
    finally:
        db.close()

@router.get("/applicants/")
def get_all_applicants(
    search: str = Query(""),
    min_exp: int = Query(0, ge=0),
    min_rating: int = Query(-2, ge=-2, le=2),
    skills: str = Query(""),
    current_user=Depends(require_role(UserRole.recruiter)),
):
    db = SessionLocal()
    try:
        q = db.query(Applicant).outerjoin(Insights, Applicant.id == Insights.applicant_id)
        if search:
            s = f"%{search.lower()}%"
            q = q.filter(
                func.lower(Applicant.name).like(s) |
                func.lower(Applicant.email).like(s) |
                func.lower(Applicant.linkedin_url).like(s) |
                func.lower(Insights.summary).like(s)
            )
        if min_exp:
            q = q.filter((Insights.experience_years != None) & (Insights.experience_years >= min_exp))
        if min_rating is not None:
            q = q.filter((Insights.rating != None) & (Insights.rating >= min_rating))
        rows = q.order_by(Applicant.created_at.desc()).all()
        wanted_skills_list = [s.strip().lower() for s in skills.split(',') if s.strip()]
        results: List[dict] = []
        for app in rows:
            ins = db.query(Insights).filter(Insights.applicant_id == app.id).first()
            # Extract education_score from stored breakdown if present
            ed_score = None
            if ins and getattr(ins, 'scoring_breakdown', None):
                ed_score = (ins.scoring_breakdown or {}).get('subscores', {}).get('education_score', 0)
            if len(wanted_skills_list) > 0 and ins is not None and getattr(ins, "summary", None):
                text = (getattr(ins, "summary", "") or "").lower()
                if not all(w in text for w in wanted_skills_list):
                    continue
            results.append({
                "id": app.id,
                "name": app.name,
                "email": app.email,
                "linkedin_url": app.linkedin_url,
                "status": getattr(app, "status", None),
                "insights": {
                    "rating": getattr(ins, "rating", None) if ins else None,
                    "summary": getattr(ins, "summary", None) if ins else None,
                    "experience_years": getattr(ins, "experience_years", None) if ins else None,
                    "sentiment_score": getattr(ins, "sentiment_score", None) if ins else None,
                    "activity_score": getattr(ins, "activity_score", None) if ins else None,
                    "top_endorsed_skills": getattr(ins, "top_endorsed_skills", None) if ins else None,
                    "projects": getattr(ins, "projects", None) if ins else None,
                    # New: include education_score for SummaryCell meters in list view
                    "education_score": ed_score,
                }
            })
        return results
    finally:
        db.close()


@router.get("/applicants/{applicant_id}/similar")
def similar_applicants(applicant_id: int, current_user=Depends(require_role(UserRole.recruiter))):
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.applicant_id == applicant_id).first()
        if resume is None:
            raise HTTPException(status_code=404, detail="Applicant resume not found")
        parts = []
        if getattr(resume, "raw_text", None):
            parts.append(getattr(resume, "raw_text"))
        if getattr(resume, "structured_data", None) is not None:
            parts.append(str(getattr(resume, "structured_data")))
        if not parts:
            return []
        sims = similar_to_text("\n".join(parts), k=5)
        out = []
        for d in sims:
            out.append({
                "snippet": d.page_content,
                "source": (getattr(d, 'metadata', {}) or {}).get('source')
            })
        return out
    finally:
        db.close()


@router.get("/applicants/{applicant_id}/scoring_breakdown")
def get_scoring_breakdown(applicant_id: int, current_user=Depends(get_current_user)):
    """Return clean scoring breakdown for an applicant for the frontend.
    Shape: {
      rating, rating_label, experience_years,
      breakdown: { weights, subscores }
    }
    """
    db = SessionLocal()
    try:
        applicant = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        if not applicant:
            raise HTTPException(status_code=404, detail="Applicant not found")
        # Authorization: recruiters can view any; applicants can view only their own applicant
        role = getattr(current_user, 'role', None)
        user_id = getattr(current_user, 'id', None)
        if role == UserRole.recruiter:
            pass
        elif role == UserRole.applicant:
            if getattr(applicant, 'user_id', None) != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to view this applicant")
        else:
            raise HTTPException(status_code=403, detail="Not authorized")
        insights = db.query(Insights).filter(Insights.applicant_id == applicant_id).first()
        resume = db.query(Resume).filter(Resume.applicant_id == applicant_id).first()

        breakdown = getattr(insights, "scoring_breakdown", None) if insights else None
        rating = getattr(insights, "rating", None) if insights else None
        rating_label = None
        experience_years = getattr(insights, "experience_years", None) if insights else None

        # Fallback: recompute from available data and persist if possible
        if not breakdown:
            try:
                sr = None
                # 1) Prefer existing structured_data
                if resume and getattr(resume, "structured_data", None):
                    sr = getattr(resume, "structured_data")
                else:
                    # 2) If we have raw_text, structure it now (leverages improved NER + normalization)
                    raw_text = getattr(resume, "raw_text", None) if resume else None
                    if raw_text:
                        from app.worker.tasks.intelligence_engine import create_structured_resume
                        from app.services.normalize import normalize_structured_resume
                        sr = normalize_structured_resume(create_structured_resume(raw_text, {}))
                    else:
                        # 3) As a last resort, re-parse the saved file path
                        rp = getattr(applicant, 'resume_path', None)
                        if rp:
                            from app.worker.tasks.data_ingestion import process_resume_file
                            from app.worker.tasks.intelligence_engine import create_structured_resume
                            from app.services.normalize import normalize_structured_resume
                            text_now = process_resume_file(rp)
                            sr = normalize_structured_resume(create_structured_resume(text_now, {}))

                if sr is not None:
                    gen = generate_candidate_insights(sr)
                    breakdown = gen.get("scoring_breakdown")
                    rating = gen.get("rating")
                    rating_label = gen.get("rating_label")
                    experience_years = gen.get("experience_years")

                    # Persist insights if missing or stale
                    if insights is None:
                        insights = Insights(applicant_id=applicant_id)
                        db.add(insights)
                        db.flush()
                    db.query(Insights).filter(Insights.id == insights.id).update({
                        Insights.rating: rating,
                        Insights.summary: gen.get("summary"),
                        Insights.sentiment_score: gen.get("sentiment_score"),
                        Insights.activity_score: gen.get("activity_score"),
                        Insights.top_endorsed_skills: gen.get("top_endorsed_skills"),
                        Insights.projects: gen.get("projects"),
                        Insights.experience_years: experience_years,
                        Insights.scoring_breakdown: breakdown,
                    })
                    try:
                        db.query(Applicant).filter(Applicant.id == applicant_id).update({Applicant.status: "processed"})
                    except Exception:
                        pass
                    db.commit()
            except Exception:
                # Leave breakdown as None; will handle below
                pass

        # If we still don't have a rating label, derive a simple label
        if rating_label is None and rating is not None:
            if rating >= 90:
                rating_label = "Outstanding"
            elif rating >= 75:
                rating_label = "Strong"
            elif rating >= 60:
                rating_label = "Good"
            elif rating >= 40:
                rating_label = "Fair"
            else:
                rating_label = "Needs improvement"

        if not insights and not breakdown:
            # As a final fallback, do not 404 — return an empty breakdown so the UI can render gracefully
            return {
                "rating": rating,
                "rating_label": rating_label,
                "experience_years": experience_years,
                "breakdown": breakdown or {},
            }

        return {
            "rating": rating,
            "rating_label": rating_label,
            "experience_years": experience_years,
            "breakdown": breakdown or {},
        }
    finally:
        db.close()
