"""
Các mô hình gợi ý. Viết thuần PyTorch/numpy — KHÔNG dùng torch_geometric
vì máy này không cài được gói mới (pip bị chặn ghi metadata).

Vì sao tự viết lan truyền đồ thị thay vì dùng PyG:
  LightGCN chỉ cần một phép "gather + scatter-add có chuẩn hoá bậc", tức
  hai dòng torch. Tự viết giúp (a) không thêm dependency, (b) thấy rõ cái
  gì được gửi lên server trong FL (chỉ state_dict, không phải đồ thị).

Bốn mô hình:
  Popularity   : baseline không cá nhân hoá
  SkillCBF     : content-based theo kỹ năng (TF-IDF cosine)
  ItemKNN      : collaborative filtering item-based
  LightGCN     : GNN lan truyền trên đồ thị User–Job–Skill–Industry
  GraphSAGE    : biến thể có MLP + chuẩn hoá L2, dùng cho ablation
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# =====================================================================
# 1. Lan truyền đồ thị dùng chung
# =====================================================================
def normalize_edges(edge_index: torch.Tensor, n_nodes: int) -> torch.Tensor:
    """Chuẩn hoá cạnh theo bậc đích: A_norm = D^-1 A.

    LightGCN gốc dùng D^-1/2 A D^-1/2, nhưng khi đồ thị có nút bậc rất cao
    (kỹ năng "python" nối hàng trăm job) thì D^-1/2 làm embedding của nút
    bậc thấp gần như biến mất. D^-1 A giữ được tín hiệu từ nút bậc thấp.
    """
    src, dst = edge_index[0], edge_index[1]
    deg = torch.zeros(n_nodes, dtype=torch.float32)
    deg.index_add_(0, dst, torch.ones(src.numel(), dtype=torch.float32))
    deg = deg.clamp(min=1.0)
    return src, dst, 1.0 / deg


def propagate(emb: torch.Tensor, src, dst, inv_deg, layers: int) -> torch.Tensor:
    """Lan truyền K tầng, trả về trung bình cộng các tầng (LightGCN)."""
    outs = [emb]
    x = emb
    for _ in range(layers):
        ax = torch.zeros_like(x)
        ax.index_add_(0, dst, x[src])
        x = ax * inv_deg.unsqueeze(1)
        outs.append(x)
    return torch.stack(outs, 0).mean(0)


# =====================================================================
# 2. LightGCN
# =====================================================================
class LightGCN(nn.Module):
    """GNN gợi ý trên đồ thị không đồng nhất User–Job–Skill–Industry.

    Điểm số của cặp (u, j) là tích vô hướng embedding sau lan truyền.
    Chỉ có MỘT tham số học được: bảng embedding. Đây là lý do mô hình nhẹ
    và cũng là lý do FL chỉ cần gửi `n_nodes × dim` số thực.
    """

    def __init__(self, n_nodes: int, dim: int = 32, layers: int = 2):
        super().__init__()
        self.n_nodes = n_nodes
        self.dim = dim
        self.layers = layers
        self.emb = nn.Embedding(n_nodes, dim)
        nn.init.normal_(self.emb.weight, std=0.1)

    def encode(self, src, dst, inv_deg) -> torch.Tensor:
        return propagate(self.emb.weight, src, dst, inv_deg, self.layers)

    def scores(self, node_emb: torch.Tensor, user_idx: torch.Tensor,
               job_idx: torch.Tensor) -> torch.Tensor:
        return node_emb[user_idx] @ node_emb[job_idx].T


class GraphSAGE(nn.Module):
    """Biến thể có MLP + chuẩn hoá L2 sau mỗi tầng (để so sánh kiến trúc).

    Khác LightGCN: có trọng số học được giữa các tầng và chuẩn hoá L2, nên
    biểu diễn phi tuyến hơn nhưng nhiều tham số hơn và khó hội tụ hơn khi
    dữ liệu cực thưa. Dùng làm ablation để trả lời "có cần MLP không?".
    """

    def __init__(self, n_nodes: int, dim: int = 32, layers: int = 2,
                 dropout: float = 0.1):
        super().__init__()
        self.n_nodes = n_nodes
        self.dim = dim
        self.layers = layers
        self.emb = nn.Embedding(n_nodes, dim)
        nn.init.normal_(self.emb.weight, std=0.1)
        self.self_w = nn.ModuleList([nn.Linear(dim, dim) for _ in range(layers)])
        self.neigh_w = nn.ModuleList([nn.Linear(dim, dim) for _ in range(layers)])
        self.dropout = dropout

    def encode(self, src, dst, inv_deg) -> torch.Tensor:
        x = self.emb.weight
        for k in range(self.layers):
            neigh = torch.zeros_like(x)
            neigh.index_add_(0, dst, x[src])
            neigh = neigh * inv_deg.unsqueeze(1)
            h = self.self_w[k](x) + self.neigh_w[k](neigh)
            h = F.relu(h)
            if self.dropout > 0:
                h = F.dropout(h, self.dropout, self.training)
            x = F.normalize(h, p=2, dim=1) if k == self.layers - 1 else h
        return x


def bpr_loss(node_emb, user_idx, pos_job_idx, neg_job_idx, reg=1e-5,
             weight=None) -> torch.Tensor:
    """Bayesian Personalised Ranking.

    Với mỗi cặp (u, j+), lấy ngẫu nhiên một tin j- chưa tương tác. Hàm mất
    mát đẩy điểm của j+ cao hơn j-. Chỉ dùng các tương tác ĐÃ BIẾT nên phù
    hợp với dữ liệu ngầm (implicit) và với FL (client chỉ có dữ liệu của mình).
    """
    u = node_emb[user_idx]
    p = node_emb[pos_job_idx]
    n = node_emb[neg_job_idx]
    pos_s = (u * p).sum(1)
    neg_s = (u * n).sum(1)
    loss = -F.logsigmoid(pos_s - neg_s)
    if weight is not None:
        loss = loss * weight
    return loss.mean() + reg * (u.norm(2).pow(2).mean())


# =====================================================================
# 3. Baseline không dùng GNN
# =====================================================================
def popularity_scores(train: np.ndarray) -> np.ndarray:
    """Điểm = số lượt tương tác của tin trong train (không cá nhân hoá)."""
    return np.tile((train > 0).sum(0).astype(np.float32), (train.shape[0], 1))


def skill_cbf_scores(job_skills: list[list[str]],
                     user_skills: list[list[str]]) -> np.ndarray:
    """Content-based: TF-IDF trên tập kỹ năng, cosine giữa hồ sơ và tin."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vec = TfidfVectorizer(analyzer=lambda x: x, norm="l2")
    X = vec.fit_transform(list(job_skills) + list(user_skills))
    n_jobs = len(job_skills)
    return cosine_similarity(X[n_jobs:], X[:n_jobs]).astype(np.float32)


