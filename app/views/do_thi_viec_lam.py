"""Trang 2 — Đồ thị việc làm: đồ thị 2D/3D tương tác trên bộ dữ liệu CareerBuilder + O*NET (V3).

BỐ CỤC:
    [ Tiêu đề: Đồ thị việc làm ]            (KHÔNG còn câu hỏi đầu trang)
    [ Tìm kiếm ........................ ] [ Loại ▼ ] [ 2D | 3D ]  |  4 thẻ số liệu nhỏ
    [ ĐỒ THỊ 2D/3D TƯƠNG TÁC — hero 620px ]                       |  (dọc, bên phải)
    [                                     ]                       |  panel chi tiết
    [ hai biểu đồ cột phụ + bảng số liệu — trong expander ]
"""

from __future__ import annotations

import hashlib
import html
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
from app.components.v3_graph import (V3GraphIndex, extract_ego_subgraph,
                                     extract_silo_subgraph,
                                     layout_subgraph_to_dfs, load_v3_index,
                                     search_all_nodes)
from app.paths import PATHS

GRAPH_HEIGHT = 620
_MODE_SILO = "Silo Nhà tuyển dụng"
_MODE_GLOBAL = "Tìm kiếm toàn bộ (264.995 nút)"

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
    """Danh sách láng giềng của từng nút (ưu tiên nối qua `node_id`/`source`/`target`, fallback toạ độ)."""
    nbrs: list[dict[int, set[str]]] = [dict() for _ in range(len(nodes))]
    if nodes.empty or edges.empty:
        return nbrs

    if "node_id" in nodes.columns and {"source", "target"} <= set(edges.columns):
        id_to_idx = {str(nid): i for i, nid in enumerate(nodes["node_id"].tolist())}
        kind_col = "edge_kind" if "edge_kind" in edges.columns else "kind"
        for src, tgt, kind in zip(
            edges["source"].tolist(),
            edges["target"].tolist(),
            edges[kind_col].tolist(),
        ):
            a = id_to_idx.get(str(src))
            b = id_to_idx.get(str(tgt))
            if a is None or b is None or a == b:
                continue
            nbrs[a].setdefault(b, set()).add(str(kind))
            nbrs[b].setdefault(a, set()).add(str(kind))
        return nbrs

    keyed: dict[tuple[float, float], int] = {}
    for i, (x, y) in enumerate(zip(nodes["x"].to_numpy(),
                                   nodes["y"].to_numpy())):
        keyed[(round(float(x), 6), round(float(y), 6))] = i

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
        edge = html.escape(" · ".join(sorted(kinds)))
        label_esc = html.escape(str(row["label"]))
        kind_esc = html.escape(str(row["kind"]))
        rows.append(
            f"<div class='gx-nbr'>"
            f"<span class='gx-dot' style='background:{color}'></span>"
            f"<span style='flex:1 1 auto;overflow:hidden;text-overflow:ellipsis;"
            f"white-space:nowrap'>{label_esc}</span>"
            f"<span class='gx-hit-kind'>{kind_esc} · {edge}</span></div>")
    if len(items) > limit:
        rows.append(f"<div class='gx-hint'>… và {len(items) - limit} "
                    f"láng giềng khác.</div>")
    if not rows:
        rows.append("<div class='gx-hint'>Nút này không có láng giềng.</div>")
    return "".join(rows)


@st.cache_resource(show_spinner="Đang nạp chỉ mục đồ thị V3 (264.995 nút)…")
def get_v3_index() -> V3GraphIndex:
    """Singleton chỉ mục đồ thị V3 cho toàn bộ 264.995 nút và 9.116 silo."""
    return load_v3_index()


def _select_node(nid: int) -> None:
    st.session_state["gx-sel-nid"] = int(nid)


def _close_detail() -> None:
    st.session_state["gx-sel-nid"] = None


def _on_mode_change() -> None:
    st.session_state["gx-sel-nid"] = None
    st.session_state["gx-ego-extra"] = []


def _on_silo_change() -> None:
    st.session_state["gx-sel-nid"] = None


