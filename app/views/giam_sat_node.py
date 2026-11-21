"""Trang 6 — Giám sát node Federated Learning (nhúng giao diện ui/).

CÁCH TRANG NÀY HOẠT ĐỘNG — phương án 1a: iframe + inline CSS/JS
----------------------------------------------------------------
`ui/index.html` nạp CSS/JS bằng đường dẫn TƯƠNG ĐỐI (`assets/app.css`,
`vendor/chart.umd.min.js`, `assets/app.js`). Nhúng thẳng vào
`st.components.v1.html()` là hỏng: component dùng iframe `srcdoc` nên mọi
đường dẫn tương đối trỏ vào chỗ không tồn tại → mất CSS, không chạy JS.

Vì vậy `tools/build_ui_inline.py` sinh ra `ui/_inline/index_inline.html`:
một file HTML duy nhất đã nhúng sẵn CSS, JS và cả font base64. Trang này chỉ
đọc file đó rồi đưa vào iframe. **Không sửa tay file sinh** — sửa ở `ui/` rồi
chạy lại `python tools/build_ui_inline.py`.

VỀ `?api=`:
    Component iframe của Streamlit không cho thêm query string vào URL (nội
    dung đi qua `srcdoc`). Bản inline chèn một shim rất nhỏ trước `app.js`,
    bơm giá trị `api` tương đương `?api=...` vào `URLSearchParams` — nên vẫn
    đổi được backend mà không phải sửa `ui/assets/app.js`.

VỀ WebSocket trong iframe:
    Same-origin với `127.0.0.1:8000` nên thường chạy được. Nếu bị chặn (proxy,
    CSP, trình duyệt chặn mixed content), `app.js` chỉ hiện badge
    "disconnected" và tự thử lại mỗi 3 s — phần REST (danh sách client, start
    training, biểu đồ) **vẫn hoạt động**, trang không crash.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components import (  # noqa: E402
    GREEN, INK, ORANGE, ORANGE_DARK, RED, SKY, finding, header, metric_row,
)

# Mặc định khớp `API_BASE` trong ui/assets/app.js. Cho phép đổi khi cần:
#   $env:DSS_API_BASE="http://127.0.0.1:8011"
DEFAULT_API_BASE = "http://127.0.0.1:8000"
API_BASE = os.environ.get("DSS_API_BASE", DEFAULT_API_BASE).rstrip("/")

INLINE_HTML = ROOT / "ui" / "_inline" / "index_inline.html"
PLACEHOLDER = "__FL_API_BASE__"

# Hai lệnh chạy tay — in NGUYÊN VĂN để người xem copy được.
RUN_UVICORN = "python -m uvicorn api.main:app --host 127.0.0.1 --port 8000"
RUN_STREAMLIT = "python -m streamlit run app/streamlit_app.py"

# Chiều cao iframe: đủ cho console 2 cột + explainers bên dưới mà không cần scrollbar lồng.
IFRAME_HEIGHT = 1180


# =====================================================================
# Bản inline — tự sinh nếu thiếu/cũ
# =====================================================================
def _ensure_inline_at_import() -> None:
    """Nếu `ui/_inline/` chưa có thì sinh ngay lúc import.

    Chỉ sinh khi THIẾU file — không kiểm tra "cũ" ở đây (việc đó làm trong
    `_inline_html`, nơi đã có cache theo mtime của ui/). Nhờ vậy import module
    không tốn thời gian khi mọi thứ đã sẵn sàng, và lỗi build không làm sập
    toàn bộ app lúc import.
    """
    if INLINE_HTML.is_file():
        return
    try:
        from tools.build_ui_inline import ensure_inline

        ensure_inline()
    except Exception as exc:                       # noqa: BLE001
        # Không raise: trang sẽ báo lỗi rõ ràng khi render (xem `_inline_html`).
        print(f"[giam_sat_node] chưa sinh được bản inline: {exc}", file=sys.stderr)


_ensure_inline_at_import()


@st.cache_data(show_spinner=False)
def _build_inline(stamp: int) -> dict:
    """Sinh lại bản inline. `stamp` chỉ để phá cache khi file nguồn đổi."""
    from tools.build_ui_inline import build

    return build()


def _sources_stamp() -> int:
    """Dấu vân tay theo mtime của các file nguồn — đổi ở ui/ là tự build lại."""
    files = [ROOT / "ui" / "index.html", ROOT / "ui" / "assets" / "app.css",
             ROOT / "ui" / "assets" / "app.js",
             ROOT / "ui" / "vendor" / "chart.umd.min.js"]
    stamp = 0
    for f in files:
        try:
            stamp = max(stamp, int(f.stat().st_mtime_ns))
        except OSError:
            pass
    return stamp


def _inline_html(api_base: str) -> tuple[str | None, str | None]:
    """Trả (html đã chèn api base, lỗi nếu có). Không bao giờ ném exception."""
    try:
        from tools.build_ui_inline import PLACEHOLDER as ph

        info = _build_inline(_sources_stamp())
    except Exception as exc:                       # build lỗi: thử dùng file có sẵn
        if not INLINE_HTML.is_file():
            return None, f"Không sinh được bản inline và chưa có file sẵn: {exc}"
        info = {"path": INLINE_HTML, "size": INLINE_HTML.stat().st_size}
        ph = PLACEHOLDER

    path = Path(info["path"])
    if not path.is_file():
        return None, f"Không thấy bản inline: {path}"
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"Không đọc được {path.name}: {exc}"

    # Thay token bằng API base thật (đã escape JSON để thành chuỗi JS hợp lệ).
    html = html.replace(ph, json.dumps(api_base)[1:-1])

    # "Mở lại": đổi marker để Streamlit coi là nội dung mới và render lại iframe.
    counter = st.session_state.get("giam_sat_reload", 0)
    html = html.replace("</body>", f"<!-- reload:{counter} -->\n</body>")
    return html, None


# =====================================================================
# Kiểm tra backend
# =====================================================================
def _probe(url: str, timeout: float = 3.0) -> tuple[dict | None, str | None]:
    """GET một URL JSON. Trả (payload, lỗi) — lỗi là chuỗi thân thiện."""
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as res:       # noqa: S310 (URL tin cậy)
            raw = res.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return None, f"HTTP {exc.code} từ {url}"
    except URLError as exc:
        return None, f"không kết nối được {url} ({exc.reason})"
    except TimeoutError:
        return None, f"{url} quá {timeout:g}s không phản hồi"
    except Exception as exc:                             # noqa: BLE001
        return None, f"lỗi khi gọi {url}: {exc}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, f"{url} trả về không phải JSON"
    return (data if isinstance(data, dict) else None), None


@st.cache_data(ttl=10, show_spinner=False)
def _health(api_base: str) -> dict:
    """Kết quả /health, cache 10 s để rerun của Streamlit không gọi liên tục."""
    payload, err = _probe(f"{api_base}/health", timeout=3.0)
    if err:
        return {"state": "down", "error": err, "db": None, "artifacts": None}
    db = bool(payload.get("db"))
    artifacts = bool(payload.get("artifacts"))
    return {
        "state": "live" if (db or artifacts) else "degraded",
        "error": None,
        "db": db,
        "artifacts": artifacts,
        "raw": payload,
    }


def _badge(text: str, color: str) -> str:
    return (f"<span style='display:inline-flex;align-items:center;gap:0.4rem;"
            f"background:{color}14;color:{color};border:1px solid {color}55;"
            f"padding:0.28rem 0.65rem;border-radius:999px;font-size:0.82rem;"
            f"font-weight:600'>{text}</span>")


def _commands_block() -> None:
    st.markdown("Chạy **2 terminal** (Terminal 1 phải đứng yên, đừng tắt):")
    st.code(
        "# Terminal 1\n"
        f"{RUN_UVICORN}\n"
        "# Terminal 2 (chỉ khi chưa chạy)\n"
        f"{RUN_STREAMLIT}",
        language="powershell",
    )


def _backend_block(health: dict) -> str:
    """Vẽ khối trạng thái backend. Trả về: 'live' | 'degraded' | 'down'."""
    state = health["state"]

    if state == "live":
        st.markdown(
            _badge("● Backend đang chạy", GREEN)
            + f"&nbsp; <span style='color:#64748B;font-size:0.85rem'>"
              f"`{API_BASE}` · db: **{'bật' if health['db'] else 'tắt'}** · "
              f"artifacts: **{'có' if health['artifacts'] else 'không'}**</span>",
            unsafe_allow_html=True,
        )
        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            if st.button("🔄 Mở lại", help="Tải lại giao diện giám sát bên dưới.",
                         use_container_width=True):
                st.session_state["giam_sat_reload"] = \
                    int(st.session_state.get("giam_sat_reload", 0)) + 1
                _health.clear()
                st.rerun()
        with c2:
            if st.button("🩺 Kiểm tra lại", use_container_width=True):
                _health.clear()
                st.rerun()
        return state

    if state == "degraded":
        st.markdown(
            _badge("◐ Backend chạy nhưng thiếu dữ liệu", ORANGE)
            + f"&nbsp;<span style='color:#64748B;font-size:0.85rem'>"
              f"`{API_BASE}` trả lời nhưng `db=false` và `artifacts=false`.</span>",
            unsafe_allow_html=True,
        )
        st.warning(
            "Backend có phản hồi nhưng **chưa nạp được PostgreSQL lẫn artifacts**, "
            "nên các endpoint `/api/clients`, `/api/graph/summary` sẽ không có số "
            "liệu thật. Giao diện bên dưới sẽ tự chuyển sang chế độ giả lập "
            "(badge *DEMO MODE* trong khung).\n\n"
            "Khởi động lại backend với dữ liệu:",
            icon="⚠️",
        )
        _commands_block()
        return state

    # state == "down"
    st.markdown(
        _badge("○ Backend chưa chạy", RED)
        + f"&nbsp;<span style='color:#64748B;font-size:0.85rem'>"
          f"{health['error']}</span>",
        unsafe_allow_html=True,
    )
    st.warning(
        "**Chưa kết nối được backend.** Cần chạy 2 lệnh dưới đây, mỗi lệnh một "
        "terminal riêng:",
        icon="⚠️",
    )
    _commands_block()
    if st.button("🩺 Kiểm tra lại", key="retry_down"):
        _health.clear()
        st.rerun()
    return state


# =====================================================================
# Trang
# =====================================================================
def render() -> None:
    header(
        "Giám sát node Federated Learning",
        "9.116 nhà tuyển dụng, mỗi nhà một node, dữ liệu không rời máy",
        kicker="FL Node Console · nhúng từ ui/ (inline CSS/JS)",
    )

    # --- Giải thích ngắn: gập gọn để bảng điều khiển lên cao hơn -------
    with st.expander("Cơ chế Federated Learning: dữ liệu ở lại máy như thế nào?", expanded=False):
        st.markdown(
            "Mỗi **nhà tuyển dụng** là một node giữ dữ liệu của riêng mình. Trong "
            "một vòng huấn luyện, node nhận tham số mô hình từ máy chủ, học trên "
            "dữ liệu **tại chỗ**, rồi chỉ gửi lên **phần tham số đã thay đổi**. "
            "Dữ liệu thô — tin tuyển dụng, hồ sơ ứng viên — không bao giờ rời máy. "
            "Bảng điều khiển bên dưới cho thấy từng node báo cáo gì và mất bao lâu."
        )

    metric_row([
        {"value": "9.116", "label": "Node (nhà tuyển dụng)", "color": ORANGE_DARK},
        {"value": "264.995", "label": "Nút trong đồ thị",
         "help": "Người dùng + tin tuyển dụng + kỹ năng + nghề O*NET", "color": INK},
        {"value": "764.364", "label": "Cạnh user–job", "color": SKY},
    ])

    st.divider()

    # --- Khối kiểm tra backend ----------------------------------------
    health = _health(API_BASE)
    state = _backend_block(health)

    if state != "live":
        finding(
            "Đang ở DEMO MODE — số liệu giả lập",
            "Giao diện vẫn chạy được để xem bố cục, nhưng mọi con số (client, "
            "độ trễ, Recall@20) là <b>giả lập cục bộ trong trình duyệt</b>, "
            "không phải kết quả từ backend. Muốn số liệu thật: chạy lệnh ở trên "
            "rồi bấm <b>Kiểm tra lại</b>.",
            "warn",
        )

    st.divider()

    # --- Nhúng giao diện ----------------------------------------------
    st.subheader("Bảng điều khiển node")

    html, err = _inline_html(API_BASE)
    if err or html is None:
        st.error(f"Không nhúng được giao diện: {err}")
        st.info(
            "Chạy lại bộ sinh bản inline rồi tải lại trang:\n\n"
            "```powershell\npython tools/build_ui_inline.py\n```"
        )
    else:
        with st.container(key="gx-graph-card"):
            components.html(html, height=IFRAME_HEIGHT, scrolling=False)

    with st.expander("WebSocket bị chặn trong iframe thì sao?"):
        st.markdown(
            """
            Khung nhúng là một **iframe** của Streamlit. Trình duyệt cho phép
            WebSocket tới `127.0.0.1:8000`, nhưng một số môi trường chặn:
            proxy công ty, extension bảo mật, hoặc CSP chặn `ws:`.

            Khi đó:

            * badge **WebSocket** ở góc phải hiện `disconnected` (màu đỏ) và
              `app.js` tự thử lại mỗi 3 giây — không có exception, không treo;
            * phần **REST vẫn chạy**: danh sách client, biểu đồ, Start Training
              và trạng thái lượt chạy đều lấy bằng HTTP;
            * dòng chảy sự kiện sẽ trống. Cách xử lý: mở thẳng
              `ui/index.html` bằng trình duyệt (chạy
              `python -m http.server 8080 --directory ui` rồi vào
              `http://127.0.0.1:8080/`) — ở đó WebSocket không bị iframe chặn.
            """
        )
