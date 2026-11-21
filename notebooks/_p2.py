# %% [markdown]
# # [4] Kiến trúc GNN + Học liên bang
#
# ## 4.1 Sơ đồ tổng thể
#
# ```
#                        ┌──────────────────────────────────────────┐
#                        │  SERVER (không giữ dữ liệu thô của client)│
#                        │                                          │
#                        │   E_global  ←  FedAvg({E_c})             │
#                        │   (264.995 × dim)                        │
#                        └───────▲───────────────┬──────────────────┘
#                    E_c (up)    │               │   E_global (down)
#              ┌─────────────────┴───┐   ┌───────┴──────────────┐
#              │ Client c1         │   │ Client c2            │ … 9.116 client
#              │ (employer #1)     │   │ (employer #2)        │
#              │ ┌───────────────┐ │   │ ┌──────────────────┐ │
#              │ │ Đồ thị con:   │ │   │ │ Đồ thị con:      │ │
#              │ │ job CỦA c1    │ │   │ │ job CỦA c2       │ │
#              │ │ + app vào job │ │   │ │ + app vào job    │ │
#              │ │   của c1      │ │   │ │   của c2         │ │
#              │ │ + nghề/kỹ năng│ │   │ │ + nghề/kỹ năng   │ │
#              │ └───────────────┘ │   │ └──────────────────┘ │
#              │  Lan truyền GNN   │   │  Lan truyền GNN      │
#              │  + BPR loss       │   │  + BPR loss          │
#              └───────────────────┘   └──────────────────────┘
#                    DỮ LIỆU THÔ KHÔNG RỜI KHỎI Ô NÀY
# ```
#
# ## 4.2 TẠI SAO cross-silo là hợp lệ (câu hội đồng chắc chắn hỏi)
#
# **Client = nhà tuyển dụng (employer)**, không phải người dùng. Đây là **cross-silo**
# FL: số client ít hơn nhiều so với số user, mỗi client là một tổ chức có dữ liệu
# **thật sự riêng**.
#
# Lập luận:
#
# 1. Nhà tuyển dụng chỉ **sở hữu** một loại quan sát: *"user X đã ứng tuyển vào tin
#    của tôi"*. Họ **không** biết user X ứng tuyển ở đâu khác.
# 2. Vì vậy **mỗi cạnh (u, j) thuộc về `client_of_job[j]`** — người sở hữu tin `j`.
#    Đây là ranh giới silo **thật**. (`client_of_user[u]` chỉ là nhãn "client mà user
#    ứng tuyển **nhiều nhất**" — argmax, **không phải** membership độc quyền.)
# 3. Một user có thể xuất hiện ở nhiều client: **44,58%** user thuộc ≥2 client, trung
#    bình **2,41 client/user**. Đây là **bản chất thị trường tuyển dụng**, KHÔNG phải
#    rò rỉ: client A **không** thấy application của user đó vào job của client B.
# 4. Bằng chứng định lượng rằng hai nhãn này **không** trùng nhau: chỉ
#    **{pct_train:.2f}%** cạnh train và **{pct_test:.2f}%** cạnh test có
#    `client_of_user[u] == client_of_job[j]`. Nếu dùng `client_of_user` để chia silo
#    thì **hơn một nửa** cạnh sẽ bị gán sai chủ.
#
# > **Kết luận**: dùng `client_of_job[j]` để gán cạnh vào client. Dùng
# > `client_of_user[u]` là **sai** — nó gộp application của user vào job của employer
# > khác, tức là trộn silo.
#
# ## 4.3 Kiểm tra: 9.116 client có dữ liệu không?
#
# Đây là kiểm tra **đã thực hiện** (in ở section `[3]`), không phải giả định:
#
# | Kiểm tra | Kết quả |
# |---|---|
# | Client có ≥ 1 job | **9.116 / 9.116 (100%)** |
# | Client có ≥ 1 cạnh train | **9.116 / 9.116 (100%)** |
# | Client **không** có cạnh train | **0** |
# | Cạnh train/client | min **5** / median **22** / mean **43,8** / max **4.320** |
# | Client ≥ 10 cạnh train | **8.745 (95,9%)** |
# | Client ≥ 50 cạnh train | **1.895 (20,8%)** |
# | Job/client | min 1 / median 4 / max 603 |
#
# ## 4.4 Hai cấu hình thực nghiệm được khai báo
#
# | Tên | Tập client tham gia | Dùng cho |
# |---|---|---|
# | **scale-main** | `SCALE` cấu hình (mặc định 50 client lớn nhất theo `n_apps`) | Chạy mẫu trên Kaggle, sweep tham số, ablation |
# | **scale-full** | Toàn bộ 9.116 client (hoặc 1.895 client ≥ 50 cạnh) | Một vòng "chứng minh quy mô" — chỉ 1 vòng, đo thời gian, không tune |
#
# Phân bố client **rất lệch** (max 4.320 cạnh gấp 864 lần min 5), nên metric được
# báo **tách nhóm** client ≥10 job và <10 job ở section `[7]`, và ablation
# weighted vs unweighted FedAvg ở `[8]`.

