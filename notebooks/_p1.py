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
        "/kaggle/input/dss-gnn-fl-v3/artifacts/v3",
        "/kaggle/input/dss-gnn-fl-v3",
        here,
        os.path.join(here, "artifacts", "v3"),
        os.path.dirname(here),
        os.path.join(os.path.dirname(here), "artifacts", "v3"),
        "/content/GNN-FL-JobRec/artifacts/v3",
        "/content/artifacts/v3",
        "/content/drive/MyDrive/dss-gnn-fl-v3/artifacts/v3",
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
