"""
Notebook tái lập kết quả bài toán 1: GNN + Học liên bang cho gợi ý việc làm.

Chạy: jupyter nbconvert --to notebook --execute notebooks/01_medajob_fl.ipynb
hoặc mở bằng Jupyter và chạy lần lượt.

Notebook này KHÔNG huấn luyện lại từ đầu (mất ~80 giây, đã có trong
results/); nó đọc kết quả và tái hiện các bảng/hình chính, kèm phần
chạy lại một thí nghiệm nhỏ để chứng minh pipeline hoạt động.
"""

# %% [markdown]
# # Bài toán 1 — GNN kết hợp Học liên bang cho gợi ý việc làm
#
# Notebook này tái lập các con số trong báo cáo. Cấu trúc:
#
# 1. Nạp kết quả đã sinh (`results/reco_main.json`)
# 2. Bảng so sánh sáu hệ gợi ý
# 3. Đường cong học liên bang
# 4. **Chạy lại thật** một thí nghiệm FedAvg nhỏ để chứng minh pipeline sống
# 5. Kiểm tra tính tất định

# %%
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))

from src.common import load_config

cfg = load_config()
results = json.loads((ROOT / "results" / "reco_main.json").read_text(encoding="utf-8"))
print("Đã nạp:", ROOT / "results" / "reco_main.json")
print("Các hệ:", list(results["systems"]))

# %% [markdown]
# ## 1. Dữ liệu

# %%
d = results["data_summary"]
print(f"Người dùng       : {d['n_users']}")
print(f"Tin tuyển dụng   : {d['n_jobs']:,}")
print(f"Kỹ năng          : {d['n_skills']}")
print(f"Ngành            : {d['n_industries']}")
print(f"Train / Test     : {d['n_train']} / {d['n_test']}")
print(f"Người dùng in test: {d['users_in_test']}")
print(f"Độ thưa          : {d['sparsity_pct']:.2f}%")
print(f"\nChất lượng dữ liệu: {d['quality']['template_jobs']} tin template "
      f"({d['quality']['template_pct']}%)")

# %% [markdown]
# ## 2. Bảng so sánh sáu hệ gợi ý
#
# Con số quan trọng nhất: Recall@20 của mô hình liên bang so với cục bộ
# (không chia sẻ gì) và tập trung (mốc trên lý thuyết).

# %%
labels = [
    ("popularity", "Phổ biến"),
    ("skill_cbf", "Nội dung (kỹ năng)"),
    ("item_knn", "Item-KNN"),
    ("local_only", "Cục bộ (không chia sẻ)"),
    ("fedavg", "Liên bang (FedAvg)"),
    ("fedprox", "Liên bang (FedProx)"),
    ("centralized", "Tập trung"),
]
rows = []
for key, label in labels:
    s = results["systems"].get(key)
    if not s:
        continue
    ci = s.get("recall@20_ci", {})
    rows.append({
        "Hệ": label,
        "R@10": round(s["recall@10"], 4),
        "R@20": round(s["recall@20"], 4),
        "CI dưới": round(ci.get("lo", float("nan")), 4),
        "CI trên": round(ci.get("hi", float("nan")), 4),
        "NDCG@20": round(s["ndcg@20"], 4),
        "MRR@20": round(s["mrr@20"], 4),
    })
df = pd.DataFrame(rows)
display(df)

# %%
loc = results["systems"]["local_only"]["recall@20"]
fed = results["systems"]["fedavg"]["recall@20"]
cent = results["systems"]["centralized"]["recall@20"]
gap = cent - loc
print(f"Cục bộ {loc:.4f} → Liên bang {fed:.4f} → Tập trung {cent:.4f}")
print(f"Học liên bang lấy lại {(fed - loc) / gap:.1%} khoảng cách "
      f"do chia nhỏ dữ liệu gây ra")

# %% [markdown]
# ## 3. Đường cong học liên bang
#
# FedAvg **không hội tụ đơn điệu** — đây là hiện tượng thật, không phải lỗi.

# %%
for s in results["client_sweep"]:
    curve = pd.DataFrame(s["curve"])
    print(f"\n=== {s['n_clients']} khách hàng ===")
    print(f"  Cục bộ: {s['local_only']['recall@20']:.4f} | "
          f"FedAvg cuối: {s['fedavg_final']['recall@20']:.4f} | "
          f"đỉnh: {s['fedavg_best']['recall@20']:.4f}")
    display(curve[["round", "recall@20", "ndcg@20", "train_loss"]].head(10))