def item_knn_scores(train: np.ndarray, k: int = 20) -> np.ndarray:
    """Item-KNN: độ giống giữa 2 tin = cosine trên cột nhị phân của train."""
    from sklearn.metrics.pairwise import cosine_similarity

    B = (train >= 4).astype(np.float32)
    if B.sum() == 0:
        return np.zeros_like(train)
    sim = cosine_similarity(B.T)
    np.fill_diagonal(sim, 0.0)
    if k < sim.shape[0]:
        # giữ k láng giềng gần nhất
        thresh = np.partition(sim, -k, axis=1)[:, -k][:, None]
        sim = np.where(sim >= thresh, sim, 0.0)
    return (B @ sim).astype(np.float32)


# =====================================================================
# 4. Đóng gói tham số để mô phỏng payload FL
# =====================================================================
@dataclass
class PayloadStats:
    """Số byte thực sự truyền trong một vòng FL."""

    down_bytes: int
    up_bytes: int
    n_params: int


def state_dict_bytes(state: dict[str, torch.Tensor]) -> int:
    """Kích thước nhị phân thật của state_dict (float32)."""
    return int(sum(v.numel() * 4 for v in state.values() if v.is_floating_point()))


def raw_data_bytes(train: np.ndarray) -> int:
    """Số byte nếu phải gửi dữ liệu thô lên server (mỗi tương tác ~ 8 byte
    cho (user_id, job_id) cộng 4 byte rating)."""
    return int((train > 0).sum()) * 12
