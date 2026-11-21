# %% [markdown]
# # [8] Ablation
#
# Năm phép ablation theo yêu cầu, cộng **hai phép bổ sung** phát sinh từ hạn chế dữ
# liệu đã khai báo ở `[2]` và `[4]`.
#
# | # | Biến thể | Cắt gì | Câu hỏi |
# |---|---|---|---|
# | **(a)** | Bỏ lớp **skill** | Không đưa nút kỹ năng vào đồ thị con của client | Kỹ năng có đóng góp? |
# | **(b)** | Bỏ lớp **occupation** | Không đưa nút nghề (và do đó cả kỹ năng) vào | Nghề + kỹ năng đóng góp bao nhiêu? |
# | **(c)** | Ngưỡng client **5 / 10 / 20** | Đổi số client tham gia | Ít client hơn có tốt hơn? |
# | **(d)** | **FedAvg vs FedProx** | Đổi cách tổng hợp | FedProx (phạt `mu`) có giúp với client lệch? |
# | **(e)** | `local_epochs` **1 vs 5** | Số epoch cục bộ | Client học kỹ hơn có lợi? |
# | **(f)** | *Bổ sung*: **chỉ xét job có nghề** | Cố định catalog = 26.678 job có nghề, so base vs bỏ skill | Đóng góp của skill khi nó **phủ 100% job** — "trần trên" của lớp skill |
# | **(g)** | *Bổ sung*: FedAvg **weighted vs unweighted** | Cách tính trọng số | Client lớn (4.320 cạnh) có lấn át client nhỏ (5 cạnh)? |
#
# ## 8.0 QUY TẮC ĐÁNH GIÁ — đọc trước khi đọc bảng
#
# Mọi biến thể FL ở đây chỉ có **20 client** (mặc định), tức chỉ sở hữu **~11% số job**
# của đồ thị. Những job ngoài vũ trụ đó **giữ nguyên embedding khởi tạo ngẫu nhiên**
# vì chưa client nào học chúng. Nếu chấm điểm trên **toàn bộ 82.876 job catalog**, mọi
# biến thể đều bị kéo về gần 0 và **không phân biệt được** — con số sẽ vô nghĩa.
#
# > **Vì vậy** mỗi biến thể được chấm trên **vũ trụ job của chính các client tham gia**
# > (`catalog_u = CATALOG ∩ job của N client đó`), với mẫu user có positive nằm trong
# > vũ trụ này. Cột `n_catalog` trong bảng ghi rõ số job dùng để chấm. Chỉ các dòng
# > **cùng `n_catalog`** mới được so trực tiếp với nhau.
#
# Nhóm **(f)** đặc biệt: **cả ba** biến thể (f1)/(f2)/(f3) chấm trên **cùng một catalog
# job-có-nghề**, nên chênh lệch chỉ do lớp skill/occupation — đây là phép đo sạch.
#
# ## 8.1 Vì sao (b) kỳ vọng **bất đối xứng**
#
# Lớp nghề **dày ở phía user, thưa ở phía job**: **136.264 user** có cạnh nghề trong
# train, nhưng chỉ **26.678 job** có (gấp **5,1 lần**). Vì vậy đường lan truyền kỹ
# năng chủ yếu đi qua user (`u → nghề → skill`). Bỏ lớp nghề sẽ mất thông tin **phía
# user nhiều hơn phía job** — kết quả ablation cần được đọc theo hướng đó.
#
# ## 8.2 Vì sao (f) là ablation mạnh
#
# 68,6% job không nối được lên nghề (xem `[2.3]`). Nếu **chỉ giữ 26.678 job có nghề**,
# số cạnh user–job giảm mạnh nhưng lớp skill **phủ 100% job**. So sánh (a)/(b)/(f) cho
# biết: thiếu skill là do **dữ liệu nghèo liên kết**, hay do **mô hình không dùng được
# skill**? Đây là câu hỏi phản biện quan trọng nhất về lớp skill.

# %%
# ============================================================================
# [8b] Chạy 5 ablation bắt buộc + 2 ablation bổ sung
# ============================================================================
T8 = time.perf_counter()
ABL = []
BASE_CFG = dict(n_clients=CFG["abl_clients"], rounds=CFG["abl_rounds"],
                local_epochs=LOCAL_EPOCHS, dim=DIM, layers=LAYERS,
                algo="fedavg", weighted=True)
