"""Trang 2 — Đồ thị việc làm: đồ thị 2D/3D tương tác trên bộ dữ liệu CareerBuilder + O*NET (V3).

BỐ CỤC:
    [ Tiêu đề: Đồ thị việc làm ]            (KHÔNG còn câu hỏi đầu trang)
    [ Tìm kiếm ........................ ] [ Loại ▼ ] [ 2D | 3D ]  |  4 thẻ số liệu nhỏ
    [ ĐỒ THỊ 2D/3D TƯƠNG TÁC — hero 620px ]                       |  (dọc, bên phải)
    [                                     ]                       |  panel chi tiết
    [ hai biểu đồ cột phụ + bảng số liệu — trong expander ]
"""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.components import (bar_chart, data_note, finding, graph_html,
                            load_json, render_chart, spring_layout, theme)
from app.components.graph3d import graph_html_3d
from app.paths import PATHS

GRAPH_HEIGHT = 620

# Bốn loại nút của đồ thị V3 (giữ tương thích cả "Nghề O*NET" và "Ngành")
_KIND_COLOR = {
    "Người dùng": "#7b241c",
    "Tin tuyển dụng": "#e8836b",
    "Kỹ năng": "#0EA5E9",
    "Nghề O*NET": "#10B981",
    "Ngành": "#10B981",
}
_KIND_ORDER = ["Người dùng", "Tin tuyển dụng", "Kỹ năng", "Nghề O*NET"]
_KIND_ALL = ["Tất cả", *_KIND_ORDER]