def _on_ego_pick() -> None:
    picked = st.session_state.get("gx-ego-pick")
    st.session_state["gx-sel-nid"] = int(picked) if picked is not None else None


def _select_ego_center(nid: int) -> None:
    st.session_state["gx-ego-center"] = int(nid)
    st.session_state["gx-ego-extra"] = []
    st.session_state["gx-sel-nid"] = int(nid)


def _expand_ego_node(nid: int) -> None:
    extra = list(st.session_state.get("gx-ego-extra") or [])
    nid_i = int(nid)
    if nid_i not in extra:
        extra.append(nid_i)
    st.session_state["gx-ego-extra"] = extra
    st.session_state["gx-sel-nid"] = nid_i


def _reset_ego_extra() -> None:
    st.session_state["gx-ego-extra"] = []


def _jump_to_silo(cid: int) -> None:
    st.session_state["gx-mode"] = _MODE_SILO
    st.session_state["gx-silo"] = int(cid)
    st.session_state["gx-sel-nid"] = None
    st.session_state["gx-ego-extra"] = []


def _has_unshown_neighbors(
    index: V3GraphIndex,
    nid: int,
    displayed_nids: set[int],
) -> bool:
    """Kiểm tra `nid` còn ít nhất 1 láng giềng chưa xuất hiện trong `displayed_nids`."""
    s0, s1 = int(index.starts[nid]), int(index.starts[nid + 1])
    for v in index.nbrs[s0:s1].tolist():
        if v not in displayed_nids:
            return True
    return False


def _render_detail(
    nodes: pd.DataFrame,
    nbrs,
    i: int,
    *,
    index: V3GraphIndex | None = None,
) -> None:
    """Bảng chi tiết một nút: nhãn, loại, bậc, danh sách láng giềng."""
    row = nodes.iloc[i]
    kind = str(row["kind"])
    color = _KIND_COLOR.get(kind, "#7f8c8d")
    total = len(nbrs[i])

    extra_lines: list[str] = []
    nid_val = int(row["nid"]) if "nid" in nodes.columns else None
    if "sub_degree" in nodes.columns:
        sub_deg_val = int(row["sub_degree"])
        if sub_deg_val != int(row["degree"]):
            extra_lines.append(f"Bậc trong tập trích xuất: <b>{sub_deg_val:,}</b>")
    if index is not None and nid_val is not None:
        nmeta = index.node_meta(nid_val)
        gdeg = nmeta.get("global_degree")
        if gdeg is not None and int(gdeg) != int(row["degree"]):
            extra_lines.append(f"Bậc toàn đồ thị: <b>{int(gdeg):,}</b>")
        if kind == "Tin tuyển dụng":
            emp = nmeta.get("employer") or ""
            loc = ", ".join(p for p in (nmeta.get("city"), nmeta.get("state")) if p)
            if emp:
                extra_lines.append(f"Nhà tuyển dụng: <b>{html.escape(str(emp))}</b>")
            if loc:
                extra_lines.append(f"Địa điểm: {html.escape(str(loc))}")
        elif kind == "Nghề O*NET" and nmeta.get("occ_title"):
            extra_lines.append(f"Mã O*NET-SOC: <b>{html.escape(str(nmeta.get('occ_code') or ''))}</b>")
        elif kind == "Người dùng" and nmeta.get("occupation"):
            extra_lines.append(f"Nghề hồ sơ: {html.escape(str(nmeta.get('occupation')))}")

    extra_html = (
        "<div class='gx-panel-meta' style='margin-top:3px'>" + " · ".join(extra_lines) + "</div>"
        if extra_lines else ""
    )

    st.markdown(
        f"<div class='gx-panel' style='border-left-color:{color}'>"
        f"<div class='gx-panel-kind'>"
        f"<span class='gx-dot' style='background:{color};display:inline-block;"
        f"vertical-align:middle;margin-right:5px'></span>{html.escape(kind)}</div>"
        f"<div class='gx-panel-name'>{html.escape(str(row['label']))}</div>"
        f"<div class='gx-panel-meta'>Bậc đang vẽ: "
        f"<b>{int(row['degree'])}</b> · Láng giềng: <b>{total}</b></div>"
        f"{extra_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='gx-side-title'>Láng giềng</div>",
                unsafe_allow_html=True)
    st.markdown(_neighbours_html(nodes, nbrs, i), unsafe_allow_html=True)

    if nbrs[i] and "nid" in nodes.columns:
        deg_arr = nodes["degree"].to_numpy()
        top_items = sorted(nbrs[i].items(), key=lambda kv: (-int(deg_arr[kv[0]]), int(kv[0])))[:6]
        st.caption("Chọn nhanh láng giềng")
        for j, kinds in top_items:
            nrow = nodes.iloc[j]
            nnid = int(nrow["nid"])
            nlabel = str(nrow["label"])
            nshort = nlabel if len(nlabel) <= 30 else nlabel[:29] + "…"
            edge_txt = " · ".join(sorted(kinds))
            st.button(
                f"↪ {nshort}",
                key=f"gx-nbr-{nnid}",
                width="stretch",
                help=f"{nrow['kind']} · {edge_txt} · bậc {int(nrow['degree'])}",
                on_click=_select_node,
                args=(nnid,),
            )


