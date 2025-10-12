"""
DEPRECATED: Prefer scripts/ingest_resume_corpus.py which handles batching, metadata, and absolute paths.
This legacy script now uses the shared embeddings service (Google text-embedding-004).
"""

import os
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.embeddings import get_embedder

# Helper: Parse resume files (PDF/DOCX)
def parse_resume(resume_path):
    ext = os.path.splitext(resume_path)[1].lower()
    try:
        if ext == '.pdf':
            import fitz
            with fitz.open(resume_path) as doc:
                return "\n".join(page.get_text() for page in doc)
        elif ext == '.docx':
            import docx
            doc = docx.Document(resume_path)
            return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Failed to parse {resume_path}: {e}")
    return ""

# 1. Collect all resume texts
resume_dirs = [
    "resumedataset/data/data",
    "resumes/Resumes"
]
all_texts = []
for resume_dir in resume_dirs:
    for root, _, files in os.walk(resume_dir):
        for file in files:
            if file.endswith(('.pdf', '.docx')):
                path = os.path.join(root, file)
                text = parse_resume(path)
                if text:
                    all_texts.append(text)

# 2. Chunk text
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = []
for text in all_texts:
    docs.extend(splitter.create_documents([text]))



# 3. Embed and store in ChromaDB using Google embeddings
embedder = get_embedder()
vectorstore = Chroma.from_documents(docs, embedder, persist_directory="chroma_db")
vectorstore.persist()
print("Ingestion complete. ChromaDB is ready for RAG (Google embeddings).")
