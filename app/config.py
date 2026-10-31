import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DOCULENS_DATA_DIR", ROOT / "artifacts"))
DB_PATH = DATA_DIR / "doculens.db"
INDEX_PATH = DATA_DIR / "index.faiss"
EMBED_MODEL = os.getenv("DOCULENS_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDER = os.getenv("DOCULENS_EMBEDDER", "fastembed")  # fastembed | tfidf
GENERATOR = os.getenv("DOCULENS_GENERATOR", "auto")  # auto | t5 | extractive
T5_MODEL = os.getenv("DOCULENS_T5_MODEL", "google/flan-t5-small")
CHUNK_CHARS = 900
CHUNK_OVERLAP = 150
MAX_UPLOAD_BYTES = int(os.getenv("DOCULENS_MAX_UPLOAD_MB", "5")) * 1024 * 1024
ALLOWED_EXTS = {".pdf", ".txt", ".md"}
# Abstention: combined hybrid score of the best chunk must clear this bar,
# tuned on the eval tuning split (see eval/questions.json, scripts/evaluate.py).
ABSTAIN_THRESHOLD = float(os.getenv("DOCULENS_ABSTAIN_THRESHOLD", "0.18"))
INDEX_VERSION = f"emb={EMBED_MODEL};chunk={CHUNK_CHARS}/{CHUNK_OVERLAP};v1"
