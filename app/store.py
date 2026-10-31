"""SQLite metadata store + FAISS index persistence."""
import json, sqlite3, threading
from pathlib import Path
import numpy as np
from . import config

_lock = threading.Lock()

def _conn():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS documents(
          id TEXT PRIMARY KEY, name TEXT, sha256 TEXT UNIQUE, ext TEXT,
          pages INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS chunks(
          id TEXT PRIMARY KEY, doc_id TEXT, page INTEGER, seq INTEGER, text TEXT);
        CREATE TABLE IF NOT EXISTS ingestions(
          id TEXT PRIMARY KEY, doc_id TEXT, status TEXT, detail TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)

def doc_by_hash(h):
    with _conn() as c:
        r = c.execute("SELECT * FROM documents WHERE sha256=?", (h,)).fetchone()
        return dict(r) if r else None

def add_document(doc, pages, chunks):
    with _lock, _conn() as c:
        c.execute("INSERT INTO documents(id,name,sha256,ext,pages) VALUES(?,?,?,?,?)",
                  (doc["id"], doc["name"], doc["sha256"], doc["ext"], pages))
        c.executemany("INSERT INTO chunks(id,doc_id,page,seq,text) VALUES(?,?,?,?,?)",
                      [(ch["id"], doc["id"], ch["page"], ch["seq"], ch["text"]) for ch in chunks])

def set_ingestion(iid, doc_id, status, detail=""):
    with _lock, _conn() as c:
        c.execute("INSERT OR REPLACE INTO ingestions(id,doc_id,status,detail) VALUES(?,?,?,?)",
                  (iid, doc_id, status, detail))

def get_ingestion(iid):
    with _conn() as c:
        r = c.execute("SELECT * FROM ingestions WHERE id=?", (iid,)).fetchone()
        return dict(r) if r else None

def all_chunks():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM chunks ORDER BY doc_id, seq")]

def page_text(doc_id, page):
    with _conn() as c:
        rows = c.execute("SELECT text FROM chunks WHERE doc_id=? AND page=? ORDER BY seq",
                         (doc_id, page)).fetchall()
        doc = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not rows or not doc:
            return None
        return {"document_id": doc_id, "name": doc["name"], "page": page,
                "text": "\n".join(r["text"] for r in rows)}

def save_index(index, chunk_ids):
    import faiss
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(config.INDEX_PATH))
    (config.DATA_DIR / "chunk_ids.json").write_text(json.dumps(chunk_ids))

def load_index():
    import faiss
    if not config.INDEX_PATH.exists():
        return None, []
    idx = faiss.read_index(str(config.INDEX_PATH))
    ids = json.loads((config.DATA_DIR / "chunk_ids.json").read_text())
    return idx, ids

def counts():
    with _conn() as c:
        d = c.execute("SELECT COUNT(*) n FROM documents").fetchone()["n"]
        ch = c.execute("SELECT COUNT(*) n FROM chunks").fetchone()["n"]
        return d, ch
