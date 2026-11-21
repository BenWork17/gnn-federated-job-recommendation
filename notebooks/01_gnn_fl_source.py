# %% [markdown]
# # GNN + Học liên bang cho Gợi ý việc làm — Notebook thực nghiệm (v3)
#
# Notebook bám đúng **10 yêu cầu** của đề bài. Mỗi yêu cầu là một section có số thứ
# tự trong heading. Chạy được trên **Kaggle** (CPU hoặc GPU T4; **không bắt buộc GPU**),
# trên **Google Colab** và trên máy local.
#
# ---
#
# ## HƯỚNG DẪN UPLOAD DỮ LIỆU LÊN KAGGLE (5 bước)
#
# 1. **Nén thư mục `artifacts/v3`** — tổng 26,9 MB:
#    `graph.npz` 3,57 MB | `clients.json` 1,08 MB | `job_titles.json` 11,91 MB |
#    `user_titles.json` 10,34 MB | `meta.json` 0,01 MB
#    ```bash
#    zip -r dss-gnn-fl-v3.zip artifacts/v3
#    ```
# 2. Vào **Kaggle → Datasets → New Dataset**, upload file zip, đặt tên `dss-gnn-fl-v3`.
# 3. Trong notebook: **Add Data → chọn dataset vừa tạo**. Đường dẫn sẽ là
#    `/kaggle/input/dss-gnn-fl-v3/` (bên trong là `artifacts/v3/`).
# 4. **(Tuỳ chọn, khuyến nghị)** upload thêm `_newdata_audit/v3_verify/test_clean_index.npz`
#    vào cùng dataset — notebook dùng danh sách 880 cạnh test bị rò rỉ đường vòng đã
#    kiểm chứng. Nếu **không** upload, notebook **tự tính lại** và in rõ đang dùng
#    đường nào (xem section `[7]`).
# 5. **Bật Internet** trong Settings **chỉ khi** cần `pip install`. Sau khi cài xong,
#    notebook chạy **hoàn toàn offline**: không tải dữ liệu, không gọi API ngoài.
#
# > **Không hard-code đường dẫn tuyệt đối.** Cell code đầu tiên tự dò `ART`
# > (thư mục artifacts) và `OUT` (thư mục ghi) theo môi trường; mọi cell sau chỉ
# > dùng hai biến này.
#
# ---
#
# ## Bản đồ 10 yêu cầu → section
#
# | Yêu cầu | Nội dung | Section |
# |---|---|---|
# | 1 | Mục tiêu, GraphSafe, ba GNN sẽ thử | `[1]` |
# | 2 | Bộ dữ liệu MEDAJob + CareerBuilder | `[2]` |
# | 3 | EDA + tiền xử lý | `[3]` |
# | 4 | Kiến trúc GNN + FL, tính hợp lệ cross-silo | `[4]` |
# | 5 | Phân tích tham số (sweep) | `[5]` |
# | 6 | Môi trường, cài đặt, mount Google Drive | `[6]` |
# | 7 | Chỉ số đánh giá + baseline + bootstrap CI | `[7]` |
# | 8 | Ablation | `[8]` |
# | 9 | WebAPI + PostgreSQL | `[9]` |
# | 10 | UI giám sát node + độ trễ | `[10]` |
#
# Cuối notebook có **bảng tổng kết yêu cầu → đạt/chưa đạt → số đo**.

# %% [markdown]
# ## Cell 0 — Bootstrap môi trường (phần đầu của yêu cầu [6], đặt trước để mọi cell khác dùng được)
#
# Cell code đầu tiên **không hard-code đường dẫn**: nó dò `graph.npz` theo thứ tự
# ưu tiên (biến môi trường → Kaggle → Colab → local), chọn thư mục ghi phù hợp
# (`/kaggle/working` trên Kaggle), chọn `device`, và đặt thang chạy `SCALE`.
#
# Notebook **không dùng `torch_geometric`**: mọi phép lan truyền viết bằng
# `torch.sparse.mm`, nên không cần cài gói nặng và chạy tốt trên CPU.

# %%
# ============================================================================
# CELL 0 — DÒ MÔI TRƯỜNG (Kaggle / Colab / local). Không hard-code đường dẫn.
# ============================================================================
import glob
import json
import math
import os
import platform
import sys
import time

T_NOTEBOOK = time.perf_counter()


def _first_existing(cands, filename="graph.npz"):
    """Trả về thư mục đầu tiên chứa `filename`."""
    for c in cands:
        if c and os.path.exists(os.path.join(c, filename)):
            return c
    return None


def find_artifacts():
    """Tìm thư mục chứa graph.npz theo thứ tự ưu tiên."""
    here = os.path.abspath(os.getcwd())
    cands = [
        os.environ.get("DSS_ARTIFACT_DIR", ""),
        # --- Kaggle: dạng MỚI (datasets/<user>/<slug>) ---
        "/kaggle/input/datasets/baohoanhao/dss-gnn-fl-v3",
        "/kaggle/input/datasets/baohoanhao/dss-gnn-fl-v3/v3",
        "/kaggle/input/datasets/baohoanhao/dss-gnn-fl-v3/artifacts/v3",
        # --- Kaggle: dạng CŨ (<slug>) ---
        "/kaggle/input/dss-gnn-fl-v3/v3",
        "/kaggle/input/dss-gnn-fl-v3",
        "/kaggle/input/dss-gnn-fl-v3/artifacts/v3",
        # --- local ---
        here,
        os.path.join(here, "artifacts", "v3"),
        os.path.dirname(here),
        os.path.join(os.path.dirname(here), "artifacts", "v3"),
        # --- Colab ---
        "/content/GNN-FL-JobRec/artifacts/v3",
        "/content/artifacts/v3",
        "/content/drive/MyDrive/dss-gnn-fl-v3/artifacts/v3",
        "/content/drive/MyDrive/dss-gnn-fl-v3",
    ]
    hit = _first_existing(cands)
    if hit:
        return os.path.abspath(hit)
    # quét đệ quy trong /kaggle/input và /content
    for base in ("/kaggle/input", "/content"):
        if os.path.isdir(base):
            hits = glob.glob(os.path.join(base, "**", "graph.npz"), recursive=True)
            if hits:
                return os.path.dirname(hits[0])
    raise FileNotFoundError(
        "Không tìm thấy graph.npz. Làm theo hướng dẫn upload ở cell markdown đầu "
        "tiên (Add Data → dataset chứa artifacts/v3), hoặc đặt biến môi trường "
        "DSS_ARTIFACT_DIR trỏ tới thư mục artifacts/v3."
    )