# Vũ trụ đánh giá CỐ ĐỊNH cho toàn bộ section [8]: job của `abl_clients` client lớn nhất.
# Dùng chung một vũ trụ cho mọi biến thể thì chênh lệch R@20 mới phản ánh đúng
# tác động của biến thể, không lẫn việc đổi tập ứng viên.
FIXED_UNIVERSE_CIDS = select_clients(CFG["abl_clients"])
print(f"Vũ trụ đánh giá CỐ ĐỊNH của section [8] = job của "
      f"{len(FIXED_UNIVERSE_CIDS)} client lớn nhất")


def _abl(name, note, fixed_cids=None, **kw):
    """Chạy 1 biến thể FL và ghi kết quả.

    `fixed_cids`: nếu truyền vào, dùng CÙNG một vũ trụ job (của các client này) cho
    mọi biến thể trong nhóm — bắt buộc khi so sánh các biến thể có số client khác
    nhau (nhóm c), vì mỗi số client sở hữu một tập job khác nhau.

    Điểm quan trọng: metric tính trên **vũ trụ job của chính các client tham gia**
    chứ không phải toàn catalog 82.876 job. Lý do: các client này chỉ sở hữu ~11%
    số job; chấm trên toàn catalog thì phần lớn ứng viên giữ embedding khởi tạo
    ngẫu nhiên -> mọi biến thể đều ~0 và không phân biệt được.
    """
    cfg = dict(BASE_CFG)
    cfg.update({k: v for k, v in kw.items() if k in cfg})
    extra = {k: v for k, v in kw.items() if k not in cfg}
    t0 = time.perf_counter()
    res = run_federated(verbose=False, **cfg, **extra)
    universe = job_universe_of_clients(
        res["client_ids"] if fixed_cids is None else fixed_cids)
    catalog_u = np.intersect1d(CATALOG, universe)
    pos_u = -np.ones(N_JOBS, dtype=np.int64)
    pos_u[catalog_u] = np.arange(catalog_u.size)
    pos_map_u = {}
    for u, js in POS_ALL.items():
        sel_js = [j for j in js if pos_u[j] >= 0]
        if sel_js:
            pos_map_u[u] = [int(pos_u[j]) for j in sel_js]
    users_u = np.array(sorted(pos_map_u), dtype=np.int64)
    dt = time.perf_counter() - t0
    if users_u.size == 0:
        row = dict(biến_thể=name, ghi_chú=note + " [vũ trụ rỗng]",
                   R10=np.nan, R20=np.nan, NDCG20=np.nan, MRR20=np.nan,
                   coverage=np.nan, giây=round(dt, 1), n_shard=res["n_shards"],
                   n_catalog=int(catalog_u.size))
        ABL.append(row)
        print(f"  {name:34s} (vũ trụ rỗng)")
        return row, res

    n_u = int(min(CFG["eval_users"], users_u.size))
    ev_u = np.sort(np.random.default_rng(42).choice(users_u, n_u, replace=False))
    evp_u = [np.array(pos_map_u[int(u)], dtype=np.int64) for u in ev_u]
    m = evaluate_embeddings(full_forward(res["E"]), ev_u, evp_u, catalog=catalog_u)
    row = dict(biến_thể=name, ghi_chú=note,
               R10=round(m["recall@10"], 4), R20=round(m["recall@20"], 4),
               NDCG20=round(m["ndcg@20"], 4), MRR20=round(m["mrr@20"], 4),
               coverage=round(m["coverage@10"], 4), giây=round(dt, 1),
               n_shard=res["n_shards"], n_catalog=int(catalog_u.size),
               universe="cố định" if fixed_cids is not None else "theo biến thể")
    ABL.append(row)
    print(f"  {name:34s} R@20={row['R20']:.4f} NDCG@20={row['NDCG20']:.4f} "
          f"cov={row['coverage']:.4f} | {res['n_shards']} client, "
          f"{catalog_u.size:,} job ({dt:.0f}s)")
    return row, res


# --- mốc so sánh: cấu hình đầy đủ ---
BASE_ROW, BASE_RES = _abl("(base) đầy đủ", "nghề + kỹ năng, FedAvg weighted",
                          fixed_cids=FIXED_UNIVERSE_CIDS)

# --- (a) bỏ lớp skill ---
ROW_A, _ = _abl("(a) bỏ lớp skill", "không đưa nút kỹ năng vào đồ thị con",
                fixed_cids=FIXED_UNIVERSE_CIDS, include_skill=False)