# %%
# ============================================================================
# [4b] THƯ VIỆN DÙNG CHUNG — dựng ma trận kề, mô hình GNN, vòng FL
# ============================================================================
T4 = time.perf_counter()
set_seed(42)

# --- cạnh train dùng cho lan truyền: TẤT CẢ loại cạnh, chỉ phần train ---
ADJ_NODES = N_NODES


def build_norm_adj(mask_edge: np.ndarray, add_self: bool = True):
    """Ma trận kề chuẩn hoá đối xứng D^-1/2 (A + I) D^-1/2 ở dạng torch.sparse (COO).

    `mask_edge`: mask bool trên 764.364 cạnh — chọn tập cạnh đưa vào đồ thị.
    Đồ thị trong artifacts lưu **1 dòng / cạnh vô hướng**, nên phải tự đối xứng hoá
    bằng cách nối (i, j) với (j, i).
    """
    src = EDGE_INDEX[0][mask_edge]
    dst = EDGE_INDEX[1][mask_edge]
    row = np.concatenate([src, dst])
    col = np.concatenate([dst, src])
    A = sp.coo_matrix((np.ones(row.size, dtype=np.float32), (row, col)),
                      shape=(ADJ_NODES, ADJ_NODES)).tocsr()
    A.sum_duplicates()
    if add_self:
        A = A + sp.eye(ADJ_NODES, dtype=np.float32, format="csr")
    deg = np.asarray(A.sum(1)).ravel()
    dinv = 1.0 / np.sqrt(np.maximum(deg, 1.0))
    M = (sp.diags(dinv) @ A @ sp.diags(dinv)).tocoo()
    return torch.sparse_coo_tensor(
        torch.from_numpy(np.vstack([M.row, M.col]).astype(np.int64)),
        torch.from_numpy(M.data.astype(np.float32)),
        (ADJ_NODES, ADJ_NODES)).coalesce()


print("Đang dựng ma trận kề toàn đồ thị (train)...")
ADJ_FULL = build_norm_adj(TRAIN_MASK)
print(f"ADJ_FULL nnz = {ADJ_FULL._nnz():,}")

# --- cạnh train user-job ở dạng tensor ---
UT = torch.from_numpy(uj_tr_src.astype(np.int64))
JT = torch.from_numpy((uj_tr_dst - O_J).astype(np.int64))
N_TRAIN_EDGES = int(UT.numel())
print(f"Cạnh train user-job: {N_TRAIN_EDGES:,}")


# ---------------------------------------------------------------- GNN models
def propagate(E: torch.Tensor, adj, layers: int) -> torch.Tensor:
    """Lan truyền LightGCN: trung bình embedding của các tầng 0..L."""
    h = E
    acc = [E]
    for _ in range(layers):
        h = torch.sparse.mm(adj, h)
        acc.append(h)
    return torch.stack(acc).mean(0)


def bpr_loss_from_scores(pos: torch.Tensor, neg: torch.Tensor, reg_term: torch.Tensor,
                         reg_w: float = 1e-5) -> torch.Tensor:
    """BPR: -log sigmoid(pos - neg) + reg * ||E||^2."""
    return -torch.nn.functional.logsigmoid(pos - neg).mean() + reg_w * reg_term


