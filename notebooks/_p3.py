# %% [markdown]
# # [5] Phân tích tham số
#
# Bốn siêu tham số cần khảo sát, mỗi cái một trục:
#
# | Tham số | Giá trị thử | Câu hỏi |
# |---|---|---|
# | `dim` (số chiều embedding) | **16, 32, 64** | Bao nhiêu chiều là đủ cho 265k nút? |
# | `layers` (số tầng lan truyền) | **1, 2, 3** | Lan truyền xa hơn có giúp hay chỉ làm mịn quá mức? |
# | `n_clients` | **5, 10, 20** | Ít client (nhiều dữ liệu/client) có tốt hơn? |
# | `local_epochs` | **1, 5** | Client học kỹ hơn mỗi vòng có lợi? |
#
# Mỗi cấu hình chạy **cùng ngân sách** (cùng số vòng, cùng batch) để so sánh công bằng.
# Kết quả ghi vào `sweep_results` và vẽ thành bảng + biểu đồ.
#
# > Chi phí mỗi lần chạy trên CPU ~10-60 s tuỳ cấu hình; `SCALE='tiny'` bỏ qua sweep.
#
# ## [5b] Thư viện đánh giá dùng chung (chi tiết metric ở section `[7]`)
#
# Toàn bộ metric tính trên **cùng một tập ứng viên** và **cùng một mẫu user** để
# so sánh được giữa các mô hình.

# %%
# ============================================================================
# [5b] Chuẩn bị tập đánh giá + hàm tính metric (dùng lại ở [7] và [8])
# ============================================================================
T5 = time.perf_counter()
set_seed(42)

# --- job có ít nhất 1 cạnh train = catalog ứng viên ---
job_train_deg = np.bincount(uj_tr_dst - O_J, minlength=N_JOBS)
CATALOG = np.where(job_train_deg >= 1)[0]                     # 82.876 job
CATALOG_POS = -np.ones(N_JOBS, dtype=np.int64)
CATALOG_POS[CATALOG] = np.arange(CATALOG.size)
COLD_JOBS = np.where(job_train_deg == 0)[0]                   # 1.969 job chỉ có test
IST_COLD = np.zeros(N_JOBS, dtype=bool)
IST_COLD[COLD_JOBS] = True
print(f"Catalog ứng viên: {CATALOG.size:,} job | cold-start (0 cạnh train): {COLD_JOBS.size:,} "
      f"({100 * COLD_JOBS.size / N_JOBS:.2f}%)")

# --- positive của từng user trong test ---
TEST_USER = EDGE_INDEX[0][M_TE]
TEST_JOB = EDGE_INDEX[1][M_TE] - O_J
POS_ALL = {}
for _u, _j in zip(TEST_USER.tolist(), TEST_JOB.tolist()):
    POS_ALL.setdefault(_u, []).append(_j)

# --- job user đã tương tác trong train (để loại khỏi gợi ý) ---
SEEN = {}
for _u, _j in zip(uj_tr_src.tolist(), (uj_tr_dst - O_J).tolist()):
    SEEN.setdefault(_u, []).append(_j)

# --- mẫu user đánh giá: chỉ user có ≥1 positive NẰM TRONG catalog ---
USERS_WITH_POS = np.array(sorted(
    u for u, js in POS_ALL.items() if any(CATALOG_POS[j] >= 0 for j in js)), dtype=np.int64)
print(f"User có positive trong catalog: {USERS_WITH_POS.size:,}")

_rng_eval = np.random.default_rng(42)
N_EVAL = int(min(CFG["eval_users"], USERS_WITH_POS.size))
EVAL_USERS = np.sort(_rng_eval.choice(USERS_WITH_POS, size=N_EVAL, replace=False))
EVAL_POS = [np.array([CATALOG_POS[j] for j in POS_ALL[int(u)] if CATALOG_POS[j] >= 0],
                     dtype=np.int64) for u in EVAL_USERS]
print(f"ĐÁNH GIÁ TRÊN MẪU: {N_EVAL:,} user (lấy ngẫu nhiên seed 42 từ "
      f"{USERS_WITH_POS.size:,} user) — đây là MẪU, không phải toàn bộ")
print(f"  positive/user: min {min(len(p) for p in EVAL_POS)} | "
      f"mean {np.mean([len(p) for p in EVAL_POS]):.2f} | max {max(len(p) for p in EVAL_POS)}")

# --- giá trị đúng (IDCG) cho NDCG@20, tính 1 lần ---
_IDCG = np.zeros(64)
for _k in range(1, 64):
    _IDCG[_k] = (1.0 / np.log2(np.arange(2, 2 + min(_k, 20)))).sum()


def scores_for_model(E: torch.Tensor, users: np.ndarray, catalog: np.ndarray = None) -> np.ndarray:
    """Tính điểm user × catalog cho một ma trận embedding.

    E: (N_NODES, dim) cho mô hình đồ thị, hoặc (N_USERS+N_JOBS, dim) cho BPR-MF.
    `catalog`: chỉ số job toàn cục dùng làm ứng viên (mặc định CATALOG).
    """
    catalog = CATALOG if catalog is None else catalog
    E = E.detach().cpu().numpy() if torch.is_tensor(E) else E
    if E.shape[0] == N_NODES:
        PU = E[users]
        PJ = E[O_J:O_J + N_JOBS][catalog]
    else:                                   # BPR-MF: [user; job]
        PU = E[users]
        PJ = E[N_USERS + catalog]
    sc = PU @ PJ.T
    # loại job đã tương tác trong train (đánh giá "gợi ý MỚI")
    pos_of_catalog = -np.ones(N_JOBS, dtype=np.int64)
    pos_of_catalog[catalog] = np.arange(catalog.size)
    for r, u in enumerate(users.tolist()):
        idx = [pos_of_catalog[j] for j in SEEN.get(u, []) if pos_of_catalog[j] >= 0]
        if idx:
            sc[r, idx] = -np.inf
    return sc


