"""Embedding backends. Primary: all-MiniLM-L6-v2 via fastembed (ONNX, CPU).
Fallback: TF-IDF (used in tests / if the model cannot be downloaded) — the
active backend is always reported honestly by the API."""
import numpy as np
from . import config

class FastEmbedEmbedder:
    name = config.EMBED_MODEL
    def __init__(self):
        from fastembed import TextEmbedding
        self._m = TextEmbedding(model_name=config.EMBED_MODEL)
        self.dim = 384
    def embed(self, texts):
        v = np.array(list(self._m.embed(texts)), dtype="float32")
        n = np.linalg.norm(v, axis=1, keepdims=True); n[n == 0] = 1
        return v / n

class TfidfEmbedder:
    name = "tfidf-fallback (not a neural embedding model)"
    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._v = TfidfVectorizer(max_features=4096)
        self.dim = 4096
        self._fitted = False
    def embed(self, texts):
        if not self._fitted:
            self._v.fit(texts); self._fitted = True
        v = self._v.transform(texts).toarray().astype("float32")
        n = np.linalg.norm(v, axis=1, keepdims=True); n[n == 0] = 1
        return v / n

_embedder = None
def get_embedder():
    global _embedder
    if _embedder is None:
        if config.EMBEDDER == "tfidf":
            _embedder = TfidfEmbedder()
        else:
            _embedder = FastEmbedEmbedder()
    return _embedder
