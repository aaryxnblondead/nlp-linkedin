"""
Script: ingest_resume_corpus.py
Purpose: Parse every resume under resumes/Resumes and resumedataset/data/data,
         chunk and upsert into ChromaDB global corpus for recruiter Q&A and similarity.

Run from backend folder so relative paths and env work.
"""

import os
import sys
import argparse
from typing import List, Tuple

# Ensure backend root is on sys.path so `app.*` imports work when executed as a module
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, os.pardir))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.embeddings import add_corpus_texts


def parse_resume_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            try:
                from fitz import open as fitz_open  # PyMuPDF
            except Exception:
                import fitz  # fallback name
                fitz_open = fitz.open  # type: ignore[attr-defined]
            with fitz_open(path) as doc:  # type: ignore[misc]
                lines = []
                for page in doc:
                    if hasattr(page, "get_text"):
                        lines.append(page.get_text("text"))
                    else:
                        # very old fallback
                        lines.append(page.getText("text"))
                return "\n".join(lines)
        if ext == ".docx":
            import docx
            doc = docx.Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        if ext == ".txt":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as e:
        print(f"[parse] Failed {path}: {e}")
    return ""


def collect_resume_texts(custom_roots: List[str] | None = None, max_files: int | None = None) -> List[Tuple[str, str]]:
    roots = custom_roots or [
        os.path.join(PROJECT_ROOT, "resumes", "Resumes"),
        os.path.join(PROJECT_ROOT, "resumedataset", "data", "data"),
    ]
    pairs: List[Tuple[str, str]] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith((".pdf", ".docx", ".txt")):
                    path = os.path.join(dirpath, fn)
                    text = parse_resume_file(path)
                    if text and text.strip():
                        pairs.append((path, text))
                        if max_files is not None and len(pairs) >= max_files:
                            return pairs
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Ingest resumes into Chroma corpus store")
    parser.add_argument("--max-files", type=int, default=None, help="Limit number of resumes to ingest")
    parser.add_argument("--batch-chunks", type=int, default=500, help="Number of chunks per add-texts batch")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size for text splitter")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="Chunk overlap for text splitter")
    parser.add_argument("--roots", nargs="*", default=None, help="Optional absolute roots to scan for resumes")
    args = parser.parse_args()

    items = collect_resume_texts(args.roots, args.max_files)
    if not items:
        print("No resumes found to ingest.")
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    total_chunks = 0
    batch_texts: List[str] = []
    batch_meta: List[dict] = []
    batch_target = max(1, args.batch_chunks)

    for idx, (path, text) in enumerate(items, start=1):
        docs = splitter.create_documents([text])
        local = len(docs)
        for d in docs:
            batch_texts.append(d.page_content)
            batch_meta.append({"source": path})
        total_chunks += local
        if len(batch_texts) >= batch_target:
            print(f"Upserting batch: {len(batch_texts)} chunks (file {idx}/{len(items)})...")
            add_corpus_texts(batch_texts, batch_meta)
            batch_texts.clear()
            batch_meta.clear()
    # flush remainder
    if batch_texts:
        print(f"Upserting final batch: {len(batch_texts)} chunks...")
        add_corpus_texts(batch_texts, batch_meta)

    print(f"Ingestion complete. Total resumes: {len(items)} | Total chunks: {total_chunks}")


if __name__ == "__main__":
    main()