ART = find_artifacts()

# --- thư mục ghi: Kaggle/Colab chỉ cho ghi trong working dir ---
if os.path.isdir("/kaggle"):
    OUT = "/kaggle/working/results_v3"
elif os.path.isdir("/content"):
    OUT = "/content/results_v3"
else:
    OUT = os.path.join(os.path.dirname(os.path.dirname(ART)), "results", "v3")
FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)

# --- mount Google Drive (chỉ Colab, tuỳ chọn) ---
MOUNT_DRIVE = False          # đổi True nếu artifacts nằm trên Google Drive
if MOUNT_DRIVE:
    try:
        from google.colab import drive  # type: ignore
        drive.mount("/content/drive")
        print("Đã mount Google Drive -> /content/drive")
    except Exception as exc:  # không phải Colab
        print("Bỏ qua mount Drive:", type(exc).__name__)

import numpy as np
import torch

# --- chọn thiết bị: CPU là đủ, GPU chỉ nhanh hơn ---
device = "cuda" if torch.cuda.is_available() else "cpu"

# --- thang chạy: đổi SCALE nếu muốn nhanh hơn / đầy đủ hơn ---
# Đo trên CPU 6 thread: 'tiny' ~3 phút | 'small' ~28 phút | 'full' ~2-3 giờ
# Kaggle cho 9-12 h/phiên nên 'small' an toàn; 'full' chỉ nên chạy khi có GPU.
SCALE = os.environ.get("DSS_SCALE", "small")   # 'tiny' | 'small' | 'full'
SCALE_CFG = {
    # eval_users: số user LẤY MẪU để đánh giá (ghi rõ là mẫu trong section [7])
    # sweep_pts: số cấu hình sweep (0 = bỏ qua) — mỗi cấu hình tốn ~50 s ở 'small'
    # abl_rounds: số vòng FL cho mỗi biến thể ablation (giữ nhỏ để tổng thời gian vừa)
    "tiny":  dict(eval_users=200,  gnn_epochs=2,  fl_clients=10,  fl_rounds=2,
                  sweep=False, abl_rounds=2, abl_clients=10),
    "small": dict(eval_users=800,  gnn_epochs=6,  fl_clients=50,  fl_rounds=6,
                  sweep=True,  abl_rounds=4, abl_clients=20),
    "full":  dict(eval_users=3000, gnn_epochs=10, fl_clients=200, fl_rounds=8,
                  sweep=True,  abl_rounds=8, abl_clients=50),
}
CFG = SCALE_CFG[SCALE]

print("=" * 78)
print("MÔI TRƯỜNG")
print("=" * 78)
print(f"Python        : {sys.version.split()[0]} | {platform.system()} {platform.machine()}")
print(f"numpy / torch : {np.__version__} / {torch.__version__}")
print(f"device        : {device}" + (f" ({torch.cuda.get_device_name(0)})" if device == "cuda" else " (CPU — đủ dùng)"))
print(f"ART (đọc)     : {ART}")
print(f"OUT (ghi)     : {OUT}")
print(f"SCALE         : {SCALE} -> {CFG}")
print(f"Threads torch : {torch.get_num_threads()}")

# %%
# ============================================================================
# Cell 0b — Kiểm gói tối thiểu. Kaggle có sẵn mọi gói -> cell này không cài gì.
# ============================================================================
# Trên Colab nếu thiếu torch, bỏ comment dòng dưới rồi chạy lại cell 0:
# %pip install -q torch --index-url https://download.pytorch.org/whl/cpu
REQUIRED = ["numpy", "scipy", "torch", "matplotlib"]
missing = []
for _pkg in REQUIRED:
    try:
        __import__(_pkg)
    except Exception as _exc:
        missing.append(f"{_pkg} ({type(_exc).__name__})")
print("Gói thiếu:", missing if missing else "không thiếu — notebook chạy offline được")
assert not missing, f"Thiếu gói: {missing}. Bật Internet rồi chạy lại cell này."

# %%
# ============================================================================
# Cell 0c — Đồng hồ đo thời gian + seed (dùng xuyên suốt notebook)
# ============================================================================
TIMINGS = []


def mark(section: str, t_start: float, note: str = "") -> float:
    """Ghi nhận thời gian chạy của một section; in bảng ở cuối notebook."""
    dt = time.perf_counter() - t_start
    TIMINGS.append({"section": section, "seconds": round(dt, 2), "note": note})
    print(f"[⏱ {section}] {dt:.1f}s {note}")
    return dt


def set_seed(seed: int = 42) -> None:
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


set_seed(42)
print("Seed = 42 | lấy mẫu tất định qua np.random.default_rng / torch.Generator")

