import os
import sys
from app.services.embeddings import chunk_texts, upsert_corpus_chunks
from app.worker.tasks.data_ingestion import process_resume_file

def main(root: str):
    if not os.path.isdir(root):
        print(f"Not a directory: {root}")
        sys.exit(1)
    files = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith((".pdf", ".docx", ".txt")):
                files.append(os.path.join(dirpath, f))
    if not files:
        print("No resume files found.")
        return
    texts = []
    for p in files:
        try:
            txt = process_resume_file(p)
            if txt:
                texts.append(txt)
        except Exception:
            continue
    if not texts:
        print("No extractable text found.")
        return
    chunks = chunk_texts(["\n\n".join(texts)])  # fewer, larger chunks for global corpus
    upsert_corpus_chunks(chunks, metas=None)
    chunks = chunk_texts(["\n\n".join(texts)])  # fewer, larger chunks for global corpus
    upsert_corpus_chunks(chunks)
    print(f"Ingested {len(files)} files; produced {len(chunks)} chunks into corpus.")
    if len(sys.argv) < 2:
        print("Usage: python -m app.scripts.ingest_resume_corpus <folder>")
        sys.exit(1)
    main(sys.argv[1])