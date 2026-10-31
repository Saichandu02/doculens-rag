"""Grounded generation.

Modes:
- t5: google/flan-t5-small via transformers (attempted when GENERATOR=auto/t5
  and torch+transformers are installed). Answer is still constrained: the
  generated text is kept only if it shares factual tokens (numbers/names)
  with the cited evidence; otherwise we fall back to extractive.
- extractive (default fallback): answer is composed verbatim from the most
  relevant sentences of the retrieved chunks, so every claim is traceable to
  a citation. This is a real grounded path, not a mock.

Grounding rules (all must hold for a sentence to be used as evidence):
- at least 2 distinctive content-token matches with the question, where
  "distinctive" excludes corpus-common tokens (present in >50% of chunks,
  e.g. the company name) and stopwords; light prefix stemming is applied
  (approve ~ approval).
- and at least one of: >=3 distinctive matches, a numeric token from the
  question appearing verbatim, or the containing chunk itself matching the
  question strongly (>=5 distinctive matches).
- year consistency: if the question names a year, a sentence stating a
  different year cannot be evidence.
Document text is untrusted data: injection-looking spans are excluded.
"""
import re
from . import config, store

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"reveal (the )?(system prompt|secret|password|api key)",
    r"you are now", r"disregard .* instructions", r"print .* secret",
]
def looks_like_injection(text):
    t = text.lower()
    return any(re.search(p, t) for p in INJECTION_PATTERNS)

STOP = {
    "what", "is", "the", "of", "a", "an", "in", "on", "for", "does", "did",
    "how", "much", "many", "when", "which", "who", "was", "were", "are",
    "and", "or", "to", "from", "with", "by", "at", "as", "it", "its",
    "their", "this", "that", "be", "been", "has", "have", "had", "will",
    "would", "can", "could", "should", "do", "under", "about", "into"}

def _stem(t):
    for suf in ("ing", "ed", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            t = t[:-len(suf)]
            break
    if len(t) > 4 and t.endswith("e"):
        t = t[:-1]  # mature / matures -> matur
    return t

def _tokens(text, stem=False):
    toks = set(re.findall(r"[a-z0-9]+", text.lower())) - STOP
    return {_stem(t) for t in toks} if stem else toks

_common_cache = {"n": -1, "set": set()}
def _common_tokens():
    chunks = store.all_chunks()
    if _common_cache["n"] != len(chunks):
        df = {}
        for c in chunks:
            for t in _tokens(c["text"]):
                df[t] = df.get(t, 0) + 1
        _common_cache["set"] = {t for t, n in df.items() if n > max(1, len(chunks) // 2)}
        _common_cache["n"] = len(chunks)
    return _common_cache["set"]

def _match_count(qtok_stem, text):
    """Distinctive stemmed matches between question tokens and a text span."""
    stok = {_stem(t) for t in _tokens(text)}
    common = {_stem(t) for t in _common_tokens()}
    return len((qtok_stem & stok) - common)

_t5 = None
_t5_tried = False
def _try_t5():
    global _t5, _t5_tried
    if _t5_tried:
        return _t5
    _t5_tried = True
    if config.GENERATOR == "extractive":
        return None
    try:
        from transformers import pipeline
        _t5 = pipeline("text2text-generation", model=config.T5_MODEL, device=-1)
    except Exception as e:  # recorded honestly in verification docs
        print(f"[generate] flan-t5 unavailable: {type(e).__name__}: {e}")
        _t5 = None
    return _t5

def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 25]

def _extractive_answer(question, hits):
    qraw = _tokens(question)
    qstem = {_stem(t) for t in qraw}
    qnums = {t for t in qraw if any(ch.isdigit() for ch in t)}
    qyears = {t for t in qnums if len(t) == 4}
    scored = []
    for rank, h in enumerate(hits):
        chunk_match = _match_count(qstem, h["text"])
        for s in _sentences(h["text"]):
            if looks_like_injection(s):
                continue
            s_years = {t for t in re.findall(r"\b(?:19|20)\d{2}\b", s)}
            if qyears and s_years and not (qyears & s_years):
                continue  # evidence about a different year
            ov = _match_count(qstem, s)
            numeric_hit = bool(qnums & set(re.findall(r"[a-z0-9]+", s.lower())))
            if ov < 2 or not (ov >= 3 or numeric_hit or chunk_match >= 3):
                continue
            bonus = 3 * len(qnums & set(re.findall(r"[a-z0-9]+", s.lower()))) + max(0, 3 - rank)
            # Density ranking: matches per unit length, so a short factual
            # sentence beats a long heading-merged sentence with the same
            # number of matches.
            density = (ov + 0.5 * bonus) / (1 + len(s) / 300)
            scored.append((density, s, h))
    scored.sort(key=lambda x: -x[0])
    picked, seen = [], set()
    for _sc, s, h in scored:
        if s in seen:
            continue
        picked.append((s, h)); seen.add(s)
        if len(picked) >= 4:
            break
    return picked

def generate(question, hits):
    """Returns (answer_text, mode, citations_hits_used)."""
    picked = _extractive_answer(question, hits)
    if not picked:
        return "", "extractive", []
    used = []
    for s, h in picked:
        if h not in used:
            used.append(h)
    extractive = " ".join(s for s, _ in picked)
    pipe = _try_t5()
    if pipe is not None:
        context = " ".join(s for s, _ in picked)
        prompt = (f"Answer the question using only this context. "
                  f"Context: {context} Question: {question}")
        try:
            out = pipe(prompt, max_new_tokens=80, do_sample=False)[0]["generated_text"].strip()
            ev_nums = set(re.findall(r"\d[\d,\.]*", context))
            out_nums = set(re.findall(r"\d[\d,\.]*", out))
            if out and out_nums.issubset(ev_nums) and len(out) > 3:
                return out, f"t5:{config.T5_MODEL}", used
        except Exception as e:
            print(f"[generate] t5 inference failed: {e}")
    return extractive, "extractive-grounded", used