@lru_cache(maxsize=1)
def _load_v3_subgraph_base() -> dict:
    """Lấy mẫu đồ thị con tất định từ `artifacts/v3/graph.npz` (264.995 nút, 764.364 cạnh).

    Thuật toán chọn mẫu tất định (< 0.3s):
      1. Chọn 30 nút Nghề O*NET (`occ`) có nhiều kết nối `job-occ` và `occ-skill` nhất.
      2. Chọn 120 nút Kỹ năng (`skill`) phổ biến nhất nối với 30 nghề đó (`edge_type == 2`).
      3. Chọn đúng 200 nút Tin tuyển dụng (`job`) thuộc 30 nghề trên (`edge_type == 1`),
         ưu tiên các tin có nhiều lượt ứng tuyển nhất để đảm bảo liên thông.
      4. Chọn 80 nút Người dùng (`user`) có ứng tuyển vào 200 tin vừa chọn (`edge_type == 0`),
         sao cho tổng cạnh Riêng tư (`user-job` + `user-occ`) < số cạnh Công khai (`share < 0.5`).
      5. Gán nhãn thật từ `job_titles.json`, `user_titles.json`, `occ_ids` và `skill_names`.
    """
    v3_dir = PATHS["v3"]
    z = np.load(v3_dir / "graph.npz", allow_pickle=False)
    nU = int(z["n_users"])         # 171,807
    nJ = int(z["n_jobs"])          # 84,845
    nO = int(z["n_occupations"])   # 583
    nS = int(z["n_skills"])        # 7,760
    n_nodes = int(z["n_nodes"])    # 264,995

    off_job = nU
    off_occ = nU + nJ
    off_skill = nU + nJ + nO

    ei, et = z["edge_index"], z["edge_type"]

    # 1. Chọn 30 nút Nghề O*NET có cả cạnh job-occ (et==1) và occ-skill (et==2)
    m1 = et == 1
    m2 = et == 2
    occ_job_deg = np.bincount(ei[1][m1], minlength=n_nodes)[off_occ:off_skill]
    occ_sk_deg = np.bincount(ei[0][m2], minlength=n_nodes)[off_occ:off_skill]
    valid_occ = np.where((occ_job_deg > 0) & (occ_sk_deg > 0))[0]
    occ_score = occ_job_deg[valid_occ] + occ_sk_deg[valid_occ] * 5
    top_occ_local = valid_occ[np.argsort(-occ_score)[:30]]
    top_occ = {int(off_occ + i) for i in top_occ_local}
    assert top_occ, "không chọn được nghề O*NET nào"

    # 2. Chọn 120 nút Kỹ năng phổ biến nhất nối với 30 nghề trên (et==2)
    m2_occ = m2 & np.isin(ei[0], list(top_occ))
    sk_deg = np.bincount(ei[1][m2_occ], minlength=n_nodes)[off_skill:n_nodes]
    top_sk_local = np.argsort(-sk_deg)[:120]
    top_skills = {int(off_skill + i) for i in top_sk_local if sk_deg[i] > 0}
    assert top_skills, "không chọn được kỹ năng nào"

    # 3. Chọn đúng 200 nút Tin tuyển dụng nối với 30 nghề trên (et==1)
    m0 = et == 0
    job_app_deg = np.bincount(ei[1][m0], minlength=n_nodes)
    m1_occ = m1 & np.isin(ei[1], list(top_occ))
    cand_jobs = np.unique(ei[0][m1_occ])
    cand_order = np.argsort(-job_app_deg[cand_jobs])
    n_job_sample = min(200, nJ, len(cand_jobs))
    job_nodes = [int(j) for j in cand_jobs[cand_order[:n_job_sample]]]
    assert len(job_nodes) == n_job_sample, "không chọn đủ 200 tin tuyển dụng"
    assert all(off_job <= j < off_occ for j in job_nodes), (
        "job_nodes phải nằm trọn trong dải nút tin tuyển dụng"
    )

    # 4. Chọn 80 nút Người dùng có ứng tuyển vào 200 tin trên (et==0)
    m0_job = m0 & np.isin(ei[1], job_nodes)
    cand_users, user_job_counts = np.unique(ei[0][m0_job], return_counts=True)
    u_order = np.argsort(-user_job_counts)
    user_nodes = [int(u) for u in cand_users[u_order[:80]]]

    keep_arr = np.fromiter(
        set(user_nodes) | set(job_nodes) | top_occ | top_skills,
        dtype=np.int64,
    )
    m = np.isin(ei[0], keep_arr) & np.isin(ei[1], keep_arr)
    s, d, t = ei[0][m], ei[1][m], et[m]

    # Bỏ cạnh trùng
    pairs: set[tuple[int, int]] = set()
    es: list[int] = []
    ed: list[int] = []
    ek: list[str] = []
    for a_val, b_val, typ_val in zip(s.tolist(), d.tolist(), t.tolist()):
        key = (a_val, b_val) if a_val < b_val else (b_val, a_val)
        if key in pairs:
            continue
        pairs.add(key)
        es.append(a_val)
        ed.append(b_val)
        # edge_type 1 (job-occ) & 2 (occ-skill) là Công khai; 0 (user-job) & 3 (user-occ) là Riêng tư
        ek.append("Công khai" if typ_val in (1, 2) else "Riêng tư")

    nodes_used = sorted(set(es) | set(ed))
    idx = {n: i for i, n in enumerate(nodes_used)}

    # Đọc nhãn thật từ job_titles.json và user_titles.json
    job_titles_path = v3_dir / "job_titles.json"
    user_titles_path = v3_dir / "user_titles.json"
    job_meta: dict = {}
    user_meta: dict = {}
    if job_titles_path.exists():
        with open(job_titles_path, encoding="utf-8") as f:
            job_meta = json.load(f)
    if user_titles_path.exists():
        with open(user_titles_path, encoding="utf-8") as f:
            user_meta = json.load(f)

    user_ids = z["user_ids"]
    job_ids = z["job_ids"]
    occ_ids = z["occ_ids"]
    skill_names = z["skill_names"]

    kinds: list[str] = []
    labels: list[str] = []
    for n in nodes_used:
        if n < off_job:
            kinds.append("Người dùng")
            uid = str(user_ids[n])
            u_info = user_meta.get(uid) or {}
            u_title = str(u_info.get("title") or "").strip()
            if u_title:
                labels.append(f"Ứng viên #{uid} · {u_title[:36]}")
            else:
                labels.append(f"Ứng viên #{uid}")
        elif n < off_occ:
            kinds.append("Tin tuyển dụng")
            jid = str(job_ids[n - off_job])
            j_info = job_meta.get(jid) or {}
            j_title = str(j_info.get("title") or "").strip()
            j_emp = str(j_info.get("employer") or "").strip()
            if j_title and j_emp:
                labels.append(f"{j_title[:42]} ({j_emp[:20]})")
            elif j_title:
                labels.append(j_title[:60])
            else:
                labels.append(f"Tin #{jid}")
        elif n < off_skill:
            kinds.append("Nghề O*NET")
            occ_code = str(occ_ids[n - off_occ])
            labels.append(f"Nghề O*NET {occ_code}")
        else:
            kinds.append("Kỹ năng")
            sk_name = str(skill_names[n - off_skill]).strip()
            labels.append(sk_name[:60] if sk_name else f"Kỹ năng #{n - off_skill}")

    deg = np.zeros(len(nodes_used), dtype=int)
    src_idx = [idx[a] for a in es]
    dst_idx = [idx[b] for b in ed]
    for ia, ib in zip(src_idx, dst_idx):
        deg[ia] += 1
        deg[ib] += 1

    return {
        "n_nodes_used": len(nodes_used),
        "src_idx": src_idx,
        "dst_idx": dst_idx,
        "ek": ek,
        "kinds": kinds,
        "labels": labels,
        "deg": deg,
    }


