# Design Decisions

1. **fastembed (ONNX) for all-MiniLM-L6-v2 instead of PyTorch
   sentence-transformers.** Same embedding model, ~10x smaller install and
   far lower RAM — important on a 4-core / 8 GB box. Tradeoff: fewer model
   choices than the full sentence-transformers catalog.
2. **Hybrid retrieval (vector + lexical, RRF fusion).** Financial questions
   hinge on exact numbers and names; pure vector search can miss those, pure
   lexical search misses paraphrases. Evaluated in `eval/results.json`.
3. **Grounded extractive generation as the safety floor.** Answers are
   composed from verbatim evidence sentences that clear a 2-content-token
   grounding bar, so citations are honest by construction. A generative
   model (flan-t5-small via transformers, or a GGUF model via llama.cpp)
   can be enabled, but its output is kept only if every number it states
   appears in the evidence; otherwise the extractive answer is used.
4. **Abstention over hallucination.** If retrieval/grounding is weak the API
   returns `insufficient_evidence` rather than guessing — measured on the
   unanswerable + injection slice of the evaluation set.
5. **Document text is untrusted data.** Injection-pattern sentences are
   excluded from answers; the corpus contains a deliberate injection memo
   and the test-suite + eval verify no secret is "revealed" (there is none)
   and the system abstains.
6. **SQLite + FAISS files, no server DB.** Right-sized for a single-node
   demo; both persist in `artifacts/` and survive restarts. Tradeoff: not
   multi-writer safe — a real deployment would move metadata to Postgres
   and the index to a vector service.
7. **Dated policy revisions kept as separate documents** (v1 2024, v2 2025)
   rather than overwriting, so questions must name a version — mirroring
   real document collections and testing revision handling.
