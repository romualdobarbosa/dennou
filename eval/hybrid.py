"""BM25 e fusão de rankings pro experimento de busca híbrida (só stdlib).

- `tokenize` normaliza pra minúsculas sem acento e quebra em [a-z0-9_]+, então
  `--hard` vira `hard` e "função" casa com "funcao".
- `BM25` é o Okapi clássico (k1, b), um documento por nota.
- `rrf` é Reciprocal Rank Fusion: score = soma de 1/(k + posição) nas listas.
- `weighted` soma alpha * cosseno + (1 - alpha) * BM25 dividido pelo maior
  BM25 da pergunta (fica em [0, 1], na mesma escala do cosseno).
"""

import math
import re
import unicodedata
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _TOKEN.findall(text)


class BM25:
    def __init__(self, docs: dict[str, str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = {doc_id: Counter(tokenize(text)) for doc_id, text in docs.items()}
        self.len = {doc_id: sum(tf.values()) for doc_id, tf in self.tf.items()}
        self.avg_len = sum(self.len.values()) / len(self.len) if self.len else 0.0
        df = Counter(term for tf in self.tf.values() for term in tf)
        n = len(self.tf)
        # IDF do Lucene: sempre positivo, mesmo pra termo em mais da metade dos docs.
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> dict[str, float]:
        terms = [t for t in tokenize(query) if t in self.idf]
        out = {}
        for doc_id, tf in self.tf.items():
            norm = self.k1 * (1 - self.b + self.b * self.len[doc_id] / self.avg_len)
            s = 0.0
            for t in terms:
                f = tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out[doc_id] = s
        return out


def ranking(scores: dict[str, float]) -> list[str]:
    """Ids em ordem de score decrescente; empate desfeito pelo id."""
    return sorted(scores, key=lambda d: (-scores[d], d))


def rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    out: dict[str, float] = {}
    for ranked in rankings:
        for pos, doc_id in enumerate(ranked, start=1):
            out[doc_id] = out.get(doc_id, 0.0) + 1.0 / (k + pos)
    return out


def weighted(cosine: dict[str, float], bm25: dict[str, float], alpha: float) -> dict[str, float]:
    top = max(bm25.values(), default=0.0)
    return {
        d: alpha * cosine[d] + (1 - alpha) * (bm25.get(d, 0.0) / top if top > 0 else 0.0)
        for d in cosine
    }