def metrics_from_scores(sc: np.ndarray, users: np.ndarray,
                        pos_list: list, k_list=(10, 20),
                        catalog: np.ndarray = None) -> dict:
    """Recall@k, NDCG@20, MRR@20. Trả vector theo từng user để bootstrap."""
    catalog = CATALOG if catalog is None else catalog
    n_cat = catalog.size
    n = sc.shape[0]
    out = {f"recall@{k}": np.full(n, np.nan) for k in k_list}
    out["ndcg@20"] = np.full(n, np.nan)
    out["mrr@20"] = np.full(n, np.nan)
    top1 = np.zeros(n, dtype=np.int64)
    TOPM = 64
    for r in range(n):
        s = sc[r]
        pos = pos_list[r]
        if pos.size == 0:
            continue
        cand = np.argpartition(-s, TOPM)[:TOPM + 1]
        cand = cand[np.argsort(-s[cand])]
        rank = np.full(n_cat, 10 ** 6, dtype=np.int64)
        rank[cand] = np.arange(cand.size)
        pr = rank[pos]
        for k in k_list:
            out[f"recall@{k}"][r] = float((pr < k).mean())
        dcg = (1.0 / np.log2(pr[pr < 20] + 2)).sum()
        out["ndcg@20"][r] = dcg / max(_IDCG[min(pos.size, 20)], 1e-9)
        out["mrr@20"][r] = 0.0 if (pr >= 20).all() else 1.0 / (pr.min() + 1)
        top1[r] = catalog[cand[0]]
    out["_top1"] = top1
    return out


def summarize(vec: dict, coverage_top1: np.ndarray = None, catalog_size: int = None) -> dict:
    """Gộp vector per-user thành số trung bình (bỏ NaN)."""
    res = {}
    for k, v in vec.items():
        if k.startswith("_"):
            continue
        res[k] = float(np.nanmean(v)) if np.size(v) else float("nan")
    if coverage_top1 is not None:
        n_cat = CATALOG.size if catalog_size is None else catalog_size
        valid = coverage_top1[coverage_top1 >= 0]
        res["coverage@10"] = float(len(set(valid.tolist())) / n_cat) if valid.size else 0.0
    return res


def bootstrap_ci(vec: np.ndarray, n_boot: int = 1000, alpha: float = 0.05, seed: int = 42):
    """Bootstrap CI 95% cho trung bình của một metric theo user."""
    v = np.asarray(vec, dtype=np.float64)
    v = v[~np.isnan(v)]
    if v.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for i in range(n_boot):
        means[i] = v[rng.integers(0, v.size, v.size)].mean()
    return (float(np.percentile(means, 100 * alpha / 2)),
            float(np.percentile(means, 100 * (1 - alpha / 2))))


def evaluate_embeddings(E, users=None, pos_list=None, with_ci: bool = False,
                        seed: int = 42, catalog: np.ndarray = None) -> dict:
    """Chấm điểm + metric cho một ma trận embedding."""
    users = EVAL_USERS if users is None else users
    pos_list = EVAL_POS if pos_list is None else pos_list
    catalog = CATALOG if catalog is None else catalog
    sc = scores_for_model(E, users, catalog)
    vec = metrics_from_scores(sc, users, pos_list, catalog=catalog)
    res = summarize(vec, vec["_top1"], catalog_size=catalog.size)
    res["_vec"] = {k: v for k, v in vec.items() if not k.startswith("_")}
    if with_ci:
        for key in ("recall@10", "recall@20", "ndcg@20", "mrr@20"):
            lo, hi = bootstrap_ci(vec[key], seed=seed)
            res[f"{key}_ci95"] = [round(lo, 4), round(hi, 4)]
    return res


print("Đã chuẩn bị xong hạ tầng đánh giá.")

# %% [markdown]
# ## [5c] Sweep tham số
#
# Mỗi dòng là một cấu hình FL (FedAvg, weighted). Cột `R@20` là chỉ số chính.
# Bảng in ra ngay và vẽ thành 4 biểu đồ nhỏ.

# %%
T5b = time.perf_counter()
SWEEP = []
SWEEP_CFG = [
    # (dim, layers, n_clients, local_epochs)
    (16, 2, 10, 1), (32, 2, 10, 1), (64, 2, 10, 1),      # trục dim
    (32, 1, 10, 1), (32, 2, 10, 1), (32, 3, 10, 1),      # trục layers
    (32, 2, 5, 1), (32, 2, 10, 1), (32, 2, 20, 1),       # trục n_clients
    (32, 2, 10, 5),                                       # trục local_epochs
]
# bỏ trùng lặp (32,2,10,1) xuất hiện ở 3 trục — chỉ chạy 1 lần
SEEN_CFG = set()
SWEEP_CFG_UNIQUE = []
for c in SWEEP_CFG:
    if c not in SEEN_CFG:
        SEEN_CFG.add(c)
        SWEEP_CFG_UNIQUE.append(c)

if not CFG["sweep"]:
    print(f"SCALE={SCALE}: bỏ qua sweep để chạy nhanh. Đổi SCALE='small' để chạy đủ.")
