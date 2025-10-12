"""
Script: ingest_real_resumes.py
Purpose: Ingest resumes from the provided 'real resumes' folder and enqueue them for processing.

Usage (Windows cmd):
  cd backend
  python -m scripts.ingest_real_resumes --root "..\\real resumes" --max 100
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


def iter_resume_paths(root):
    if not os.path.isdir(root):
        return
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
                yield os.path.join(dirpath, fn)


def main():
    parser = argparse.ArgumentParser(description="Ingest 'real resumes' folder and enqueue processing")
    parser.add_argument("--root", default=os.path.join(PROJECT_ROOT, "real resumes"), help="Root folder of resumes")
    parser.add_argument("--max", type=int, default=None, help="Max number of resumes")
    parser.add_argument("--skip-existing", action="store_true", help="Skip if resume_path already present")
    args = parser.parse_args()

    root = os.path.normpath(args.root)
    print(f"Root: {root}")
    print(f"Exists: {os.path.exists(root)} | IsDir: {os.path.isdir(root)}")
    files = list(iter_resume_paths(root) or [])
    print(f"Discovered files: {len(files)}")
    if not files:
        print("No resumes found to ingest.")
        return
    db = SessionLocal()
    try:
        count = 0
        for path in files:
            name = os.path.splitext(os.path.basename(path))[0]
            if args.skip_existing:
                exists = db.query(Applicant).filter(Applicant.resume_path == path).first()
                if exists:
                    continue
            app = Applicant(name=name, email=None, resume_path=path, linkedin_url=None)
            db.add(app)
            db.commit()
            db.refresh(app)
            try:
                process_applicant_pipeline.delay(app.id, path, None)
            except Exception:
                process_applicant_pipeline(app.id, path, None)
            count += 1
            if args.max is not None and count >= args.max:
                break
        print(f"Enqueued {count} resumes from: {args.root}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