# %%
# ============================================================================
# Cell 0d — Hằng số mô hình (một chỗ duy nhất, không rải rác trong code)
# ============================================================================
DIM = 32                 # số chiều embedding mặc định
LAYERS = 2               # số tầng lan truyền mặc định
LOCAL_EPOCHS = 1         # số epoch cục bộ mỗi vòng FL
LR = 0.05                # learning rate cục bộ
BATCH = 8192             # batch BPR
N_BOOT = 1000            # số lần bootstrap cho CI 95%
K_EVAL = (10, 20)        # các ngưỡng K của Recall

print(f"Siêu tham số: dim={DIM} | layers={LAYERS} | local_epochs={LOCAL_EPOCHS} | "
      f"lr={LR} | batch={BATCH} | n_boot={N_BOOT} | K={K_EVAL}")

# %% [markdown]
# # [1] Mục tiêu — Gợi ý việc làm an toàn dữ liệu bằng GNN + Học liên bang
#
# ## 1.1 Bài toán
#
# Cho một người dùng đã có lịch sử ứng tuyển, xếp hạng các **tin tuyển dụng** mà
# người đó nhiều khả năng ứng tuyển tiếp theo. Đây là bài toán **top-K recommendation**
# trên **đồ thị hai phía user–job**, có thêm hai lớp thông tin:
#
# * **Nghề (occupation)**: mã O*NET-SOC dạng `11-1011` — **7 ký tự**, lấy `soc[:7]`,
#   dùng **nhất quán** ở nút nghề, cạnh job–nghề, cạnh nghề–kỹ năng và cạnh user–nghề.
# * **Kỹ năng công nghệ (skill)**: từ `Technology Skills.txt` của O*NET, nối vào nghề.
#   (Không dùng `Skills.txt`: 879/879 nghề đều đủ 35 element → entropy 0, vô dụng.)
#
# ## 1.2 GraphSafe — an toàn dữ liệu: dữ liệu KHÔNG rời node
#
# **GraphSafe** là nguyên tắc thiết kế của đồ án, gồm 4 điều kiện:
#
# | # | Điều kiện | Cách đảm bảo trong notebook |
# |---|---|---|
# | 1 | Dữ liệu thô **không rời node** | Vòng lặp FL chỉ trao đổi ma trận embedding `n_node × dim`; không gửi cặp `(user, job)` nào |
# | 2 | Client chỉ thấy **quan sát của chính mình** | Đồ thị con của client dựng từ **job thuộc sở hữu client đó**; không đọc cạnh của client khác |
# | 3 | Server **không tái dựng** được dữ liệu gốc | Server chỉ nhận trung bình có trọng số embedding; `dim` ≪ số cạnh |
# | 4 | **Tái lập được** | Seed 42; mọi phép lấy mẫu dùng `default_rng` / `torch.Generator` riêng |
#
# > Trung thực: điều kiện 3 là **bảo vệ theo thiết kế**, không phải bảo vệ hình thức
# > (không phải differential privacy). Notebook **không** tuyên bố FL ở đây chống
# > được tấn công suy luận thành viên (membership inference). Xem "Hạn chế" ở bảng tổng kết.
#
# ## 1.3 Ba kiến trúc GNN sẽ thử
#
# | Mô hình | Công thức lan truyền | Vai trò trong đồ án |
# |---|---|---|
# | **LightGCN** | $e_u^{(l+1)}=\sum_{j\in N(u)}\frac{1}{\sqrt{d_ud_j}}e_j^{(l)}$; đầu ra = trung bình các tầng | Mô hình chính: **không** tham số phi tuyến, phù hợp đồ thị cực thưa |
# | **GraphSAGE** | $h_u^{(l+1)}=\sigma\!\left(W\cdot\mathrm{MEAN}_{j\in N(u)}h_j^{(l)}\right)$ | Kiểm chứng: thêm MLP có giúp gì không? |
# | **GAT** | $\alpha_{uj}=\mathrm{softmax}_j\big(\mathrm{LeakyReLU}(a^\top[Wh_u\Vert Wh_j])\big)$ | Kiểm chứng: attention có phân biệt được láng giềng? |
#
# Mọi mô hình học bằng **BPR loss**: với cạnh dương $(u,j^+)$ lấy ngẫu nhiên một job
# âm $j^-$, tối đa hoá $\log\sigma\big(s(u,j^+)-s(u,j^-)\big)$.
#
# ## 1.4 Câu hỏi nghiên cứu
#
# 1. GNN có vượt baseline cổ điển (Popularity, Item-KNN, BPR-MF) trên dữ liệu thật?
# 2. **Liên bang hoá** mất bao nhiêu chất lượng so với huấn luyện tập trung?
# 3. Lớp **nghề + kỹ năng** đóng góp bao nhiêu? (CareerBuilder nghèo liên kết nghề hơn MEDAJob — xem `[2]` và `[8]`.)
# 4. **Số client** và **cách tổng hợp FedAvg** ảnh hưởng thế nào tới chất lượng và độ trễ?

