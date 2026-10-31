"""Ingestion: parse PDF/TXT, hash, dedupe, chunk with stable IDs, index."""
import hashlib, io, uuid
from pathlib import Path
import numpy as np
from . import config, store

def parse_pages(name: str, raw: bytes):
    ext = Path(name).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(raw))
        return ext, [(i + 1, (p.extract_text() or "")) for i, p in enumerate(r.pages)]
    if ext in (".txt", ".md"):
        text = raw.decode("utf-8", errors="replace")
        # form-feed separates pages in our text fixtures; otherwise one page
        parts = text.split("\f") if "\f" in text else [text]
        return ext, [(i + 1, t) for i, t in enumerate(parts)]
    raise ValueError(f"unsupported format: {ext or name}")

def chunk_page(text, size=config.CHUNK_CHARS, overlap=config.CHUNK_OVERLAP):
    text = " ".join(text.split())
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size])
        if i + size >= len(text):
            break
        i += size - overlap
    return [c for c in out if c.strip()]

def rebuild_index():
    import faiss
    chunks = store.all_chunks()
    emb = __import__("app.embeddings", fromlist=["get_embedder"]).get_embedder()
    if not chunks:
        return 0
    vecs = emb.embed([c["text"] for c in chunks])
    idx = faiss.IndexFlatIP(vecs.shape[1])
    idx.add(vecs)
    store.save_index(idx, [c["id"] for c in chunks])
    return len(chunks)

def ingest_bytes(name: str, raw: bytes):
    """Returns (ingestion_id, doc_dict, duplicate_bool). Raises ValueError on bad input."""
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise ValueError(f"file too large: {len(raw)} bytes > {config.MAX_UPLOAD_BYTES}")
    ext = Path(name).suffix.lower()
    if ext not in config.ALLOWED_EXTS:
        raise ValueError(f"unsupported format: {ext or '(none)'}")
    sha = hashlib.sha256(raw).hexdigest()
    iid = uuid.uuid4().hex[:12]
    existing = store.doc_by_hash(sha)
    if existing:
        store.set_ingestion(iid, existing["id"], "duplicate",
                            "identical sha256 already ingested; no new chunks created")
        return iid, existing, True
    ext2, pages = parse_pages(name, raw)
    doc_id = "doc_" + sha[:10]
    doc = {"id": doc_id, "name": name, "sha256": sha, "ext": ext2}
    chunks, seq = [], 0
    for page_no, ptext in pages:
        for piece in chunk_page(ptext):
            chunks.append({"id": f"{doc_id}:p{page_no}:c{seq}", "page": page_no,
                           "seq": seq, "text": piece})
            seq += 1
    if not chunks:
        raise ValueError("no extractable text found")
    store.add_document(doc, len(pages), chunks)
    store.set_ingestion(iid, doc_id, "processing", f"{len(chunks)} chunks; indexing")
    rebuild_index()
    store.set_ingestion(iid, doc_id, "completed", f"{len(chunks)} chunks indexed")
    return iid, doc, False
