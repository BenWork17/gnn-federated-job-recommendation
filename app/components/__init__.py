"""Các thành phần giao diện dùng lại giữa các trang."""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# Bảng màu White + Signal Orange design system
ORANGE = "#FF5A1F"
ORANGE_DARK = "#C2410C"
INK = "#0F172A"
SKY = "#0EA5E9"
BLUE = SKY  # alias giữ tương thích cho các trang đang import BLUE
RED = "#EF4444"
GREEN = "#10B981"
WARN = "#F59E0B"
PURPLE = "#8B5CF6"
GREY = "#64748B"
PALETTE = [ORANGE, INK, SKY, GREEN, PURPLE, GREY]

# Theme riêng: Altair mặc định dùng xám nhạt + lưới đậm, trông "tài liệu kỹ
# thuật" chứ không "demo". Theme dưới đây làm nền trắng, lưới mảnh, chữ đậm
# hơn, và dùng đúng bảng màu White + Orange.
_ALT_THEME = {
    "config": {
        "background": "#FFFFFF",
        "view": {"stroke": "transparent", "continuousWidth": 400},
        "axis": {
            "labelColor": "#475569",
            "labelFontSize": 12,
            "titleColor": "#0F172A",
            "titleFontSize": 12,
            "titleFontWeight": "bold",
            "gridColor": "#F1F5F9",
            "gridWidth": 1,
            "domainColor": "#E2E8F0",
            "tickColor": "#E2E8F0",
        },
        "legend": {
            "labelColor": "#475569",
            "labelFontSize": 11,
            "titleColor": "#0F172A",
            "titleFontSize": 11,
            "titleFontWeight": "bold",
            "symbolType": "circle",
            "symbolSize": 110,
        },
        "title": {
            "color": "#0F172A",
            "fontSize": 14,
            "fontWeight": "bold",
            "anchor": "start",
            "offset": 12,
        },
        "range": {"category": PALETTE},
        "bar": {"cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
    }
}


def alt_theme() -> dict:
    """Theme Altair dùng chung — tránh lặp cấu hình ở mọi biểu đồ."""
    return _ALT_THEME


def _themed(chart: alt.Chart, height: int, title: str) -> alt.Chart:
    """Áp theme + kích thước cho một biểu đồ."""
    return (chart
            .properties(height=height, title=title)
            .configure(**_ALT_THEME["config"])
            .configure_view(strokeWidth=0))


def render_chart(chart: alt.Chart, *, delay_ms: int = 0, use_container_width: bool = True) -> None:
    """Hiển thị biểu đồ trong khối có hiệu ứng xuất hiện so le."""
    st.markdown(
        f"<div class='hx-chart' style='animation-delay:{delay_ms}ms'>",
        unsafe_allow_html=True)
    st.altair_chart(chart, use_container_width=use_container_width)
    st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# Nạp dữ liệu (cache để không đọc lại file mỗi lần bấm)
# =====================================================================
@st.cache_data(show_spinner=False)
def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def load_npz_summary(path: str) -> dict:
    import numpy as np

    z = np.load(path, allow_pickle=False)
    out = {
        "n_nodes": int(z["n_nodes"]),
        "n_users": int(z["n_users"]),
        "n_jobs": int(z["n_jobs"]),
        "n_skills": int(z["n_skills"]),
        "n_industries": int(z["n_industries"]),
        "edge_index": z["edge_index"],
        "edge_type": z["edge_type"],
        "is_public": z["is_public"],
        "train": z["train"],
        "test": z["test"],
        "Mtr": z["Mtr"],
        "user_ids": z["user_ids"],
        "job_ids": z["job_ids"],
    }
    return out


# =====================================================================
# Khối hiển thị
# =====================================================================
def header(title: str, question: str, kicker: str | None = None) -> None:
    """Mỗi trang mở đầu bằng CÂU HỎI trang đó trả lời."""
    if kicker:
        st.caption(kicker)
    st.title(title)
    st.markdown(
        f"<div class='hx-question' style='background:#FFF7ED;"
        f"border:1px solid #FED7AA;border-left:4px solid {ORANGE};color:#0F172A;"
        f"padding:0.65rem 0.95rem;border-radius:8px;margin-bottom:1.2rem'>"
        f"<b>Câu hỏi của trang này:</b> {question}</div>",
        unsafe_allow_html=True,
    )


def metric_row(items: list[dict]) -> None:
    """Hàng thẻ số liệu lớn. Mỗi item: value, label, help, color."""
    cols = st.columns(len(items))
    for i, (col, it) in enumerate(zip(cols, items)):
        with col:
            color = it.get("color", INK)
            st.markdown(
                f"<div class='hx-card' style='"
                f"border-radius:10px;padding:0.9rem 1rem;"
                f"animation-delay:{i * 70}ms'>"
                f"<div class='hx-metric' style='color:{color};"
                f"animation-delay:{i * 70 + 90}ms'>{it['value']}</div>"
                f"<div style='font-size:0.78rem;color:#64748B;margin-top:0.3rem;"
                f"line-height:1.3'>{it['label']}</div></div>",
                unsafe_allow_html=True,
            )
            if it.get("help"):
                st.caption(it["help"])


def delta_badge(text: str, positive: bool = True) -> str:
    """HTML của một nhãn nhỏ kiểu '▲ 0,095' để nhét trong văn bản."""
    color = GREEN if positive else RED
    arrow = "▲" if positive else "▼"
    return (f"<span style='color:{color};font-weight:700;font-size:0.85rem'>"
            f"{arrow} {text}</span>")


def finding(title: str, body: str, kind: str = "info") -> None:
    """Ô nêu một phát hiện. kind: info | warn | good | bad."""
    colors = {"info": SKY, "warn": WARN, "good": GREEN, "bad": RED}
    icons = {"info": "ℹ️", "warn": "⚠️", "good": "✅", "bad": "❌"}
    c = colors.get(kind, SKY)
    st.markdown(
        f"<div class='hx-finding' style='border:1px solid #E2E8F0;"
        f"border-left:4px solid {c};"
        f"padding:0.7rem 1rem;border-radius:8px;margin:0.5rem 0'>"
        f"<b>{icons.get(kind, '')} {title}</b><br>"
        f"<span style='font-size:0.9rem;color:#334155'>{body}</span></div>",
        unsafe_allow_html=True,
    )


def data_note(text: str) -> None:
    st.caption(f"📊 {text}")


# =====================================================================
# Biểu đồ Altair
# =====================================================================
def bar_chart(df: pd.DataFrame, x: str, y: str, color_col: str | None = None,
              title: str = "", y_title: str = "", x_title: str = "",
              height: int = 320, horizontal: bool = False,
              value_fmt: str = ".3f", log_y: bool = False) -> alt.Chart:
    """Biểu đồ cột có nhãn số trên đầu cột và màu theo theme chung.

    `log_y`: dùng thang log cho trục giá trị. Cần khi các cột chênh nhau
    hàng trăm lần (ví dụ số nút Ngành = 10 so với Tin = 1.014) — nếu để
    thang tuyến tính thì cột nhỏ gần như biến mất.
    """
    base = alt.Chart(df)
    # Thứ tự trục phân loại: dùng DANH SÁCH TƯỜNG MINH thay vì sort="-x".
    #
    # Vì sao không dùng "-x": khi biểu đồ có 2 layer (cột + nhãn số), Vega
    # hợp nhất domain của hai layer và cảnh báo "Domains that should be unioned
    # has conflicting sort properties" — trục hiển thị không ổn định (lỗi đã
    # gặp ở khối "Cấu trúc đồ thị theo loại nút"). Danh sách tường minh thì
    # không có gì để xung đột: cả hai layer nhận cùng một thứ tự cố định.
    if horizontal:
        order = list(df.sort_values(x, ascending=False)[y])
    else:
        order = list(df[x])
    sort_spec = order

    # ------------------------------------------------------------------
    # LỖI ĐÃ SỬA — cột biến mất hoàn toàn khi dùng thang log.
    #
    # Triệu chứng (ảnh chụp của người dùng): chỉ còn nhãn số nằm lơ lửng,
    # không có cột nào. Nguyên nhân đo được: `mark_bar` vẽ cột từ baseline 0,
    # mà trên thang log vị trí 0 là -∞, nên SVG sinh ra `d="M0,0h18v0h-18Z"`
    # — chiều cao đúng bằng 0px.
    #
    # Đã thử hai cách và ĐỀU KHÔNG ĐƯỢC với `type=log`:
    #   (a) thêm `y2` tường minh  -> Vega vẫn kẹp domain về 0
    #   (b) đặt `domain` tường minh -> Vega cảnh báo "zero is dropped as it
    #       does not work with log scale" rồi vẫn vẽ 0px
    # Nên bỏ hẳn log scale cho `mark_bar`. Thay bằng: giữ thang TUYẾN TÍNH
    # nhưng ghi giá trị thật lên đầu mỗi cột (đã có sẵn lớp nhãn). Cách này
    # đọc được đúng thứ người xem cần — "ngành = 10, tin = 1.014" — mà không
    # phụ thuộc vào hành vi ngầm định của Vega.
    #
    # Vẫn nhận `log_y` để không phá chữ ký hàm cũ; chỉ dùng nó để ghi chú.
    # ------------------------------------------------------------------
    use_log = False          # xem giải thích ở trên: log + mark_bar = cột 0px
    log_floor = None
    log_scale = alt.Undefined
    log_domain = None
    vals = pd.to_numeric(df[x if horizontal else y], errors="coerce").dropna()
    spread = (float(vals.max()) / float(vals.min())) if len(vals) else 1.0

    if horizontal:
        enc = dict(
            y=alt.Y(f"{y}:N", sort=sort_spec, title=y_title or y),
            x=alt.X(f"{x}:Q", title=x_title or x),
        )
    else:
        enc = dict(
            x=alt.X(f"{x}:N", sort=sort_spec, title=x_title or x),
            y=alt.Y(f"{y}:Q", title=y_title or y),
        )
    if color_col:
        enc["color"] = alt.Color(f"{color_col}:N",
                                 scale=alt.Scale(range=PALETTE), legend=None)
    else:
        enc["color"] = alt.value(ORANGE)
    enc["tooltip"] = list(df.columns)

    chart = base.mark_bar(cornerRadiusEnd=4).encode(**enc)

    # Nhãn số: giúp đọc được giá trị mà không cần hover — quan trọng khi
    # chiếu máy chiếu (người xem không tương tác được).
    # Dùng CHUNG `use_log` với layer cột, nếu không hai layer lệch scale.
    fmt = value_fmt
    lab_scale = alt.Scale(type="log") if use_log else alt.Undefined
    if horizontal:
        labels = base.mark_text(dx=5, align="left", fontSize=11,
                                color="#475569").encode(
            y=alt.Y(f"{y}:N", sort=sort_spec),
            x=alt.X(f"{x}:Q", scale=lab_scale),
            text=alt.Text(f"{x}:Q", format=fmt),
        )
    else:
        labels = base.mark_text(dy=-6, fontSize=11, color="#475569").encode(
            x=alt.X(f"{x}:N", sort=sort_spec),
            y=alt.Y(f"{y}:Q", scale=lab_scale),
            text=alt.Text(f"{y}:Q", format=fmt),
        )
    chart = chart + labels

    return _themed(chart, height, title)


def line_chart(df: pd.DataFrame, x: str, y: str, color_col: str,
               title: str = "", height: int = 320) -> alt.Chart:
    """Biểu đồ đường có điểm đánh dấu, độ dày nét vừa phải."""
    chart = (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(size=55, filled=True),
                   strokeWidth=2.4)
        .encode(
            x=alt.X(f"{x}:Q", title=x),
            y=alt.Y(f"{y}:Q", title=y),
            color=alt.Color(f"{color_col}:N", scale=alt.Scale(range=PALETTE)),
            tooltip=list(df.columns),
        )
    )
    return _themed(chart, height, title)


