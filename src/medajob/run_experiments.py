"""
Chạy toàn bộ thực nghiệm bài toán 1 và ghi results/reco_main.json.

Sáu hệ được so sánh trên CÙNG một tập test:
  1. Popularity        — không cá nhân hoá, sàn tham chiếu
  2. SkillCBF          — content-based theo kỹ năng
  3. ItemKNN           — collaborative filtering cổ điển
  4. Local-only        — mỗi client tự train, không chia sẻ gì
  5. FedAvg (GNN)      — học liên bang
  6. Centralized (GNN) — mô hình gộp toàn bộ dữ liệu (mốc trên lý thuyết)

Cách đọc kết quả cho đúng:
  - FedAvg được báo cáo CẢ đường cong theo vòng, giá trị ĐỈNH và giá trị
    VÒNG CUỐI. Không chỉ báo đỉnh, vì như thế là chọn có lợi.
  - Mọi chỉ số kèm CI 95% bootstrap trên 16 user có mặt trong test. Với
    n = 16, khoảng tin cậy rộng là bản chất của dữ liệu, không phải lỗi.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common import (ROOT, banner, load_config, save_json, set_seed,
                        setup_console, step)
from src.medajob.evaluate import evaluate_ranking
from src.medajob.federated import GraphParts, build_norm, run_federated
from src.medajob.models import (GraphSAGE, LightGCN, item_knn_scores,
                                popularity_scores, raw_data_bytes,
                                skill_cbf_scores, state_dict_bytes)


# =====================================================================
# 0. Nạp artifacts
# =====================================================================
def load_artifacts(cfg: dict) -> dict:
    art = Path(cfg["paths"]["artifacts"]) / "medajob"
    z = np.load(art / "graph.npz", allow_pickle=False)
    import pandas as pd

    jobs = pd.read_csv(art / "jobs.csv", encoding="utf-8-sig")
    users = pd.read_csv(art / "users.csv", encoding="utf-8-sig")
    meta = __import__("json").loads((art / "meta.json").read_text(encoding="utf-8"))
    return {
        "z": z, "jobs": jobs, "users": users, "meta": meta,
        "n_nodes": int(z["n_nodes"]), "n_users": int(z["n_users"]),
        "n_jobs": int(z["n_jobs"]),
        "edge_index": z["edge_index"], "edge_type": z["edge_type"],
        "train": z["train"], "test": z["test"],
        "Mtr": z["Mtr"], "Mte": z["Mte"],
        "client_of_job": z["client_of_job"], "user_client": z["user_client"],
    }


def split_clients(client_of_job: np.ndarray, user_client: np.ndarray,
                  n_clients: int) -> tuple[np.ndarray, np.ndarray]:
    """Gán lại client id về [0, n_clients).

    Dùng phép chia lấy dư để giữ tính tất định và để mỗi client có quy mô
    tương đương. `client_of_job` ban đầu là employer_id (hàng trăm giá trị);
    ta gom lại thành n_clients nhóm.
    """
    job_client = (client_of_job.astype(np.int64) % n_clients).astype(np.int32)
    usr_client = (user_client.astype(np.int64) % n_clients).astype(np.int32)
    return job_client, usr_client


def build_parts(data: dict, n_clients: int) -> tuple[GraphParts, np.ndarray]:
    """Tách đồ thị thành phần công khai (server) và riêng tư (client)."""
    ei = data["edge_index"]
    et = data["edge_type"]
    n_users = data["n_users"]
    job_client, usr_client = split_clients(
        data["client_of_job"], data["user_client"], n_clients)

    # edge_type: 0=job–skill, 1=job–industry -> công khai
    #            2=user–skill, 3=user–job       -> riêng tư
    public = et <= 1
    pub_src, pub_dst = ei[0][public], ei[1][public]

    priv = ~public
    priv_src, priv_dst = ei[0][priv], ei[1][priv]
    priv_type = et[priv]

    # Cạnh được lưu ở CẢ HAI chiều, nên đầu nút user có thể nằm ở src hoặc
    # dst. Xác định đầu nào là user bằng khoảng chỉ số [0, n_users).
    owner = np.empty(priv_src.size, dtype=np.int32)
    for i in range(priv_src.size):
        a, b = int(priv_src[i]), int(priv_dst[i])
        user_node = a if a < n_users else b
        other = b if user_node == a else a
        if priv_type[i] == 2:            # user–skill: chủ sở hữu là client của user
            owner[i] = usr_client[user_node]
        else:                             # user–job: chủ sở hữu là client của job
            owner[i] = job_client[other - n_users]

    parts = GraphParts(
        n_nodes=data["n_nodes"], n_users=n_users, n_jobs=data["n_jobs"],
        pub_src=pub_src, pub_dst=pub_dst,
        priv_src=priv_src, priv_dst=priv_dst, priv_owner=owner,
        n_clients=n_clients,
    )
    return parts, usr_client


# =====================================================================
# 1. Huấn luyện tập trung
# =====================================================================
def train_centralized(data: dict, cfg: dict, *, arch: str = "lightgcn",
                      seed: int = 42) -> dict[str, torch.Tensor]:
    set_seed(seed)
    g = cfg["medajob"]["graph"]
    mcfg = cfg["medajob"]["train"]
    n_nodes, n_users, n_jobs = data["n_nodes"], data["n_users"], data["n_jobs"]

    model = (LightGCN(n_nodes, dim=g["dim"], layers=g["layers"]) if arch == "lightgcn"
             else GraphSAGE(n_nodes, dim=g["dim"], layers=g["layers"]))
    src, dst, inv_deg = build_norm(data["edge_index"][0], data["edge_index"][1], n_nodes)
    opt = torch.optim.Adam(model.parameters(), lr=float(mcfg["lr"]))

    ui, ji = np.where(data["Mtr"])
    uu = torch.tensor(ui, dtype=torch.long)
    jj = torch.tensor(ji, dtype=torch.long) + n_users
    n = uu.numel()

    model.train()
    for _ in range(int(mcfg["epochs"])):
        opt.zero_grad()
        emb = model.encode(src, dst, inv_deg)
        neg = torch.randint(n_users, n_users + n_jobs, (n,))
        from src.medajob.models import bpr_loss
        loss = bpr_loss(emb, uu, jj, neg, reg=float(mcfg["reg"]))
        loss.backward()
        opt.step()
    return {k: v.detach().clone() for k, v in model.state_dict().items()}


def scores_from_state(state: dict[str, torch.Tensor], data: dict,
                      cfg: dict, n_users: int, n_jobs: int,
                      arch: str = "lightgcn") -> np.ndarray:
    """Tính ma trận điểm (n_users × n_jobs) từ state_dict."""
    g = cfg["medajob"]["graph"]
    n_nodes = data["n_nodes"]
    if arch == "lightgcn":
        model = LightGCN(n_nodes, dim=g["dim"], layers=g["layers"])
    else:
        model = GraphSAGE(n_nodes, dim=g["dim"], layers=g["layers"])
    model.load_state_dict(state)
    model.eval()
    src, dst, inv_deg = build_norm(data["edge_index"][0], data["edge_index"][1], n_nodes)
    with torch.no_grad():
        emb = model.encode(src, dst, inv_deg)
        s = emb[:n_users] @ emb[n_users:n_users + n_jobs].T
    return s.cpu().numpy()


# =====================================================================
# 2. Local-only
# =====================================================================
def train_local_only(data: dict, parts: GraphParts, usr_client: np.ndarray,
                     cfg: dict, seed: int = 42) -> np.ndarray:
    """Mỗi client tự train, KHÔNG chia sẻ gì. Điểm của user lấy từ mô hình
    của client sở hữu user đó."""
    set_seed(seed)
    g = cfg["medajob"]["graph"]
    mcfg = cfg["medajob"]["train"]
    n_nodes, n_users, n_jobs = data["n_nodes"], data["n_users"], data["n_jobs"]
    out = np.zeros((n_users, n_jobs), dtype=np.float32)

    for c in range(parts.n_clients):
        users = np.where(usr_client == c)[0]
        if users.size == 0:
            continue
        sub = data["Mtr"][users]
        ui, ji = np.where(sub)
        if ui.size == 0:
            continue

        model = LightGCN(n_nodes, dim=g["dim"], layers=g["layers"])
        src, dst, inv_deg = build_norm(*parts.edges_for_client(c), n_nodes)
        opt = torch.optim.Adam(model.parameters(), lr=float(mcfg["lr"]))
        uu = torch.tensor(users[ui], dtype=torch.long)
        jj = torch.tensor(ji, dtype=torch.long) + n_users
        n = uu.numel()

        model.train()
        for _ in range(int(mcfg["epochs"])):
            opt.zero_grad()
            emb = model.encode(src, dst, inv_deg)
            neg = torch.randint(n_users, n_users + n_jobs, (n,))
            from src.medajob.models import bpr_loss
            loss = bpr_loss(emb, uu, jj, neg, reg=float(mcfg["reg"]))
            loss.backward()
            opt.step()

        model.eval()
        with torch.no_grad():
            emb = model.encode(src, dst, inv_deg)
            out[users] = (emb[users] @ emb[n_users:n_users + n_jobs].T).cpu().numpy()
    return out


# =====================================================================
# 3. Main
# =====================================================================
def main() -> dict:
    setup_console()
    cfg = load_config()
    set_seed(int(cfg["seed"]))
    banner("BÀI TOÁN 1 — GNN + FEDERATED LEARNING CHO GỢI Ý VIỆC LÀM")

    data = load_artifacts(cfg)
    n_users, n_jobs = data["n_users"], data["n_jobs"]
    m = cfg["medajob"]
    k_list = tuple(int(k) for k in m["k_list"])
    thr = float(m["relevant_threshold"])
    boot = m["bootstrap"]

    def ev(scores: np.ndarray, name: str) -> dict:
        r = evaluate_ranking(scores, data["test"], data["Mtr"],
                             k_list=k_list, relevant_threshold=thr,
                             n_boot=int(boot["n_boot"]), seed=int(cfg["seed"]))
        r["system"] = name
        return r

    results: dict = {"systems": {}, "protocol": {}, "config": {
        "k_list": list(k_list), "relevant_threshold": thr,
        "n_eval_users": int(data["meta"]["clean"]["users_in_test"]),
    }}

    # --- 3.1 Ba baseline ---------------------------------------------
    step("Baseline: Popularity, SkillCBF, ItemKNN")
    job_skills = [str(s).split("|") if isinstance(s, str) else []
                  for s in data["jobs"]["skills"].fillna("")]
    user_skills = [str(s).split("|") if isinstance(s, str) else []
                   for s in data["users"]["skills"].fillna("")]
    job_skills = [[x for x in row if x] for row in job_skills]
    user_skills = [[x for x in row if x] for row in user_skills]

    results["systems"]["popularity"] = ev(popularity_scores(data["train"]), "Popularity")
    results["systems"]["skill_cbf"] = ev(skill_cbf_scores(job_skills, user_skills), "SkillCBF")
    results["systems"]["item_knn"] = ev(item_knn_scores(data["train"]), "ItemKNN")
    for key in ("popularity", "skill_cbf", "item_knn"):
        r = results["systems"][key]
        step(f"  {r['system']:<14} R@20={r.get('recall@20', float('nan')):.4f} "
             f"NDCG@20={r.get('ndcg@20', float('nan')):.4f}")

    # --- 3.2 Centralized ---------------------------------------------
    step("Huấn luyện tập trung (mốc trên lý thuyết)")
    t0 = time.perf_counter()
    state_c = train_centralized(data, cfg, arch="lightgcn", seed=int(cfg["seed"]))
    sec_c = time.perf_counter() - t0
    sc = scores_from_state(state_c, data, cfg, n_users, n_jobs)
    results["systems"]["centralized"] = ev(sc, "Centralized GNN")
    results["systems"]["centralized"]["train_seconds"] = round(sec_c, 2)
    results["systems"]["centralized"]["n_params"] = int(
        state_dict_bytes(state_c) // 4)
    step(f"  Centralized   R@20={results['systems']['centralized']['recall@20']:.4f} "
         f"NDCG@20={results['systems']['centralized']['ndcg@20']:.4f} ({sec_c:.1f}s)")

    # ablation kiến trúc
    step("Ablation: GraphSAGE thay LightGCN")
    state_g = train_centralized(data, cfg, arch="graphsage", seed=int(cfg["seed"]))
    sg = scores_from_state(state_g, data, cfg, n_users, n_jobs, arch="graphsage")
    results["systems"]["centralized_sage"] = ev(sg, "Centralized GraphSAGE")
    step(f"  GraphSAGE     R@20={results['systems']['centralized_sage']['recall@20']:.4f}")

    # --- 3.3 Quét số client ------------------------------------------
    step("Quét số client: local-only vs FedAvg")
    n_clients_list = [int(c) for c in m["federated"]["n_clients"]]
    fed_cfg = m["federated"]
    sweep: list[dict] = []

    for n_clients in n_clients_list:
        parts, usr_client = build_parts(data, n_clients)

        loc = train_local_only(data, parts, usr_client, cfg, seed=int(cfg["seed"]))
        r_loc = ev(loc, f"Local-only (C={n_clients})")

        def eval_fn(state, _data=data, _cfg=cfg):
            s = scores_from_state(state, _data, _cfg, n_users, n_jobs)
            return evaluate_ranking(s, _data["test"], _data["Mtr"],
                                    k_list=k_list, relevant_threshold=thr,
                                    n_boot=200, seed=int(_cfg["seed"]))

        g = m["graph"]
        state_f, logs, info = run_federated(
            parts, data["train"], usr_client, g,
            rounds=int(fed_cfg["rounds"]),
            local_epochs=int(fed_cfg["local_epochs"]),
            lr=float(fed_cfg["lr"]),
            dim=int(g["dim"]), layers=int(g["layers"]),
            reg=float(m["train"]["reg"]),
            mu=0.0,
            sample_rate=float(fed_cfg["sample_rate"]),
            eval_fn=eval_fn,
            seed=int(cfg["seed"]),
        )
        cur = [lg.metrics.get("recall@20", float("nan")) for lg in logs]
        best_i = int(np.nanargmax(cur)) if logs else 0
        s_final = scores_from_state(state_f, data, cfg, n_users, n_jobs)
        r_fed_final = ev(s_final, f"FedAvg (C={n_clients}, final)")
        r_fed_best = dict(logs[best_i].metrics) if logs else {}
        r_fed_best["system"] = f"FedAvg (C={n_clients}, best round)"

        sweep.append({
            "n_clients": n_clients,
            "local_only": r_loc,
            "fedavg_final": r_fed_final,
            "fedavg_best": r_fed_best,
            "curve": [{"round": lg.round,
                       "recall@20": lg.metrics.get("recall@20"),
                       "ndcg@20": lg.metrics.get("ndcg@20"),
                       "mrr@20": lg.metrics.get("mrr@20"),
                       "train_loss": lg.mean_train_loss,
                       "up_bytes": lg.up_bytes} for lg in logs],
            "fl_info": info,
            "client_sizes": {
                "jobs_per_client": np.bincount(
                    (data["client_of_job"] % n_clients)).tolist(),
                "users_per_client": np.bincount(usr_client).tolist(),
            },
        })
        step(f"  C={n_clients:2d}  local R@20={r_loc['recall@20']:.4f} | "
             f"FedAvg final={r_fed_final['recall@20']:.4f} "
             f"best={cur[best_i]:.4f} (vòng {best_i + 1})")

        if n_clients == n_clients_list[0]:
            results["systems"]["local_only"] = r_loc
            results["systems"]["fedavg"] = r_fed_final
            results["systems"]["fedavg_best"] = r_fed_best

    results["client_sweep"] = sweep

    # --- 3.4 FedProx ------------------------------------------------
    step("FedProx (mu>0) — chống trôi cục bộ")
    n_prox = n_clients_list[0]
    parts, usr_client = build_parts(data, n_prox)
    g = m["graph"]

    def eval_fn2(state, _data=data, _cfg=cfg):
        s = scores_from_state(state, _data, _cfg, n_users, n_jobs)
        return evaluate_ranking(s, _data["test"], _data["Mtr"],
                                k_list=k_list, relevant_threshold=thr,
                                n_boot=200, seed=int(_cfg["seed"]))

    state_p, logs_p, info_p = run_federated(
        parts, data["train"], usr_client, g,
        rounds=int(fed_cfg["rounds"]),
        local_epochs=int(fed_cfg["local_epochs"]),
        lr=float(fed_cfg["lr"]),
        dim=int(g["dim"]), layers=int(g["layers"]),
        reg=float(m["train"]["reg"]),
        mu=float(fed_cfg["fedprox_mu"]),
        sample_rate=float(fed_cfg["sample_rate"]),
        eval_fn=eval_fn2,
        seed=int(cfg["seed"]),
    )
    sp = scores_from_state(state_p, data, cfg, n_users, n_jobs)
    results["systems"]["fedprox"] = ev(sp, "FedProx")
    cur_p = [lg.metrics.get("recall@20", float("nan")) for lg in logs_p]
    results["fedprox_curve"] = [{"round": lg.round,
                                 "recall@20": lg.metrics.get("recall@20"),
                                 "ndcg@20": lg.metrics.get("ndcg@20"),
                                 "mrr@20": lg.metrics.get("mrr@20")} for lg in logs_p]
    step(f"  FedProx final R@20={results['systems']['fedprox']['recall@20']:.4f} "
         f"best={np.nanmax(cur_p):.4f}")

    # --- 3.5 Chi phí truyền thông ------------------------------------
    fl0 = sweep[0]["fl_info"]
    raw_b = raw_data_bytes(data["train"])
    up_b = fl0["up_bytes_total"]
    # Điểm hoà vốn: FL gửi O(n_nodes × dim) byte MỖI VÒNG, không phụ thuộc
    # số tương tác. Dữ liệu thô thì tỉ lệ với số tương tác. Với tập rất nhỏ
    # này (249 tương tác) FL tốn byte HƠN tập trung; nhưng payload không
    # chứa bản ghi cá nhân nào. Báo cáo cả hai chiều cho trung thực.
    bytes_per_interaction = 12
    crossover_interactions = int(round(
        up_b / bytes_per_interaction)) if up_b else 0
    results["communication"] = {
        "param_bytes_per_transfer": fl0["param_bytes_per_transfer"],
        "n_params": fl0["param_bytes_per_transfer"] // 4,
        "up_bytes_total": up_b,
        "mean_up_bytes_per_round": fl0["mean_up_bytes_per_round"],
        "raw_data_bytes_if_centralized": raw_b,
        "n_rounds": fl0["rounds_run"],
        "n_clients": fl0["n_clients"],
        "ratio_up_vs_raw": up_b / max(raw_b, 1),
        "crossover_interactions": crossover_interactions,
        "raw_bytes_per_interaction": bytes_per_interaction,
        "interpretation": (
            "FL tốn NHIỀU byte hơn gửi dữ liệu thô ở quy mô này "
            f"({up_b / 1024:.0f} KB tham số so với {raw_b / 1024:.1f} KB "
            f"dữ liệu thô) vì payload là O(số nút × số chiều) và không phụ "
            "thuộc số tương tác. Lợi ích của FL ở đây KHÔNG phải băng thông "
            "mà là dữ liệu gốc không rời khỏi client. FL chỉ rẻ hơn về byte "
            f"khi tập dữ liệu vượt khoảng {crossover_interactions:,} tương tác."
        ),
    }
    step(f"  Truyền thông: {up_b / 1024:.0f} KB tham số so với "
         f"{raw_b / 1024:.1f} KB dữ liệu thô "
         f"(hoà vốn ở ~{crossover_interactions:,} tương tác)")

    # --- 3.6 Ghi kết quả --------------------------------------------
    results["data_summary"] = {
        "n_users": int(n_users), "n_jobs": int(n_jobs),
        "n_skills": int(data["meta"]["clean"]["skills"]),
        "n_industries": int(data["meta"]["clean"]["industries"]),
        "n_train": int(data["Mtr"].sum()), "n_test": int(data["Mte"].sum()),
        "users_in_test": int(data["meta"]["clean"]["users_in_test"]),
        "n_employers": int(data["meta"]["n_employers"]),
        "sparsity_pct": data["meta"]["sparsity_pct"],
        "quality": data["meta"]["quality"],
        "industry_counts": data["meta"]["graph"]["industry_counts"],
        "public_edges": int(data["meta"]["graph"]["public_edges"]),
        "private_edges": int(data["meta"]["graph"]["private_edges"]),
    }
    out = Path(cfg["paths"]["results"]) / "reco_main.json"
    save_json(out, results)
    banner("XONG BÀI TOÁN 1")
    step(f"Đã ghi {out}")
    return results


if __name__ == "__main__":
    main()