else:
    for (dim, layers, ncl, lep) in SWEEP_CFG_UNIQUE:
        t0 = time.perf_counter()
        res = run_federated(n_clients=ncl, rounds=CFG["fl_rounds"], local_epochs=lep,
                            dim=dim, layers=layers, algo="fedavg", weighted=True,
                            eval_cb=lambda E, r: {}, verbose=False)
        m = evaluate_embeddings(full_forward(res["E"]))
        dt = time.perf_counter() - t0
        row = dict(dim=dim, layers=layers, n_clients=ncl, local_epochs=lep,
                   recall10=round(m["recall@10"], 4), recall20=round(m["recall@20"], 4),
                   ndcg20=round(m["ndcg@20"], 4), mrr20=round(m["mrr@20"], 4),
                   coverage=round(m["coverage@10"], 4), seconds=round(dt, 1),
                   n_shards=res["n_shards"])
        SWEEP.append(row)
        print(f"  dim={dim:2d} layers={layers} n_clients={ncl:2d} local_epochs={lep} "
              f"-> R@20={row['recall20']:.4f} NDCG@20={row['ndcg20']:.4f} ({dt:.0f}s)")

    # --- bảng ---
    if SWEEP:
        import csv as _csv
        cols = ["dim", "layers", "n_clients", "local_epochs", "recall10", "recall20",
                "ndcg20", "mrr20", "coverage", "seconds", "n_shards"]
        print("\n=== BẢNG SWEEP ===")
        print(" | ".join(f"{c:>12s}" for c in cols))
        for row in SWEEP:
            print(" | ".join(f"{row[c]:>12}" for c in cols))
        with open(os.path.join(OUT, "sweep_results.csv"), "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(SWEEP)

        # --- biểu đồ: 4 trục ---
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))
        axes = axes.ravel()
        base = dict(dim=32, layers=2, n_clients=10, local_epochs=1)

        def _pick(field):
            rows = [r for r in SWEEP if all(r[k] == v for k, v in base.items() if k != field)]
            rows.sort(key=lambda r: r[field])
            return [r[field] for r in rows], [r["recall20"] for r in rows], [r["ndcg20"] for r in rows]

        for ax, field, xlabel in zip(axes,
                                     ["dim", "layers", "n_clients", "local_epochs"],
                                     ["dim", "số tầng lan truyền", "số client", "local_epochs"]):
            xs, r20, nd = _pick(field)
            if not xs:
                ax.set_title(f"{xlabel} (thiếu cấu hình nền)"); continue
            ax.plot(range(len(xs)), r20, "o-", label="Recall@20")
            ax.plot(range(len(xs)), nd, "s--", label="NDCG@20")
            ax.set_xticks(range(len(xs)))
            ax.set_xticklabels([str(x) for x in xs])
            ax.set_xlabel(xlabel); ax.set_ylabel("giá trị")
            ax.set_title(f"Ảnh hưởng {xlabel}"); ax.legend(); ax.grid(alpha=.3)
        fig.suptitle("Phân tích tham số — FedAvg trên CareerBuilder (mẫu user cố định)", fontsize=13)
        fig.tight_layout()
        sweep_path = os.path.join(FIG, "F02_sweep_tham_so.png")
        fig.savefig(sweep_path, dpi=160, bbox_inches="tight")
        plt.close(fig)
        print("Đã lưu hình:", sweep_path)

mark("[5] Phân tích tham số", T5, f"{len(SWEEP)} cấu hình")

# %% [markdown]
# # [6] Môi trường — cài đặt, mount Google Drive, hướng dẫn upload
#
# Phần **bootstrap môi trường đã chạy ở cell code đầu tiên** (dò `ART`/`OUT`,
# chọn `device`, đặt `SCALE`). Section này in lại **trạng thái môi trường** và
# hướng dẫn chi tiết cho ba nền tảng.
#
# ## 6.1 Bảng so sánh ba môi trường
#
# | | **Kaggle** (khuyến nghị) | **Google Colab** | **Local** |
# |---|---|---|---|
# | Gói có sẵn | `torch`, `numpy`, `scipy`, `matplotlib` | `torch`, `numpy`, `scipy`, `matplotlib` | cần `pip install -r requirements.txt` |
# | Cài thêm | **không cần** | có thể cần `torch` bản CPU | như trên |
# | Nơi đọc dữ liệu | `/kaggle/input/dss-gnn-fl-v3/artifacts/v3` | Google Drive hoặc `/content` | `artifacts/v3` |
# | Nơi ghi | `/kaggle/working/results_v3` | `/content/results_v3` | `results/v3` |
# | GPU | T4 ×2 (không bắt buộc) | T4 (không bắt buộc) | không cần |
# | Giới hạn phiên | 12 h (GPU) / 9 h | 12 h | — |
#
# ## 6.2 Mount Google Drive (chỉ Colab)
#
# ```python
# # 1) Bật ở cell 0:  MOUNT_DRIVE = True
# # 2) Hoặc chạy tay:
# from google.colab import drive
# drive.mount('/content/drive')
# # 3) Đặt artifacts tại:  /content/drive/MyDrive/dss-gnn-fl-v3/artifacts/v3/graph.npz
# #    Cell 0 tự dò đường dẫn này.
# ```
#
# ## 6.3 Hướng dẫn upload (nhắc lại, chi tiết ở cell markdown đầu notebook)
#
# 1. `zip -r dss-gnn-fl-v3.zip artifacts/v3` (26,9 MB)
# 2. Kaggle → **Datasets → New Dataset** → upload → tên `dss-gnn-fl-v3`
# 3. Notebook → **Add Data** → chọn dataset → `/kaggle/input/dss-gnn-fl-v3/`
# 4. (Tuỳ chọn) upload `test_clean_index.npz` để dùng danh sách cạnh sạch đã kiểm chứng
# 5. Bật **Internet** chỉ khi cần `pip install`; sau đó chạy offline
#
# ## 6.4 Kiểm tra môi trường đã sẵn sàng

# %%
# ============================================================================
# [6e] In lại trạng thái môi trường + kiểm tra quyền ghi
# ============================================================================
T6 = time.perf_counter()
probe = os.path.join(OUT, "_write_probe.txt")
try:
    with open(probe, "w", encoding="utf-8") as f:
        f.write("ok")
    os.remove(probe)
    writable = True
except Exception as exc:
    writable = False
    print("KHÔNG ghi được vào OUT:", type(exc).__name__, exc)

print("=== MÔI TRƯỜNG SẴN SÀNG ===")
print(f"device                 : {device}")
print(f"ART                    : {ART}")
print(f"  graph.npz            : {os.path.getsize(GRAPH_PATH) / 1e6:.2f} MB")
print(f"  clients.json         : {os.path.getsize(CLIENTS_PATH) / 1e6:.2f} MB")
print(f"  meta.json            : {os.path.getsize(META_PATH) / 1e3:.1f} KB")
print(f"OUT                    : {OUT}  (ghi được: {writable})")
print(f"FIG                    : {FIG}")
print(f"SCALE                  : {SCALE} -> {CFG}")
print(f"torch.cuda.is_available: {torch.cuda.is_available()}  (không bắt buộc)")
print("Không cần internet sau bước cài đặt: mọi dữ liệu đọc từ ART.")
assert writable, f"Không ghi được vào {OUT} — đổi OUT sang thư mục có quyền ghi."
mark("[6] Môi trường", T6)

