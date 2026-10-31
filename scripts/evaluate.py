"""Evaluate DocuLens against eval/questions.json through the real HTTP API.

Metrics (reported honestly, split by tuning / held_out):
- recall@5: expected document among top-5 search results
- citation_validity: at least one /api/ask citation resolves via the page
  endpoint AND belongs to the expected document/page
- answer_term_hit: expected term appears in the answer text
- abstention_accuracy: unanswerable/injection questions return
  insufficient_evidence and disclose no 'secret'
Writes eval/results.json.
Usage: .venv/bin/python scripts/evaluate.py"""
import json, os
from pathlib import Path
import requests

API = os.getenv("DOCULENS_API", "http://localhost:8100")
ROOT = Path(__file__).resolve().parent.parent

def main():
    qs = json.loads((ROOT / "eval" / "questions.json").read_text())
    docs = {d["id"]: d["name"] for d in requests.get(f"{API}/api/documents", timeout=10).json()["documents"]}
    rows, agg = [], {"answerable": 0, "recall@5": 0, "citation_valid": 0, "term_hit": 0,
                     "unanswerable": 0, "abstained": 0}
    for q in qs:
        s = requests.post(f"{API}/api/search", json={"query": q["question"], "k": 5}, timeout=120).json()
        a = requests.post(f"{API}/api/ask", json={"question": q["question"], "k": 5}, timeout=120).json()
        row = {"id": q["id"], "split": q["split"], "category": q["category"]}
        if q["answerable"]:
            agg["answerable"] += 1
            names = [docs.get(r["document_id"]) for r in s["results"]]
            row["recall@5"] = q["expected_document"] in names
            agg["recall@5"] += row["recall@5"]
            valid = False
            for c in a.get("citations", []):
                if docs.get(c["document_id"]) == q["expected_document"] and c["page"] == q["expected_page"]:
                    pg = requests.get(f"{API}/api/documents/{c['document_id']}/pages/{c['page']}", timeout=10)
                    if pg.status_code == 200:
                        page_text = " ".join(pg.json()["text"].split())
                        if " ".join(c["text"][:60].split()) in page_text:
                            valid = True
            row["citation_valid"] = valid; agg["citation_valid"] += valid
            row["term_hit"] = q["expected_term"] in a.get("answer", "")
            agg["term_hit"] += row["term_hit"]
            row["status"] = a.get("status")
        else:
            agg["unanswerable"] += 1
            ok = a.get("status") == "insufficient_evidence" and "api key is" not in a.get("answer", "").lower()
            row["abstained_correctly"] = ok; agg["abstained"] += ok
        rows.append(row)
    n, m = agg["answerable"], agg["unanswerable"]
    summary = {
        "questions": len(qs), "answerable": n, "unanswerable": m,
        "recall@5": round(agg["recall@5"] / n, 3) if n else None,
        "citation_validity": round(agg["citation_valid"] / n, 3) if n else None,
        "answer_term_hit": round(agg["term_hit"] / n, 3) if n else None,
        "abstention_accuracy": round(agg["abstained"] / m, 3) if m else None,
        "api": API}
    out = {"summary": summary, "rows": rows}
    (ROOT / "eval" / "results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(summary, indent=1))

if __name__ == "__main__":
    main()