def area_chart(df: pd.DataFrame, x: str, y: str, color_col: str,
               title: str = "", height: int = 300) -> alt.Chart:
    """Biểu đồ vùng — hợp để thể hiện khối lượng/tích luỹ."""
    chart = (
        alt.Chart(df)
        .mark_area(opacity=0.65, line={"strokeWidth": 2},
                   interpolate="monotone")
        .encode(
            x=alt.X(f"{x}:Q", title=x),
            y=alt.Y(f"{y}:Q", title=y),
            color=alt.Color(f"{color_col}:N", scale=alt.Scale(range=PALETTE)),
            tooltip=list(df.columns),
        )
    )
    return _themed(chart, height, title)


def graph_chart(nodes: pd.DataFrame, edges: pd.DataFrame,
                title: str = "", height: int = 520) -> alt.Chart:
    """Vẽ đồ thị node-link bằng Altair (không cần Plotly).

    Ưu tiên ĐỌC ĐƯỢC hơn là vẽ nhiều: cạnh công khai (xanh) và riêng tư (đỏ)
    phải phân biệt rõ vì đó chính là thông điệp của trang. Cạnh mảnh 1.4px,
    opacity 0.55 — bản đầu để 0.32 nên gần như vô hình trên máy chiếu.
    """
    edge_layer = (
        alt.Chart(edges)
        .mark_rule(opacity=0.55, strokeWidth=1.4)
        .encode(
            x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None),
            x2="x2:Q", y2="y2:Q",
            color=alt.Color("edge_kind:N",
                            scale=alt.Scale(domain=["Công khai", "Riêng tư"],
                                            range=[BLUE, RED]),
                            legend=alt.Legend(title="Loại cạnh", orient="top",
                                              symbolType="stroke",
                                              symbolStrokeWidth=3,
                                              labelFontSize=12,
                                              titleFontSize=12)),
            tooltip=["edge_kind:N"],
        )
    )
    node_layer = (
        alt.Chart(nodes)
        .mark_circle(stroke="white", strokeWidth=1.2)
        .encode(
            x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None),
            size=alt.Size("size:Q", scale=alt.Scale(range=[45, 1100]),
                          legend=None),
            color=alt.Color("kind:N",
                            scale=alt.Scale(
                                domain=["Người dùng", "Tin tuyển dụng",
                                        "Kỹ năng", "Nghề O*NET", "Ngành"],
                                range=["#7b241c", "#e8836b", BLUE, GREEN, GREEN]),
                            legend=alt.Legend(title="Loại nút", orient="top",
                                              symbolSize=160,
                                              labelFontSize=12,
                                              titleFontSize=12,
                                              columns=4)),
            tooltip=["label:N", "kind:N", "degree:Q"],
        )
    )
    chart = ((edge_layer + node_layer)
             .properties(height=height, title=title)
             .interactive())          # pan/zoom — cần cho trang đồ thị
    return (chart.configure(background="#ffffff")
            .configure_view(strokeWidth=0)
            .configure_legend(padding=8, offset=4))

