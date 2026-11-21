"""
Regression test cho 4 lỗi thật đã gặp trong phiên sửa giao diện.

1. `bar_chart` dùng hai giá trị `sort` khác nhau cho hai layer (cột + nhãn)
   -> Vega cảnh báo "Domains that should be unioned has conflicting sort
   properties" và trục hiển thị sai. Khối "Cấu trúc đồ thị theo loại nút"
   bị đúng lỗi này.
2. Đồ thị 3D tự canh khung lại sau mỗi lần lực đẩy dừng -> người dùng zoom ra
   rồi thả chuột thì camera tự lùi vào, "tự zoom nhỏ lại".
3. Gợi ý hồ sơ mới phải xử lý được đầu vào rỗng/không tồn tại, và không phân
   biệt hoa/thường.
4. Không được quay lại dịch thuật ngữ chuyên ngành (xem docs/QUY_UOC_THUAT_NGU.md).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / ".mplcache"))
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------
# 1. Biểu đồ: sort phải nhất quán giữa các layer
# ---------------------------------------------------------------------
def _sort_of_layers(spec: dict) -> list[tuple[str, object]]:
    """Lấy (trục, giá trị sort) của các trục phân loại trong mọi layer."""
    out = []
    for lyr in spec.get("layer", [spec]):
        for ax in ("x", "y"):
            enc = lyr.get("encoding", {}).get(ax, {})
            if enc.get("type") == "nominal":
                out.append((ax, enc.get("sort")))
    return out


def test_bar_chart_layers_share_same_sort() -> None:
    """Hai layer không được có sort khác nhau trên cùng một trục.

    Đây là nguyên nhân cảnh báo "conflicting sort properties" của Vega.
    """
    from app.components import bar_chart

    df = pd.DataFrame({"loai": ["A", "B", "C"], "so": [3, 1, 2]})

    vertical = bar_chart(df, "loai", "so").to_dict()
    sorts = _sort_of_layers(vertical)
    assert len({str(s) for s in sorts}) == 1, f"sort lệch nhau: {sorts}"

    horizontal = bar_chart(df, "so", "loai", horizontal=True).to_dict()
    sorts_h = _sort_of_layers(horizontal)
    assert len({str(s) for s in sorts_h}) == 1, f"sort lệch nhau: {sorts_h}"


def test_bar_chart_sort_is_explicit_list() -> None:
    """Sort phải là danh sách tường minh, không phải "-x" hay None.

    `sort="-x"` trên layer khiến Vega hợp nhất domain thất bại khi có 2 layer.
    """
    from app.components import bar_chart

    df = pd.DataFrame({"loai": ["A", "B"], "so": [2, 1]})
    for spec in (bar_chart(df, "loai", "so").to_dict(),
                 bar_chart(df, "so", "loai", horizontal=True).to_dict()):
        for _, sort_val in _sort_of_layers(spec):
            assert isinstance(sort_val, list), \
                f"sort phải là danh sách tường minh, đang là {sort_val!r}"


def test_bar_chart_bars_have_height_with_log_y() -> None:
    """`log_y=True` KHÔNG được làm cột cao 0px.

    Lỗi đã gặp (ảnh chụp màn hình): khối "Số nút theo loại (thang log)" chỉ
    còn nhãn số lơ lửng, không có cột nào. Nguyên nhân: `mark_bar` vẽ từ
    baseline 0, mà 0 trên thang log là -∞ -> Vega sinh `d="M0,0h18v0h-18Z"`
    (chiều cao 0). Thêm `y2` hay đặt `domain` đều không cứu được.
    Cách sửa: bỏ log scale cho mark_bar; cột trở lại thang tuyến tính.

    Test này khẳng định KHÔNG emit scale log nữa — nếu ai thêm lại log scale
    cho mark_bar, cột sẽ biến mất như trước.
    """
    from app.components import bar_chart

    df = pd.DataFrame({"loai": ["A", "B"], "so": [1014, 10]})
    spec = bar_chart(df, "loai", "so", log_y=True).to_dict()
    enc = spec["layer"][0]["encoding"]
    y_enc = enc.get("y", {})
    scale = y_enc.get("scale") or {}
    assert scale.get("type") != "log", (
        "mark_bar + scale log làm cột cao 0px — xem chú thích trong bar_chart")


def test_bar_chart_still_shows_values() -> None:
    """Vì bỏ thang log, giá trị thật phải hiện trên đầu cột."""
    from app.components import bar_chart

    df = pd.DataFrame({"loai": ["A", "B"], "so": [1014, 10]})
    spec = bar_chart(df, "loai", "so", log_y=True,
                     value_fmt=",.0f").to_dict()
    assert len(spec["layer"]) == 2, "phải có layer cột + layer nhãn"
    labels = spec["layer"][1]
    assert labels["mark"]["type"] == "text"
    assert labels["encoding"]["text"]["format"] == ",.0f"


# ---------------------------------------------------------------------
# 2. Đồ thị 3D: không tự canh khung lại sau khi người dùng đã zoom
# ---------------------------------------------------------------------
def test_3d_does_not_refit_camera_on_every_engine_stop() -> None:
    """`onEngineStop` không được gọi `zoomToFit` vô điều kiện.

    Lỗi: kéo nút -> lực đẩy chạy lại -> dừng -> camera tự lùi ra, nên người
    dùng thấy "tự zoom nhỏ lại khi vừa thả chuột".
    """
    from app.components.graph3d import _JS_APP

    assert "firstFitDone" in _JS_APP, "thiếu cờ canh-khung-một-lần"
    assert "userMovedCamera" in _JS_APP, "thiếu cờ theo dõi người dùng đã zoom"

    # cờ phải được kiểm tra ngay trong onEngineStop
    m = re.search(r"Graph\.onEngineStop\(function \(\) \{(.*?)\}\);",
                  _JS_APP, re.S)
    assert m, "không tìm thấy onEngineStop"
    body = m.group(1)
    assert "firstFitDone" in body and "userMovedCamera" in body, \
        "onEngineStop vẫn canh khung vô điều kiện"


def test_3d_tracks_user_camera_gestures() -> None:
    """Phải bắt sự kiện chuột/cuộn để biết người dùng đã tự điều khiển."""
    from app.components.graph3d import _JS_APP

    for ev in ("wheel", "pointerdown"):
        assert f"'{ev}'" in _JS_APP, f"thiếu theo dõi sự kiện {ev}"


def test_3d_has_color_legend() -> None:
    """Đồ thị 3D phải có chú giải màu.

    Bản trước không có, người xem không biết màu xanh/đỏ/tím nghĩa là gì —
    đúng phản hồi "chưa có chú thích".
    """
    from app.components.graph3d import _JS_APP, graph_html_3d
    from app.views import do_thi_viec_lam as V

    nodes, edges = V.build_graph_view.__wrapped__(dim=3)
    html = graph_html_3d(nodes, edges)

    assert 'id="legend"' in html, "thiếu khung chú giải"
    assert "buildLegend" in _JS_APP, "thiếu hàm dựng chú giải"
    # chú giải phải liệt kê đủ 4 loại nút và 2 loại cạnh
    for k in ("Người dùng", "Tin tuyển dụng", "Kỹ năng", "Ngành",
              "Công khai", "Riêng tư"):
        assert k in html, f"chú giải thiếu mục {k}"


def test_3d_overlays_stacked_above_canvas() -> None:
    """`#panel` và `#legend` phải HIỆN được, không bị canvas đè.

    Lỗi đã gặp: bảng điều khiển và chú giải biến mất hoàn toàn, chỉ còn dòng
    gợi ý ở dưới. Hai nguyên nhân cộng lại:
      (1) `#panel`/`#legend` nằm TRƯỚC `#g` trong DOM, mà canvas của thư viện
          nằm trong `.scene-container` (position:relative) nên vẽ đè lên.
          `#hint` nằm SAU `#g` nên vẫn hiện — đúng ảnh chụp màn hình.
      (2) overlay là `position:absolute` nhưng KHÔNG có `z-index`.
    """
    from app.components.graph3d import graph_html_3d
    from app.views import do_thi_viec_lam as V

    nodes, edges = V.build_graph_view.__wrapped__(dim=3)
    html = graph_html_3d(nodes, edges)

    i_g = html.find('<div id="g">')
    i_panel = html.find('<div id="panel">')
    i_legend = html.find('<div id="legend">')
    assert i_g > 0 and i_panel > 0 and i_legend > 0

    # canvas phải đứng TRƯỚC overlay trong DOM
    assert i_g < i_panel, "#panel phải nằm SAU #g, nếu không bị canvas đè"
    assert i_g < i_legend, "#legend phải nằm SAU #g, nếu không bị canvas đè"

    # và phải có z-index để chắc chắn nổi lên trên
    compact = html.replace(" ", "")
    assert "z-index:30" in compact, "overlay thiếu z-index"


def test_3d_hides_library_navinfo() -> None:
    """Dòng 'Left-click: rotate...' của thư viện không được chồng lên gợi ý."""
    from app.components.graph3d import _JS_APP

    assert ".showNavInfo(false)" in _JS_APP, \
        "phải tắt navInfo, nếu không nó đè lên dòng #hint của ta"


def test_3d_tooltip_is_readable() -> None:
    """Tooltip phải do ta tự vẽ, không dùng mặc định (chữ sáng, không nền).

    Lỗi đã gặp: rê chuột vào nút thì chữ trắng hiện trên nền trắng -> không
    đọc được. Nguyên nhân: `.scene-tooltip` mặc định của thư viện dùng
    `color: lavender` và không có background.
    """
    from app.components.graph3d import _JS_APP, graph_html_3d
    from app.views import do_thi_viec_lam as V

    nodes, edges = V.build_graph_view.__wrapped__(dim=3)
    html = graph_html_3d(nodes, edges)

    # tooltip được TẠO BẰNG JS (document.createElement) chứ không có sẵn
    # trong HTML tĩnh, nên phải kiểm trong _JS_APP.
    assert "document.createElement('div')" in _JS_APP
    assert "tip.id = 'tip'" in _JS_APP, "thiếu khung tooltip tự viết"
    assert "showTip" in _JS_APP, "thiếu hàm hiện tooltip"
    # tắt tooltip mặc định của thư viện
    assert ".nodeLabel('')" in _JS_APP, \
        "phải tắt nodeLabel mặc định, nếu không tooltip sáng-màu vẫn hiện"
    # tooltip phải có nền sáng + chữ đậm trong CSS
    css = html.replace(" ", "").replace("\n", "")
    assert "#tip{" in css, "thiếu CSS cho tooltip"
    assert "background:#ffffff" in css and "color:#1f2733" in css, \
        "tooltip phải nền trắng, chữ đậm để đọc được trên nền trắng"


# ---------------------------------------------------------------------
# 3. Gợi ý hồ sơ mới (cold-start)
# ---------------------------------------------------------------------
@pytest.fixture(scope="module")
def jobs_df() -> pd.DataFrame:
    return pd.read_csv(ROOT / "artifacts" / "medajob" / "jobs.csv",
                       encoding="utf-8-sig")


def test_coldstart_returns_results(jobs_df) -> None:
    from app.components.coldstart import score_profile

    df = score_profile(jobs_df, ["python", "sql"], top_k=5)
    assert not df.empty
    assert len(df) <= 5
    assert list(df["hạng"]) == sorted(df["hạng"])
    # hạng bắt đầu từ 1 và liên tục
    assert list(df["hạng"]) == list(range(1, len(df) + 1))


def test_coldstart_empty_profile_returns_empty(jobs_df) -> None:
    from app.components.coldstart import score_profile

    assert score_profile(jobs_df, []).empty
    assert score_profile(jobs_df, ["", "  "]).empty


def test_coldstart_unknown_skill_returns_empty(jobs_df) -> None:
    from app.components.coldstart import score_profile

    assert score_profile(jobs_df, ["ky_nang_khong_ton_tai_xyz"]).empty


def test_coldstart_is_case_insensitive(jobs_df) -> None:
    """'Python' và 'python' phải cho cùng kết quả."""
    from app.components.coldstart import score_profile

    a = score_profile(jobs_df, ["Python", "SQL"], top_k=5)
    b = score_profile(jobs_df, ["python", "sql"], top_k=5)
    assert list(a["tiêu đề"]) == list(b["tiêu đề"])


def test_coldstart_min_match_filters(jobs_df) -> None:
    """min_match cao hơn phải cho ít kết quả hơn hoặc bằng."""
    from app.components.coldstart import score_profile

    loose = score_profile(jobs_df, ["python", "sql"], min_match=1)
    strict = score_profile(jobs_df, ["python", "sql"], min_match=2)
    assert len(strict) <= len(loose)
    assert (strict["số kỹ năng khớp"] >= 2).all()


def test_coldstart_lists_skills(jobs_df) -> None:
    """all_skills phải trả danh sách không rỗng, đã sắp theo độ phổ biến."""
    from app.components.coldstart import all_skills

    sk = all_skills(jobs_df)
    assert len(sk) > 50
    assert sk[0] == "python"       # kỹ năng phổ biến nhất trong bộ dữ liệu này


# ---------------------------------------------------------------------
# 4. Thuật ngữ chuyên ngành phải giữ nguyên tiếng Anh
# ---------------------------------------------------------------------
def test_no_translated_jargon_in_app() -> None:
    """Không được dịch các thuật ngữ trong docs/QUY_UOC_THUAT_NGU.md."""
    banned = [
        "học liên bang", "Học liên bang",
        "mô hình liên bang", "Mô hình liên bang",
        "mạng nơ-ron đồ thị", "đồ thị nơ-ron",
        "trung bình liên bang",
    ]
    offenders = []
    for f in list((ROOT / "app").rglob("*.py")):
        txt = f.read_text(encoding="utf-8", errors="replace")
        for b in banned:
            if b in txt:
                offenders.append((f.relative_to(ROOT).as_posix(), b))
    assert not offenders, f"còn dịch thuật ngữ: {offenders}"


def test_glossary_doc_exists() -> None:
    """Quy ước thuật ngữ phải tồn tại để người viết sau đối chiếu."""
    p = ROOT / "docs" / "QUY_UOC_THUAT_NGU.md"
    assert p.exists()
    txt = p.read_text(encoding="utf-8")
    for term in ("Federated Learning", "GNN", "GraphSAGE", "cold-start"):
        assert term in txt, f"quy ước thiếu thuật ngữ {term}"
