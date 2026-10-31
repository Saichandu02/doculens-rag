# Architecture

```
data/corpus (PDF/TXT) ──► POST /api/documents ──► parse (pypdf / text)
                                                    │ sha256 dedupe
                                                    ▼
                                          chunk (900 chars / 150 overlap,
                                          stable IDs doc:p<page>:c<seq>)
                                                    │
                          ┌─────────────────────────┼──────────────────┐
                          ▼                         ▼                  ▼
                   SQLite metadata            FAISS IndexFlatIP    page text
                   (documents, chunks,        (MiniLM-L6-v2        (source
                    ingestions tables)         embeddings, L2-     viewer via
                                               normalized)         /pages/{p})
POST /api/search ─► hybrid retrieval: FAISS vector rank + lexical (token
                    overlap) rank, fused with Reciprocal Rank Fusion
POST /api/ask ────► retrieval ─► grounded generation (extractive composer,
                    optional flan-t5-small guarded by a numeric-grounding
                    check, optional llama.cpp GGUF adapter) ─► citations
                    Abstention: no chunk clearing the evidence bar returns
                    status=insufficient_evidence with no citations.
Streamlit UI ─────► HTTP client of the API (ask, citations, source viewer,
                    upload)
```

Components: `app/main.py` (API), `app/ingest.py`, `app/retrieval.py`,
`app/generate.py`, `app/embeddings.py`, `app/store.py`, `ui/streamlit_app.py`.

Consistency: the FAISS index and SQLite are written together at ingestion;
on restart the API reloads both from `artifacts/` — no re-ingestion needed.
Index version (`emb model ; chunking ; v1`) is returned by every response.
