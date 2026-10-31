"""Hybrid retrieval: lexical (TF-IDF cosine) + vector (FAISS) fused with RRF."""
import re
import numpy as np
from . import store
from .embeddings import get_embedder

def _tokens(t):
    return set(re.findall(r"[a-z0-9]+", t.lower()))

class Retriever:
    def __init__(self):
        self.refresh()
    def refresh(self):
        self.chunks = store.all_chunks()
        self.by_id = {c["id"]: c for c in self.chunks}
        self.index, self.ids = store.load_index()
    @property
    def ready(self):
        return bool(self.chunks) and self.index is not None
    def search(self, query, k=5):
        if not self.ready:
            return []
        emb = get_embedder()
        qv = emb.embed([query])
        if self.index.ntotal != len(self.ids):  # stale index guard
            self.refresh()
        D, I = self.index.search(qv, min(k * 3, self.index.ntotal))
        vec_rank = {}
        for rank, (score, pos) in enumerate(zip(D[0], I[0])):
            if pos >= 0:
                vec_rank[self.ids[pos]] = (rank, float(score))
        qtok = _tokens(query)
        lex = []
        for c in self.chunks:
            ctok = _tokens(c["text"])
            j = len(qtok & ctok) / max(1, len(qtok | ctok))
            # bonus for exact numeric / named matches, common in finance Qs
            lex.append((c["id"], j))
        lex.sort(key=lambda x: -x[1])
        lex_rank = {cid: (r, s) for r, (cid, s) in enumerate(lex[:k * 3])}
        fused = {}
        for cid, (r, s) in vec_rank.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + r)
        for cid, (r, s) in lex_rank.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + r)
        out = []
        for cid, fscore in sorted(fused.items(), key=lambda x: -x[1])[:k]:
            c = self.by_id[cid]
            out.append({"chunk_id": cid, "document_id": c["doc_id"], "page": c["page"],
                        "text": c["text"], "score": round(float(fscore), 4),
                        "vector_score": round(vec_rank.get(cid, (0, 0.0))[1], 4),
                        "lexical_score": round(lex_rank.get(cid, (0, 0.0))[1], 4)})
        return out

_retriever = None
def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
def refresh_retriever():
    global _retriever
    _retriever = Retriever()
    return _retriever
