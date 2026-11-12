"""Keyword search (BM25) over the chunks + a 'is this really in the documents?' check."""
import math
import re
from rank_bm25 import BM25Okapi

STOP = set("""a an the is are was were be been of to in on for from by with at as and or not no
what which who whom how when where why does do did should can could would will shall
it its this that these those there their they them i we you my our me any all about into
than then if else also must may mean means go goes get give need tell show use allowed""".split())

# Words people say on the floor -> words the documents use
SYNONYMS = {"fault": ["alarm"], "often": ["frequency"], "frequent": ["frequency"], "interval": ["frequency"],
            "schedule": ["frequency"], "permitted": ["authorised"], "lockout": ["lock"], "unlock": ["lock", "remove"],
            "part": ["material"], "parts": ["material"], "component": ["material"], "who": ["responsible"],
            "tolerance": ["tolerance"], "limit": ["max"], "oil": ["oil"]}


def stem(w: str) -> str:
    for suf in ("ment", "ing", "es", "s", "ed"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokenize(text: str) -> list[str]:
    toks = []
    for t in re.findall(r"[a-z0-9]+(?:[-./][a-z0-9]+)*", text.lower()):
        parts = [t] + (re.split(r"[-./]", t) if re.search(r"[-./]", t) else [])
        for p in parts:
            if p and p not in STOP:
                toks.append(stem(p))
    return toks


class Searcher:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.docs = [tokenize(f'{c["doc_id"]} {c["title"]} {c["section"]} {c["text"]}') for c in chunks]
        self.bm25 = BM25Okapi(self.docs)
        n = len(self.docs)
        df = {}
        for d in self.docs:
            for t in set(d):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}
        self.max_idf = math.log((n + 1) / 0.5)

    def _expand(self, q: str) -> list[str]:
        toks = tokenize(q)
        for t in list(toks):
            toks += [stem(x) for x in SYNONYMS.get(t, []) if stem(x) not in toks]
        return toks

    def coverage(self, q_tokens: list[str], idx: int) -> float:
        """Share of the question's (rare-word-weighted) terms that appear in this chunk."""
        uniq = set(q_tokens)
        if not uniq:
            return 0.0
        doc = set(self.docs[idx])
        w = lambda t: self.idf.get(t, self.max_idf)  # unknown word = very rare = very important
        return sum(w(t) for t in uniq if t in doc) / sum(w(t) for t in uniq)

    def search(self, question: str, k: int = 4, min_cov: float = 0.3):
        q = self._expand(question)
        scores = self.bm25.get_scores(q)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        hits, old_hits = [], []
        for i in ranked[: k + 4]:
            cov = self.coverage(q, i)
            if scores[i] <= 0 or cov < min_cov:
                continue
            c = {**self.chunks[i], "score": round(float(scores[i]), 2), "coverage": round(cov, 2)}
            (hits if c["is_latest"] else old_hits).append(c)
        return hits[:k], old_hits