# --- (b) bỏ lớp occupation ---
ROW_B, _ = _abl("(b) bỏ lớp occupation", "không đưa nút nghề (kéo theo cả kỹ năng)",
                fixed_cids=FIXED_UNIVERSE_CIDS, include_occ=False, include_skill=False)

# --- (c) ngưỡng client 5 / 10 / 20 ---
# Dùng CÙNG một vũ trụ đánh giá = job của 20 client lớn nhất, để mọi mức
# n_clients được chấm trên đúng một catalog (nếu không, mỗi mức có catalog
# khác nhau và chênh lệch không so sánh được).
print(f"\n[nhóm (c)] chấm trên vũ trụ cố định của {len(FIXED_UNIVERSE_CIDS)} client")
ROW_C = {}
for ncl in (5, 10, CFG["abl_clients"]):
    if ncl > CFG["abl_clients"]:
        continue
    ROW_C[ncl], _ = _abl(f"(c) n_clients={ncl}", f"{ncl} client lớn nhất",
                         fixed_cids=FIXED_UNIVERSE_CIDS, n_clients=ncl)

# --- (d) FedAvg vs FedProx ---
ROW_D_AVG, _ = _abl("(d) FedAvg", "trung bình có trọng số",
                    fixed_cids=FIXED_UNIVERSE_CIDS, algo="fedavg")
ROW_D_PROX, _ = _abl("(d) FedProx (mu=0.01)", "thêm phạt ||E - E_global||^2",
                     fixed_cids=FIXED_UNIVERSE_CIDS, algo="fedprox", mu=0.01)

# --- (e) local_epochs 1 vs 5 ---
ROW_E1, _ = _abl("(e) local_epochs=1", "1 epoch cục bộ/vòng",
                 fixed_cids=FIXED_UNIVERSE_CIDS, local_epochs=1)
ROW_E5, _ = _abl("(e) local_epochs=5", "5 epoch cục bộ/vòng",
                 fixed_cids=FIXED_UNIVERSE_CIDS, local_epochs=5)

# --- (g) weighted vs unweighted FedAvg ---
ROW_G_W, _ = _abl("(g) FedAvg weighted", "trọng số = số cạnh user-job",
                  fixed_cids=FIXED_UNIVERSE_CIDS, weighted=True)
ROW_G_U, _ = _abl("(g) FedAvg unweighted", "mọi client trọng số 1",
                  fixed_cids=FIXED_UNIVERSE_CIDS, weighted=False)
print("\nĐã chạy xong 5 ablation bắt buộc + 2 bổ sung.")

# %%
# ============================================================================
# [8c] Ablation (f) — chỉ giữ job CÓ NGHỀ: đo lớp skill khi nó phủ 100% job
# ============================================================================
# VẤN ĐỀ CẦN TRÁNH: nếu chỉ so "base trên catalog đầy đủ" với "biến thể trên
# catalog job-có-nghề" thì kết quả lẫn hai hiệu ứng (đổi dữ liệu + đổi catalog),
# không kết luận được gì.
#
# CÁCH LÀM ĐÚNG: cố định **một** catalog = job có nghề ∩ vũ trụ client, rồi so
# (f1) base với (f2) bỏ skill TRÊN CÙNG catalog đó. Chênh lệch khi đó chỉ còn do
# lớp skill, và vì skill phủ 100% job nên đây là "trần trên" đóng góp của skill.
jobs_with_occ = np.unique(EDGE_INDEX[0][EDGE_TYPE == ET_JOB_OCC] - O_J)
print(f"Job có nghề: {jobs_with_occ.size:,}/{N_JOBS:,} "
      f"({100 * jobs_with_occ.size / N_JOBS:.2f}%) — 68,6% job còn lại không có nghề.")

# Catalog (f) = job có nghề ∩ job thuộc vũ trụ client đã cố định
_universe_fixed = job_universe_of_clients(FIXED_UNIVERSE_CIDS)
CATALOG_OCC = np.intersect1d(np.intersect1d(CATALOG, jobs_with_occ), _universe_fixed)
CATALOG_POS_OCC = -np.ones(N_JOBS, dtype=np.int64)
CATALOG_POS_OCC[CATALOG_OCC] = np.arange(CATALOG_OCC.size)
_pos_occ = {}
for u, js in POS_ALL.items():
    sel = [int(CATALOG_POS_OCC[j]) for j in js if CATALOG_POS_OCC[j] >= 0]
    if sel:
        _pos_occ[u] = sel
