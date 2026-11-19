import math

import pytest

from eval.metrics import (
    ndcg_at_k,
    percentile,
    recall_at_k,
    reciprocal_rank,
    suggest_threshold,
    threshold_curve,
)

REL = {"a": 2, "b": 1, "c": 1}


def test_recall_hit_and_miss():
    assert recall_at_k(["x", "a", "y"], REL, 1) == 0.0
    assert recall_at_k(["x", "a", "y"], REL, 3) == 1.0


def test_recall_ignores_grade_1():
    assert recall_at_k(["b", "c"], REL, 5) == 0.0


def test_recall_any_of_two_answers():
    rel = {"a": 2, "d": 2}
    assert recall_at_k(["d", "x"], rel, 1) == 1.0


def test_recall_empty_list():
    assert recall_at_k([], REL, 5) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(["a"], REL) == 1.0
    assert reciprocal_rank(["b", "x", "a"], REL) == pytest.approx(1 / 3)
    assert reciprocal_rank(["b", "c"], REL) == 0.0
    assert reciprocal_rank([], REL) == 0.0


def test_ndcg_perfect_order():
    assert ndcg_at_k(["a", "b", "c"], REL, 5) == pytest.approx(1.0)


def test_ndcg_by_hand():
    # ranked: b(1), x(0), a(2) -> DCG = 1/log2(2) + 0 + 2/log2(4) = 1 + 1 = 2
    # ideal:  a(2), b(1), c(1) -> IDCG = 2 + 1/log2(3) + 1/log2(4)
    idcg = 2 + 1 / math.log2(3) + 0.5
    assert ndcg_at_k(["b", "x", "a"], REL, 5) == pytest.approx(2 / idcg)


def test_ndcg_cutoff_limits_ideal():
    # k=1: IDCG considera só a melhor nota (grau 2)
    assert ndcg_at_k(["b"], REL, 1) == pytest.approx(0.5)


def test_ndcg_empty_cases():
    assert ndcg_at_k([], REL, 5) == 0.0
    assert ndcg_at_k(["a"], {}, 5) == 0.0


def test_percentile():
    assert percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)
    assert percentile([10], 95) == 10
    assert percentile([], 50) == 0.0


def test_threshold_curve_and_suggestion():
    answerable = [(["a", "b"], {"a": 0.6, "b": 0.3}, {"a": 2})]
    no_answer = [(["z"], {"z": 0.5}), (["y"], {"y": 0.2})]
    curve = threshold_curve(answerable, no_answer, [0.0, 0.4, 0.55, 0.7])
    assert [c["fp_rate"] for c in curve] == [1.0, 0.5, 0.0, 0.0]
    assert [c["recall"] for c in curve] == [1.0, 1.0, 1.0, 0.0]
    best = suggest_threshold(curve, max_fp=0.1)
    assert best["threshold"] == 0.55
    assert suggest_threshold(curve[:2], max_fp=0.1) is None
