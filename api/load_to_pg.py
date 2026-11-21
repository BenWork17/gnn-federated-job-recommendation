#!/usr/bin/env python
"""load_to_pg.py — nạp artifacts/v3 vào PostgreSQL bằng COPY (nhanh).

Ví dụ:
    python api/load_to_pg.py --dsn "postgresql://postgres:postgres@127.0.0.1:5432/dss_jobs"
    python api/load_to_pg.py --artifacts artifacts/v3 --batch-size 200000 --truncate

Nguồn dữ liệu:
    artifacts/v3/graph.npz      : edge_index, edge_type, user_ids, job_ids,
                                  client_of_job, client_of_user, occ_ids (mã nghề)
    artifacts/v3/clients.json   : [{client_id, employer_name, n_apps, n_users, n_jobs}]
    artifacts/v3/job_titles.json: {job_id -> {title, city, state, employer, occupation}}
    artifacts/v3/meta.json      : (tuỳ chọn) occupation_names, skill_names

Lớp kỹ năng (job_skills / user_skills) là SUY QUA NGHỀ: job -> nghề -> skill và
user -> nghề -> skill, đúng như meta.json mô tả. Không có cạnh skill trực tiếp
trong graph.npz nên phải dựng 2 bước ở đây.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACTS = ROOT / "artifacts" / "v3"
DEFAULT_DSN = "postgresql://postgres:postgres@127.0.0.1:5432/dss_jobs"

try:  # dùng lại đúng logic đã kiểm chứng của api/artifacts.py (một nguồn sự thật)
    from .artifacts import load_artifacts
except ImportError:  # chạy trực tiếp: python api/load_to_pg.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from artifacts import load_artifacts


def _split_edges(edge_index: np.ndarray, n_users: int, n_jobs: int):
    """Tách edge_index thành user-job, job-skill, user-skill theo khoảng chỉ số.

    DEPRECATED: giữ lại cho tương thích; ``load()`` dùng thẳng ``load_artifacts``
    (đọc ``edge_type`` + suy 2 bước qua nghề). Hàm này bỏ qua lớp nghề nên
    trả job-skill/user-skill RỖNG với graph.npz v3 thật.
    """
    src, dst = edge_index[0], edge_index[1]
    n_skill_off = n_users + n_jobs

    uj_mask = ((src < n_users) & (dst >= n_users) & (dst < n_skill_off)) | \
              ((dst < n_users) & (src >= n_users) & (src < n_skill_off))
    js_mask = ((src >= n_users) & (src < n_skill_off) & (dst >= n_skill_off)) | \
              ((dst >= n_users) & (dst < n_skill_off) & (src >= n_skill_off))
    us_mask = ((src < n_users) & (dst >= n_skill_off)) | ((dst < n_users) & (src >= n_skill_off))

    s, d = src[uj_mask], dst[uj_mask]
    u_idx = np.where(s < n_users, s, d)
    j_idx = np.where(s < n_users, d, s) - n_users

    s, d = src[js_mask], dst[js_mask]
    j2 = np.where((s >= n_users) & (s < n_skill_off), s, d) - n_users
    s2 = np.where((s >= n_users) & (s < n_skill_off), d, s) - n_skill_off

    s, d = src[us_mask], dst[us_mask]
    u2 = np.where(s < n_users, s, d)
    sk2 = np.where(s < n_users, d, s) - n_skill_off

    return (u_idx, j_idx), (j2, s2), (u2, sk2)


def load(args) -> int:
    try:
        import psycopg
    except ImportError:
        print("Thiếu psycopg. Cài: pip install 'psycopg[binary]'", file=sys.stderr)
        return 2

    art = Path(args.artifacts)
    npz_path, clients_path = art / "graph.npz", art / "clients.json"
    if not npz_path.exists():
        print(f"Không thấy {npz_path}. Chạy src/prepare_v3.py trước.", file=sys.stderr)
        return 2
    t_start = time.perf_counter()

    # MỘT nguồn sự thật: dùng đúng loader của API (đọc edge_type + suy 2 bước
    # qua nghề + nạp job_titles.json). Tránh hai bên hiểu artifacts khác nhau.
    ds = load_artifacts(art)
    if ds is None:
        print(f"Không nạp được artifacts tại {art}. Chạy src/prepare_v3.py trước.",
              file=sys.stderr)
        return 2
    n_users, n_jobs, n_skills = ds.n_users, ds.n_jobs, ds.n_skills
    user_ids, job_ids = ds.user_ids, ds.job_ids
    client_of_job = ds.client_of_job
    skill_names = list(ds.skill_names)
    occ_names = list(ds.occ_names)
    occ_ids = np.asarray(ds.occ_ids, dtype=np.int64)   # chỉ số nghề theo job (-1 = không có)
    uj, js, us = ds.uj, ds.js, ds.us
    print(f"[load] graph: users={n_users} jobs={n_jobs} skills={n_skills} "
          f"occupations={ds.n_occupations} clients={len(ds.clients)}")
    print(f"[load] user-job={uj.shape[1]} job-skill={js.shape[1]} user-skill={us.shape[1]} "
          f"(2 lớp skill suy qua nghề)")
    clients = ds.clients
    titles, title_employers = ds.titles, ds.employers

    employer_of_job: dict[int, str] = {}
    for j in range(n_jobs):
        c = int(client_of_job[j])
        if 0 <= c < len(clients):
            employer_of_job[j] = clients[c]["name"]

    bs = max(1_000, int(args.batch_size))
    dsn = args.dsn
    try:
        conn = psycopg.connect(dsn, autocommit=False)
    except Exception as exc:
        print(f"Không kết nối được PostgreSQL: {exc}", file=sys.stderr)
        return 2

    def copy_rows(cur, sql, rows):
        if not rows:
            return 0
        with cur.copy(sql) as cp:
            for r in rows:
                cp.write_row(r)
        return len(rows)

    total_apps = 0
    with conn.cursor() as cur:
        if args.truncate:
            print("[load] TRUNCATE ...")
            cur.execute("TRUNCATE apps, job_skills, user_skills, jobs, users, employers, "
                        "node_latency, round_metrics, train_runs RESTART IDENTITY CASCADE")
            conn.commit()

        # ---- users ----
        rows = [(int(user_ids[i]), None, None, None) for i in range(n_users)]
        for i in range(0, len(rows), bs):
            copy_rows(cur, "COPY users(user_id, state, degree, years_exp) FROM STDIN", rows[i:i + bs])
            conn.commit()
        print(f"[load] users: {len(rows)}")

        # ---- jobs (title/city/state lấy từ job_titles.json nếu có) ----
        rows = []
        n_title = 0
        for j in range(n_jobs):
            jid = int(job_ids[j])
            occ = occ_names[occ_ids[j]] if 0 <= occ_ids[j] < len(occ_names) else None
            title = titles.get(jid)
            if title:
                n_title += 1
            emp = title_employers.get(jid) or employer_of_job.get(j)
            rows.append((jid, title, emp, occ, None, None))
        for i in range(0, len(rows), bs):
            copy_rows(cur, "COPY jobs(job_id, title, employer, occupation, city, state) FROM STDIN",
                      rows[i:i + bs])
            conn.commit()
        print(f"[load] jobs: {len(rows)} (có title: {n_title})")

        # ---- apps ----
        rows = []
        for u, j in zip(uj[0].tolist(), uj[1].tolist()):
            rows.append((int(user_ids[u]), int(job_ids[j]), None))
            if len(rows) >= bs:
                total_apps += copy_rows(cur, "COPY apps(user_id, job_id, applied_at) FROM STDIN", rows)
                conn.commit()
                rows = []
        total_apps += copy_rows(cur, "COPY apps(user_id, job_id, applied_at) FROM STDIN", rows)
        conn.commit()
        print(f"[load] apps: {total_apps}")

        # ---- job_skills ----
        rows = []
        for j, s in zip(js[0].tolist(), js[1].tolist()):
            rows.append((int(job_ids[j]), skill_names[s]))
            if len(rows) >= bs:
                copy_rows(cur, "COPY job_skills(job_id, skill) FROM STDIN", rows)
                conn.commit()
                rows = []
        copy_rows(cur, "COPY job_skills(job_id, skill) FROM STDIN", rows)
        conn.commit()

        # ---- user_skills ----
        rows = []
        for u, s in zip(us[0].tolist(), us[1].tolist()):
            rows.append((int(user_ids[u]), skill_names[s]))
            if len(rows) >= bs:
                copy_rows(cur, "COPY user_skills(user_id, skill) FROM STDIN", rows)
                conn.commit()
                rows = []
        copy_rows(cur, "COPY user_skills(user_id, skill) FROM STDIN", rows)
        conn.commit()

        # ---- employers ----
        rows = [(c["client_id"], c["name"], c["n_apps"], c["n_users"], c["n_jobs"]) for c in clients]
        copy_rows(cur, "COPY employers(client_id, name, n_apps, n_users, n_jobs) FROM STDIN", rows)
        conn.commit()
        print(f"[load] employers: {len(rows)}")

        cur.execute("ANALYZE")
        conn.commit()
    conn.close()
    print(f"[load] XONG trong {time.perf_counter() - t_start:.1f}s")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Nạp artifacts/v3 vào PostgreSQL")
    ap.add_argument("--dsn", default=__import__("os").environ.get("DSS_PG_DSN", DEFAULT_DSN))
    ap.add_argument("--artifacts", default=str(DEFAULT_ARTIFACTS))
    ap.add_argument("--batch-size", type=int, default=100_000)
    ap.add_argument("--truncate", action="store_true", help="xóa dữ liệu cũ trước khi nạp")
    sys.exit(load(ap.parse_args()))


if __name__ == "__main__":
    main()
