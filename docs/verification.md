# Verification — what actually ran (2026-10-31)

Environment: Python 3.12.3, 4 cores, ~8 GB RAM (shared VM), **no Docker**.
API on port 8100, Streamlit UI on port 8501.

## Local completion: YES. Public deployment: pending (no account authorized).
## CI: workflow file committed; remote CI execution NOT claimed.
## Docker: Dockerfile/compose written as configuration; NOT executed (no Docker).

## Runtime / model facts

- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` via fastembed
  (ONNX Runtime, CPU). Verified: standalone embed of 2 texts -> (2, 384)
  in 2.2 s.
- The Python HF client stalled downloading the 90 MB model.onnx through
  this environment's egress proxy (same failure as the PyTorch wheel).
  Workaround used: curl download placed into the fastembed/HF cache
  (sha256 verified: bbd7b466…f0c5), API run with `HF_HUB_OFFLINE=1`.
  Reproducible via `scripts/download_model.sh`.
- Generation attempts:
  1. `pip install torch` (CPU index) — FAILED twice: large-wheel downloads
     stalled / network errors through the proxy. flan-t5-small therefore
     could not run here. The T5 adapter (`app/generate.py`) is implemented
     with a numeric-grounding guard but was **not executed**.
  2. `llama-cpp-python` source build — FAILED after ~7 min during ggml
     compilation (build subprocess error) in this shared environment.
  3. **Running path: extractive grounded composer** — real retrieval +
     verbatim evidence sentences under grounding rules; every live result
     below used it (`generation_mode: extractive-grounded`).

## Ingestion (real HTTP)

`scripts/ingest_corpus.py` -> all 8 corpus files returned 200/completed.
`GET /readyz`: `{"status":"ready","documents":8,"chunks":13,
"embedding_model":"sentence-transformers/all-MiniLM-L6-v2",
"index_version":"emb=sentence-transformers/all-MiniLM-L6-v2;chunk=900/150;v1"}`

## Real ask (before AND after an API restart, no re-ingestion)

Request: `POST /api/ask {"question":"When does the Meridian loan mature?"}`
Response (both times, identical answer + citation):

```json
{"status": "supported",
 "answer": "The loan matures on December 1, 2027. Loan Agreement - Northbeam Snacks Inc and Meridian Community Bank Meridian Community Bank extended a term loan of $600,000 to Northbeam Snacks Inc on June 1, 2024.",
 "citations": [{"document_id": "doc_bdb223553a", "page": 1,
                "chunk_id": "doc_bdb223553a:p1:c0", "score": 0.0333}],
 "generation_mode": "extractive-grounded",
 "total_latency_ms": "~10-80 (varies with shared-VM load)"}
```

Unsupported example: "What is the weather in Paris today?" ->
`insufficient_evidence`. Smoke script (`scripts/smoke.sh`) passed end to end.

## Persistence

API killed and restarted; `/readyz` immediately reported 8 documents /
13 chunks from the on-disk SQLite + FAISS artifacts, and the ask above was
repeated successfully with **no re-ingestion**.

## UI

Streamlit app started on :8501, returned HTTP 200. (Interactive click-through
not recorded; screenshot/recording pending — see docs/demo.md.)

## Tests

`DOCULENS_EMBEDDER=tfidf DOCULENS_GENERATOR=extractive pytest -q`
-> **8 passed**. Covers ingest/search/ask, duplicate detection, unsupported
format (400), oversize (400), unanswerable abstention, prompt injection,
page endpoints + 404s. Tests use the TF-IDF embedder so CI needs no model
download; the live system above used the real MiniLM embedder.

## Evaluation (`scripts/evaluate.py`, 51 questions, live API)

From `eval/results.json`:

| Metric | Result |
|---|---|
| recall@5 (answerable, n=43) | 1.000 |
| citation validity | 1.000 |
| answer term hit | 0.977 (42/43) |
| abstention accuracy (n=8, incl. 2 injection) | 1.000 |

Known miss: Q30 "Who must approve travel requests under Expense Policy
Version 2?" — response is supported and cited to the correct document/page,
but its top-ranked evidence sentences omit the word "director".
Questions carry a tuning/held-out split flag (every 5th = tuning); metrics
above are for the full set. Rubric: recall@5 = expected document in top-5
search results; citation validity = an ask citation on the expected
document+page whose text appears in the page endpoint's text; term hit =
expected term string in the answer; abstention = status
`insufficient_evidence` with no fabricated disclosure.
The corpus' injection memo ("IGNORE ALL PREVIOUS INSTRUCTIONS…") is
synthetic test data written for this project; the system filters such
spans from answers and both injection questions abstained.

## Release checklist

- [x] Clean-checkout quickstart documented and executed locally
- [x] Tests green, evaluation saved (`eval/results.json`)
- [x] No secrets, model weights, or FAISS binaries in git (see .gitignore)
- [ ] Screenshot + 60–90 s demo recording (pending tooling)
- [ ] Public HTTPS deployment (pending an authorized account)
- [ ] Tag release after the two items above
