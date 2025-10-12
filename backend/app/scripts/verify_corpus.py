from app.services.embeddings import get_corpus_vs

def main():
    try:
        vs = get_corpus_vs()
        # Try a tiny query and report count
        docs = vs.similarity_search("resume", k=3)
        print({"ok": True, "hits": len(docs)})
        for d in docs:
            print("-", (d.page_content or "").strip()[:140].replace("\n"," "))
    except Exception as e:
        print({"ok": False, "error": str(e)})

if __name__ == "__main__":
    main()