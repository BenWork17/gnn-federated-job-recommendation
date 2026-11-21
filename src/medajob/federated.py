"""
Mô phỏng học liên bang (Federated Learning) cho mô hình GNN gợi ý.

Điểm quan trọng nhất về mặt kỹ thuật — và cũng là lỗi hay gặp:
  Nếu mỗi client train trên đồ thị cục bộ của mình rồi lấy TRUNG BÌNH TOÀN
  BỘ bảng embedding, các nút mà client đó không có dữ liệu sẽ bị kéo về 0
  ở mỗi vòng. Sau vài chục vòng, mô hình toàn cục sụp đổ dù client nào
  cũng "học tốt". Đây chính là hiện tượng đã quan sát thấy khi thử nhanh.

Cách làm đúng: FedAvg THƯA (sparse FedAvg)
  - Client chỉ gửi các hàng embedding mà nó THỰC SỰ cập nhật, kèm trọng số
    bằng số tương tác cục bộ của nút đó.
  - Server cộng dồn có trọng số rồi chia cho tổng trọng số CỦA CHÍNH NÚT
    ĐÓ (không chia cho tổng trọng số toàn cục).
  - Nút không client nào chạm tới giữ nguyên giá trị server.
  Kết quả: giống hệt FedAvg chuẩn khi mọi client có cùng không gian nút,
  nhưng không bị pha loãng.

Ranh giới riêng tư (được kiểm bằng test tự động):
  Payload client gửi lên CHỈ gồm (node_index, vector float32, weight).
  Không có user_id, job_id, rating, hay bất kỳ bản ghi thô nào.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np
import torch
import torch.nn.functional as F

from src.medajob.models import LightGCN, bpr_loss


# =====================================================================
# 1. Cấu trúc dữ liệu
# =====================================================================
@dataclass
class GraphParts:
    """Đồ thị đã tách thành phần CÔNG KHAI (server) và RIÊNG TƯ (client)."""

    n_nodes: int
    n_users: int
    n_jobs: int
    # cạnh công khai: job–skill, job–industry (server giữ, phát cho mọi client)
    pub_src: np.ndarray
    pub_dst: np.ndarray
    # cạnh riêng tư: user–skill, user–job (chỉ client sở hữu mới có)
    priv_src: np.ndarray
    priv_dst: np.ndarray
    priv_owner: np.ndarray  # client id của từng cạnh riêng tư
    n_clients: int

    def edges_for_client(self, c: int) -> tuple[np.ndarray, np.ndarray]:
        """Cạnh mà client c nhìn thấy = công khai + riêng tư của mình."""
        own = self.priv_owner == c
        src = np.concatenate([self.pub_src, self.priv_src[own]])
        dst = np.concatenate([self.pub_dst, self.priv_dst[own]])
        return src, dst


@dataclass
class ClientUpdate:
    """Gói tin client gửi lên server. Đây là thứ được kiểm tra riêng tư."""

    client_id: int
    node_idx: np.ndarray          # chỉ số nút đã cập nhật
    rows: np.ndarray              # embedding mới của các nút đó (float32)
    weight: np.ndarray            # trọng số = số tương tác cục bộ
    n_samples: int
    train_loss: float = float("nan")

    @property
    def n_bytes(self) -> int:
        return int(self.rows.size * 4 + self.node_idx.size * 8
                   + self.weight.size * 4)

    def as_dict(self) -> dict:
        return {
            "client_id": int(self.client_id),
            "n_nodes_sent": int(self.node_idx.size),
            "n_bytes": self.n_bytes,
            "n_samples": int(self.n_samples),
        }


@dataclass
class RoundLog:
    round: int
    up_bytes: int = 0
    down_bytes: int = 0
    mean_train_loss: float = float("nan")
    metrics: dict = field(default_factory=dict)


# =====================================================================
# 2. Tiện ích đồ thị
# =====================================================================
def build_norm(src: np.ndarray, dst: np.ndarray, n_nodes: int) -> tuple:
    """Chuyển cạnh numpy -> tensor + nghịch đảo bậc (D^-1 A)."""
    s = torch.tensor(src, dtype=torch.long)
    d = torch.tensor(dst, dtype=torch.long)
    deg = torch.zeros(n_nodes, dtype=torch.float32)
    deg.index_add_(0, d, torch.ones(s.numel()))
    return s, d, 1.0 / deg.clamp(min=1.0)


# =====================================================================
# 3. Train cục bộ
# =====================================================================
def local_train(
    global_state: dict[str, torch.Tensor],
    edges: tuple,
    interactions: np.ndarray,
    n_users: int,
    n_jobs: int,
    cfg: dict,
    *,
    n_nodes: int,
    mu: float = 0.0,
    seed: int = 0,
) -> tuple[dict[str, torch.Tensor], int, float]:
    """Train một client. Trả về (state_dict mới, n_samples, loss trung bình).

    `interactions`: mảng (n, 2) gồm (user_index, job_index) của các tương tác
    DƯƠNG tính mà client sở hữu. Không chứa rating gốc.

    `mu > 0` bật FedProx: thêm số hạng mu/2 * ||w - w_global||^2 để client
    không trôi quá xa mô hình toàn cục (giúp hội tụ khi dữ liệu không đồng nhất).
    """
    torch.manual_seed(seed)
    model = LightGCN(n_nodes, dim=int(cfg["dim"]), layers=int(cfg["layers"]))
    model.load_state_dict(global_state)
    opt = torch.optim.Adam(model.parameters(), lr=float(cfg["lr"]))
    src, dst, inv_deg = edges

    uu = torch.tensor(interactions[:, 0], dtype=torch.long)
    jj = torch.tensor(interactions[:, 1], dtype=torch.long) + n_users
    n = max(int(uu.numel()), 1)

    # LƯU Ý QUAN TRỌNG: phải lấy tensor tham số qua named_parameters().
    # model.state_dict() trả về tensor đã detach, nên nếu tính số hạng
    # proximal trên state_dict thì nó KHÔNG có gradient và FedProx trở thành
    # FedAvg trần (đã kiểm bằng thực nghiệm: mu=5 cho kết quả trùng khít
    # mu=0 tới 7e-7). named_parameters() mới nối vào đồ thị autograd.
    ref = {name: p.detach().clone() for name, p in model.named_parameters()}

    losses: list[float] = []
    for _ in range(int(cfg["epochs"])):
        opt.zero_grad()
        emb = model.encode(src, dst, inv_deg)
        neg = torch.randint(n_users, n_users + n_jobs, (n,))
        loss = bpr_loss(emb, uu, jj, neg, reg=float(cfg["reg"]))
        if mu > 0:
            prox = sum(((p - ref[name]) ** 2).sum()
                       for name, p in model.named_parameters())
            loss = loss + 0.5 * mu * prox
        loss.backward()
        opt.step()
        losses.append(float(loss.detach().item()))
    return {k: v.detach().clone() for k, v in model.state_dict().items()}, n, float(np.mean(losses))


# =====================================================================
# 4. Server: FedAvg thưa
# =====================================================================
def sparse_fedavg(
    global_state: dict[str, torch.Tensor],
    updates: list[ClientUpdate],
) -> tuple[dict[str, torch.Tensor], int]:
    """Cộng dồn delta có trọng số theo TỪNG NÚT.

    Trả về (state_dict mới, số nút được cập nhật).
    Chỉ nút có tổng trọng số > 0 mới thay đổi -> không pha loãng.
    """
    new_state = {k: v.detach().clone() for k, v in global_state.items()}
    key = "emb.weight"
    base = global_state[key]
    n_nodes = base.shape[0]

    acc = torch.zeros_like(base, dtype=torch.float64)
    wsum = torch.zeros(n_nodes, dtype=torch.float64)

    for upd in updates:
        if upd.node_idx.size == 0:
            continue
        idx = torch.tensor(upd.node_idx, dtype=torch.long)
        rows = torch.tensor(upd.rows, dtype=torch.float64)
        w = torch.tensor(upd.weight, dtype=torch.float64)
        delta = rows - base[idx].double()
        acc.index_add_(0, idx, delta * w.unsqueeze(1))
        wsum.index_add_(0, idx, w)

    touched = wsum > 0
    n_touched = int(touched.sum())
    if n_touched:
        merged = base.clone()
        merged[touched] = (base[touched].double()
                           + acc[touched] / wsum[touched].unsqueeze(1)).float()
        new_state[key] = merged
    return new_state, n_touched


def make_update(
    client_id: int,
    global_state: dict[str, torch.Tensor],
    local_state: dict[str, torch.Tensor],
    interactions: np.ndarray,
    n_users: int,
    n_jobs: int,
) -> ClientUpdate:
    """Đóng gói phần đã thay đổi thành gói tin gửi server.

    Chỉ gửi những hàng embedding THAY ĐỔI. Trọng số của một nút = số tương
    tác cục bộ liên quan tới nút đó (user: số rating của user; job: số
    rating của job; skill/industry: số cạnh của nó trong đồ thị cục bộ).
    """
    key = "emb.weight"
    g = global_state[key]
    l = local_state[key]
    changed = torch.any(~torch.isclose(g, l, atol=0.0), dim=1).numpy()
    node_idx = np.where(changed)[0]

    # trọng số theo số tương tác (1 cho user, 1 cho job, cộng dồn)
    weight = np.ones(node_idx.size, dtype=np.float32)
    if interactions.size:
        cnt_u = np.bincount(interactions[:, 0], minlength=n_users)
        cnt_j = np.bincount(interactions[:, 1], minlength=n_jobs)
        for pos, node in enumerate(node_idx):
            if node < n_users:
                weight[pos] = max(1, int(cnt_u[node]))
            elif node < n_users + n_jobs:
                weight[pos] = max(1, int(cnt_j[node - n_users]))
            else:
                weight[pos] = 1  # kỹ năng/ngành: trọng số đơn vị

    return ClientUpdate(
        client_id=client_id,
        node_idx=node_idx.astype(np.int64),
        rows=l[node_idx].detach().cpu().numpy().astype(np.float32),
        weight=weight,
        n_samples=int(interactions.shape[0]),
    )


# =====================================================================
# 5. Vòng lặp FL đầy đủ
# =====================================================================
def run_federated(
    parts: GraphParts,
    train_matrix: np.ndarray,
    client_of_user: np.ndarray,
    cfg: dict,
    *,
    rounds: int,
    local_epochs: int,
    lr: float,
    dim: int,
    layers: int,
    reg: float,
    mu: float = 0.0,
    sample_rate: float = 1.0,
    eval_fn=None,
    seed: int = 0,
) -> tuple[dict[str, torch.Tensor], list[RoundLog], dict]:
    """Chạy FedAvg/FedProx và trả về (state cuối, log từng vòng, thông tin phụ).

    `eval_fn(state) -> dict` được gọi sau mỗi vòng để ghi đường cong học.
    """
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)

    model = LightGCN(parts.n_nodes, dim=dim, layers=layers)
    global_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    local_cfg = {"dim": dim, "layers": layers, "lr": lr,
                 "epochs": local_epochs, "reg": reg}

    # tương tác dương tính theo từng client (chỉ số, KHÔNG có rating)
    interactions_by_client: dict[int, np.ndarray] = {}
    for c in range(parts.n_clients):
        users = np.where(client_of_user == c)[0]
        if users.size == 0:
            interactions_by_client[c] = np.zeros((0, 2), dtype=np.int64)
            continue
        sub = train_matrix[users]
        ui, ji = np.where(sub > 0)
        interactions_by_client[c] = np.stack(
            [users[ui], ji], axis=1).astype(np.int64)

    edge_cache = {c: build_norm(*parts.edges_for_client(c), parts.n_nodes)
                  for c in range(parts.n_clients)}

    logs: list[RoundLog] = []
    up_bytes_total = 0
    down_bytes_total = 0
    param_bytes = int(global_state["emb.weight"].numel() * 4)

    for rnd in range(1, rounds + 1):
        # --- chọn client tham gia ------------------------------------
        if sample_rate >= 1.0:
            chosen = list(range(parts.n_clients))
        else:
            m = max(1, int(round(sample_rate * parts.n_clients)))
            chosen = sorted(rng.choice(parts.n_clients, m, replace=False).tolist())

        updates: list[ClientUpdate] = []
        losses: list[float] = []
        for c in chosen:
            inter = interactions_by_client[c]
            if inter.shape[0] == 0:
                continue
            local_state, n_samples, loss = local_train(
                global_state, edge_cache[c], inter,
                parts.n_users, parts.n_jobs, local_cfg,
                n_nodes=parts.n_nodes, mu=mu,
                seed=seed + rnd * 1000 + c,
            )
            upd = make_update(c, global_state, local_state, inter,
                              parts.n_users, parts.n_jobs)
            updates.append(upd)
            losses.append(loss)
            down_bytes_total += param_bytes      # server -> client
            up_bytes_total += upd.n_bytes        # client -> server

        if not updates:
            break
        global_state, n_touched = sparse_fedavg(global_state, updates)

        log = RoundLog(round=rnd,
                       up_bytes=int(sum(u.n_bytes for u in updates)),
                       down_bytes=param_bytes * len(updates),
                       mean_train_loss=float(np.mean(losses)))
        if eval_fn is not None:
            log.metrics = eval_fn(global_state)
        logs.append(log)

    # Chi phí truyền thông: một lần gửi mô hình xuống mỗi client đã chọn
    # (chỉ cần 1 lần/đầu phiên, không phải mỗi vòng — sau vòng 1 client đã
    # có state cũ và chỉ nhận phần thay đổi). Báo cáo cả hai cách tính để
    # không phóng đại lợi ích.
    info = {
        "rounds_run": len(logs),
        "n_clients": parts.n_clients,
        "param_bytes_per_transfer": param_bytes,
        "up_bytes_total": up_bytes_total,
        "down_bytes_total": down_bytes_total,
        "mean_up_bytes_per_round": (up_bytes_total / len(logs) if logs else 0),
        "down_bytes_initial_broadcast": param_bytes * parts.n_clients,
        "mu": mu,
        "local_epochs": local_epochs,
        "lr": lr,
    }
    return global_state, logs, info