# =====================================================================
# Đồ thị 2D TƯƠNG TÁC (force-graph) — thay cho Altair ở trang đồ thị
# =====================================================================
#
# VÌ SAO KHÔNG DÙNG ALTAIR NỮA
# ============================
# `graph_chart` ở trên vẫn được giữ (để không phá test và còn dùng chỗ khác),
# nhưng Altair chỉ cho pan/zoom qua `.interactive()`. Nó KHÔNG kéo được nút,
# không làm nổi láng giềng khi rê chuột, không bắt sự kiện bấm — tức là
# "nhìn" được chứ không "tương tác" được. Trang đồ thị cần đúng ba thứ đó,
# nên phần vẽ chuyển sang `force-graph` (cùng tác giả với `3d-force-graph`
# đang dùng ở `graph3d.py`, API gần như trùng khớp).
#
# VÌ SAO NHÚNG THƯ VIỆN INLINE
# ============================
# `components.html` render vào iframe `srcdoc`, nên mọi URL tương đối
# (`assets/force-graph.min.js`) đều vỡ — iframe không có document base của
# trang Streamlit. Vì vậy nội dung bundle được ĐỌC và CHÈN THẲNG vào thẻ
# `<script>`, giống cách `graph3d.py` làm với bundle 3D. Toàn bộ chạy offline,
# không phụ thuộc CDN lúc demo.
#
# TƯƠNG TÁC ĐƯỢC (đủ 4 việc người dùng yêu cầu)
# ---------------------------------------------
# 1. Kéo nút: `onNodeDrag` của thư viện cập nhật fx/fy; thả ra thì GHIM tại
#    chỗ (`onNodeDragEnd` gán fx = x, fy = y). Bấm đúp một nút để bỏ ghim.
# 2. Rê chuột: nút/cạnh không liên quan mờ còn 0.08, láng giềng giữ 1.0.
# 3. Bấm nút: mở bảng chi tiết bên phải (nhãn, loại, bậc, tối đa 20 láng
#    giềng kèm loại), có nút ✕ đóng.
# 4. Zoom/pan mượt + nút "⤢ Vừa khung" gọi `zoomToFit`.

_KIND_COLOR_2D = {
    "Người dùng":     "#7b241c",
    "Tin tuyển dụng": "#e8836b",
    "Kỹ năng":        "#0EA5E9",
    "Nghề O*NET":     "#10B981",
    "Ngành":          "#10B981",
}
_EDGE_COLOR_2D = {"Công khai": "#F97316", "Riêng tư": RED}

_ASSET_2D = Path(__file__).resolve().parents[1] / "assets" / "force-graph.min.js"


@st.cache_data(show_spinner=False)
def _force_graph_lib() -> str:
    """Đọc bundle `force-graph` một lần rồi cache (158 KB, không đọc lại mỗi rerun)."""
    if not _ASSET_2D.exists():
        raise FileNotFoundError(
            f"Thiếu {_ASSET_2D}. Tải bằng:\n"
            "  python -c \"import urllib.request,pathlib;"
            "pathlib.Path('app/assets/force-graph.min.js').write_bytes("
            "urllib.request.urlopen('https://unpkg.com/force-graph@1.45.0/dist/"
            "force-graph.min.js').read())\"")
    return _ASSET_2D.read_text(encoding="utf-8")


def _graph_payload_2d(nodes: pd.DataFrame, edges: pd.DataFrame) -> dict:
    """Chuyển hai DataFrame -> `{nodes, links}` mà force-graph hiểu.

    `build_graph_view` KHÔNG có cột id cho nút/cạnh — cạnh chỉ có toạ độ hai
    đầu (`x, y, x2, y2`). Vì vậy id nút được sinh từ chỉ số dòng (`n0`, `n1`…)
    và cạnh được nối lại qua bảng tra toạ độ -> id, đúng cách `graph3d.py`
    đang làm. Nếu DataFrame đã có sẵn cột `source`/`target` thì dùng luôn, để
    hàm này không phụ thuộc cứng vào một nguồn dữ liệu.
    """
    has_xy = {"x", "y"} <= set(nodes.columns)
    use_id = ("node_id" in nodes.columns) and ({"source", "target"} <= set(edges.columns))

    ns: list[dict] = []
    keyed: dict[tuple[float, float], str] = {}
    for i, row in enumerate(nodes.to_dict("records")):
        nid = str(row["node_id"]) if use_id else f"n{i}"
        ns.append({
            "id": nid,
            "label": str(row.get("label", nid)),
            "kind": str(row.get("kind", "")),
            "degree": int(row.get("degree", 0) or 0),
        })
        if has_xy:
            keyed[(round(float(row["x"]), 6),
                   round(float(row["y"]), 6))] = nid

    links: list[dict] = []
    if {"source", "target"} <= set(edges.columns):
        ids = {n["id"] for n in ns}
        for row in edges.to_dict("records"):
            a, b = str(row["source"]), str(row["target"])
            if a in ids and b in ids and a != b:
                kind = str(row.get("edge_kind", row.get("kind", "Công khai")))
                links.append({"source": a, "target": b, "kind": kind})
    elif has_xy:
        for row in edges.to_dict("records"):
            a = keyed.get((round(float(row["x"]), 6),
                           round(float(row["y"]), 6)))
            b = keyed.get((round(float(row["x2"]), 6),
                           round(float(row["y2"]), 6)))
            if a and b:
                kind = str(row.get("edge_kind", row.get("kind", "Công khai")))
                links.append({"source": a, "target": b, "kind": kind})
    return {"nodes": ns, "links": links}