# %% [markdown]
# ## 4. Chi phí truyền thông
#
# Đây là kết quả **không thuận lợi**: ở quy mô dữ liệu này, gửi tham số
# tốn nhiều byte hơn gửi thẳng dữ liệu thô. Lợi ích của FL là bảo mật.

# %%
c = results["communication"]
print(f"Tổng byte gửi lên     : {c['up_bytes_total'] / 1024:,.0f} KB")
print(f"Dữ liệu thô nếu gửi   : {c['raw_data_bytes_if_centralized'] / 1024:.0f} KB")
print(f"Tỉ lệ                 : gấp {c['ratio_up_vs_raw']:,.0f} lần")
print(f"Hoà vốn ở             : {c['crossover_interactions']:,} tương tác")
print(f"\n{c['interpretation']}")

# %% [markdown]
# ## 5. Chạy lại THẬT một thí nghiệm nhỏ
#
# Phần trên chỉ đọc kết quả. Để chứng minh pipeline hoạt động, ta chạy lại
# một cấu hình FedAvg rút gọn (2 vòng, 2 epoch cục bộ) và kiểm tra rằng
# mô hình sinh ra đúng loại kết quả.

# %%
import numpy as np

from src.medajob.evaluate import evaluate_ranking
from src.medajob.federated import run_federated
from src.medajob.run_experiments import (build_parts, load_artifacts,
                                         scores_from_state)

data = load_artifacts(cfg)
parts, usr_client = build_parts(data, 5)
nU, nJ = data["n_users"], data["n_jobs"]
g = cfg["medajob"]["graph"]


def eval_fn(state):
    s = scores_from_state(state, data, cfg, nU, nJ)
    return evaluate_ranking(s, data["test"], data["Mtr"], k_list=(20,),
                            relevant_threshold=4, n_boot=50, seed=42)


state, logs, info = run_federated(
    parts, data["train"], usr_client, g,
    rounds=2, local_epochs=2, lr=0.02,
    dim=int(g["dim"]), layers=int(g["layers"]),
    reg=1e-5, mu=0.0, sample_rate=1.0, eval_fn=eval_fn, seed=42)

print(f"Sau {info['rounds_run']} vòng rút gọn:")
for lg in logs:
    print(f"  vòng {lg.round}: R@20 = {lg.metrics.get('recall@20', float('nan')):.4f}, "
          f"loss = {lg.mean_train_loss:.4f}, "
          f"gửi lên = {lg.up_bytes:,} byte")
print(f"\nSố tham số           : {info['param_bytes_per_transfer'] // 4:,}")
print(f"Byte mỗi lần chuyển  : {info['param_bytes_per_transfer']:,}")

# %% [markdown]
# ## 6. Kiểm tra tính tất định
#
# Hai lần chạy cùng seed phải cho cùng kết quả. Nếu không, mọi so sánh
# trong báo cáo đều không đáng tin.

# %%
def run_once(seed: int):
    st, lg, _ = run_federated(
        parts, data["train"], usr_client, g,
        rounds=2, local_epochs=2, lr=0.02,
        dim=int(g["dim"]), layers=int(g["layers"]),
        reg=1e-5, mu=0.0, sample_rate=1.0, eval_fn=eval_fn, seed=seed)
    return st["emb.weight"].clone()


a = run_once(42)
b = run_once(42)
c_ = run_once(43)
print(f"|w(seed=42) lần 1 − lần 2| max = {(a - b).abs().max().item():.2e}  "
      f"(phải ~ 0)")
print(f"|w(seed=42) − w(seed=43)| max  = {(a - c_).abs().max().item():.2e}  "
      f"(phải > 0, chứng tỏ seed có tác dụng)")

# %% [markdown]
# ## Kết luận
#
# - Học liên bang thu hẹp khoảng cách với mô hình tập trung mà không gửi dữ liệu gốc.
# - Mô hình đồ thị vượt mọi baseline: dựng đồ thị có đóng góp thật.
# - Ở quy mô này FL tốn nhiều băng thông hơn, lợi ích nằm ở tuân thủ pháp lý.
# - Tập kiểm thử chỉ 16 người dùng → khoảng tin cậy rộng, cần thêm dữ liệu.
