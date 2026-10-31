# Dataset Card — Northbeam Snacks Inc (fictional corpus)

- **What it is:** 8 original, synthetic documents (4 PDF, 4 TXT) about a fictional
  company, "Northbeam Snacks Inc", written for this project by
  `scripts/generate_corpus.py`. No real company, bank, customer, or employer
  data is included anywhere.
- **Contents:** annual reports 2023 (TXT) and 2024 (PDF), expense policy v1
  (PDF, Jan 2024) and v2 (TXT, Mar 2025, supersedes v1 — deliberate dated
  conflict), a loan agreement (PDF), a 2025 product pricing list (TXT),
  Q2 2025 board minutes (PDF), and an internal memo (TXT) that contains a
  deliberate prompt-injection line used for safety evaluation.
- **License:** MIT (same as the repository). Free to reuse.
- **Known limitations:** tiny (8 documents, ~15 pages); numbers are invented
  for demonstration; the corpus proves retrieval/grounding engineering, not
  real-world financial QA accuracy.