# %% [markdown]
# # [7] Chỉ số đánh giá + biểu đồ
#
# ## 7.1 Metric
#
# | Metric | Công thức | Ý nghĩa |
# |---|---|---|
# | **Recall@10 / @20** | $\frac{1}{|U|}\sum_u \frac{\|Rel_u \cap TopK_u\|}{\|Rel_u\|}$ | Bao nhiêu phần trăm tin liên quan được lọt vào top-K |
# | **NDCG@20** | $\frac{DCG@20}{IDCG@20}$, $DCG=\sum_i \frac{rel_i}{\log_2(i+1)}$ | Chất lượng **thứ hạng**, không chỉ "có mặt" |
# | **MRR@20** | $\frac{1}{|U|}\sum_u \frac{1}{rank_u^{first}}$ | Tin liên quan đầu tiên xuất hiện sớm đến đâu |
# | **Coverage@10** | $\frac{\| \bigcup_u Top10_u \|}{|Catalog|}$ | Hệ có bị "dồn" vào vài job phổ biến không |
#
# Mọi metric tính **trung bình theo user** (macro), bỏ job user đã tương tác trong
# train (chỉ gợi ý tin **mới**), và tính trên **82.876 job** catalog có ≥1 cạnh train.
#
# ## 7.2 Ba tập đánh giá — BẮT BUỘC báo cả ba
#
# | Tập | Mô tả | Lý do |
# |---|---|---|
# | **(a) Toàn bộ test** | 37.957 cạnh test | Con số "thô", dễ so sánh với tài liệu |
# | **(b) Test SẠCH** | 37.077 cạnh (loại 880 cạnh, **2,32%**) | Loại rò rỉ **đường vòng** `u → nghề → j` trong train |
# | **(c) Bỏ cold-start job** | Loại 1.969 job chỉ có test | Job chưa từng thấy khi train → không thể học |
#
# ### Rò rỉ đường vòng là gì?
#
# Nếu user `u` và job `j` **cùng nối tới một nút nghề** qua cạnh **train**, mô hình có
# thể đi `u → nghề → j` để "đoán" cạnh test `(u, j)` mà không cần học tương tác thật.
# Đây là rò rỉ **gián tiếp**, khác với rò rỉ trực tiếp (đã bị `train_mask`/`test_mask`
# loại sạch: `train_mask & test_mask = 0`).
#
# File `test_clean_index.npz` (37.957 phần tử, `is_clean` bool) đã kiểm chứng sẵn.
# Nếu thiếu, notebook **tự tính lại** từ `graph.npz` và in rõ đang dùng đường nào.
#
# ### Sau khi làm sạch, mẫu đánh giá thay đổi
#
# Loại 880 cạnh khiến **348 user không còn cạnh test nào**. Những user này **bị loại
# khỏi mẫu**, KHÔNG tính là miss (nếu tính là miss thì R@20 bị kéo xuống sai).
#
# ## 7.3 Baseline
#
# | Baseline | Cách hoạt động | Vai trò |
# |---|---|---|
# | **Popularity** | Xếp hạng job theo số application trong train | Mốc "không học gì" |
# | **Item-KNN** | $s(u,j)=\sum_{j'\in N(u)}\cos(j,j')$ trên ma trận user–job | Mốc collaborative lọc cổ điển |
# | **BPR-MF** | Thừa số hoá ma trận thuần, **không** dùng đồ thị | Chứng minh cấu trúc đồ thị có đóng góp |
#
# ## 7.4 Bootstrap CI 95%
#
# Với mỗi metric, lấy **1.000 mẫu có hoàn lại** trên tập user, tính trung bình mỗi
# mẫu, lấy phân vị 2,5% và 97,5%. CI rộng = kết luận chưa chắc; CI hẹp = ổn định.
#
# ## 7.5 ⚠️ HAI VŨ TRỤ ĐÁNH GIÁ — đọc kỹ trước khi so sánh FedAvg với LightGCN
#
# Đây là điểm dễ bị hiểu sai nhất trong notebook:
#
# | Vũ trụ | Catalog | Ai được đánh giá công bằng? |
# |---|---|---|
# | **Toàn đồ thị** | 82.876 job có ≥1 cạnh train | Mô hình **tập trung** (LightGCN, GraphSAGE, GAT, BPR-MF, Item-KNN, Popularity) — chúng thấy **toàn bộ** 726.407 cạnh train |
# | **Vũ trụ FL** | job thuộc **N client tham gia** (mặc định 50 → ~9.058 job) | **FedAvg** — nó chỉ học được từ các client đó |
#
# **Vì sao phải tách**: FL chỉ có 50/9.116 client, tức chỉ sở hữu **~11% số job**.
# Những job còn lại **giữ nguyên embedding khởi tạo ngẫu nhiên** vì chưa client nào
# học chúng. Nếu chấm FedAvg trên toàn catalog 82.876 job, hơn 89% ứng viên là
# "rác chưa huấn luyện" → R@20 sụp còn vài phần trăm và **không phản ánh năng lực
# thật** của FL, chỉ phản ánh việc nó chưa thấy dữ liệu.
#
# > **Cách đọc đúng**: so FedAvg với các mô hình khác **trong cùng vũ trụ FL**
# > (bảng "SO SÁNH CÔNG BẰNG TRÊN CÙNG VŨ TRỤ"). Con số FedAvg trên toàn catalog
# > được in ra chỉ để tham khảo và **không** dùng để kết luận FL kém hơn LightGCN.
#
# Đây cũng chính là lý do section `[8]` cố định vũ trụ đánh giá khi so các biến thể.

# %%
# ============================================================================
# [7b] Nạp / tự tính danh sách cạnh test SẠCH (có fallback)
# ============================================================================
T7 = time.perf_counter()
CLEAN_PATH = None
for _cand in [os.path.join(ART, "test_clean_index.npz"),
              os.path.join(os.path.dirname(ART), "_newdata_audit", "v3_verify", "test_clean_index.npz"),
              os.path.join(os.path.dirname(os.path.dirname(ART)), "_newdata_audit",
                           "v3_verify", "test_clean_index.npz")]:
    if os.path.exists(_cand):
        CLEAN_PATH = _cand
        break

CLEAN_SOURCE = None
if CLEAN_PATH:
    _cl = np.load(CLEAN_PATH, allow_pickle=False)
    IS_CLEAN = _cl["is_clean"].astype(bool)
    _edge_pos = _cl["edge_pos"].astype(np.int64)
    _user_cl = _cl["user"].astype(np.int64)
    _job_cl = _cl["job"].astype(np.int64)
    # kiểm tra khớp thứ tự với edge_index
    _te_pos = np.where(M_TE)[0]
    assert IS_CLEAN.size == N_TEST_UJ, (IS_CLEAN.size, N_TEST_UJ)
    if np.array_equal(_te_pos, _edge_pos):
        CLEAN_SOURCE = f"file có sẵn: {CLEAN_PATH}"
    else:
        CLEAN_SOURCE = None
        print("File clean không khớp thứ tự cạnh test -> tự tính lại.")

