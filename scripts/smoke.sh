#!/usr/bin/env bash
# Smoke test against a running DocuLens API (default http://localhost:8100)
set -euo pipefail
API="${DOCULENS_API:-http://localhost:8100}"
echo "== healthz =="; curl -sf "$API/healthz"; echo
echo "== readyz =="; curl -sf "$API/readyz"; echo
echo "== search =="
curl -sf -X POST "$API/api/search" -H 'Content-Type: application/json' \
  -d '{"query":"What was total revenue in 2024?","k":3}'; echo
echo "== ask (supported) =="
curl -sf -X POST "$API/api/ask" -H 'Content-Type: application/json' \
  -d '{"question":"What was total revenue in 2024?"}'; echo
echo "== ask (unsupported, must abstain) =="
curl -sf -X POST "$API/api/ask" -H 'Content-Type: application/json' \
  -d '{"question":"What is the weather in Paris today?"}'; echo
echo "smoke OK"
