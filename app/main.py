"""DocuLens FastAPI service."""
import time
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from . import config, store
from .ingest import ingest_bytes
from .retrieval import get_retriever, refresh_retriever
from .generate import generate, looks_like_injection
from .embeddings import get_embedder

app = FastAPI(title="DocuLens RAG", version="1.0.0")
store.init_db()

class SearchReq(BaseModel):
    query: str
    k: int = 5
class AskReq(BaseModel):
    question: str
    k: int = 5

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "doculens-rag"}

@app.get("/readyz")
def readyz():
    r = get_retriever()
    docs, chunks = store.counts()
    if not r.ready:
        raise HTTPException(503, "index not ready: no documents ingested or index missing")
    return {"status": "ready", "documents": docs, "chunks": chunks,
            "embedding_model": get_embedder().name,
            "index_version": config.INDEX_VERSION}

@app.post("/api/documents")
async def upload(background: BackgroundTasks, file: UploadFile = File(...)):
    raw = await file.read()
    try:
        iid, doc, dup = ingest_bytes(file.filename, raw)
    except ValueError as e:
        raise HTTPException(400, str(e))
    refresh_retriever()
    return {"ingestion_id": iid, "document_id": doc["id"], "name": doc["name"],
            "duplicate": dup, "status": "duplicate" if dup else "completed"}

@app.get("/api/documents")
def list_documents():
    import sqlite3
    c = sqlite3.connect(config.DB_PATH); c.row_factory = sqlite3.Row
    return {"documents": [dict(r) for r in c.execute("SELECT id,name,ext,pages,created_at FROM documents")]}

@app.get("/api/ingestions/{iid}")
def ingestion(iid: str):
    rec = store.get_ingestion(iid)
    if not rec:
        raise HTTPException(404, "ingestion not found")
    return rec

@app.get("/api/documents/{doc_id}/pages/{page}")
def page(doc_id: str, page: int):
    p = store.page_text(doc_id, page)
    if not p:
        raise HTTPException(404, "document/page not found")
    return p

def _citations(hits):
    return [{"document_id": h["document_id"], "page": h["page"],
             "chunk_id": h["chunk_id"], "score": h["score"],
             "text": h["text"][:400]} for h in hits]

@app.post("/api/search")
def search(req: SearchReq):
    t0 = time.time()
    hits = get_retriever().search(req.query, k=req.k)
    return {"query": req.query, "results": _citations(hits),
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "index_version": config.INDEX_VERSION}

PRIVACY_PATTERNS = ("home address", "phone number", "social security",
                    "password", "personal email", "date of birth")
@app.post("/api/ask")
def ask(req: AskReq):
    t0 = time.time()
    if any(p in req.question.lower() for p in PRIVACY_PATTERNS):
        return {"question": req.question, "status": "insufficient_evidence",
                "answer": "That asks for personal information, which this system does not retrieve or disclose.",
                "citations": [], "model": get_embedder().name,
                "index_version": config.INDEX_VERSION,
                "retrieval_latency_ms": 0, "total_latency_ms": round((time.time() - t0) * 1000, 1)}
    r = get_retriever()
    hits = r.search(req.question, k=req.k)
    t_ret = time.time()
    if not hits or hits[0]["vector_score"] < 0.08 and hits[0]["lexical_score"] < 0.03:
        return {"question": req.question, "status": "insufficient_evidence",
                "answer": "I don't have enough evidence in the ingested documents to answer that.",
                "citations": [], "model": get_embedder().name,
                "index_version": config.INDEX_VERSION,
                "retrieval_latency_ms": round((t_ret - t0) * 1000, 1),
                "total_latency_ms": round((time.time() - t0) * 1000, 1)}
    # Abstention guard: best hybrid evidence must actually mention question terms
    answer, mode, used = generate(req.question, hits)
    if not answer:
        return {"question": req.question, "status": "insufficient_evidence",
                "answer": "Retrieved passages did not contain a supported answer to that question.",
                "citations": [], "model": get_embedder().name,
                "index_version": config.INDEX_VERSION,
                "retrieval_latency_ms": round((t_ret - t0) * 1000, 1),
                "total_latency_ms": round((time.time() - t0) * 1000, 1)}
    return {"question": req.question, "status": "supported", "answer": answer,
            "citations": _citations(used), "generation_mode": mode,
            "model": get_embedder().name, "index_version": config.INDEX_VERSION,
            "retrieval_latency_ms": round((t_ret - t0) * 1000, 1),
            "generation_latency_ms": round((time.time() - t_ret) * 1000, 1),
            "total_latency_ms": round((time.time() - t0) * 1000, 1)}
