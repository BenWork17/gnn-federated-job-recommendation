"""Trang 2 — Đồ thị việc làm: đồ thị 2D tương tác là hero section.

BỐ CỤC (viết lại theo 6 yêu cầu của người dùng):

    [ Tiêu đề: Đồ thị việc làm ]            (KHÔNG còn câu hỏi đầu trang)
    [ Tìm kiếm ........................ ] [ Loại ▼ ]   |  4 thẻ số liệu nhỏ
    [ ĐỒ THỊ 2D TƯƠNG TÁC — hero 620px  ]              |  (dọc, bên phải)
    [                                   ]              |  panel chi tiết
    [ hai biểu đồ cột phụ + bảng số liệu — trong expander ]

VÌ SAO ĐỔI KHỎI ALTAIR: bản cũ vẽ đồ thị bằng Altair, mà Altair chỉ cho
pan/zoom qua `.interactive()` — KHÔNG kéo được nút, KHÔNG highlight láng
giềng, KHÔNG bấm được. Đó đúng là lý do người dùng nói "khó tương tác".
Nay đồ thị là `force-graph` nhúng trong `components.html` (xem
`app/components/__init__.py` → `graph_html`): kéo nút, rê làm nổi láng
giềng, bấm mở bảng chi tiết, cuộn để zoom.

VÌ SAO BỎ HẾT BỘ LỌC: người dùng yêu cầu rõ "xóa phần bộ lọc hiển thị".
Đồ thị luôn vẽ đủ 4 loại nút và cả hai loại cạnh; việc "làm nổi phần liên
quan" do tương tác hover/click đảm nhiệm, không cần widget lọc.
"""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.components import (bar_chart, data_note, finding, graph_html,
                            load_json, render_chart, spring_layout, theme)
from app.components.graph3d import graph_html_3d
from app.paths import PATHS

# Chiều cao khung đồ thị hero. 620px + hàng tìm kiếm ~72px + tiêu đề ~60px
# => khối hero chiếm gần trọn màn hình đầu tiên trên laptop 1000px.
GRAPH_HEIGHT = 620

# Bốn loại nút — trùng mã màu với `_KIND_COLOR_2D` trong components để bảng
# chi tiết bên phải và nút trong đồ thị cùng một màu.
_KIND_COLOR = {
    "Người dùng": "#7b241c",
    "Tin tuyển dụng": "#e8836b",
    "Kỹ năng": "#2f6fb5",
    "Ngành": "#27ae60",
}
_KIND_ORDER = ["Người dùng", "Tin tuyển dụng", "Kỹ năng", "Ngành"]
_KIND_ALL = ["Tất cả", *_KIND_ORDER]