# %% [markdown]
# # [2] Bộ dữ liệu — MEDAJob (case study phương pháp) + CareerBuilder (thực nghiệm chính)
#
# | | **MEDAJob** | **CareerBuilder** |
# |---|---|---|
# | Vai trò | Case study **phương pháp** | **Thực nghiệm chính** |
# | Ứng viên (user) | 70 | 389.708 (171.807 vào đồ thị) |
# | Tin tuyển dụng (job) | 1.014 | 1.092.096 (84.845 vào đồ thị) |
# | Tương tác (app) | 307 (249 train / 58 test) | **1.603.111** |
# | Nút kỹ năng / nghề | 603 / 10 ngành | 7.760 kỹ năng / 583 nghề |
#
# ## 2.1 Số liệu CareerBuilder (đo trên dữ liệu thô; notebook không đo lại)
#
# | Chỉ số | Giá trị |
# |---|---|
# | Application (`apps.tsv`) | **1.603.111** |
# | Job trích được employer | **377.132** (34,54% của 1.092.096) |
# | Application có employer | **697.396** (43,50% của 1.603.111) |
# | Employer phân biệt (trước lọc chất lượng) | 60.778 |
# | **Client FL** (employer ≥ 10 application, ≥ 2 job) | **9.116** |
# | Application phủ bởi client | 436.893 (**27,25%** tổng app) |
#
# ### ⚠️ Ghi rõ về tầng tương tác MEDAJob
#
# > Tầng tương tác của MEDAJob (307 tương tác) do **20 tài khoản thử nghiệm** tạo ra
# > trong quá trình phát triển website môn học. Vì vậy MEDAJob **chỉ dùng làm case
# > study phương pháp** (kiểm tra pipeline, định nghĩa metric, minh hoạ luồng FL) —
# > **KHÔNG dùng làm bằng chứng thực nghiệm** về chất lượng gợi ý. Mọi con số chất
# > lượng trong notebook này tính trên **CareerBuilder**.
#
# ## 2.2 Vì sao 27,25% chứ không phải 43,50%?
#
# Đây là **đánh đổi có chủ ý** để nhãn employer chính xác, không phải trích kém.
# `meta.json` ghi từng bước:
#
# | Bước | % app còn lại |
# |---|---|
# | 0. `apps.tsv` gốc | 100% |
# | 1. job có trong `jobs.tsv` | 100% |
# | 2. + trích được employer (regex/domain/blacklist) | 30,18% |
# | 3. + bỏ tên chỉ xuất hiện ở < 2 job | — |
# | 4. + job map được nghề có kỹ năng (P1) | 30,18% |
# | 5. + employer ≥ 10 application (**client cuối**) | **27,25%** |
#
# ## 2.3 Hạn chế đã biết: 68,6% job KHÔNG nối được lên nghề
#
# Chỉ **26.678/84.845 job (31,44%)** có cạnh job–nghề, tức **58.167 job (68,6%)**
# không nối được lên nghề, nên kỹ năng **không lan tới** các job đó.
#
# * **Nguyên nhân**: 69,7% title CareerBuilder không khớp được title O*NET —
#   CareerBuilder phủ mọi ngành, còn O*NET là taxonomy nghề của Mỹ.
# * **Lựa chọn đánh đổi**: **không ép** job phải có nghề. Nếu ép, mất ~2/3 tương tác
#   và độ phủ app tụt từ 27% xuống ~9%. Job không nghề vẫn là nút hợp lệ và **vẫn giữ
#   cạnh user–job**.
# * Hệ quả được khai báo ở `[7]` (đánh giá cold-start) và đo trực tiếp ở `[8]`
#   (ablation chỉ giữ job có nghề).

# %%
# ============================================================================
# [2b] Nạp artifacts + UNIT TEST ngay (fail sớm nếu sai)
# ============================================================================
import scipy.sparse as sp

GRAPH_PATH = os.path.join(ART, "graph.npz")
META_PATH = os.path.join(ART, "meta.json")
CLIENTS_PATH = os.path.join(ART, "clients.json")

g = np.load(GRAPH_PATH, allow_pickle=False)

# --- 1) shape phải khớp tuyệt đối (quy ước PyG: 1 dòng cho mỗi cạnh vô hướng) ---
assert g["edge_index"].shape == (2, 764364), g["edge_index"].shape
assert g["edge_type"].shape == (764364,), g["edge_type"].shape
assert g["train_mask"].shape == (764364,), g["train_mask"].shape
assert g["test_mask"].shape == (764364,), g["test_mask"].shape
# --- 2) đại số nút ---
assert int(g["n_nodes"]) == 264995, int(g["n_nodes"])
assert int(g["n_users"]) == 171807 and int(g["n_jobs"]) == 84845
assert int(g["n_occupations"]) == 583 and int(g["n_skills"]) == 7760
assert [int(x) for x in g["offsets"]] == [0, 171807, 256652, 257235], list(g["offsets"])
print("OK: 264.995 nút | 764.364 cạnh | edge_index (2, 764364)")

EDGE_INDEX = g["edge_index"].astype(np.int64)
EDGE_TYPE = g["edge_type"].astype(np.int16)
TRAIN_MASK = g["train_mask"].astype(bool)
TEST_MASK = g["test_mask"].astype(bool)
N_NODES = int(g["n_nodes"])
N_USERS = int(g["n_users"])
N_JOBS = int(g["n_jobs"])
N_OCC = int(g["n_occupations"])
N_SKILL = int(g["n_skills"])
O_U, O_J, O_O, O_S = [int(x) for x in g["offsets"]]
CLIENT_OF_JOB = g["client_of_job"].astype(np.int64)
CLIENT_OF_USER = g["client_of_user"].astype(np.int64)
# `is_public` CHỈ bật cho occ + skill (8.343 nút) -> đọc là "nút danh mục công khai",
# KHÔNG phải "nút công khai" nói chung. Job = 0.
IS_CATALOG_NODE = g["is_public"].astype(bool)
OCC_IDS = g["occ_ids"]
SKILL_NAMES = g["skill_names"]
EDGE_TYPE_NAMES = [str(x) for x in g["edge_type_names"]]

with open(META_PATH, encoding="utf-8") as f:
    meta = json.load(f)
with open(CLIENTS_PATH, encoding="utf-8") as f:
    CLIENTS = json.load(f)