_users_occ = np.array(sorted(_pos_occ), dtype=np.int64)
_n_occ = int(min(CFG["eval_users"], _users_occ.size))
EVAL_USERS_OCC = np.sort(np.random.default_rng(42).choice(_users_occ, _n_occ, replace=False))
EVAL_POS_OCC = [np.array(_pos_occ[int(u)], dtype=np.int64) for u in EVAL_USERS_OCC]
print(f"Catalog (f) job-có-nghề ∩ vũ trụ client: {CATALOG_OCC.size:,} job | "
      f"mẫu đánh giá: {EVAL_USERS_OCC.size:,} user")

# So 3 cấu hình trên CÙNG catalog này: base, bỏ skill, bỏ occupation
print("\n=== (f) TRÊN CÙNG CATALOG JOB-CÓ-NGHỀ — chỉ khác lớp skill/occupation ===")
F_ROWS = []
for _label, _kw in [("(f1) base: nghề + kỹ năng", {}),
                    ("(f2) bỏ skill", dict(include_skill=False)),
                    ("(f3) bỏ occupation+skill", dict(include_occ=False, include_skill=False))]:
    _t_f = time.perf_counter()
    _res = run_federated(verbose=False, **BASE_CFG, **_kw)
    _m = evaluate_embeddings(full_forward(_res["E"]), EVAL_USERS_OCC,
                             EVAL_POS_OCC, catalog=CATALOG_OCC)
    _row = dict(biến_thể=_label,
                ghi_chú=f"cùng catalog {CATALOG_OCC.size:,} job có nghề",
                R10=round(_m["recall@10"], 4), R20=round(_m["recall@20"], 4),
                NDCG20=round(_m["ndcg@20"], 4), MRR20=round(_m["mrr@20"], 4),
                coverage=round(_m["coverage@10"], 4),
                giây=round(time.perf_counter() - _t_f, 1),
                n_shard=_res["n_shards"], n_catalog=int(CATALOG_OCC.size),
                universe="cố định")
    ABL.append(_row)
    F_ROWS.append(_row)
    print(f"  {_label:28s} R@20={_row['R20']:.4f} NDCG@20={_row['NDCG20']:.4f} "
          f"MRR@20={_row['MRR20']:.4f}")

_f_base, _f_noskill, _f_noocc = F_ROWS
print(f"\n  Đóng góp của lớp SKILL khi skill phủ 100% job: "
      f"ΔR@20 = {_f_base['R20'] - _f_noskill['R20']:+.4f} "
      f"({100 * (_f_base['R20'] - _f_noskill['R20']) / max(_f_noskill['R20'], 1e-9):+.1f}%)")
print(f"  Đóng góp của cả NGHỀ + SKILL: "
      f"ΔR@20 = {_f_base['R20'] - _f_noocc['R20']:+.4f} "
      f"({100 * (_f_base['R20'] - _f_noocc['R20']) / max(_f_noocc['R20'], 1e-9):+.1f}%)")
print(f"  (f) trên catalog job-có-nghề: R@20={_f_base['R20']:.4f} NDCG@20={_f_base['NDCG20']:.4f}")
print("  -> Vì cả (f1)/(f2)/(f3) chấm trên CÙNG catalog job-có-nghề, chênh lệch ở trên "
      "thuần tuý do lớp skill/occupation, không lẫn hiệu ứng đổi catalog.")

# %%
# ============================================================================
# [8d] Bảng ablation + biểu đồ
# ============================================================================
import csv as _csv2

cols_abl = ["biến_thể", "ghi_chú", "R10", "R20", "NDCG20", "MRR20", "coverage",
            "giây", "n_shard", "n_catalog"]
print("=== BẢNG ABLATION ===")
print(" | ".join(f"{c:>24s}" if c in ("biến_thể", "ghi_chú") else f"{c:>9s}" for c in cols_abl))
for r in ABL:
    print(" | ".join(f"{str(r[c]):>24s}" if c in ("biến_thể", "ghi_chú") else f"{r[c]:>9}"
                    for c in cols_abl))
with open(os.path.join(OUT, "ablation_results.csv"), "w", newline="", encoding="utf-8") as f:
    w = _csv2.DictWriter(f, fieldnames=cols_abl)
    w.writeheader()
    w.writerows([{k: r.get(k) for k in cols_abl} for r in ABL])

