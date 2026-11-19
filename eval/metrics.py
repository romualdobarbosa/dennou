"""Métricas de retrieval para o eval (só stdlib, fácil de testar).

Convenções:
- `ranked` é a lista de ids de nota em ordem de score decrescente, já sem
  duplicatas (uma nota aparece uma vez só, mesmo com chunking).
- `relevant` mapeia id -> grau (2 = responde, 1 = relacionada); nota ausente
  vale 0.
- Recall@k é "pelo menos uma nota de grau 2 no top-k" (0 ou 1 por pergunta).
  Com duas notas de grau 2 (ex. WHERE vs HAVING), achar uma já conta.
- MRR usa a posição da primeira nota de grau 2.
- nDCG@k usa ganho linear igual ao grau (2/1) e desconto log2(posição + 1);
  o IDCG vem das notas relevantes ordenadas por grau.
"""

import math

ANSWER = 2


def recall_at_k(ranked: list[str], relevant: dict[str, int], k: int) -> float:
    """1.0 se alguma nota de grau 2 está no top-k, senão 0.0."""
    return 1.0 if any(relevant.get(n, 0) >= ANSWER for n in ranked[:k]) else 0.0


def reciprocal_rank(ranked: list[str], relevant: dict[str, int]) -> float:
    """1/posição da primeira nota de grau 2 na lista, ou 0.0 se não aparece."""
    for i, n in enumerate(ranked, start=1):
        if relevant.get(n, 0) >= ANSWER:
            return 1.0 / i
    return 0.0


def dcg(gains: list[int]) -> float:
    return sum(g / math.log2(i + 1) for i, g in enumerate(gains, start=1))


def ndcg_at_k(ranked: list[str], relevant: dict[str, int], k: int) -> float:
    """nDCG@k com ganhos graduados. Sem nenhuma nota relevante, devolve 0.0."""
    ideal = sorted((g for g in relevant.values() if g > 0), reverse=True)[:k]
    idcg = dcg(ideal)
    if idcg == 0:
        return 0.0
    return dcg([relevant.get(n, 0) for n in ranked[:k]]) / idcg


def percentile(values: list[float], p: float) -> float:
    """Percentil com interpolação linear (igual ao default do numpy)."""
    if not values:
        return 0.0
    xs = sorted(values)
    pos = (len(xs) - 1) * p / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def thresholded(ranked: list[str], scores: dict[str, float], threshold: float) -> list[str]:
    """Mantém só as notas com score >= threshold (a regra do agente é score >= 0.4)."""
    return [n for n in ranked if scores[n] >= threshold]


def threshold_curve(
    answerable: list[tuple[list[str], dict[str, float], dict[str, int]]],
    no_answer: list[tuple[list[str], dict[str, float]]],
    thresholds: list[float],
    k: int = 5,
) -> list[dict]:
    """
    Para cada threshold:
    - fp_rate: fração das perguntas sem resposta cujo top-1 tem score >= threshold
      (o agente usaria uma nota que não responde nada);
    - recall: Recall@k das perguntas com resposta, contando só notas acima do threshold.
    """
    curve = []
    for t in thresholds:
        fp = [1.0 if r and s[r[0]] >= t else 0.0 for r, s in no_answer]
        rec = [recall_at_k(thresholded(r, s, t), rel, k) for r, s, rel in answerable]
        curve.append({"threshold": round(t, 2), "fp_rate": mean(fp), "recall": mean(rec)})
    return curve


def suggest_threshold(curve: list[dict], max_fp: float = 0.10) -> dict | None:
    """
    Maior recall com fp_rate <= max_fp. Empate: menor fp_rate, depois o maior
    threshold (mais conservador). None se nenhum threshold atende.
    """
    ok = [c for c in curve if c["fp_rate"] <= max_fp + 1e-9]
    if not ok:
        return None
    return max(ok, key=lambda c: (c["recall"], -c["fp_rate"], c["threshold"]))