def train_lightgcn(dim: int, layers: int, epochs: int, steps: int = 10, batch: int = 8192,
                   lr: float = 0.02, seed: int = 42, adj=None):
    """LightGCN tập trung (mốc trên lý thuyết cho FL).

    Kỹ thuật: mỗi epoch lan truyền MỘT lần rồi tích luỹ gradient qua `steps`
    micro-batch, cuối epoch mới `opt.step()` một lần. Cách này tránh lỗi
    "variable modified by inplace operation" (Adam sửa tham số giữa hai lần
    backward trên cùng đồ thị tính toán).
    """
    adj = ADJ_FULL if adj is None else adj
    torch.manual_seed(seed)
    E = torch.nn.Parameter(torch.randn(N_NODES, dim) * 0.1)
    opt = torch.optim.Adam([E], lr=lr)
    gen = torch.Generator().manual_seed(seed)
    for _ep in range(epochs):
        for _si in range(steps):
            # Lan truyền lại MỖI bước tối ưu: sau khi Adam sửa E, đồ thị tính toán
            # cũ đã hỏng (backward lần hai -> "modified by inplace operation").
            out = propagate(E, adj, layers)
            b = torch.randint(0, N_TRAIN_EDGES, (batch,), generator=gen)
            eu = out[UT[b]]
            ej = out[O_J + JT[b]]
            pos = (eu * ej).sum(1)
            neg_idx = torch.randint(0, N_JOBS, (batch,), generator=gen)
            neg = (eu * out[O_J + neg_idx]).sum(1)
            loss = bpr_loss_from_scores(pos, neg, E.pow(2).mean())
            opt.zero_grad()
            loss.backward()
            opt.step()
            del out
    with torch.no_grad():
        return propagate(E.detach(), adj, layers)


def train_graphsage(dim: int, epochs: int, steps: int = 10, batch: int = 8192,
                    lr: float = 0.02, seed: int = 42):
    """GraphSAGE kiểu mean-aggregator (thêm MLP phi tuyến)."""
    torch.manual_seed(seed)
    E = torch.nn.Parameter(torch.randn(N_NODES, dim) * 0.1)
    W = torch.nn.Parameter(torch.eye(dim) * 0.8)
    # mean aggregator: D^-1 A (không self-loop) rồi cộng residual
    src = EDGE_INDEX[0][TRAIN_MASK]
    dst = EDGE_INDEX[1][TRAIN_MASK]
    row = np.concatenate([src, dst])
    col = np.concatenate([dst, src])
    A = sp.coo_matrix((np.ones(row.size, dtype=np.float32), (row, col)),
                      shape=(N_NODES, N_NODES)).tocsr()
    A.sum_duplicates()
    deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1.0)
    M = (sp.diags(1.0 / deg) @ A).tocoo()
    adj_mean = torch.sparse_coo_tensor(
        torch.from_numpy(np.vstack([M.row, M.col]).astype(np.int64)),
        torch.from_numpy(M.data.astype(np.float32)), (N_NODES, N_NODES)).coalesce()

    opt = torch.optim.Adam([E, W], lr=lr)
    gen = torch.Generator().manual_seed(seed)
    out = None
    for _ep in range(epochs):
        for _si in range(steps):
            # Tầng ra TUYẾN TÍNH (không relu): relu ở đầu ra làm mọi embedding
            # không âm -> tích vô hướng bị chi phối bởi chuẩn, hạng hoá thành
            # "popularity theo norm" và mô hình mất khả năng phân biệt.
            out = torch.sparse.mm(adj_mean, E) @ W + 0.5 * E
            b = torch.randint(0, N_TRAIN_EDGES, (batch,), generator=gen)
            eu = out[UT[b]]
            ej = out[O_J + JT[b]]
            pos = (eu * ej).sum(1)
            neg_idx = torch.randint(0, N_JOBS, (batch,), generator=gen)
            neg = (eu * out[O_J + neg_idx]).sum(1)
            loss = bpr_loss_from_scores(pos, neg, E.pow(2).mean() + W.pow(2).mean())
            opt.zero_grad()
            loss.backward()
            opt.step()
            del out
    with torch.no_grad():
        return torch.sparse.mm(adj_mean, E) @ W + 0.5 * E


def _sample_neighbours(adj_coo, max_deg: int):
    """Lấy tối đa `max_deg` láng giềng đầu tiên của mỗi nút (CSR đã sort theo cột)."""
    A = adj_coo.tocsr()
    A.sort_indices()
    deg = np.diff(A.indptr)
    take = np.minimum(deg, max_deg)
    dst = np.repeat(np.arange(A.shape[0]), take)
    offs = A.indptr[:-1][:, None] + np.arange(max_deg)[None, :]
    sel = take[:, None] > np.arange(max_deg)[None, :]
    src = A.indices[offs[sel]]
    return (torch.from_numpy(src.astype(np.int64)),
            torch.from_numpy(dst.astype(np.int64)))


