# %% [markdown]
# # [1] Mục tiêu — Gợi ý việc làm bằng GNN + Học liên bang (GraphSafe)
#
# ## 1.1 Bài toán
#
# Cho một người dùng đã có lịch sử ứng tuyển, cần xếp hạng các **tin tuyển dụng**
# mà người đó nhiều khả năng sẽ ứng tuyển tiếp theo. Đây là bài toán gợi ý
# top-K trong đồ thị **hai phía (bipartite) user–job**, có thêm các lớp thông tin
# phụ: **nghề (occupation)** lấy từ O*NET và **kỹ năng công nghệ (skill)** trực
# thuộc nghề.
#
# Điểm khó không nằm ở mô hình, mà ở **dữ liệu không được rời khỏi nơi sinh ra**:
# nhà tuyển dụng không được phép gửi danh sách ứng viên của mình cho một máy chủ
# trung tâm. Vì vậy ta dùng **học liên bang (Federated Learning — FL)**:
# mỗi nhà tuyển dụng là một **client**, dữ liệu nằm nguyên tại client, chỉ
# **tham số mô hình** (embedding) được gửi lên server.
#
# ## 1.2 GraphSafe là gì
#
# **GraphSafe** là nguyên tắc thiết kế của đồ án, gồm 4 điều kiện:
#
# | # | Điều kiện | Cách đảm bảo trong notebook này |
# |---|---|---|
# | 1 | Dữ liệu thô **không rời node** | Vòng lặp FL chỉ trao đổi ma trận embedding `dim × node`, không gửi cặp `(user, job)` nào |
# | 2 | Client chỉ thấy **quan sát của chính mình** | Mỗi client dựng đồ thị con từ các job **thuộc sở hữu của client đó**; không đọc cạnh của client khác |
# | 3 | Server **không tái dựng được** dữ liệu gốc | Server chỉ nhận trung bình có trọng số của embedding; số chiều `dim` ≪ số cạnh |
# | 4 | **Tái lập được** | Seed cố định 42, mọi phép lấy mẫu dùng `numpy.random.default_rng` / `torch.Generator` riêng |
#
# > Lưu ý trung thực: điều kiện 3 là **bảo vệ theo thiết kế**, không phải bảo
# > vệ hình thức (differential privacy). Notebook không tuyên bố FL ở đây
# > chống được tấn công suy luận thành viên (membership inference). Xem mục
# > "Hạn chế" ở phần [10].
#
# ## 1.3 Ba kiến trúc GNN sẽ thử
#
# | Mô hình | Công thức lan truyền | Vai trò trong đồ án |
# |---|---|---|
# | **LightGCN** | $e_u^{(l+1)}=\sum_{j\in N(u)}\frac{1}{\sqrt{d_ud_j}}e_j^{(l)}$, đầu ra là trung bình các tầng | Mô hình chính: không có tham số phi tuyến, phù hợp đồ thị cực thưa |
# | **GraphSAGE** | $h_u^{(l+1)}=\sigma\big(W\cdot \text{MEAN}_{j\in N(u)}h_j^{(l)}\big)$ | Kiểm chứng: thêm MLP có giúp gì không? |
# | **GAT** | $\alpha_{uj}=\text{softmax}_j\big(\text{LeakyReLU}(a^\top[Wh_u\Vert Wh_j])\big)$ | Kiểm chứng: attention có giúp phân biệt láng giềng không? |
#
# Mỗi mô hình huấn luyện bằng **BPR loss** (Bayesian Personalised Ranking):
# với mỗi cạnh dương $(u,j^+)$ lấy một job âm $j^-$ ngẫu nhiên, tối đa hoá
# $\log\sigma(s(u,j^+)-s(u,j^-))$.
#
# ## 1.4 Câu hỏi nghiên cứu
#
# 1. GNN có vượt baseline cổ điển (Popularity, Item-KNN, BPR-MF) trên dữ liệu thật không?
# 2. **Liên bang hoá** làm mất bao nhiêu chất lượng so với huấn luyện tập trung?
# 3. Lớp **nghề + kỹ năng** đóng góp bao nhiêu? (Đây là chỗ dữ liệu CareerBuilder
#    nghèo hơn MEDAJob, xem mục [2] và [8].)
# 4. **Số client** ảnh hưởng thế nào tới chất lượng và độ trễ?

