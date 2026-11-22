"""Đồ thị 3D tương tác — nhúng `3d-force-graph` (Three.js/WebGL) vào Streamlit.

VÌ SAO KHÔNG DÙNG PYDECK (đã thử và thất bại)
=============================================
Bản đầu dùng `pdk.View(type="OrbitView")`. Kết quả: **khung trắng hoàn toàn**.
pydeck serialize view thành `"@@type": "OrbitView"`, còn bundle deck.gl mà
Streamlit đóng gói **chỉ đăng ký `MapView`** — registry tra ra `undefined` ->
canvas rỗng, không báo lỗi. Chi tiết ở mục 9 của
`docs/KHAO_SAT_DEMO_TRUC_QUAN.md`.

QUY TẮC AN TOÀN: KHÔNG GỌI API d3 TRỰC TIẾP
============================================
Đã gặp lỗi runtime: `TypeError: Cannot read properties of undefined
(reading 'tick')`.

Truy trong bundle: `tickFrame` làm

    t.engineRunning && ( ... t.layout[a?"tick":"step"]() ... )

`t.layout` CHỈ được gán trong một nhánh bên trong handler `graphData`
(nhánh dựng d3-force / ngraph layout), nhưng `t.engineRunning = true` thì đặt
**vô điều kiện** ở cuối handler. Nếu nhánh đó không chạy — ví dụ vì khung chưa
có kích thước, hoặc vì `d3Force('charge')` chưa tồn tại lúc ta gọi — thì
`engineRunning` bật mà `layout` vẫn `undefined`, và frame kế tiếp sẽ nổ.

`d3ReheatSimulation()` và `d3Force(...)` đều gọi `resetCountdown()`, tức bật
`engineRunning` — đúng đường dẫn tới lỗi trên.

Vì vậy module này **chỉ** dùng API công khai cấp cao (`graphData`,
`nodeColor`, `linkColor`, `zoomToFit`, accessor props). Mọi thay đổi bố cục
đều thực hiện bằng cách **tính toạ độ ở JS rồi nạp lại qua `graphData()`** —
đường này để thư viện tự dựng lại layout bên trong nó.

BA CÁCH SẮP XẾP
================
- `force`  — toạ độ gốc từ `spring_layout` của Python, để d3 tự chạy.
- `kind`   — tách 4 cụm theo loại nút (tứ diện).
- `layer`  — xếp tầng: Ngành -> Kỹ năng -> Tin -> Người dùng.

`kind`/`layer` giữ nguyên hình dạng cục bộ của từng loại trong `spring_layout`
rồi co giãn về bán kính `SPREAD` và dời về tâm cụm. Cách này tất định, không
phải chỉnh tham số lực — dễ tái lập và dễ kiểm bằng test.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

ASSET = Path(__file__).resolve().parents[1] / "assets" / "3d-force-graph.min.js"

# Màu khớp app/components/__init__.py (White + Orange design system)
_KIND_COLOR = {
    "Người dùng":     "#7b241c",
    "Tin tuyển dụng": "#e8836b",
    "Kỹ năng":        "#0EA5E9",
    "Nghề O*NET":     "#10B981",
    "Ngành":          "#10B981",
}
_EDGE_COLOR = {"Công khai": "#F97316", "Riêng tư": "#EF4444"}

# Bán kính mỗi cụm sau co giãn. Khoảng cách giữa các tâm cụm phải > 2*SPREAD,
# nếu không các cụm chồng lên nhau và chế độ "tách cụm" không còn tác dụng.
SPREAD = 150.0
_CLUSTER_CENTERS = {
    "Người dùng":     {"x": 340, "y": -50, "z": 0},
    "Tin tuyển dụng": {"x": -140, "y": 220, "z": 220},
    "Kỹ năng":        {"x": -140, "y": -220, "z": 220},
    "Ngành":          {"x": -140, "y": 0, "z": -290},
}
_LAYER_CENTERS = {
    "Ngành":          {"x": 0, "y": 190, "z": 0},
    "Kỹ năng":        {"x": 0, "y": 65, "z": 0},
    "Tin tuyển dụng": {"x": 0, "y": -70, "z": 0},
    "Người dùng":     {"x": 0, "y": -200, "z": 0},
}

# Các method cấp cao mà module này thực sự gọi. Test đối chiếu với bundle để
# chắc không gọi tên không tồn tại.
ALLOWED_METHODS = (
    "backgroundColor", "cooldownTicks", "graphData", "linkColor",
    "linkOpacity", "linkWidth", "nodeColor", "nodeId", "nodeLabel",
    "nodeOpacity", "nodeResolution", "nodeVal", "onEngineStop",
    "onNodeClick", "onNodeHover", "zoomToFit",
)


@lru_cache(maxsize=1)
def _lib_source() -> str:
    """Đọc bundle JS một lần rồi cache (690 KB, không đọc lại mỗi rerun)."""
    if not ASSET.exists():
        raise FileNotFoundError(
            f"Thiếu {ASSET}. Chạy: python tools/fetch_3d_asset.py")
    return ASSET.read_text(encoding="utf-8")


def _payload(nodes: pd.DataFrame, edges: pd.DataFrame) -> dict:
    """Chuyển DataFrame -> {nodes, links} mà 3d-force-graph hiểu.

    Toạ độ đưa vào bằng `x/y/z` (không phải `fx/fy/fz`): `fx/fy/fz` là ghim
    cứng, sẽ làm lực đẩy 3D vô hiệu và đồ thị đặc lại rất khó đọc.
    """
    use_id = ("node_id" in nodes.columns) and ({"source", "target"} <= set(edges.columns))
    scale = 220.0
    ns = []
    ids = set()
    keyed = {}
    for r in nodes.itertuples(index=False):
        nid = str(r.node_id) if use_id else f"{r.label}|{r.x:.5f}|{r.y:.5f}"
        ids.add(nid)
        ns.append({
            "id": nid,
            "name": str(r.label),
            "kind": str(r.kind),
            "deg": int(r.degree),
            "x": (float(r.x) - 0.5) * scale,
            "y": (float(r.y) - 0.5) * scale,
            "z": (float(r.z) - 0.5) * scale,
        })
        if not use_id:
            keyed[(round(float(r.x), 5), round(float(r.y), 5))] = nid

    links = []
    if use_id:
        has_edge_kind = "edge_kind" in edges.columns
        for r in edges.itertuples(index=False):
            a, b = str(r.source), str(r.target)
            if a in ids and b in ids and a != b:
                ek = str(r.edge_kind if has_edge_kind else getattr(r, "kind", "Công khai"))
                # source/target là CHUỖI ID, không phải object — tránh phụ thuộc
                # vào việc thư viện đã thay object vào chưa
                links.append({"source": a, "target": b, "kind": ek})
    else:
        for r in edges.itertuples(index=False):
            a = keyed.get((round(float(r.x), 5), round(float(r.y), 5)))
            b = keyed.get((round(float(r.x2), 5), round(float(r.y2), 5)))
            if a and b:
                # source/target là CHUỖI ID, không phải object — tránh phụ thuộc
                # vào việc thư viện đã thay object vào chưa
                links.append({"source": a, "target": b,
                              "kind": str(r.edge_kind)})
    return {"nodes": ns, "links": links}


_JS_APP = r"""
(function () {
  // --- kiểm môi trường trước khi làm gì khác ------------------------
  try {
    var cv = document.createElement('canvas');
    if (!cv.getContext('webgl2')) {
      fail('Trình duyệt không hỗ trợ WebGL2 (cần Chrome/Edge/Firefox bản mới).');
      return;
    }
  } catch (e) {
    fail('Không khởi tạo được WebGL: ' + e.message);
    return;
  }

  var DATA = __DATA__;
  var KC = __KC__, EC = __EC__;
  var TETRA = __TETRA__, LAYER = __LAYER__, SPREAD = __SPREAD__;

  if (!DATA.nodes || !DATA.nodes.length) {
    fail('Không có nút nào để vẽ.');
    return;
  }

  var ALLN = DATA.nodes, ALLL = DATA.links;
  var ORIG = {}, MAXDEG = 0;
  var byId = {};
  ALLN.forEach(function (n) {
    ORIG[n.id] = { x: n.x, y: n.y, z: n.z };
    byId[n.id] = n;
    if (n.deg > MAXDEG) MAXDEG = n.deg;
  });

  var mode = 'force';
  var minDeg = 0;
  var focusOn = true;
  var hovered = null, pinned = null, focusSet = null, adj = null;
  var ready = false;
  // LỖI ĐÃ SỬA — "tự zoom nhỏ lại khi vừa thả chuột":
  // bản trước gọi `Graph.onEngineStop(() => zoomToFit(...))`. Sự kiện này bắn
  // lại MỖI LẦN lực đẩy dừng, kể cả khi người dùng vừa kéo/zoom xong (kéo nút
  // làm lực đẩy chạy lại), nên khung nhìn bị giật về "vừa toàn đồ thị".
  // Giờ chỉ tự canh khung MỘT LẦN sau khi nạp dữ liệu lần đầu, và chỉ khi
  // người dùng chưa tự đụng vào camera.
  var userMovedCamera = false;
  var firstFitDone = false;

  function lid(v) { return (v && v.id) || v; }

  // ---------------- tô sáng kết quả tìm kiếm --------------------------
  // Giống bản 2D: ô tìm kiếm nằm NGOÀI iframe nên Streamlit truyền danh sách
  // nút khớp vào lúc sinh HTML. Mỗi lần gõ thêm, Streamlit rerun và iframe
  // được dựng lại với tập mới — không cần IPC hai chiều.
  var HL = {};
  (function () {
    var arr = __HIGHLIGHT__;
    for (var i = 0; i < arr.length; i++) { HL[arr[i]] = true; }
  })();
  var HL_COUNT = Object.keys(HL).length;
  function isHl(id) { return !!HL[id]; }

  // Tập "sáng" khi có tìm kiếm = nút khớp ∪ láng giềng trực tiếp của chúng.
  // Mọi nút ngoài tập này mờ hẳn — giống hệt hành vi bấm một nút (`focusSet`).
  // Dựng lại mỗi lần `graphData` vì danh sách cạnh thay đổi theo bộ lọc/layout.
  var HL_FOCUS = {};
  function buildHlFocus(links) {
    HL_FOCUS = {};
    if (!HL_COUNT) { return; }
    Object.keys(HL).forEach(function (id) { HL_FOCUS[id] = true; });
    links.forEach(function (l) {
      var a = lid(l.source), b = lid(l.target);
      if (HL[a]) { HL_FOCUS[b] = true; }
      if (HL[b]) { HL_FOCUS[a] = true; }
    });
  }

  function buildAdj(links) {
    var m = {};
    links.forEach(function (l) {
      var a = lid(l.source), b = lid(l.target);
      (m[a] = m[a] || {})[b] = true;
      (m[b] = m[b] || {})[a] = true;
    });
    return m;
  }

  function nodeColorFn(n) {
    // Ưu tiên: đang có focus (bấm/rê) thì theo focus; còn không thì theo
    // tìm kiếm.
    //
    // LỖI ĐÃ SỬA — tìm kiếm chỉ ĐỔI MÀU nút khớp, phần còn lại vẫn nguyên
    // màu nên không "nổi" lên được (người dùng nói: "không hiện trên đồ thị").
    // Yêu cầu là hành vi GIỐNG BẤM MỘT NÚT: nút khớp + láng giềng sáng, mọi
    // thứ khác mờ hẳn đi.
    // Nay: tập "sáng" = nút khớp ∪ láng giềng của chúng (HL_FOCUS). Mọi nút
    // ngoài tập đó tô #e8ecf1, đúng sắc mà `focusSet` đang dùng.
    if (focusSet && !focusSet[n.id]) { return '#e8ecf1'; }
    if (HL_COUNT > 0) {
      if (HL_FOCUS[n.id]) {
        return isHl(n.id) ? '#b8860b' : (KC[n.kind] || '#7f8c8d');
      }
      return '#e8ecf1';
    }
    return KC[n.kind] || '#7f8c8d';
  }
  function linkColorFn(l) {
    if (focusSet && !(focusSet[lid(l.source)] && focusSet[lid(l.target)]))
      return '#f2f5f8';
    // Cạnh nằm ngoài đường đi liên quan tới kết quả tìm kiếm thì luôn mờ.
    if (HL_COUNT > 0 &&
        !(HL_FOCUS[lid(l.source)] && HL_FOCUS[lid(l.target)])) {
      return '#f2f5f8';
    }
    return EC[l.kind] || '#7f8c8d';
  }

  // Tooltip TỰ VIẾT thay vì để thư viện lo.
  // Lỗi đã gặp: `.scene-tooltip` mặc định của 3d-force-graph có `color:
  // lavender` (chữ sáng) không có nền -> trên nền trắng của app, chữ gần như
  // vô hình khi rê chuột vào nút. Giờ ta tự dựng thẻ tooltip nền trắng, chữ
  // đậm, viền nhẹ — và tắt tooltip mặc định.
  var tip = document.createElement('div');
  tip.id = 'tip';
  document.body.appendChild(tip);

  function showTip(n, ev) {
    if (!n) { tip.style.display = 'none'; return; }
    var color = KC[n.kind] || '#7f8c8d';
    tip.innerHTML =
      '<div class="t-name">' + n.name + '</div>' +
      '<div class="t-row"><span class="t-dot" style="background:' + color +
      '"></span>' + n.kind + '</div>' +
      '<div class="t-row t-muted">bậc ' + n.deg + '</div>';
    tip.style.display = 'block';
    var pad = 14;
    var x = (ev ? ev.clientX : 0) + pad;
    var y = (ev ? ev.clientY : 0) + pad;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    if (x + w > window.innerWidth - 8) x = window.innerWidth - w - 8;
    if (y + h > window.innerHeight - 8) y = (ev ? ev.clientY : 0) - h - pad;
    tip.style.left = Math.max(4, x) + 'px';
    tip.style.top = Math.max(4, y) + 'px';
  }

  var Graph = ForceGraph3D()(document.getElementById('g'))
    .backgroundColor('#ffffff')
    .showNavInfo(false)       // dòng "Left-click: rotate..." của thư viện
                              // chồng lên dòng gợi ý của ta (thấy trong ảnh)
    .nodeId('id')
    .nodeLabel('')            // tắt tooltip mặc định (chữ sáng, không nền)
    .nodeVal(function (n) { return 1.1 + Math.sqrt(n.deg) * 0.95; })
    .nodeOpacity(0.95)
    .nodeResolution(10)
    .linkOpacity(function (l) { return l.kind === 'Riêng tư' ? 0.8 : 0.3; })
    .linkWidth(function (l) { return l.kind === 'Riêng tư' ? 1.6 : 0.7; })
    .cooldownTicks(180);

  // --- tính toạ độ cho chế độ cụm / tầng ----------------------------
  function clustered(centers, flatten) {
    var stat = {}, out = {};
    ALLN.forEach(function (n) {
      var o = ORIG[n.id];
      var s = stat[n.kind] || (stat[n.kind] = {
        sx: 0, sy: 0, sz: 0, n: 0, r: 0, list: []
      });
      s.sx += o.x; s.sy += o.y; s.sz += o.z; s.n++;
      s.list.push(n.id);
    });
    for (var k in stat) {
      var s = stat[k];
      s.cx = s.sx / s.n; s.cy = s.sy / s.n; s.cz = s.sz / s.n;
      s.list.forEach(function (id) {
        var o = ORIG[id];
        var d = Math.sqrt(Math.pow(o.x - s.cx, 2) +
                          Math.pow(o.y - s.cy, 2) +
                          Math.pow(o.z - s.cz, 2));
        if (d > s.r) s.r = d;
      });
      if (s.r < 1e-6) s.r = 1;
    }
    ALLN.forEach(function (n) {
      var s = stat[n.kind], c = centers[n.kind] || (n.kind === 'Nghề O*NET' ? centers['Ngành'] : null);
      var o = ORIG[n.id];
      if (!s || !c) { out[n.id] = o; return; }
      var sc = SPREAD / s.r;
      var dx = (o.x - s.cx) * sc, dy = (o.y - s.cy) * sc, dz = (o.z - s.cz) * sc;
      if (flatten) dy *= 0.14;
      out[n.id] = { x: c.x + dx, y: c.y + dy, z: c.z + dz };
    });
    return out;
  }

  // --- nạp dữ liệu (ĐƯỜNG DUY NHẤT để đổi bố cục) --------------------
  function render() {
    var kept = ALLN.filter(function (n) { return n.deg >= minDeg; });
    if (!kept.length) { fail('Bộ lọc bậc hiện tại không còn nút nào.'); return; }

    var keep = {};
    kept.forEach(function (n) { keep[n.id] = true; });

    var pos = null;
    if (mode === 'kind') pos = clustered(TETRA, false);
    else if (mode === 'layer') pos = clustered(LAYER, true);

    var ns = kept.map(function (n) {
      var p = (pos && pos[n.id]) || ORIG[n.id];
      return {
        id: n.id, name: n.name, kind: n.kind, deg: n.deg,
        x: p.x, y: p.y, z: p.z
      };
    });
    var ls = ALLL.filter(function (l) {
      return keep[lid(l.source)] && keep[lid(l.target)];
    }).map(function (l) {
      return { source: lid(l.source), target: lid(l.target), kind: l.kind };
    });

    adj = buildAdj(ls);
    buildHlFocus(ls);   // phải chạy TRƯỚC graphData để màu đúng ngay frame đầu
    Graph.graphData({ nodes: ns, links: ls });

    // Hook cho kiểm chứng tự động (Selenium): 3d-force-graph vẽ bằng WebGL
    // nên KHÔNG đọc được pixel bằng `getImageData`, và instance graph không
    // nằm ở biến toàn cục nào. Phơi ra đây để test đọc được trạng thái thật
    // (số nút, màu từng nút, tập tô sáng) thay vì đoán qua ảnh.
    window.__G3__ = {
      graph: Graph,
      nodes: ns,
      links: ls,
      hl: HL,
      hlCount: HL_COUNT,
      // đếm nút theo màu: GỌI THẲNG nodeColorFn thay vì đọc `n.color`.
      // `n.color` chỉ có sau khi three.js chạy accessor trong frame vẽ; đọc
      // sớm sẽ ra undefined. Gọi hàm là nguồn sự thật, không phụ thuộc frame.
      colors: function () {
        var c = {};
        ns.forEach(function (n) {
          var k = nodeColorFn(n) || 'none';
          c[k] = (c[k] || 0) + 1;
        });
        return c;
      },
      status: function () {
        return {nodes: ns.length, links: ls.length,
                hlCount: HL_COUNT, hlFocusCount: Object.keys(HL_FOCUS).length,
                ready: ready};
      }
    };

    var cnt = document.getElementById('degcount');
    if (cnt) cnt.textContent = ns.length + ' nút / ' + ls.length + ' cạnh';
    ready = true;
  }

  // --- làm nổi vùng liên quan ---------------------------------------
  function updateFocus() {
    var target = hovered || pinned;
    if (!focusOn || !target || !adj) {
      focusSet = null;
    } else {
      focusSet = {};
      focusSet[target] = true;
      var nb = adj[target] || {};
      for (var k in nb) focusSet[k] = true;
    }
    // hàm mới (closure mới) để thư viện thấy prop đổi và vẽ lại màu
    Graph.nodeColor(nodeColorFn).linkColor(linkColorFn);
    var lab = document.getElementById('focusinfo');
    if (lab) {
      lab.textContent = (!focusSet) ? ''
        : 'Đang làm nổi ' + Object.keys(focusSet).length + ' nút'
          + (pinned ? ' · đã ghim' : '');
    }
  }

  // --- nối UI -------------------------------------------------------
  function setMode(next) {
    mode = next;
    document.querySelectorAll('#panel button[data-layout]').forEach(function (b) {
      b.classList.toggle('on', b.dataset.layout === mode);
    });
    render();
    // đổi cách sắp xếp -> coi như người dùng muốn xem lại toàn cảnh
    userMovedCamera = false;
    setTimeout(function () {
      if (!userMovedCamera) Graph.zoomToFit(700, 50);
    }, 700);
  }

  document.querySelectorAll('#panel button[data-layout]').forEach(function (b) {
    b.addEventListener('click', function () {
      try { setMode(b.dataset.layout); }
      catch (e) { fail('Đổi cách sắp xếp thất bại: ' + e.message); }
    });
  });

  var slider = document.getElementById('degs');
  slider.min = 0;
  slider.max = Math.max(1, Math.min(20, MAXDEG));
  slider.value = minDeg;
  document.getElementById('degv').textContent = minDeg;
  slider.addEventListener('input', function () {
    var parsed = parseInt(slider.value, 10);
    minDeg = isNaN(parsed) ? 0 : parsed;
    document.getElementById('degv').textContent = minDeg;
    try { render(); }
    catch (e) { fail('Lọc theo bậc thất bại: ' + e.message); }
  });

  document.getElementById('focuscb').addEventListener('change', function (e) {
    focusOn = e.target.checked;
    updateFocus();
  });

  document.getElementById('reset').addEventListener('click', function () {
    pinned = null; hovered = null;
    focusSet = null;
    userMovedCamera = false;          // đây là hành động chủ động: canh lại
    Graph.nodeColor(nodeColorFn).linkColor(linkColorFn);
    Graph.zoomToFit(700, 50);
    var lab = document.getElementById('focusinfo');
    if (lab) lab.textContent = '';
  });

  // Đánh dấu người dùng đã tự điều khiển camera -> thôi tự canh khung.
  // Nghe trên chính canvas của thư viện (wheel/chuột/kéo), không đụng API
  // điều khiển nội bộ.
  (function watchCamera() {
    var host = document.getElementById('g');
    function mark() { userMovedCamera = true; }
    ['wheel', 'pointerdown', 'touchstart'].forEach(function (ev) {
      host.addEventListener(ev, mark, { passive: true });
    });
  })();

  Graph.onNodeHover(function (n) {
    hovered = n ? n.id : null;
    updateFocus();
    document.body.style.cursor = n ? 'pointer' : null;
  });

  // rê chuột: hiện tooltip tự viết ở đúng vị trí con trỏ
  document.getElementById('g').addEventListener('mousemove', function (ev) {
    if (hovered) showTip(byId[hovered], ev); else tip.style.display = 'none';
  });
  document.getElementById('g').addEventListener('mouseleave', function () {
    tip.style.display = 'none';
  });

  Graph.onNodeClick(function (n) {
    pinned = (pinned === n.id) ? null : n.id;
    updateFocus();
  });

  // --- chú giải màu (bản trước thiếu, người xem không biết màu là gì) --
  (function buildLegend() {
    var box = document.getElementById('legend');
    if (!box) return;
    var html = '<div class="lg-title">Loại nút</div>';
    Object.keys(KC).forEach(function (k) {
      if (k === 'Ngành' && KC['Nghề O*NET']) return;
      var label = (k === 'Nghề O*NET') ? 'Nghề O*NET (Ngành)' : k;
      html += '<div class="lg-row"><span class="lg-dot" style="background:'
            + KC[k] + '"></span>' + label + '</div>';
    });
    html += '<div class="lg-sep"></div><div class="lg-title">Loại cạnh</div>';
    html += '<div class="lg-row"><span class="lg-line" style="border-top-color:'
          + EC['Công khai'] + '"></span>Công khai</div>';
    html += '<div class="lg-row"><span class="lg-line" style="border-top-color:'
          + EC['Riêng tư'] + '"></span>Riêng tư</div>';
    html += '<div class="lg-sep"></div>'
          + '<div class="lg-row muted-txt" style="color:#6b7787">'
          + 'Kích thước nút = bậc</div>';
    box.innerHTML = html;
  })();

  // khởi động: đặt màu trước, rồi nạp dữ liệu một lần duy nhất
  Graph.nodeColor(nodeColorFn).linkColor(linkColorFn);
  try {
    render();
    document.querySelector('button[data-layout="force"]')
      .classList.add('on');
  } catch (e) {
    fail('Khởi tạo thất bại: ' + e.message);
    return;
  }

  // Canh khung MỘT LẦN sau lần nạp đầu — không canh lại mỗi khi lực đẩy dừng.
  // Nếu canh lại theo `onEngineStop`, mỗi lần kéo nút (làm lực đẩy chạy lại)
  // rồi thả chuột thì camera sẽ tự lùi ra, đúng triệu chứng "tự zoom nhỏ lại".
  Graph.onEngineStop(function () {
    if (!firstFitDone && !userMovedCamera) {
      firstFitDone = true;
      Graph.zoomToFit(800, 50);
    }
  });
})();
"""


def graph_html_3d(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    height: int = 600,
    highlight: list[int] | None = None,
) -> str:
    """Sinh một trang HTML tự chứa vẽ đồ thị 3D (không cần mạng).

    `highlight`: danh sách CHỈ SỐ DÒNG trong `nodes` (đã `reset_index`), dùng
    để tô sáng kết quả tìm kiếm giống bản 2D. `None`/rỗng = không tô sáng.
    """
    data = _payload(nodes, edges)
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    # Đổi chỉ số dòng -> node id của 3D. `_payload` sinh id dạng
    # f"{label}|{x:.5f}|{y:.5f}", nên phải dựng lại đúng chuỗi đó.
    hl_ids: list[str] = []
    if highlight:
        for v in highlight:
            try:
                iv = int(v)
            except (TypeError, ValueError):
                continue
            if 0 <= iv < len(data["nodes"]):
                hl_ids.append(data["nodes"][iv]["id"])

    app_js = (_JS_APP
              .replace("__DATA__", blob)
              .replace("__KC__", json.dumps(_KIND_COLOR, ensure_ascii=False))
              .replace("__EC__", json.dumps(_EDGE_COLOR, ensure_ascii=False))
              .replace("__TETRA__",
                       json.dumps(_CLUSTER_CENTERS, ensure_ascii=False))
              .replace("__LAYER__",
                       json.dumps(_LAYER_CENTERS, ensure_ascii=False))
              .replace("__HIGHLIGHT__", json.dumps(hl_ids))
              .replace("__SPREAD__", repr(SPREAD)))

    return f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8">
<style>
  html,body{{margin:0;padding:0;background:#fff;overflow:hidden;
            font-family:system-ui,-apple-system,sans-serif}}
  #g{{width:100%;height:{height}px}}
  /* LỖI ĐÃ SỬA — bảng điều khiển và chú giải biến mất.
     Hai nguyên nhân cộng lại:
       (1) THỨ TỰ DOM: #panel/#legend nằm TRƯỚC #g, mà canvas của thư viện
           nằm trong .scene-container (position:relative) nên vẽ đè lên.
           #hint nằm SAU #g nên vẫn hiện — đúng ảnh chụp màn hình.
       (2) KHÔNG có z-index: overlay là position:absolute nhưng không xếp
           lớp, canvas WebGL thắng theo thứ tự vẽ.
     Sửa: đặt overlay SAU #g trong DOM **và** cho z-index cao. */
  #panel{{position:absolute;top:8px;left:8px;z-index:30;background:#ffffffF2;
          border:1px solid #E2E8F0;border-radius:10px;padding:8px 10px;
          font-size:12px;color:#0F172A;box-shadow:0 2px 10px rgba(15,23,42,0.06);
          max-width:min(96%,560px)}}
  #panel .row{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;
               margin-bottom:6px}}
  #panel .row:last-child{{margin-bottom:0}}
  #panel .lab{{color:#475569;min-width:64px;font-weight:600}}
  #panel button{{font:inherit;padding:3px 9px;border-radius:8px;
                 border:1px solid #E2E8F0;background:#fff;color:#0F172A;
                 cursor:pointer}}
  #panel button:hover{{background:#FFF7ED;border-color:#FDBA74;color:#C2410C}}
  #panel button.on{{background:#F97316;border-color:#F97316;color:#fff;
                    font-weight:600}}
  #panel input[type=range]{{width:120px}}
  #panel .muted{{color:#64748B}}
  #hint{{position:absolute;left:10px;bottom:8px;font-size:11px;color:#475569;
         background:#ffffffdd;padding:3px 7px;border-radius:6px}}
  #err{{display:none;font-size:14px;color:#EF4444;padding:18px;line-height:1.5}}
  /* Chú giải màu — bản trước KHÔNG có, người xem không biết màu nghĩa là gì */
  #legend{{position:absolute;right:8px;top:8px;z-index:30;background:#ffffffF2;
           border:1px solid #E2E8F0;border-radius:10px;padding:7px 10px;
           font-size:11px;color:#0F172A;box-shadow:0 2px 10px rgba(15,23,42,0.06);
           line-height:1.7}}
  #legend .lg-title{{font-weight:700;font-size:11px;color:#475569;
                     margin-bottom:3px}}
  #legend .lg-row{{display:flex;align-items:center;gap:6px;white-space:nowrap}}
  #legend .lg-dot{{width:9px;height:9px;border-radius:50%;flex:0 0 auto}}
  #legend .lg-line{{width:16px;height:0;border-top-width:2px;
                    border-top-style:solid;flex:0 0 auto}}
  #legend .lg-sep{{height:1px;background:#F1F5F9;margin:5px 0}}
  /* Tooltip tự viết: nền trắng, chữ đậm. Mặc định của thư viện là chữ
     lavender không nền -> vô hình trên nền trắng. */
  #tip{{position:fixed;display:none;z-index:9999;pointer-events:none;
        background:#ffffff;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
        border:1px solid #E2E8F0;border-radius:8px;
        padding:7px 10px;box-shadow:0 8px 24px rgba(15,23,42,0.12);
        font:12px/1.5 system-ui,-apple-system,sans-serif;color:#1f2733;
        max-width:280px}}
  #tip .t-name{{font-weight:700;margin-bottom:3px;color:#111824}}
  #tip .t-row{{display:flex;align-items:center;gap:6px}}
  #tip .t-dot{{width:8px;height:8px;border-radius:50%;flex:0 0 auto}}
  #tip .t-muted{{color:#6b7787;margin-top:1px}}
</style></head>
<body>
<div id="err"></div>
<!-- Canvas PHẢI đứng trước các overlay trong DOM: canvas của thư viện nằm
     trong .scene-container (position:relative), nếu overlay đứng trước thì
     bị vẽ đè lên và biến mất (lỗi đã gặp: không thấy chú giải). -->
<div id="g"></div>
<div id="panel">
  <div class="row">
    <span class="lab">Sắp xếp</span>
    <button data-layout="force">Chụm theo liên kết</button>
    <button data-layout="kind">Tách cụm theo loại</button>
    <button data-layout="layer">Xếp tầng</button>
  </div>
  <div class="row">
    <span class="lab">Bậc ≥</span>
    <input type="range" id="degs" min="0" max="10" value="0">
    <span id="degv" class="muted">0</span>
    <span id="degcount" class="muted"></span>
  </div>
  <div class="row">
    <label><input type="checkbox" id="focuscb" checked>
      Làm nổi vùng liên quan khi rê / bấm</label>
    <button id="reset">Xem lại toàn bộ</button>
  </div>
  <div class="row"><span id="focusinfo" class="muted"></span></div>
</div>
<div id="legend"></div>
<div id="hint">Kéo để xoay · cuộn để zoom · bấm một nút để ghim vùng liên quan · bấm lại để bỏ</div>
<script>
// Báo lỗi RÕ RÀNG thay vì khung trắng im lặng.
function fail(msg) {{
  var e = document.getElementById('err');
  if (!e) {{ return; }}
  e.style.display = 'block';
  e.innerHTML = '<b>Không vẽ được đồ thị 3D.</b><br>' + msg +
    '<br><br>Dùng tab <b>2D</b> ở cột bên phải — nội dung giống hệt.';
  var g = document.getElementById('g');
  if (g) {{ g.style.display = 'none'; }}
  var h = document.getElementById('hint');
  if (h) {{ h.style.display = 'none'; }}
  var p = document.getElementById('panel');
  if (p) {{ p.style.display = 'none'; }}
}}
window.addEventListener('error', function (ev) {{
  fail('Lỗi JavaScript: ' + (ev.message || 'không rõ'));
}});
</script>
<script>{_lib_source()}</script>
<script>{app_js}</script>
</body></html>"""


def render_graph_3d(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    height: int = 600,
) -> None:
    """Vẽ đồ thị 3D ngay trong trang Streamlit hiện tại."""
    st.components.v1.html(graph_html_3d(nodes, edges, height=height),
                          height=height + 4, scrolling=False)
