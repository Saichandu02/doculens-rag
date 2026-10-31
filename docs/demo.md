# Demo Walkthrough (60–90 seconds)

Recording status: **pending** (no screen-recording tooling in the build
environment). Script:

1. Start the API + UI (README quickstart). Show `/readyz`: 8 documents.
2. Ask: "What was total revenue in 2024?" → answer $4,200,000 with a citation
   to annual_report_2024.pdf page 1. Click the citation and open the full
   source page in the viewer.
3. Ask: "What is the daily meal allowance under Expense Policy Version 2?"
   → $75, cited to expense_policy_v2.txt — then ask the same for Version 1
   ($50) to show dated-revision handling.
4. Ask an unsupported question: "What is Northbeam's stock ticker symbol?"
   → the system abstains with `insufficient_evidence` instead of inventing
   an answer.
5. Upload the same PDF again → the UI reports it as a duplicate (sha256).
