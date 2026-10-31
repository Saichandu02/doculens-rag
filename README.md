# DocuLens — Financial Document Search with Verifiable Citations

DocuLens answers questions about a small financial document collection and
links every answer to exact source passages — or explicitly says it does
not have enough evidence. Personal project; all documents are fictional.

- **Live demo:** none (no deployment account authorized — public deployment pending)
- **Verified local URLs:** API http://localhost:8100 · UI http://localhost:8501
- **Screenshot:** pending (no capture tooling in the build environment; see
  `docs/demo.md` for the walkthrough script)

## Implemented capabilities

1. Ingestion of PDF/TXT/MD with sha256 duplicate detection, stable
   page/chunk IDs, size/format rejection, and ingestion status tracking.
2. Hybrid retrieval — FAISS vector search (all-MiniLM-L6-v2 embeddings via
   fastembed/ONNX) fused with lexical ranking via Reciprocal Rank Fusion.
3. Grounded answers with citations that resolve to exact document + page,
   year-consistency and evidence-density grounding rules, privacy guard,
   prompt-injection filtering, and `insufficient_evidence` abstention.

## Quickstart (Linux)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/generate_corpus.py        # fictional corpus (8 docs)
# If the Python HF client stalls downloading the embedding model:
bash scripts/download_model.sh
NO_PROXY=localhost,127.0.0.1 HF_HUB_OFFLINE=1 \
  .venv/bin/uvicorn app.main:app --port 8100 &      # API
.venv/bin/python scripts/ingest_corpus.py           # ingest via HTTP
.venv/bin/streamlit run ui/streamlit_app.py         # UI on :8501
bash scripts/smoke.sh                               # end-to-end smoke test
```

Windows (PowerShell): same commands with `.venv\Scripts\` paths and
`$env:HF_HUB_OFFLINE=1` set before starting uvicorn.

Docker: `docker compose up` is provided as configuration (Docker was not
available in the build environment, so the compose stack is unexecuted —
see `docs/verification.md`).

## API

| Endpoint | Purpose |
|---|---|
| `GET /healthz` / `GET /readyz` | liveness / index readiness |
| `POST /api/documents` | upload + ingest (multipart) |
| `GET /api/ingestions/{id}` | ingestion status |
| `GET /api/documents` | list documents |
| `GET /api/documents/{id}/pages/{page}` | source page viewer data |
| `POST /api/search` | hybrid retrieval |
| `POST /api/ask` | grounded answer + citations or abstention |

Example (verified live, see `docs/verification.md`):

```bash
curl -X POST localhost:8100/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"When does the Meridian loan mature?"}'
# -> {"status":"supported",
#     "answer":"The loan matures on December 1, 2027. ...",
#     "citations":[{"document_id":"doc_bdb223553a","page":1, ...}]}
```

## Measured results (this build, `eval/results.json`)

Evaluation set: 51 questions (43 answerable, 8 unanswerable/injection),
with tuning/held-out split marked per question.

- recall@5: **1.000** (43/43)
- citation validity: **1.000** (43/43)
- answer term hit: **0.977** (42/43 — known miss: "Who must approve travel
  requests under Version 2?" answers with supported policy text but the
  top-ranked sentences omit the word "director")
- abstention accuracy: **1.000** (8/8, including both injection attempts)

Tests: `pytest` — 8 passed (duplicates, unsupported format, oversize,
unanswerable, injection, page endpoints). Run with
`DOCULENS_EMBEDDER=tfidf DOCULENS_GENERATOR=extractive .venv/bin/pytest -q`
(the test embedder avoids a model download in CI; production uses MiniLM).

## Limitations & tradeoffs

- Generation in this environment is the **extractive grounded composer**:
  flan-t5-small could not be installed (PyTorch CPU wheel downloads stalled
  through the egress proxy, twice) and llama-cpp-python's source build
  failed during compilation in this shared ~8 GB environment. The T5
  adapter is implemented behind a numeric-grounding guard and will activate
  where torch is installable. Details in `docs/verification.md`.
- Corpus is tiny and fictional; metrics prove engineering behavior, not
  real-world financial QA accuracy.
- SQLite + file FAISS index: single-node only.
- Extractive answers can include adjacent context sentences; they never
  include unsupported claims, but they are not fluent prose.

## Resume bullets (personal project, from measured results only)

- Built a RAG service (FastAPI, FAISS, MiniLM embeddings) over a synthetic
  financial corpus achieving 1.00 recall@5 and 1.00 citation validity on a
  51-question evaluation with explicit abstention for unsupported queries.
- Implemented hybrid vector+lexical retrieval and grounding rules
  (year consistency, evidence density, injection filtering) that abstained
  correctly on 8/8 unanswerable and prompt-injection test questions.

## Docs

`docs/architecture.md` · `docs/demo.md` · `docs/decisions.md` ·
`docs/verification.md` · `data/DATASET_CARD.md` · License: MIT
