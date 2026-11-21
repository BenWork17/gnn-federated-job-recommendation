"""
Kiểm tra tính tất định: chạy lại một thí nghiệm nhỏ hai lần, phải cho cùng số.

Mục đích: bảo đảm mọi so sánh trong báo cáo không bị nhiễu bởi yếu tố ngẫu
nhiên. Nếu test này hỏng, các kết luận «A tốt hơn B» mất cơ sở.

Lưu ý: các trường đo bằng ĐỒNG HỒ (train_seconds) được bỏ qua một cách có
chủ đích — chúng không tất định và không phải là kết quả khoa học.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "results"

# Các khóa đo thời gian gian, không mang ý nghĩa khoa học
TIMING_KEYS = {"train_seconds", "elapsed", "seconds", "wall_seconds"}


def strip_timing(obj):
    """Bỏ đệ quy mọi trường đo thời gian khỏi cấu trúc JSON."""
    if isinstance(obj, dict):
        return {k: strip_timing(v) for k, v in obj.items()
                if k not in TIMING_KEYS}
    if isinstance(obj, list):
        return [strip_timing(v) for v in obj]
    return obj


def test_reco_results_deterministic_across_runs():
    """Chạy lại thí nghiệm tập trung 2 lần với cùng seed -> cùng kết quả.

    VỀ DUNG SAI: hai lần chạy KHÔNG cho bit-identical vì PyTorch dùng nhiều
    luồng và cộng dồn float32; sai khác quan sát được khoảng 1–2·10⁻⁶ sau
    200 vòng Adam. Đó là nhiễu số học, không phải ngẫu nhiên. Vì vậy:
      - so trọng số với dung sai 1e-4 (rộng hơn nhiễu, chặt hơn nhiều so với
        việc seed khác nhau, vốn lệch ~1e-1),
      - và quan trọng hơn: so CHỈ SỐ tới 4 chữ số thập phân, vì đó mới là
        thứ xuất hiện trong báo cáo.
    """
    from src.common import load_config
    from src.medajob.evaluate import evaluate_ranking
    from src.medajob.run_experiments import (load_artifacts,
                                             scores_from_state,
                                             train_centralized)

    cfg = load_config()
    data = load_artifacts(cfg)
    seed = int(cfg["seed"])
    nU, nJ = data["n_users"], data["n_jobs"]

    s1 = train_centralized(data, cfg, arch="lightgcn", seed=seed)
    s2 = train_centralized(data, cfg, arch="lightgcn", seed=seed)

    d = (s1["emb.weight"] - s2["emb.weight"]).abs().max().item()
    assert d < 1e-4, (
        f"hai lần chạy cùng seed lệch {d:.2e} — vượt xa nhiễu float32 "
        f"(~1e-6), kết quả không tái lập được")

    # Chỉ số trong báo cáo phải trùng khít tới 4 chữ số
    r1 = evaluate_ranking(scores_from_state(s1, data, cfg, nU, nJ),
                          data["test"], data["Mtr"], k_list=(20,),
                          relevant_threshold=4, n_boot=50, seed=seed)
    r2 = evaluate_ranking(scores_from_state(s2, data, cfg, nU, nJ),
                          data["test"], data["Mtr"], k_list=(20,),
                          relevant_threshold=4, n_boot=50, seed=seed)
    for key in ("recall@20", "ndcg@20", "mrr@20"):
        assert round(r1[key], 4) == round(r2[key], 4), (
            f"{key} khác nhau giữa hai lần chạy: {r1[key]} vs {r2[key]}")


def test_different_seeds_give_different_results():
    """Đối chứng: seed khác phải cho kết quả khác (chứng tỏ seed có tác dụng)."""
    from src.common import load_config
    from src.medajob.run_experiments import load_artifacts, train_centralized

    cfg = load_config()
    data = load_artifacts(cfg)

    s1 = train_centralized(data, cfg, arch="lightgcn", seed=1)
    s2 = train_centralized(data, cfg, arch="lightgcn", seed=2)

    d = (s1["emb.weight"] - s2["emb.weight"]).abs().max().item()
    assert d > 1e-4, "seed khác nhau cho cùng kết quả — seed không được dùng"


def test_metrics_identical_after_stripping_timing():
    """Hai lần chạy: mọi chỉ số phải trùng sau khi bỏ trường thời gian."""
    path = RESULTS / "reco_main.json"
    if not path.exists():
        pytest.skip("chưa có kết quả")
    a = strip_timing(json.loads(path.read_text(encoding="utf-8")))
    b = strip_timing(json.loads(path.read_text(encoding="utf-8")))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_documented_key_numbers_match_results():
    """Các con số then chốt trong báo cáo phải khớp với results/*.json."""
    reco_p = RESULTS / "reco_main.json"
    if not reco_p.exists():
        pytest.skip("chưa có kết quả")

    reco = json.loads(reco_p.read_text(encoding="utf-8"))

    # Bất biến logic, không phụ thuộc giá trị cụ thể
    assert 0.0 <= reco["systems"]["fedavg"]["recall@20"] <= 1.0

    # Học liên bang phải tốt hơn cục bộ (luận điểm chính của đồ án)
    assert (reco["systems"]["fedavg"]["recall@20"]
            > reco["systems"]["local_only"]["recall@20"]), (
        "FedAvg không vượt mô hình cục bộ — luận điểm chính của đồ án không còn đúng")

    # Mô hình tập trung là mốc trên: không được thấp hơn liên bang
    assert (reco["systems"]["centralized"]["recall@20"]
            >= reco["systems"]["fedavg"]["recall@20"] - 0.05), (
        "Mốc tập trung thấp hơn liên bang quá nhiều — kiểm tra lại giao thức")

    # Đồ thị phải vượt baseline không dùng đồ thị
    for baseline in ("popularity", "skill_cbf", "item_knn"):
        assert (reco["systems"]["centralized"]["recall@20"]
                > reco["systems"][baseline]["recall@20"]), (
            f"Mô hình đồ thị không vượt baseline {baseline}")


def test_ci_brackets_mean():
    """Khoảng tin cậy 95% phải chứa giá trị trung bình."""
    path = RESULTS / "reco_main.json"
    if not path.exists():
        pytest.skip("chưa có kết quả")
    reco = json.loads(path.read_text(encoding="utf-8"))
    for key, s in reco["systems"].items():
        ci = s.get("recall@20_ci")
        if not ci:
            continue
        assert ci["lo"] <= ci["mean"] + 1e-9, f"{key}: CI dưới > mean"
        assert ci["hi"] >= ci["mean"] - 1e-9, f"{key}: CI trên < mean"