if CLEAN_SOURCE is None:
    # --- FALLBACK: tự tính 880 cạnh có đường vòng u -> nghề -> j trong TRAIN ---
    print("Không tìm thấy test_clean_index.npz -> TỰ TÍNH lại đường vòng từ graph.npz.")
    _occ_u_tr = [set(OCC_OF_USER_L[u].tolist()) for u in range(N_USERS)]
    _occ_j_tr = [set(OCC_OF_JOB_L[j].tolist()) for j in range(N_JOBS)]
    DETOUR = np.zeros(N_TEST_UJ, dtype=bool)
    for i, (u, j) in enumerate(zip(uj_te_src.tolist(), (uj_te_dst - O_J).tolist())):
        su = _occ_u_tr[u]
        if su:
            sj = _occ_j_tr[j]
            if sj and not su.isdisjoint(sj):
                DETOUR[i] = True
    IS_CLEAN = ~DETOUR
    _user_cl = uj_te_src
    _job_cl = uj_te_dst - O_J
    CLEAN_SOURCE = "TỰ TÍNH từ graph.npz (không có file kiểm chứng)"

N_LEAK = int((~IS_CLEAN).sum())
print(f"Nguồn danh sách sạch : {CLEAN_SOURCE}")
print(f"Cạnh test            : {N_TEST_UJ:,}")
print(f"Cạnh SẠCH            : {int(IS_CLEAN.sum()):,} ({100 * IS_CLEAN.mean():.2f}%)")
print(f"Cạnh rò rỉ đường vòng: {N_LEAK:,} ({100 * N_LEAK / N_TEST_UJ:.2f}%)")
assert N_LEAK == 880 or "tự tính" in CLEAN_SOURCE, \
    f"số cạnh rò rỉ phải là 880, nhận {N_LEAK}"

# --- user còn cạnh test sạch (loại 348 user mất hết test) ---
USERS_CLEAN = np.unique(_user_cl[IS_CLEAN])
print(f"User có cạnh test      : {np.unique(uj_te_src).size:,}")
print(f"User còn cạnh test SẠCH: {USERS_CLEAN.size:,} "
      f"(mất {np.unique(uj_te_src).size - USERS_CLEAN.size} user)")

# --- mẫu đánh giá SẠCH dùng cùng seed: chọn từ USERS_CLEAN ---
USERS_CLEAN_POS_OK = np.array(
    [u for u in USERS_CLEAN
     if any(CATALOG_POS[j] >= 0 for j in POS_ALL[int(u)])], dtype=np.int64)
N_EVAL_CLEAN = int(min(CFG["eval_users"], USERS_CLEAN_POS_OK.size))
EVAL_USERS_CLEAN = np.sort(np.random.default_rng(42).choice(
    USERS_CLEAN_POS_OK, size=N_EVAL_CLEAN, replace=False))
EVAL_POS_CLEAN = []
for u in EVAL_USERS_CLEAN:
    js = [j for j in POS_ALL[int(u)] if CATALOG_POS[j] >= 0 and
          IS_CLEAN[np.where((uj_te_src == u) & ((uj_te_dst - O_J) == j))[0][0]]]
    EVAL_POS_CLEAN.append(np.array([CATALOG_POS[j] for j in js], dtype=np.int64))
print(f"Mẫu đánh giá SẠCH      : {EVAL_USERS_CLEAN.size:,} user "
      f"(positive/user mean {np.mean([len(p) for p in EVAL_POS_CLEAN]):.2f})")

# %% [markdown]
# ## [7c] Chạy so sánh: 3 GNN + 3 baseline
#
# Mỗi mô hình được huấn luyện **cùng ngân sách** (`CFG['gnn_epochs']`), cùng seed.
# Sau đó chấm điểm trên **hai mẫu user**: (a) mẫu đầy đủ và (b) mẫu sạch.

# %%
T7b = time.perf_counter()
MODEL_RESULTS = {}
MODEL_EMB = {}   # giữ embedding từng mô hình để đánh giá lại trên vũ trụ FL


def _record(name, E, kind="graph"):
    """Chấm 1 mô hình trên 3 tập: (a) catalog đầy đủ, (b) test sạch, (c) tính cold-start là miss."""
    out = {"name": name, "kind": kind}
    # (a) mẫu đầy đủ — positive chỉ gồm job NẰM TRONG catalog
    a = evaluate_embeddings(E, EVAL_USERS, EVAL_POS, with_ci=True)
    out.update({k: v for k, v in a.items() if k != "_vec"})
    out["_vec_full"] = a["_vec"]
    # (b) mẫu SẠCH (loại 880 cạnh rò rỉ đường vòng)
    b = evaluate_embeddings(E, EVAL_USERS_CLEAN, EVAL_POS_CLEAN)
    out["clean_recall20"] = b["recall@20"]
    out["clean_ndcg20"] = b["ndcg@20"]
    out["clean_mrr20"] = b["mrr@20"]
    out["clean_recall10"] = b["recall@10"]
    # (c) COLD-START tính là MISS: mẫu số là TẤT CẢ positive của user (kể cả job
    #     không có cạnh train). Job cold không nằm trong catalog nên không bao giờ
    #     được xếp hạng -> luôn miss. Đây là con số "bi quan" để so sánh.
    n_cold_pos = int(sum(1 for u in EVAL_USERS.tolist()
                         for j in POS_ALL[int(u)] if CATALOG_POS[j] < 0))
    sc_c = scores_for_model(E, EVAL_USERS)
    rec20_c = np.zeros(len(EVAL_USERS))
    for r, (u, p) in enumerate(zip(EVAL_USERS.tolist(), EVAL_POS)):
        top = np.argpartition(-sc_c[r], 21)[:22]
        rank = np.full(CATALOG.size, 10 ** 6, dtype=np.int64)
        rank[top] = np.argsort(-sc_c[r][top])
        hits_in_cat = int((rank[p] < 20).sum())
        total = len(POS_ALL[u])
        rec20_c[r] = hits_in_cat / total if total else np.nan
    out["recall20_with_cold_as_miss"] = float(np.nanmean(rec20_c))
    out["n_cold_positives_in_eval"] = n_cold_pos
    out["coverage@10"] = a["coverage@10"]
    return out


