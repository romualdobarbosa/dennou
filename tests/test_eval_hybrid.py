import pytest

from eval import hybrid as h


def test_tokenize_lowercases_strips_accents_and_punctuation():
    assert h.tokenize("Função `git reset --hard` É") == ["funcao", "git", "reset", "hard", "e"]


def test_bm25_ranks_doc_with_rare_query_term_first():
    bm25 = h.BM25(
        {
            "a": "git reset desfaz commits locais",
            "b": "git revert cria um commit novo",
            "c": "receita de pão de queijo",
        }
    )
    scores = bm25.scores("como usar git revert")
    assert h.ranking(scores)[0] == "b"
    assert scores["c"] == 0.0


def test_bm25_unknown_query_terms_score_zero():
    bm25 = h.BM25({"a": "alpha", "b": "beta"})
    assert bm25.scores("gamma") == {"a": 0.0, "b": 0.0}


def test_ranking_breaks_ties_by_id():
    assert h.ranking({"b": 1.0, "a": 1.0, "c": 2.0}) == ["c", "a", "b"]


def test_rrf_sums_reciprocal_ranks():
    fused = h.rrf([["a", "b"], ["b", "a", "c"]], k=0)
    assert fused == pytest.approx({"a": 1 + 1 / 2, "b": 1 / 2 + 1, "c": 1 / 3})


def test_weighted_normalizes_bm25_by_query_max():
    fused = h.weighted({"a": 0.8, "b": 0.4}, {"a": 0.0, "b": 10.0}, alpha=0.5)
    assert fused == pytest.approx({"a": 0.4, "b": 0.7})


def test_weighted_without_lexical_match_is_scaled_cosine():
    fused = h.weighted({"a": 0.8}, {"a": 0.0}, alpha=0.7)
    assert fused == pytest.approx({"a": 0.56})