# --- bảng "delta so với base" — chỉ so trong CÙNG nhóm catalog ---
base_r20 = BASE_ROW["R20"]
print(f"\n=== DELTA SO VỚI MỐC (base, catalog {BASE_ROW.get('n_catalog'):,} job) ===")
for r in ABL:
    if r is BASE_ROW:
        continue
    if r.get("n_catalog") != BASE_ROW.get("n_catalog"):
        continue    # khác catalog -> không so trực tiếp
    if isinstance(r["R20"], float) and not np.isnan(r["R20"]):
        print(f"{r['biến_thể']:34s} ΔR@20 = {r['R20'] - base_r20:+.4f} "
              f"({100 * (r['R20'] - base_r20) / max(base_r20, 1e-9):+.1f}%)")
print(f"\n(Các biến thể (f) dùng catalog khác ({CATALOG_OCC.size:,} job có nghề) nên "
      f"được so riêng trong nhóm (f1)↔(f2)↔(f3) ở trên.)")

# --- biểu đồ ablation: 4 ô gồm cả nhóm (f) ---
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
axes = axes.ravel()
mandatory = [r for r in ABL if str(r["biến_thể"]).startswith(("(base)", "(a)", "(b)"))]
panels = [
    ("(a) bỏ skill / (b) bỏ occupation", mandatory),
    ("(c) số client", sorted([r for r in ABL if str(r["biến_thể"]).startswith("(c)")],
                             key=lambda r: r["biến_thể"])),
    ("(d) FedAvg vs FedProx, (e) local_epochs, (g) weighted",
     [r for r in ABL if str(r["biến_thể"]).startswith(("(d)", "(e)", "(g)"))]),
    ("(f) trên catalog job-có-nghề", F_ROWS),
]
for ax, (title, subset) in zip(axes, panels):
    if not subset:
        ax.text(.5, .5, "không có dữ liệu", ha="center", va="center"); ax.axis("off")
        continue
    labels = [str(r["biến_thể"]).replace("(", "").replace(")", "") for r in subset]
    vals = [r["R20"] for r in subset]
    ax.barh(labels[::-1], vals[::-1], color="#9bbb59")
    ax.set_xlabel("Recall@20")
    ax.set_title(title, fontsize=10)
    ax.grid(alpha=.3, axis="x")
fig.suptitle("Ablation — FedAvg trên CareerBuilder (cùng catalog trong từng nhóm)", fontsize=13)
fig.tight_layout()
abl_path = os.path.join(FIG, "F04_ablation.png")
fig.savefig(abl_path, dpi=160, bbox_inches="tight")
plt.close(fig)
print("\nĐã lưu hình:", abl_path)
mark("[8] Ablation", T8, f"{len(ABL)} biến thể")

