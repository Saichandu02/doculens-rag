"""DocuLens Streamlit UI: ask, inspect citations, view source pages."""
import os, requests, streamlit as st

API = os.getenv("DOCULENS_API", "http://localhost:8100")
st.set_page_config(page_title="DocuLens", layout="wide")
st.title("DocuLens — Financial Document Search")
st.caption("Answers are grounded in the ingested fictional corpus; citations resolve to exact pages.")

try:
    h = requests.get(f"{API}/readyz", timeout=3).json()
    st.success(f"Index ready: {h['documents']} documents, {h['chunks']} chunks · {h['embedding_model']}")
except Exception:
    st.warning("API not ready — start it with the quickstart in README.md and ingest the corpus.")

q = st.text_input("Ask a question about the documents")
if st.button("Ask") and q:
    r = requests.post(f"{API}/api/ask", json={"question": q, "k": 5}, timeout=120).json()
    st.write(f"**Status:** {r['status']} · **Mode:** {r.get('generation_mode', '-')} · **Total:** {r.get('total_latency_ms')} ms")
    st.write(r["answer"])
    for c in r.get("citations", []):
        with st.expander(f"Source: {c['document_id']} — page {c['page']} (score {c['score']})"):
            st.write(c["text"])
            if st.button(f"Open full page {c['page']}", key=c["chunk_id"]):
                page = requests.get(f"{API}/api/documents/{c['document_id']}/pages/{c['page']}", timeout=10).json()
                st.text(page["text"])

st.divider()
st.subheader("Upload a document (.pdf / .txt / .md, ≤5 MB)")
up = st.file_uploader("Document", type=["pdf", "txt", "md"])
if up and st.button("Ingest"):
    resp = requests.post(f"{API}/api/documents", files={"file": (up.name, up.getvalue())}, timeout=300)
    st.write(resp.json())