@st.cache_data(show_spinner="Đang dựng đồ thị…")
def build_graph_view(dim: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lấy đồ thị con để vẽ. Giữ TẤT CẢ nút ngành/kỹ năng phổ biến và
    lấy mẫu nút người dùng/tin để hình còn đọc được.

    `dim=2` → DataFrame có x, y (cho đồ thị 2D).
    `dim=3` → thêm cột z (cho pydeck OrbitView / graph3d).
    Cùng một tập nút/cạnh và cùng công thức bố cục, nên 2D và 3D không làm
    đổi nội dung, chỉ đổi cách nhìn. Trang này chỉ dùng `dim=2`; `dim=3`
    vẫn giữ nguyên chữ ký vì `tests/test_graph_view.py` gọi thẳng."""

    z = np.load(PATHS["medajob"] / "graph.npz", allow_pickle=False)
    nU, nJ = int(z["n_users"]), int(z["n_jobs"])
    nS, nI = int(z["n_skills"]), int(z["n_industries"])
    ei, et = z["edge_index"], z["edge_type"]

    jobs = pd.read_csv(PATHS["medajob"] / "jobs.csv", encoding="utf-8-sig")
    users = pd.read_csv(PATHS["medajob"] / "users.csv", encoding="utf-8-sig")

    rng = np.random.default_rng(42)
    # Giữ 120 kỹ năng phổ biến nhất (bản đầu 60 -> đồ thị vỡ thành nhiều cụm
    # rời rạc vì phần lớn tin chỉ nối vào các kỹ năng ngoài mẫu).
    #
    # LỖI ĐÃ SỬA (hai lần):
    # (1) `if s < nS` — `s` là NODE ID TUYỆT ĐỐI (bắt đầu từ off_skill=1084),
    #     không phải chỉ số trong dải kỹ năng, nên điều kiện luôn sai.
    # (2) Cộng thêm off_skill vào kết quả argsort — nhưng argsort đã trả về
    #     index tuyệt đối trên mảng độ dài n_nodes, nên cộng nữa sẽ ra id
    #     không tồn tại (2168 > 1697).
    # Cách đúng: argsort trên mảng độ dài n_nodes -> lọc lấy dải skill ->
    # DÙNG NGUYÊN giá trị đó (không cộng gì).
    off_skill = nU + nJ
    skill_deg = np.bincount(ei[1][(et == 0) & (ei[1] >= off_skill)],
                            minlength=off_skill + nS + nI)
    order = np.argsort(-skill_deg)
    top_skills = [int(v) for v in order
                  if off_skill <= v < off_skill + nS][:120]
    assert top_skills, "không chọn được kỹ năng nào — kiểm tra lại chỉ số nút"

    # Chọn tin có NHIỀU kỹ năng nằm trong mẫu nhất, thay vì 200 tin đầu tiên.
    # Lý do: tin đầu tiên theo id là dữ liệu seed sinh tự động, kỹ năng nghèo
    # nàn -> nút treo lơ lửng ngoài đồ thị.
    skill_set = set(top_skills)
    job_edges: dict[int, int] = {}
    e0 = (et == 0)
    for a, b in zip(ei[0][e0], ei[1][e0]):
        if nU <= a < nU + nJ and b in skill_set:
            job_edges[int(a)] = job_edges.get(int(a), 0) + 1
    ranked = sorted(job_edges.items(), key=lambda kv: (-kv[1], kv[0]))
    n_job_sample = min(200, nJ)

    # LỖI ĐÃ SỬA (cùng gốc với `top_skills` ở trên, bản trước bỏ sót):
    # `job_edges` được dựng bằng `job_edges[int(a)]` với `a` lấy từ `ei[0]`,
    # tức a là NODE ID TUYỆT ĐỐI. Nên `j` đã là id tuyệt đối rồi —
    # bản trước cộng thêm `nU` là cộng hai lần, làm 29/200 "tin" rơi vào
    # dải kỹ năng (id 1087, 1099, ...) và mất 540 cạnh công khai.
    job_nodes = [int(j) for j, _ in ranked[:n_job_sample]]
    assert job_nodes, "không chọn được tin nào — kiểm tra lại chỉ số nút"
    assert all(nU <= j < nU + nJ for j in job_nodes), \
        "job_nodes phải nằm trọn trong dải nút tin tuyển dụng"

    user_nodes = list(range(0, nU))
    keep = set(user_nodes) | set(job_nodes) | set(top_skills) | \
        set(range(nU + nJ + nS, nU + nJ + nS + nI))

    # lọc cạnh
    m = np.isin(ei[0], list(keep)) & np.isin(ei[1], list(keep))
    s, d, t = ei[0][m], ei[1][m], et[m]

    # bỏ cạnh trùng (đồ thị lưu 2 chiều)
    pairs = set()
    es, ed, ek = [], [], []
    for a, b, typ in zip(s, d, t):
        key = (min(a, b), max(a, b))
        if key in pairs:
            continue
        pairs.add(key)
        es.append(a); ed.append(b)
        ek.append("Công khai" if typ <= 1 else "Riêng tư")

    nodes_used = sorted(set(es) | set(ed))
    idx = {n: i for i, n in enumerate(nodes_used)}
    pos = spring_layout(len(nodes_used),
                        [idx[a] for a in es], [idx[b] for b in ed],
                        iterations=70, dim=dim)

    kinds, labels = [], []
    for n in nodes_used:
        if n < nU:
            kinds.append("Người dùng")
            uid = int(z["user_ids"][n])
            labels.append(f"Ứng viên {uid}")
        elif n < nU + nJ:
            kinds.append("Tin tuyển dụng")
            jid = int(z["job_ids"][n - nU])
            row = jobs[jobs.id == jid]
            labels.append(str(row.job_title.iloc[0])[:60] if len(row) else f"Tin {jid}")
        elif n < nU + nJ + nS:
            kinds.append("Kỹ năng")
            labels.append(f"Kỹ năng #{n - nU - nJ}")
        else:
            kinds.append("Ngành")
            labels.append(f"Ngành #{n - nU - nJ - nS}")

    deg = np.zeros(len(nodes_used))
    for a, b in zip(es, ed):
        deg[idx[a]] += 1
        deg[idx[b]] += 1

    node_df = pd.DataFrame({
        "x": pos[:, 0], "y": pos[:, 1], "kind": kinds, "label": labels,
        "degree": deg.astype(int),
        "size": np.sqrt(deg + 1),
    })
    edge_df = pd.DataFrame({
        "x": [pos[idx[a], 0] for a in es],
        "y": [pos[idx[a], 1] for a in es],
        "x2": [pos[idx[b], 0] for b in ed],
        "y2": [pos[idx[b], 1] for b in ed],
        "edge_kind": ek,
    })
    if dim == 3:
        node_df["z"] = pos[:, 2]
        edge_df["z"] = [pos[idx[a], 2] for a in es]
        edge_df["z2"] = [pos[idx[b], 2] for b in ed]
    return node_df, edge_df


# =====================================================================
# Tiện ích cho thanh tìm kiếm + bảng chi tiết (thuần Python, không đụng
# `app/components/__init__.py`)
# =====================================================================
def _fold(text: str) -> str:
    """Bỏ dấu tiếng Việt để gõ "ky nang" vẫn tìm ra "Kỹ năng".

    Người dùng hay gõ không dấu; nếu so khớp thô thì gần như không tìm được
    gì. `đ` không tách được bằng NFD nên phải thay tay.
    """
    s = str(text).lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _index_graph(nodes: pd.DataFrame,
                 edges: pd.DataFrame) -> list[dict[int, set[str]]]:
    """Danh sách láng giềng của từng nút, nối cạnh qua TOẠ ĐỘ.

    `build_graph_view` không có cột id cho nút; cạnh chỉ có toạ độ hai đầu
    (`x, y, x2, y2`). Đây đúng là cách `graph_html` nối cạnh, nên bảng chi
    tiết bên phải và đồ thị trong iframe luôn nói về cùng một cặp nút.
    """
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
    """4 thẻ số liệu THU NHỎ, xếp dọc (thay cho `metric_row` dải ngang)."""
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
    # --- a. Tiêu đề gọn, KHÔNG có khối "Câu hỏi của trang này" -----------
    # Cố ý KHÔNG gọi `header(...)`: hàm đó luôn in khối câu hỏi, mà yêu cầu
    # của người dùng là bỏ câu hỏi ở trang này. `header()` giữ nguyên hành vi
    # cho các trang khác (components/__init__.py không bị sửa).
    st.caption("DỮ LIỆU MEDA JOB")
    st.markdown("<h1 class='gx-title'>Đồ thị việc làm</h1>",
                unsafe_allow_html=True)

    meta = load_json(str(PATHS["medajob"] / "meta.json"))
    g = meta["graph"]

    # Đồ thị luôn đủ 4 loại nút và cả hai loại cạnh — không còn bộ lọc.
    nodes, edges = build_graph_view(dim=2)
    nodes = nodes.reset_index(drop=True)
    edges = edges.reset_index(drop=True)
    nbrs = _index_graph(nodes, edges)
    n_kind = nodes["kind"].value_counts().to_dict()

    if "gx-sel" not in st.session_state:
        st.session_state["gx-sel"] = None
    # Chế độ xem: "2D" (force-graph, tương tác mượt) hoặc "3D" (three.js,
    # xoay/zoom thật). Mặc định 2D vì kéo/hover/click chạy mượt hơn.
    #
    # VÌ SAO KHÔI PHỤC 3D: người dùng đã đầu tư `graph3d.py` (529 dòng) và
    # `3d-force-graph.min.js` (690 KB). Bản thiết kế lại đầu tiên bỏ luôn nút
    # chuyển vì yêu cầu "xóa bộ lọc hiển thị" — nhưng chế độ xem KHÔNG phải
    # bộ lọc, và mất 3D là mất một tính năng đã có. Nay giữ cả hai.
    if "gx-dim" not in st.session_state:
        st.session_state["gx-dim"] = "2D"

    # Tỉ lệ 1 : 0.2 là GIÁ TRỊ DỰ PHÒNG. Chiều rộng thật của cột phải do CSS
    # trong theme.py quy định theo px, thông qua selector
    # `div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card)`.
    #
    # VÌ SAO PHẢI DÙNG CSS THAY TỈ LỆ:
    # `st.columns` chỉ nhận TỈ LỆ, nên tỉ lệ [4, 1] cho cột phải tới 355px ở
    # màn 1920px — quá rộng so với yêu cầu "4 thẻ nhỏ nằm bên phải" (người
    # dùng muốn nó GỌN để nhường chỗ cho đồ thị). Tỉ lệ cố định cũng sai theo
    # hướng ngược lại khi mở sidebar. `:has()` cho đúng ở mọi bề ngang.
    #
    # LỖI ĐÃ GẶP: bọc `st.container(key="gx-hero")` quanh `st.columns` KHÔNG
    # sinh ra class `.st-key-gx-hero` (đo trong DOM: container chứa columns
    # render ra `stLayoutWrapper` không mang khoá), nên CSS theo khoá đó
    # không bao giờ khớp. `:has()` bám vào khối có `.st-key-gx-graph-card` —
    # khoá này CÓ trong DOM (đã đo).
    c_left, c_right = st.columns([1, 0.2], gap="medium")

    # ------------ CỘT TRÁI: tìm kiếm + ĐỒ THỊ HERO ------------------
    with c_left:
        # Hàng control: tìm kiếm (rộng) + loại nút + chế độ 2D/3D (hẹp).
        # Chế độ xem nằm CHUNG hàng với tìm kiếm nên không tốn thêm chiều cao.
        c_q, c_kind, c_dim = st.columns([3, 1.1, 0.9], gap="small")
        with c_q:
            q = st.text_input("Tìm trong đồ thị",
                              placeholder="gõ tên, kỹ năng, ngành… "
                                          "(không cần dấu)",
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

        # TÍNH KẾT QUẢ TÌM KIẾM TRƯỚC KHI VẼ ĐỒ THỊ — để truyền danh sách
        # nút khớp vào `graph_html(highlight=...)`. Nếu tính sau thì đồ thị đã
        # được sinh xong và không tô sáng được gì.
        # `_search_nodes` trả DataFrame đã sắp theo bậc; lấy chỉ số dòng.
        _hits = _search_nodes(nodes, q, kind_filter)
        _hit_positions = [int(i) for i in _hits.index] if len(_hits) else []

        with st.container(key="gx-graph-card"):
            if st.session_state["gx-dim"] == "3D":
                # 3D: dùng graph3d.py có sẵn (three.js, xoay/zoom thật).
                # Bố cục 3 chiều tính riêng, cùng tập nút/cạnh với 2D.
                nodes3, edges3 = build_graph_view(dim=3)
                nodes3 = nodes3.reset_index(drop=True)
                edges3 = edges3.reset_index(drop=True)

                # TÔ SÁNG cho 3D — phải tính LẠI vị trí vì `nodes3` là
                # DataFrame khác (bố cục 3 chiều), thứ tự dòng có thể khác
                # `nodes` của 2D. Ghép theo `label` thay vì dùng
                # `_hit_positions` của 2D — nếu dùng thẳng sẽ tô sáng SAI nút.
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
                # Truyền danh sách nút khớp tìm kiếm để TÔ SÁNG trên đồ thị.
                # `nodes` đã `reset_index(drop=True)` nên vị trí trùng với chỉ
                # số dòng — đúng thứ `graph_html` cần.
                #
                # VÌ SAO CẦN `key`: `components.html` không nhận tham số key,
                # nên Streamlit so sánh HTML để quyết định có render lại iframe
                # hay không. Xoá từ khoá làm HTML gần giống bản trước (khác mỗi
                # `var arr = [...]`), và Streamlit có thể bỏ qua thay đổi →
                # đồ thị giữ nguyên trạng thái tô sáng cũ.
                # Bọc trong `st.container` có key phụ thuộc vào từ khoá để ép
                # dựng lại khối mỗi khi kết quả tìm kiếm đổi.
                _hl_sig = "none" if not _hit_positions else f"{len(_hit_positions)}-{_hit_positions[0]}"
                with st.container(key=f"gx-graph-2d-{_hl_sig}"):
                    components.html(
                        graph_html(nodes, edges, height=GRAPH_HEIGHT,
                                   show_search=False,
                                   highlight=_hit_positions),
                        height=GRAPH_HEIGHT + 4, scrolling=False)

        st.caption(
            f"Đang vẽ **{len(nodes):,} nút** và **{len(edges):,} cạnh** "
            f"(đồ thị con): {n_kind.get('Người dùng', 0):,} người dùng · "
            f"{n_kind.get('Tin tuyển dụng', 0):,} tin · "
            f"{n_kind.get('Kỹ năng', 0):,} kỹ năng · "
            f"{n_kind.get('Ngành', 0):,} ngành. "
            "Kéo nút để dời (thả ra ghim tại chỗ, bấm đúp bỏ ghim), rê "
            "chuột để làm nổi láng giềng, bấm nút để mở bảng chi tiết, "
            "cuộn để zoom."
        )

    # ---------- CỘT PHẢI: 4 thẻ nhỏ + tìm kiếm + chi tiết -----------
    with c_right:
        _mini_cards([
            {"value": f"{g['nodes']:,}", "label": "Nút (đồ thị đầy đủ)"},
            {"value": f"{g['public_edges']:,}",
             "label": "Cạnh công khai — máy chủ thấy", "cls": "is-public"},
            {"value": f"{g['private_edges']:,}",
             "label": "Cạnh riêng tư — chỉ ở khách hàng",
             "cls": "is-private"},
            {"value": f"{g['industries']}", "label": "Nút ngành"},
        ])

        hits = _hits   # đã tính ở trên, trước khi vẽ đồ thị (để tô sáng)
        if q.strip():
            st.markdown("<div class='gx-side-title'>Kết quả tìm kiếm</div>",
                        unsafe_allow_html=True)
            if hits.empty:
                st.markdown(
                    "<div class='gx-hint'>Không tìm thấy nút nào khớp "
                    f"“{q.strip()}”. Thử từ khoá ngắn hơn hoặc đổi loại "
                    "nút.</div>", unsafe_allow_html=True)
            else:
                st.caption(f"{len(hits):,} nút khớp — bấm để xem chi tiết.")
                for i in hits.index[:12]:
                    row = nodes.iloc[i]
                    label = str(row["label"])
                    short = label if len(label) <= 34 else label[:33] + "…"
                    if st.button(f"{short}", key=f"gx-hit-{i}",
                                 width="stretch",
                                 help=f"{row['kind']} · "
                                      f"bậc {int(row['degree'])}"):
                        st.session_state["gx-sel"] = int(i)
                if len(hits) > 12:
                    st.caption(f"… và {len(hits) - 12:,} nút khác, "
                               "gõ thêm để thu hẹp.")

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
        "Ranh giới rất rõ: máy chủ chỉ thấy cấu trúc nghề nghiệp",
        f"{g['public_edges']:,} cạnh công khai nối tin tuyển dụng với kỹ năng "
        f"và ngành — đây là thông tin đăng tuyển công khai. Toàn bộ "
        f"{g['private_edges']:,} cạnh còn lại (ai biết kỹ năng gì, ai thích "
        "tin nào) chỉ tồn tại bên trong khách hàng. Rê chuột vào một nút "
        "công khai trong đồ thị: phần liên quan sáng lên, phần riêng tư "
        "mờ đi — đó chính là đường ranh giới này.",
        "good",
    )

    with st.expander("Cách đọc đồ thị", expanded=False):
        st.caption(
            "Đồ thị phía trên là **đồ thị con** để vẽ được: giữ toàn bộ ứng "
            "viên, 200 tin có nhiều kỹ năng phổ biến nhất và 120 kỹ năng phổ "
            "biến nhất. Chọn tin theo độ phổ biến (không phải theo id) để đồ "
            "thị liên thông thay vì vỡ thành nhiều cụm rời rạc."
        )

    with st.expander("Cấu trúc đồ thị theo loại nút và phân bố ngành",
                     expanded=False):
        # Lưới 2 CỘT TỰ CO dùng `theme.grid(2, ...)` — hàm này trả về
        # container có khoá, CSS ở theme.py biến `.st-key-lx-grid-2-*` thành
        # grid `minmax(420px, 1fr)`; dưới 900px tự về 1 cột.
        #
        # LỖI ĐÃ ĐO VÀ SỬA: `render_chart` phát ra BA khối markdown riêng
        # (`<div class=hx-chart>`, biểu đồ, `</div>`). Nếu gọi thẳng trong
        # lưới, grid nhận 6 con thay vì 2 -> auto-fit chia 3 cột, biểu đồ rơi
        # vào cột GIỮA. Cách sửa: mỗi biểu đồ bọc trong `st.container()`.
        with theme.grid(2, "chart-phu"):
            with st.container():
                df = pd.DataFrame({
                    "loại": ["Người dùng", "Tin tuyển dụng", "Kỹ năng",
                             "Ngành"],
                    "số_nút": [meta["clean"]["users"], meta["clean"]["jobs"],
                               meta["clean"]["skills"],
                               meta["clean"]["industries"]],
                })
                # Biểu đồ số nút chênh nhau ~100 lần (10 vs 1.014). Thang log
                # làm `mark_bar` cột cao đúng 0px (xem chú thích trong
                # `bar_chart`), nên vẽ thang tuyến tính, giá trị thật vẫn
                # hiện trên đầu cột.
                render_chart(bar_chart(df, "loại", "số_nút",
                                       title="Số nút theo loại "
                                             "(giá trị thật trên đầu cột)",
                                       height=280, value_fmt=",.0f"),
                             delay_ms=60)

            with st.container():
                ind = pd.DataFrame([
                    {"ngành": k, "số_tin": v}
                    for k, v in sorted(meta["graph"]["industry_counts"].items(),
                                       key=lambda x: -x[1])
                ])
                render_chart(bar_chart(ind, "số_tin", "ngành",
                                       horizontal=True, title="Phân bố ngành",
                                       height=280, value_fmt=",.0f"),
                             delay_ms=120)

        st.markdown("**Bảng số liệu của hai biểu đồ trên**")
        t1, t2 = st.columns(2, gap="medium")
        with t1:
            st.markdown("**Số nút theo loại**")
            st.dataframe(df, hide_index=True, width="stretch")
        with t2:
            st.markdown("**Số tin theo ngành**")
            st.dataframe(ind, hide_index=True, width="stretch")

    data_note(
        f"Ngành được suy ra từ tiêu đề tin bằng từ điển khoá, không phải nhãn "
        f"do con người gán. {meta['graph']['industry_counts'].get('Khác', 0):,} tin "
        "rơi vào «Khác» vì tiêu đề không khớp từ khoá nào."
    )


def alt_log(df: pd.DataFrame):
    import altair as alt
    return alt.Y("số_nút:Q", scale=alt.Scale(type="log"), title="Số nút")