def _adj_coo_from_mask(mask_edge):
    src = EDGE_INDEX[0][mask_edge]
    dst = EDGE_INDEX[1][mask_edge]
    row = np.concatenate([src, dst])
    col = np.concatenate([dst, src])
    A = sp.coo_matrix((np.ones(row.size, dtype=np.float32), (row, col)),
                      shape=(N_NODES, N_NODES)).tocsr()
    A.sum_duplicates()
    return A


def train_gat(dim: int, epochs: int, max_deg: int = 5, steps: int = 8, batch: int = 8192,
              lr: float = 0.02, seed: int = 42):
    """GAT 1 tầng attention, lấy mẫu tối đa `max_deg` láng giềng/nút (chia lô để vừa RAM)."""
    torch.manual_seed(seed)
    A = _adj_coo_from_mask(TRAIN_MASK)
    src, dst = _sample_neighbours(A, max_deg)
    E = torch.nn.Parameter(torch.randn(N_NODES, dim) * 0.1)
    W = torch.nn.Parameter(torch.eye(dim) * 0.8)
    aw = torch.nn.Parameter(torch.randn(2 * dim) * 0.1)
    opt = torch.optim.Adam([E, W, aw], lr=lr)
    gen = torch.Generator().manual_seed(seed)
    CHUNK = 400_000
    starts = list(range(0, src.numel(), CHUNK))
    n_edge = src.numel()

    def gat_forward():
        Wh = E @ W
        a1, a2 = aw[:dim], aw[dim:]
        mx = torch.full((N_NODES,), -1e30)
        for s in starts:
            e = min(s + CHUNK, n_edge)
            d = dst[s:e]
            lg = torch.nn.functional.leaky_relu(
                (Wh[src[s:e]] * a1).sum(-1) + (Wh[d] * a2).sum(-1), 0.2)
            mx = mx.scatter_reduce(0, d, lg, reduce="amax", include_self=True)
        den = torch.zeros(N_NODES)
        for s in starts:
            e = min(s + CHUNK, n_edge)
            d = dst[s:e]
            lg = torch.nn.functional.leaky_relu(
                (Wh[src[s:e]] * a1).sum(-1) + (Wh[d] * a2).sum(-1), 0.2)
            den = den.index_add(0, d, torch.exp(lg - mx[d]))
        agg = torch.zeros(N_NODES, dim)
        for s in starts:
            e = min(s + CHUNK, n_edge)
            d = dst[s:e]
            lg = torch.nn.functional.leaky_relu(
                (Wh[src[s:e]] * a1).sum(-1) + (Wh[d] * a2).sum(-1), 0.2)
            al = torch.exp(lg - mx[d]) / (den[d] + 1e-12)
            agg = agg.index_add(0, d, Wh[src[s:e]] * al[:, None])
        # Tầng ra TUYẾN TÍNH (không relu) — cùng lý do như GraphSAGE: relu ở đầu ra
        # làm embedding không âm, hạng bị chi phối bởi chuẩn thay vì hướng.
        return agg + E

    out = None
    for _ep in range(epochs):
        for _si in range(steps):
            out = gat_forward()
            b = torch.randint(0, N_TRAIN_EDGES, (batch,), generator=gen)
            eu = out[UT[b]]
            ej = out[O_J + JT[b]]
            pos = (eu * ej).sum(1)
            neg_idx = torch.randint(0, N_JOBS, (batch,), generator=gen)
            neg = (eu * out[O_J + neg_idx]).sum(1)
            loss = bpr_loss_from_scores(pos, neg, E.pow(2).mean())
            opt.zero_grad()
            loss.backward()
            opt.step()
            del out
    with torch.no_grad():
        return gat_forward()


# ------------------------------------------------- baseline BPR-MF (không đồ thị)
def train_bpr_mf(dim: int, epochs: int, steps: int = 10, batch: int = 8192,
                 lr: float = 0.02, seed: int = 42):
    """BPR-MF thuần ma trận thừa số hoá — KHÔNG dùng cấu trúc đồ thị."""
    torch.manual_seed(seed)
    PU = torch.nn.Parameter(torch.randn(N_USERS, dim) * 0.1)
    PJ = torch.nn.Parameter(torch.randn(N_JOBS, dim) * 0.1)
    opt = torch.optim.Adam([PU, PJ], lr=lr)
    gen = torch.Generator().manual_seed(seed)
    for _ep in range(epochs):
        for _si in range(steps):
            b = torch.randint(0, N_TRAIN_EDGES, (batch,), generator=gen)
            u = UT[b]
            pj = JT[b]
            nj = torch.randint(0, N_JOBS, (batch,), generator=gen)
            pos = (PU[u] * PJ[pj]).sum(1)
            neg = (PU[u] * PJ[nj]).sum(1)
            reg = PU[u].pow(2).sum() + PJ[pj].pow(2).sum() + PJ[nj].pow(2).sum()
            loss = (-torch.nn.functional.logsigmoid(pos - neg).mean()
                    + 1e-5 * reg / max(batch, 1))
            opt.zero_grad()
            loss.backward()
            opt.step()
    return torch.cat([PU.detach(), PJ.detach()], dim=0)   # (n_users+n_jobs) × dim


