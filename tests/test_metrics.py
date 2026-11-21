"""Test cho các chỉ số đánh giá — so với giá trị tính tay."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.medajob.evaluate import evaluate_ranking


def make_case():
    """2 user, 5 job. User 0 thích job 1 và 3; user 1 thích job 4.

    Điểm số được đặt để thứ hạng đã biết trước, nhờ đó tính tay được.
    """
    scores = np.array([
        [0.9, 0.8, 0.7, 0.6, 0.1],   # user 0: top = 0,1,2,3,4
        [0.9, 0.8, 0.7, 0.6, 0.5],   # user 1: top = 0,1,2,3,4
    ])
    test = np.zeros((2, 5))
    test[0, 1] = 5.0   # liên quan
    test[0, 3] = 4.0   # liên quan
    test[1, 4] = 5.0   # liên quan
    train_mask = np.zeros((2, 5), dtype=bool)
    return scores, test, train_mask


def test_recall_at_k_by_hand():
    scores, test, Mtr = make_case()
    r = evaluate_ranking(scores, test, Mtr, k_list=(2,), relevant_threshold=4,
                         n_boot=10)
    # User 0: top-2 = {0,1}, liên quan {1,3} -> 1 hit / 2 liên quan = 0.5
    # User 1: top-2 = {0,1}, liên quan {4}   -> 0 hit / 1 = 0.0
    assert r["recall@2"] == pytest.approx(0.25)  # trung bình (0.5 + 0)/2


def test_precision_at_k_by_hand():
    scores, test, Mtr = make_case()
    r = evaluate_ranking(scores, test, Mtr, k_list=(2,), relevant_threshold=4,
                         n_boot=10)
    # User 0: 1 hit / 2 = 0.5 ; User 1: 0/2 = 0 -> trung bình 0.25
    assert r["precision@2"] == pytest.approx(0.25)


def test_ndcg_at_k_by_hand():
    scores, test, Mtr = make_case()
    r = evaluate_ranking(scores, test, Mtr, k_list=(2,), relevant_threshold=4,
                         n_boot=10)
    # User 0: DCG = 0/log2(2) + 1/log2(3) = 0.6309
    #         IDCG (2 liên quan) = 1/log2(2) + 1/log2(3) = 1.6309
    #         NDCG = 0.38685
    # User 1: DCG = 0 -> NDCG = 0
    expected = (0.0 / 1.0 + 1.0 / np.log2(3)) / (1.0 + 1.0 / np.log2(3)) / 2
    assert r["ndcg@2"] == pytest.approx(expected, rel=1e-6)


def test_mrr_by_hand():
    scores, test, Mtr = make_case()
    r = evaluate_ranking(scores, test, Mtr, k_list=(5,), relevant_threshold=4,
                         n_boot=10)
    # User 0: liên quan đầu tiên ở hạng 2 -> RR = 1/2
    # User 1: liên quan ở hạng 5 -> RR = 1/5
    assert r["mrr@5"] == pytest.approx((0.5 + 0.2) / 2)


def test_seen_items_are_excluded():
    """Tin đã có trong train không được xuất hiện lại trong gợi ý."""
    scores = np.array([[0.9, 0.8, 0.7]])
    test = np.zeros((1, 3))
    test[0, 2] = 5.0
    Mtr = np.zeros((1, 3), dtype=bool)
    Mtr[0, 0] = True  # job 0 đã tương tác

    r = evaluate_ranking(scores, test, Mtr, k_list=(2,),
                         relevant_threshold=4, n_boot=10)
    # Sau khi ẩn job 0, top-2 = {1, 2}; job 2 liên quan -> recall = 1.0
    assert r["recall@2"] == pytest.approx(1.0)


def test_users_without_relevant_items_are_skipped():
    """User không có tin liên quan KHÔNG được tính vào mẫu số."""
    scores = np.array([[0.9, 0.8], [0.1, 0.2]])
    test = np.zeros((2, 2))
    test[0, 1] = 5.0     # chỉ user 0 có liên quan
    Mtr = np.zeros((2, 2), dtype=bool)

    r = evaluate_ranking(scores, test, Mtr, k_list=(2,),
                         relevant_threshold=4, n_boot=10)
    assert r["n_eval"] == 1
    assert r["recall@2"] == pytest.approx(1.0)


def test_no_relevant_items_returns_error():
    scores = np.zeros((2, 3))
    test = np.zeros((2, 3))
    Mtr = np.zeros((2, 3), dtype=bool)
    r = evaluate_ranking(scores, test, Mtr, k_list=(2,), n_boot=10)
    assert r["n_eval"] == 0
    assert "error" in r


def test_ci_contains_mean():
    scores, test, Mtr = make_case()
    r = evaluate_ranking(scores, test, Mtr, k_list=(2,), n_boot=200, seed=1)
    ci = r["recall@2_ci"]
    assert ci["lo"] <= ci["mean"] <= ci["hi"]
    assert ci["n"] == 2


def test_perfect_ranking_scores_one():
    """Xếp hạng hoàn hảo phải cho Recall = 1 và NDCG = 1."""
    scores = np.array([[0.9, 0.1], [0.9, 0.1]])
    test = np.array([[5.0, 0.0], [5.0, 0.0]])
    Mtr = np.zeros((2, 2), dtype=bool)
    r = evaluate_ranking(scores, test, Mtr, k_list=(1,),
                         relevant_threshold=4, n_boot=10)
    assert r["recall@1"] == pytest.approx(1.0)
    assert r["ndcg@1"] == pytest.approx(1.0)
    assert r["mrr@1"] == pytest.approx(1.0)
