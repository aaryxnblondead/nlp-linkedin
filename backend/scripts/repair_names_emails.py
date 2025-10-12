"""
Repair script: Update Applicant.name and Applicant.email in-place
by re-extracting from stored Resume.raw_text using our NER pipeline.

Usage (Windows cmd):
  cd backend
  python -m scripts.repair_names_emails --limit 100
"""

import os
import sys
import argparse

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.db import SessionLocal
from app.models.applicant import Applicant, Resume
from app.worker.tasks.intelligence_engine import create_structured_resume


def looks_like_filename(n: str) -> bool:
    nlow = (n or "").lower()
    if any(x in nlow for x in ["resume", "cv", "_", "-", ".doc", ".pdf", ".docx"]):
        return True
    if any(ch.isdigit() for ch in nlow):
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=200)
    ap.add_argument('--only-missing', action='store_true', help='Only update rows with missing name/email')
    args = ap.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(Applicant).order_by(Applicant.created_at.desc()).limit(args.limit).all()
        updated = 0
        scanned = 0
        for app in rows:
            scanned += 1
            res = db.query(Resume).filter(Resume.applicant_id == app.id).first()
            if res is None or not getattr(res, 'raw_text', None):
                continue
            sr = create_structured_resume(res.raw_text, {})
            sr_name = (sr.get('name') or '').strip()
            sr_email = (sr.get('email') or '').strip()
            do_update = {}
            current_name = (getattr(app, 'name', '') or '').strip()
            current_email = (getattr(app, 'email', '') or '').strip()
            if sr_name and (looks_like_filename(current_name) or (not current_name)):
                do_update[Applicant.name] = sr_name
            if sr_email and (not current_email):
                do_update[Applicant.email] = sr_email
            if args.only_missing:
                # If only-missing set, require that current field be empty
                if Applicant.name in do_update and current_name:
                    do_update.pop(Applicant.name, None)
                if Applicant.email in do_update and current_email:
                    do_update.pop(Applicant.email, None)
            if do_update:
                db.query(Applicant).filter(Applicant.id == app.id).update(do_update)
                db.commit()
                updated += 1
        print(f"Scanned: {scanned} | Updated: {updated}")
    finally:
        db.close()


if __name__ == '__main__':
    main()
