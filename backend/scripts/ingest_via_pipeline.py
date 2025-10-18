from __future__ import annotations

import os
import sys
import argparse
from typing import List


def main() -> int:
    # Autoload .env so DB/flags work the same as the app
    try:
        from dotenv import load_dotenv, find_dotenv
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Ingest resumes via the same applicant upload pipeline")
    parser.add_argument("--root", default=os.getenv("INGEST_ROOT", "/app/resumes/Resumes"), help="Root folder containing resumes")
    parser.add_argument("--glob", default="*.pdf;*.doc;*.docx", help="Semicolon-separated patterns")
    parser.add_argument("--limit", type=int, default=0, help="Max files to ingest (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="List files but do not enqueue")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"Root folder not found: {root}")
        return 1

    # Collect files
    patterns = [p.strip() for p in (args.glob or "").split(";") if p.strip()]
    found: List[str] = []
    for base, _, files in os.walk(root):
        for fn in files:
            lower = fn.lower()
            if any(lower.endswith(ext.replace("*", "").lower()) for ext in patterns):
                found.append(os.path.join(base, fn))

    if args.limit and len(found) > args.limit:
        found = found[: args.limit]

    if not found:
        print(f"No files found under {root} matching {patterns}")
        return 0

    print(f"Discovered {len(found)} files. dry_run={args.dry_run}")

    # Import application services only after env is loaded
    from app.db import SessionLocal
    from app.models.applicant import Applicant
    from app.services.storage import get_storage_service
    from app.worker.tasks.processing_pipeline import process_applicant_pipeline

    storage = get_storage_service()
    db = SessionLocal()
    enqueued = 0
    try:
        for i, path in enumerate(found, start=1):
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception as e:
                print(f"[SKIP] Cannot read {path}: {e}")
                continue

            # Derive a provisional name from filename; pipeline will improve it later
            base = os.path.basename(path)
            name_guess = os.path.splitext(base)[0]
            email = ""
            linkedin_url = ""

            if args.dry_run:
                print(f"[DRY] Would save and enqueue: {path}")
                continue

            # Save to the same storage used by uploads (uploaded_resumes)
            saved_path, _ = storage.save(data, base)

            # Create Applicant and enqueue the same pipeline as the upload endpoint
            try:
                applicant = Applicant(name=name_guess, email=email, resume_path=saved_path, linkedin_url=linkedin_url)
                db.add(applicant)
                db.commit()
                db.refresh(applicant)
            except Exception as e:
                db.rollback()
                print(f"[ERR] DB insert failed for {base}: {e}")
                continue

            try:
                # Try async; fallback to sync if celery unavailable
                try:
                    process_applicant_pipeline.delay(applicant.id, saved_path, linkedin_url)  # type: ignore[attr-defined]
                    status = "queued"
                except Exception:
                    ok = process_applicant_pipeline(applicant.id, saved_path, linkedin_url)
                    status = "done" if ok else "failed"
                enqueued += 1
                print(f"[{status}] {i}/{len(found)} -> applicant_id={applicant.id} file={base}")
            except Exception as e:
                print(f"[ERR] Pipeline failed for applicant_id={getattr(applicant,'id',None)}: {e}")
    finally:
        db.close()

    print(f"Completed. Enqueued/processed {enqueued} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
