"""
Bước 1 của bài toán 1: làm sạch MEDAJob và dựng sẵn cấu trúc đồ thị.

Tái sử dụng NGUYÊN pipeline làm sạch của Lab03 (lab03.py) để số liệu khớp
với các bài lab trước, sau đó bổ sung ba thứ mà Lab03 chưa có:

  1. Nút NGÀNH (industry) suy ra từ tiêu đề tin -> đây là một phần của
     "cấu trúc đồ thị chung" nằm trên máy chủ trung tâm.
  2. Phân vùng dữ liệu theo "khách hàng" (client) để mô phỏng FL.
  3. Đóng gói thành .npz + .json để các bước sau không phải đọc CSV lại.

Đầu ra
------
artifacts/medajob/graph.npz    : chỉ số, cạnh, đặc trưng, mặt nạ train/test
artifacts/medajob/meta.json    : thống kê làm sạch, nhãn ngành, tên job/user
artifacts/medajob/jobs.csv     : bảng job đã làm sạch (để app hiển thị)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):  # cho phép chạy `python src/medajob/prepare.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common import banner, load_config, save_json, set_seed, step

# =====================================================================
# Các bảng tra dùng lại từ lab03.py (giữ nguyên để kết quả khớp lab)
# =====================================================================
PHRASES2 = {
    ("machine", "learning"), ("power", "bi"), ("rest", "api"), ("api", "rest"),
    ("data", "engineering"), ("software", "delivery"), ("deep", "learning"),
    ("computer", "vision"), ("manual", "testing"), ("api", "testing"),
    ("spring", "boot"), ("big", "data"), ("data", "warehouse"),
    ("natural", "language"), ("language", "processing"), ("unit", "testing"),
    ("ui", "ux"), ("full", "stack"), ("micro", "services"),
}
PHRASES3 = {("natural", "language", "processing"), ("unit", "testing", "framework")}
ALIAS = {
    "reactjs": "react", "react.js": "react", "nodejs": "node.js", "c/c++": "c++",
    "restful api": "rest api", "restful": "rest api", "powerbi": "power bi",
    "scikit learn": "scikit-learn", "js": "javascript", "ts": "typescript",
    "k8s": "kubernetes", "postgres": "postgresql", "ml": "machine learning",
}

# ---------------------------------------------------------------------
# Từ điển ngành. Thứ tự quan trọng: ngành cụ thể phải đứng trước
# "Software Engineering" (ngành mặc định, quá rộng).
# ---------------------------------------------------------------------
INDUSTRIES: list[tuple[str, tuple[str, ...]]] = [
    ("AI/ML", ("machine learning", "ml engineer", "nlp", "computer vision",
               "deep learning", "ai engineer", "data scientist")),
    ("Data & Analytics", ("data analyst", "data engineer", "business intelligence",
                          "bi developer", "analytics", "data specialist")),
    ("Cloud & DevOps", ("devops", "cloud", "sre", "site reliability", "kubernetes",
                        "aws", "platform engineer")),
    ("Quality Assurance", ("qa ", "qa engineer", "tester", "test engineer",
                           "automation engineer", "quality")),
    ("Security", ("security", "pentest", "soc analyst", "appsec")),
    ("Mobile", ("android", "ios ", "flutter", "react native", "mobile")),
    ("Embedded & IoT", ("embedded", "firmware", "iot", "hardware")),
    ("Product & Business", ("product owner", "product manager", "business analyst",
                            "sales", "marketing", "recruiter", "hr ")),
    ("Software Engineering", ("developer", "engineer", "backend", "frontend",
                              "fullstack", "full stack", "software", "programmer")),
]


# =====================================================================
# 1. Làm sạch kỹ năng
# =====================================================================
def parse_skills(value) -> list[str]:
    """Chuẩn hoá 1 ô kỹ năng về list token sạch.

    CSV gốc trộn 2 định dạng (JSON list và chuỗi phân cách dấu phẩy), kèm
    token dính quote/bracket và cụm từ bị tách rời ("machine","learning").
    """
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []

    tokens = None
    if text[0] in "[{":
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                tokens = [str(x) for x in parsed]
            elif isinstance(parsed, dict):
                tokens = [str(x) for x in parsed.values()]
        except Exception:
            tokens = None
    if tokens is None:
        tokens = [x for x in re.split(r"[,;\n]+", text) if x.strip()]

    clean: list[str] = []
    for token in tokens:
        token = re.sub(r"[\[\]\"'{}]", " ", str(token)).strip().lower()
        token = re.sub(r"\s+", " ", token)
        if token:
            clean.append(token)

    merged: list[str] = []
    i = 0
    while i < len(clean):
        if i + 2 < len(clean) and tuple(clean[i : i + 3]) in PHRASES3:
            merged.append(" ".join(clean[i : i + 3]))
            i += 3
        elif i + 1 < len(clean) and tuple(clean[i : i + 2]) in PHRASES2:
            merged.append(" ".join(clean[i : i + 2]))
            i += 2
        else:
            merged.append(clean[i])
            i += 1

    out: list[str] = []
    seen: set[str] = set()
    for token in merged:
        token = ALIAS.get(token, token)
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


def title_key(title: str) -> str:
    """Bỏ số thứ tự cuối tiêu đề ('Python Backend Developer 41') để gom trùng."""
    text = re.sub(r"\s+\d{1,2}$", "", str(title).strip().lower())
    return re.sub(r"\s+", " ", text)


def infer_industry(title: str) -> str:
    t = " " + str(title).lower() + " "
    for name, keywords in INDUSTRIES:
        if any(k in t for k in keywords):
            return name
    return "Khác"


# =====================================================================
# 2. Pipeline chính
# =====================================================================
def build(cfg: dict) -> dict:
    raw_dir = Path(cfg["paths"]["medajob_raw"])
    art_dir = Path(cfg["paths"]["artifacts"]) / "medajob"
    art_dir.mkdir(parents=True, exist_ok=True)
    set_seed(int(cfg["seed"]))
    rng = np.random.default_rng(int(cfg["seed"]))

    banner("BƯỚC 1 — LÀM SẠCH MEDAJob VÀ DỰNG ĐỒ THỊ")

    jobs = pd.read_csv(raw_dir / "job.csv", encoding="utf-8-sig")
    prof = pd.read_csv(raw_dir / "user_profiles.csv", encoding="utf-8-sig")
    rat = pd.read_csv(raw_dir / "ratings.csv", encoding="utf-8-sig")
    views = pd.read_csv(raw_dir / "job_views.csv", encoding="utf-8-sig")
    n_raw = {"jobs": len(jobs), "profiles": len(prof),
             "ratings": len(rat), "views": len(views)}
    step(f"Dữ liệu gốc: {n_raw['jobs']} tin | {n_raw['profiles']} hồ sơ | "
         f"{n_raw['ratings']} rating | {n_raw['views']} view")

    # --- 2.1 Kỹ năng + lọc tin còn hiệu lực ---------------------------
    jobs["sk"] = jobs.job_skills.apply(parse_skills)
    prof["sk"] = prof.user_skills.apply(parse_skills)
    n_closed = int((jobs.status != "open").sum())
    jobs = jobs[(jobs.status == "open") & (jobs.sk.str.len() > 0)].copy()

    # --- 2.2 Đánh dấu tin dùng "template kỹ năng" ---------------------
    # Nhiều tin dùng chung một tập kỹ năng mẫu -> làm nhiễu CBF/Popularity.
    # Không loại (sẽ mất 2/3 dữ liệu) mà đếm để báo cáo.
    TEMPLATE_MIN = 30
    set_count = jobs.sk.map(lambda xs: tuple(sorted(xs))).value_counts()
    jobs["is_template"] = jobs.sk.map(
        lambda xs: set_count[tuple(sorted(xs))] >= TEMPLATE_MIN and len(xs) <= 6
    )

    # --- 2.3 Loại tin trùng (dữ liệu seed sinh tự động) --------------
    rate_count = rat.groupby("job_id").size()
    jobs["n_rating"] = jobs.id.map(rate_count).fillna(0).astype(int)
    jobs["dup_key"] = (
        jobs.job_title.map(title_key)
        + "|"
        + jobs.sk.map(lambda xs: ",".join(sorted(xs)))
        + "|"
        + jobs.company_name.astype(str).str.strip().str.lower()
    )
    jobs = jobs.sort_values(["dup_key", "n_rating", "id"],
                            ascending=[True, False, True])
    kept = jobs.drop_duplicates("dup_key", keep="first")
    remap = dict(zip(jobs.id, jobs.dup_key.map(kept.set_index("dup_key").id)))
    n_template = int(kept.set_index("id").is_template.sum())
    jobs = kept.sort_values("id").reset_index(drop=True)
    n_drop_dup = n_raw["jobs"] - len(jobs)

    # --- 2.4 Ngành + phân vùng client ---------------------------------
    jobs["industry"] = jobs.job_title.map(infer_industry)

    # --- 2.5 Hồ sơ + rating -------------------------------------------
    prof = prof[prof.sk.str.len() > 0].reset_index(drop=True)
    rat = rat[rat.rating.between(1, 5)].copy()
    rat["job_id"] = rat.job_id.map(lambda x: remap.get(x, x))
    rat = rat[rat.job_id.isin(set(jobs.id))]
    rat = rat[rat.user_id.isin(set(prof.user_id))]
    rat = rat.drop_duplicates(["user_id", "job_id"], keep="last")
    n_drop_rating = n_raw["ratings"] - len(rat)

    qual = {
        "jobs_dropped_closed": n_closed,
        "jobs_dropped_duplicate": int(n_drop_dup),
        "ratings_dropped": int(n_drop_rating),
        "template_jobs": n_template,
        "template_pct": round(100 * n_template / max(len(jobs), 1), 1),
        "title_only_jobs": int(
            (jobs.job_description.astype(str).str.strip().str.lower()
             == jobs.job_title.astype(str).str.strip().str.lower()).sum()
        ),
        "seed_link_jobs": int(
            jobs.link.astype(str).str.contains("tkrecsys.example.com", na=False).sum()
        ),
    }
    step(f"Sau làm sạch: {len(jobs)} tin | {len(prof)} user | {len(rat)} rating")
    step(f"Chất lượng: {qual['template_jobs']} tin template "
         f"({qual['template_pct']}%), {qual['jobs_dropped_duplicate']} tin trùng bị loại")

    # --- 2.6 Ma trận rating + chia train/test --------------------------
    uids = prof.user_id.to_numpy()
    jids = jobs.id.to_numpy()
    uix = {u: i for i, u in enumerate(uids)}
    jix = {j: i for i, j in enumerate(jids)}
    nU, nJ = len(uids), len(jids)

    R = np.zeros((nU, nJ), dtype=np.float32)
    for row in rat.itertuples():
        R[uix[row.user_id], jix[row.job_id]] = row.rating
    M = R > 0

    test_ratio = float(cfg["medajob"]["test_ratio"])
    min_for_test = int(cfg["medajob"]["min_ratings_for_test"])
    train, test = R.copy(), np.zeros_like(R)
    for u in range(nU):
        idx = np.where(M[u])[0]
        if len(idx) >= min_for_test:
            n_test = max(1, int(round(len(idx) * test_ratio)))
            picked = rng.choice(idx, n_test, replace=False)
            test[u, picked] = R[u, picked]
            train[u, picked] = 0.0
    Mtr, Mte = train > 0, test > 0
    step(f"Train/Test: {int(Mtr.sum())}/{int(Mte.sum())} tương tác "
         f"({int((Mte.sum(1) > 0).sum())} user có mặt trong test)")

    # --- 2.7 Từ điển nút công khai ------------------------------------
    skills = sorted({s for xs in jobs.sk for s in xs})
    sidx = {s: i for i, s in enumerate(skills)}
    industries = sorted(set(jobs.industry))
    iidx = {s: i for i, s in enumerate(industries)}
    nS, nI = len(skills), len(industries)

    # --- 2.8 Phân vùng client -----------------------------------------
    # Mỗi employer là một khách hàng; gom lại thành C nhóm để mô phỏng
    # "mỗi nền tảng/công ty giữ dữ liệu riêng".
    employer = jobs.employer_id.astype(int).to_numpy()
    client_of_job = (employer % 100).astype(np.int32)  # client gốc = employer
    user_client = (np.arange(nU) % 100).astype(np.int32)  # user cũng thuộc 1 client

    # --- 2.9 Chỉ số nút ------------------------------------------------
    # Thứ tự nút: [user | job | skill | industry]
    off_user, off_job = 0, nU
    off_skill, off_ind = nU + nJ, nU + nJ + nS
    n_nodes = nU + nJ + nS + nI

    def node_id(kind: str, idx: int) -> int:
        return {"user": off_user, "job": off_job,
                "skill": off_skill, "industry": off_ind}[kind] + idx

    # --- 2.10 Cạnh -----------------------------------------------------
    # (a) job - skill      : công khai (cấu trúc tin tuyển dụng)
    # (b) job - industry   : công khai
    # (c) user - skill     : riêng tư (từ hồ sơ ứng viên)
    # (d) user - job       : riêng tư (tương tác, chỉ train)
    e_src: list[int] = []
    e_dst: list[int] = []
    e_type: list[int] = []  # 0=job-skill 1=job-industry 2=user-skill 3=user-job

    def add(a: int, b: int, t: int) -> None:
        e_src.extend((a, b))
        e_dst.extend((b, a))
        e_type.extend((t, t))

    for j in range(nJ):
        for s in jobs.sk.iat[j]:
            add(node_id("job", j), node_id("skill", sidx[s]), 0)
        add(node_id("job", j), node_id("industry", iidx[jobs.industry.iat[j]]), 1)
    n_job_skill, n_job_ind = len(e_src) // 2, 0  # tạm, tính lại bên dưới

    n_pub_edges = len(e_src) // 2
    for u in range(nU):
        for s in prof.sk.iat[u]:
            if s in sidx:
                add(node_id("user", u), node_id("skill", sidx[s]), 2)

    # edge_index của đồ thị RIÊNG TƯ đầy đủ (dùng cho mô hình tập trung)
    for (u, j) in zip(*np.where(Mtr)):
        add(node_id("user", int(u)), node_id("job", int(j)), 3)

    edge_index = np.asarray([e_src, e_dst], dtype=np.int64)
    edge_type = np.asarray(e_type, dtype=np.int16)

    # --- 2.11 Đặc trưng nút -------------------------------------------
    # Nút công khai (skill/industry) dùng one-hot; nút riêng tư (user/job)
    # học embedding. Ở đây chỉ cần cờ "là nút công khai" cho app vẽ màu.
    is_public = np.zeros(n_nodes, dtype=np.int8)
    is_public[off_skill:] = 1

    # --- 2.12 Lưu artifacts -------------------------------------------
    np.savez_compressed(
        art_dir / "graph.npz",
        n_nodes=n_nodes, n_users=nU, n_jobs=nJ, n_skills=nS, n_industries=nI,
        offsets=np.array([off_user, off_job, off_skill, off_ind]),
        edge_index=edge_index, edge_type=edge_type,
        is_public=is_public,
        R=R, train=train, test=test, Mtr=Mtr, Mte=Mte,
        user_ids=uids, job_ids=jids,
        client_of_job=client_of_job, user_client=user_client,
        n_public_edges=n_pub_edges,
    )

    jobs_out = jobs[["id", "job_title", "company_name", "job_location",
                     "job_type", "experience_level", "industry", "employer_id"]].copy()
    jobs_out["skills"] = jobs.sk.map(lambda xs: "|".join(xs))
    jobs_out.to_csv(art_dir / "jobs.csv", index=False, encoding="utf-8-sig")

    prof_out = prof[["user_id", "title"]].copy()
    prof_out["skills"] = prof.sk.map(lambda xs: "|".join(xs))
    prof_out.to_csv(art_dir / "users.csv", index=False, encoding="utf-8-sig")

    meta = {
        "raw": n_raw,
        "clean": {"jobs": nJ, "users": nU, "ratings": int(len(rat)),
                  "skills": nS, "industries": nI,
                  "train": int(Mtr.sum()), "test": int(Mte.sum()),
                  "users_in_test": int((Mte.sum(1) > 0).sum())},
        "quality": qual,
        "graph": {"nodes": int(n_nodes), "edges": int(edge_index.shape[1]),
                  "public_edges": int(n_pub_edges),
                  "private_edges": int(edge_index.shape[1] - n_pub_edges),
                  "skills": nS, "industries": nI,
                  "industry_counts": jobs.industry.value_counts().to_dict()},
        "sparsity_pct": round(100 * float(M.sum()) / (nU * nJ), 4),
        "n_employers": int(jobs.employer_id.nunique()),
        "n_companies": int(jobs.company_name.nunique()),
    }
    save_json(art_dir / "meta.json", meta)

    step(f"Đồ thị: {n_nodes} nút ({nU} user, {nJ} job, {nS} kỹ năng, {nI} ngành) "
         f"| {edge_index.shape[1]} cạnh có hướng")
    step(f"  công khai (job–skill, job–industry): {n_pub_edges} | "
         f"riêng tư (user–skill, user–job): {edge_index.shape[1] - n_pub_edges}")
    step(f"Đã lưu: {art_dir}")
    return meta


if __name__ == "__main__":
    from src.common import setup_console

    setup_console()
    build(load_config())