print("Đã định nghĩa xong thư viện mô hình.")

# %% [markdown]
# ## [4c] Chia dữ liệu theo client — code ĐÚNG (gán theo `client_of_job`)
#
# Mỗi client `c` giữ:
#
# * **job thuộc sở hữu của `c`** (`client_of_job[j] == c`),
# * **mọi application vào các job đó** (dù user đến từ đâu),
# * **nghề/kỹ năng công khai** nối từ các job và user đó.
#
# Client `c` **không** đọc cạnh `(u, j')` với `j'` thuộc client khác.
#
# Để chạy nhanh, cạnh train user-job được **sắp xếp theo client** trước, rồi mỗi
# client lấy một **lát cắt liên tục** — không quét lại 398.936 cạnh 9.116 lần.

# %%
T4b = time.perf_counter()

# --- sắp xếp cạnh train theo client của JOB (silo thật) ---
client_of_train_edge = CLIENT_OF_JOB[(uj_tr_dst - O_J)]
order_c = np.argsort(client_of_train_edge, kind="stable")
E_U_SORTED = uj_tr_src[order_c]
E_J_SORTED = uj_tr_dst[order_c]
E_C_SORTED = client_of_train_edge[order_c]
# ranh giới lát cắt của từng client: [slice_start[c], slice_end[c])
SLICE_START = np.searchsorted(E_C_SORTED, np.arange(N_CLIENTS_TOTAL), side="left")
SLICE_END = np.searchsorted(E_C_SORTED, np.arange(N_CLIENTS_TOTAL), side="right")
CLIENT_TRAIN_EDGES = SLICE_END - SLICE_START

# --- cấu trúc công khai (nghề/kỹ năng) để mở rộng đồ thị con ---
m_job_occ = EDGE_TYPE == ET_JOB_OCC
m_occ_skill = EDGE_TYPE == ET_OCC_SKILL
m_user_occ = EDGE_TYPE == ET_USER_OCC

OCC_OF_JOB = sp.csr_matrix(
    (np.ones(int(m_job_occ.sum()), dtype=np.float32),
     (EDGE_INDEX[0][m_job_occ] - O_J, EDGE_INDEX[1][m_job_occ] - O_O)),
    shape=(N_JOBS, N_OCC))
SKILL_OF_OCC = sp.csr_matrix(
    (np.ones(int(m_occ_skill.sum()), dtype=np.float32),
     (EDGE_INDEX[0][m_occ_skill] - O_O, EDGE_INDEX[1][m_occ_skill] - O_S)),
    shape=(N_OCC, N_SKILL))
OCC_OF_USER = sp.csr_matrix(
    (np.ones(int(m_user_occ.sum()), dtype=np.float32),
     (EDGE_INDEX[0][m_user_occ] - O_U, EDGE_INDEX[1][m_user_occ] - O_O)),
    shape=(N_USERS, N_OCC))

# danh sách nghề/kỹ năng dạng list để tra cứu nhanh
OCC_OF_JOB_L = [OCC_OF_JOB.indices[OCC_OF_JOB.indptr[i]:OCC_OF_JOB.indptr[i + 1]] + O_O
                for i in range(N_JOBS)]
SKILL_OF_OCC_L = [SKILL_OF_OCC.indices[SKILL_OF_OCC.indptr[i]:SKILL_OF_OCC.indptr[i + 1]] + O_S
                  for i in range(N_OCC)]
OCC_OF_USER_L = [OCC_OF_USER.indices[OCC_OF_USER.indptr[i]:OCC_OF_USER.indptr[i + 1]] + O_O
                 for i in range(N_USERS)]


