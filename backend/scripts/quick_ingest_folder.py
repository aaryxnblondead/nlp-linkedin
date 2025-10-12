"""
Quickly ingest a folder of resumes without Celery/Redis or embeddings.
For each file, it will:
  - Create an Applicant row
  - Parse resume text (PDF/DOCX/DOC/TXT)
  - Extract name/email/skills using our NER and compute insights
  - Save Resume + Insights; update Applicant fields; mark status=processed

Usage (Windows cmd):
  cd backend
  python -m scripts.quick_ingest_folder --root "..\\real resumes" --max 100 --skip-existing
"""

import os
import sys
import argparse

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, os.pardir))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.db import SessionLocal
from app.models.applicant import Applicant, Resume, Insights
from app.worker.tasks.data_ingestion import process_resume_file
from app.worker.tasks.intelligence_engine import create_structured_resume, generate_candidate_insights
from app.services.normalize import normalize_structured_resume


def iter_resume_paths(root):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
                yield os.path.join(dirpath, fn)


def looks_like_filename(n: str) -> bool:
    nlow = (n or "").lower()
    if any(x in nlow for x in ["resume", "cv", "_", "-", ".doc", ".pdf", ".docx"]):
        return True
    if any(ch.isdigit() for ch in nlow):
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Quick folder ingest without embeddings")
    ap.add_argument("--root", default=os.path.join(PROJECT_ROOT, "real resumes"))
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()

    root = os.path.normpath(args.root)
    if not os.path.isdir(root):
        print(f"Root not found: {root}")
        return

    db = SessionLocal()
    try:
        count = 0
        created = 0
        processed = 0
        for path in iter_resume_paths(root):
            if args.max is not None and count >= args.max:
                break
            count += 1
            if args.skip_existing:
                ex = db.query(Applicant).filter(Applicant.resume_path == path).first()
                if ex:
                    continue
            placeholder = os.path.splitext(os.path.basename(path))[0]
            app = Applicant(name=placeholder, email=None, resume_path=path, linkedin_url=None)
            db.add(app)
            db.commit()
            db.refresh(app)
            created += 1

            # Parse + structure + insights
            try:
                text = process_resume_file(path)
                sr = create_structured_resume(text, {})
                sr = normalize_structured_resume(sr)
                ins = generate_candidate_insights(sr)

                # Upsert Applicant fields
                updates = {}
                sr_name = (sr.get("name") or "").strip()
                sr_email = (sr.get("email") or "").strip()
                current_name = str(getattr(app, "name", "") or "").strip()
                current_email = str(getattr(app, "email", "") or "").strip()
                if sr_name and (not current_name or looks_like_filename(current_name)):
                    updates[Applicant.name] = sr_name
                if sr_email and not current_email:
                    updates[Applicant.email] = sr_email
                if updates:
                    db.query(Applicant).filter(Applicant.id == app.id).update(updates)
                    db.commit()

                # Save resume + insights (skip embeddings)
                db.add(Resume(applicant_id=app.id, raw_text=text, structured_data=sr))
                db.add(Insights(
                    applicant_id=app.id,
                    rating=ins.get("rating"),
                    summary=ins.get("summary"),
                    experience_years=ins.get("experience_years"),
                    sentiment_score=ins.get("sentiment_score"),
                    activity_score=ins.get("activity_score"),
                    chatbot_kb={"scoring_breakdown": ins.get("scoring_breakdown")},
                ))
                db.query(Applicant).filter(Applicant.id == app.id).update({Applicant.status: "processed"})
                db.commit()
                processed += 1
            except Exception as e:
                db.rollback()
                try:
                    db.query(Applicant).filter(Applicant.id == app.id).update({Applicant.status: "failed"})
                    db.commit()
                except Exception:
                    db.rollback()
                print(f"Failed processing {path}: {e}")

        print(f"Scanned: {count} | Created: {created} | Processed: {processed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
