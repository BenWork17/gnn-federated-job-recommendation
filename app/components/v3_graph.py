"""Động cơ đồ thị đầy đủ CareerBuilder + O*NET (V3 — 264.995 nút / 764.364 cạnh).

Cung cấp:
- `load_v3_index()`: nạp và lập chỉ mục CSR vô hướng đối xứng trên toàn bộ
  `artifacts/v3/graph.npz`, kèm 9.116 silo từ `clients.json`, metadata từ
  `job_titles.json` / `user_titles.json` và tên nghề O*NET từ `db_29_3_text.zip`
  (tùy chọn, fallback sang mã SOC nếu thiếu).
- `extract_silo_subgraph()`: trích xuất toàn bộ Tin tuyển dụng (`client_of_job`),
  Ứng viên ứng tuyển (`edge_type == 0`, Riêng tư), Nghề O*NET (`edge_type == 1`,
  Công khai) và Kỹ năng (`edge_type == 2`, Công khai) thuộc một nhà tuyển dụng.
- `search_all_nodes()`: tìm kiếm trên toàn bộ 264.995 nút + 9.116 nhà tuyển dụng
  cho cả 5 loại truy vấn (nghề O*NET, kỹ năng, tin tuyển dụng, nhà tuyển dụng,
  ID/tiêu đề ứng viên).
- `extract_ego_subgraph()`: BFS 1-hop / 2-hop vô hướng quanh nút tâm + mở rộng
  láng giềng (`extra_nids`) với tùy chọn giới hạn nút an toàn cho nút hub.
- `layout_subgraph_to_dfs()`: chuyển đồ thị con sang `(nodes_df, edges_df, meta)`,
  dùng `spring_layout` khi N <= 400 và bố cục O(N) tất định theo tầng/vòng khi
  N > 400 để tránh cấp phát ma trận O(N^2).
"""

from __future__ import annotations

import csv
import json
import math
import unicodedata
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.components import spring_layout
from app.paths import PATHS, ROOT

DEFAULT_ONET_ZIP = ROOT / "_newdata_audit" / "t4_verify" / "db_29_3_text.zip"

KIND_USER = "Người dùng"
KIND_JOB = "Tin tuyển dụng"
KIND_OCC = "Nghề O*NET"
KIND_SKILL = "Kỹ năng"

EDGE_PUBLIC = "Công khai"
EDGE_PRIVATE = "Riêng tư"


def _fold(text: str) -> str:
    """Chuẩn hóa chữ thường + bỏ dấu tiếng Việt để tìm kiếm không dấu."""
    s = str(text or "")
    if s.isascii():
        return s.lower()
    s = s.lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _load_onet_occ_titles(onet_zip_path: Path | None) -> dict[str, str]:
    """Đọc bảng mã SOC 6 ký tự (soc[:7]) -> tên nghề từ `Occupation Data.txt`."""
    if onet_zip_path is None or not onet_zip_path.exists():
        return {}
    out: dict[str, str] = {}
    try:
        with zipfile.ZipFile(onet_zip_path, "r") as zf:
            candidates = [
                n for n in zf.namelist()
                if n.endswith("Occupation Data.txt")
            ]
            if not candidates:
                return {}
            raw = zf.read(candidates[0]).decode("utf-8", errors="replace")
        reader = csv.reader(raw.splitlines(), delimiter="\t")
        header = next(reader, None)
        if not header:
            return {}
        for row in reader:
            if len(row) < 2:
                continue
            full_code = row[0].strip()
            title = row[1].strip()
            if len(full_code) < 7 or not title:
                continue
            soc6 = full_code[:7]
            # Ưu tiên mã gốc `.00` nếu có nhiều nhánh con chung prefix 7 ký tự
            if soc6 not in out or full_code.endswith(".00"):
                out[soc6] = title
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError):
        return {}
    return out


