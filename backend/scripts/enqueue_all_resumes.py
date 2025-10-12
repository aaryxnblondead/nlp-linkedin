"""
Script: enqueue_all_resumes.py
Purpose: Create Applicant rows and push every resume into the async processing pipeline.
         This guarantees each resume is parsed, analyzed, and embedded per-applicant.

Run from backend folder.
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
from app.models.applicant import Applicant
from app.worker.tasks.processing_pipeline import process_applicant_pipeline


def iter_resume_paths(custom_roots=None):
    roots = custom_roots or [
        os.path.join(PROJECT_ROOT, "resumes", "Resumes"),
        os.path.join(PROJECT_ROOT, "resumedataset", "data", "data"),
        os.path.join(PROJECT_ROOT, "real resumes"),
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
                    yield os.path.join(dirpath, fn)


def main():
    parser = argparse.ArgumentParser(description="Enqueue all resumes into the processing pipeline")
    parser.add_argument("--max-applicants", type=int, default=None, help="Limit number of resumes to enqueue")
    parser.add_argument("--roots", nargs="*", default=None, help="Optional absolute roots to scan for resumes")
    parser.add_argument("--skip-existing", action="store_true", help="Skip files already present as Applicants")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seen = set()
        count = 0
        for path in iter_resume_paths(args.roots):
            name = os.path.splitext(os.path.basename(path))[0]
            if args.skip_existing:
                # Dedupe by resume_path
                existing = db.query(Applicant).filter(Applicant.resume_path == path).first()
                if existing:
                    continue
            # Create applicant for each file
            app = Applicant(name=name, email=None, resume_path=path, linkedin_url=None)
            db.add(app)
            db.commit()
            db.refresh(app)
            try:
                process_applicant_pipeline.delay(app.id, path, None)  # enqueue
            except Exception:
                process_applicant_pipeline(app.id, path, None)  # fallback sync
            count += 1
            if args.max_applicants is not None and count >= args.max_applicants:
                break
        print(f"Enqueued {count} resumes for processing.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
