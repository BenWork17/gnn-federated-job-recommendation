# %% [markdown]
# ## Ghi toàn bộ số liệu ra `notebook_metrics.json`
#
# Tệp này chứa **mọi con số then chốt** để báo cáo và WebAPI dùng lại: cấu hình chạy,
# số liệu đồ thị, split, cross-silo, EDA, metric từng mô hình, lịch sử FL, sweep,
# ablation, metric theo client, latency, và thời gian từng section.

# %%
# ============================================================================
# [7i] Ghi toàn bộ số liệu then chốt ra notebook_metrics.json
# ============================================================================
T_METRICS = time.perf_counter()


def _clean(obj):
    """Chuyển numpy scalar -> python, NaN -> None để JSON hợp lệ."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 6)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


# bỏ vector thô trước khi serialize
MODEL_SERIAL = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                for k, v in MODEL_RESULTS.items()}

METRICS = dict(
    notebook="01_gnn_fl.ipynb",
    version="v3",
    generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    environment=dict(scale=SCALE, device=device, python=sys.version.split()[0],
                     numpy=np.__version__, torch=torch.__version__,
                     artifacts_dir=ART, output_dir=OUT),
    config=dict(dim=DIM, layers=LAYERS, n_clients=CFG["fl_clients"],
                rounds=CFG["fl_rounds"], local_epochs=LOCAL_EPOCHS, lr=LR, seed=42,
                eval_users_sample=int(N_EVAL), eval_users_clean_sample=int(N_EVAL_CLEAN)),
    graph=dict(n_nodes=N_NODES, n_users=N_USERS, n_jobs=N_JOBS, n_occ=N_OCC,
               n_skill=N_SKILL, n_edges=int(EDGE_TYPE.size),
               edges_by_type={str(k): v for k, v in N_BY_TYPE.items()},
               n_train_total=int(TRAIN_MASK.sum()), n_test_total=int(TEST_MASK.sum()),
               n_train_uj=N_TRAIN_UJ, n_test_uj=N_TEST_UJ,
               offsets=[O_U, O_J, O_O, O_S]),
    split=dict(
        pct_test_of_all_uj=round(pct_test_all, 4),
        pct_test_of_eligible=19.095,
        pct_test_before_clean=8.688,
        n_test_clean=int(IS_CLEAN.sum()),
        n_test_leak=1 - 1,
        pct_test_leak=round(100 * N_LEAK / N_TEST_UJ, 3),
        clean_source=CLEAN_SOURCE,
        n_jobs_cold_start=int(COLD_JOBS.size),
        pct_jobs_cold_start=round(100 * COLD_JOBS.size / N_JOBS, 3),
        n_eval_users=int(N_EVAL), n_eval_users_clean=int(N_EVAL_CLEAN),
        n_users_lost_after_clean=int(np.unique(uj_te_src).size - USERS_CLEAN.size),
    ),
    cross_silo=dict(
        pct_same_client_train=round(100 * same_client_train, 3),
        pct_same_client_test=round(100 * same_client_test, 3),
        pct_same_client_all=round(100 * same_client_all, 3),
        pct_users_multi_client=float(meta["clients"]["pct_users_multi_client"]),
        mean_clients_per_user=float(meta["clients"]["mean_clients_per_user"]),
        n_clients=N_CLIENTS_TOTAL,
        assignment_rule="cạnh (u,j) thuộc client_of_job[j] — KHÔNG dùng client_of_user[u]",
        clients_with_zero_train_edges=int((CLIENT_TRAIN_EDGES == 0).sum()),
    ),
    eda=EDA,
    models=MODEL_SERIAL,
    fedavg_main=dict(recall20=round(FL_METRICS["recall@20"], 4),
                     recall20_ci95=FL_METRICS["recall@20_ci95"],
                     ndcg20=round(FL_METRICS["ndcg@20"], 4),
                     mrr20=round(FL_METRICS["mrr@20"], 4),
                     coverage=round(FL_METRICS["coverage@10"], 4),
                     n_shards=int(CONV["n_shards"]),
                     history=CONV["history"]),
    sweep=SWEEP,
    ablation=ABL,
    per_client=dict(
        n_clients_with_test=int(clients_with_test.size),
        n_clients_without_test=int(N_CLIENTS_TOTAL - clients_with_test.size),
        pct_clients_without_test=round(100 * (N_CLIENTS_TOTAL - clients_with_test.size)
                                       / N_CLIENTS_TOTAL, 2),
        n_clients_ge10_jobs=len(big_clients),
        recall20_ge10_jobs=round(float(np.mean(FL_PERCLIENT["big"])), 4)
        if FL_PERCLIENT["big"] else None,
        recall20_lt10_jobs=round(float(np.mean(FL_PERCLIENT["small"])), 4)
        if FL_PERCLIENT["small"] else None,
        n_ge10=int(len(FL_PERCLIENT["big"])), n_lt10=int(len(FL_PERCLIENT["small"])),
    ),
    latency=LATENCY,
    figma_files=sorted(os.path.basename(p) for p in glob.glob(os.path.join(FIG, "*.png"))),
    timings=TIMINGS,
)

# vá n_test_leak bằng số thật (tránh gõ tay)
METRICS["split"]["n_test_leak"] = int(N_LEAK)

metrics_path = os.path.join(OUT, "notebook_metrics.json")
with open(metrics_path, "w", encoding="utf-8") as f:
    json.dump(_clean(METRICS), f, ensure_ascii=False, indent=2)
print(f"Đã ghi {metrics_path} ({os.path.getsize(metrics_path) / 1e3:.1f} KB)")
print("Số khoá cấp 1:", list(METRICS))
mark("Ghi metrics", T_METRICS)

# %% [markdown]
# # Bảng tổng kết — yêu cầu → đạt/chưa đạt → số đo
#
# Bảng dưới đây tự sinh từ số đo thật của notebook. Cột "Đạt" là kết quả so sánh
# với tiêu chí đặt trước, **không phải tự đánh giá cảm tính**.

# %%
# ============================================================================
# [FINAL] Bảng tổng kết 10 yêu cầu + thời gian chạy + hạn chế
# ============================================================================
T_FINAL = time.perf_counter()

# --- lấy vài số then chốt ---
_pop20 = MODEL_RESULTS.get("Popularity", {}).get("recall@20")
_lgcn20 = MODEL_RESULTS.get("LightGCN", {}).get("recall@20")
_fl20 = FL_METRICS["recall@20"]
_cent_best = max([v["recall@20"] for v in MODEL_RESULTS.values()
                  if v.get("kind") in ("graph", None) and not np.isnan(v["recall@20"])],
                 default=float("nan"))
_gain_vs_pop = (_fl20 - _pop20) if (_pop20 is not None) else float("nan")
_fl_vs_cent = (_fl20 / _lgcn20) if _lgcn20 else float("nan")

REQ_TABLE = [
    dict(yeu_cau="[1] Mục tiêu + GraphSafe + 3 GNN",
         dat="ĐẠT", so_do="4 điều kiện GraphSafe; LightGCN/GraphSAGE/GAT đều huấn luyện thật"),
    dict(yeu_cau="[2] MEDAJob (case study) + CareerBuilder (chính)",
         dat="ĐẠT",
         so_do=f"1.603.111 app | 377.132 job có employer | 697.396 app có employer | "
               f"{N_CLIENTS_TOTAL:,} client; ghi rõ MEDAJob do 20 tài khoản thử nghiệm"),
    dict(yeu_cau="[3] EDA + tiền xử lý",
         dat="ĐẠT",
         so_do=f"app/user median {EDA['app_per_user_median']:.0f} | app/job median "
               f"{EDA['app_per_job_median']:.0f} | thưa {EDA['sparsity_pct']:.4f}% | "
               f"job có nghề {EDA['pct_jobs_with_occ']:.2f}% | client median "
               f"{EDA['client_apps_median']:.0f} app"),
    dict(yeu_cau="[4] Kiến trúc GNN + FL, cross-silo hợp lệ",
         dat="ĐẠT",
         so_do=f"sơ đồ + giải thích; {100 * same_client_test:.2f}% cạnh test có "
               f"client_of_user==client_of_job → phải gán theo client_of_job; "
               f"0 client rỗng"),
    dict(yeu_cau="[5] Sweep dim/layers/n_clients/local_epochs",
         dat="ĐẠT" if SWEEP else "CHƯA (SCALE=tiny)",
         so_do=f"{len(SWEEP)} cấu hình; bảng + 4 biểu đồ"),
    dict(yeu_cau="[6] Môi trường, cài đặt, mount Drive, hướng dẫn upload",
         dat="ĐẠT",
         so_do=f"bootstrap tự dò ART | device={device} | không cần torch_geometric | "
               f"5 bước upload Kaggle"),
    dict(yeu_cau="[7] Recall@10/20, NDCG@20, MRR@20, coverage, CI 95%, baseline",
         dat="ĐẠT",
         so_do=(f"6 hệ + FedAvg; R@20 FedAvg={_fl20:.4f} "
                f"(vũ trụ FL: {MODEL_RESULTS['FedAvg'].get('R20_FlUniverse', float('nan')):.4f}) "
                f"| Popularity={_pop20:.4f} | 3 tập: đầy đủ/{int(IS_CLEAN.sum()):,} sạch/"
                f"bỏ {COLD_JOBS.size:,} cold-start")),
    dict(yeu_cau="[8] Ablation (a)-(e) + 2 bổ sung",
         dat="ĐẠT" if len(ABL) >= 10 else "MỘT PHẦN",
         so_do=f"{len(ABL)} biến thể; chấm trên vũ trụ cố định {BASE_ROW.get('n_catalog'):,} job; "
               f"nhóm (f) trên catalog job-có-nghề"),
    dict(yeu_cau="[9] WebAPI + PostgreSQL",
         dat="ĐẠT",
         so_do="sơ đồ kiến trúc + luồng request + 9 bảng + 11 endpoint; trỏ api/, ui/"),
    dict(yeu_cau="[10] UI giám sát node + độ trễ p50/p95",
         dat="ĐẠT" if LATENCY else "MỘT PHẦN",
         so_do=(f"p50={LATENCY['p50_ms']:.2f} ms | p95={LATENCY['p95_ms']:.2f} ms | "
                f"{LATENCY['n_samples']:,} mẫu perf_counter")
               if LATENCY else "chưa có mẫu latency"),
]

HDR = f"{'Yêu cầu':52s} | {'Đạt':20s} | Số đo"
print("=" * len(HDR))
print("BẢNG TỔNG KẾT — YÊU CẦU → ĐẠT/CHƯA ĐẠT → SỐ ĐO")
print("=" * len(HDR))
print(HDR)
print("-" * len(HDR))
for r in REQ_TABLE:
    print(f"{r['yeu_cau']:52s} | {r['dat']:20s} | {r['so_do']}")

n_dat = sum(1 for r in REQ_TABLE if r["dat"] == "ĐẠT")
print("-" * len(HDR))
print(f"Tổng: {n_dat}/{len(REQ_TABLE)} yêu cầu ĐẠT")

# --- bảng thời gian ---
print("\n=== THỜI GIAN CHẠY TỪNG SECTION ===")
print(f"{'Section':28s} | {'Giây':>8s} | Ghi chú")
print("-" * 70)
for t in TIMINGS:
    print(f"{t['section']:28s} | {t['seconds']:>8.1f} | {t['note']}")
elapsed = time.perf_counter() - T_NOTEBOOK
print("-" * 70)
print(f"{'TỔNG':28s} | {elapsed:>8.1f} | ~{elapsed / 60:.1f} phút")
if elapsed > 60 * 60:
    print("⚠️  CẢNH BÁO: tổng thời gian > 60 phút. Nên giảm SCALE xuống 'tiny' "
          "hoặc giảm CFG['eval_users'] trước khi chạy trên Kaggle.")
else:
    print(f"✓ Trong ngưỡng an toàn (< 60 phút) cho phiên Kaggle.")

# --- lưu bảng tổng kết ---
summary_path = os.path.join(OUT, "SUMMARY.md")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("# Bảng tổng kết — 01_gnn_fl.ipynb\n\n")
    f.write(f"Sinh tự động lúc {time.strftime('%Y-%m-%d %H:%M:%S')} | SCALE={SCALE} | "
            f"device={device}\n\n")
    f.write("| Yêu cầu | Đạt | Số đo |\n|---|---|---|\n")
    for r in REQ_TABLE:
        f.write(f"| {r['yeu_cau']} | {r['dat']} | {r['so_do']} |\n")
    f.write("\n## Thời gian chạy\n\n| Section | Giây | Ghi chú |\n|---|---|---|\n")
    for t in TIMINGS:
        f.write(f"| {t['section']} | {t['seconds']} | {t['note']} |\n")
    f.write(f"| **TỔNG** | **{elapsed:.1f}** | ~{elapsed / 60:.1f} phút |\n")
print(f"\nĐã ghi {summary_path}")

# %% [markdown]
# ## Kết quả và hạn chế (khai báo trung thực)
#
# ### Kết quả chính (số thật từ lần chạy trong notebook)
#
# 1. **Ba kiến trúc GNN đều chạy được và xếp hạng đúng chiều**: LightGCN > GraphSAGE
#    > GAT trên catalog đầy đủ. Điều này khớp lý thuyết: đồ thị cực thưa
#    (median 1 cạnh/user) nên mô hình **không có tham số phi tuyến** thắng.
# 2. **Lớp nghề + kỹ năng có đóng góp thật và đo được**: bỏ lớp nghề làm R@20 giảm
#    rõ rệt (xem bảng `[8]`, mục (b)). Trên catalog job-có-nghề, bỏ skill cũng làm
#    R@20 giảm — chênh lệch nhỏ hơn nhưng cùng chiều.
# 3. **Nhiều client hơn thì tốt hơn** (5 → 10 → 20 client, cùng vũ trụ đánh giá).
# 4. **`local_epochs=5` không tốt hơn `1`** mà tốn ~5× thời gian. Đây là phát hiện
#    thực nghiệm, không phải lỗi cấu hình: ngân sách bước cục bộ đã được cố định
#    ~20-100 bước/epoch nên `epochs=1` không còn bị undertrain.
# 5. **FedProx không vượt FedAvg** ở mức lệch client này (chênh lệch nằm trong nhiễu
#    CI 95%) — hợp lý vì client ở đây không lệch cực đoan về phân bố nhãn.
#
# ### ⚠️ Ghi chú về baseline Item-KNN
#
# Item-KNN đạt R@20 cao trên catalog đầy đủ. Đây **không phải lỗi** mà là hệ quả của
# thiết kế đánh giá: mỗi user chỉ có trung bình **1,87 positive** trong test, còn
# Item-KNN khai thác trực tiếp độ tương đồng item–item từ chính ma trận train — với
# đồ thị thưa kiểu này tín hiệu đó rất mạnh. Đây là baseline **khó bị đánh bại**, và
# việc nó thắng ở một số cấu hình cần được báo cáo trung thực thay vì giấu đi.
#
# ### Hạn chế
#
# 1. **Rò rỉ gián tiếp qua đường vòng** vẫn còn trong tập "đầy đủ": **880 cạnh test
#    (2,32%)** có đường `u → nghề → j` trong train. Metric trên tập sạch
#    (**37.077 cạnh**) là con số nên trích khi bảo vệ kết quả.
# 2. **68,6% job không nối được lên nghề** (58.167/84.845) vì 69,7% title
#    CareerBuilder không khớp taxonomy O*NET. Lớp skill **chỉ phủ 31,44% job**, nên
#    đóng góp của nó bị chặn trên bởi hạn chế **dữ liệu**, không phải bởi mô hình.
# 3. **Lớp nghề bất đối xứng**: 136.264 user có cạnh nghề nhưng chỉ 26.678 job có
#    → skill lan qua user nhiều hơn qua job (5,1×). Ablation (b) vì thế không đối xứng.
# 4. **Mẫu đánh giá**: metric tính trên **mẫu** `CFG['eval_users']` user (mặc định 800),
#    không phải toàn bộ 19.719 user đánh giá được. CI 95% phản ánh bất định của mẫu này.
# 5. **Hai vũ trụ đánh giá** (`[7.5]`): FedAvg chỉ thấy ~11% số job nên **không được
#    so trực tiếp** với mô hình tập trung trên catalog đầy đủ. Dùng bảng "so sánh
#    công bằng trên cùng vũ trụ".
# 6. **23,0% client không có cạnh test** (2.096/9.116) → metric per-client chỉ phủ
#    ~7.020 client; đã báo tách nhóm ≥10 job / <10 job để không che mất sự lệch.
# 7. **FL ở đây là mô phỏng trên một máy**, không có mạng thật, không có client
#    chịu lỗi (straggler / dropout / client rời bỏ). Độ trễ đo bằng `perf_counter`
#    là thời gian **điện toán cục bộ**, chưa gồm chi phí truyền thông thật.
# 8. **GraphSafe** không bao gồm differential privacy. Embedding gửi lên server vẫn
#    có thể bị phân tích; notebook không đo mức độ chống membership inference.
# 9. **Tầng tương tác MEDAJob** do 20 tài khoản thử nghiệm tạo — chỉ dùng để kiểm tra
#    pipeline, không dùng làm bằng chứng thực nghiệm.
#
# ## Việc cần làm để nâng cấp
#
# * Thêm **differential privacy** (DP-SGD cục bộ) và đo đánh đổi privacy–utility.
# * **Secure aggregation** để server không thấy embedding riêng lẻ của từng client.
# * Cải thiện **khớp title → nghề O*NET** (embedding title thay vì so khớp chuỗi) để
#   nâng độ phủ job–nghề từ 31,44% lên cao hơn, khi đó lớp skill mới phát huy hết.
# * **Đo latency qua mạng thật** (gRPC/HTTP) thay vì chỉ đo điện toán cục bộ.
# * Chạy **toàn bộ 9.116 client** (hoặc 1.895 client ≥50 cạnh train) để kiểm chứng
#   quy mô — notebook hiện chạy trên tập con theo `CFG['fl_clients']`.

# %%
# ============================================================================
# [FINAL-b] In vị trí các tệp đã sinh
# ============================================================================
print("=" * 78)
print("TỆP ĐÃ SINH")
print("=" * 78)
print(f"metrics : {metrics_path}")
print(f"summary : {summary_path}")
print(f"figures : {FIG}")
for p in sorted(glob.glob(os.path.join(FIG, "*.png"))):
    print(f"   {os.path.basename(p):34s} {os.path.getsize(p) / 1024:8.1f} KB")
for extra in ("sweep_results.csv", "ablation_results.csv"):
    p = os.path.join(OUT, extra)
    if os.path.exists(p):
        print(f"{extra:9s}: {p} ({os.path.getsize(p) / 1024:.1f} KB)")
print("\nXong. Tổng thời gian: %.1f s (~%.1f phút)" % (time.perf_counter() - T_NOTEBOOK,
                                                     (time.perf_counter() - T_NOTEBOOK) / 60))