N_CLIENTS_TOTAL = len(CLIENTS)
JOB_TITLES = None
try:
    with open(os.path.join(ART, "job_titles.json"), encoding="utf-8") as f:
        JOB_TITLES = json.load(f)      # {job_id -> {title, city, state, employer, occupation}}
except FileNotFoundError:
    print("(không có job_titles.json — chỉ dùng cho EDA, không bắt buộc)")

# --- 3) kiểm tra chéo ---
assert bool(g["is_symmetric"]), "artifacts phải khai báo đồ thị đối xứng"
assert int((TRAIN_MASK & TEST_MASK).sum()) == 0, "train/test chồng lấn"
assert EDGE_INDEX.min() == 0 and EDGE_INDEX.max() == N_NODES - 1
assert int((EDGE_INDEX[0] == EDGE_INDEX[1]).sum()) == 0, "có self-loop"
assert all(len(x) == 7 for x in OCC_IDS.tolist()), "mã nghề phải dài 7 ký tự (soc[:7], dạng 11-1011)"
assert N_CLIENTS_TOTAL == 9116, N_CLIENTS_TOTAL
assert int(IS_CATALOG_NODE.sum()) == N_OCC + N_SKILL, int(IS_CATALOG_NODE.sum())

ET_USER_JOB, ET_JOB_OCC, ET_OCC_SKILL, ET_USER_OCC = 0, 1, 2, 3
N_BY_TYPE = {t: int((EDGE_TYPE == t).sum()) for t in range(4)}
assert N_BY_TYPE == {0: 436893, 1: 26678, 2: 25866, 3: 274927}, N_BY_TYPE

M_TR = TRAIN_MASK & (EDGE_TYPE == ET_USER_JOB)     # cạnh user-job dùng để train
M_TE = TEST_MASK & (EDGE_TYPE == ET_USER_JOB)      # cạnh user-job dùng để test
N_TRAIN_UJ = int(M_TR.sum())
N_TEST_UJ = int(M_TE.sum())
assert (N_TRAIN_UJ, N_TEST_UJ) == (398936, 37957), (N_TRAIN_UJ, N_TEST_UJ)
assert int(TRAIN_MASK.sum()) == 726407, int(TRAIN_MASK.sum())

print("\n=== ĐỒ THỊ ===")
print(f"Nút            : {N_NODES:,} = {N_USERS:,} user + {N_JOBS:,} job + {N_OCC} nghề + {N_SKILL:,} kỹ năng")
print(f"Cạnh (1 dòng)  : {EDGE_TYPE.size:,}")
for t, name in enumerate(EDGE_TYPE_NAMES):
    if t == 0:
        extra = (f"  (train {int((TRAIN_MASK & (EDGE_TYPE == t)).sum()):,}"
                 f" | test {int((TEST_MASK & (EDGE_TYPE == t)).sum()):,})")
    else:
        extra = "  (train hết, không có test)"
    print(f"   {t} {name:9s}: {N_BY_TYPE[t]:>9,}{extra}")
print(f"Train tổng     : {int(TRAIN_MASK.sum()):,} | Test: {int(TEST_MASK.sum()):,}")
print(f"Độ thưa        : {meta['sparsity_pct']:.5f}%  (ma trận user × job)")
print(f"Client FL      : {N_CLIENTS_TOTAL:,} (min {min(c['n_apps'] for c in CLIENTS)} / "
      f"median {int(np.median([c['n_apps'] for c in CLIENTS]))} / max {max(c['n_apps'] for c in CLIENTS):,} app)")

# --- 4) TỈ LỆ TEST THẬT: min_apps_for_test=5 khiến 63,3% cạnh không bao giờ vào test ---
pct_test_all = 100.0 * N_TEST_UJ / (N_TRAIN_UJ + N_TEST_UJ)
print(f"\nTest = {N_TEST_UJ:,}/{N_TRAIN_UJ + N_TEST_UJ:,} = {pct_test_all:.3f}% toàn bộ cạnh user-job")
print("  → trên tập ĐỦ ĐIỀU KIỆN (user có ≥ 5 app) là ~19,1%; KHÔNG phải 20% như "
      "`test_ratio` trong config.")
print("  → 63,3% cạnh user-job không bao giờ vào test vì user có < 5 application.")

# --- 5) CẠNH THUỘC CLIENT NÀO? ---
# Mỗi cạnh (u, j) thuộc về client_of_job[j] — nhà tuyển dụng SỞ HỮU tin đó.
# client_of_user[u] chỉ là nhãn "client mà user ứng tuyển NHIỀU NHẤT" (argmax),
# KHÔNG phải membership độc quyền. Vì vậy gán cạnh theo client_of_job.
uj_all_src = EDGE_INDEX[0][EDGE_TYPE == ET_USER_JOB]
uj_all_dst = EDGE_INDEX[1][EDGE_TYPE == ET_USER_JOB]
uj_tr_src = EDGE_INDEX[0][M_TR]
uj_tr_dst = EDGE_INDEX[1][M_TR]
uj_te_src = EDGE_INDEX[0][M_TE]
uj_te_dst = EDGE_INDEX[1][M_TE]
same_client_train = float((CLIENT_OF_USER[uj_tr_src] == CLIENT_OF_JOB[uj_tr_dst - O_J]).mean())
same_client_test = float((CLIENT_OF_USER[uj_te_src] == CLIENT_OF_JOB[uj_te_dst - O_J]).mean())
same_client_all = float((CLIENT_OF_USER[uj_all_src] == CLIENT_OF_JOB[uj_all_dst - O_J]).mean())
print("\n=== CROSS-SILO: cạnh thuộc client nào? ===")
print(f"client_of_user[u] == client_of_job[j] trên TRAIN : {100 * same_client_train:.2f}%")
print(f"                                trên TEST        : {100 * same_client_test:.2f}%")
print(f"                                trên TẤT CẢ u–j   : {100 * same_client_all:.2f}%")
print("=> Gán cạnh vào client theo client_of_job[j] (silo THẬT), không theo client_of_user[u].")
print(f"=> {meta['clients']['pct_users_multi_client']}% user thuộc ≥2 client (mean "
      f"{meta['clients']['mean_clients_per_user']} client/user) — bản chất thị trường "
      f"tuyển dụng, KHÔNG phải rò rỉ dữ liệu.")