@dataclass
class V3GraphIndex:
    """Chỉ mục bộ nhớ cho toàn bộ đồ thị V3 (264.995 nút, 764.364 cạnh, 9.116 silo)."""

    n_users: int
    n_jobs: int
    n_occupations: int
    n_skills: int
    n_nodes: int
    off_job: int
    off_occ: int
    off_skill: int

    user_ids: np.ndarray
    job_ids: np.ndarray
    occ_ids: np.ndarray
    skill_names: np.ndarray
    client_of_job: np.ndarray
    client_of_user: np.ndarray

    edge_index: np.ndarray
    edge_type: np.ndarray

    # CSR vô hướng đối xứng trên toàn bộ 264.995 nút
    starts: np.ndarray
    nbrs: np.ndarray
    nbr_types: np.ndarray
    deg: np.ndarray

    # CSR silo: client_id -> danh sách node id tin tuyển dụng toàn cục
    clients: list[dict]
    client_by_id: dict[int, dict]
    client_starts: np.ndarray
    client_jobs: np.ndarray
    client_names_folded: list[str]

    # Metadata & tra cứu ID
    job_meta: dict[str, dict]
    user_meta: dict[str, dict]
    occ_titles: dict[str, str]
    uid_to_node: dict[str, int]
    jid_to_node: dict[str, int]
    occ_to_node: dict[str, int]
    skill_to_node: dict[str, int]

    # Chỉ mục tìm kiếm đã gấp dấu cho toàn bộ 264.995 nút
    search_texts: list[str]

    def node_kind(self, nid: int) -> str:
        if nid < self.off_job:
            return KIND_USER
        if nid < self.off_occ:
            return KIND_JOB
        if nid < self.off_skill:
            return KIND_OCC
        return KIND_SKILL

    def node_raw_id(self, nid: int) -> str:
        if nid < self.off_job:
            return str(self.user_ids[nid])
        if nid < self.off_occ:
            return str(self.job_ids[nid - self.off_job])
        if nid < self.off_skill:
            return str(self.occ_ids[nid - self.off_occ])
        return str(self.skill_names[nid - self.off_skill])

    def node_label(self, nid: int) -> str:
        if nid < self.off_job:
            uid = str(self.user_ids[nid])
            u_info = self.user_meta.get(uid) or {}
            u_title = str(u_info.get("title") or "").strip()
            if u_title:
                return f"Ứng viên #{uid} · {u_title[:42]}"
            return f"Ứng viên #{uid}"
        if nid < self.off_occ:
            jid = str(self.job_ids[nid - self.off_job])
            j_info = self.job_meta.get(jid) or {}
            j_title = str(j_info.get("title") or "").strip()
            j_emp = str(j_info.get("employer") or "").strip()
            if j_title and j_emp:
                return f"{j_title[:44]} ({j_emp[:22]})"
            if j_title:
                return j_title[:64]
            return f"Tin #{jid}"
        if nid < self.off_skill:
            code = str(self.occ_ids[nid - self.off_occ])
            otitle = self.occ_titles.get(code, "").strip()
            if otitle:
                return f"Nghề {code} · {otitle[:48]}"
            return f"Nghề O*NET {code}"
        sk_name = str(self.skill_names[nid - self.off_skill]).strip()
        return sk_name[:64] if sk_name else f"Kỹ năng #{nid - self.off_skill}"

    def node_meta(self, nid: int) -> dict:
        meta: dict = {
            "nid": int(nid),
            "raw_id": self.node_raw_id(nid),
            "global_degree": int(self.deg[nid]),
        }
        if nid < self.off_job:
            uid = meta["raw_id"]
            u_info = self.user_meta.get(uid) or {}
            meta["title"] = str(u_info.get("title") or "")
            meta["occupation"] = str(u_info.get("occupation") or "")
        elif nid < self.off_occ:
            j_local = nid - self.off_job
            jid = meta["raw_id"]
            j_info = self.job_meta.get(jid) or {}
            cid = int(self.client_of_job[j_local])
            meta["client_id"] = cid
            meta["title"] = str(j_info.get("title") or "")
            meta["employer"] = str(j_info.get("employer") or "")
            meta["city"] = str(j_info.get("city") or "")
            meta["state"] = str(j_info.get("state") or "")
            meta["occupation"] = str(j_info.get("occupation") or "")
        elif nid < self.off_skill:
            code = meta["raw_id"]
            meta["occ_code"] = code
            meta["occ_title"] = self.occ_titles.get(code, "")
        else:
            meta["skill_name"] = meta["raw_id"]
        return meta