def build_client_subgraph(cid: int, include_skill: bool = True,
                          include_occ: bool = True) -> dict:
    """Dựng đồ thị con của client `cid` = nhà tuyển dụng `cid`.

    Trả dict: nodes (chỉ số nút toàn cục), edge_index cục bộ, lu/lj (cạnh user-job
    cục bộ), n (số nút cục bộ), w (trọng số FedAvg = số cạnh user-job).

    include_skill=False / include_occ=False dùng cho ablation ở section [8].
    """
    a, b = SLICE_START[cid], SLICE_END[cid]
    if a == b:
        return None
    uu = np.unique(E_U_SORTED[a:b])                     # user index (0..N_USERS-1)
    jj = np.unique(E_J_SORTED[a:b] - O_J)               # job index (0..N_JOBS-1)

    occ_parts = [np.zeros(0, dtype=np.int64)]
    if include_occ:
        occ_set = set()
        for j in jj:
            occ_set.update(OCC_OF_JOB_L[j].tolist())
        for u in uu:
            occ_set.update(OCC_OF_USER_L[u].tolist())
        occ_parts.append(np.fromiter(occ_set, dtype=np.int64, count=len(occ_set)))
    occ_nodes = np.concatenate(occ_parts) if len(occ_parts) > 1 else occ_parts[0]

    skill_nodes = np.zeros(0, dtype=np.int64)
    if include_skill and occ_nodes.size:
        sk_set = set()
        for o in occ_nodes:
            sk_set.update(SKILL_OF_OCC_L[o - O_O].tolist())
        skill_nodes = np.fromiter(sk_set, dtype=np.int64, count=len(sk_set))

    nodes = np.concatenate([uu, jj + O_J, occ_nodes, skill_nodes]).astype(np.int64)
    n_local = nodes.size

    # ánh xạ toàn cục -> cục bộ
    gmap = -np.ones(N_NODES, dtype=np.int64)
    gmap[nodes] = np.arange(n_local)

    # giữ cạnh có CẢ HAI đầu nằm trong tập nút cục bộ VÀ thuộc train
    keep = (gmap[EDGE_INDEX[0]] >= 0) & (gmap[EDGE_INDEX[1]] >= 0) & TRAIN_MASK
    le = gmap[EDGE_INDEX[:, keep]]

    # cạnh user-job cục bộ (dùng cho BPR)
    is_u = nodes < N_USERS
    is_j = (nodes >= O_J) & (nodes < O_J + N_JOBS)
    m_uj = is_u[le[0]] & is_j[le[1]]
    return dict(
        cid=cid, nodes=nodes, edge_index=le, adj=None,
        lu=le[0][m_uj].astype(np.int64), lj=le[1][m_uj].astype(np.int64),
        n=n_local, nu=int(is_u.sum()), nj=int(is_j.sum()),
        n_occ=int(occ_nodes.size), n_skill=int(skill_nodes.size),
        w=float(m_uj.sum()),
    )


def norm_adj_local(le: np.ndarray, n: int):
    """Ma trận kề chuẩn hoá đối xứng cho đồ thị con cục bộ."""
    row = np.concatenate([le[0], le[1]])
    col = np.concatenate([le[1], le[0]])
    A = sp.coo_matrix((np.ones(row.size, dtype=np.float32), (row, col)),
                      shape=(n, n)).tocsr()
    A.sum_duplicates()
    A = A + sp.eye(n, dtype=np.float32, format="csr")
    deg = np.asarray(A.sum(1)).ravel()
    dinv = 1.0 / np.sqrt(np.maximum(deg, 1.0))
    M = (sp.diags(dinv) @ A @ sp.diags(dinv)).tocoo()
    return torch.sparse_coo_tensor(
        torch.from_numpy(np.vstack([M.row, M.col]).astype(np.int64)),
        torch.from_numpy(M.data.astype(np.float32)), (n, n)).coalesce()


def get_shard_adj(shard: dict):
    """Lấy ma trận kề cục bộ, CACHE lại trong shard để không dựng lại mỗi vòng."""
    if shard.get("adj") is None:
        shard["adj"] = norm_adj_local(shard["edge_index"], shard["n"])
    return shard["adj"]


def select_clients(n_clients: int, min_train_edges: int = 0) -> list:
    """Chọn `n_clients` client LỚN NHẤT (theo số cạnh train) để chạy thực nghiệm."""
    cand = np.where(CLIENT_TRAIN_EDGES >= max(1, min_train_edges))[0]
    ranked = cand[np.argsort(-CLIENT_TRAIN_EDGES[cand], kind="stable")]
    return ranked[:n_clients].tolist()


