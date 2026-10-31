# Progress

- [x] Scaffold, config, SQLite store, FAISS persistence
- [x] Fictional corpus generator (8 docs) + dataset card
- [x] Ingestion: hash dedupe, page/chunk IDs, oversize/format rejection
- [x] Hybrid retrieval (fastembed MiniLM + lexical, RRF)
- [x] Grounded generation + abstention + injection filtering
- [x] FastAPI endpoints (all contract endpoints) + Streamlit UI
- [x] Pytest suite (8 tests)
- [x] Live ingest → search → ask over HTTP
- [x] Evaluation run (51 questions) → eval/results.json: recall@5 1.0, citation validity 1.0, term hit 0.977, abstention 1.0
- [x] Restart persistence check (ask repeated after restart, no re-ingestion)
- [x] Local LLM attempt — torch download stalled x2, llama.cpp build failed; extractive grounded path runs (docs/verification.md)
- [x] Final README + verification with real numbers
- [x] Git commits

Public deployment: **pending** — no deployment account authorized; local
completion only, per the build prompt. Docker files are provided as
configuration; Docker is not available in this environment, so the compose
stack itself was not executed here.
