"""
Regression test cho hai lỗi thật đã gặp ở trang *Đồ thị việc làm*.

Cả hai đều KHÔNG làm app crash — chỉ làm hình vẽ sai — nên rất dễ lọt qua
smoke test. Đây là lý do có file này.

Lỗi 1: `top_skills` cộng offset lần hai (đã sửa trước).
Lỗi 2: `job_nodes` cộng offset lần hai (sửa trong phiên này).

Cách kiểm: nút "Tin tuyển dụng" phải nằm trọn trong dải node id của tin
(`[n_users, n_users+n_jobs)`). Nếu cộng nhầm `n_users`, một phần id sẽ rơi
sang dải kỹ năng và hình sẽ gán nhãn "Tin" cho nút kỹ năng.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / ".mplcache"))
sys.path.insert(0, str(ROOT))

GRAPH = ROOT / "artifacts" / "medajob" / "graph.npz"


@pytest.fixture(scope="module")
def dims() -> tuple[int, int, int, int]:
    z = np.load(GRAPH, allow_pickle=False)
    return (int(z["n_users"]), int(z["n_jobs"]),
            int(z["n_skills"]), int(z["n_industries"]))


@pytest.fixture(scope="module")
def view2d(dims):
    from app.views.do_thi_viec_lam import build_graph_view
    return build_graph_view.__wrapped__(dim=2)


@pytest.fixture(scope="module")
def view3d(dims):
    from app.views.do_thi_viec_lam import build_graph_view
    return build_graph_view.__wrapped__(dim=3)


def test_all_jobs_are_real_jobs(dims, view2d) -> None:
    """Số nút nhãn "Tin tuyển dụng" phải bằng đúng số tin được chọn (200).

    Bản lỗi chỉ cho ra 171 vì 29 id bị đẩy sang dải kỹ năng.
    """
    _, nJ, _, _ = dims
    nodes, _ = view2d
    n_job_expected = min(200, nJ)
    n_job_actual = int((nodes.kind == "Tin tuyển dụng").sum())
    assert n_job_actual == n_job_expected, (
        f"chỉ {n_job_actual}/{n_job_expected} tin được chọn đúng — "
        "nghi cộng offset lần hai vào job_nodes"
    )


def test_graph_not_fragmented(dims, view2d) -> None:
    """Đồ thị con phải liên thông đủ: không được rỗng cạnh và phải có
    cả cạnh công khai lẫn riêng tư (hai vế của luận điểm "ranh giới dữ liệu").
    """
    _, edges = view2d
    kinds = edges.edge_kind.value_counts()
    assert kinds.get("Công khai", 0) > 0, "không còn cạnh công khai"
    assert kinds.get("Riêng tư", 0) > 0, "không còn cạnh riêng tư"


def test_private_edges_are_minority(view2d) -> None:
    """Trong đồ thị con, cạnh riêng tư phải là thiểu số.

    Nếu là đa số thì gần như chắc chắn việc chọn nút đã sai (chọn nhầm sang
    vùng ứng viên), vì đồ thị con giữ toàn bộ tin + kỹ năng công khai.
    """
    _, edges = view2d
    share = (edges.edge_kind == "Riêng tư").mean()
    assert share < 0.5, f"cạnh riêng tư chiếm {share:.0%} — chọn nút sai"


def test_2d_and_3d_have_same_content(view2d, view3d) -> None:
    """Bật/tắt 2D–3D chỉ đổi cách nhìn, KHÔNG đổi tập nút/cạnh."""
    n2, e2 = view2d
    n3, e3 = view3d
    assert len(n2) == len(n3)
    assert len(e2) == len(e3)
    assert list(n2.kind) == list(n3.kind)


def test_3d_has_finite_z(view3d) -> None:
    """Toạ độ z phải hữu hạn — NaN sẽ làm pydeck không vẽ được gì."""
    nodes, edges = view3d
    for name, df, cols in [("nút", nodes, ["x", "y", "z"]),
                           ("cạnh", edges, ["x", "y", "z", "x2", "y2", "z2"])]:
        arr = df[cols].to_numpy(dtype=float)
        assert np.isfinite(arr).all(), f"{name} 3D có toạ độ NaN/inf"


def test_deck_builds_and_drops_private_edges(view3d) -> None:
    """HTML 3D dựng được, và tắt cạnh riêng tư thì số cạnh giảm đúng."""
    from app.components.graph3d import graph_html_3d

    nodes, edges = view3d
    html = graph_html_3d(nodes, edges)
    assert "ForceGraph3D" in html
    assert "Không vẽ được đồ thị 3D" in html, "thiếu báo lỗi thay cho khung trắng"

    public_only = edges[edges.edge_kind == "Công khai"]
    n_private = len(edges) - len(public_only)
    assert n_private > 0
    html2 = graph_html_3d(nodes, public_only)
    assert public_only.edge_kind.nunique() == 1


def test_3d_payload_has_no_broken_links(view3d) -> None:
    """Mọi cạnh phải trỏ tới nút tồn tại — cạnh gãy làm đồ thị gần như rỗng."""
    import json
    import re

    from app.components.graph3d import graph_html_3d

    nodes, edges = view3d
    html = graph_html_3d(nodes, edges)
    m = re.search(r"var DATA = (\{.*?\});\n", html, re.S)
    assert m, "không tìm thấy DATA trong HTML"
    data = json.loads(m.group(1).replace("<\\/", "</"))

    assert len(data["nodes"]) == len(nodes)
    ids = {n["id"] for n in data["nodes"]}
    broken = [lk for lk in data["links"]
              if lk["source"] not in ids or lk["target"] not in ids]
    assert not broken, f"{len(broken)} cạnh trỏ tới nút không tồn tại"


def test_3d_nodes_not_hard_pinned(view3d) -> None:
    """Nút phải dùng `x/y/z`, KHÔNG dùng `fx/fy/fz`.

    Lỗi đã gặp: ghim cứng mọi nút vào toạ độ Python thì lực đẩy 3D không làm
    gì, đồ thị đặc lại và rất khó đọc. Đây là lý do phải tách `x/y/z`.
    """
    import json
    import re

    from app.components.graph3d import graph_html_3d

    nodes, edges = view3d
    html = graph_html_3d(nodes, edges)
    data = json.loads(
        re.search(r"var DATA = (\{.*?\});\n", html, re.S).group(1)
        .replace("<\\/", "</"))

    for n in data["nodes"][:50]:
        assert "x" in n and "y" in n and "z" in n
        assert "fx" not in n and "fy" not in n and "fz" not in n, \
            "nút bị ghim cứng — lực đẩy 3D sẽ vô hiệu"


def test_3d_has_layout_and_filter_controls() -> None:
    """Phải có 3 cách sắp xếp + lọc theo bậc + làm nổi vùng liên quan."""
    from app.components.graph3d import graph_html_3d
    from app.views import do_thi_viec_lam as V

    nodes, edges = V.build_graph_view.__wrapped__(dim=3)
    html = graph_html_3d(nodes, edges)

    for layout in ("force", "kind", "layer"):
        assert f'data-layout="{layout}"' in html, f"thiếu nút sắp xếp {layout}"
    assert 'id="degs"' in html, "thiếu lọc theo bậc"
    assert 'id="focuscb"' in html, "thiếu làm nổi vùng liên quan"
    assert 'id="reset"' in html, "thiếu nút xem lại toàn bộ"


def test_cluster_centers_are_separated() -> None:
    """Tâm các cụm phải cách nhau > 2×spread, nếu không cụm chồng lên nhau.

    `spread` = 150 trong graph3d.py, nên ngưỡng là 300. Đã từng đặt tứ diện
    chỉ cách 260 khiến "tách cụm" gần như không có tác dụng.
    """
    import itertools
    import math

    from app.components.graph3d import SPREAD, _CLUSTER_CENTERS

    centers = _CLUSTER_CENTERS
    assert len(centers) == 4
    for a, b in itertools.combinations(centers.values(), 2):
        d = math.dist((a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"]))
        assert d > 2 * SPREAD, f"hai tâm cụm chỉ cách {d:.0f} (< {2*SPREAD:.0f})"


def test_no_unsafe_d3_api_calls() -> None:
    """KHÔNG được gọi API d3 trực tiếp.

    Lỗi đã gặp: `TypeError: Cannot read properties of undefined
    (reading 'tick')`.

    Trong bundle, `tickFrame` gọi `t.layout.tick()`, nhưng `t.layout` chỉ được
    gán trong một nhánh của handler `graphData`, còn `engineRunning` thì bật
    vô điều kiện. `d3ReheatSimulation()`/`d3Force()` đều gọi `resetCountdown()`
    (bật `engineRunning`) nên dễ rơi vào trạng thái `layout` undefined.

    Vì vậy mọi đổi bố cục phải đi qua `graphData()`.
    """
    from app.components.graph3d import _JS_APP

    forbidden = ["d3ReheatSimulation", "d3Force", "d3AlphaTarget",
                 "d3AlphaDecay", "d3VelocityDecay", "resetCountdown",
                 "tickFrame"]
    found = [f for f in forbidden if f + "(" in _JS_APP]
    assert not found, f"gọi API d3 nguy hiểm (gây lỗi 'reading tick'): {found}"


def test_all_graph_methods_are_verified() -> None:
    """Mọi method gọi trên Graph phải nằm trong ALLOWED_METHODS."""
    import re

    from app.components.graph3d import ALLOWED_METHODS, _JS_APP

    called = set(re.findall(r"\bGraph\.([a-zA-Z]\w*)\(", _JS_APP))
    extra = called - set(ALLOWED_METHODS)
    assert not extra, f"gọi method chưa kiểm: {sorted(extra)}"


def test_3d_asset_present() -> None:
    """Bundle JS phải có sẵn — app phải chạy offline, không tải CDN lúc chạy."""
    asset = ROOT / "app" / "assets" / "3d-force-graph.min.js"
    assert asset.exists(), "thiếu bundle — chạy: python tools/fetch_3d_asset.py"
    assert asset.stat().st_size > 200_000, "bundle nghi bị cắt cụt"


def test_deck_rejects_empty_graph() -> None:
    """Đồ thị rỗng phải báo lỗi rõ ràng, không để vẽ khung trắng."""
    import pandas as pd

    from app.components.graph3d import graph_html_3d

    empty_nodes = pd.DataFrame(
        {"x": [], "y": [], "z": [], "kind": [], "label": [], "degree": []})
    empty_edges = pd.DataFrame(
        {"x": [], "y": [], "z": [], "x2": [], "y2": [], "z2": [],
         "edge_kind": []})
    html = graph_html_3d(empty_nodes, empty_edges)
    assert "Không có nút nào để vẽ" in html


def test_spring_layout_dim_3() -> None:
    """spring_layout phải trả đúng số chiều được yêu cầu."""
    from app.components import spring_layout

    src = [0, 1, 2, 1]
    dst = [1, 2, 3, 3]
    p2 = spring_layout(4, src, dst, iterations=5, dim=2)
    p3 = spring_layout(4, src, dst, iterations=5, dim=3)
    assert p2.shape == (4, 2)
    assert p3.shape == (4, 3)
    assert np.isfinite(p2).all() and np.isfinite(p3).all()