# ---- baseline 1: Popularity ----
t0 = time.perf_counter()
pop = job_train_deg.astype(np.float64).copy()
pop_emb = np.zeros((N_NODES, 1), dtype=np.float32)
pop_emb[O_J:O_J + N_JOBS, 0] = pop
pop_emb[:N_USERS, 0] = 1.0            # user vector = 1 để score = popularity
MODEL_EMB["Popularity"] = pop_emb
MODEL_RESULTS["Popularity"] = _record("Popularity", pop_emb, kind="baseline")
MODEL_RESULTS["Popularity"]["seconds"] = round(time.perf_counter() - t0, 2)
print(f"Popularity    : R@20={MODEL_RESULTS['Popularity']['recall@20']:.4f}")

# ---- baseline 2: Item-KNN (cosine trên ma trận user–job) ----
t0 = time.perf_counter()
Aui = sp.csr_matrix(
    (np.ones(N_TRAIN_UJ, dtype=np.float32), ((uj_tr_dst - O_J), uj_tr_src)),
    shape=(N_JOBS, N_USERS))
_nrm = np.sqrt(np.asarray(Aui.multiply(Aui).sum(1)).ravel())
_nrm[_nrm == 0] = 1.0
Aui = (sp.diags(1.0 / _nrm) @ Aui).tocsr()


def _iknn_scores(users, catalog, pos_of_catalog):
    """Điểm Item-KNN cho `users` trên `catalog` (đã loại job đã tương tác).

    Aui có shape (N_JOBS, N_USERS) — hàng = job, cột = user.
    Công thức: s(u, j) = Σ_{j' ∈ profile(u)} cos(j, j')
    với cos(j, j') = (Aui · Auiᵀ)[j, j'] = (Aui[j] · Aui[j']).
    Vì Aui đã chuẩn hoá hàng về norm 1 nên tích vô hướng chính là cosine.
    """
    sc = np.full((len(users), catalog.size), -1e9, dtype=np.float32)
    for r, u in enumerate(np.asarray(users).tolist()):
        prof = [j for j in SEEN.get(u, []) if pos_of_catalog[j] >= 0]
        if prof:
            # vector đại diện cho profile: tổng các HÀNG job (không phải cột!)
            prof_vec = np.asarray(Aui[prof].sum(0)).ravel()      # (N_USERS,)
            sim = np.asarray(Aui @ prof_vec).ravel()             # (N_JOBS,)
        else:
            sim = np.zeros(N_JOBS, dtype=np.float32)
        sc[r] = sim[catalog]
        idx = [pos_of_catalog[j] for j in SEEN.get(u, []) if pos_of_catalog[j] >= 0]
        if idx:
            sc[r, idx] = -np.inf
    return sc


# (a) tập đầy đủ
_ik_sc = _iknn_scores(EVAL_USERS, CATALOG, CATALOG_POS)
_ik_vec = metrics_from_scores(_ik_sc, EVAL_USERS, EVAL_POS)
MODEL_RESULTS["Item-KNN"] = summarize(_ik_vec, _ik_vec["_top1"])
lo, hi = bootstrap_ci(_ik_vec["recall@20"])
# (b) tập sạch
_ik_sc_c = _iknn_scores(EVAL_USERS_CLEAN, CATALOG, CATALOG_POS)
_ik_vec_c = metrics_from_scores(_ik_sc_c, EVAL_USERS_CLEAN, EVAL_POS_CLEAN)
MODEL_EMB["Item-KNN"] = None   # Item-KNN chấm trực tiếp, không có embedding
MODEL_RESULTS["Item-KNN"].update({
    "recall@20_ci95": [round(lo, 4), round(hi, 4)],
    "clean_recall20": float(np.nanmean(_ik_vec_c["recall@20"])),
    "clean_ndcg20": float(np.nanmean(_ik_vec_c["ndcg@20"])),
    "clean_mrr20": float(np.nanmean(_ik_vec_c["mrr@20"])),
    "clean_recall10": float(np.nanmean(_ik_vec_c["recall@10"])),
    "seconds": round(time.perf_counter() - t0, 2),
})
print(f"Item-KNN      : R@20={MODEL_RESULTS['Item-KNN']['recall@20']:.4f}")

# ---- baseline 3: BPR-MF ----
t0 = time.perf_counter()
E_bpr = train_bpr_mf(dim=DIM, epochs=CFG["gnn_epochs"])
MODEL_EMB["BPR-MF"] = E_bpr
MODEL_RESULTS["BPR-MF"] = _record("BPR-MF", E_bpr, kind="baseline")
MODEL_RESULTS["BPR-MF"]["seconds"] = round(time.perf_counter() - t0, 2)
print(f"BPR-MF        : R@20={MODEL_RESULTS['BPR-MF']['recall@20']:.4f}")