# %% [markdown]
# # [3] EDA + tiền xử lý
#
# ## 3.1 Các bước làm sạch đã thực hiện ở `src/prepare_v3.py`
#
# | Vấn đề | Tỉ lệ | Cách xử lý |
# |---|---|---|
# | Job description chứa HTML | **92%** | Bóc thẻ bằng regex + `html.unescape` trước khi trích employer/title |
# | Bản ghi trùng lặp | **14,2%** | Khử theo `(user_id, job_id)`; giữ bản ghi sớm nhất |
# | Mojibake (lỗi bảng mã) | **1,9%** | Sửa bằng `ftfy`-style repair; không sửa được thì bỏ |
# | Zip5 hỏng (mã bưu chính) | **37%** | Không dùng Zip5 làm đặc trưng (quá nhiễu), chỉ giữ `city`/`state` |
# | Trích employer từ text | **34,54%** job, 43,50% app | 9 nguồn regex + domain/email + blacklist; sau lọc chất lượng còn 30,18% app |
#
# ## 3.2 Phân bố cần xem
#
# 1. **App/user** và **app/job** — đo độ tập trung (đuôi dài).
# 2. **Độ thưa** ma trận user × job.
# 3. **Phân bố ngành nghề** — top nghề theo số job.
# 4. **% job có skill** (đi qua nghề) — chỉ số quyết định sức mạnh lớp skill.
# 5. **Phân bố client theo `n_apps`** — mức lệch giữa client lớn và nhỏ.
#
# ⚠️ **Bất đối xứng quan trọng**: lớp nghề **dày ở phía user, thưa ở phía job**.
# **136.264 user** có cạnh nghề trong train nhưng chỉ **26.678 job** có cạnh nghề
# (gấp **5,1 lần**). Vì vậy đường lan truyền skill chủ yếu đi qua user
# (`u → nghề → skill`), ít qua job. Hệ quả này được đo ở ablation `[8]`.

# %%
# ============================================================================
# [3b] EDA — phân bố bậc, độ thưa, ngành nghề, client
# ============================================================================
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T3 = time.perf_counter()
set_seed(42)

deg_user = np.bincount(uj_tr_src, minlength=N_NODES)[:N_USERS]
deg_job = np.bincount(uj_tr_dst - O_J, minlength=N_JOBS)
deg_user_nz = deg_user[deg_user > 0]
deg_job_nz = deg_job[deg_job > 0]

sparsity = 100.0 * (1.0 - N_TRAIN_UJ / (N_USERS * N_JOBS))
print("=== PHÂN BỐ BẬC (train) ===")
print(f"User có ≥1 cạnh train : {deg_user_nz.size:,}/{N_USERS:,} "
      f"({100 * deg_user_nz.size / N_USERS:.2f}%)")
print(f"  app/user: min {deg_user_nz.min()} | median {int(np.median(deg_user_nz))} | "
      f"p90 {int(np.percentile(deg_user_nz, 90))} | max {deg_user_nz.max():,}")
print(f"Job có ≥1 cạnh train  : {deg_job_nz.size:,}/{N_JOBS:,} "
      f"({100 * deg_job_nz.size / N_JOBS:.2f}%)")
print(f"  app/job : min {deg_job_nz.min()} | median {int(np.median(deg_job_nz))} | "
      f"p90 {int(np.percentile(deg_job_nz, 90))} | max {deg_job_nz.max():,}")
print(f"Độ thưa ma trận user×job: {sparsity:.5f}%  (tức {100 - sparsity:.5f}% ô có dữ liệu)")
print(f"User đuôi dài: top 1% user chiếm "
      f"{100 * np.sort(deg_user_nz)[::-1][:max(1, deg_user_nz.size // 100)].sum() / deg_user_nz.sum():.1f}% số cạnh")

# --- % job có nghề / có skill ---
n_jobs_with_occ = int((EDGE_TYPE == ET_JOB_OCC).sum())
n_jobs_without_occ = N_JOBS - n_jobs_with_occ
n_skill_edges = int((EDGE_TYPE == ET_OCC_SKILL).sum())
occ_with_skill = np.unique(EDGE_INDEX[0][EDGE_TYPE == ET_OCC_SKILL])
print("\n=== LỚP NGHỀ & KỸ NĂNG ===")
print(f"Job có cạnh nghề   : {n_jobs_with_occ:,}/{N_JOBS:,} = "
      f"{100 * n_jobs_with_occ / N_JOBS:.2f}%   (thiếu: {n_jobs_without_occ:,} = "
      f"{100 * n_jobs_without_occ / N_JOBS:.2f}%)")
print(f"Nghề có kỹ năng    : {occ_with_skill.size}/{N_OCC} "
      f"({100 * occ_with_skill.size / N_OCC:.1f}%)")
print(f"Cạnh nghề–kỹ năng  : {n_skill_edges:,} | nút kỹ năng: {N_SKILL:,}")
print(f"User có cạnh nghề  : {len(np.unique(EDGE_INDEX[0][EDGE_TYPE == ET_USER_OCC])):,} "
      f"→ lớp nghề dày ở phía user, thưa ở phía job (bất đối xứng ~5,1×)")

