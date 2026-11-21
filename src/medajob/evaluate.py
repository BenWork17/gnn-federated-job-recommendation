"""
Chỉ số đánh giá xếp hạng, tính ở MỨC TỪNG USER rồi mới lấy trung bình.

Vì sao tính theo user rồi trung bình (macro) chứ không gộp tất cả:
  Mỗi user có số tin "liên quan" rất khác nhau (1 đến 52). Nếu gộp, user
  có nhiều tin liên quan sẽ chi phối chỉ số, và con số cuối cùng không còn
  trả lời câu hỏi "một người dùng điển hình được gợi ý tốt đến đâu".

Quy ước:
  - Chỉ đánh giá trên user có ít nhất 1 tin liên quan trong test.
  - Tin "liên quan" = rating >= ngưỡng (mặc định 4) trong test.
  - Ẩn khỏi danh sách gợi ý các tin đã biết trong TRAIN (không ẩn test,
    nếu ẩn thì không bao giờ có hit).
  - Top-K cắt sau khi đã ẩn, nên K là số tin thực sự nhìn thấy.
"""

from __future__ import annotations

import numpy as np

from src.common import bootstrap_ci


def _dcg(rels: np.ndarray) -> float:
    if rels.size == 0:
        return 0.0
    return float(np.sum(rels / np.log2(np.arange(2, rels.size + 2))))


def evaluate_ranking(
    scores: np.ndarray,
    test: np.ndarray,
    train_mask: np.ndarray,
    k_list: tuple[int, ...] = (10, 20),
    relevant_threshold: float = 4.0,
    n_boot: int = 1000,
    seed: int = 42,
) -> dict:
    """Trả về dict: chỉ số trung bình, CI 95% và phân bố theo từng user.

    `scores` có thể chứa -inf (đã ẩn) hoặc NaN; cả hai đều bị coi là không
    hợp lệ và bị đẩy xuống cuối danh sách.
    """
    scores = np.nan_to_num(np.asarray(scores, dtype=np.float64),
                           nan=-np.inf, posinf=np.inf, neginf=-np.inf)
    n_users, n_jobs = scores.shape
    rel_all = test >= relevant_threshold

    # ẩn tin đã biết trong train
    masked = scores.copy()
    masked[train_mask] = -np.inf

    # sắp xếp 1 lần, dùng cho mọi K
    order = np.argsort(-masked, axis=1)
    valid = np.isfinite(np.take_along_axis(masked, order, axis=1))

    result: dict = {"per_user": {}, "n_jobs": int(n_jobs)}
    max_k = max(k_list)

    per_user_recall = {k: [] for k in k_list}
    per_user_ndcg = {k: [] for k in k_list}
    per_user_mrr = {k: [] for k in k_list}
    per_user_prec = {k: [] for k in k_list}
    recommended_at_max: set[int] = set()
    evaluated_users: list[int] = []

    for u in range(n_users):
        rel = set(np.where(rel_all[u])[0].tolist())
        if not rel:
            continue
        evaluated_users.append(u)
        top = order[u][valid[u]][:max_k]
        recommended_at_max.update(top.tolist())

        for k in k_list:
            topk = top[:k]
            hits = rel.intersection(topk.tolist())
            per_user_prec[k].append(len(hits) / k)
            per_user_recall[k].append(len(hits) / len(rel))
            ideal = _dcg(np.ones(min(len(rel), k)))
            gain = _dcg(np.array([1.0 if j in rel else 0.0 for j in topk]))
            per_user_ndcg[k].append(gain / ideal if ideal > 0 else 0.0)
            rr = 0.0
            for rank, j in enumerate(topk, start=1):
                if j in rel:
                    rr = 1.0 / rank
                    break
            per_user_mrr[k].append(rr)

    if not evaluated_users:
        return {"error": "no user has a relevant item in test", "n_eval": 0}

    for k in k_list:
        result[f"precision@{k}"] = float(np.mean(per_user_prec[k]))
        result[f"recall@{k}"] = float(np.mean(per_user_recall[k]))
        result[f"ndcg@{k}"] = float(np.mean(per_user_ndcg[k]))
        result[f"mrr@{k}"] = float(np.mean(per_user_mrr[k]))
        result[f"recall@{k}_ci"] = bootstrap_ci(per_user_recall[k], n_boot, seed=seed)
        result[f"ndcg@{k}_ci"] = bootstrap_ci(per_user_ndcg[k], n_boot, seed=seed)
        result[f"mrr@{k}_ci"] = bootstrap_ci(per_user_mrr[k], n_boot, seed=seed)

    result["coverage@%d" % max_k] = len(recommended_at_max) / n_jobs
    result["n_eval"] = len(evaluated_users)
    result["evaluated_users"] = [int(u) for u in evaluated_users]
    result["per_user"] = {
        "user_index": [int(u) for u in evaluated_users],
        "recall": {str(k): [float(x) for x in per_user_recall[k]] for k in k_list},
        "ndcg": {str(k): [float(x) for x in per_user_ndcg[k]] for k in k_list},
        "mrr": {str(k): [float(x) for x in per_user_mrr[k]] for k in k_list},
    }
    return result


def top_k_recommendations(scores: np.ndarray, user_idx: int,
                          train_mask: np.ndarray, k: int = 20) -> list[tuple[int, float]]:
    """Danh sách (job_index, score) đã ẩn tin user từng tương tác."""
    s = np.array(scores[user_idx], dtype=np.float64, copy=True)
    s[train_mask[user_idx]] = -np.inf
    order = np.argsort(-s)[:k]
    return [(int(j), float(s[j])) for j in order if np.isfinite(s[j])]


def rmse(scores: np.ndarray, test: np.ndarray, threshold: float = 0.0) -> float:
    """RMSE trên các ô test có rating (chỉ dùng cho mô hình explicit)."""
    mask = test > threshold
    if mask.sum() == 0:
        return float("nan")
    pred = np.clip(scores[mask], 1.0, 5.0)
    return float(np.sqrt(np.mean((pred - test[mask]) ** 2)))
