"""
One-time converter: .doc (Word 97-2003) -> .docx

Tries, in order on Windows:
- Microsoft Word COM automation (win32com) if available
- LibreOffice (soffice) command-line if installed

Usage (Windows cmd):
  cd backend
  set PYTHONPATH=.
  python -m scripts.convert_doc_to_docx --root "..\real resumes" --only-problematic

Flags:
  --root: folder to scan (default: project_root/real resumes)
  --overwrite: replace existing .docx outputs
  --only-problematic: only convert if our text extractor returns empty/very short
"""
from __future__ import annotations

import os
import sys
import argparse
import subprocess
from typing import Optional, List

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, os.pardir))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def has_soffice() -> bool:
    try:
        # On Windows, soffice.exe may be on PATH
        res = subprocess.run(["soffice", "--version"], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def convert_with_word(doc_path: str, out_docx: str) -> bool:
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch('Word.Application')
        word.Visible = False
        # Ensure output dir exists
        os.makedirs(os.path.dirname(out_docx), exist_ok=True)
        doc = word.Documents.Open(doc_path)
        # 16 = wdFormatDocumentDefault (docx)
        doc.SaveAs(out_docx, FileFormat=16)
        doc.Close(False)
        word.Quit()
        return os.path.exists(out_docx)
    except Exception:
        return False


def convert_with_soffice(doc_path: str, out_dir: str) -> Optional[str]:
    try:
        os.makedirs(out_dir, exist_ok=True)
        # soffice --headless --convert-to docx --outdir <out_dir> <doc>
        res = subprocess.run([
            "soffice", "--headless", "--convert-to", "docx", "--outdir", out_dir, doc_path
        ], capture_output=True)
        if res.returncode == 0:
            base = os.path.splitext(os.path.basename(doc_path))[0]
            out_path = os.path.join(out_dir, base + ".docx")
            return out_path if os.path.exists(out_path) else None
    except Exception:
        pass
    return None


def iter_doc_files(root: str) -> List[str]:
    out: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith('.doc'):
                out.append(os.path.join(dirpath, fn))
    return out


def should_convert_only_if_problematic(doc_path: str) -> bool:
    # Import extractor and see if we get meaningful text
    try:
        from app.worker.tasks.data_ingestion import process_resume_file
        txt = process_resume_file(doc_path) or ""
        # If extractor yields < 120 chars, consider problematic
        return len(txt.strip()) < 120
    except Exception:
        return True


def convert_all(root: str, overwrite: bool = False, only_problematic: bool = False) -> int:
    files = iter_doc_files(root)
    if not files:
        print("[convert] No .doc files found.")
        return 0
    count = 0
    use_soffice = has_soffice()
    for path in files:
        base, _ = os.path.splitext(path)
        out_docx = base + ".docx"
        if not overwrite and os.path.exists(out_docx):
            continue
        if only_problematic and not should_convert_only_if_problematic(path):
            continue
        ok = convert_with_word(path, out_docx)
        if not ok and use_soffice:
            out = convert_with_soffice(path, os.path.dirname(path))
            ok = bool(out and os.path.exists(out))
        if ok:
            print(f"[convert] Converted: {os.path.basename(path)} -> {os.path.basename(out_docx)}")
            count += 1
        else:
            print(f"[convert] FAILED: {path}")
    print(f"[convert] Total converted: {count}")
    return count


def main():
    ap = argparse.ArgumentParser(description="Convert .doc files to .docx in-place")
    ap.add_argument("--root", default=os.path.join(PROJECT_ROOT, "real resumes"), help="Root directory to scan")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing .docx files")
    ap.add_argument("--only-problematic", action="store_true", help="Convert only when text extraction is poor")
    args = ap.parse_args()
    root = os.path.normpath(args.root)
    print(f"Root: {root} | Exists: {os.path.exists(root)}")
    convert_all(root, overwrite=args.overwrite, only_problematic=args.only_problematic)


if __name__ == "__main__":
    main()
