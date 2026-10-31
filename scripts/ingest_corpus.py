"""Ingest every file in data/corpus/ through the real HTTP API.
Usage: DOCULENS_API=http://localhost:8100 .venv/bin/python scripts/ingest_corpus.py"""
import os, sys
from pathlib import Path
import requests

API = os.getenv("DOCULENS_API", "http://localhost:8100")
CORPUS = Path(__file__).resolve().parent.parent / "data" / "corpus"

def main():
    files = sorted(p for p in CORPUS.iterdir() if p.suffix.lower() in (".pdf", ".txt", ".md"))
    if not files:
        sys.exit("no corpus files — run scripts/generate_corpus.py first")
    for p in files:
        with open(p, "rb") as f:
            r = requests.post(f"{API}/api/documents", files={"file": (p.name, f)}, timeout=600)
        print(p.name, r.status_code, r.json())
    print(requests.get(f"{API}/readyz", timeout=10).json())

if __name__ == "__main__":
    main()
