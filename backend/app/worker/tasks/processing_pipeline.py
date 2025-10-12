from app.worker.tasks.data_ingestion import process_resume_file, scrape_linkedin_profile
from app.worker.tasks.intelligence_engine import create_structured_resume, generate_candidate_insights
from app.services.normalize import normalize_structured_resume
from app.models.applicant import Applicant, Resume, LinkedInProfile, Insights
from app.db import SessionLocal
from app.worker.celery_app import celery_app

@celery_app.task
def process_applicant_pipeline(applicant_id, resume_path, linkedin_url):
    db = SessionLocal()
    try:
        # mark processing
        app = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        try:
            db.query(Applicant).filter(Applicant.id == applicant_id).update({Applicant.status: "processing"})
            db.commit()
        except Exception:
            pass
            db.commit()

        # Step 1: Parse resume
        resume_text = process_resume_file(resume_path)
        # Step 2: Optionally scrape LinkedIn (disabled by default)
        from app.core import config
        linkedin_data = {}
        if getattr(config, 'USE_LINKEDIN_SCRAPE', False) and linkedin_url:
            try:
                linkedin_data = scrape_linkedin_profile(linkedin_url) or {}
            except Exception:
                linkedin_data = {"error": "scrape_disabled_or_failed"}
        # Step 3: Structure resume (ignores LinkedIn per policy)
        structured_resume = create_structured_resume(resume_text, linkedin_data)
        # Step 3.0: Normalize and enrich structured fields (skills canonicalization, name/org casing, email casing)
        try:
            structured_resume = normalize_structured_resume(structured_resume)
        except Exception:
            pass
        # Step 3.1: Update Applicant name/email. Replace placeholder filename-like names.
        try:
            sr_name = (structured_resume.get("name") or "").strip()
            sr_email = (structured_resume.get("email") or "").strip()
            updates = {}
            current_name = str(getattr(app, "name", "") or "").strip() if app else ""
            current_email = str(getattr(app, "email", "") or "").strip() if app else ""
            def looks_like_filename(n: str) -> bool:
                nlow = (n or "").lower()
                if any(x in nlow for x in ["resume", "cv", "_", "-", ".doc", ".pdf", ".docx"]):
                    return True
                if any(ch.isdigit() for ch in nlow):
                    return True
                return False
            if app and sr_name and (not current_name or looks_like_filename(current_name)):
                updates[Applicant.name] = sr_name
            if app and (not current_email) and sr_email:
                updates[Applicant.email] = sr_email
            if updates:
                db.query(Applicant).filter(Applicant.id == applicant_id).update(updates)
                db.commit()
        except Exception:
            # Non-fatal; continue pipeline even if update fails
            db.rollback()
        # Step 4: Generate insights
        insights = generate_candidate_insights(structured_resume)

        # Step 6: Save to DB
        resume = Resume(applicant_id=applicant_id, raw_text=resume_text, structured_data=structured_resume)
        # Optionally persist LinkedIn profile only if scraping enabled and we got meaningful data
        linkedin = None
        if getattr(config, 'USE_LINKEDIN_SCRAPE', False) and linkedin_data and isinstance(linkedin_data, dict) and not linkedin_data.get('error'):
            linkedin = LinkedInProfile(applicant_id=applicant_id, profile_data=linkedin_data)
        insight = Insights(
            applicant_id=applicant_id,
            rating=insights.get("rating"),
            summary=insights.get("summary"),
            sentiment_score=insights.get("sentiment_score"),
            activity_score=insights.get("activity_score"),
            top_endorsed_skills=insights.get("top_endorsed_skills"),
            projects=insights.get("projects"),
            experience_years=insights.get("experience_years"),
            consistency_flags=insights.get("consistency_flags"),
        )
        db.add(resume)
        if linkedin is not None:
            db.add(linkedin)
        db.add(insight)
        try:
            db.query(Applicant).filter(Applicant.id == applicant_id).update({Applicant.status: "processed"})
        except Exception:
            pass
        db.commit()
        return True
    except Exception:
        try:
            db.query(Applicant).filter(Applicant.id == applicant_id).update({Applicant.status: "failed"})
            db.commit()
        except Exception:
            pass
            db.commit()
        raise
    finally:
        db.close()