print(f"Đã sắp xếp {N_TRAIN_EDGES:,} cạnh train theo client của JOB "
      f"(kiểm tra: tổng theo client = {int(CLIENT_TRAIN_EDGES.sum()):,})")
assert int(CLIENT_TRAIN_EDGES.sum()) == N_TRAIN_EDGES, "số cạnh sau khi chia sai"
print(f"Client có ≥1 cạnh train: {int((CLIENT_TRAIN_EDGES > 0).sum()):,} / {N_CLIENTS_TOTAL:,} "
      f"— client rỗng: {int((CLIENT_TRAIN_EDGES == 0).sum())}")
print(f"cạnh train/client: min {CLIENT_TRAIN_EDGES.min()} | median "
      f"{int(np.median(CLIENT_TRAIN_EDGES))} | mean {CLIENT_TRAIN_EDGES.mean():.1f} | "
      f"max {CLIENT_TRAIN_EDGES.max():,}")
assert int((CLIENT_TRAIN_EDGES == 0).sum()) == 0, "có client rỗng — không thể chạy FL"

# kiểm tra đồ thị con đầu tiên
_sel0 = select_clients(CFG["fl_clients"])
_s0 = build_client_subgraph(_sel0[0])
print(f"\nVí dụ client {_s0['cid']}: {_s0['n']:,} nút cục bộ "
      f"({_s0['nu']:,} user, {_s0['nj']:,} job, {_s0['n_occ']} nghề, {_s0['n_skill']:,} kỹ năng) "
      f"| {_s0['edge_index'].shape[1]:,} cạnh | {int(_s0['w']):,} cạnh user-job")
mark("[4] Kiến trúc + chia client", T4)

# %%
# ============================================================================
# [4d] Vòng huấn luyện liên bang: FedAvg / FedProx
# ============================================================================