# %% [markdown]
# # [9] WebAPI + PostgreSQL
#
# ## 9.1 Kiến trúc
#
# ```
#   ┌──────────────┐   HTTP/JSON    ┌───────────────────┐   SQL    ┌──────────────┐
#   │  UI (tĩnh)   │ ─────────────► │  FastAPI (api/)   │ ───────► │ PostgreSQL   │
#   │  ui/index.html│ ◄──────────── │  main.py           │ ◄─────── │  dss_jobs    │
#   │  + WebSocket │   WS /ws/...   │  db.py (Pg/InMem)  │          │  9 bảng      │
#   └──────────────┘                │  fl_sim.py (runner)│          └──────────────┘
#                                   │  artifacts.py      │
#                                   └───────────────────┘
#                                          │ đọc
#                                          ▼
#                                   artifacts/v3/graph.npz
# ```
#
# | Thành phần | Tệp | Vai trò |
# |---|---|---|
# | API server | `api/main.py` | 11 endpoint REST + 2 WebSocket, CORS |
# | Truy cập DB | `api/db.py` | `PgStore` (PostgreSQL) và `InMemoryStore` (dự phòng, **cùng interface**) |
# | Nạp dữ liệu | `api/load_to_pg.py` | `COPY ... FROM STDIN` từ `artifacts/v3` vào PostgreSQL |
# | DDL | `api/schema.sql` | 9 bảng + index |
# | Đọc artifacts | `api/artifacts.py` | Nạp `graph.npz` / `clients.json`, fallback dữ liệu demo |
# | Runner FL | `api/fl_sim.py` | Mô phỏng vòng FL chạy nền, **đo latency thật** bằng `perf_counter` |
# | UI | `ui/index.html` | Bảng client + biểu đồ metric + latency theo thời gian thực |
#
# ## 9.2 Sơ đồ luồng một request
#
# ```
# POST /api/recommend  {user_id: 47, k: 10}
#    │
#    ├─► main.recommend()            kiểm tra tham số (k ≤ 100)
#    ├─► store.get_user_edges(47)    SELECT job_id FROM apps WHERE user_id=47      ── SQL
#    ├─► artifacts.embedding_lookup  lấy vector user + ứng viên từ graph.npz
#    ├─► tính dot-product, loại job đã tương tác
#    └─► 200 {user_id, items:[{job_id, title, employer, score, matched_skills}]}
# ```
#
# ```
# POST /api/train/start {n_clients, rounds, algorithm, local_epochs}
#    │
#    ├─► main.train_start()          sinh run_id (UUID)
#    ├─► store.create_run(run_id)    INSERT INTO train_runs                        ── SQL
#    ├─► fl_sim.FLSimulator.start()  tạo asyncio.Task chạy nền
#    └─► 200 {run_id, status:"running"}
#
#        (nền) mỗi vòng r:
#          ├─ với từng client:  t0 = perf_counter(); mô phỏng cập nhật; latency = ...
#          ├─ store.add_round_metric(...)  INSERT INTO round_metrics               ── SQL
#          ├─ store.add_latency(...)       INSERT INTO node_latency                ── SQL
#          └─ broadcast  ──►  WebSocket /ws/train/{run_id}  ──►  UI cập nhật biểu đồ
# ```
#
# ## 9.3 Bảng dữ liệu (9 bảng)
#
# | Bảng | Nội dung |
# |---|---|
# | `users` | `user_id`, `state`, `degree`, `years_exp` |
# | `jobs` | `job_id`, `title`, `employer`, `occupation`, `city`, `state` |
# | `apps` | `(user_id, job_id, applied_at)` — tương tác gốc |
# | `employers` | `client_id`, `name`, `n_apps`, `n_users`, `n_jobs` |
# | `job_skills` / `user_skills` | kỹ năng suy qua nghề (ghi rõ trong `meta.json`) |
# | `train_runs` | một lần chạy FL (có `stopped_at_round` cho t7) |
# | `round_metrics` | metric từng vòng |
# | `node_latency` | **độ trễ thật từng client từng vòng** |
#
# ## 9.4 Chạy thử nhanh (không cần PostgreSQL)
#
# ```bash
# python api/main.py --dry-run --port 8000     # InMemoryStore, dữ liệu demo
# # hoặc đầy đủ:
# createdb dss_jobs && psql -d dss_jobs -f api/schema.sql
# python api/load_to_pg.py --dsn "postgresql://postgres:postgres@127.0.0.1:5432/dss_jobs"
# python -m uvicorn api.main:app --port 8000
# ```
#
# ## 9.5 Danh sách endpoint
#
# | Phương thức | Đường dẫn | Mô tả |
# |---|---|---|
# | GET | `/health` | Trạng thái server + DB + artifacts |
# | GET | `/api/clients` | Danh sách client (phân trang, sắp xếp) |
# | GET | `/api/clients/{client_id}` | Chi tiết một client |
# | GET | `/api/graph/summary` | Số nút/cạnh/client |
# | POST | `/api/recommend` | Gợi ý top-K cho một user |
# | POST | `/api/train/start` | Bắt đầu một lần chạy FL |
# | POST | `/api/train/stop/{run_id}` | Dừng giữa chừng |
# | GET | `/api/train/status/{run_id}` | Trạng thái + metric + latency |
# | GET | `/api/train/runs` | Danh sách các lần chạy |
# | WS | `/ws/latency` | Stream độ trễ thời gian thực |
# | WS | `/ws/train/{run_id}` | Stream metric từng vòng |