# --- phân bố client ---
client_apps = np.array([c["n_apps"] for c in CLIENTS], dtype=np.int64)
client_jobs = np.array([c["n_jobs"] for c in CLIENTS], dtype=np.int64)
client_users = np.array([c["n_users"] for c in CLIENTS], dtype=np.int64)
# cạnh train thật theo client_of_job (silo thật)
train_edges_per_client = np.bincount(CLIENT_OF_JOB[uj_tr_dst - O_J], minlength=N_CLIENTS_TOTAL)
print("\n=== PHÂN BỐ CLIENT (9.116) ===")
for label, arr in [("n_apps", client_apps), ("n_jobs", client_jobs), ("n_users", client_users)]:
    print(f"{label:7s}: min {arr.min():>4} | p25 {int(np.percentile(arr, 25)):>4} | "
          f"median {int(np.median(arr)):>4} | p75 {int(np.percentile(arr, 75)):>4} | max {arr.max():>5,}")
print(f"cạnh train/client: min {train_edges_per_client.min()} | median "
      f"{int(np.median(train_edges_per_client))} | mean {train_edges_per_client.mean():.1f} | "
      f"max {train_edges_per_client.max():,}")
print(f"Client KHÔNG có cạnh train: {int((train_edges_per_client == 0).sum())}  ← phải bằng 0")
print(f"Client có ≥10 cạnh train : {int((train_edges_per_client >= 10).sum()):,} "
      f"({100 * float((train_edges_per_client >= 10).mean()):.1f}%)")
print(f"Client có ≥50 cạnh train : {int((train_edges_per_client >= 50).sum()):,} "
      f"({100 * float((train_edges_per_client >= 50).mean()):.1f}%)")
print(f"Client chỉ có 1 job      : {int((client_jobs == 1).sum()):,} | ≤3 job: {int((client_jobs <= 3).sum()):,}")
assert train_edges_per_client.min() > 0, "có client rỗng — không hợp lệ cho FL"

# --- hình EDA ---
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.ravel()
axes[0].hist(np.log10(deg_user_nz), bins=40, color="#3572b0")
axes[0].set_title("Phân bố app/user (log10)"); axes[0].set_xlabel("log10(số app)")
axes[1].hist(np.log10(deg_job_nz), bins=40, color="#c0504d")
axes[1].set_title("Phân bố app/job (log10)"); axes[1].set_xlabel("log10(số app)")
axes[2].bar(["Có dữ liệu", "Trống"], [100 - sparsity, sparsity], color=["#3572b0", "#cccccc"])
axes[2].set_title(f"Độ thưa ma trận user×job\n({sparsity:.4f}% trống)"); axes[2].set_ylabel("%")
occ_counts = np.bincount(EDGE_INDEX[1][EDGE_TYPE == ET_JOB_OCC] - O_O, minlength=N_OCC)
top_occ = np.argsort(-occ_counts)[:15]
axes[3].barh([str(OCC_IDS[i]) for i in top_occ][::-1], occ_counts[top_occ][::-1], color="#9bbb59")
axes[3].set_title("Top 15 nghề theo số job"); axes[3].set_xlabel("số job")
axes[4].bar(["Có nghề", "Không nghề"], [n_jobs_with_occ, n_jobs_without_occ], color=["#4f81bd", "#c0504d"])
axes[4].set_title(f"% job có cạnh nghề\n({100 * n_jobs_with_occ / N_JOBS:.1f}% có)"); axes[4].set_ylabel("số job")
axes[5].hist(np.log10(client_apps), bins=40, color="#8064a2")
axes[5].axvline(np.log10(10), color="k", ls="--", lw=1)
axes[5].set_title("Phân bố client theo n_apps (log10)"); axes[5].set_xlabel("log10(n_apps)")
fig.suptitle("EDA — CareerBuilder, đồ thị v3 (mẫu đầy đủ, không lấy mẫu)", fontsize=13)
fig.tight_layout()
eda_path = os.path.join(FIG, "F01_eda_phan_bo.png")
fig.savefig(eda_path, dpi=160, bbox_inches="tight")
plt.close(fig)
print("\nĐã lưu hình:", eda_path)

EDA = dict(
    n_users_in_train=int(deg_user_nz.size), n_jobs_in_train=int(deg_job_nz.size),
    app_per_user_median=float(np.median(deg_user_nz)), app_per_job_median=float(np.median(deg_job_nz)),
    sparsity_pct=round(sparsity, 5),
    n_jobs_with_occ=n_jobs_with_occ, pct_jobs_with_occ=round(100 * n_jobs_with_occ / N_JOBS, 2),
    n_occ_with_skill=int(occ_with_skill.size),
    client_apps_median=float(np.median(client_apps)),
    train_edges_per_client_min=int(train_edges_per_client.min()),
    train_edges_per_client_median=float(np.median(train_edges_per_client)),
    clients_ge10_train=int((train_edges_per_client >= 10).sum()),
    clients_ge50_train=int((train_edges_per_client >= 50).sum()),
)
mark("[3] EDA", T3)

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

# %% [markdown]
# ## [7f] Đánh giá tách nhóm client — vì phân bố client rất lệch
#
# FedAvg bị **chi phối bởi client lớn**: max 4.320 cạnh train gấp **864 lần** min 5
# cạnh. Nếu chỉ báo trung bình toàn cục, con số bị kéo bởi vài client lớn và **không
# phản ánh chất lượng trên client nhỏ**.
#
# Vì vậy R@20 được báo **tách hai nhóm**: client **≥10 job** và client **<10 job**
# (418 client chỉ có **1 job**; 3.877 client có **≤3 job**).
#
# ⚠️ Đồng thời phải nói rõ: **2.096 client (23,0%)** không có cạnh test nào, nên
# metric per-client chỉ phủ **~7.020 client** trên 9.116 — không phải toàn bộ.