@lru_cache(maxsize=1)
def _load_v3_index_cached(v3_dir_str: str, onet_zip_str: str) -> V3GraphIndex:
    v3_dir = Path(v3_dir_str)
    onet_zip = Path(onet_zip_str) if onet_zip_str else None

    z = np.load(v3_dir / "graph.npz", allow_pickle=False)
    n_users = int(z["n_users"])
    n_jobs = int(z["n_jobs"])
    n_occupations = int(z["n_occupations"])
    n_skills = int(z["n_skills"])
    n_nodes = int(z["n_nodes"])

    off_job = n_users
    off_occ = n_users + n_jobs
    off_skill = n_users + n_jobs + n_occupations

    user_ids = z["user_ids"]
    job_ids = z["job_ids"]
    occ_ids = z["occ_ids"]
    skill_names = z["skill_names"]
    client_of_job = z["client_of_job"]
    client_of_user = z["client_of_user"]
    ei = z["edge_index"]
    et = z["edge_type"]

    # Xây dựng CSR vô hướng đối xứng trên toàn bộ n_nodes
    src = ei[0].astype(np.int32, copy=False)
    dst = ei[1].astype(np.int32, copy=False)
    et_i8 = et.astype(np.int8, copy=False)

    all_u = np.concatenate([src, dst])
    all_v = np.concatenate([dst, src])
    all_t = np.concatenate([et_i8, et_i8])

    order = np.argsort(all_u, kind="mergesort")
    sorted_u = all_u[order]
    nbrs = all_v[order]
    nbr_types = all_t[order]

    deg = np.bincount(sorted_u, minlength=n_nodes).astype(np.int32)
    starts = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(deg, out=starts[1:])

    # Nạp JSON metadata
    with open(v3_dir / "clients.json", encoding="utf-8") as f:
        clients: list[dict] = json.load(f)
    client_by_id = {int(c["client_id"]): c for c in clients}
    n_clients = len(clients)
    client_names_folded = [_fold(c.get("employer_name", "")) for c in clients]

    # CSR client_id -> global job node ids
    job_cids = client_of_job.astype(np.int32, copy=False)
    j_order = np.argsort(job_cids, kind="mergesort")
    client_jobs = (j_order + off_job).astype(np.int32)
    c_counts = np.bincount(job_cids, minlength=n_clients).astype(np.int64)
    client_starts = np.zeros(n_clients + 1, dtype=np.int64)
    np.cumsum(c_counts, out=client_starts[1:])

    job_meta: dict[str, dict] = {}
    job_titles_path = v3_dir / "job_titles.json"
    if job_titles_path.exists():
        with open(job_titles_path, encoding="utf-8") as f:
            job_meta = json.load(f)

    user_meta: dict[str, dict] = {}
    user_titles_path = v3_dir / "user_titles.json"
    if user_titles_path.exists():
        with open(user_titles_path, encoding="utf-8") as f:
            user_meta = json.load(f)

    occ_titles = _load_onet_occ_titles(onet_zip)

    # Bảng tra cứu ID -> global nid
    uid_list = user_ids.tolist()
    jid_list = job_ids.tolist()
    occ_list = occ_ids.tolist()
    sk_list = skill_names.tolist()

    uid_to_node = {str(u): i for i, u in enumerate(uid_list)}
    jid_to_node = {str(j): off_job + i for i, j in enumerate(jid_list)}
    occ_to_node = {str(o): off_occ + i for i, o in enumerate(occ_list)}
    skill_to_node = {_fold(s): off_skill + i for i, s in enumerate(sk_list)}

    # Chuỗi tìm kiếm đã gấp dấu cho toàn bộ 264.995 nút
    search_texts: list[str] = [""] * n_nodes
    for i, uid in enumerate(uid_list):
        u_info = user_meta.get(uid)
        if u_info:
            ut = u_info.get("title") or ""
            search_texts[i] = f"{uid} {_fold(ut)}".strip()
        else:
            search_texts[i] = uid

    for i, jid in enumerate(jid_list):
        j_info = job_meta.get(jid)
        if j_info:
            jt = j_info.get("title") or ""
            je = j_info.get("employer") or ""
            jc = j_info.get("city") or ""
            js = j_info.get("state") or ""
            jo = j_info.get("occupation") or ""
            search_texts[off_job + i] = _fold(f"{jid} {jt} {je} {jc} {js} {jo}")
        else:
            search_texts[off_job + i] = jid

    for i, code in enumerate(occ_list):
        otitle = occ_titles.get(code, "")
        search_texts[off_occ + i] = _fold(f"{code} {otitle}".strip())

    for i, sk in enumerate(sk_list):
        search_texts[off_skill + i] = _fold(sk)

    return V3GraphIndex(
        n_users=n_users,
        n_jobs=n_jobs,
        n_occupations=n_occupations,
        n_skills=n_skills,
        n_nodes=n_nodes,
        off_job=off_job,
        off_occ=off_occ,
        off_skill=off_skill,
        user_ids=user_ids,
        job_ids=job_ids,
        occ_ids=occ_ids,
        skill_names=skill_names,
        client_of_job=client_of_job,
        client_of_user=client_of_user,
        edge_index=ei,
        edge_type=et,
        starts=starts,
        nbrs=nbrs,
        nbr_types=nbr_types,
        deg=deg,
        clients=clients,
        client_by_id=client_by_id,
        client_starts=client_starts,
        client_jobs=client_jobs,
        client_names_folded=client_names_folded,
        job_meta=job_meta,
        user_meta=user_meta,
        occ_titles=occ_titles,
        uid_to_node=uid_to_node,
        jid_to_node=jid_to_node,
        occ_to_node=occ_to_node,
        skill_to_node=skill_to_node,
        search_texts=search_texts,
    )


def load_v3_index(
    v3_dir: Path | str | None = None,
    onet_zip_path: Path | str | None = None,
) -> V3GraphIndex:
    """Nạp (có cache singleton) toàn bộ chỉ mục đồ thị V3."""
    resolved_v3 = Path(v3_dir) if v3_dir is not None else Path(PATHS["v3"])
    resolved_onet = (
        Path(onet_zip_path) if onet_zip_path is not None else DEFAULT_ONET_ZIP
    )
    onet_str = str(resolved_onet.resolve()) if resolved_onet.exists() else ""
    return _load_v3_index_cached(str(resolved_v3.resolve()), onet_str)