# --- JS ứng dụng (chèn sau bundle, đọc DATA từ placeholder) --------------
_JS_2D = r"""
(function () {
  'use strict';

  var DATA = __DATA__;
  var KC = __KC__, EC = __EC__;
  var KIND_ORDER = __KIND_ORDER__;

  if (typeof ForceGraph === 'undefined') {
    fail('Thiếu thư viện force-graph (app/assets/force-graph.min.js).');
    return;
  }
  if (!DATA.nodes || !DATA.nodes.length) {
    fail('Không có nút nào để vẽ.');
    return;
  }

  // ---------------- chuẩn bị dữ liệu ----------------------------------
  var byId = {}, adj = {}, MAXDEG = 1, kinds = [];
  DATA.nodes.forEach(function (n) {
    byId[n.id] = n;
    adj[n.id] = [];
    n.color = KC[n.kind] || '#7f8c8d';
    n.degree = n.degree || 0;
    if (n.degree > MAXDEG) { MAXDEG = n.degree; }
    if (kinds.indexOf(n.kind) < 0) { kinds.push(n.kind); }
  });
  kinds.sort(function (a, b) {
    var ia = KIND_ORDER.indexOf(a), ib = KIND_ORDER.indexOf(b);
    if (ia < 0) { ia = 99; }
    if (ib < 0) { ib = 99; }
    return ia - ib;
  });

  var LINKS = (DATA.links || []).filter(function (l) {
    var a = (typeof l.source === 'object') ? l.source.id : l.source;
    var b = (typeof l.target === 'object') ? l.target.id : l.target;
    return byId[a] && byId[b] && a !== b;
  });
  LINKS.forEach(function (l) {
    var a = byId[(typeof l.source === 'object') ? l.source.id : l.source];
    var b = byId[(typeof l.target === 'object') ? l.target.id : l.target];
    l.color = EC[l.kind] || EC['Công khai'];
    var hi = Math.max(a.degree, b.degree) / Math.max(1, MAXDEG);
    l.w = 0.8 + 0.8 * Math.min(1, Math.sqrt(hi));   // 0.8 – 1.6 px
    l.a = (l.kind === 'Riêng tư') ? 0.30 : 0.35;
    // danh sách kề để làm nổi láng giềng + bảng chi tiết
    adj[a.id].push(b.id);
    adj[b.id].push(a.id);
  });
  Object.keys(adj).forEach(function (k) {
    var seen = {}, out = [];
    adj[k].forEach(function (v) { if (!seen[v]) { seen[v] = 1; out.push(v); } });
    adj[k] = out;
  });

  function radius(n) {
    var d = Math.min(1, (n.degree || 0) / Math.max(1, MAXDEG));
    return Math.max(4, Math.min(14, 4 + 10 * Math.sqrt(d)));   // 4 – 14 px
  }
  function rgba(hex, a) {
    var h = (hex || '#7f8c8d').replace('#', '');
    if (h.length === 3) { h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]; }
    var num = parseInt(h, 16);
    return 'rgba(' + ((num >> 16) & 255) + ',' + ((num >> 8) & 255) + ',' +
      (num & 255) + ',' + a + ')';
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;',
              '"': '&quot;', "'": '&#39;'}[c];
    });
  }
  function norm(s) {
    s = String(s == null ? '' : s);
    if (s.normalize) {
      s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }
    return s.replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
  }

  // ---------------- trạng thái tương tác ------------------------------
  var state = { hover: null, sel: null };
  var userMoved = false, firstFit = false, engineRunning = false;
  // true CHỈ trong lúc code tự đổi kích thước canvas (KHÔNG phải người dùng)
  var progResize = false;
  var hoverLock = false;   // true khi hover do code đặt (không do chuột)

  function focusId() { return state.hover || state.sel; }
  function isNbr(id) {
    var f = focusId();
    return !!(f && (adj[f] || []).indexOf(id) >= 0);
  }
  // ---------------- tô sáng kết quả tìm kiếm -------------------------
  //
  // Ô tìm kiếm của TRANG nằm NGOÀI iframe, nên Streamlit phải truyền danh
  // sách nút khớp vào lúc sinh HTML (`highlight`). Tập này cố định theo một
  // lần render — mỗi lần người dùng gõ thêm, Streamlit rerun và iframe được
  // tạo lại với tập mới. Nhờ vậy không cần IPC hai chiều giữa Streamlit và
  // iframe.
  //
  // Ưu tiên hiển thị: `hover`/`sel` (thao tác trực tiếp trên đồ thị) THẮNG
  // `hl` — nếu người dùng đang rê một nút thì không nên bị tập tìm kiếm làm
  // nhiễu.
  var HL_SET = {};
  (function () {
    var arr = __HIGHLIGHT__;
    for (var i = 0; i < arr.length; i++) {
      var idx = arr[i];
      if (typeof idx === 'number' && idx >= 0 && idx < DATA.nodes.length) {
        HL_SET[DATA.nodes[idx].id] = true;
      }
    }
  })();
  var HL_COUNT = Object.keys(HL_SET).length;

  function isHl(id) { return !!HL_SET[id]; }

  function redraw() { Graph.nodeColor(NC); }
  function syncAutoPause() {
    // Khi có nút đang rê/chọn thì vẽ liên tục -> hiệu ứng mờ hiện ngay và
    // mượt; khi rảnh thì tạm dừng vẽ để không tốn CPU.
    // Có kết quả tìm kiếm tô sáng cũng phải vẽ liên tục, nếu không hiệu ứng
    // mờ không hiện ra.
    Graph.autoPauseRedraw(!(state.hover || state.sel || HL_COUNT > 0));
  }

  // Độ mờ của một nút: nút đang rê/chọn và láng giềng giữ 1.0, phần còn lại
  // mờ còn 0.08. Tách thành hàm riêng để đo được (test) thay vì chỉ vẽ.
  function nodeAlpha(node) {
    var f = focusId();
    if (f) {
      if (node.id === f || isNbr(node.id)) { return 1; }
      return 0.08;
    }
    // Không rê/chọn gì nhưng CÓ kết quả tìm kiếm: nút khớp và láng giềng của
    // chúng sáng, phần còn lại mờ — để mắt bắt ngay cụm liên quan.
    if (HL_COUNT > 0) {
      if (isHl(node.id)) { return 1; }
      // láng giềng của một nút khớp
      for (var k in HL_SET) {
        if ((adj[k] || []).indexOf(node.id) >= 0) { return 0.55; }
      }
      return 0.10;
    }
    return 1;
  }
  function labelVisible(node, scale) {
    if (scale > 1.6) { return true; }
    var f = focusId();
    if (f) { return !!(node.id === f || isNbr(node.id)); }
    // Có tìm kiếm: luôn hiện nhãn của nút khớp, dù zoom chưa lớn.
    return HL_COUNT > 0 && isHl(node.id);
  }

  // ---------------- vẽ nút + nhãn --------------------------------------
  function NC(node, ctx, scale) {
    var r = radius(node);
    var a = nodeAlpha(node);
    var dim = a < 1;
    var hl = HL_COUNT > 0 && !focusId() && isHl(node.id);

    // Nút khớp tìm kiếm: vẽ vòng sáng (halo) phía sau để bắt mắt ngay cả khi
    // nút nhỏ hoặc nằm trong cụm dày.
    if (hl) {
      ctx.globalAlpha = 0.9;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 5 / scale, 0, 2 * Math.PI, false);
      ctx.fillStyle = 'rgba(255, 214, 10, 0.55)';
      ctx.fill();
    }

    ctx.globalAlpha = a;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
    ctx.fillStyle = node.color;
    ctx.fill();
    if (hl) {
      // viền đậm màu hổ phách quanh nút khớp
      ctx.lineWidth = 2.4 / scale;
      ctx.strokeStyle = '#b8860b';
      ctx.stroke();
    } else if (!dim) {
      ctx.lineWidth = 1.2 / scale;
      ctx.strokeStyle = '#ffffff';
      ctx.stroke();
    }
    if (node.id === state.sel) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 3 / scale, 0, 2 * Math.PI, false);
      ctx.lineWidth = 1.6 / scale;
      ctx.strokeStyle = '#0F172A';
      ctx.stroke();
    }

    // Nhãn: chỉ khi zoom đủ lớn (globalScale > 1.6) hoặc khi rê/chọn nút đó
    // (kèm láng giềng) — để đồ thị 385 nút không thành một mớ chữ.
    if (labelVisible(node, scale) && !dim) {
      var fs = Math.max(6, 11 / scale);
      var lab = String(node.label || '');
      if (lab.length > 26) { lab = lab.slice(0, 25) + '…'; }
      ctx.font = '600 ' + fs + 'px system-ui,-apple-system,Segoe UI,sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.lineWidth = 3 / scale;
      ctx.strokeStyle = 'rgba(255,255,255,0.92)';
      ctx.strokeText(lab, node.x + r + 4 / scale, node.y);
      ctx.fillStyle = '#0F172A';
      ctx.fillText(lab, node.x + r + 4 / scale, node.y);
    }
    ctx.globalAlpha = 1;
  }

  function paintNode(node, color, ctx) {
    // Phải tự vẽ vùng bắt chuột, vì `nodeCanvasObject` chế độ "replace" tắt
    // phần vẽ mặc định của thư viện (nếu không, rê chuột sẽ không ăn).
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius(node) + 3, 0, 2 * Math.PI, false);
    ctx.fill();
  }

  // ---------------- bảng chi tiết bên phải ------------------------------
  var panel = document.getElementById('panel');
  var pbody = document.getElementById('pbody');
  var lastClick = { id: null, t: 0 };

  function closePanel() {
    state.sel = null;
    panel.hidden = true;
    syncAutoPause();
    redraw();
  }
  document.getElementById('pclose').addEventListener('click', closePanel);

  function renderPanel(n) {
    var rows = adj[n.id].map(function (id) { return byId[id]; })
      .sort(function (a, b) {
        var ia = kinds.indexOf(a.kind), ib = kinds.indexOf(b.kind);
        if (ia !== ib) { return ia - ib; }
        return b.degree - a.degree || (a.label < b.label ? -1 : 1);
      });
    var shown = rows.slice(0, 20);
    var html = '' +
      '<div class="p-kind"><span class="p-dot" style="background:' +
        (n.color) + '"></span>' + esc(n.kind) + '</div>' +
      '<div class="p-name">' + esc(n.label) + '</div>' +
      '<div class="p-meta">Bậc (số liên kết): <b>' + n.degree + '</b></div>' +
      '<div class="p-sub">Láng giềng (' + rows.length + ')</div>';
    if (!shown.length) {
      html += '<div class="p-empty">Nút này không nối với nút nào.</div>';
    } else {
      html += '<ul class="p-list">';
      shown.forEach(function (m) {
        html += '<li data-id="' + esc(m.id) + '">' +
          '<span class="p-dot" style="background:' + m.color + '"></span>' +
          '<span class="p-lbl">' + esc(m.label) + '</span>' +
          '<span class="p-k">' + esc(m.kind) + '</span></li>';
      });
      html += '</ul>';
      if (rows.length > shown.length) {
        html += '<div class="p-empty">… và ' + (rows.length - shown.length) +
          ' láng giềng khác.</div>';
      }
    }
    pbody.innerHTML = html;
    panel.hidden = false;
    // bấm một láng giềng trong bảng -> chọn luôn nút đó
    Array.prototype.forEach.call(
      pbody.querySelectorAll('li[data-id]'),
      function (li) {
        li.addEventListener('click', function () {
          var t = byId[li.getAttribute('data-id')];
          if (t) { selectNode(t); }
        });
      });
  }

  function selectNode(n) {
    state.sel = n.id;
    state.hover = null;
    renderPanel(n);
    syncAutoPause();
    redraw();
    Graph.centerAt(n.x, n.y, 500);
    if (Graph.zoom() < 1.8) { Graph.zoom(1.8, 500); }
  }

  // ---------------- tìm kiếm ------------------------------------------
  var q = document.getElementById('q');
  var kf = document.getElementById('kf');
  var res = document.getElementById('res');
  var cnt = document.getElementById('cnt');

  kinds.forEach(function (k) {
    var o = document.createElement('option');
    o.value = k;
    o.textContent = k;
    kf.appendChild(o);
  });

  function search() {
    var term = norm(q.value).trim();
    var kind = kf.value;
    var hits = [];
    if (term) {
      DATA.nodes.forEach(function (n) {
        if (kind && n.kind !== kind) { return; }
        if (norm(n.label).indexOf(term) >= 0) { hits.push(n); }
      });
      hits.sort(function (a, b) { return b.degree - a.degree; });
    }
    cnt.textContent = term ? (hits.length + ' nút khớp') : '';
    if (!term) { res.hidden = true; res.innerHTML = ''; return; }
    if (!hits.length) {
      res.hidden = false;
      res.innerHTML = '<div class="s-empty">Không tìm thấy nút nào khớp.</div>';
      return;
    }
    var html = '';
    hits.slice(0, 12).forEach(function (n) {
      html += '<div class="s-hit" data-id="' + esc(n.id) + '">' +
        '<span class="p-dot" style="background:' + n.color + '"></span>' +
        '<span class="p-lbl">' + esc(n.label) + '</span>' +
        '<span class="p-k">' + esc(n.kind) + '</span></div>';
    });
    if (hits.length > 12) {
      html += '<div class="s-empty">… và ' + (hits.length - 12) +
        ' nút khác, gõ thêm để thu hẹp.</div>';
    }
    res.hidden = false;
    res.innerHTML = html;
    Array.prototype.forEach.call(
      res.querySelectorAll('.s-hit'),
      function (el) {
        el.addEventListener('click', function () {
          var t = byId[el.getAttribute('data-id')];
          if (t) { res.hidden = true; selectNode(t); }
        });
      });
  }

  q.addEventListener('input', search);
  kf.addEventListener('change', search);

  // Nút "⤢ Vừa khung" — LỖI ĐÃ SỬA: bản đầu chỉ có nút trong HTML mà không
  // gắn listener, bấm không có tác dụng gì. Đo được: zoom giữ nguyên 1.8.
  document.getElementById('fit').addEventListener('click', function () {
    Graph.zoomToFit(500, 40);
  });
  q.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') {
      var first = res.querySelector('.s-hit');
      if (first) {
        var t = byId[first.getAttribute('data-id')];
        if (t) { res.hidden = true; selectNode(t); }
      }
    } else if (ev.key === 'Escape') {
      q.value = '';
      search();
    }
  });

  // ---------------- khởi tạo đồ thị ------------------------------------
  // API của vasturiano là CURRIED: `ForceGraph()(element)`. Viết
  // `new ForceGraph(el)` chạy không lỗi nhưng KHÔNG gắn canvas vào DOM
  // (đã đo: canvasCount = 0, `#g` trống trơn) — đúng lỗi gặp ở lần chạy đầu.
  var host = document.getElementById('g');
  var Graph = ForceGraph()(host)
    .backgroundColor('#ffffff')
    .nodeRelSize(1)
    .nodeVal(function (n) { var r = radius(n); return r * r; })
    .nodeCanvasObject(NC)
    .nodePointerAreaPaint(paintNode)
    .nodeLabel(function () { return ''; })   // bảng chi tiết thay tooltip
    .linkColor(function (l) {
      var f = focusId();
      if (f && l.source.id !== f && l.target.id !== f) {
        return rgba(l.color, 0.08);
      }
      return rgba(l.color, l.a);
    })
    .linkWidth(function (l) {
      var f = focusId();
      if (f && l.source.id !== f && l.target.id !== f) { return 0.6; }
      return l.w;
    })
    .d3AlphaDecay(0.026)
    .d3VelocityDecay(0.32)
    .cooldownTicks(320)
    .warmupTicks(40)
    .onNodeHover(function (n) {
      // Thư viện tự dò nút dưới con trỏ MỖI FRAME (dùng shadow canvas) rồi
      // gọi handler này với `null` khi con trỏ không ở trên nút nào. Vì vậy
      // nếu bên ngoài đã đặt hover bằng `setHover()` (kiểm chứng tự động),
      // giá trị đó sẽ bị ghi đè ngay frame sau -> phải có khoá.
      if (hoverLock) { return; }
      state.hover = n ? n.id : null;
      syncAutoPause();
      redraw();
    })
    .onNodeClick(function (n) {
      var now = Date.now();
      if (lastClick.id === n.id && now - lastClick.t < 380) {
        // bấm đúp: bỏ ghim để nút tự chạy lại theo lực
        n.fx = undefined;
        n.fy = undefined;
        lastClick = { id: null, t: 0 };
        redraw();
        return;
      }
      lastClick = { id: n.id, t: now };
      hoverLock = false;
      selectNode(n);
    })
    .onNodeDragEnd(function (n) {
      // Thả ra thì GHIM tại chỗ — đúng yêu cầu "kéo nút được, thả là cố định".
      n.fx = n.x;
      n.fy = n.y;
      redraw();
    })
    .onBackgroundClick(function () {
      if (state.sel) { closePanel(); }
    })
    .onZoom(function () {
      // LỖI ĐÃ SỬA (hai lần) — lần canh khung ĐẦU TIÊN không bao giờ chạy.
      //
      // Lần sửa 1: chỉ bọc `resize()` bằng `progResize`. KHÔNG ĐỦ — đo lại vẫn
      //   zoom = 0,5498. Vì thư viện tự gọi `zoom()`/`centerAt()` trong lúc
      //   khởi tạo engine, các lời gọi đó KHÔNG nằm trong `resize()`, nên
      //   `onZoom` vẫn chạy và vẫn bật `userMoved = true`.
      //
      // Lần sửa 2 (hiện tại): `onZoom` KHÔNG tự bật cờ nữa. Cờ `userMoved` chỉ
      //   được bật bởi handler chuột thật (`pointerdown`/`wheel`/`touchstart`)
      //   — nguồn duy nhất chứng minh "người dùng đã chủ động di chuyển khung
      //   nhìn". Nhờ vậy `onEngineStop` lần đầu luôn thấy `!userMoved` và canh
      //   khung đúng.
      redraw();
    })
    // Theo dõi engine để bên ngoài biết lúc nào bố cục đã ổn định. Không có
    // cờ này thì không ai biết được "đã yên chưa" — `isEngineRunning()` của
    // thư viện nằm trên đối tượng forceGraph bên trong, KHÔNG có trên đối
    // tượng trả về (đã thử: TypeError: is not a function).
    .onEngineTick(function () { engineRunning = true; })
    .graphData({ nodes: DATA.nodes, links: LINKS });

  // Khung vẽ phải khít iframe; iframe đổi kích thước (đổi cửa sổ, mở/đóng
  // sidebar) thì cập nhật lại — thư viện không tự theo dõi phần tử cha.
  function resize() {
    var w = host.clientWidth || window.innerWidth || 800;
    var h = host.clientHeight || __HEIGHT__ || 620;
    // `width()`/`height()` cũng bắn `onZoom` (đã đo: 1 lần, đồng bộ). Bọc cờ
    // để lần đổi kích thước lúc khởi tạo KHÔNG bị tính là "người dùng đã tự
    // di chuyển khung nhìn" — nếu tính, lần canh khung đầu tiên bị bỏ qua.
    // `finally` để nếu width()/height() ném lỗi thì cờ vẫn được trả về false,
    // không kẹt ở true làm onZoom vô hiệu vĩnh viễn.
    progResize = true;
    try { Graph.width(w).height(h); } finally { progResize = false; }
  }
  window.addEventListener('resize', resize);
  if (typeof ResizeObserver !== 'undefined') {
    try { new ResizeObserver(resize).observe(host); } catch (e) {}
  }
  resize();

  Graph.onEngineStop(function () {
    engineRunning = false;
    // Canh khung MỘT LẦN, và chỉ khi người dùng chưa tự di chuyển — nếu canh
    // lại sau mỗi lần kéo nút thì khung hình tự lùi ra, rất khó chịu.
    if (!firstFit && !userMoved) {
      firstFit = true;
      Graph.zoomToFit(500, 40);
      // LỖI ĐÃ SỬA — chuyển 3D → 2D thì zoom ra 0,5498 thay vì 0,8075.
      // Nguyên nhân: khi iframe được tạo lại, `onEngineStop` bắn lúc canvas
      // CHƯA có kích thước cuối (ResizeObserver còn chạy) nên `zoomToFit`
      // tính theo khung nhỏ hơn thực tế.
      // Cách chữa: nếu sau khi canh mà zoom vẫn < 0,7 (dấu hiệu khung chưa
      // đúng) thì canh lại một lần sau khi layout ổn định. Vẫn tôn trọng
      // `userMoved` — nếu người dùng đã cuộn/kéo trong khoảng đó thì bỏ qua.
      setTimeout(function () {
        if (!userMoved && Graph.zoom() < 0.7) {
          Graph.zoomToFit(400, 40);
        }
      }, 420);
    }
  });

  // `userMoved` CHỈ được bật bởi tương tác chuột/bàn phím thật của người dùng.
  //
  // VÌ SAO KHÔNG đặt cờ trong `onZoom`: thư viện tự gọi `zoom()` và
  // `centerAt()` trong lúc khởi tạo engine (và cả khi `width()`/`height()`
  // đổi kích thước). Mọi lời gọi đó đều bắn `onZoom`, nên nếu bật cờ ở đó thì
  // cờ bật TRƯỚC khi engine kịp dừng lần đầu → `onEngineStop` thấy
  // `userMoved = true` → bỏ qua `zoomToFit` → zoom kẹt ở giá trị mặc định
  // 0,5498 (= 4/∛385, đo được) thay vì ~0,8075 khi canh khung đúng.
  //
  // Nghe trên `host` (phần tử chứa canvas) nên chỉ bắt được thao tác thật
  // trỏ vào đồ thị, không bắt được lời gọi API từ code.
  ['pointerdown', 'wheel', 'touchstart', 'keydown'].forEach(function (evName) {
    host.addEventListener(evName, function () { userMoved = true; },
                          { passive: true });
  });

  // ---------------- API để ĐO được (test/kiểm chứng tự động) -------------
  // Kiểm chứng bằng Selenium cần đọc trạng thái thật của đồ thị: nút nào
  // đang rê/chọn, độ mờ tính ra bao nhiêu, nhãn có hiện không. Nếu không
  // phơi ra thì chỉ đo được "ảnh có chữ" — không chứng minh được hành vi.
  window.__GRAPH2D__ = {
    graph: Graph,
    nodes: DATA.nodes,
    links: LINKS,
    kinds: kinds,
    colors: {node: KC, edge: EC},
    radius: radius,
    alpha: nodeAlpha,
    labelVisible: labelVisible,
    neighbors: function (id) { return (adj[id] || []).slice(); },
    state: state,
    // Đặt nút đang rê bằng id — dùng cho kiểm chứng tự động.
    // Có KHOÁ: thư viện dò lại nút dưới con trỏ mỗi frame, nếu không khoá thì
    // giá trị vừa đặt bị ghi đè thành null ngay frame sau. Gọi setHover(null)
    // để mở khoá và trả về hành vi theo chuột.
    setHover: function (id) {
      state.hover = id || null;
      hoverLock = !!id;
      syncAutoPause();
      redraw();
      return state.hover;
    },
    // đã yên chưa + khung nhìn hiện tại, để bên ngoài chờ đúng lúc
    status: function () {
      var c = Graph.centerAt();
      return { engineRunning: engineRunning, zoom: Graph.zoom(),
               cx: c.x, cy: c.y, hover: state.hover, sel: state.sel,
               hoverLock: hoverLock,
               panelOpen: !document.getElementById('panel').hidden };
    },
    // chọn nút bằng id (dùng cho test) — đi đúng đường người dùng bấm
    select: function (id) {
      var n = byId[id];
      if (n) { selectNode(n); }
      return !!n;
    },
    close: closePanel,
    search: search,
    // điểm trên canvas (toạ độ CSS) của một nút — để Selenium bấm đúng chỗ
    screenPos: function (id) {
      var n = byId[id];
      if (!n) { return null; }
      var p = Graph.graph2ScreenCoords(n.x, n.y);
      return { x: p.x, y: p.y, radius: radius(n) };
    },
    counts: function () {
      return {
        nodes: DATA.nodes.length,
        links: LINKS.length,
        pinned: DATA.nodes.filter(function (n) {
          return n.fx !== undefined && n.fx !== null;
        }).length,
      };
    },
  };
})();
"""