# ---- 3 GNN ----
# Mọi mô hình đều được LAN TRUYỀN LẠI trên toàn đồ thị trước khi chấm điểm
# (`full_forward`) để so sánh công bằng, không ưu tiên mô hình nào.
for _name, _fn in [("LightGCN", lambda: train_lightgcn(DIM, LAYERS, CFG["gnn_epochs"])),
                   ("GraphSAGE", lambda: train_graphsage(DIM, CFG["gnn_epochs"])),
                   ("GAT", lambda: train_gat(DIM, max(1, CFG["gnn_epochs"] // 2)))]:
    t0 = time.perf_counter()
    E = _fn()
    MODEL_EMB[_name] = E
    MODEL_RESULTS[_name] = _record(_name, E)
    MODEL_RESULTS[_name]["seconds"] = round(time.perf_counter() - t0, 2)
    print(f"{_name:13s}: R@20={MODEL_RESULTS[_name]['recall@20']:.4f} "
          f"(sạch {MODEL_RESULTS[_name]['clean_recall20']:.4f}) "
          f"({MODEL_RESULTS[_name]['seconds']:.0f}s)")

# %%
# ============================================================================
# [7d] Bảng tổng hợp 3 tập đánh giá + CI 95%
# ============================================================================
rows = []
for name, r in MODEL_RESULTS.items():
    rows.append(dict(
        mô_hình=name,
        R10=round(r["recall@10"], 4), R20=round(r["recall@20"], 4),
        R20_CI95=r.get("recall@20_ci95"),
        R20_sạch=round(r["clean_recall20"], 4),
        NDCG20=round(r["ndcg@20"], 4),
        NDCG20_sạch=round(r["clean_ndcg20"], 4),
        MRR20=round(r["mrr@20"], 4),
        coverage=round(r["coverage@10"], 4),
        giây=r.get("seconds"),
    ))
for r in rows:
    print(f"{r['mô_hình']:12s} R@10={r['R10']:.4f} R@20={r['R20']:.4f} "
          f"R@20(sạch)={r['R20_sạch']:.4f} NDCG@20={r['NDCG20']:.4f} "
          f"MRR@20={r['MRR20']:.4f} cov={r['coverage']:.4f}")

print("\n=== MỨC PHỒNG DO RÒ RỈ ĐƯỜNG VÒNG (R@20 đầy đủ − R@20 sạch) ===")
for r in rows:
    delta = r["R20"] - r["R20_sạch"]
    print(f"{r['mô_hình']:12s}: {delta:+.4f}  ({100 * delta / max(r['R20_sạch'], 1e-9):+.2f}%)")

print(f"\nCold-start: {COLD_JOBS.size:,} job ({100 * COLD_JOBS.size / N_JOBS:.2f}%) chỉ có test, "
      f"0 cạnh train -> không thể gợi ý được; metric ở trên tính trên catalog "
      f"{CATALOG.size:,} job có ≥1 cạnh train nên ĐÃ loại cold-start khỏi tử số.")
print(f"  3 tập: (a) {N_TEST_UJ:,} cạnh test | (b) {int(IS_CLEAN.sum()):,} cạnh sạch | "
      f"(c) bỏ {COLD_JOBS.size:,} cold-start job")

# %%
# ============================================================================
# [7e] Biểu đồ: hội tụ, so sánh phương pháp, ảnh hưởng số client
# ============================================================================
T7c = time.perf_counter()

# --- (1) đường cong hội tụ FL ---
CONV = run_federated(n_clients=CFG["fl_clients"], rounds=CFG["fl_rounds"],
                     local_epochs=LOCAL_EPOCHS, dim=DIM, layers=LAYERS,
                     algo="fedavg", weighted=True, verbose=True,
                     eval_cb=lambda E, r: {"recall20": evaluate_embeddings(full_forward(E))["recall@20"],
                                           "ndcg20": evaluate_embeddings(full_forward(E))["ndcg@20"]})
FL_E = full_forward(CONV["E"])
FL_METRICS = evaluate_embeddings(FL_E, with_ci=True)
MODEL_EMB["FedAvg"] = CONV["E"]
MODEL_RESULTS["FedAvg"] = dict(FL_METRICS, name="FedAvg", kind="federated",
                               seconds=round(sum(h["round_seconds"] for h in CONV["history"]), 2))
print(f"\nFedAvg (cấu hình chính): R@20={FL_METRICS['recall@20']:.4f} "
      f"CI95={FL_METRICS['recall@20_ci95']}")

# --- (1b) ĐÁNH GIÁ CÔNG BẰNG TRÊN VŨ TRỤ CỦA FL ---
# FL chỉ học từ các job thuộc N client tham gia; job ngoài vũ trụ giữ embedding
# khởi tạo ngẫu nhiên. Chấm trên toàn catalog là bất lợi không công bằng cho FL.
FL_UNIVERSE = job_universe_of_clients(CONV["client_ids"])
CATALOG_FL = np.intersect1d(CATALOG, FL_UNIVERSE)
print(f"\n=== VŨ TRỤ ĐÁNH GIÁ CÔNG BẰNG CHO FL ===")
print(f"Client tham gia       : {CONV['n_shards']:,} / {N_CLIENTS_TOTAL:,}")
print(f"Job thuộc các client  : {FL_UNIVERSE.size:,} / {N_JOBS:,} "
      f"({100 * FL_UNIVERSE.size / N_JOBS:.2f}%)")
print(f"Catalog trong vũ trụ  : {CATALOG_FL.size:,} job")

# mẫu user + positive giới hạn trong vũ trụ FL
_catfl_pos = -np.ones(N_JOBS, dtype=np.int64)
_catfl_pos[CATALOG_FL] = np.arange(CATALOG_FL.size)
_pos_fl = {}
for u, js in POS_ALL.items():
    sel_js = [j for j in js if _catfl_pos[j] >= 0]
    if sel_js:
        _pos_fl[u] = [int(_catfl_pos[j]) for j in sel_js]
_users_fl = np.array(sorted(_pos_fl), dtype=np.int64)
print(f"User có positive trong vũ trụ FL: {_users_fl.size:,}")
FAIR = {}          # luôn khởi tạo để nhánh else không làm biến chưa gán
if _users_fl.size:
    _n_fl = int(min(CFG["eval_users"], _users_fl.size))
    EVAL_USERS_FL = np.sort(np.random.default_rng(42).choice(_users_fl, _n_fl, replace=False))
    EVAL_POS_FL = [np.array(_pos_fl[int(u)], dtype=np.int64) for u in EVAL_USERS_FL]
    MODEL_RESULTS["FedAvg"]["universe_jobs"] = int(FL_UNIVERSE.size)
    MODEL_RESULTS["FedAvg"]["universe_catalog"] = int(CATALOG_FL.size)
    _fl_uni = evaluate_embeddings(FL_E, EVAL_USERS_FL, EVAL_POS_FL,
                                  catalog=CATALOG_FL, with_ci=True)
    MODEL_RESULTS["FedAvg"]["R20_FlUniverse"] = round(_fl_uni["recall@20"], 4)
    MODEL_RESULTS["FedAvg"]["NDCG20_FlUniverse"] = round(_fl_uni["ndcg@20"], 4)
    MODEL_RESULTS["FedAvg"]["MRR20_FlUniverse"] = round(_fl_uni["mrr@20"], 4)
    MODEL_RESULTS["FedAvg"]["R20_FlUniverse_ci95"] = _fl_uni["recall@20_ci95"]
    print(f"  FedAvg trên vũ trụ FL: R@20={_fl_uni['recall@20']:.4f} "
          f"NDCG@20={_fl_uni['ndcg@20']:.4f} CI={_fl_uni['recall@20_ci95']}")

    # so sánh công bằng: chấm MỌI mô hình trên cùng vũ trụ này
    print("\n=== SO SÁNH CÔNG BẰNG TRÊN CÙNG VŨ TRỤ (mọi hệ cùng catalog + cùng mẫu user) ===")
    FAIR = {"FedAvg": _fl_uni}
    for _nm, _emb in MODEL_EMB.items():
        if _nm == "FedAvg" or _emb is None:
            continue
        _r = evaluate_embeddings(_emb, EVAL_USERS_FL, EVAL_POS_FL, catalog=CATALOG_FL)
        FAIR[_nm] = _r
        print(f"  {_nm:12s}: R@20={_r['recall@20']:.4f} NDCG@20={_r['ndcg@20']:.4f}")
        MODEL_RESULTS[_nm]["R20_FlUniverse"] = round(_r["recall@20"], 4)
    # Item-KNN trên vũ trụ FL
    _ik_fl = _iknn_scores(EVAL_USERS_FL, CATALOG_FL, _catfl_pos)
    _ik_v_fl = metrics_from_scores(_ik_fl, EVAL_USERS_FL, EVAL_POS_FL, catalog=CATALOG_FL)
    FAIR["Item-KNN"] = summarize(_ik_v_fl)
    MODEL_RESULTS["Item-KNN"]["R20_FlUniverse"] = round(FAIR["Item-KNN"]["recall@20"], 4)
    print(f"  {'Item-KNN':12s}: R@20={FAIR['Item-KNN']['recall@20']:.4f}")
    _fl_gap = FAIR["FedAvg"]["recall@20"] - max(
        v["recall@20"] for k, v in FAIR.items() if k != "FedAvg")
    print(f"\n  FedAvg so với hệ tốt nhất cùng vũ trụ: {_fl_gap:+.4f}")
else:
    FAIR = {}
    print("Không đủ user trong vũ trụ FL để đánh giá công bằng.")

fig, axes = plt.subplots(1, 4, figsize=(20, 4.6))
xs = [h["round"] for h in CONV["history"]]
axes[0].plot(xs, [h["recall20"] for h in CONV["history"]], "o-", label="Recall@20")
axes[0].plot(xs, [h["ndcg20"] for h in CONV["history"]], "s--", label="NDCG@20")
axes[0].set_xlabel("vòng FL"); axes[0].set_ylabel("metric"); axes[0].legend(); axes[0].grid(alpha=.3)
axes[0].set_title(f"Hội tụ FedAvg ({CFG['fl_clients']} client, {CFG['fl_rounds']} vòng)")

# --- (2a) so sánh trên catalog ĐẦY ĐỦ (mọi hệ thấy khác nhau — xem [7.5]) ---
names = [r["mô_hình"] for r in rows] + ["FedAvg"]
vals = [r["R20"] for r in rows] + [FL_METRICS["recall@20"]]
lo_err = [r["R20"] - (r["R20_CI95"][0] if r["R20_CI95"] else r["R20"]) for r in rows] + \
         [FL_METRICS["recall@20"] - FL_METRICS["recall@20_ci95"][0]]
hi_err = [(r["R20_CI95"][1] - r["R20"] if r["R20_CI95"] else 0.0) for r in rows] + \
         [FL_METRICS["recall@20_ci95"][1] - FL_METRICS["recall@20"]]
axes[1].barh(names[::-1], vals[::-1], xerr=[lo_err[::-1], hi_err[::-1]],
             color="#4f81bd", error_kw=dict(ecolor="k", lw=1, capsize=3))
axes[1].set_xlabel("Recall@20 (CI 95%)")
axes[1].set_title("Catalog ĐẦY ĐỦ\n(FedAvg chỉ thấy ~11% job — KHÔNG so trực tiếp)", fontsize=10)
axes[1].grid(alpha=.3, axis="x")

# --- (2b) so sánh CÔNG BẰNG trên cùng vũ trụ FL ---
if FAIR:
    fair_names = list(FAIR)
    fair_vals = [FAIR[k]["recall@20"] for k in fair_names]
    fair_lo = [FAIR[k]["recall@20"] - (FAIR[k]["recall@20_ci95"][0]
                                       if FAIR[k].get("recall@20_ci95") else FAIR[k]["recall@20"])
               for k in fair_names]
    fair_hi = [(FAIR[k]["recall@20_ci95"][1] - FAIR[k]["recall@20"]
                if FAIR[k].get("recall@20_ci95") else 0.0) for k in fair_names]
    axes[2].barh(fair_names[::-1], fair_vals[::-1],
                 xerr=[fair_lo[::-1], fair_hi[::-1]],
                 color="#9bbb59", error_kw=dict(ecolor="k", lw=1, capsize=3))
    axes[2].set_xlabel("Recall@20")
    axes[2].set_title(f"CÙNG vũ trụ FL ({CATALOG_FL.size:,} job)\n"
                      f"— so sánh công bằng", fontsize=10)
    axes[2].grid(alpha=.3, axis="x")
else:
    axes[2].text(.5, .5, "không đủ user", ha="center", va="center"); axes[2].axis("off")

# --- (3) ảnh hưởng số client ---
if SWEEP:
    rows_nc = sorted([r for r in SWEEP if r["dim"] == 32 and r["layers"] == 2
                      and r["local_epochs"] == 1], key=lambda r: r["n_clients"])
    axes[3].plot([r["n_clients"] for r in rows_nc], [r["recall20"] for r in rows_nc],
                 "o-", label="Recall@20")
    axes[3].plot([r["n_clients"] for r in rows_nc], [r["ndcg20"] for r in rows_nc],
                 "s--", label="NDCG@20")
    axes[3].set_xlabel("số client"); axes[3].legend(); axes[3].grid(alpha=.3)
    axes[3].set_title("Ảnh hưởng số client")
else:
    axes[3].text(.5, .5, "bỏ qua (SCALE=tiny)", ha="center", va="center")
    axes[3].axis("off")

fig.suptitle("Đánh giá — CareerBuilder, mẫu user cố định, CI 95% bootstrap 1.000 lần",
             fontsize=13)
fig.tight_layout()
cmp_path = os.path.join(FIG, "F03_so_sanh_va_hoi_tu.png")
fig.savefig(cmp_path, dpi=160, bbox_inches="tight")
plt.close(fig)
print("Đã lưu hình:", cmp_path)
mark("[7] Đánh giá", T7, f"{len(MODEL_RESULTS)} hệ")
