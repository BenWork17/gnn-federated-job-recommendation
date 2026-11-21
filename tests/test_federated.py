"""
Test cho học liên bang: FedAvg thưa, FedProx, và ranh giới riêng tư.

Ba nhóm kiểm tra:
  1. Sparse FedAvg cho kết quả đúng về mặt số học.
  2. Số hạng proximal của FedProx THỰC SỰ có gradient (bug đã gặp: dùng
     state_dict() khiến nó mất gradient và FedProx = FedAvg).
  3. Payload client gửi lên không chứa dữ liệu thô (id người dùng, rating).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.medajob.federated import (ClientUpdate, build_norm, local_train,
                                   make_update, sparse_fedavg)
from src.medajob.models import LightGCN


# =====================================================================
# 1. Sparse FedAvg
# =====================================================================
def test_sparse_fedavg_identical_clients_returns_their_value():
    """Nếu mọi client gửi CÙNG một giá trị, kết quả phải đúng giá trị đó."""
    n = 5
    base = torch.zeros(n, 3)
    target = torch.ones(n, 3) * 2.0
    updates = [
        ClientUpdate(client_id=i, node_idx=np.arange(n),
                     rows=target.numpy(),
                     weight=np.ones(n, dtype=np.float32), n_samples=10)
        for i in range(3)
    ]
    new_state, touched = sparse_fedavg({"emb.weight": base}, updates)
    assert touched == n
    assert torch.allclose(new_state["emb.weight"], target, atol=1e-6)


def test_sparse_fedavg_weighted_average():
    """Hai client với trọng số khác nhau -> trung bình có trọng số."""
    n = 2
    base = torch.zeros(n, 1)
    u1 = ClientUpdate(0, np.array([0]), np.array([[2.0]], dtype=np.float32),
                      np.array([1.0], dtype=np.float32), 1)
    u2 = ClientUpdate(1, np.array([0]), np.array([[4.0]], dtype=np.float32),
                      np.array([3.0], dtype=np.float32), 3)
    new_state, _ = sparse_fedavg({"emb.weight": base}, [u1, u2])
    # (2*1 + 4*3) / (1+3) = 14/4 = 3.5
    assert new_state["emb.weight"][0, 0].item() == pytest.approx(3.5, abs=1e-6)
    # nút 1 không ai chạm -> giữ nguyên 0
    assert new_state["emb.weight"][1, 0].item() == pytest.approx(0.0)


def test_sparse_fedavg_does_not_dilute_untouched_nodes():
    """Đây là bug của FedAvg trần: nút không có dữ liệu bị kéo về 0."""
    n = 4
    base = torch.ones(n, 2) * 5.0
    # client chỉ cập nhật nút 0
    upd = ClientUpdate(0, np.array([0]), np.array([[7.0, 7.0]], dtype=np.float32),
                       np.array([1.0], dtype=np.float32), 1)
    new_state, touched = sparse_fedavg({"emb.weight": base}, [upd])
    assert touched == 1
    assert new_state["emb.weight"][0, 0].item() == pytest.approx(7.0, abs=1e-6)
    # các nút còn lại PHẢI giữ nguyên 5.0, không bị kéo về 0
    for i in range(1, n):
        assert new_state["emb.weight"][i, 0].item() == pytest.approx(5.0)


def test_make_update_only_sends_changed_rows():
    """Client chỉ gửi các hàng embedding thực sự thay đổi."""
    n = 6
    base = torch.zeros(n, 4)
    local = base.clone()
    local[2] = 1.0
    local[5] = 2.0
    inter = np.array([[0, 0], [1, 1]], dtype=np.int64)

    upd = make_update(0, {"emb.weight": base}, {"emb.weight": local},
                      inter, n_users=2, n_jobs=4)
    assert set(upd.node_idx.tolist()) == {2, 5}
    assert upd.n_bytes > 0


# =====================================================================
# 2. FedProx phải có gradient
# =====================================================================
def _tiny_setup():
    n_nodes, n_users, n_jobs, dim = 12, 3, 6, 4
    src = torch.tensor([0, 1, 2, 3, 4, 5])
    dst = torch.tensor([3, 4, 5, 6, 7, 8])
    s, d, inv = build_norm(src.numpy(), dst.numpy(), n_nodes)
    inter = np.array([[0, 0], [1, 1], [2, 2]], dtype=np.int64)
    state = {"emb.weight": torch.randn(n_nodes, dim) * 0.1}
    return state, (s, d, inv), inter, n_users, n_jobs, dim


def test_fedprox_gradient_differs_from_fedavg():
    """Số hạng proximal PHẢI ảnh hưởng tới kết quả train cục bộ.

    Đây là regression test cho bug: tính prox trên state_dict() (đã detach)
    khiến mu=5 cho kết quả trùng khít mu=0 tới ~1e-6.
    """
    state, edges, inter, n_users, n_jobs, dim = _tiny_setup()
    base_cfg = {"dim": dim, "layers": 1, "lr": 0.05, "epochs": 5, "reg": 0.0}

    out = {}
    for mu in (0.0, 5.0):
        st, _, _ = local_train(state, edges, inter, n_users, n_jobs, base_cfg,
                               n_nodes=12, mu=mu, seed=7)
        out[mu] = st["emb.weight"]

    diff = (out[0.0] - out[5.0]).abs().max().item()
    assert diff > 1e-3, (
        f"mu=0 và mu=5 cho kết quả gần như giống hệt (max diff = {diff:.2e}). "
        "Số hạng proximal có thể đang chạy trên tensor đã detach — xem "
        "chú thích trong federated.local_train.")


def test_fedprox_mu_larger_means_smaller_drift():
    """μ càng lớn thì tham số càng ít trôi khỏi mô hình toàn cục."""
    state, edges, inter, n_users, n_jobs, dim = _tiny_setup()
    cfg = {"dim": dim, "layers": 1, "lr": 0.05, "epochs": 8, "reg": 0.0}

    drift = {}
    for mu in (0.0, 2.0, 20.0):
        st, _, _ = local_train(state, edges, inter, n_users, n_jobs, cfg,
                               n_nodes=12, mu=mu, seed=3)
        drift[mu] = (st["emb.weight"] - state["emb.weight"]).norm().item()

    assert drift[20.0] < drift[0.0], (
        f"μ lớn không giảm drift: {drift}")


def test_local_train_does_not_mutate_global_state():
    """Train cục bộ không được sửa tham số toàn cục tại chỗ."""
    state, edges, inter, n_users, n_jobs, dim = _tiny_setup()
    before = state["emb.weight"].clone()
    cfg = {"dim": dim, "layers": 1, "lr": 0.05, "epochs": 3, "reg": 0.0}
    local_train(state, edges, inter, n_users, n_jobs, cfg,
                n_nodes=12, mu=0.0, seed=0)
    assert torch.allclose(state["emb.weight"], before)


# =====================================================================
# 3. Ranh giới riêng tư
# =====================================================================
def test_payload_contains_no_raw_data():
    """Gói tin client gửi lên chỉ có embedding, không có id hay rating."""
    n_nodes = 20
    base = torch.zeros(n_nodes, 4)
    local = base.clone()
    local[3] = torch.tensor([1.0, 2.0, 3.0, 4.0])
    inter = np.array([[0, 5]], dtype=np.int64)  # (user 0, job 5)

    upd = make_update(0, {"emb.weight": base}, {"emb.weight": local},
                      inter, n_users=10, n_jobs=10)

    # các trường được phép
    allowed = {"client_id", "node_idx", "rows", "weight", "n_samples",
               "train_loss", "n_bytes", "as_dict"}
    assert set(vars(upd)) <= allowed

    # không có mảng nào chứa cặp (user_id, job_id) hay rating
    assert upd.node_idx.dtype.kind in "iu"
    assert upd.rows.dtype == np.float32
    # số phần tử gửi lên = số HÀNG đã đổi × số chiều, không phải số mẫu
    assert upd.rows.shape == (upd.node_idx.size, 4)


def test_payload_size_independent_of_record_count():
    """Kích thước payload là O(số nút × chiều), KHÔNG phụ thuộc số bản ghi."""
    n_nodes, dim = 50, 8
    base = torch.zeros(n_nodes, dim)
    local = base.clone()
    local[1] = 1.0

    small = make_update(0, {"emb.weight": base}, {"emb.weight": local},
                        np.array([[0, 0]]), n_users=25, n_jobs=25)
    big_inter = np.array([[i % 25, i % 25] for i in range(500)], dtype=np.int64)
    big = make_update(0, {"emb.weight": base}, {"emb.weight": local},
                      big_inter, n_users=25, n_jobs=25)

    assert small.n_bytes == big.n_bytes, (
        "payload phải giống nhau dù số tương tác khác nhau — "
        "đây chính là điểm khác biệt so với gửi dữ liệu thô")


def test_client_update_dict_has_no_data_fields():
    upd = ClientUpdate(0, np.array([1, 2]), np.zeros((2, 3), np.float32),
                       np.ones(2, np.float32), 5)
    d = upd.as_dict()
    for bad in ("user_id", "job_id", "rating", "records", "features"):
        assert bad not in d