def extract_silo_subgraph(
    index: V3GraphIndex,
    client_id: int,
    *,
    include_user_occ: bool = False,
) -> dict:
    """Trích xuất đồ thị con Silo Nhà tuyển dụng từ `client_of_job`.

    Luôn lấy tập Tin tuyển dụng qua `client_of_job == client_id`, tập Ứng viên
    qua cạnh `edge_type == 0` (`user-job`, Riêng tư) nối vào các tin đó (KHÔNG
    dùng `client_of_user`), Nghề O*NET qua `edge_type == 1` (`job-occ`, Công khai),
    và Kỹ năng qua `edge_type == 2` (`occ-skill`, Công khai).
    """
    cid = int(client_id)
    if cid not in index.client_by_id:
        raise ValueError(f"client_id không hợp lệ: {client_id}")

    j_start = int(index.client_starts[cid])
    j_end = int(index.client_starts[cid + 1])
    job_arr = index.client_jobs[j_start:j_end]

    job_set = set(job_arr.tolist())
    user_set: set[int] = set()
    occ_set: set[int] = set()
    skill_set: set[int] = set()

    seen_pairs: set[tuple[int, int]] = set()
    edges_raw: list[tuple[int, int, int, str]] = []

    starts = index.starts
    nbrs = index.nbrs
    nbr_types = index.nbr_types

    def _add_edge(u: int, v: int, et_val: int) -> None:
        key = (u, v) if u < v else (v, u)
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        kind_str = EDGE_PUBLIC if et_val in (1, 2) else EDGE_PRIVATE
        edges_raw.append((u, v, et_val, kind_str))

    # 1. Từ tất cả Job của silo -> lấy User (et==0) và Occupation (et==1)
    for j in job_arr.tolist():
        s0, s1 = int(starts[j]), int(starts[j + 1])
        for k in range(s0, s1):
            nb = int(nbrs[k])
            et_val = int(nbr_types[k])
            if et_val == 0:
                user_set.add(nb)
                _add_edge(nb, j, 0)
            elif et_val == 1:
                occ_set.add(nb)
                _add_edge(j, nb, 1)

    # 2. Từ các Occupation của silo -> lấy Skill (et==2)
    for o in sorted(occ_set):
        s0, s1 = int(starts[o]), int(starts[o + 1])
        for k in range(s0, s1):
            if int(nbr_types[k]) == 2:
                sk = int(nbrs[k])
                skill_set.add(sk)
                _add_edge(o, sk, 2)

    # 3. Tùy chọn thêm cạnh user-occ (et==3) nội bộ trong tập occ của silo
    if include_user_occ and occ_set:
        for u in sorted(user_set):
            s0, s1 = int(starts[u]), int(starts[u + 1])
            for k in range(s0, s1):
                if int(nbr_types[k]) == 3:
                    o = int(nbrs[k])
                    if o in occ_set:
                        _add_edge(u, o, 3)

    all_nids = sorted(job_set | user_set | occ_set | skill_set)
    sub_deg: dict[int, int] = {n: 0 for n in all_nids}
    for u, v, _, _ in edges_raw:
        sub_deg[u] += 1
        sub_deg[v] += 1

    nodes: list[dict] = []
    for nid in all_nids:
        nodes.append({
            "nid": nid,
            "kind": index.node_kind(nid),
            "label": index.node_label(nid),
            "raw_id": index.node_raw_id(nid),
            "degree": sub_deg[nid],
            "meta": index.node_meta(nid),
        })

    n_public = sum(1 for _, _, _, k in edges_raw if k == EDGE_PUBLIC)
    n_private = len(edges_raw) - n_public
    client_info = index.client_by_id[cid]

    return {
        "mode": "silo",
        "client_id": cid,
        "nodes": nodes,
        "edges": edges_raw,
        "stats": {
            "client": client_info,
            "n_jobs": len(job_set),
            "n_users": len(user_set),
            "n_occs": len(occ_set),
            "n_skills": len(skill_set),
            "n_nodes": len(nodes),
            "n_edges": len(edges_raw),
            "n_public": n_public,
            "n_private": n_private,
            "n_apps": sum(1 for _, _, et_v, _ in edges_raw if et_v == 0),
        },
    }


def search_all_nodes(
    index: V3GraphIndex,
    query: str,
    *,
    kind_filter: str = "Tất cả",
    limit: int = 30,
) -> list[dict]:
    """Tìm kiếm trên toàn bộ 264.995 nút + 9.116 nhà tuyển dụng cho cả 5 loại truy vấn."""
    q_raw = str(query or "").strip()
    if not q_raw:
        return []
    term = _fold(q_raw)
    if not term:
        return []
    q_id_clean = q_raw.lstrip("#").strip()

    kf = "Nghề O*NET" if kind_filter == "Ngành" else kind_filter
    if kf == KIND_USER:
        lo, hi = 0, index.off_job
    elif kf == KIND_JOB:
        lo, hi = index.off_job, index.off_occ
    elif kf == KIND_OCC:
        lo, hi = index.off_occ, index.off_skill
    elif kf == KIND_SKILL:
        lo, hi = index.off_skill, index.n_nodes
    else:
        lo, hi = 0, index.n_nodes

    search_texts = index.search_texts
    deg = index.deg
    off_job = index.off_job
    off_occ = index.off_occ
    off_skill = index.off_skill

    # Tìm tập ứng viên khớp theo chuỗi con đã gấp dấu
    raw_hits = [
        nid for nid in range(lo, hi)
        if term in search_texts[nid]
    ]

    # Đảm bảo tra cứu chính xác ID (kể cả trong 15.618 user thiếu user_titles.json)
    exact_candidates: set[int] = set()
    if q_id_clean in index.uid_to_node:
        uid_nid = index.uid_to_node[q_id_clean]
        if lo <= uid_nid < hi:
            exact_candidates.add(uid_nid)
    if q_id_clean in index.jid_to_node:
        jid_nid = index.jid_to_node[q_id_clean]
        if lo <= jid_nid < hi:
            exact_candidates.add(jid_nid)
    if q_raw in index.occ_to_node:
        occ_nid = index.occ_to_node[q_raw]
        if lo <= occ_nid < hi:
            exact_candidates.add(occ_nid)
    if term in index.skill_to_node:
        sk_nid = index.skill_to_node[term]
        if lo <= sk_nid < hi:
            exact_candidates.add(sk_nid)

    if exact_candidates:
        hit_set = set(raw_hits) | exact_candidates
        raw_hits = list(hit_set)

    # Xếp hạng: khớp chính xác ID/tên (tier 0) -> prefix (tier 1) -> khớp từ/nhà tuyển dụng (tier 2) -> substring (tier 3)
    matched_cids = {
        cid for cid, cname in enumerate(index.client_names_folded)
        if term in cname
    }

    scored: list[tuple[int, int, int, str]] = []
    for nid in raw_hits:
        gdeg = int(deg[nid])
        if nid < off_job:
            uid = str(index.user_ids[nid])
            if q_id_clean == uid:
                tier = 0
                src_tag = "user_id"
            elif uid.startswith(term):
                tier = 1
                src_tag = "user_id"
            elif term in uid:
                tier = 2
                src_tag = "user_id"
            else:
                u_title = _fold((index.user_meta.get(uid) or {}).get("title") or "")
                tier = 0 if u_title == term else (1 if u_title.startswith(term) else 3)
                src_tag = "user_title"
        elif nid < off_occ:
            j_local = nid - off_job
            jid = str(index.job_ids[j_local])
            cid = int(index.client_of_job[j_local])
            j_info = index.job_meta.get(jid) or {}
            j_title_f = _fold(j_info.get("title") or "")
            j_emp_f = _fold(j_info.get("employer") or "")
            if q_id_clean == jid:
                tier = 0
                src_tag = "job_id"
            elif j_emp_f == term:
                tier = 0
                src_tag = "employer"
            elif j_title_f == term:
                tier = 0
                src_tag = "job_title"
            elif j_title_f.startswith(term) or j_emp_f.startswith(term):
                tier = 1
                src_tag = "employer" if (cid in matched_cids or term in j_emp_f) and term not in j_title_f else "job_title"
            elif cid in matched_cids or term in j_emp_f:
                tier = 2
                src_tag = "employer" if term not in j_title_f else "job_title"
            elif term in jid:
                tier = 2
                src_tag = "job_id"
            else:
                tier = 3
                src_tag = "job_title"
        elif nid < off_skill:
            code = str(index.occ_ids[nid - off_occ])
            code_l = code.lower()
            otitle_f = _fold(index.occ_titles.get(code, ""))
            if term == code_l or otitle_f == term:
                tier = 0
                src_tag = "occ_code" if term == code_l else "occ_title"
            elif code_l.startswith(term) or otitle_f.startswith(term):
                tier = 1
                src_tag = "occ_code" if code_l.startswith(term) else "occ_title"
            elif term in code_l:
                tier = 2
                src_tag = "occ_code"
            else:
                tier = 3
                src_tag = "occ_title"
        else:
            sk_f = search_texts[nid]
            if sk_f == term:
                tier = 0
            elif sk_f.startswith(term):
                tier = 1
            else:
                tier = 3
            src_tag = "skill"

        scored.append((tier, -gdeg, nid, src_tag))

    scored.sort()
    results: list[dict] = []
    for _, _, nid, src_tag in scored[: max(1, int(limit))]:
        cid_val: int | None = None
        emp_val = ""
        if off_job <= nid < off_occ:
            j_local = nid - off_job
            cid_val = int(index.client_of_job[j_local])
            emp_val = str((index.job_meta.get(str(index.job_ids[j_local])) or {}).get("employer") or "")
        results.append({
            "nid": nid,
            "kind": index.node_kind(nid),
            "label": index.node_label(nid),
            "raw_id": index.node_raw_id(nid),
            "degree": int(deg[nid]),
            "match_source": src_tag,
            "client_id": cid_val,
            "employer": emp_val,
        })
    return results