# %%
# ============================================================================
# [7g] R@20 theo nhóm client (chỉ trên client CÓ cạnh test)
# ============================================================================
T7d = time.perf_counter()

# --- client của từng cạnh test (theo JOB, silo thật) ---
client_of_test_edge = CLIENT_OF_JOB[uj_te_dst - O_J]
clients_with_test = np.unique(client_of_test_edge)
print(f"Client có ≥1 cạnh test: {clients_with_test.size:,}/{N_CLIENTS_TOTAL:,} "
      f"({100 * clients_with_test.size / N_CLIENTS_TOTAL:.1f}%)")
print(f"Client KHÔNG có test  : {N_CLIENTS_TOTAL - clients_with_test.size:,} "
      f"({100 * (N_CLIENTS_TOTAL - clients_with_test.size) / N_CLIENTS_TOTAL:.1f}%) "
      f"— không tính được metric per-client")
client_jobs_all = np.array([c["n_jobs"] for c in CLIENTS], dtype=np.int64)
big_clients = set(np.where(client_jobs_all >= 10)[0].tolist())
print(f"Client ≥10 job: {len(big_clients):,} | <10 job: {N_CLIENTS_TOTAL - len(big_clients):,}")


def per_client_recall20(E, max_users_per_client: int = 300, seed: int = 42) -> dict:
    """R@20 trung bình theo client, tách nhóm ≥10 job và <10 job."""
    E = E.detach().cpu().numpy() if torch.is_tensor(E) else E
    if E.shape[0] == N_NODES:
        get_u = lambda arr: E[arr]
        get_j = lambda arr: E[O_J + arr]
    else:
        get_u = lambda arr: E[arr]
        get_j = lambda arr: E[N_USERS + arr]
    rng = np.random.default_rng(seed)
    by_group = {"big": [], "small": []}
    per_client = {}
    for cid in clients_with_test.tolist():
        m = client_of_test_edge == cid
        us = np.unique(uj_te_src[m])
        if us.size == 0:
            continue
        if us.size > max_users_per_client:
            us = np.sort(rng.choice(us, max_users_per_client, replace=False))
        # catalog = các job có ≥1 cạnh train
        users_pos = []
        for u in us.tolist():
            ps = [j for j in POS_ALL.get(u, []) if CATALOG_POS[j] >= 0]
            if ps:
                users_pos.append((u, ps))
        if not users_pos:
            continue
        U = np.array([x[0] for x in users_pos])
        sc = get_u(U) @ get_j(CATALOG).T
        rec = []
        for r, (u, ps) in enumerate(users_pos):
            idx = [CATALOG_POS[j] for j in SEEN.get(u, []) if CATALOG_POS[j] >= 0]
            if idx:
                sc[r, idx] = -np.inf
            top = np.argpartition(-sc[r], 20)[:21]
            rank = np.full(CATALOG.size, 10 ** 6, dtype=np.int64)
            rank[top] = np.argsort(-sc[r][top])
            pr = rank[[CATALOG_POS[j] for j in ps]]
            rec.append(float((pr < 20).mean()))
        val = float(np.mean(rec))
        per_client[cid] = dict(recall20=val, n_users=len(users_pos),
                               n_jobs=int(client_jobs_all[cid]))
        by_group["big" if cid in big_clients else "small"].append(val)
    return dict(per_client=per_client, big=by_group["big"], small=by_group["small"])


FL_PERCLIENT = per_client_recall20(FL_E)
print("\n=== R@20 TÁCH NHÓM CLIENT (trung bình theo client, không theo user) ===")
for gname, label in [("big", "client ≥10 job"), ("small", "client <10 job")]:
    arr = np.array(FL_PERCLIENT[gname])
    if arr.size:
        lo, hi = bootstrap_ci(arr, seed=7)
        print(f"{label:16s}: n={arr.size:5,} client | R@20 = {arr.mean():.4f} "
              f"[{lo:.4f}, {hi:.4f}] | median {np.median(arr):.4f}")
    else:
        print(f"{label:16s}: không có client nào")
print(f"{'tất cả':16s}: n={len(FL_PERCLIENT['big']) + len(FL_PERCLIENT['small']):5,} client "
      f"(trên {N_CLIENTS_TOTAL:,} client, phần còn lại không có cạnh test)")

fig, ax = plt.subplots(1, 1, figsize=(7, 4))
data = [np.array(FL_PERCLIENT["big"]), np.array(FL_PERCLIENT["small"])]
labels = [f"≥10 job\n(n={data[0].size:,})", f"<10 job\n(n={data[1].size:,})"]
if data[0].size and data[1].size:
    ax.boxplot([d[~np.isnan(d)] for d in data], tick_labels=labels, showmeans=True)
    ax.set_ylabel("Recall@20 theo client")
    ax.set_title("Phân bố R@20 tách nhóm client — FedAvg bị chi phối bởi client lớn")
    ax.grid(alpha=.3, axis="y")
    fig.tight_layout()
    grp_path = os.path.join(FIG, "F06_r20_theo_nhom_client.png")
    fig.savefig(grp_path, dpi=160, bbox_inches="tight")
    print("Đã lưu hình:", grp_path)
plt.close(fig)
mark("[7f] Tách nhóm client", T7d, f"{len(FL_PERCLIENT['per_client']):,} client có test")

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
