"""
Print a snapshot of the most recent applicants with extracted name/email/status.

Usage (Windows cmd):
  cd backend
  python -m scripts.print_applicants_snapshot --limit 20
"""

import os
import sys
import argparse

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.db import SessionLocal
from app.models.applicant import Applicant, Insights


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=20)
    args = ap.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(Applicant).order_by(Applicant.created_at.desc()).limit(args.limit).all()
        print(f"Applicants (latest {len(rows)}):")
        for a in rows:
            ins = db.query(Insights).filter(Insights.applicant_id == a.id).first()
            print(f"- id={a.id} name={a.name!r} email={a.email!r} status={getattr(a,'status',None)} rating={getattr(ins,'rating',None) if ins else None}")
    finally:
        db.close()


if __name__ == '__main__':
    main()
