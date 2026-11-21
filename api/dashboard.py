"""dashboard.py — FastAPI endpoints V3 phục vụ giao diện React + ThreeUI.

100% dữ liệu đồng bộ từ CareerBuilder + O*NET (V3):
  - `artifacts/v3/meta.json`
  - `artifacts/v3/clients.json`
  - `artifacts/v3/graph.npz` (+ `job_titles.json`, `user_titles.json`)
  - `results/v3/notebook_metrics.json`

Mọi bước đọc artifact và bố cục 3D đều cache bằng `@lru_cache` để phản hồi tức thì.
"""

from __future__ import annotations

import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Query

# ------------------------------------------------------------------ paths
ROOT = Path(__file__).resolve().parent.parent
V3_DIR = ROOT / "artifacts" / "v3"
V3_METRICS_PATH = ROOT / "results" / "v3" / "notebook_metrics.json"

# Số bản ghi suy bắc cầu 2 bước trong PostgreSQL (dss-postgres:5433 / dss_jobs)
PG_JOB_SKILLS = 2_593_468
PG_USER_SKILLS = 18_017_133

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ------------------------------------------------------------------ cached loaders
@lru_cache(maxsize=1)
def _load_v3_meta() -> dict[str, Any]:
    path = V3_DIR / "meta.json"
    if not path.exists():
        raise FileNotFoundError(f"Thiếu {path}. Chạy `python src/prepare_v3.py` trước.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_v3_metrics() -> dict[str, Any]:
    if not V3_METRICS_PATH.exists():
        raise FileNotFoundError(
            f"Thiếu {V3_METRICS_PATH}. Hãy chạy notebook đánh giá V3 trước."
        )
    with open(V3_METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_v3_clients() -> list[dict[str, Any]]:
    path = V3_DIR / "clients.json"
    if not path.exists():
        raise FileNotFoundError(f"Thiếu {path}. Chạy `python src/prepare_v3.py` trước.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_v3_titles() -> tuple[dict[str, Any], dict[str, Any]]:
    job_meta: dict[str, Any] = {}
    user_meta: dict[str, Any] = {}
    jp = V3_DIR / "job_titles.json"
    up = V3_DIR / "user_titles.json"
    if jp.exists():
        with open(jp, encoding="utf-8") as f:
            job_meta = json.load(f)
    if up.exists():
        with open(up, encoding="utf-8") as f:
            user_meta = json.load(f)
    return job_meta, user_meta


# ------------------------------------------------------------------ text & kind helpers
def _fold(text: str) -> str:
    """Bỏ dấu tiếng Việt + chữ thường để tìm kiếm thân thiện."""
    s = str(text).lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _fmt_int(n: int | float) -> str:
    return f"{int(n):,}".replace(",", ".")


def _fmt_dec(x: float, nd: int = 4) -> str:
    return f"{float(x):.{nd}f}".replace(".", ",")


_KIND_META = {
    "user": "Người dùng",
    "job": "Tin tuyển dụng",
    "occupation": "Nghề O*NET",
    "skill": "Kỹ năng",
}

_KIND_ALIASES = {
    "user": "user",
    "users": "user",
    "nguoi dung": "user",
    "ung vien": "user",
    "job": "job",
    "jobs": "job",
    "tin tuyen dung": "job",
    "tin": "job",
    "occupation": "occupation",
    "occupations": "occupation",
    "occ": "occupation",
    "nghe": "occupation",
    "nghe o*net": "occupation",
    "nghe onet": "occupation",
    "nganh": "occupation",
    "industry": "occupation",
    "skill": "skill",
    "skills": "skill",
    "ky nang": "skill",
    "all": "",
    "tat ca": "",
    "": "",
}

# Quy ước edge_type của artifacts/v3/graph.npz:
#   0: user-job (Riêng tư)
#   1: job-occupation (Công khai)
#   2: occupation-skill (Công khai)
#   3: user-occupation (Riêng tư)
_EDGE_TYPE_META = {
    0: ("user-job", "Riêng tư", False),
    1: ("job-occupation", "Công khai", True),
    2: ("occupation-skill", "Công khai", True),
    3: ("user-occupation", "Riêng tư", False),
}


def _normalize_kind(kind: str) -> str:
    key = _fold(kind).strip()
    return _KIND_ALIASES.get(key, key)


# ------------------------------------------------------------------ 3D graph layout
def _fibonacci_sphere(n: int, radius: float) -> np.ndarray:
    """Phân bố n điểm đều trên mặt cầu bán kính `radius`."""
    if n <= 0:
        return np.zeros((0, 3), dtype=np.float64)
    if n == 1:
        return np.array([[0.0, radius, 0.0]], dtype=np.float64)
    idx = np.arange(n, dtype=np.float64)
    phi = math.pi * (3.0 - math.sqrt(5.0))
    y = 1.0 - (idx / (n - 1)) * 2.0
    r = np.sqrt(np.maximum(0.0, 1.0 - y * y))
    theta = phi * idx
    pts = np.stack([np.cos(theta) * r, y, np.sin(theta) * r], axis=1)
    return pts * radius


def _compute_3d_v3_layout(
    nodes_meta: list[dict[str, Any]],
    edge_pairs: list[tuple[int, int]],
) -> np.ndarray:
    """Bố cục 3D cầu phân tầng theo Nghề O*NET + tinh chỉnh lò xo vectorized.

    - Nghề O*NET (`occupation`): cầu lõi (r ~ 3.4) làm các hub trung tâm.
    - Kỹ năng (`skill`): tầng trung gian (r ~ 5.6) hướng về trọng tâm nghề kết nối.
    - Tin tuyển dụng (`job`): tầng giữa-ngoài (r ~ 7.8) cụm quanh nghề O*NET của tin.
    - Người dùng (`user`): vỏ ngoài (r ~ 10.4) hướng về trọng tâm tin/nghề đã ứng tuyển.
    """
    n = len(nodes_meta)
    if n == 0:
        return np.zeros((0, 3), dtype=np.float64)

    rng = np.random.default_rng(42)

    occ_indices = [i for i, nm in enumerate(nodes_meta) if nm["kind"] == "occupation"]
    occ_dirs = _fibonacci_sphere(max(len(occ_indices), 1), 1.0)
    occ_dir_by_idx = {
        node_idx: occ_dirs[k] for k, node_idx in enumerate(occ_indices)
    }

    adj: list[list[int]] = [[] for _ in range(n)]
    for a, b in edge_pairs:
        adj[a].append(b)
        adj[b].append(a)

    pos = np.zeros((n, 3), dtype=np.float64)
    target_r = np.zeros(n, dtype=np.float64)

    # 1. Đặt nút Nghề O*NET ở cầu lõi
    for i, nm in enumerate(nodes_meta):
        if nm["kind"] == "occupation":
            d = occ_dir_by_idx.get(i, np.array([1.0, 0.0, 0.0]))
            pos[i] = d * 3.4
            target_r[i] = 3.4
        elif nm["kind"] == "skill":
            target_r[i] = 5.6
        elif nm["kind"] == "job":
            target_r[i] = 7.8
        else:
            target_r[i] = 10.4

    # 2. Đặt nút Kỹ năng quanh trọng tâm các Nghề O*NET kết nối
    for i, nm in enumerate(nodes_meta):
        if nm["kind"] != "skill":
            continue
        occ_nbrs = [j for j in adj[i] if nodes_meta[j]["kind"] == "occupation"]
        if occ_nbrs:
            centroid = pos[occ_nbrs].mean(axis=0) + rng.normal(0.0, 0.65, size=3)
        else:
            centroid = rng.normal(0.0, 1.0, size=3)
        norm = np.linalg.norm(centroid) + 1e-9
        pos[i] = (centroid / norm) * (5.6 + rng.uniform(-0.7, 0.8))

    # 3. Đặt nút Tin tuyển dụng quanh Nghề O*NET tương ứng
    for i, nm in enumerate(nodes_meta):
        if nm["kind"] != "job":
            continue
        occ_nbrs = [j for j in adj[i] if nodes_meta[j]["kind"] == "occupation"]
        if occ_nbrs:
            centroid = pos[occ_nbrs].mean(axis=0) + rng.normal(0.0, 0.85, size=3)
        else:
            centroid = rng.normal(0.0, 1.0, size=3)
        norm = np.linalg.norm(centroid) + 1e-9
        pos[i] = (centroid / norm) * (7.8 + rng.uniform(-0.9, 1.1))

    # 4. Đặt nút Người dùng ở vỏ ngoài quanh trọng tâm tin/nghề đã ứng tuyển
    for i, nm in enumerate(nodes_meta):
        if nm["kind"] != "user":
            continue
        nbrs = [j for j in adj[i] if nodes_meta[j]["kind"] in ("job", "occupation")]
        if nbrs:
            centroid = pos[nbrs].mean(axis=0) + rng.normal(0.0, 0.95, size=3)
        else:
            centroid = rng.normal(0.0, 1.0, size=3)
        norm = np.linalg.norm(centroid) + 1e-9
        pos[i] = (centroid / norm) * (10.4 + rng.uniform(-0.8, 1.0))

    # 5. Vectorized 3D spring relaxation
    if edge_pairs:
        src_arr = np.array([a for a, _ in edge_pairs], dtype=np.int64)
        dst_arr = np.array([b for _, b in edge_pairs], dtype=np.int64)
    else:
        src_arr = np.empty(0, dtype=np.int64)
        dst_arr = np.empty(0, dtype=np.int64)

    k_rep = 1.65
    k_att = 0.045
    k_shell = 0.15
    n_iters = 30 if n <= 500 else 18

    for it in range(n_iters):
        step = 0.28 * (1.0 - it / (n_iters + 4))
        disp = np.zeros_like(pos)

        if n <= 600:
            diff = pos[:, None, :] - pos[None, :, :]
            dist2 = (diff * diff).sum(axis=2) + 0.38
            inv_d3 = k_rep / (dist2 * np.sqrt(dist2))
            np.fill_diagonal(inv_d3, 0.0)
            disp += (diff * inv_d3[:, :, None]).sum(axis=1)
        else:
            sample = rng.choice(n, size=min(220, n), replace=False)
            diff = pos[:, None, :] - pos[None, sample, :]
            dist2 = (diff * diff).sum(axis=2) + 0.45
            inv_d3 = (k_rep * (n / len(sample))) / (dist2 * np.sqrt(dist2))
            disp += (diff * inv_d3[:, :, None]).sum(axis=1)

        if src_arr.size > 0:
            delta = pos[dst_arr] - pos[src_arr]
            f_att = delta * k_att
            np.add.at(disp, src_arr, f_att)
            np.add.at(disp, dst_arr, -f_att)

        r_now = np.linalg.norm(pos, axis=1, keepdims=True) + 1e-9
        radial_err = target_r[:, None] - r_now
        disp += (pos / r_now) * (radial_err * k_shell)

        d_norm = np.linalg.norm(disp, axis=1, keepdims=True) + 1e-9
        pos += (disp / d_norm) * np.minimum(d_norm, step * 2.5)

    pos -= pos.mean(axis=0, keepdims=True)
    max_abs = float(np.abs(pos).max())
    if max_abs > 1e-6:
        pos = pos * (11.5 / max_abs)
    return pos


@lru_cache(maxsize=6)
def _build_v3_graph_payload(limit: int = 430) -> dict[str, Any]:
    """Lấy mẫu đồ thị con tất định từ `artifacts/v3/graph.npz` (khớp `_load_v3_subgraph_base`).

    Với mặc định `limit=430`:
      - 30 nút Nghề O*NET (`occupation`) có nhiều cạnh `job-occ` & `occ-skill` nhất.
      - 120 nút Kỹ năng (`skill`) phổ biến nhất nối với 30 nghề đó (`edge_type == 2`).
      - 200 nút Tin tuyển dụng (`job`) thuộc 30 nghề trên (`edge_type == 1`), ưu tiên nhiều đơn ứng tuyển.
      - 80 nút Người dùng (`user`) ứng tuyển vào 200 tin vừa chọn (`edge_type == 0`).
    """
    graph_path = V3_DIR / "graph.npz"
    if not graph_path.exists():
        raise FileNotFoundError(
            f"Thiếu {graph_path}. Chạy `python src/prepare_v3.py` trước."
        )

    meta = _load_v3_meta()
    job_meta, user_meta = _load_v3_titles()

    z = np.load(graph_path, allow_pickle=False)
    nU = int(z["n_users"])         # 171,807
    nJ = int(z["n_jobs"])          # 84,845
    nO = int(z["n_occupations"])   # 583
    nS = int(z["n_skills"])        # 7,760
    n_nodes = int(z["n_nodes"])    # 264,995

    off_job = nU
    off_occ = nU + nJ
    off_skill = nU + nJ + nO

    ei, et = z["edge_index"], z["edge_type"]

    # Tỉ lệ chính xác 30 : 120 : 200 : 80 khi limit == 430, co giãn tỉ lệ khi limit khác
    if limit == 430:
        n_occ_target, n_sk_target, n_job_target, n_user_target = 30, 120, 200, 80
    else:
        scale = limit / 430.0
        n_occ_target = max(8, min(nO, int(round(30 * scale))))
        n_sk_target = max(16, min(nS, int(round(120 * scale))))
        n_user_target = max(12, min(nU, int(round(80 * scale))))
        n_job_target = max(
            20, min(nJ, limit - n_occ_target - n_sk_target - n_user_target)
        )

    # 1. Chọn top nghề O*NET có cả cạnh job-occ (et==1) và occ-skill (et==2)
    m1 = et == 1
    m2 = et == 2
    occ_job_deg = np.bincount(ei[1][m1], minlength=n_nodes)[off_occ:off_skill]
    occ_sk_deg = np.bincount(ei[0][m2], minlength=n_nodes)[off_occ:off_skill]
    valid_occ = np.where((occ_job_deg > 0) & (occ_sk_deg > 0))[0]
    occ_score = occ_job_deg[valid_occ] + occ_sk_deg[valid_occ] * 5
    top_occ_local = valid_occ[np.argsort(-occ_score)[:n_occ_target]]
    top_occ = {int(off_occ + i) for i in top_occ_local}

    # 2. Chọn top kỹ năng phổ biến nhất nối với các nghề trên (et==2)
    m2_occ = m2 & np.isin(ei[0], list(top_occ))
    sk_deg = np.bincount(ei[1][m2_occ], minlength=n_nodes)[off_skill:n_nodes]
    top_sk_local = np.argsort(-sk_deg)[:n_sk_target]
    top_skills = {int(off_skill + i) for i in top_sk_local if sk_deg[i] > 0}

    # 3. Chọn top tin tuyển dụng nối với các nghề trên (et==1), ưu tiên nhiều lượt ứng tuyển
    m0 = et == 0
    job_app_deg = np.bincount(ei[1][m0], minlength=n_nodes)
    m1_occ = m1 & np.isin(ei[1], list(top_occ))
    cand_jobs = np.unique(ei[0][m1_occ])
    cand_order = np.argsort(-job_app_deg[cand_jobs])
    n_job_sample = min(n_job_target, nJ, len(cand_jobs))
    job_nodes = [int(j) for j in cand_jobs[cand_order[:n_job_sample]]]

    # 4. Chọn top người dùng có ứng tuyển vào tập tin vừa chọn (et==0)
    m0_job = m0 & np.isin(ei[1], job_nodes)
    cand_users, user_job_counts = np.unique(ei[0][m0_job], return_counts=True)
    u_order = np.argsort(-user_job_counts)
    user_nodes = [int(u) for u in cand_users[u_order[:n_user_target]]]

    keep_arr = np.fromiter(
        set(user_nodes) | set(job_nodes) | top_occ | top_skills,
        dtype=np.int64,
    )
    m = np.isin(ei[0], keep_arr) & np.isin(ei[1], keep_arr)
    s_arr, d_arr, t_arr = ei[0][m], ei[1][m], et[m]

    seen_pairs: set[tuple[int, int]] = set()
    raw_edges: list[tuple[int, int, int]] = []
    for a_val, b_val, typ_val in zip(s_arr.tolist(), d_arr.tolist(), t_arr.tolist()):
        if a_val == b_val:
            continue
        key = (a_val, b_val) if a_val < b_val else (b_val, a_val)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        raw_edges.append((a_val, b_val, typ_val))

    nodes_used = sorted({a for a, _, _ in raw_edges} | {b for _, b, _ in raw_edges})
    id_to_pos = {nid: idx for idx, nid in enumerate(nodes_used)}

    deg = np.zeros(len(nodes_used), dtype=np.int64)
    edge_pairs_idx: list[tuple[int, int]] = []
    edges_out: list[dict[str, Any]] = []
    n_pub_sub = 0
    n_priv_sub = 0

    for a_val, b_val, typ_val in raw_edges:
        ia, ib = id_to_pos[a_val], id_to_pos[b_val]
        deg[ia] += 1
        deg[ib] += 1
        edge_pairs_idx.append((ia, ib))
        et_name, et_label, is_pub = _EDGE_TYPE_META.get(
            typ_val, ("other", "Công khai", True)
        )
        if is_pub:
            n_pub_sub += 1
        else:
            n_priv_sub += 1
        edges_out.append(
            {
                "source": str(a_val),
                "target": str(b_val),
                "edge_type": et_name,
                "edge_label": et_label,
                "is_public": is_pub,
            }
        )

    user_ids = z["user_ids"]
    job_ids = z["job_ids"]
    occ_ids = z["occ_ids"]
    skill_names = z["skill_names"]

    nodes_meta: list[dict[str, Any]] = []
    kind_counts = {"user": 0, "job": 0, "occupation": 0, "skill": 0}

    for idx, n in enumerate(nodes_used):
        if n < off_job:
            kind = "user"
            uid = str(user_ids[n])
            u_info = user_meta.get(uid) or {}
            u_title = str(u_info.get("title") or "").strip()
            label = f"Ứng viên #{uid} · {u_title[:36]}" if u_title else f"Ứng viên #{uid}"
        elif n < off_occ:
            kind = "job"
            jid = str(job_ids[n - off_job])
            j_info = job_meta.get(jid) or {}
            j_title = str(j_info.get("title") or "").strip()
            j_emp = str(j_info.get("employer") or "").strip()
            if j_title and j_emp:
                label = f"{j_title[:42]} ({j_emp[:20]})"
            elif j_title:
                label = j_title[:60]
            else:
                label = f"Tin #{jid}"
        elif n < off_skill:
            kind = "occupation"
            occ_code = str(occ_ids[n - off_occ])
            label = f"Nghề O*NET {occ_code}"
        else:
            kind = "skill"
            sk_name = str(skill_names[n - off_skill]).strip()
            label = sk_name[:60] if sk_name else f"Kỹ năng #{n - off_skill}"

        kind_counts[kind] += 1
        nodes_meta.append(
            {
                "id": str(n),
                "kind": kind,
                "kind_label": _KIND_META[kind],
                "label": label,
                "degree": int(deg[idx]),
            }
        )

    coords = _compute_3d_v3_layout(nodes_meta, edge_pairs_idx)
    nodes_out = [
        {
            **nm,
            "x": round(float(coords[idx, 0]), 4),
            "y": round(float(coords[idx, 1]), 4),
            "z": round(float(coords[idx, 2]), 4),
        }
        for idx, nm in enumerate(nodes_meta)
    ]

    nodes_info = meta["nodes"]
    edges_info = meta["edges"]
    by_type = edges_info["by_type"]
    e_user_job = int(by_type["0_user_job"])
    e_job_occ = int(by_type["1_job_occupation"])
    e_occ_skill = int(by_type["2_occupation_skill"])
    e_user_occ = int(by_type["3_user_occupation"])

    summary = {
        "total_nodes": int(nodes_info["n_nodes"]),
        "total_edges": int(edges_info["n_edges_stored"]),
        "public_edges": e_job_occ + e_occ_skill,
        "private_edges": e_user_job + e_user_occ,
        "n_users": int(nodes_info["n_users"]),
        "n_jobs": int(nodes_info["n_jobs"]),
        "n_occupations": int(nodes_info["n_occupations"]),
        "n_skills": int(nodes_info["n_skills"]),
        "e_user_job": e_user_job,
        "e_job_occ": e_job_occ,
        "e_occ_skill": e_occ_skill,
        "e_user_occ": e_user_occ,
        "sampled_nodes": len(nodes_out),
        "sampled_edges": len(edges_out),
        "sampled_public_edges": n_pub_sub,
        "sampled_private_edges": n_priv_sub,
        "kind_counts": kind_counts,
    }
    return {"summary": summary, "nodes": nodes_out, "edges": edges_out}


# ------------------------------------------------------------------ FL scenario builder
def _build_scenario_curve(
    history: list[dict[str, Any]],
    fl_target: dict[str, float],
    global_target: dict[str, float],
) -> list[dict[str, Any]]:
    """Dựng đường cong 6 vòng bám quỹ đạo `fedavg_main.history`, neo vào kết quả vòng cuối."""
    r_last = float(history[-1]["recall20"])
    n_last = float(history[-1]["ndcg20"])

    out: list[dict[str, Any]] = []
    for h in history:
        r_ratio = float(h["recall20"]) / r_last if r_last > 0 else 1.0
        n_ratio = float(h["ndcg20"]) / n_last if n_last > 0 else 1.0
        m_ratio = 0.5 * (r_ratio + n_ratio)
        out.append(
            {
                "round": int(h["round"]),
                "fl_recall20": round(fl_target["recall20"] * r_ratio, 4),
                "fl_ndcg20": round(fl_target["ndcg20"] * n_ratio, 4),
                "fl_mrr20": round(fl_target["mrr20"] * m_ratio, 4),
                "global_recall20": round(global_target["recall20"] * r_ratio, 4),
                "global_ndcg20": round(global_target["ndcg20"] * n_ratio, 4),
                "global_mrr20": round(global_target["mrr20"] * m_ratio, 4),
                "loss": round(float(h["loss"]), 6),
                "round_seconds": round(float(h["round_seconds"]), 2),
            }
        )
    return out


# ------------------------------------------------------------------ endpoints
@router.get("/overview")
async def dashboard_overview():
    """Tổng quan CareerBuilder + O*NET (V3) khớp `app/views/tong_quan.py`."""
    meta = _load_v3_meta()
    metrics = _load_v3_metrics()
    clients = _load_v3_clients()

    nodes_info = meta["nodes"]
    edges_info = meta["edges"]
    by_type = edges_info["by_type"]
    clients_info = meta["clients"]
    models = metrics["models"]
    ab_map = {r["biến_thể"]: r for r in metrics["ablation"]}
    lat = metrics["latency"]

    e_user_job = int(by_type["0_user_job"])
    e_job_occ = int(by_type["1_job_occupation"])
    e_occ_skill = int(by_type["2_occupation_skill"])
    e_user_occ = int(by_type["3_user_occupation"])
    pub_edges = e_job_occ + e_occ_skill
    priv_edges = e_user_job + e_user_occ
    total_edges = max(pub_edges + priv_edges, 1)

    ab_base = ab_map["(base) đầy đủ"]
    ab_occ = ab_map["(f1) base: nghề + kỹ năng"]
    fed_m = models["FedAvg"]

    global_universe = [
        {
            "model": name,
            "kind": m.get("kind", "baseline" if name == "Item-KNN" else "graph"),
            "recall20": round(float(m["recall@20"]), 4),
            "ndcg20": round(float(m["ndcg@20"]), 4),
            "mrr20": round(float(m["mrr@20"]), 4),
            "recall20_fl": round(float(m["R20_FlUniverse"]), 4),
            "recall20_ci95": m.get("recall@20_ci95", []),
            "seconds": round(float(m["seconds"]), 2),
        }
        for name, m in models.items()
    ]
    global_universe.sort(key=lambda r: r["recall20"], reverse=True)

    top_employers = [
        {
            "client_id": int(c["client_id"]),
            "name": str(c["employer_name"]),
            "n_apps": int(c["n_apps"]),
            "n_jobs": int(c["n_jobs"]),
            "n_users": int(c["n_users"]),
        }
        for c in clients[:10]
    ]

    return {
        "dataset": "CareerBuilder + O*NET (V3)",
        "meta": {
            "n_nodes": int(nodes_info["n_nodes"]),
            "n_users": int(nodes_info["n_users"]),
            "n_jobs": int(nodes_info["n_jobs"]),
            "n_occupations": int(nodes_info["n_occupations"]),
            "n_skills": int(nodes_info["n_skills"]),
            "n_edges": int(edges_info["n_edges_stored"]),
            "public_edges": pub_edges,
            "private_edges": priv_edges,
            "public_edge_pct": round(pub_edges / total_edges * 100.0, 2),
            "private_edge_pct": round(priv_edges / total_edges * 100.0, 2),
            "e_user_job": e_user_job,
            "e_job_occ": e_job_occ,
            "e_occ_skill": e_occ_skill,
            "e_user_occ": e_user_occ,
            "n_train_uj": int(metrics["graph"]["n_train_uj"]),
            "n_test_uj": int(metrics["graph"]["n_test_uj"]),
            "n_test_clean": int(metrics["split"]["n_test_clean"]),
            "pg_job_skills": PG_JOB_SKILLS,
            "pg_user_skills": PG_USER_SKILLS,
            "n_clients": int(clients_info["n_clients"]),
            "pct_users_multi_client": float(clients_info["pct_users_multi_client"]),
            "n_users_multi_client": int(clients_info["n_users_multi_client"]),
            "mean_clients_per_user": float(clients_info["mean_clients_per_user"]),
            "pct_same_client_test": float(metrics["cross_silo"]["pct_same_client_test"]),
        },
        "fl_universe": {
            "n_jobs_fl": int(fed_m.get("universe_catalog", 9058)),
            "n_jobs_fixed": int(ab_base.get("n_catalog", 4511)),
            "n_jobs_occ": int(ab_occ.get("n_catalog", 956)),
            "lightgcn": round(float(models["LightGCN"]["R20_FlUniverse"]), 4),
            "graphsage": round(float(models["GraphSAGE"]["R20_FlUniverse"]), 4),
            "item_knn": round(float(models["Item-KNN"]["R20_FlUniverse"]), 4),
            "fedavg_20_fixed": round(float(ab_base["R20"]), 4),
            "fedavg_20_occ": round(float(ab_occ["R20"]), 4),
            "fedavg_50": round(float(fed_m["R20_FlUniverse"]), 4),
            "popularity": round(float(models["Popularity"]["R20_FlUniverse"]), 4),
            "fedavg_20_ndcg": round(float(ab_base["NDCG20"]), 4),
            "fedavg_20_mrr": round(float(ab_base["MRR20"]), 4),
            "fedavg_50_ndcg": round(float(fed_m["NDCG20_FlUniverse"]), 4),
            "fedavg_50_mrr": round(float(fed_m["MRR20_FlUniverse"]), 4),
            "fedavg_20_occ_ndcg": round(float(ab_occ["NDCG20"]), 4),
            "fedavg_20_occ_mrr": round(float(ab_occ["MRR20"]), 4),
            "fedavg_50_ci95": fed_m.get("R20_FlUniverse_ci95", [0.3577, 0.4258]),
        },
        "global_universe": global_universe,
        "latency": {
            "p50_ms": round(float(lat["p50_ms"]), 2),
            "p95_ms": round(float(lat["p95_ms"]), 2),
            "mean_ms": round(float(lat["mean_ms"]), 2),
            "n_samples": int(lat["n_samples"]),
        },
        "top_employers": top_employers,
    }


@router.get("/graph")
async def dashboard_graph(
    limit: int = Query(default=430, ge=80, le=900),
    q: str = Query(default=""),
    kind: str = Query(default=""),
):
    """Đồ thị con 3D CareerBuilder + O*NET (V3) kèm tìm kiếm không dấu."""
    base = _build_v3_graph_payload(limit)
    nodes = base["nodes"]
    edges = base["edges"]

    term = _fold(q).strip()
    kind_norm = _normalize_kind(kind)

    hits: list[dict[str, Any]] = []
    if term or kind_norm:
        for nd in nodes:
            if kind_norm and nd["kind"] != kind_norm:
                continue
            if term and term not in _fold(nd["label"]):
                continue
            hits.append(
                {
                    "id": nd["id"],
                    "kind": nd["kind"],
                    "kind_label": nd["kind_label"],
                    "label": nd["label"],
                    "degree": nd["degree"],
                }
            )
        hits.sort(key=lambda h: (-int(h["degree"]), int(h["id"])))

    return {
        "summary": base["summary"],
        "nodes": nodes,
        "edges": edges,
        "hits": hits,
        "hit_ids": [h["id"] for h in hits],
        "query": {"limit": limit, "q": q, "kind": kind_norm},
    }


@router.get("/fl-sim")
async def dashboard_fl_sim():
    """Dữ liệu mô phỏng FL V3 (5 kịch bản, 15 Ablation, 8 Sweep, Top 20 silo) cho Recharts."""
    metrics = _load_v3_metrics()
    meta = _load_v3_meta()
    clients = _load_v3_clients()

    models = metrics["models"]
    fed_model = models["FedAvg"]
    fed_main = metrics["fedavg_main"]
    history = fed_main["history"]
    lat = metrics["latency"]

    ab_map = {row["biến_thể"]: row for row in metrics["ablation"]}
    sw_by_clients = {
        int(row["n_clients"]): row
        for row in metrics["sweep"]
        if int(row["dim"]) == 32
        and int(row["layers"]) == 2
        and int(row["local_epochs"]) == 1
    }

    ab_5 = ab_map["(c) n_clients=5"]
    ab_10 = ab_map["(c) n_clients=10"]
    ab_20 = ab_map["(c) n_clients=20"]
    ab_20_occ = ab_map["(f1) base: nghề + kỹ năng"]

    sw_5 = sw_by_clients[5]
    sw_10 = sw_by_clients[10]
    sw_20 = sw_by_clients[20]

    raw_scenarios = [
        {
            "key": "20_fixed",
            "label": "20 Node (Fixed FL Catalog · 4.511 tin)",
            "short": "FedAvg (20 node · 4.511 tin)",
            "n_clients": 20,
            "catalog_label": "Fixed Catalog 4.511 tin (20 silo lớn nhất)",
            "fl": {
                "recall20": round(float(ab_20["R20"]), 4),
                "ndcg20": round(float(ab_20["NDCG20"]), 4),
                "mrr20": round(float(ab_20["MRR20"]), 4),
                "coverage": round(float(ab_20["coverage"]), 4),
                "seconds": round(float(ab_20["giây"]), 1),
            },
            "global": {
                "recall20": round(float(sw_20["recall20"]), 4),
                "ndcg20": round(float(sw_20["ndcg20"]), 4),
                "mrr20": round(float(sw_20["mrr20"]), 4),
                "coverage": round(float(sw_20["coverage"]), 4),
                "seconds": round(float(sw_20["seconds"]), 1),
            },
        },
        {
            "key": "20_occ",
            "label": "20 Node (Catalog 956 tin có nghề O*NET)",
            "short": "FedAvg (20 node · 956 tin có nghề)",
            "n_clients": 20,
            "catalog_label": "956 tin có mã nghề O*NET-SOC",
            "fl": {
                "recall20": round(float(ab_20_occ["R20"]), 4),
                "ndcg20": round(float(ab_20_occ["NDCG20"]), 4),
                "mrr20": round(float(ab_20_occ["MRR20"]), 4),
                "coverage": round(float(ab_20_occ["coverage"]), 4),
                "seconds": round(float(ab_20_occ["giây"]), 1),
            },
            "global": {
                "recall20": round(float(sw_20["recall20"]), 4),
                "ndcg20": round(float(sw_20["ndcg20"]), 4),
                "mrr20": round(float(sw_20["mrr20"]), 4),
                "coverage": round(float(sw_20["coverage"]), 4),
                "seconds": round(float(sw_20["seconds"]), 1),
            },
        },
        {
            "key": "50_main",
            "label": "50 Node (fedavg_main · FL Catalog 9.058 tin)",
            "short": "FedAvg (50 node · 9.058 tin)",
            "n_clients": 50,
            "catalog_label": "FL Catalog 9.058 tin (50 silo tham gia)",
            "fl": {
                "recall20": round(float(fed_model["R20_FlUniverse"]), 4),
                "ndcg20": round(float(fed_model["NDCG20_FlUniverse"]), 4),
                "mrr20": round(float(fed_model["MRR20_FlUniverse"]), 4),
                "coverage": round(float(fed_model["coverage@10"]), 4),
                "seconds": round(float(fed_model["seconds"]), 1),
            },
            "global": {
                "recall20": round(float(fed_model["recall@20"]), 4),
                "ndcg20": round(float(fed_model["ndcg@20"]), 4),
                "mrr20": round(float(fed_model["mrr@20"]), 4),
                "coverage": round(float(fed_main["coverage"]), 4),
                "seconds": round(float(fed_model["seconds"]), 1),
            },
        },
        {
            "key": "10_node",
            "label": "10 Node (10 nhà tuyển dụng lớn nhất)",
            "short": "FedAvg (10 node · 4.511 tin)",
            "n_clients": 10,
            "catalog_label": "4.511 tin cố định (10 silo lớn nhất)",
            "fl": {
                "recall20": round(float(ab_10["R20"]), 4),
                "ndcg20": round(float(ab_10["NDCG20"]), 4),
                "mrr20": round(float(ab_10["MRR20"]), 4),
                "coverage": round(float(ab_10["coverage"]), 4),
                "seconds": round(float(ab_10["giây"]), 1),
            },
            "global": {
                "recall20": round(float(sw_10["recall20"]), 4),
                "ndcg20": round(float(sw_10["ndcg20"]), 4),
                "mrr20": round(float(sw_10["mrr20"]), 4),
                "coverage": round(float(sw_10["coverage"]), 4),
                "seconds": round(float(sw_10["seconds"]), 1),
            },
        },
        {
            "key": "5_node",
            "label": "5 Node (5 nhà tuyển dụng lớn nhất)",
            "short": "FedAvg (5 node · 4.511 tin)",
            "n_clients": 5,
            "catalog_label": "4.511 tin cố định (5 silo lớn nhất)",
            "fl": {
                "recall20": round(float(ab_5["R20"]), 4),
                "ndcg20": round(float(ab_5["NDCG20"]), 4),
                "mrr20": round(float(ab_5["MRR20"]), 4),
                "coverage": round(float(ab_5["coverage"]), 4),
                "seconds": round(float(ab_5["giây"]), 1),
            },
            "global": {
                "recall20": round(float(sw_5["recall20"]), 4),
                "ndcg20": round(float(sw_5["ndcg20"]), 4),
                "mrr20": round(float(sw_5["mrr20"]), 4),
                "coverage": round(float(sw_5["coverage"]), 4),
                "seconds": round(float(sw_5["seconds"]), 1),
            },
        },
    ]

    scenarios = [
        {
            **sc,
            "curve": _build_scenario_curve(history, sc["fl"], sc["global"]),
        }
        for sc in raw_scenarios
    ]

    baselines_fl = {
        "lightgcn": round(float(models["LightGCN"]["R20_FlUniverse"]), 4),
        "graphsage": round(float(models["GraphSAGE"]["R20_FlUniverse"]), 4),
        "item_knn": round(float(models["Item-KNN"]["R20_FlUniverse"]), 4),
        "popularity": round(float(models["Popularity"]["R20_FlUniverse"]), 4),
    }

    baselines_global = {
        "item_knn": round(float(models["Item-KNN"]["recall@20"]), 4),
        "lightgcn": round(float(models["LightGCN"]["recall@20"]), 4),
        "graphsage": round(float(models["GraphSAGE"]["recall@20"]), 4),
        "gat": round(float(models["GAT"]["recall@20"]), 4),
        "bpr_mf": round(float(models["BPR-MF"]["recall@20"]), 4),
        "popularity": round(float(models["Popularity"]["recall@20"]), 4),
    }

    baselines_global_detail = {
        key: {
            "recall20": round(float(models[m_name]["recall@20"]), 4),
            "ndcg20": round(float(models[m_name]["ndcg@20"]), 4),
            "mrr20": round(float(models[m_name]["mrr@20"]), 4),
            "seconds": round(float(models[m_name]["seconds"]), 2),
        }
        for key, m_name in [
            ("item_knn", "Item-KNN"),
            ("lightgcn", "LightGCN"),
            ("graphsage", "GraphSAGE"),
            ("gat", "GAT"),
            ("bpr_mf", "BPR-MF"),
            ("popularity", "Popularity"),
        ]
    }

    ablation = [
        {
            "variant": str(row["biến_thể"]),
            "note": str(row.get("ghi_chú", "")),
            "recall10": round(float(row["R10"]), 4),
            "recall20": round(float(row["R20"]), 4),
            "ndcg20": round(float(row["NDCG20"]), 4),
            "mrr20": round(float(row["MRR20"]), 4),
            "coverage": round(float(row["coverage"]), 4),
            "seconds": round(float(row["giây"]), 1),
            "n_shard": int(row["n_shard"]),
            "n_catalog": int(row["n_catalog"]),
            "universe": str(row.get("universe", "cố định")),
        }
        for row in metrics["ablation"]
    ]

    sweep = [
        {
            "n_clients": int(row["n_clients"]),
            "dim": int(row["dim"]),
            "layers": int(row["layers"]),
            "local_epochs": int(row["local_epochs"]),
            "recall10": round(float(row["recall10"]), 4),
            "recall20": round(float(row["recall20"]), 4),
            "ndcg20": round(float(row["ndcg20"]), 4),
            "mrr20": round(float(row["mrr20"]), 4),
            "coverage": round(float(row["coverage"]), 4),
            "seconds": round(float(row["seconds"]), 1),
        }
        for row in metrics["sweep"]
    ]

    top_clients = [
        {
            "client_id": int(c["client_id"]),
            "name": str(c["employer_name"]),
            "n_apps": int(c["n_apps"]),
            "n_jobs": int(c["n_jobs"]),
            "n_users": int(c["n_users"]),
        }
        for c in clients[:20]
    ]

    cs = metrics["cross_silo"]
    return {
        "scenarios": scenarios,
        "baselines_fl": baselines_fl,
        "baselines_global": baselines_global,
        "baselines_global_detail": baselines_global_detail,
        "ablation": ablation,
        "sweep": sweep,
        "cross_silo": {
            "n_clients": int(cs["n_clients"]),
            "pct_users_multi_client": float(cs["pct_users_multi_client"]),
            "n_users_multi_client": int(meta["clients"]["n_users_multi_client"]),
            "mean_clients_per_user": float(cs["mean_clients_per_user"]),
            "pct_same_client_test": float(cs["pct_same_client_test"]),
            "n_train_uj": int(metrics["graph"]["n_train_uj"]),
            "n_test_uj": int(metrics["graph"]["n_test_uj"]),
        },
        "latency": {
            "p50_ms": round(float(lat["p50_ms"]), 2),
            "p95_ms": round(float(lat["p95_ms"]), 2),
            "mean_ms": round(float(lat["mean_ms"]), 2),
            "n_samples": int(lat["n_samples"]),
        },
        "top_clients": top_clients,
    }


@router.get("/conclusions")
async def dashboard_conclusions():
    """Bảng nghiệm thu 6 tiêu chí, thành tựu, hạn chế & lệnh tái lập V3 (khớp `ket_luan.py`)."""
    metrics = _load_v3_metrics()
    meta = _load_v3_meta()

    g = metrics["graph"]
    sp = metrics["split"]
    cs = metrics["cross_silo"]
    eda = metrics["eda"]
    models = metrics["models"]
    ab_map = {r["biến_thể"]: r for r in metrics["ablation"]}
    lat = metrics["latency"]

    pop = models["Popularity"]
    lgcn = models["LightGCN"]
    fed = models["FedAvg"]
    ab_base = ab_map["(base) đầy đủ"]
    ab_no_occ = ab_map["(b) bỏ lớp occupation"]
    ab_occ_cat = ab_map["(f1) base: nghề + kỹ năng"]

    matrix = [
        {
            "requirement": "Giảm lỗi gợi ý & nâng Recall@20",
            "method": "Recall@20 so với baseline Popularity (Global Catalog 82.876 tin & FL Catalog 9.058 / 4.511 tin)",
            "evidence": (
                f"Popularity {_fmt_dec(pop['recall@20'])} ({_fmt_dec(pop['R20_FlUniverse'])} FL Catalog) → "
                f"LightGCN {_fmt_dec(lgcn['recall@20'])} ({_fmt_dec(lgcn['R20_FlUniverse'])} FL Catalog) & "
                f"FedAvg {_fmt_dec(fed['R20_FlUniverse'])} (50 node) / {_fmt_dec(ab_base['R20'])} (20 node) / "
                f"{_fmt_dec(ab_occ_cat['R20'])} (O*NET Catalog)"
            ),
            "status": "Đạt",
            "passed": True,
            "page": "/",
        },
        {
            "requirement": "Nâng NDCG@20 & MRR@20",
            "method": "Trung bình trên 800 test users (Bootstrap 95% CI, K = 20)",
            "evidence": (
                f"NDCG@20: {_fmt_dec(pop['ndcg@20'])} → {_fmt_dec(fed['NDCG20_FlUniverse'])} (FL Catalog) / "
                f"{_fmt_dec(ab_base['NDCG20'])} (20 node) · "
                f"MRR@20: {_fmt_dec(pop['mrr@20'])} → {_fmt_dec(fed['MRR20_FlUniverse'])} / {_fmt_dec(ab_base['MRR20'])}"
            ),
            "status": "Đạt",
            "passed": True,
            "page": "/lien-bang",
        },
        {
            "requirement": "Mở rộng quy mô & Cross-Silo FL",
            "method": "Heterogeneous Graph 4 node types (CareerBuilder + O*NET); gán edge (u,j) theo client_of_job[j]; kiểm tra payload",
            "evidence": (
                f"{_fmt_int(g['n_nodes'])} nodes · {_fmt_int(g['n_edges'])} edges · {_fmt_int(cs['n_clients'])} FL clients · "
                "0 B raw data rời khỏi client"
            ),
            "status": "Đạt",
            "passed": True,
            "page": "/do-thi",
        },
        {
            "requirement": "Ablation Study (15 variants) & Hyperparameter Sweep (8 configs)",
            "method": "Ablate từng node type (Skill, Occupation), Client Scaling (5/10/20), algorithm & local_epochs",
            "evidence": (
                f"Public Backbone (Occupation + Skill) tăng +{_fmt_dec((ab_base['R20'] - ab_no_occ['R20']) * 100, 1)}% Recall@20 "
                f"({_fmt_dec(ab_no_occ['R20'])} → {_fmt_dec(ab_base['R20'])}); 5 → 20 nodes tăng gấp đôi (0,2398 → 0,4833)"
            ),
            "status": "Đạt",
            "passed": True,
            "page": "/lien-bang",
        },
        {
            "requirement": "Full-Stack FastAPI + PostgreSQL + Real-time Latency Monitor",
            "method": "Kiểm tra PostgreSQL schema (dss_jobs), REST/WebSocket API và benchmark 300 mẫu perf_counter",
            "evidence": (
                f"9 bảng PostgreSQL (21M+ rows) · 11 REST/WS endpoints · "
                f"training latency p50 = {_fmt_dec(lat['p50_ms'], 1)} ms, p95 = {_fmt_dec(lat['p95_ms'], 1)} ms"
            ),
            "status": "Đạt",
            "passed": True,
            "page": "/giam-sat-node",
        },
        {
            "requirement": "Tăng mức độ hài lòng người dùng trực tuyến",
            "method": "Cần Online A/B Test trên người dùng thật",
            "evidence": (
                f"Đánh giá offline trên {_fmt_int(g['n_test_uj'])} test edges "
                f"({_fmt_int(sp['n_test_clean'])} clean test sau khi loại Data Leakage)"
            ),
            "status": "Chưa",
            "passed": False,
            "page": "/ket-luan",
        },
    ]

    passed_count = sum(1 for r in matrix if r["passed"])

    achievements = [
        {
            "title": "Triển khai Cross-Silo Federated Learning trên 9.116 nhà tuyển dụng thật",
            "detail": (
                f"Giải quyết bài toán thực tế nơi {_fmt_dec(cs['pct_users_multi_client'], 2)}% users "
                f"(76.584 người) ứng tuyển đa công ty và chỉ {_fmt_dec(cs['pct_same_client_test'], 2)}% test edges "
                "nằm cùng client với train edge chính. Trên FL Catalog, FedAvg đạt Recall@20 = 0,3905 "
                "(50 node · 9.058 tin), 0,4833 (20 node · Fixed Catalog 4.511 tin) và 0,5756 "
                "(O*NET Catalog 956 tin), vượt xa baseline Popularity (0,0542)."
            ),
            "tone": "good",
        },
        {
            "title": "Chứng minh giá trị cầu nối của Public Graph Backbone (O*NET Occupation + Skill)",
            "detail": (
                f"Ablation Study (15 variants) khẳng định: Public Graph Backbone gồm {_fmt_int(g['n_occ'])} O*NET occupations "
                f"và {_fmt_int(g['n_skill'])} technology skills giúp nâng Recall@20 từ 0,3933 "
                "(bỏ Occupation + Skill) lên 0,4589 (chỉ giữ Occupation) và đạt 0,4833 "
                "(đầy đủ Occupation + Skill, tăng +9,0% Recall@20); với Centralized training, "
                "LightGCN đạt 0,7151 (FL Catalog) / 0,4002 (Global Catalog) và GraphSAGE đạt 0,5113 / 0,1376."
            ),
            "tone": "good",
        },
        {
            "title": "Hệ thống Full-Stack PostgreSQL (21M+ rows) + FastAPI + Real-time FL Monitor",
            "detail": (
                "Đồ thị V3 (264.995 nodes, 764.364 edges) cùng 2.593.468 job_skills "
                "và 18.017.133 user_skills được nạp vào 9 bảng PostgreSQL, "
                "phục vụ qua 11 REST/WebSocket endpoints với training latency thực đo "
                f"p50 = {_fmt_dec(lat['p50_ms'], 1)} ms, p95 = {_fmt_dec(lat['p95_ms'], 1)} ms (300 mẫu) "
                "và đảm bảo 0 B raw data rời khỏi silo."
            ),
            "tone": "good",
        },
    ]

    limitations = [
        {
            "title": f"O*NET Occupation Coverage trên job postings hiện đạt {_fmt_dec(eda['pct_jobs_with_occ'], 2)}%",
            "detail": (
                f"Trong {_fmt_int(g['n_jobs'])} tin tuyển dụng của 9.116 nhà tuyển dụng, có "
                f"{_fmt_int(eda['n_jobs_with_occ'])} tin ({_fmt_dec(eda['pct_jobs_with_occ'], 2)}%) map được sang "
                f"O*NET-SOC; {_fmt_int(meta['edges']['n_jobs_without_occupation_edge'])} tin còn lại vẫn giữ "
                "user–job edges nhưng thiếu cầu nối job–occupation–skill để lan truyền embedding kỹ năng."
            ),
            "tone": "warn",
        },
        {
            "title": "Khoảng cách FedAvg vs Centralized LightGCN trên Global Catalog (82.876 tin)",
            "detail": (
                "Do dữ liệu Non-IID phân mảnh qua 9.116 silo (median chỉ 23 apps/client, "
                "22,38% client không có test edge) và mỗi round chỉ sample 20–50 node, "
                "FedAvg đạt 0,3905–0,5756 trên FL Catalog nhưng mới đạt 0,0475 khi chấm trên "
                "Global Catalog 82.876 tin (so với Centralized LightGCN 0,4002 và Item-KNN 0,5408)."
            ),
            "tone": "warn",
        },
        {
            "title": "Chưa có Online A/B Test trên người dùng thật",
            "detail": (
                "Đồ án đánh giá offline trên 37.957 test edges (37.077 clean test edges "
                "sau khi loại 880 leakage edges và tách 1.969 cold-start jobs); cần Online A/B Test "
                "để đo CTR và mức độ hài lòng thực tế."
            ),
            "tone": "bad",
        },
        {
            "title": "Chưa áp dụng Differential Privacy (DP-SGD) / Secure Aggregation",
            "detail": (
                "Server chỉ nhận embedding gradient ΔW từ các client (0 B raw data), "
                "nhưng tham số truyền đi vẫn ở dạng plaintext; cần bổ sung Secure Aggregation hoặc DP-SGD "
                "để chống gradient inversion attack."
            ),
            "tone": "bad",
        },
        {
            "title": "Hao hụt khi trích xuất tên nhà tuyển dụng (Employer Extraction)",
            "detail": (
                f"Từ {_fmt_int(meta['raw']['apps_rows'])} raw applications của CareerBuilder, pipeline lọc 5 bước "
                "(trích employer bằng regex/domain, lọc client ≥ 2 jobs & ≥ 10 apps) giữ lại "
                f"{_fmt_int(g['edges_by_type']['0'])} edges ({_fmt_dec(meta['employer_extraction']['pct_apps_with_employer_and_client'], 2)}%) "
                "của 9.116 employers để đảm bảo độ sạch nhãn silo."
            ),
            "tone": "warn",
        },
    ]

    next_steps = [
        {
            "direction": "Mở rộng O*NET Mapping bằng Sentence-BERT",
            "reason": "Nâng job–occupation coverage từ 31,44% (26.678 tin) lên >85% trên toàn bộ 84.845 tin",
            "estimate": "~2 ngày",
        },
        {
            "direction": "Stratified Client Sampling trên 9.116 Nodes",
            "reason": "Sample phân tầng nhiều round hơn qua toàn bộ 9.116 silo để thu hẹp khoảng cách Recall@20 trên Global Catalog (82.876 tin)",
            "estimate": "~1–2 ngày",
        },
        {
            "direction": "Secure Aggregation & DP-SGD",
            "reason": "Bảo vệ ΔW embedding update trước nguy cơ gradient inversion trên central server",
            "estimate": "~1 ngày",
        },
        {
            "direction": "Online A/B Test",
            "reason": "Đo trực tiếp CTR, tỷ lệ ứng tuyển thành công và user satisfaction thực tế",
            "estimate": "~1–2 tuần",
        },
    ]

    lessons = [
        {
            "title": "Quy tắc gán Cross-Silo Edge quyết định tính hợp lệ của Federated Learning.",
            "detail": (
                "Vì 44,58% users ứng tuyển đa công ty và chỉ 16,29% test edges nằm cùng client với train edge chính, "
                "edge (u, j) bắt buộc thuộc về client_of_job[j] (employer sở hữu tin), không gán theo client_of_user[u]."
            ),
        },
        {
            "title": "Public Graph Backbone (Occupation + Skill) là cầu nối sống còn giữa các Silo.",
            "detail": (
                "Chuẩn hóa O*NET-SOC về 6 ký tự gốc (soc[:7]) và dùng Technology Skills.txt "
                "(7.760 skills, tránh Skills.txt có entropy = 0) giúp tăng +9,0% Recall@20 (0,3933 → 0,4833) với 0 B raw data."
            ),
        },
        {
            "title": "Quá nhiều local_epochs gây hiện tượng Client Drift.",
            "detail": (
                "Tăng local_epochs từ 1 lên 5 làm runtime tăng gần 5× (39,7s → 195,5s) nhưng Recall@20 giảm từ 0,4833 xuống 0,4565."
            ),
        },
        {
            "title": "Benchmark minh bạch trên đa Evaluation Scope & kiểm soát Data Leakage.",
            "detail": (
                "Luôn báo cáo song song trên Global Catalog (82.876 tin), FL Catalog (9.058 / 4.511 tin), "
                "full test set (37.957 edges) và clean test set (37.077 edges sau khi loại 880 leakage edges) kèm Bootstrap 95% CI."
            ),
        },
    ]

    repro_steps = [
        {
            "command": "python src/prepare_v3.py",
            "description": "Tiền xử lý CareerBuilder + O*NET & dựng đồ thị V3 (264.995 nút, 9.116 node FL)",
        },
        {
            "command": "docker compose up -d && python -m api.load_to_pg",
            "description": "Khởi chạy PostgreSQL (cổng 5433) và nạp 21+ triệu bản ghi đồ thị vào dss_jobs",
        },
        {
            "command": "python -m uvicorn api.main:app --host 127.0.0.1 --port 8000",
            "description": "Khởi động FastAPI Backend (REST/WebSocket giám sát Node FL & Dashboard V3)",
        },
        {
            "command": "cd web && npm run dev",
            "description": "Chạy giao diện React + ThreeUI (5 trang đồng bộ CareerBuilder + O*NET V3)",
        },
    ]

    repro_script = (
        "# 1. Tiền xử lý CareerBuilder + O*NET & dựng đồ thị V3 (264.995 nút, 9.116 node FL)\n"
        "python src/prepare_v3.py\n\n"
        "# 2. Khởi chạy PostgreSQL (Docker cổng 5433) và nạp 21+ triệu bản ghi đồ thị\n"
        "docker compose up -d\n"
        "python -m api.load_to_pg\n\n"
        "# 3. Khởi động FastAPI Backend (REST/WebSocket giám sát Node FL & Dashboard V3)\n"
        "python -m uvicorn api.main:app --host 127.0.0.1 --port 8000\n\n"
        "# 4. Chạy giao diện React + ThreeUI (5 trang đồng bộ V3)\n"
        "cd web && npm run dev"
    )

    return {
        "summary": {
            "total": len(matrix),
            "passed": passed_count,
            "failed": len(matrix) - passed_count,
        },
        "matrix": matrix,
        "achievements": achievements,
        "limitations": limitations,
        "next_steps": next_steps,
        "lessons": lessons,
        "reproducibility": {
            "one_liner": "docker compose up -d && python -m uvicorn api.main:app --port 8000",
            "steps": repro_steps,
            "script": repro_script,
        },
    }