# %%
# ============================================================================
# [9b] Kiểm tra tĩnh sự tồn tại của api/ và ui/ (không cần chạy server)
# ============================================================================
T9 = time.perf_counter()
PROJ = os.path.dirname(os.path.dirname(ART)) if ART.endswith(os.path.join("artifacts", "v3")) else None
API_DIR = os.path.join(PROJ, "api") if PROJ else None
UI_DIR = os.path.join(PROJ, "ui") if PROJ else None
print(f"Thư mục dự án: {PROJ}")
for label, p in [("api/", API_DIR), ("ui/", UI_DIR)]:
    if p and os.path.isdir(p):
        files = sorted(os.listdir(p))[:12]
        print(f"  {label:5s} có: {len(os.listdir(p))} mục -> {files}")
    else:
        print(f"  {label:5s} KHÔNG có trong dataset artifacts "
              f"(chỉ cần khi chạy WebAPI; notebook không phụ thuộc)")
print("\nXem chi tiết kiến trúc và cách chạy trong api/README.md và ui/README.md.")
mark("[9] WebAPI + PostgreSQL", T9)

# %% [markdown]
# # [10] UI giám sát node + độ trễ
#
# ## 10.1 Màn hình UI (`ui/index.html`)
#
# Bố cục 4 vùng:
#
# ```
# ┌───────────────────────────────────────────────────────────────────────┐
# │  GNN + FL Job Recommender        [Live] [Demo]   db:●  artifacts:●    │
# ├──────────────────────┬────────────────────────────────────────────────┤
# │  CLIENT (nhà tuyển dụng)          │  BIỂU ĐỒ                                 │
# │  ┌──────────────────────────────┐ │  ┌───────────────────────────────────┐  │
# │  │ #   employer     app  job  ● │ │  │ Recall@20 / NDCG@20 theo vòng      │  │
# │  │ 0   randstad    4745  603 ●  │ │  │   ╱╲      ╱╲                       │  │
# │  │ 1   allmed…     1567  219 ●  │ │  │  ╱  ╲____╱  ╲___                   │  │
# │  │ ...                          │ │  └───────────────────────────────────┘  │
# │  └──────────────────────────────┘ │  ┌───────────────────────────────────┐  │
# │  [Bắt đầu train] [Dừng]           │  │ LATENCY p50 / p95 (ms) theo vòng   │  │
# │  n_clients: [50] rounds: [20]     │  │  ▁▂▃▅▆▇█▆▅▃                        │  │
# │  algorithm: [FedAvg ▾]            │  └───────────────────────────────────┘  │
# │  local_epochs: [1]                │  ┌───────────────────────────────────┐  │
# │                                   │  │ Bảng node: client, latency_ms,     │  │
# │                                   │  │ bytes_up/down, trạng thái          │  │
# │                                   │  └───────────────────────────────────┘  │
# └──────────────────────┴────────────────────────────────────────────────┘
# ```
#
# **Chức năng chính:**
#
# 1. **Bảng client** — 9.116 nhà tuyển dụng, sắp xếp theo `n_apps`, tìm kiếm, phân trang.
#    Mỗi dòng là một **node** tham gia FL.
# 2. **Bắt đầu / dừng huấn luyện** — gọi `POST /api/train/start` / `stop/{run_id}`.
# 3. **Biểu đồ metric** — cập nhật realtime qua WebSocket `/ws/train/{run_id}`.
# 4. **Biểu đồ latency + bảng node** — từ `/ws/latency`, mỗi phần tử là một
#    `(client_id, round, latency_ms, bytes_up, bytes_down)`.
# 5. **Chế độ demo** — nếu backend không có thật, UI tự chuyển sang dữ liệu demo và
#    ghi rõ badge **DEMO** để người xem không nhầm với số thật.
#
# Ảnh chụp màn hình có sẵn ở `ui/screenshots/` (13 ảnh: idle, running, done, demo,
# mobile, mất/kết nối lại WebSocket, 200 client, cảnh báo vượt cap).
#
# ## 10.2 Cách đo độ trễ THẬT — `time.perf_counter()`
#
# Độ trễ **không phải số giả**. Code trong `api/fl_sim.py`:
#
# ```python
# t0 = time.perf_counter()          # đồng hồ đơn điệu, độ phân giải ns
# # ... client dựng "cập nhật cục bộ" (đồ thị con + 1 epoch + serialize seed) ...
# latency_ms = (time.perf_counter() - t0) * 1000.0
# ```
#
# Vì sao `perf_counter` chứ không `time.time()`:
#
# | | `time.time()` | `time.perf_counter()` |
# |---|---|---|
# | Gốc | epoch Unix (1970) | không xác định, chỉ dùng để đo khoảng |
# | Bị ảnh hưởng bởi chỉnh đồng hồ hệ thống | **có** | **không** |
# | Độ phân giải | ~1 µs (tuỳ hệ) | cao nhất có thể (~ns) |
# | Dùng để đo khoảng thời gian | không nên | **đúng mục đích** |
#
# Mỗi client mỗi vòng có một mẫu latency → với 50 client × 20 vòng = **1.000 mẫu**.
#
# ## 10.3 p50 / p95 — vì sao dùng phân vị chứ không dùng trung bình
#
# Phân bố latency **lệch phải nặng** (đuôi dài: client lớn giữ 4.320 cạnh chậm hơn
# client 5 cạnh hàng chục lần). Trung bình bị kéo bởi vài outlier, không phản ánh
# trải nghiệm điển hình.
#
# | Chỉ số | Ý nghĩa | Cách đọc |
# |---|---|---|
# | **p50** (median) | 50% số lần đo nhanh hơn giá trị này | Độ trễ **điển hình** |
# | **p95** | 95% số lần đo nhanh hơn; 5% chậm hơn | **Độ trễ xấu** mà người dùng vẫn gặp |
# | `mean` | trung bình số học | Bị outlier kéo — **không** dùng làm SLA |
# | `max` | lần chậm nhất | Chẩn đoán, không phải SLA |
#
# Công thức: `p95 = np.percentile(latencies, 95)` (nội suy tuyến tính).
#
# ## [10b] Đo latency thật ngay trong notebook
#
# Phần dưới đo **thời gian thật** của một vòng FL (đã có ở `[7e]`: `CONV`), rồi báo
# p50 / p95 / mean / max, tách theo nhóm client lớn và nhỏ.