def extract_ego_subgraph(
    index: V3GraphIndex,
    center_nid: int,
    *,
    hops: int = 1,
    extra_nids: set[int] | list[int] | None = None,
    max_nodes: int | None = None,
) -> dict:
    """Trích xuất Ego-graph 1-hop hoặc 2-hop vô hướng quanh `center_nid`.

    Hỗ trợ `extra_nids` để mở rộng thêm 1-hop quanh các nút người dùng bấm
    "Mở rộng láng giềng". Nếu đặt `max_nodes`, giữ `center_nid`, `extra_nids`,
    láng giềng 1-hop (ưu tiên bậc cao) trước láng giềng 2-hop.
    """
    if hops not in (1, 2):
        raise ValueError(f"hops phải là 1 hoặc 2, nhận được: {hops}")
    center = int(center_nid)
    if not (0 <= center < index.n_nodes):
        raise ValueError(f"center_nid ngoài phạm vi [0, {index.n_nodes}): {center_nid}")

    extras: list[int] = []
    seen_ex: set[int] = set()
    for x in (extra_nids or ()):
        xi = int(x)
        if 0 <= xi < index.n_nodes and xi != center and xi not in seen_ex:
            seen_ex.add(xi)
            extras.append(xi)

    starts = index.starts
    nbrs = index.nbrs
    nbr_types = index.nbr_types
    deg = index.deg

    dist: dict[int, int] = {center: 0}
    hop1: list[int] = []
    hop2: list[int] = []

    # Bước 1: láng giềng trực tiếp quanh center
    s0, s1 = int(starts[center]), int(starts[center + 1])
    for k in range(s0, s1):
        v = int(nbrs[k])
        if v not in dist:
            dist[v] = 1
            hop1.append(v)

    # Bước 2 (tùy chọn): láng giềng bước 2 quanh hop1
    if hops == 2:
        # Duyệt hop1 theo bậc giảm dần cho ổn định
        hop1_sorted = sorted(hop1, key=lambda n: (-int(deg[n]), n))
        for u in hop1_sorted:
            u0, u1 = int(starts[u]), int(starts[u + 1])
            for k in range(u0, u1):
                v = int(nbrs[k])
                if v not in dist:
                    dist[v] = 2
                    hop2.append(v)

    hop1_set = set(hop1)

    # Mở rộng 1-hop quanh từng nút trong extra_nids ("Mở rộng láng giềng")
    # Ưu tiên láng giềng mới ngoài hop1 trước, sau đó mới tới láng giềng nằm trong hop1
    # để vừa mở rộng ra ngoài vừa đảm bảo nối đủ cạnh quanh nút được chọn.
    extra_nbrs_by_ex: list[list[int]] = []
    seen_extra_nbrs: set[int] = set()
    for ex in extras:
        if ex not in dist:
            dist[ex] = 1
        e0, e1 = int(starts[ex]), int(starts[ex + 1])
        ex_outer: list[int] = []
        ex_inner: list[int] = []
        for k in range(e0, e1):
            v = int(nbrs[k])
            if v not in dist:
                dist[v] = 2
            if v != center and v not in seen_ex and v not in seen_extra_nbrs:
                seen_extra_nbrs.add(v)
                if v not in hop1_set:
                    ex_outer.append(v)
                else:
                    ex_inner.append(v)
        ex_outer.sort(key=lambda n: (-int(deg[n]), n))
        ex_inner.sort(key=lambda n: (-int(deg[n]), n))
        extra_nbrs_by_ex.append(ex_outer + ex_inner)

    extra_nbrs: list[int] = []
    if extra_nbrs_by_ex:
        max_len = max(len(lst) for lst in extra_nbrs_by_ex)
        for pos in range(max_len):
            for lst in extra_nbrs_by_ex:
                if pos < len(lst):
                    extra_nbrs.append(lst[pos])

    total_unfiltered = len(dist)
    truncated = False

    if max_nodes is not None and total_unfiltered > int(max_nodes):
        cap = max(1, int(max_nodes))
        truncated = True
        ordered: list[int] = [center]
        selected_set: set[int] = {center}
        for ex in extras:
            if len(ordered) >= cap:
                break
            if ex not in selected_set:
                selected_set.add(ex)
                ordered.append(ex)

        hop1_sorted = sorted(hop1, key=lambda n: (-int(deg[n]), n))
        hop2_sorted = sorted(hop2, key=lambda n: (-int(deg[n]), n))

        remaining = cap - len(ordered)
        if remaining > 0 and extra_nbrs:
            # Dành riêng một phần ngân sách cho `extra_nbrs` để nút hub không chiếm hết `cap`
            target_extra = min(len(extra_nbrs), max(30, cap // (len(extras) + 1)))
            min_hop1_keep = min(len(hop1_sorted), max(1, remaining // 3)) if hop1_sorted else 0
            extra_quota = min(target_extra, max(1, remaining - min_hop1_keep))
            hop1_initial = remaining - extra_quota
        else:
            hop1_initial = remaining

        taken_hop1 = 0
        for n in hop1_sorted:
            if len(ordered) >= cap or taken_hop1 >= hop1_initial:
                break
            if n not in selected_set:
                selected_set.add(n)
                ordered.append(n)
                taken_hop1 += 1

        for pool in (extra_nbrs, hop1_sorted, hop2_sorted):
            for n in pool:
                if len(ordered) >= cap:
                    break
                if n not in selected_set:
                    selected_set.add(n)
                    ordered.append(n)
            if len(ordered) >= cap:
                break
    else:
        selected_set = set(dist.keys())
        ordered = sorted(selected_set)

    # Trích xuất mọi cạnh cảm sinh trên tập selected_set (mỗi cạnh vô hướng 1 lần qua u < v)
    edges_raw: list[tuple[int, int, int, str]] = []
    sub_deg: dict[int, int] = {n: 0 for n in selected_set}
    for u in sorted(selected_set):
        u0, u1 = int(starts[u]), int(starts[u + 1])
        for k in range(u0, u1):
            v = int(nbrs[k])
            if v in selected_set and u < v:
                et_val = int(nbr_types[k])
                kind_str = EDGE_PUBLIC if et_val in (1, 2) else EDGE_PRIVATE
                edges_raw.append((u, v, et_val, kind_str))
                sub_deg[u] += 1
                sub_deg[v] += 1

    nodes: list[dict] = []
    kind_counts = {KIND_USER: 0, KIND_JOB: 0, KIND_OCC: 0, KIND_SKILL: 0}
    for nid in sorted(selected_set):
        knd = index.node_kind(nid)
        kind_counts[knd] += 1
        meta = index.node_meta(nid)
        meta["hop"] = dist[nid]
        meta["is_center"] = nid == center
        meta["is_expanded"] = nid in seen_ex
        nodes.append({
            "nid": nid,
            "kind": knd,
            "label": index.node_label(nid),
            "raw_id": index.node_raw_id(nid),
            "degree": sub_deg[nid],
            "hop": dist[nid],
            "meta": meta,
        })

    n_public = sum(1 for _, _, _, k in edges_raw if k == EDGE_PUBLIC)
    n_private = len(edges_raw) - n_public

    return {
        "mode": "ego",
        "center_nid": center,
        "hops": hops,
        "extra_nids": extras,
        "truncated": truncated,
        "total_unfiltered_nodes": total_unfiltered,
        "nodes": nodes,
        "edges": edges_raw,
        "stats": {
            "center_nid": center,
            "center_label": index.node_label(center),
            "center_kind": index.node_kind(center),
            "hops": hops,
            "n_users": kind_counts[KIND_USER],
            "n_jobs": kind_counts[KIND_JOB],
            "n_occs": kind_counts[KIND_OCC],
            "n_skills": kind_counts[KIND_SKILL],
            "n_nodes": len(nodes),
            "n_edges": len(edges_raw),
            "n_public": n_public,
            "n_private": n_private,
            "truncated": truncated,
            "total_unfiltered_nodes": total_unfiltered,
        },
    }


def _fast_radial_layout(nodes: list[dict], dim: int) -> np.ndarray:
    """Bố cục O(N) tất định theo 4 vòng loại nút trong [0.04, 0.96].

    Tránh ma trận (N, N, dim) của `spring_layout` khi N > 400. Mỗi nút được
    gán tọa độ duy nhất không trùng lặp bằng góc vàng (golden angle).
    """
    n = len(nodes)
    pos = np.zeros((n, dim), dtype=np.float64)
    if n == 0:
        return pos
    if n == 1:
        pos[0, :] = 0.5
        return pos

    ring_r = {
        KIND_OCC: 0.14,
        KIND_SKILL: 0.28,
        KIND_JOB: 0.36,
        KIND_USER: 0.44,
    }
    ring_z = {
        KIND_OCC: 0.78,
        KIND_SKILL: 0.60,
        KIND_JOB: 0.42,
        KIND_USER: 0.22,
    }
    groups: dict[str, list[int]] = {
        KIND_OCC: [],
        KIND_SKILL: [],
        KIND_JOB: [],
        KIND_USER: [],
    }
    for i, nd in enumerate(nodes):
        groups.setdefault(nd["kind"], []).append(i)

    golden = math.pi * (3.0 - math.sqrt(5.0))
    for knd, idxs in groups.items():
        if not idxs:
            continue
        idxs.sort(key=lambda idx: (-int(nodes[idx]["degree"]), int(nodes[idx]["nid"])))
        m = len(idxs)
        r_base = ring_r.get(knd, 0.32)
        z_base = ring_z.get(knd, 0.5)
        for rank, i in enumerate(idxs):
            frac = (rank + 0.5) / max(1, m)
            r = r_base * (0.45 + 0.55 * math.sqrt(frac))
            theta = rank * golden + (0.4 if knd == KIND_JOB else 0.0)
            pos[i, 0] = 0.5 + r * math.cos(theta)
            pos[i, 1] = 0.5 + r * math.sin(theta)
            if dim == 3:
                pos[i, 2] = max(0.05, min(0.95, z_base + 0.12 * math.sin(theta * 2.0) * (0.5 + 0.5 * frac)))

    return np.clip(pos, 0.04, 0.96)


def _select_render_budget(
    sub: dict,
    nodes: list[dict],
    edges: list[tuple[int, int, int, str]],
    max_render_nodes: int,
) -> tuple[list[dict], list[tuple[int, int, int, str]]]:
    """Giảm tập nút hiển thị một cách tất định nhưng vẫn giữ liên thông đại diện."""
    cap = max(1, int(max_render_nodes))
    if len(nodes) <= cap:
        return nodes, edges

    by_nid = {n["nid"]: n for n in nodes}
    focal: list[int] = []
    if sub.get("mode") == "ego":
        c = sub.get("center_nid")
        if c in by_nid:
            focal.append(c)
        for ex in sub.get("extra_nids") or ():
            if ex in by_nid and ex not in focal:
                focal.append(ex)

    # Dựng danh sách kề cục bộ để ưu tiên nút có kết nối trực tiếp tới phần đã giữ
    adj: dict[int, list[int]] = {}
    for u, v, _, _ in edges:
        if u in by_nid and v in by_nid:
            adj.setdefault(u, []).append(v)
            adj.setdefault(v, []).append(u)

    selected_set: set[int] = set(focal)

    if sub.get("mode") == "silo":
        by_kind: dict[str, list[dict]] = {
            KIND_OCC: [],
            KIND_JOB: [],
            KIND_SKILL: [],
            KIND_USER: [],
        }
        for n in nodes:
            by_kind.setdefault(n["kind"], []).append(n)
        for lst in by_kind.values():
            lst.sort(key=lambda n: (-int(n["degree"]), int(n["nid"])))

        q_occ = max(1, int(cap * 0.12))
        q_job = max(1, int(cap * 0.35))
        q_skill = max(1, int(cap * 0.23))

        # 1. Giữ nghề O*NET bậc cao
        kept_occs: list[int] = []
        for n in by_kind[KIND_OCC][:q_occ]:
            if len(selected_set) < cap:
                selected_set.add(n["nid"])
                kept_occs.append(n["nid"])

        # 2. Giữ tin tuyển dụng (ưu tiên tin nối nghề đã giữ + bậc cao)
        kept_occ_set = set(kept_occs)
        job_cands = sorted(
            by_kind[KIND_JOB],
            key=lambda n: (
                0 if any(nb in kept_occ_set for nb in adj.get(n["nid"], ())) else 1,
                -int(n["degree"]),
                int(n["nid"]),
            ),
        )
        kept_jobs: list[int] = []
        for n in job_cands[:q_job]:
            if len(selected_set) < cap:
                selected_set.add(n["nid"])
                kept_jobs.append(n["nid"])

        # 3. Giữ kỹ năng nối trực tiếp với nghề đã giữ
        sk_cands = sorted(
            by_kind[KIND_SKILL],
            key=lambda n: (
                0 if any(nb in kept_occ_set for nb in adj.get(n["nid"], ())) else 1,
                -int(n["degree"]),
                int(n["nid"]),
            ),
        )
        for n in sk_cands[:q_skill]:
            if len(selected_set) < cap:
                selected_set.add(n["nid"])

        # 4. Giữ ứng viên nối trực tiếp với các tin đã giữ
        kept_job_set = set(kept_jobs)
        u_cands = sorted(
            by_kind[KIND_USER],
            key=lambda n: (
                0 if any(nb in kept_job_set for nb in adj.get(n["nid"], ())) else 1,
                -int(n["degree"]),
                int(n["nid"]),
            ),
        )
        for n in u_cands:
            if len(selected_set) >= cap:
                break
            selected_set.add(n["nid"])
    else:
        # Ego mode: giữ center + extra_nids + hop 1 trước hop 2, trong mỗi hop ưu tiên bậc cao
        rest = [n for n in nodes if n["nid"] not in selected_set]
        rest.sort(key=lambda n: (int(n.get("hop", 2)), -int(n["degree"]), int(n["nid"])))
        for n in rest:
            if len(selected_set) >= cap:
                break
            selected_set.add(n["nid"])

    # Lấp đầy nếu vẫn còn dư hạn mức
    if len(selected_set) < cap:
        rest = [n for n in nodes if n["nid"] not in selected_set]
        rest.sort(key=lambda n: (-int(n["degree"]), int(n["nid"])))
        for n in rest:
            if len(selected_set) >= cap:
                break
            selected_set.add(n["nid"])

    kept_edges = [e for e in edges if e[0] in selected_set and e[1] in selected_set]
    kept_nodes = [by_nid[nid] for nid in sorted(selected_set)]
    return kept_nodes, kept_edges


def layout_subgraph_to_dfs(
    sub: dict,
    *,
    dim: int = 2,
    max_render_nodes: int | None = None,
    kind_filter: str = "Tất cả",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Chuyển subgraph từ `extract_silo_subgraph` / `extract_ego_subgraph` sang DataFrame vẽ 2D/3D."""
    if dim not in (2, 3):
        raise ValueError(f"dim phải là 2 hoặc 3, nhận được: {dim}")

    raw_nodes: list[dict] = list(sub.get("nodes") or ())
    raw_edges: list[tuple[int, int, int, str]] = list(sub.get("edges") or ())

    kf = "Nghề O*NET" if kind_filter == "Ngành" else kind_filter
    if kf and kf != "Tất cả":
        kept_nodes = [n for n in raw_nodes if n["kind"] == kf]
        kept_set = {n["nid"] for n in kept_nodes}
        kept_edges = [e for e in raw_edges if e[0] in kept_set and e[1] in kept_set]
    else:
        kept_nodes = raw_nodes
        kept_edges = raw_edges

    truncated_render = False
    if max_render_nodes is not None and len(kept_nodes) > int(max_render_nodes):
        truncated_render = True
        kept_nodes, kept_edges = _select_render_budget(
            sub, kept_nodes, kept_edges, int(max_render_nodes),
        )

    n = len(kept_nodes)
    if n == 0:
        n_cols = ["node_id", "nid", "raw_id", "label", "kind", "degree", "sub_degree", "size", "x", "y"]
        e_cols = ["source", "target", "x0", "y0", "x1", "y1", "kind"]
        if dim == 3:
            n_cols.append("z")
            e_cols.extend(["z0", "z1"])
        return (
            pd.DataFrame(columns=n_cols),
            pd.DataFrame(columns=e_cols),
            {
                "n_nodes_total": len(raw_nodes),
                "n_edges_total": len(raw_edges),
                "n_nodes_rendered": 0,
                "n_edges_rendered": 0,
                "truncated_render": False,
                "layout_algo": "empty",
            },
        )

    # Tính bậc trên đồ thị đang hiển thị
    vis_deg: dict[int, int] = {nd["nid"]: 0 for nd in kept_nodes}
    for u, v, _, _ in kept_edges:
        vis_deg[u] += 1
        vis_deg[v] += 1

    nid_to_idx = {nd["nid"]: i for i, nd in enumerate(kept_nodes)}
    src_idx = [nid_to_idx[e[0]] for e in kept_edges]
    dst_idx = [nid_to_idx[e[1]] for e in kept_edges]

    if n <= 400:
        pos = spring_layout(n, src_idx, dst_idx, seed=42, iterations=70, dim=dim)
        algo = "spring"
    else:
        pos = _fast_radial_layout(kept_nodes, dim=dim)
        algo = "radial_o_n"

    # Ghi nhận bậc thực tế trên đồ thị đang vẽ (`vis_deg`) và giữ `sub_degree` tham khảo
    node_ids = [f"n{nd['nid']}" for nd in kept_nodes]
    degs = np.array([int(vis_deg[nd["nid"]]) for nd in kept_nodes], dtype=int)
    sub_degs = np.array([int(nd["degree"]) for nd in kept_nodes], dtype=int)

    nodes_data: dict = {
        "node_id": node_ids,
        "nid": [int(nd["nid"]) for nd in kept_nodes],
        "raw_id": [str(nd["raw_id"]) for nd in kept_nodes],
        "label": [str(nd["label"]) for nd in kept_nodes],
        "kind": [str(nd["kind"]) for nd in kept_nodes],
        "degree": degs,
        "sub_degree": sub_degs,
        "size": np.sqrt(degs + 1),
        "x": pos[:, 0],
        "y": pos[:, 1],
    }
    if dim == 3:
        nodes_data["z"] = pos[:, 2]
    nodes_df = pd.DataFrame(nodes_data)

    edges_data: dict = {
        "source": [f"n{e[0]}" for e in kept_edges],
        "target": [f"n{e[1]}" for e in kept_edges],
        "x0": [float(pos[ia, 0]) for ia in src_idx],
        "y0": [float(pos[ia, 1]) for ia in src_idx],
        "x1": [float(pos[ib, 0]) for ib in dst_idx],
        "y1": [float(pos[ib, 1]) for ib in dst_idx],
        "kind": [str(e[3]) for e in kept_edges],
    }
    if dim == 3:
        edges_data["z0"] = [float(pos[ia, 2]) for ia in src_idx]
        edges_data["z1"] = [float(pos[ib, 2]) for ib in dst_idx]
    edges_df = pd.DataFrame(edges_data)

    render_meta = {
        "n_nodes_total": len(raw_nodes),
        "n_edges_total": len(raw_edges),
        "n_nodes_rendered": len(kept_nodes),
        "n_edges_rendered": len(kept_edges),
        "truncated_render": truncated_render,
        "layout_algo": algo,
    }
    return nodes_df, edges_df, render_meta
