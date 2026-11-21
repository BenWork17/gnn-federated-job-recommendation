"""artifacts.py — nạp artifacts/v3 (graph.npz, clients.json, meta.json).

Nếu chưa có artifacts (graph-builder chưa chạy xong), sinh bộ dữ liệu DEMO
tiền định (seed cố định) cùng cấu trúc để backend + UI vẫn chạy được.
Mọi response có header ``X-Data-Source`` cho biết đang dùng số liệu thật
(``artifacts``) hay giả lập (``demo``).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# console Windows cp1252 -> ép UTF-8 để log tiếng Việt không ném lỗi
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = Path(os.environ.get("DSS_ARTIFACT_DIR") or (ROOT / "artifacts" / "v3"))

# 15 nghề mẫu cho chế độ demo
_DEMO_OCCUPATIONS = [
    "Software Developers", "Registered Nurses", "Market Research Analysts",
    "Accountants and Auditors", "Graphic Designers", "Data Scientists",
    "Customer Service Representatives", "Mechanical Engineers",
    "Sales Representatives", "Network Administrators", "Financial Analysts",
    "Project Managers", "Physical Therapists", "Electricians", "Chefs",
]
_DEMO_SKILLS = [
    "Python", "SQL", "Excel", "Java", "JavaScript", "React", "Docker", "Kubernetes",
    "AWS", "Azure", "Git", "Linux", "Tableau", "Power BI", "SAP", "Salesforce",
    "AutoCAD", "MATLAB", "R", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Spark",
    "Hadoop", "MongoDB", "PostgreSQL", "Redis", "Figma", "Adobe Photoshop",
]
_DEMO_EMPLOYERS = [
    "Acme Analytics", "Beta Health", "Gamma Logistics", "Delta Retail",
    "Epsilon Software", "Zeta Finance", "Eta Manufacturing", "Theta Media",
    "Iota Education", "Kappa Services",
]

CLIENT_ACTIVE_APPS = 10  # ngưỡng client "active" (khớp t1: >=10 app/employer)


def client_status(n_apps: int) -> str:
    """Trạng thái hiển thị của client, suy từ số application."""
    if n_apps >= CLIENT_ACTIVE_APPS:
        return "active"
    if n_apps >= 5:
        return "warm"
    return "idle"


@dataclass
class Dataset:
    """Dữ liệu đồ thị đã chuẩn hoá cho tầng API (không phụ thuộc nguồn)."""

    source: str                      # 'artifacts' | 'demo'
    n_users: int
    n_jobs: int
    n_skills: int
    n_occupations: int
    user_ids: np.ndarray             # (U,) BIGINT id thật
    job_ids: np.ndarray              # (J,)
    client_of_job: np.ndarray        # (J,) -1 nếu không rõ
    client_of_user: np.ndarray       # (U,) -1 nếu không rõ
    occ_ids: np.ndarray              # (J,)
    skill_names: list[str]
    occ_names: list[str]
    clients: list[dict]
    uj: np.ndarray                   # (2,E) chỉ số user_idx, job_idx
    js: np.ndarray                   # (2,E) chỉ số job_idx, skill_idx
    us: np.ndarray                   # (2,E) chỉ số user_idx, skill_idx
    titles: dict[int, str] = field(default_factory=dict)
    employers: dict[int, str] = field(default_factory=dict)

    # ---- thống kê ----
    def summary(self) -> dict:
        n_uj, n_js, n_us = int(self.uj.shape[1]), int(self.js.shape[1]), int(self.us.shape[1])
        possible = (self.n_users * self.n_jobs
                    + self.n_jobs * self.n_skills
                    + self.n_users * self.n_skills)
        sparsity = 100.0 * (1.0 - (n_uj + n_js + n_us) / possible) if possible else 0.0
        return {
            "n_users": int(self.n_users),
            "n_jobs": int(self.n_jobs),
            "n_skills": int(self.n_skills),
            "n_occupations": int(self.n_occupations),
            "n_edges_user_job": n_uj,
            "n_edges_job_skill": n_js,
            "n_edges_user_skill": n_us,
            "n_clients": len(self.clients),
            "sparsity_pct": round(float(sparsity), 6),
        }

    def client_rows(self) -> list[dict]:
        return [
            {
                "client_id": int(c["client_id"]),
                "name": c["name"],
                "n_apps": int(c["n_apps"]),
                "n_users": int(c["n_users"]),
                "n_jobs": int(c["n_jobs"]),
                "status": client_status(int(c["n_apps"])),
            }
            for c in self.clients
        ]


# --------------------------------------------------------------------------
# Sinh dữ liệu DEMO tiền định
# --------------------------------------------------------------------------
def build_demo_dataset(seed: int = 42) -> Dataset:
    rng = np.random.default_rng(seed)
    n_users, n_jobs, n_skills = 300, 800, 120
    n_occ = len(_DEMO_OCCUPATIONS)
    n_clients = len(_DEMO_EMPLOYERS)

    skill_names = list(_DEMO_SKILLS) + [f"tool-{i:03d}" for i in range(len(_DEMO_SKILLS), n_skills)]
    # mỗi nghề có pool skill riêng
    occ_skill_pool = [rng.choice(n_skills, size=18, replace=False) for _ in range(n_occ)]

    job_client = rng.zipf(1.6, size=n_jobs).astype(np.int64)
    job_client = np.minimum(job_client - 1, n_clients - 1)  # 0..n_clients-1
    job_occ = rng.integers(0, n_occ, size=n_jobs)

    # cạnh job-skill
    js_src, js_dst = [], []
    for j in range(n_jobs):
        pool = occ_skill_pool[job_occ[j]]
        k = int(rng.integers(3, 7))
        for s in rng.choice(pool, size=min(k, len(pool)), replace=False):
            js_src.append(j)
            js_dst.append(int(s))
    js = np.vstack([np.asarray(js_src, dtype=np.int64), np.asarray(js_dst, dtype=np.int64)])

    # user skill lấy từ pool của nghề "quan tâm"
    user_occ = rng.integers(0, n_occ, size=n_users)
    us_src, us_dst = [], []
    for u in range(n_users):
        k = int(rng.integers(3, 9))
        pool = occ_skill_pool[user_occ[u]]
        for s in rng.choice(pool, size=min(k, len(pool)), replace=False):
            us_src.append(u)
            us_dst.append(int(s))
    us = np.vstack([np.asarray(us_src, dtype=np.int64), np.asarray(us_dst, dtype=np.int64)])

    user_skill_sets = [set(us[1][us[0] == u].tolist()) for u in range(n_users)]
    job_skill_sets = [set(js[1][js[0] == j].tolist()) for j in range(n_jobs)]

    # cạnh user-job: ưu tiên job cùng nghề + trùng skill
    uj_src, uj_dst = [], []
    for u in range(n_users):
        cand = np.flatnonzero(job_occ == user_occ[u])
        if len(cand) == 0:
            cand = np.arange(n_jobs)
        weights = np.array([1.0 + 3.0 * len(user_skill_sets[u] & job_skill_sets[int(j)]) for j in cand])
        weights /= weights.sum()
        k = int(rng.integers(4, 13))
        picked = rng.choice(cand, size=min(k, len(cand)), replace=False, p=None if len(cand) == 1 else weights)
        for j in picked:
            uj_src.append(u)
            uj_dst.append(int(j))
    uj = np.vstack([np.asarray(uj_src, dtype=np.int64), np.asarray(uj_dst, dtype=np.int64)])

    # client_of_user: client của job ứng tuyển nhiều nhất
    client_of_user = np.full(n_users, -1, dtype=np.int64)
    for u in range(n_users):
        js_of_u = uj[1][uj[0] == u]
        if len(js_of_u):
            vals, counts = np.unique(job_client[js_of_u], return_counts=True)
            client_of_user[u] = int(vals[counts.argmax()])

    # thống kê client
    n_apps_per_client = np.bincount(job_client, weights=np.ones(n_jobs), minlength=n_clients)
    n_apps_app = np.zeros(n_clients, dtype=np.int64)
    for j in uj[1]:
        n_apps_app[job_client[j]] += 1
    n_users_per_client = np.zeros(n_clients, dtype=np.int64)
    for c in range(n_clients):
        n_users_per_client[c] = len(np.unique(uj[0][np.isin(uj[1], np.flatnonzero(job_client == c))]))

    clients = []
    for c in range(n_clients):
        clients.append({
            "client_id": c,
            "name": _DEMO_EMPLOYERS[c],
            "n_apps": int(n_apps_app[c]),
            "n_users": int(n_users_per_client[c]),
            "n_jobs": int(n_apps_per_client[c]),
        })
    clients.sort(key=lambda r: -r["n_apps"])

    user_ids = np.arange(1, n_users + 1, dtype=np.int64)
    job_ids = (100000 + np.arange(n_jobs)).astype(np.int64)
    occupations = {j: _DEMO_OCCUPATIONS[int(job_occ[j])] for j in range(n_jobs)}
    employers = {int(job_ids[j]): _DEMO_EMPLOYERS[int(job_client[j])] for j in range(n_jobs)}
    titles = {int(job_ids[j]): f"{occupations[j]} ({_DEMO_EMPLOYERS[int(job_client[j])]})" for j in range(n_jobs)}

    return Dataset(
        source="demo",
        n_users=n_users,
        n_jobs=n_jobs,
        n_skills=n_skills,
        n_occupations=n_occ,
        user_ids=user_ids,
        job_ids=job_ids,
        client_of_job=job_client.astype(np.int64),
        client_of_user=client_of_user,
        occ_ids=job_occ.astype(np.int64),
        skill_names=skill_names,
        occ_names=list(_DEMO_OCCUPATIONS),
        clients=clients,
        uj=uj,
        js=js,
        us=us,
        titles=titles,
        employers=employers,
    )


# --------------------------------------------------------------------------
# Nạp artifacts thật
# --------------------------------------------------------------------------
def _norm_pair(src, dst, a_lo, a_hi, b_lo):
    """Cặp (loại a, loại b) đã chuẩn hoá: hàng 0 luôn thuộc loại a.

    Đồ thị đối xứng nhưng mỗi cạnh chỉ lưu 1 chiều, nên cạnh có thể nằm theo
    chiều ngược (b -> a); hàm này tự đảo để chỉ số luôn không âm.
    """
    a_first = (src >= a_lo) & (src < a_hi)
    a = np.where(a_first, src, dst) - a_lo
    b = np.where(a_first, dst, src) - b_lo
    return a.astype(np.int32), b.astype(np.int32)


def _group(keys: np.ndarray, values: np.ndarray, n_groups: int):
    """Sắp theo `keys` rồi trả (keys_sorted, values_sorted, starts, counts).

    ``starts[g]:starts[g+1]`` là khoảng của nhóm g trong mảng đã sắp; dày đặc
    nên tra cứu O(1) cho mọi nhóm (kể cả nhóm rỗng).
    """
    order = np.argsort(keys, kind="stable")
    ks = np.ascontiguousarray(keys[order])
    vs = np.ascontiguousarray(values[order])
    starts = np.searchsorted(ks, np.arange(n_groups + 1)).astype(np.int64)
    return ks, vs, starts, np.diff(starts)


def _two_hop_pairs(src_idx: np.ndarray, mid_idx: np.ndarray, starts, values,
                   n_src: int, n_dst: int, chunk: int = 8192) -> np.ndarray:
    """Suy cạnh 2 bước ``src -> mid -> dst`` thành cạnh ``src -> dst``.

    Trả (2, E) int32, đã khử trùng. Khử trùng bằng bool matrix theo lô
    (8192 x n_dst) thay vì ``np.unique`` trên khoá int64: đo thực tế trên dữ
    liệu thật 18,0M cặp cần 2,8s và ~80 MB thay vì 22,4s.

    ``mid_idx < 0`` (job không map được nghề) bị loại bỏ trước khi nối.
    """
    out_dtype = np.int32
    keep = mid_idx >= 0
    src_idx = src_idx[keep]
    mid_idx = mid_idx[keep]
    if src_idx.size == 0:
        return np.zeros((2, 0), dtype=out_dtype)

    counts = np.diff(starts)
    s_sorted, m_sorted, s_starts, _ = _group(src_idx, mid_idx, n_src)

    parts: list[np.ndarray] = []
    for a in range(0, n_src, chunk):
        b = min(n_src, a + chunk)
        lo, hi = int(s_starts[a]), int(s_starts[b])
        if hi <= lo:
            continue
        mids = m_sorted[lo:hi].astype(np.int64)
        lens = counts[mids]
        tot = int(lens.sum())
        if tot == 0:
            continue
        rows = np.repeat(s_sorted[lo:hi], lens).astype(np.int64) - a
        stp = np.repeat(starts[mids], lens)
        offs = np.arange(tot, dtype=np.int64) - np.repeat(np.cumsum(lens) - lens, lens)
        cols = np.asarray(values)[stp + offs]
        mat = np.zeros((b - a, n_dst), dtype=bool)
        mat[rows, cols] = True
        r, c = np.nonzero(mat)
        parts.append(np.vstack([(r + a).astype(out_dtype), c.astype(out_dtype)]))
        del mat, r, c, rows, cols, mids, lens
    if not parts:
        return np.zeros((2, 0), dtype=out_dtype)
    out = np.hstack(parts)
    del parts
    return out


def _split_edge_types(edge_index: np.ndarray, edge_type,
                      n_users: int, n_jobs: int, n_occ: int, n_skills: int):
    """Tách ``edge_index`` thành 4 mặt phẳng cạnh theo ĐÚNG ``edge_type``.

    prepare_v3 lưu 4 loại: 0 user-job, 1 job-occupation, 2 occupation-skill,
    3 user-occupation (xem ``edge_type_names`` trong graph.npz). Bản cũ đoán
    loại chỉ bằng khoảng chỉ số nên gộp nhầm job-occ/occ-skill/user-occ vào
    các mặt phẳng skill -> job-skill và user-skill rỗng.

    Nếu ``edge_type`` vắng mặt, rơi về cách đoán theo khoảng chỉ số (tương
    thích ngược). Trả 4 cặp (src_idx, dst_idx) đã chuẩn hoá chiều, int32.
    """
    src = np.asarray(edge_index[0], dtype=np.int64)
    dst = np.asarray(edge_index[1], dtype=np.int64)
    o_lo, o_hi = n_users + n_jobs, n_users + n_jobs + n_occ

    def pick(mask, a_lo, a_hi, b_lo):
        if not mask.any():
            return (np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32))
        return _norm_pair(src[mask], dst[mask], a_lo, a_hi, b_lo)

    if edge_type is not None and len(edge_type) == len(src):
        et = np.asarray(edge_type, dtype=np.int64)
        uj = pick(et == 0, 0, n_users, n_users)
        job_occ = pick(et == 1, n_users, n_users + n_jobs, o_lo)
        occ_skill = pick(et == 2, o_lo, o_hi, o_hi)
        user_occ = pick(et == 3, 0, n_users, o_lo)
        return uj, job_occ, occ_skill, user_occ

    # --- tương thích ngược: không có edge_type -> đoán theo khoảng chỉ số
    is_u = src < n_users
    in_job = (src >= n_users) & (src < o_lo)
    in_occ = (src >= o_lo) & (src < o_hi)
    dst_is_u = dst < n_users
    dst_in_job = (dst >= n_users) & (dst < o_lo)
    dst_in_occ = (dst >= o_lo) & (dst < o_hi)

    uj = pick((is_u & dst_in_job) | (in_job & dst_is_u), 0, n_users, n_users)
    job_occ = pick((in_job & dst_in_occ) | (in_occ & dst_in_job), n_users, o_lo, o_lo)
    occ_skill = pick((in_occ & (dst >= o_hi)) | ((src >= o_hi) & dst_in_occ), o_lo, o_hi, o_hi)
    user_occ = pick((is_u & dst_in_occ) | (in_occ & dst_is_u), 0, n_users, o_lo)
    return uj, job_occ, occ_skill, user_occ


def load_artifacts(artifact_dir: Path | None = None) -> Dataset | None:
    """Đọc artifacts/v3. Trả None nếu thiếu file bắt buộc."""
    d = Path(artifact_dir or ARTIFACT_DIR)
    npz_path, clients_path = d / "graph.npz", d / "clients.json"
    if not npz_path.exists() or not clients_path.exists():
        return None
    try:
        with np.load(npz_path, allow_pickle=False) as z:
            n_users = int(z["n_users"])
            n_jobs = int(z["n_jobs"])
            n_skills = int(z["n_skills"])
            n_occupations = int(z["n_occupations"]) if "n_occupations" in z else 0
            edge_index = np.asarray(z["edge_index"], dtype=np.int64)
            edge_type = (np.asarray(z["edge_type"], dtype=np.int64)
                         if "edge_type" in z else None)
            user_ids = np.asarray(z["user_ids"], dtype=np.int64)
            job_ids = np.asarray(z["job_ids"], dtype=np.int64)
            client_of_job = (np.asarray(z["client_of_job"], dtype=np.int64)
                             if "client_of_job" in z else np.full(n_jobs, -1, dtype=np.int64))
            client_of_user = (np.asarray(z["client_of_user"], dtype=np.int64)
                              if "client_of_user" in z else np.full(n_users, -1, dtype=np.int64))
            # occ_ids của prepare_v3 là DANH SÁCH MÃ NGHỀ dạng chuỗi (soc[:7],
            # vd "11-1011") cho n_occupations nút — KHÔNG phải mảng chỉ số theo job.
            # Bản cũ ép int64 nên ném ValueError và API âm thầm rơi về dữ liệu demo.
            occ_codes: list[str] = []
            if "occ_ids" in z.files:
                occ_codes = [str(x) for x in z["occ_ids"].tolist()]
            # skill_names là TUỲ CHỌN: graph.npz của prepare_v3 có thể không có.
            # np.load(allow_pickle=False) ném lỗi khi key chứa object array -> bắt riêng.
            skill_names: list[str] = []
            try:
                if "skill_names" in z.files:
                    skill_names = [str(s) for s in z["skill_names"].tolist()]
            except Exception:
                skill_names = []

        clients_raw = json.loads(clients_path.read_text(encoding="utf-8"))
        clients = [
            {
                "client_id": int(c.get("client_id", i)),
                "name": str(c.get("employer_name") or c.get("name") or f"client-{i}"),
                "n_apps": int(c.get("n_apps", 0) or 0),
                "n_users": int(c.get("n_users", 0) or 0),
                "n_jobs": int(c.get("n_jobs", 0) or 0),
            }
            for i, c in enumerate(clients_raw)
        ] if isinstance(clients_raw, list) else []
        clients.sort(key=lambda r: -r["n_apps"])

        occ_names: list[str] = []
        meta: dict = {}
        meta_path = d / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                occ_names = [str(x) for x in (meta.get("occupation_names") or meta.get("occ_names") or [])]
            except Exception:
                occ_names = []
        # ưu tiên mã nghề thật trong graph.npz -> hiển thị được mã SOC ở UI
        if occ_codes and len(occ_codes) == n_occupations:
            occ_names = list(occ_codes)
        if not occ_names:
            occ_names = [f"occ-{i}" for i in range(max(n_occupations, 1))]

        # tên skill: ưu tiên graph.npz, rồi meta.json, rồi skills.json, cuối cùng là chỉ số
        if not skill_names or len(skill_names) != n_skills:
            for key in ("skill_names", "skills"):
                cand = meta.get(key) if isinstance(meta, dict) else None
                if isinstance(cand, list) and len(cand) == n_skills:
                    skill_names = [str(x) for x in cand]
                    break
        if (not skill_names or len(skill_names) != n_skills) and (d / "skills.json").exists():
            try:
                cand = json.loads((d / "skills.json").read_text(encoding="utf-8"))
                if isinstance(cand, list) and len(cand) == n_skills:
                    skill_names = [str(x) for x in cand]
            except Exception:
                pass
        if not skill_names or len(skill_names) != n_skills:
            skill_names = [f"skill-{i}" for i in range(n_skills)]

        # ---- tách cạnh theo edge_type (đúng quy ước prepare_v3), rồi suy 2 lớp skill
        uj, job_occ, occ_skill, user_occ = _split_edge_types(
            edge_index, edge_type, n_users, n_jobs, n_occupations, n_skills)
        del edge_index, edge_type
        uj = np.vstack(uj) if uj[0].size else np.zeros((2, 0), dtype=np.int64)

        # job -> nghề: mỗi job tối đa 1 nghề; -1 = job không map được mã O*NET.
        job_occ_idx = np.full(n_jobs, -1, dtype=np.int64)
        if job_occ[0].size:
            job_occ_idx[job_occ[0]] = job_occ[1]

        # nghề -> kỹ năng: bảng nhóm để suy 2 bước (nghề không có skill -> rỗng).
        if occ_skill[0].size:
            _, sk_vals, occ_starts, _ = _group(occ_skill[0], occ_skill[1], n_occupations)
            sk_vals = sk_vals.astype(np.int64)
        else:
            sk_vals = np.zeros(0, dtype=np.int64)
            occ_starts = np.zeros(n_occupations + 1, dtype=np.int64)

        # job -> kỹ năng = job -> nghề -> skill  (src = job, mid = nghề)
        js = _two_hop_pairs(np.arange(n_jobs, dtype=np.int32),
                            job_occ_idx.astype(np.int32),
                            occ_starts, sk_vals, n_jobs, n_skills)
        # user -> kỹ năng = user -> nghề -> skill
        us = _two_hop_pairs(user_occ[0].astype(np.int32), user_occ[1].astype(np.int32),
                            occ_starts, sk_vals, n_users, n_skills)

        titles: dict[int, str] = {}
        employers: dict[int, str] = {}
        jt_path = d / "job_titles.json"
        if jt_path.exists():
            try:
                raw = json.loads(jt_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        if not isinstance(v, dict):
                            continue
                        t = str(v.get("title") or "").strip()
                        if t:
                            titles[int(k)] = t
                        e = str(v.get("employer") or "").strip()
                        if e:
                            employers[int(k)] = e
            except Exception:
                titles, employers = {}, {}

        return Dataset(
            source="artifacts",
            n_users=n_users,
            n_jobs=n_jobs,
            n_skills=n_skills,
            n_occupations=n_occupations or len(occ_names),
            user_ids=user_ids,
            job_ids=job_ids,
            client_of_job=client_of_job,
            client_of_user=client_of_user,
            occ_ids=job_occ_idx,
            skill_names=skill_names,
            occ_names=occ_names,
            clients=clients,
            uj=uj,
            js=js,
            us=us,
            titles=titles,
            employers=employers,
        )
    except Exception as exc:  # artifact hỏng -> rơi về demo
        print(f"[artifacts] không đọc được {d}: {exc}")
        return None


def get_dataset(prefer_artifacts: bool = True, seed: int = 42) -> Dataset:
    if prefer_artifacts:
        ds = load_artifacts()
        if ds is not None:
            return ds
    return build_demo_dataset(seed=seed)