# %%
T10 = time.perf_counter()
lat = CONV["latencies_ms"] if "CONV" in dir() and CONV.get("latencies_ms") is not None else np.array([])
if lat.size:
    lat = np.asarray(lat, dtype=np.float64)
    p50, p95 = float(np.percentile(lat, 50)), float(np.percentile(lat, 95))
    print("=== ĐỘ TRỄ THẬT (perf_counter) — 1 vòng FL, mỗi client 1 mẫu ===")
    print(f"Số mẫu        : {lat.size:,}")
    print(f"p50           : {p50:.2f} ms   ← độ trễ ĐIỂN HÌNH")
    print(f"p95           : {p95:.2f} ms   ← độ trễ XẤU (5% chậm hơn)")
    print(f"mean          : {lat.mean():.2f} ms  ← bị outlier kéo, KHÔNG dùng làm SLA")
    print(f"max           : {lat.max():.2f} ms")
    print(f"min           : {lat.min():.2f} ms")
    print(f"p95/p50       : {p95 / max(p50, 1e-9):.2f}×  (>{3:.0f}× = đuôi dài rõ rệt)")

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    ax[0].hist(lat, bins=min(40, max(5, lat.size // 5)), color="#8064a2")
    ax[0].axvline(p50, color="g", ls="--", label=f"p50 = {p50:.1f} ms")
    ax[0].axvline(p95, color="r", ls="--", label=f"p95 = {p95:.1f} ms")
    ax[0].set_xlabel("độ trễ (ms)"); ax[0].set_ylabel("số mẫu")
    ax[0].set_title("Phân bố độ trễ client (đo thật)"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[1].plot(range(1, len(lat) + 1), lat, lw=.8, color="#4f81bd")
    ax[1].set_xlabel("lần đo"); ax[1].set_ylabel("ms")
    ax[1].set_title("Độ trễ theo thời gian"); ax[1].grid(alpha=.3)
    fig.suptitle("Độ trễ đo bằng time.perf_counter() — không phải số giả", fontsize=13)
    fig.tight_layout()
    lat_path = os.path.join(FIG, "F05_do_tre_p50_p95.png")
    fig.savefig(lat_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("Đã lưu hình:", lat_path)

    LATENCY = dict(n_samples=int(lat.size), p50_ms=round(p50, 3), p95_ms=round(p95, 3),
                   mean_ms=round(float(lat.mean()), 3), max_ms=round(float(lat.max()), 3),
                   min_ms=round(float(lat.min()), 3), p95_over_p50=round(p95 / max(p50, 1e-9), 2))
else:
    print("Không có mẫu latency (CONV chưa chạy).")
    LATENCY = {}
mark("[10] UI + độ trễ", T10)