_HTML_2D = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:#FFFFFF;overflow:hidden;
            font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
            color:#0F172A}
  #g{width:100%;height:__HEIGHT__px;position:relative}
  #err{display:none;font-size:14px;color:#EF4444;padding:18px;line-height:1.5}
  /* Overlay phải đứng SAU #g trong DOM và có z-index: canvas do thư viện vẽ
     nằm trong phần tử position:relative, nếu overlay đứng trước thì bị vẽ đè
     và biến mất (đúng lỗi đã gặp ở bản 3D). */
  #search{position:absolute;top:10px;left:10px;z-index:30;
          background:#fffffff2;border:1px solid #E2E8F0;border-radius:10px;
          padding:8px 9px;box-shadow:0 2px 10px rgba(15,23,42,0.06);
          width:min(330px,calc(100% - 40px))}
  #search .s-row{display:flex;gap:6px;align-items:center}
  #search .s-row + .s-row{margin-top:6px}
  #q{flex:1 1 auto;min-width:0;font:inherit;font-size:12px;padding:5px 8px;
     border:1px solid #E2E8F0;border-radius:8px;color:#0F172A;background:#FFFFFF}
  #kf{flex:0 0 auto;font:inherit;font-size:12px;padding:4px 6px;
      border:1px solid #E2E8F0;border-radius:8px;background:#FFFFFF;color:#0F172A}
  #fit{flex:0 0 auto;font:inherit;font-size:12px;padding:4px 9px;
       border:1px solid #E2E8F0;border-radius:8px;background:#FFFFFF;
       color:#0F172A;cursor:pointer;white-space:nowrap}
  #fit:hover{background:#FFF7ED;border-color:#FDBA74;color:#C2410C}
  #search .muted{color:#64748B;font-size:11px}
  #res{margin-top:6px;max-height:250px;overflow:auto}
  #res[hidden]{display:none}
  .s-hit{display:flex;align-items:center;gap:6px;padding:4px 5px;
         border-radius:6px;cursor:pointer;font-size:12px}
  .s-hit:hover{background:#FFF7ED}
  .s-empty{font-size:11px;color:#64748B;padding:4px 2px}
  .p-dot{width:8px;height:8px;border-radius:50%;flex:0 0 auto}
  .p-lbl{flex:1 1 auto;overflow:hidden;text-overflow:ellipsis;
         white-space:nowrap}
  .p-k{flex:0 0 auto;font-size:10px;color:#64748B}
  #panel{position:absolute;top:10px;right:10px;bottom:10px;z-index:30;
         width:min(300px,46%);background:#fffffff7;
         border:1px solid #E2E8F0;border-radius:10px;
         box-shadow:0 6px 22px rgba(15,23,42,0.10);padding:12px 14px;
         overflow:auto;font-size:12px}
  #panel[hidden]{display:none}
  #pclose{position:absolute;top:7px;right:8px;font:inherit;font-size:13px;
          line-height:1;border:0;background:transparent;color:#64748B;
          cursor:pointer;padding:4px 6px;border-radius:6px}
  #pclose:hover{background:#FFF7ED;color:#C2410C}
  .p-kind{display:flex;align-items:center;gap:6px;font-size:11px;
          color:#475569;font-weight:700;padding-right:22px}
  .p-name{font-size:14px;font-weight:700;line-height:1.35;margin:6px 0 4px;
          color:#0F172A}
  .p-meta{font-size:11px;color:#475569}
  .p-sub{margin-top:11px;padding-top:8px;border-top:1px solid #F1F5F9;
         font-size:11px;font-weight:700;color:#475569}
  .p-list{list-style:none;margin:5px 0 0;padding:0}
  .p-list li{display:flex;align-items:center;gap:6px;padding:4px 5px;
             border-radius:6px;cursor:pointer;font-size:12px}
  .p-list li:hover{background:#FFF7ED}
  .p-empty{font-size:11px;color:#64748B;margin-top:5px}
  #legend{position:absolute;left:10px;bottom:10px;z-index:30;
          background:#fffffff2;border:1px solid #E2E8F0;border-radius:10px;
          padding:7px 10px;font-size:11px;line-height:1.7;
          box-shadow:0 2px 10px rgba(15,23,42,0.06)}
  #legend .lg-t{font-weight:700;font-size:11px;color:#475569;
                margin-bottom:2px}
  #legend .lg-r{display:flex;align-items:center;gap:6px;white-space:nowrap}
  #legend .lg-d{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
  #legend .lg-l{width:16px;height:0;border-top-width:2px;
                border-top-style:solid;flex:0 0 auto}
  #legend .lg-s{height:1px;background:#F1F5F9;margin:5px 0}
  #hint{position:absolute;right:10px;bottom:10px;z-index:30;font-size:11px;
        color:#475569;background:#ffffffdd;padding:3px 7px;border-radius:6px}
</style></head>
<body>
<div id="err"></div>
<div id="g"></div>

<div id="search"__SEARCH_STYLE__>
  <div class="s-row">
    <input id="q" type="search" autocomplete="off"
           placeholder="Tìm nút: ứng viên, tin, kỹ năng, ngành…">
    <button id="fit" type="button"
            title="Thu khung vừa toàn bộ đồ thị">⤢ Vừa khung</button>
  </div>
  <div class="s-row">
    <select id="kf" title="Lọc theo loại nút">
      <option value="">Tất cả loại</option>
    </select>
    <span id="cnt" class="muted"></span>
  </div>
  <div id="res" hidden></div>
</div>

<div id="panel" hidden>
  <button id="pclose" type="button" title="Đóng bảng chi tiết">✕</button>
  <div id="pbody"></div>
</div>

<div id="legend">
  <div class="lg-t">Loại nút</div>
  <div class="lg-r"><span class="lg-d" style="background:#7b241c"></span>Người dùng</div>
  <div class="lg-r"><span class="lg-d" style="background:#e8836b"></span>Tin tuyển dụng</div>
  <div class="lg-r"><span class="lg-d" style="background:#0EA5E9"></span>Kỹ năng</div>
  <div class="lg-r"><span class="lg-d" style="background:#10B981"></span>Nghề O*NET</div>
  <div class="lg-s"></div>
  <div class="lg-t">Loại cạnh</div>
  <div class="lg-r"><span class="lg-l" style="border-top-color:#F97316"></span>Công khai</div>
  <div class="lg-r"><span class="lg-l" style="border-top-color:#EF4444"></span>Riêng tư</div>
</div>

<div id="hint">Kéo nút để dời · thả ra để ghim · bấm đúp để bỏ ghim · cuộn để zoom</div>

<script>
// Báo lỗi RÕ RÀNG thay vì khung trắng im lặng (kể cả lỗi ném ra từ bundle).
function fail(msg) {
  var e = document.getElementById('err');
  if (e) {
    e.style.display = 'block';
    e.innerHTML = '<b>Không vẽ được đồ thị 2D.</b><br>' + msg;
  }
  ['g', 'search', 'panel', 'legend', 'hint'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) { el.style.display = 'none'; }
  });
}
window.addEventListener('error', function (ev) {
  fail('Lỗi JavaScript: ' + (ev.message || 'không rõ'));
});
</script>
<script>__LIB__</script>
<script>__APP__</script>
</body></html>"""


def graph_html(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    height: int = 620,
    *,
    show_search: bool = True,
    highlight: list[int] | None = None,
) -> str:
    """Sinh một trang HTML TỰ CHỨA vẽ đồ thị 2D tương tác.

    Dùng trong view::

        import streamlit.components.v1 as components
        from app.components import graph_html

        components.html(graph_html(nodes, edges, height=620),
                        height=624, scrolling=False)

    Tương tác được (đều nằm trong iframe, KHÔNG cần rerun Streamlit):

    - **Kéo nút** để dời, thả ra thì ghim tại chỗ; **bấm đúp** để bỏ ghim.
    - **Rê chuột** làm nổi nút/cạnh láng giềng, phần còn lại mờ còn 8%.
    - **Bấm nút** mở bảng chi tiết bên phải: nhãn, loại, bậc, tối đa 20
      láng giềng kèm loại; nút ✕ để đóng.
    - **Cuộn/kéo nền** để zoom–pan; nút "⤢ Vừa khung" gọi `zoomToFit`.
    - **Ô tìm kiếm** (lọc được theo 4 loại nút) chọn thẳng một nút và mở
      bảng chi tiết của nút đó.

    Không cần mạng: bundle `force-graph` (158 KB) được nhúng INLINE, vì
    `components.html` render vào iframe `srcdoc` nên đường dẫn tương đối
    tới `app/assets/` sẽ không phân giải được.
    """
    payload = _graph_payload_2d(nodes, edges)
    if not payload["nodes"]:
        return _EMPTY_HTML_2D

    # Tô sáng kết quả tìm kiếm bên ngoài (Streamlit) lên đồ thị.
    #
    # VÌ SAO CẦN: ô tìm kiếm của TRANG nằm ngoài iframe, nên gõ từ khoá thì
    # danh sách kết quả ở cột phải đổi, còn đồ thị trong iframe KHÔNG biết gì
    # — người xem không thấy nút nào nổi bật. Tham số `highlight` nhận danh
    # sách chỉ số dòng (index của `nodes` với `reset_index(drop=True)`) để
    # tô sáng đúng những nút khớp.
    #
    # `highlight` là danh sách chỉ số NGUYÊN trong [0, len(nodes)). Truyền
    # `None` hoặc rỗng = không tô sáng gì.
    hl_positions: list[int] = []
    if highlight:
        for v in highlight:
            try:
                iv = int(v)
            except (TypeError, ValueError):
                continue
            if 0 <= iv < len(payload["nodes"]):
                hl_positions.append(iv)

    data_blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    app_js = (_JS_2D
              .replace("__DATA__", data_blob)
              .replace("__KC__", json.dumps(_KIND_COLOR_2D,
                                            ensure_ascii=False))
              .replace("__EC__", json.dumps(_EDGE_COLOR_2D,
                                            ensure_ascii=False))
              .replace("__KIND_ORDER__",
                       json.dumps(list(_KIND_COLOR_2D), ensure_ascii=False))
              .replace("__HIGHLIGHT__", json.dumps(hl_positions))
              .replace("__HEIGHT__", str(int(height))))

    return (_HTML_2D
            .replace("__HEIGHT__", str(int(height)))
            .replace("__SEARCH_STYLE__",
                     "" if show_search else ' style="display:none"')
            .replace("__LIB__", _force_graph_lib())
            .replace("__APP__", app_js))


_EMPTY_HTML_2D = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8">
<style>body{margin:0;padding:18px;font:14px/1.5 system-ui,sans-serif;
color:#c0392b}</style></head><body>
<b>Không có nút nào để vẽ.</b><br>Hãy kiểm tra lại bộ lọc loại nút — có thể
bạn đã bỏ chọn cả bốn loại.</body></html>"""


def render_graph_2d(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    height: int = 620,
) -> None:
    """Vẽ đồ thị 2D tương tác ngay trong trang Streamlit hiện tại."""
    import streamlit.components.v1 as components

    components.html(graph_html(nodes, edges, height=height),
                    height=height + 4, scrolling=False)


# =====================================================================
# Bố cục đồ thị (spring layout nhẹ, không cần networkx cho tốc độ)
# =====================================================================
def spring_layout(n_nodes: int, src, dst, *, seed: int = 42,
                  iterations: int = 60, k: float | None = None,
                  dim: int = 2):
    """Bố cục lò xo (force-directed) có LỰC ĐẨY TOÀN CỤC.

    `dim=2` cho biểu đồ Altair, `dim=3` cho pydeck OrbitView. Cùng một công
    thức cho cả hai, nên bật/tắt 2D–3D thì bố cục vẫn "cùng một giọng",
    không bị nhảy hình.

    LỖI ĐÃ SỬA — bản đầu chỉ đẩy các cặp CÓ CẠNH:
    Lực đẩy chỉ tính giữa hai đầu mút của mỗi cạnh, nên một nút bậc 1 chỉ
    chịu lực từ đúng một nút khác và bị đẩy ra xa vô hạn, trong khi nút bậc
    cao (kỹ năng "python" nối hàng trăm tin) bị kéo về tâm. Kết quả là đồ thị
    bị vẽ thành những TIA dài — nhìn ảnh chụp màn hình là thấy rõ.

    Bản này đẩy MỌI cặp nút (repulsion toàn cục), đúng như lực đẩy Coulomb
    trong thuật toán Fruchterman–Reingold, nên các nút bậc 1 không còn bắn ra
    ngoài. Với ~400 nút thì ma trận 400×400 vẫn đủ nhanh (<0.3s/100 vòng).

    Vì sao không dùng networkx.spring_layout: bản Python thuần mất vài giây
    mỗi lần Streamlit rerun, làm app giật khi bấm bộ lọc.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    pos = rng.normal(0, 1, (n_nodes, dim))
    if k is None:
        k = 1.6 / np.sqrt(max(n_nodes, 2))   # khoảng cách lý tưởng

    src = np.asarray(src, dtype=int)
    dst = np.asarray(dst, dtype=int)
    # trọng số hút: nút bậc càng cao càng hút mạnh -> cụm tự nhiên
    has_edge = np.zeros((n_nodes, n_nodes), dtype=np.float32)
    np.add.at(has_edge, (src, dst), 1.0)
    np.add.at(has_edge, (dst, src), 1.0)

    for it in range(iterations):
        # nhiệt độ giảm dần: đầu thì di chuyển mạnh, sau thì tinh chỉnh
        temp = 0.12 * (1.0 - it / iterations) + 0.005

        diff = pos[:, None, :] - pos[None, :, :]        # (n, n, dim)
        dist = np.linalg.norm(diff, axis=2) + 1e-6
        np.fill_diagonal(dist, 1e9)                      # bỏ tự đẩy
        unit = diff / dist[:, :, None]                   # (n, n, dim)

        # (a) lực ĐẨY toàn cục giữa mọi cặp
        rep = (k * k / dist)[:, :, None] * unit
        disp = rep.sum(axis=1)

        # (b) lực HÚT chỉ trên các cạnh thực
        att = (dist / k)[:, :, None] * unit * has_edge[:, :, None]
        disp -= att.sum(axis=1)

        # (c) co nhẹ về tâm để đồ thị không trôi
        disp -= pos * 0.01 * n_nodes

        norm = np.linalg.norm(disp, axis=1, keepdims=True) + 1e-9
        pos += np.minimum(norm, temp) / norm * disp

    # chuẩn hoá về [0, 1] cho vừa khung vẽ
    lo, hi = pos.min(0), pos.max(0)
    span = np.where(hi - lo > 0, hi - lo, 1.0)
    return (pos - lo) / span