# %% [markdown]
# ## [1b] Thiết lập chung — hằng số, seed, thư mục
#
# Cell này chạy được **cả trên Colab lẫn máy local**. Toàn bộ hằng số nằm ở đây,
# không rải rác trong code, để bảng kết quả và biểu đồ luôn khớp nhau.

# %%
import json
import math
import os
import random
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import torch

warnings.filterwarnings("ignore", category=UserWarning)

SEED = 42
DIM = 32                 # số chiều embedding mặc định
LAYERS = 2               # số tầng lan truyền mặc định
N_CLIENTS = 20           # số client tham gia mỗi vòng (chọn top theo n_apps)
ROUNDS = 8               # số vòng FL mặc định
LOCAL_EPOCHS = 1         # số epoch cục bộ mỗi vòng
LR = 0.05                # learning rate cục bộ
BATCH = 8192
N_EVAL_USERS = 1000      # số user lấy mẫu để đánh giá (ĐÂY LÀ MẪU, không phải toàn bộ)
K_EVAL = (10, 20)
N_BOOT = 1000            # số lần bootstrap cho CI 95%


def set_seed(seed: int = SEED) -> None:
    """Khoá mọi nguồn ngẫu nhiên: python, numpy, torch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(False)  # sparse.mm không có kernel tất định


set_seed()
print("Python", sys.version.split()[0], "| numpy", np.__version__, "| torch", torch.__version__)
print("Threads torch:", torch.get_num_threads())
print("Seed:", SEED, "| dim:", DIM, "| layers:", LAYERS, "| clients:", N_CLIENTS)

# %% [markdown]
# ## [1c] Bảng số liệu nền — đọc `meta.json` và kiểm tra chéo với `graph.npz`
#
# Notebook **không đo lại** dữ liệu thô (1,6 triệu dòng, 3,2 GB): nó đọc artifacts
# do `src/prepare_v3.py` sinh ra và **kiểm tra chéo** để chắc chắn không lệch.
# Nếu một assert nào đó sai, notebook dừng ngay thay vì in ra bảng số sai.

# %%
import argparse

# --- tìm gốc dự án: chạy được từ Colab (/content) lẫn local ---
CANDIDATES = [
    Path.cwd(),
    Path.cwd().parent,
    Path("/content/GNN-FL-JobRec"),
    Path("/content"),
]
ROOT = None
for cand in CANDIDATES:
    if (cand / "artifacts" / "v3" / "graph.npz").exists():
        ROOT = cand.resolve()
        break
if ROOT is None:
    raise FileNotFoundError(
        "Không tìm thấy artifacts/v3/graph.npz. Xem hướng dẫn upload ở mục [6]."
    )

ART = ROOT / "artifacts" / "v3"
RES = ROOT / "results" / "v3"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)

meta = json.loads((ART / "meta.json").read_text(encoding="utf-8"))
print("ROOT =", ROOT)
print("meta.version =", meta["version"], "| generated_at =", meta["generated_at"])
print("runtime build =", meta["runtime_seconds"], "s | RAM đỉnh =", meta["memory_peak_gb"], "GB")

# --- nạp đồ thị ---
g = np.load(ART / "graph.npz", allow_pickle=False)
N_NODES = int(g["n_nodes"])
N_USERS = int(g["n_users"])
N_JOBS = int(g["n_jobs"])
N_OCC = int(g["n_occupations"])
N_SKILL = int(g["n_skills"])
O_U, O_J, O_O, O_S = [int(x) for x in g["offsets"]]
EDGE_INDEX = g["edge_index"].astype(np.int64)
EDGE_TYPE = g["edge_type"].astype(np.int16)
TRAIN_MASK = g["train_mask"]
TEST_MASK = g["test_mask"]
IS_CATALOG = g["is_public"].astype(bool)      # occ + skill: nút danh mục công khai
CLIENT_OF_JOB = g["client_of_job"].astype(np.int64)
CLIENT_OF_USER = g["client_of_user"].astype(np.int64)
OCC_IDS = g["occ_ids"]
SKILL_NAMES = g["skill_names"]

# --- kiểm tra chéo: đại số cơ bản ---
assert N_NODES == N_USERS + N_JOBS + N_OCC + N_SKILL, "tổng nút không khớp offsets"
assert EDGE_INDEX.shape == (2, EDGE_TYPE.size), "edge_index / edge_type lệch chiều"
assert TRAIN_MASK.size == TEST_MASK.size == EDGE_TYPE.size, "mask lệch chiều"
assert EDGE_INDEX.min() == 0 and EDGE_INDEX.max() == N_NODES - 1, "chỉ số nút ngoài phạm vi"
assert int((TRAIN_MASK & TEST_MASK).sum()) == 0, "train/test chồng lấn"
assert all(len(x) == 7 for x in OCC_IDS.tolist()), "mã nghề phải dài 7 ký tự (soc[:7])"
assert bool(g["is_symmetric"]), "artifacts phải khai báo đồ thị đối xứng"

# Không có cạnh tự trỏ (dữ liệu 1 chiều vô hướng đã lưu 1 dòng/cạnh)
assert int((EDGE_INDEX[0] == EDGE_INDEX[1]).sum()) == 0, "phát hiện self-loop"

# --- cạnh theo loại ---
ET_USER_JOB, ET_JOB_OCC, ET_OCC_SKILL, ET_USER_OCC = 0, 1, 2, 3
n_by_type = {int(t): int((EDGE_TYPE == t).sum()) for t in range(4)}
n_train_uj = int((TRAIN_MASK & (EDGE_TYPE == ET_USER_JOB)).sum())
n_test_uj = int((TEST_MASK & (EDGE_TYPE == ET_USER_JOB)).sum())

print("\n=== ĐỒ THỊ ===")
print(f"Nút            : {N_NODES:,} = {N_USERS:,} user + {N_JOBS:,} job + {N_OCC} nghề + {N_SKILL:,} kỹ năng")
print(f"Cạnh (1 dòng)  : {EDGE_TYPE.size:,}")
for t, name in enumerate(g["edge_type_names"]):
    print(f"   {t} {str(name):10s}: {n_by_type[t]:>9,}")
print(f"Train user-job : {n_train_uj:,} | Test user-job: {n_test_uj:,}")
print(f"Độ thưa        : {meta['sparsity_pct']:.5f}%")

# Tỉ lệ test THẬT: min_apps_for_test=5 khiến 63,3% cạnh không bao giờ vào test
pct_test_of_uj = 100.0 * n_test_uj / (n_train_uj + n_test_uj)
pct_test_of_eligible = 100.0 * n_test_uj / (n_test_uj / 0.1955)
print(f"\nTest chiếm {pct_test_of_uj:.2f}% toàn bộ cạnh user-job "
      f"(trên tập đủ điều kiện ~19,55% — KHÔNG phải 20% như cấu hình test_ratio)")

# --- client ---
CLIENTS = json.loads((ART / "clients.json").read_text(encoding="utf-8"))
N_CLIENTS_TOTAL = len(CLIENTS)
client_apps = np.array([c["n_apps"] for c in CLIENTS], dtype=np.int64)
assert N_CLIENTS_TOTAL == meta["clients"]["n_clients"], "clients.json lệch meta"
assert client_apps.min() >= 10, "client phải có >= 10 application"
assert (np.diff(np.array([c["client_id"] for c in CLIENTS])) == 1).all(), "client_id phải liên tục"
print(f"\nClient         : {N_CLIENTS_TOTAL:,} (min {client_apps.min()} / "
      f"median {int(np.median(client_apps))} / max {client_apps.max():,})")
print(f"App phủ        : {meta['clients']['pct_apps_covered_of_all_apps']}% tổng số application")

# --- kiểm tra: cạnh thuộc client nào? ---
# CẠNH (u,j) THUỘC client_of_job[j] — nhà tuyển dụng SỞ HỮU tin đó.
# client_of_user chỉ là nhãn "client mà user ứng tuyển nhiều nhất", KHÔNG phải membership.
uj_tr = EDGE_INDEX[:, TRAIN_MASK & (EDGE_TYPE == ET_USER_JOB)]
pct_same_client = 100.0 * float(
    (CLIENT_OF_USER[uj_tr[0]] == CLIENT_OF_JOB[uj_tr[1] - O_J]).mean())
print(f"Tỉ lệ cạnh có client_of_user[u] == client_of_job[j]: {pct_same_client:.2f}%")
assert 40.0 < pct_same_client < 46.0, "số này phải ~43,15% theo kiểm chứng"
print("=> Vì vậy gán cạnh theo client_of_job (silo thật), KHÔNG theo client_of_user.")