def _mini_cards(items: list[dict]) -> None:
    """4 thẻ số liệu THU NHỎ, xếp dọc."""
    cards_html = "".join(
        f"<div class='gx-mini-card {html.escape(str(it.get('cls', '')))}'>"
        f"<div class='gx-mini-val'>{html.escape(str(it['value']))}</div>"
        f"<div class='gx-mini-lab'>{html.escape(str(it['label']))}</div></div>"
        for it in items)
    st.markdown(cards_html, unsafe_allow_html=True)


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

    idx = get_v3_index()

    if "gx-sel-nid" not in st.session_state:
        st.session_state["gx-sel-nid"] = None
    if "gx-dim" not in st.session_state:
        st.session_state["gx-dim"] = "2D"
    if "gx-ego-extra" not in st.session_state:
        st.session_state["gx-ego-extra"] = []
    if "gx-ego-center" not in st.session_state or st.session_state["gx-ego-center"] is None:
        default_seed = idx.skill_to_node.get("python")
        if default_seed is None:
            default_seed = int(idx.off_job)
        st.session_state["gx-ego-center"] = int(default_seed)

    mode = st.radio(
        "Chế độ đồ thị",
        [_MODE_SILO, _MODE_GLOBAL],
        horizontal=True,
        key="gx-mode",
        index=0,
        on_change=_on_mode_change,
    )

    c_left, c_right = st.columns([1, 0.2], gap="medium")

    # ------------ CỘT TRÁI: điều khiển + ĐỒ THỊ HERO ----------------
    with c_left:
        if mode == _MODE_SILO:
            client_ids = [int(c["client_id"]) for c in idx.clients]
            selected_cid = st.selectbox(
                "Nhà tuyển dụng (Silo — 9.116 node FL)",
                options=client_ids,
                index=0,
                format_func=lambda cid: (
                    f"{idx.client_by_id[cid]['employer_name']} · "
                    f"{idx.client_by_id[cid]['n_jobs']} tin · "
                    f"{idx.client_by_id[cid]['n_apps']} đơn"
                ),
                key="gx-silo",
                on_change=_on_silo_change,
            )
            c_q, c_kind, c_cap, c_dim = st.columns([2.4, 1.05, 0.85, 0.85], gap="small")
            with c_q:
                q_silo = st.text_input(
                    "Tìm trong silo",
                    placeholder="lọc nút trong silo (nghề, kỹ năng, tiêu đề tin, ứng viên)…",
                    label_visibility="collapsed",
                    key="gx-q",
                )
            with c_kind:
                kind_filter = st.selectbox(
                    "Loại", _KIND_ALL, label_visibility="collapsed", key="gx-kind",
                )
            with c_cap:
                silo_cap_choice = st.selectbox(
                    "Giới hạn hiển thị",
                    [400, 800, 1500, "Toàn bộ"],
                    index=0,
                    label_visibility="collapsed",
                    key="gx-silo-cap",
                )
            with c_dim:
                dim = st.radio(
                    "Chế độ xem",
                    ["2D", "3D"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key="gx-dim-radio",
                    index=0 if st.session_state["gx-dim"] == "2D" else 1,
                )
                st.session_state["gx-dim"] = dim

            sub = extract_silo_subgraph(idx, int(selected_cid))
            render_cap = None if silo_cap_choice == "Toàn bộ" else int(silo_cap_choice)
            dim_num = 3 if dim == "3D" else 2
            nodes, edges, render_meta = layout_subgraph_to_dfs(
                sub,
                dim=dim_num,
                max_render_nodes=render_cap,
                kind_filter=kind_filter,
            )
            nodes = nodes.reset_index(drop=True)
            edges = edges.reset_index(drop=True)
            nbrs = _index_graph(nodes, edges)

            _hits = _search_nodes(nodes, q_silo, kind_filter)
            _hit_positions = [int(i) for i in _hits.index] if len(_hits) else []
            global_hits: list[dict] = []
            q_active = q_silo

            s_stats = sub["stats"]
            emp_name = s_stats["client"]["employer_name"]
            st.caption(
                f"Silo **{emp_name}** (#{selected_cid}): "
                f"**{s_stats['n_jobs']:,}** tin · **{s_stats['n_users']:,}** ứng viên · "
                f"**{s_stats['n_occs']:,}** nghề O*NET · **{s_stats['n_skills']:,}** kỹ năng "
                f"— đang vẽ **{render_meta['n_nodes_rendered']:,} / {s_stats['n_nodes']:,}** nút, "
                f"**{render_meta['n_edges_rendered']:,} / {s_stats['n_edges']:,}** cạnh."
            )
        else:
            c_q, c_kind, c_hops, c_cap, c_dim = st.columns(
                [2.3, 1.0, 0.72, 0.72, 0.85], gap="small",
            )
            with c_q:
                q_global = st.text_input(
                    "Tìm trên toàn bộ 264.995 nút",
                    placeholder="Tên nghề, mã SOC, kỹ năng (Python), tiêu đề tin, nhà tuyển dụng, hoặc ID ứng viên…",
                    label_visibility="collapsed",
                    key="gx-global-q",
                )
            with c_kind:
                kind_filter = st.selectbox(
                    "Loại", _KIND_ALL, label_visibility="collapsed", key="gx-kind",
                )
            with c_hops:
                ego_hops = st.selectbox(
                    "Bước lân cận",
                    [1, 2],
                    index=0,
                    format_func=lambda h: f"{h}-hop",
                    label_visibility="collapsed",
                    key="gx-ego-hops",
                )
            with c_cap:
                ego_cap = st.selectbox(
                    "Giới hạn nút",
                    [250, 500, 1000],
                    index=0,
                    label_visibility="collapsed",
                    key="gx-ego-cap",
                )
            with c_dim:
                dim = st.radio(
                    "Chế độ xem",
                    ["2D", "3D"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key="gx-dim-radio",
                    index=0 if st.session_state["gx-dim"] == "2D" else 1,
                )
                st.session_state["gx-dim"] = dim

            global_hits = (
                search_all_nodes(idx, q_global, kind_filter=kind_filter, limit=15)
                if q_global.strip() else []
            )
            center_nid = int(st.session_state["gx-ego-center"])
            extra_nids = list(st.session_state.get("gx-ego-extra") or [])
            sub = extract_ego_subgraph(
                idx,
                center_nid,
                hops=int(ego_hops),
                extra_nids=extra_nids,
                max_nodes=int(ego_cap),
            )
            dim_num = 3 if dim == "3D" else 2
            nodes, edges, render_meta = layout_subgraph_to_dfs(
                sub,
                dim=dim_num,
                max_render_nodes=None,
                kind_filter=kind_filter,
            )
            nodes = nodes.reset_index(drop=True)
            edges = edges.reset_index(drop=True)
            nbrs = _index_graph(nodes, edges)

            _hits = nodes.iloc[0:0]
            _hit_positions = []
            if not nodes.empty and "nid" in nodes.columns:
                center_matches = nodes.index[nodes["nid"] == center_nid].tolist()
                if center_matches:
                    _hit_positions.append(int(center_matches[0]))
                cur_sel_nid = st.session_state.get("gx-sel-nid")
                if cur_sel_nid is not None and int(cur_sel_nid) != center_nid:
                    sel_matches = nodes.index[nodes["nid"] == int(cur_sel_nid)].tolist()
                    if sel_matches and int(sel_matches[0]) not in _hit_positions:
                        _hit_positions.append(int(sel_matches[0]))
            q_active = q_global

            e_stats = sub["stats"]
            trunc_note = (
                f" (giới hạn từ {e_stats['total_unfiltered_nodes']:,} nút lân cận)"
                if e_stats["truncated"] else ""
            )
            extra_note = f" + mở rộng {len(extra_nids)} nút" if extra_nids else ""
            st.caption(
                f"Ego-graph **{ego_hops}-hop** quanh **{e_stats['center_label']}**{extra_note}: "
                f"**{render_meta['n_nodes_rendered']:,}** nút, "
                f"**{render_meta['n_edges_rendered']:,}** cạnh{trunc_note}."
            )

        if nodes.empty:
            st.info(
                f"Không có nút loại **{kind_filter}** trong đồ thị đang chọn. "
                "Đổi bộ lọc loại nút về «Tất cả» hoặc chọn thực thể khác."
            )

        with st.container(key="gx-graph-card"):
            _hl_key = (
                "none"
                if not _hit_positions
                else hashlib.sha1(",".join(map(str, _hit_positions)).encode("ascii")).hexdigest()[:12]
            )
            if st.session_state["gx-dim"] == "3D":
                with st.container(key=f"gx-graph-3d-{_hl_key}"):
                    components.html(
                        graph_html_3d(nodes, edges, height=GRAPH_HEIGHT,
                                      highlight=_hit_positions),
                        height=GRAPH_HEIGHT + 4, scrolling=False)
            else:
                with st.container(key=f"gx-graph-2d-{_hl_key}"):
                    components.html(
                        graph_html(nodes, edges, height=GRAPH_HEIGHT,
                                   show_search=False,
                                   highlight=_hit_positions),
                        height=GRAPH_HEIGHT + 4, scrolling=False)

    # ---------- CỘT PHẢI: 4 thẻ nhỏ + tìm kiếm + chi tiết -----------
    with c_right:
        sub_stats = sub["stats"]
        if mode == _MODE_SILO:
            _mini_cards([
                {"value": f"{sub_stats['n_nodes']:,}",
                 "label": f"Nút silo (toàn V3: {n_nodes_full:,})"},
                {"value": f"{sub_stats['n_public']:,}",
                 "label": f"Cạnh công khai silo ({sub_stats['n_occs']:,} nghề · {sub_stats['n_skills']:,} kỹ năng; V3: {public_edges_full:,})",
                 "cls": "is-public"},
                {"value": f"{sub_stats['n_private']:,}",
                 "label": f"Cạnh riêng tư silo ({sub_stats['n_apps']:,} ứng tuyển; V3: {private_edges_full:,})",
                 "cls": "is-private"},
                {"value": f"{sub_stats['n_occs']:,}",
                 "label": f"Nghề O*NET silo ({n_occ_full:,} toàn V3 · {n_skills_full:,} kỹ năng)"},
            ])
        else:
            _mini_cards([
                {"value": f"{sub_stats['n_nodes']:,}",
                 "label": f"Nút Ego-graph (toàn V3: {n_nodes_full:,})"},
                {"value": f"{sub_stats['n_public']:,}",
                 "label": f"Cạnh công khai Ego-graph (toàn V3: {public_edges_full:,})",
                 "cls": "is-public"},
                {"value": f"{sub_stats['n_private']:,}",
                 "label": f"Cạnh riêng tư Ego-graph (toàn V3: {private_edges_full:,})",
                 "cls": "is-private"},
                {"value": f"{n_occ_full:,}",
                 "label": f"Nút nghề O*NET ({n_skills_full:,} kỹ năng)"},
            ])

        if mode == _MODE_SILO:
            if q_active.strip():
                st.markdown("<div class='gx-side-title'>Kết quả trong silo</div>",
                            unsafe_allow_html=True)
                if _hits.empty:
                    st.markdown(
                        "<div class='gx-hint'>Không tìm thấy nút nào khớp "
                        f"“{html.escape(q_active.strip())}” trong phần đang vẽ.</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(f"{len(_hits):,} nút khớp")
                    for i in _hits.index[:12]:
                        row = nodes.iloc[i]
                        label = str(row["label"])
                        short = label if len(label) <= 34 else label[:33] + "…"
                        nid_i = int(row["nid"])
                        st.button(
                            short,
                            key=f"gx-hit-{i}",
                            width="stretch",
                            help=f"{row['kind']} · bậc {int(row['degree'])}",
                            on_click=_select_node,
                            args=(nid_i,),
                        )
        else:
            if q_active.strip():
                st.markdown("<div class='gx-side-title'>Kết quả trên 264.995 nút</div>",
                            unsafe_allow_html=True)
                if not global_hits:
                    st.markdown(
                        "<div class='gx-hint'>Không tìm thấy nút nào khớp "
                        f"“{html.escape(q_active.strip())}”. Thử từ khoá ngắn hơn hoặc đổi loại nút.</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(f"Hiển thị top {len(global_hits)} khớp")
                    for r in global_hits[:12]:
                        label = str(r["label"])
                        short = label if len(label) <= 34 else label[:33] + "…"
                        st.button(
                            short,
                            key=f"gx-global-hit-{r['nid']}",
                            width="stretch",
                            help=f"{r['kind']} · bậc toàn đồ thị {int(r['degree']):,}",
                            on_click=_select_ego_center,
                            args=(int(r["nid"]),),
                        )

            # Bộ chọn nút đang hiển thị trong Ego-graph để xem chi tiết / mở rộng láng giềng
            if not nodes.empty and "nid" in nodes.columns:
                center_nid_cur = int(st.session_state["gx-ego-center"])
                rows_list = nodes.to_dict("records")
                rows_list.sort(
                    key=lambda r: (
                        0 if int(r["nid"]) == center_nid_cur else 1,
                        -int(r["degree"]),
                        int(r["nid"]),
                    )
                )
                ego_row_map = {int(r["nid"]): r for r in rows_list}
                ego_nids = list(ego_row_map.keys())
                cur_sel = st.session_state.get("gx-sel-nid")
                st.session_state["gx-ego-pick"] = (
                    int(cur_sel) if cur_sel is not None and int(cur_sel) in ego_row_map else None
                )
                def _fmt_ego_pick(v: object) -> str:
                    if v is None:
                        return "— Chọn nút trong Ego-graph —"
                    if isinstance(v, int):
                        r = ego_row_map.get(v)
                    elif isinstance(v, str) and v.lstrip("-").isdigit() and int(v) in ego_row_map:
                        r = ego_row_map[int(v)]
                    else:
                        return str(v)
                    if r is None:
                        return str(v)
                    prefix = "[Tâm] " if int(r["nid"]) == center_nid_cur else ""
                    return f"{prefix}{r['label']} · {r['kind']} (bậc {int(r['degree'])})"

                st.selectbox(
                    "Chọn nút trong Ego-graph",
                    options=[None, *ego_nids],
                    format_func=_fmt_ego_pick,
                    key="gx-ego-pick",
                    on_change=_on_ego_pick,
                )

        # Panel chi tiết nút đang chọn (theo nid)
        sel_nid = st.session_state.get("gx-sel-nid")
        sel_row_idx: int | None = None
        if sel_nid is not None and not nodes.empty and "nid" in nodes.columns:
            matches = nodes.index[nodes["nid"] == int(sel_nid)].tolist()
            if matches:
                sel_row_idx = int(matches[0])

        if sel_row_idx is not None:
            st.button(
                "✕ Đóng chi tiết",
                key="gx-close",
                width="stretch",
                on_click=_close_detail,
            )
            if mode == _MODE_GLOBAL:
                sel_nid_int = int(sel_nid)
                center_nid_cur = int(st.session_state["gx-ego-center"])
                extra_cur = list(st.session_state.get("gx-ego-extra") or [])
                displayed_nids = {int(v) for v in nodes["nid"].tolist()}
                can_expand = (
                    sel_nid_int != center_nid_cur
                    and sel_nid_int not in extra_cur
                    and _has_unshown_neighbors(idx, sel_nid_int, displayed_nids)
                )
                if can_expand:
                    st.button(
                        "➕ Mở rộng láng giềng",
                        key=f"gx-expand-{sel_nid_int}",
                        width="stretch",
                        help="Thêm các láng giềng 1-hop quanh nút này vào Ego-graph",
                        on_click=_expand_ego_node,
                        args=(sel_nid_int,),
                    )
                elif sel_nid_int == center_nid_cur:
                    st.markdown(
                        "<div class='gx-hint'>Đây là nút tâm của Ego-graph. "
                        "Chọn một láng giềng ở hộp chọn phía trên hoặc danh sách bên dưới "
                        "để mở rộng thêm láng giềng.</div>",
                        unsafe_allow_html=True,
                    )
                elif sel_nid_int in extra_cur:
                    st.markdown(
                        "<div class='gx-hint'>Nút này đã được mở rộng láng giềng.</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div class='gx-hint'>Tất cả láng giềng của nút này đã hiển thị trong Ego-graph.</div>",
                        unsafe_allow_html=True,
                    )

                sel_meta = idx.node_meta(sel_nid_int)
                if sel_meta.get("client_id") is not None:
                    cid_jump = int(sel_meta["client_id"])
                    emp_jump = sel_meta.get("employer") or f"Silo #{cid_jump}"
                    st.button(
                        f"🏢 Xem Silo {emp_jump[:22]}",
                        key=f"gx-jump-silo-{cid_jump}",
                        width="stretch",
                        on_click=_jump_to_silo,
                        args=(cid_jump,),
                    )
                if extra_cur:
                    st.button(
                        "↺ Thu gọn về gốc",
                        key="gx-ego-reset-extra",
                        width="stretch",
                        on_click=_reset_ego_extra,
                    )
            _render_detail(nodes, nbrs, sel_row_idx, index=idx)
        else:
            if mode == _MODE_GLOBAL and st.session_state.get("gx-ego-extra"):
                st.button(
                    "↺ Thu gọn về gốc",
                    key="gx-ego-reset-extra",
                    width="stretch",
                    on_click=_reset_ego_extra,
                )
            if not q_active.strip():
                hint_txt = (
                    "Chọn một Nhà tuyển dụng (9.116 silo) hoặc gõ từ khoá để lọc nút; "
                    "bấm một kết quả hoặc bấm nút trong đồ thị để xem chi tiết."
                    if mode == _MODE_SILO
                    else "Gõ tên nghề O*NET, kỹ năng, tiêu đề tin, nhà tuyển dụng hoặc ID ứng viên "
                         "để tìm trên toàn bộ 264.995 nút; hoặc chọn nút trong Ego-graph phía trên để xem/mở rộng."
                )
                st.markdown(f"<div class='gx-hint'>{hint_txt}</div>",
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
            "Chế độ **Silo Nhà tuyển dụng** trích xuất toàn bộ tin tuyển dụng (`client_of_job`), ứng viên ứng tuyển "
            "vào các tin đó (`user-job`, cạnh Riêng tư), cùng nghề O*NET (`job-occ`) và kỹ năng công nghệ (`occ-skill`, "
            "cạnh Công khai) của từng silo trong **9.116** node FL. Chế độ **Tìm kiếm toàn bộ** truy vấn trực tiếp "
            "trên cả **264.995 nút** để dựng Ego-graph 1–2 hop và mở rộng láng giềng tương tác."
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