@lru_cache(maxsize=2)
def _build_graph_view_cached(dim: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = _load_v3_subgraph_base()
    pos = spring_layout(
        base["n_nodes_used"],
        base["src_idx"],
        base["dst_idx"],
        iterations=70,
        dim=dim,
    )
    deg = base["deg"]
    src_idx = base["src_idx"]
    dst_idx = base["dst_idx"]

    node_df = pd.DataFrame({
        "x": pos[:, 0],
        "y": pos[:, 1],
        "kind": base["kinds"],
        "label": base["labels"],
        "degree": deg.astype(int),
        "size": np.sqrt(deg + 1),
    })
    edge_df = pd.DataFrame({
        "x": [pos[ia, 0] for ia in src_idx],
        "y": [pos[ia, 1] for ia in src_idx],
        "x2": [pos[ib, 0] for ib in dst_idx],
        "y2": [pos[ib, 1] for ib in dst_idx],
        "edge_kind": base["ek"],
    })
    if dim == 3:
        node_df["z"] = pos[:, 2]
        edge_df["z"] = [pos[ia, 2] for ia in src_idx]
        edge_df["z2"] = [pos[ib, 2] for ib in dst_idx]
    return node_df, edge_df


@st.cache_data(show_spinner="Đang dựng đồ thị CareerBuilder + O*NET (V3)…")
def build_graph_view(dim: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lấy đồ thị con để vẽ 2D/3D từ `artifacts/v3/graph.npz`.

    `dim=2` → DataFrame có x, y (cho đồ thị 2D).
    `dim=3` → thêm cột z (cho đồ thị 3D).
    Cùng một tập nút/cạnh và cùng công thức bố cục.
    """
    node_df, edge_df = _build_graph_view_cached(dim)
    return node_df.copy(), edge_df.copy()


# =====================================================================
# Tiện ích cho thanh tìm kiếm + bảng chi tiết
# =====================================================================
def _fold(text: str) -> str:
    """Bỏ dấu tiếng Việt để gõ không dấu vẫn tìm ra nút."""
    s = str(text).lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _index_graph(nodes: pd.DataFrame,
                 edges: pd.DataFrame) -> list[dict[int, set[str]]]:
    """Danh sách láng giềng của từng nút, nối cạnh qua TOẠ ĐỘ."""
    keyed: dict[tuple[float, float], int] = {}
    for i, (x, y) in enumerate(zip(nodes["x"].to_numpy(),
                                   nodes["y"].to_numpy())):
        keyed[(round(float(x), 6), round(float(y), 6))] = i

    nbrs: list[dict[int, set[str]]] = [dict() for _ in range(len(nodes))]
    cols = ("x", "y", "x2", "y2", "edge_kind")
    for x, y, x2, y2, kind in zip(*(edges[c].to_numpy() for c in cols)):
        a = keyed.get((round(float(x), 6), round(float(y), 6)))
        b = keyed.get((round(float(x2), 6), round(float(y2), 6)))
        if a is None or b is None or a == b:
            continue
        nbrs[a].setdefault(b, set()).add(str(kind))
        nbrs[b].setdefault(a, set()).add(str(kind))
    return nbrs


def _search_nodes(nodes: pd.DataFrame, q: str, kind: str) -> pd.DataFrame:
    """Lọc nút theo từ khoá (không phân biệt hoa/thường, không cần dấu)."""
    term = _fold(q).strip()
    if not term:
        return nodes.iloc[0:0]
    hay = nodes["label"].map(_fold)
    hit = hay.str.contains(term, regex=False, na=False)
    if kind != "Tất cả":
        hit &= nodes["kind"] == kind
    out = nodes[hit]
    return out.sort_values("degree", ascending=False)


def _neighbours_html(nodes: pd.DataFrame, nbrs, i: int, limit: int = 20) -> str:
    """HTML danh sách láng giềng (kèm loại + loại cạnh), tối đa `limit` mục."""
    deg = nodes["degree"].to_numpy()
    items = sorted(nbrs[i].items(), key=lambda kv: -int(deg[kv[0]]))
    rows = []
    for j, kinds in items[:limit]:
        row = nodes.iloc[j]
        color = _KIND_COLOR.get(str(row["kind"]), "#7f8c8d")
        edge = " · ".join(sorted(kinds))
        rows.append(
            f"<div class='gx-nbr'>"
            f"<span class='gx-dot' style='background:{color}'></span>"
            f"<span style='flex:1 1 auto;overflow:hidden;text-overflow:ellipsis;"
            f"white-space:nowrap'>{row['label']}</span>"
            f"<span class='gx-hit-kind'>{row['kind']} · {edge}</span></div>")
    if len(items) > limit:
        rows.append(f"<div class='gx-hint'>… và {len(items) - limit} "
                    f"láng giềng khác.</div>")
    if not rows:
        rows.append("<div class='gx-hint'>Nút này không có láng giềng.</div>")
    return "".join(rows)


def _render_detail(nodes: pd.DataFrame, nbrs, i: int) -> None:
    """Bảng chi tiết một nút: nhãn, loại, bậc, danh sách láng giềng."""
    row = nodes.iloc[i]
    kind = str(row["kind"])
    color = _KIND_COLOR.get(kind, "#7f8c8d")
    total = len(nbrs[i])
    st.markdown(
        f"<div class='gx-panel' style='border-left-color:{color}'>"
        f"<div class='gx-panel-kind'>"
        f"<span class='gx-dot' style='background:{color};display:inline-block;"
        f"vertical-align:middle;margin-right:5px'></span>{kind}</div>"
        f"<div class='gx-panel-name'>{row['label']}</div>"
        f"<div class='gx-panel-meta'>Bậc (số cạnh nối trực tiếp): "
        f"<b>{int(row['degree'])}</b> · Láng giềng: <b>{total}</b></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='gx-side-title'>Láng giềng</div>",
                unsafe_allow_html=True)
    st.markdown(_neighbours_html(nodes, nbrs, i), unsafe_allow_html=True)


def _mini_cards(items: list[dict]) -> None:
    """4 thẻ số liệu THU NHỎ, xếp dọc."""
    html = "".join(
        f"<div class='gx-mini-card {it.get('cls', '')}'>"
        f"<div class='gx-mini-val'>{it['value']}</div>"
        f"<div class='gx-mini-lab'>{it['label']}</div></div>"
        for it in items)
    st.markdown(html, unsafe_allow_html=True)


# =====================================================================
# Trang
# =====================================================================
def render() -> None:
    st.markdown("<h1 class='gx-title'>Đồ thị việc làm (CareerBuilder + O*NET V3)</h1>",
                unsafe_allow_html=True)

    meta = load_json(str(PATHS["v3"] / "meta.json"))
    nodes_meta = meta["nodes"]
    edges_meta = meta["edges"]
    by_type = edges_meta["by_type"]

    n_nodes_full = int(nodes_meta["n_nodes"])          # 264,995
    n_users_full = int(nodes_meta["n_users"])          # 171,807
    n_jobs_full = int(nodes_meta["n_jobs"])            # 84,845
    n_occ_full = int(nodes_meta["n_occupations"])      # 583
    n_skills_full = int(nodes_meta["n_skills"])        # 7,760

    e_user_job = int(by_type["0_user_job"])            # 436,893
    e_job_occ = int(by_type["1_job_occupation"])       # 26,678
    e_occ_skill = int(by_type["2_occupation_skill"])   # 25,866
    e_user_occ = int(by_type["3_user_occupation"])     # 274,927

    public_edges_full = e_job_occ + e_occ_skill        # 52,544
    private_edges_full = e_user_job + e_user_occ       # 711,820

    nodes, edges = build_graph_view(dim=2)
    nodes = nodes.reset_index(drop=True)
    edges = edges.reset_index(drop=True)
    nbrs = _index_graph(nodes, edges)

    if "gx-sel" not in st.session_state:
        st.session_state["gx-sel"] = None
    if "gx-dim" not in st.session_state:
        st.session_state["gx-dim"] = "2D"

    c_left, c_right = st.columns([1, 0.2], gap="medium")

    # ------------ CỘT TRÁI: tìm kiếm + ĐỒ THỊ HERO ------------------
    with c_left:
        c_q, c_kind, c_dim = st.columns([3, 1.1, 0.9], gap="small")
        with c_q:
            q = st.text_input("Tìm trong đồ thị",
                              placeholder="gõ tên nghề, kỹ năng (Python, SAP, Excel), nhà tuyển dụng…",
                              label_visibility="collapsed",
                              key="gx-q")
        with c_kind:
            kind_filter = st.selectbox("Loại", _KIND_ALL,
                                       label_visibility="collapsed",
                                       key="gx-kind")
        with c_dim:
            dim = st.radio("Chế độ xem", ["2D", "3D"], horizontal=True,
                           label_visibility="collapsed", key="gx-dim-radio",
                           index=0 if st.session_state["gx-dim"] == "2D" else 1)
            st.session_state["gx-dim"] = dim

        _hits = _search_nodes(nodes, q, kind_filter)
        _hit_positions = [int(i) for i in _hits.index] if len(_hits) else []

        with st.container(key="gx-graph-card"):
            if st.session_state["gx-dim"] == "3D":
                nodes3, edges3 = build_graph_view(dim=3)
                nodes3 = nodes3.reset_index(drop=True)
                edges3 = edges3.reset_index(drop=True)

                _hl3: list[int] = []
                if len(_hits):
                    _hit_labels = set(_hits["label"].astype(str))
                    _hl3 = [i for i, lab in enumerate(nodes3["label"].astype(str))
                            if lab in _hit_labels]

                _sig3 = "none" if not _hl3 else f"{len(_hl3)}-{_hl3[0]}"
                with st.container(key=f"gx-graph-3d-{_sig3}"):
                    components.html(
                        graph_html_3d(nodes3, edges3, height=GRAPH_HEIGHT,
                                      highlight=_hl3),
                        height=GRAPH_HEIGHT + 4, scrolling=False)
            else:
                _hl_sig = "none" if not _hit_positions else f"{len(_hit_positions)}-{_hit_positions[0]}"
                with st.container(key=f"gx-graph-2d-{_hl_sig}"):
                    components.html(
                        graph_html(nodes, edges, height=GRAPH_HEIGHT,
                                   show_search=False,
                                   highlight=_hit_positions),
                        height=GRAPH_HEIGHT + 4, scrolling=False)

    # ---------- CỘT PHẢI: 4 thẻ nhỏ + tìm kiếm + chi tiết -----------
    with c_right:
        _mini_cards([
            {"value": f"{n_nodes_full:,}", "label": "Nút (đồ thị đầy đủ)"},
            {"value": f"{public_edges_full:,}",
             "label": f"Cạnh công khai — máy chủ thấy ({e_job_occ:,} tin–nghề + {e_occ_skill:,} nghề–kỹ năng)",
             "cls": "is-public"},
            {"value": f"{private_edges_full:,}",
             "label": f"Cạnh riêng tư — chỉ ở khách hàng ({e_user_job:,} ứng tuyển + {e_user_occ:,} hồ sơ nghề)",
             "cls": "is-private"},
            {"value": f"{n_occ_full:,}",
             "label": f"Nút nghề O*NET ({n_skills_full:,} kỹ năng)"},
        ])

        hits = _hits
        if q.strip():
            st.markdown("<div class='gx-side-title'>Kết quả tìm kiếm</div>",
                        unsafe_allow_html=True)
            if hits.empty:
                st.markdown(
                    "<div class='gx-hint'>Không tìm thấy nút nào khớp "
                    f"“{q.strip()}”. Thử từ khoá ngắn hơn hoặc đổi loại "
                    "nút.</div>", unsafe_allow_html=True)
            else:
                st.caption(f"{len(hits):,} nút khớp")
                for i in hits.index[:12]:
                    row = nodes.iloc[i]
                    label = str(row["label"])
                    short = label if len(label) <= 34 else label[:33] + "…"
                    if st.button(f"{short}", key=f"gx-hit-{i}",
                                 width="stretch",
                                 help=f"{row['kind']} · "
                                      f"bậc {int(row['degree'])}"):
                        st.session_state["gx-sel"] = int(i)

        sel = st.session_state.get("gx-sel")
        if sel is not None and 0 <= int(sel) < len(nodes):
            if st.button("✕ Đóng chi tiết", key="gx-close",
                         width="stretch"):
                st.session_state["gx-sel"] = None
                sel = None
        if sel is not None and 0 <= int(sel) < len(nodes):
            _render_detail(nodes, nbrs, int(sel))
        elif not q.strip():
            st.markdown(
                "<div class='gx-hint'>Gõ vào ô tìm kiếm để lọc nút theo "
                "4 loại, rồi bấm một kết quả để xem chi tiết ở đây. "
                "Bấm thẳng một nút trong đồ thị cũng mở bảng chi tiết "
                "ngay trong khung.</div>",
                unsafe_allow_html=True)

    # ---------------- Dưới hero: phát hiện + phần phụ trong expander -----
    finding(
        "Ranh giới bảo mật rõ ràng: máy chủ chỉ giữ khung xương Nghề O*NET – Kỹ năng",
        f"<b>{public_edges_full:,} cạnh công khai</b> (<b>{e_job_occ:,}</b> cạnh tin–nghề O*NET + "
        f"<b>{e_occ_skill:,}</b> cạnh nghề O*NET–kỹ năng công nghệ) nằm trên máy chủ làm cầu nối truyền thông tin; "
        f"toàn bộ <b>{private_edges_full:,} cạnh riêng tư</b> (<b>{e_user_job:,}</b> lượt ứng tuyển user–job + "
        f"<b>{e_user_occ:,}</b> hồ sơ lịch sử nghề user–occupation) giữ tuyệt đối tại <b>9.116</b> silo nhà tuyển dụng.",
        "good",
    )

    with st.expander("Cách đọc đồ thị", expanded=False):
        st.caption(
            f"Đồ thị đầy đủ có **{n_nodes_full:,} nút** và **{int(edges_meta['n_edges_stored']):,} cạnh**. "
            "Khung tương tác phía trên hiển thị **đồ thị con đại diện (430 nút)**: giữ 30 nghề O*NET trung tâm, "
            "120 kỹ năng công nghệ phổ biến nhất, 200 tin tuyển dụng tiêu biểu có gắn mã nghề O*NET và 80 ứng viên "
            "nộp đơn liên thông giữa các tin đó để vẽ 2D/3D mượt mà mà vẫn giữ nguyên cấu trúc liên kết thật."
        )

    with st.expander("Cấu trúc đồ thị theo loại nút và phân bố nhà tuyển dụng / nghề O*NET",
                     expanded=False):
        with theme.grid(2, "chart-phu"):
            with st.container():
                df_nodes = pd.DataFrame({
                    "loại": ["Người dùng", "Tin tuyển dụng", "Kỹ năng", "Nghề O*NET"],
                    "số_nút": [n_users_full, n_jobs_full, n_skills_full, n_occ_full],
                })
                render_chart(bar_chart(df_nodes, "loại", "số_nút",
                                       title="Số nút theo 4 loại thực thể (264.995 nút)",
                                       height=280, value_fmt=",.0f"),
                             delay_ms=60)

            with st.container():
                top_emps = meta["employer_extraction"]["top20_employers_by_apps"][:12]
                df_emps = pd.DataFrame([
                    {"nhà_tuyển_dụng": str(name), "số_đơn": int(cnt)}
                    for name, cnt in top_emps
                ])
                render_chart(bar_chart(df_emps, "số_đơn", "nhà_tuyển_dụng",
                                       horizontal=True,
                                       title="Top 12 Nhà tuyển dụng (Node FL) có nhiều lượt ứng tuyển nhất",
                                       height=280, value_fmt=",.0f"),
                             delay_ms=120)

        st.markdown("**Bảng số liệu của hai biểu đồ trên**")
        t1, t2 = st.columns(2, gap="medium")
        with t1:
            st.markdown("**Số nút theo loại thực thể**")
            st.dataframe(df_nodes, hide_index=True, width="stretch")
        with t2:
            st.markdown("**Top 12 Nhà tuyển dụng (Node FL) theo lượt ứng tuyển**")
            st.dataframe(df_emps, hide_index=True, width="stretch")

        data_note(
            f"Chuẩn hóa nghề theo O*NET-SOC 6 ký tự (soc[:7], {n_occ_full} nghề); "
            f"kỹ năng trích từ O*NET Technology Skills.txt ({n_skills_full:,} kỹ năng). "
            f"{edges_meta['n_jobs_with_occupation_edge']:,}/{n_jobs_full:,} tin ({edges_meta['pct_jobs_with_occupation_edge']}%) "
            "ánh xạ được trực tiếp vào mã nghề O*NET."
        )


def alt_log(df: pd.DataFrame):
    import altair as alt
    return alt.Y("số_nút:Q", scale=alt.Scale(type="log"), title="Số nút")