def local_train(shard: dict, E_global: torch.Tensor, dim: int, layers: int,
                epochs: int, lr: float, seed: int, mu: float = 0.0):
    """Huấn luyện cục bộ trên đồ thị con của MỘT client.

    Chỉ trả embedding cục bộ (không trả dữ liệu). `mu > 0` -> FedProx
    (thêm phạt ||E - E_global||^2).
    """
    nodes = shard["nodes"]
    n = shard["n"]
    lu = torch.from_numpy(shard["lu"])
    lj = torch.from_numpy(shard["lj"])
    if lu.numel() == 0:
        return None
    adj = get_shard_adj(shard)
    E0 = E_global[nodes].detach().clone()
    E = torch.nn.Parameter(E0.clone())
    opt = torch.optim.Adam([E], lr=lr)
    gen = torch.Generator().manual_seed(seed)
    loss_v = 0.0
    # Dùng FULL-BATCH trên toàn bộ cạnh user-job của client (đồ thị con nhỏ:
    # median 22 cạnh, max 4.320) — ổn định hơn mini-batch nhiều so với cỡ mẫu này.
    # Nếu client quá lớn thì lấy mẫu tối đa 4.096 cạnh.
    n_edges_local = int(lu.numel())
    if n_edges_local > 4096:
        _sel = torch.randperm(n_edges_local, generator=gen)[:4096]
        lu_b, lj_b = lu[_sel], lj[_sel]
    else:
        lu_b, lj_b = lu, lj
    # Ngân sách bước cố định ~20 bước/epoch cục bộ (tối thiểu 20, tối đa 100) để
    # `local_epochs=1` không bị undertrain — nếu không, so sánh (e) 1 vs 5 epoch
    # chỉ phản ánh "chưa hội tụ", không phản ánh chất lượng.
    n_steps = int(max(20, min(100, 20 * epochs)))
    for _si in range(n_steps):
        out = propagate(E, adj, layers)
        eu = out[lu_b]
        pos = (eu * out[lj_b]).sum(1)
        neg_idx = torch.randint(0, n, (lu_b.numel(),), generator=gen)
        neg = (eu * out[neg_idx]).sum(1)
        loss = bpr_loss_from_scores(pos, neg, E.pow(2).mean())
        if mu > 0:
            # FedProx: phạt độ lệch khỏi mô hình toàn cục, lấy TRUNG BÌNH để
            # không phụ thuộc số nút cục bộ (dùng .sum() sẽ lấn át BPR loss).
            loss = loss + 0.5 * mu * (E - E0).pow(2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        loss_v = float(loss.detach())
    # Trả embedding GỐC (CHƯA lan truyền) — đây là "mô hình cục bộ" client gửi lên.
    # Server chấm điểm bằng `full_forward` giống hệt mọi mô hình khác; nếu trả
    # embedding đã lan truyền thì bước chấm sẽ lan truyền LẦN HAI (sai).
    return E.detach(), loss_v


def full_forward(E: torch.Tensor, layers: int = None) -> torch.Tensor:
    """Lan truyền embedding trên TOÀN đồ thị train trước khi chấm điểm.

    Dùng chung cho mọi hệ (LightGCN, FedAvg, ...) để mọi mô hình được đánh giá
    bằng đúng một phép biến đổi — so sánh công bằng, không ưu tiên hệ nào.
    """
    L = LAYERS if layers is None else layers
    with torch.no_grad():
        return propagate(E.detach(), ADJ_FULL, L)


def run_federated(n_clients: int = 50, rounds: int = 6, local_epochs: int = 1,
                  dim: int = 32, layers: int = 2, lr: float = 0.05,
                  algo: str = "fedavg", mu: float = 0.01, seed: int = 42,
                  weighted: bool = True, client_ids: list = None,
                  include_skill: bool = True, include_occ: bool = True,
                  eval_cb=None, verbose: bool = True):
    """Mô phỏng FL: mỗi vòng, mọi client huấn luyện cục bộ rồi server FedAvg.

    Dữ liệu thô KHÔNG rời client: chỉ `E` (n × dim) được gửi lên.
    `eval_cb(E_global, round)` tuỳ chọn để đo metric sau mỗi vòng.
    """
    set_seed(seed)
    if client_ids is None:
        client_ids = select_clients(n_clients)
    E_global = torch.randn(N_NODES, dim) * 0.1     # "khởi tạo" chung, không phải dữ liệu

    shards = []
    for cid in client_ids:
        sh = build_client_subgraph(cid, include_skill=include_skill, include_occ=include_occ)
        if sh is not None and sh["lu"].size > 0:
            shards.append(sh)

    history = []
    latencies_ms = []
    for rnd in range(1, rounds + 1):
        t_round = time.perf_counter()
        num = torch.zeros(N_NODES, dim)
        den = torch.zeros(N_NODES)
        losses = []
        for sh in shards:
            t_client = time.perf_counter()
            res = local_train(sh, E_global, dim=dim, layers=layers, epochs=local_epochs,
                              lr=lr, seed=seed * 1000 + rnd, mu=(mu if algo == "fedprox" else 0.0))
            latencies_ms.append((time.perf_counter() - t_client) * 1000.0)
            if res is None:
                continue
            E_local, loss_v = res
            losses.append(loss_v)
            w = sh["w"] if weighted else 1.0
            idx = torch.from_numpy(sh["nodes"])
            num.index_add_(0, idx, E_local * w)
            den.index_add_(0, idx, torch.full((sh["n"],), float(w)))
        touched = den > 0
        E_global = E_global.clone()
        E_global[touched] = (num[touched] / den[touched][:, None])
        rec = dict(round=rnd, loss=float(np.mean(losses)) if losses else float("nan"),
                   round_seconds=round(time.perf_counter() - t_round, 2),
                   n_clients=len(shards))
        if eval_cb is not None:
            rec.update(eval_cb(E_global, rnd))
        history.append(rec)
        if verbose:
            extra = " ".join(f"{k}={v:.4f}" for k, v in rec.items()
                             if isinstance(v, float) and k not in ("round_seconds", "loss"))
            print(f"  vòng {rnd:2d}/{rounds}: loss={rec['loss']:.4f} "
                  f"({rec['round_seconds']:.1f}s) {extra}")
    return dict(E=E_global, history=history,
                latencies_ms=np.array(latencies_ms), n_shards=len(shards),
                client_ids=[sh["cid"] for sh in shards])


def job_universe_of_clients(client_ids) -> np.ndarray:
    """Tập job (chỉ số toàn cục) thuộc sở hữu của các client đã chọn.

    Dùng để đánh giá công bằng: FL chỉ có thể biết các job thuộc client tham gia;
    job ngoài vũ trụ này giữ embedding khởi tạo ngẫu nhiên nên chấm điểm trên
    chúng là không công bằng cho FL.
    """
    owned = np.isin(CLIENT_OF_JOB, np.asarray(client_ids))
    return np.where(owned)[0]


print("Đã định nghĩa xong vòng FL (FedAvg / FedProx).")
