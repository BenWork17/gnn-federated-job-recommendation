"""
Demo trực quan: GNN + Federated Learning cho gợi ý việc làm.

Chạy:
    python -m streamlit run app/streamlit_app.py --server.headless=true

Trên máy này, ~/.streamlit không ghi được nên phải đặt biến môi trường;
run_all.ps1 và README đã làm việc đó. Nếu chạy tay, dùng:

    $env:MPLCONFIGDIR="$PWD/artifacts/.mplcache"
    python -m streamlit run app/streamlit_app.py --server.headless=true `
        --browser.gatherUsageStats=false
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Cho phép `python -m streamlit run app/streamlit_app.py` từ thư mục gốc
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.paths import missing_artifacts, run_all_command  # noqa: E402
from app.components.theme import inject_theme  # noqa: E402

st.set_page_config(
    page_title="GNN + Federated Learning · CareerBuilder + O*NET (V3)",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# ---------------------------------------------------------------------
# Chặn sớm nếu thiếu artifact, thay vì để từng trang lỗi khó hiểu
# ---------------------------------------------------------------------
missing = missing_artifacts()
if missing:
    st.error(
        "### Chưa có kết quả để hiển thị\n\n"
        "App này đọc số liệu từ `results/v3/notebook_metrics.json` và `artifacts/v3/`, "
        "do pipeline CareerBuilder + O*NET (V3) sinh ra. Hiện còn thiếu:\n\n"
        + "\n".join(f"- {m}" for m in missing)
        + f"\n\n**Cách nhanh nhất** — chạy một lệnh:\n\n```powershell\n"
        f"{run_all_command()}\n```"
    )
    st.stop()

from app.views import (do_thi_viec_lam, fl_sim, giam_sat_node,  # noqa: E402
                       ket_luan, tong_quan)

# ---------------------------------------------------------------------
# Điều hướng (5 mục đồng nhất trên bộ dữ liệu CareerBuilder + O*NET V3)
# ---------------------------------------------------------------------
PAGES = [
    st.Page(tong_quan.render, title="Tổng quan", icon=None,
            url_path="tong-quan", default=True),
    st.Page(do_thi_viec_lam.render, title="Đồ thị việc làm", icon=None,
            url_path="do-thi"),
    st.Page(fl_sim.render, title="Federated Learning simulation", icon=None,
            url_path="lien-bang"),
    st.Page(giam_sat_node.render, title="Giám sát node FL", icon=None,
            url_path="giam-sat-node", default=False),
    st.Page(ket_luan.render, title="Kết luận & hạn chế", icon=None,
            url_path="ket-luan"),
]

nav = st.navigation(PAGES, position="sidebar")

if "sb_mini" not in st.session_state:
    st.session_state["sb_mini"] = False

with st.sidebar:
    _is_mini = bool(st.session_state.get("sb_mini", False))
    with st.container(key="sb-toggle-wrap"):
        _lbl = "»" if _is_mini else "« Thu nhỏ thanh bên"
        _hlp = (
            "Mở rộng thanh taskbar bên trái"
            if _is_mini
            else "Thu nhỏ thanh taskbar bên trái thành thanh icon gọn"
        )
        if st.button(_lbl, key="sb-mini-toggle-btn", help=_hlp, width="stretch"):
            st.session_state["sb_mini"] = not _is_mini
            st.rerun()

    if st.session_state.get("sb_mini", False):
        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"][aria-expanded="true"],
            [data-testid="stSidebar"][aria-expanded="true"] {
                width: 68px !important;
                min-width: 68px !important;
                max-width: 68px !important;
                flex: 0 0 68px !important;
                transition: width 0.2s ease, min-width 0.2s ease;
            }
            [data-testid="stSidebar"][aria-expanded="true"] > div,
            [data-testid="stSidebarContent"] {
                width: 68px !important;
                min-width: 68px !important;
                max-width: 68px !important;
                overflow-x: hidden !important;
            }
            [data-testid="stSidebarHeader"] {
                padding: 0.35rem 0.25rem !important;
                justify-content: center !important;
            }
            [data-testid="stSidebarNav"]::before {
                display: none !important;
            }
            [data-testid="stSidebarNavItems"] {
                padding: 0 !important;
            }
            [data-testid="stSidebarNavLink"] {
                justify-content: center !important;
                padding: 0.55rem 0 !important;
                margin: 4px 0.35rem !important;
            }
            [data-testid="stSidebarNavItems"] li a::before {
                margin-right: 0 !important;
                width: 20px !important;
                height: 20px !important;
                flex: 0 0 20px !important;
            }
            [data-testid="stSidebarNavLink"] span {
                display: none !important;
            }
            [data-testid="stSidebarUserContent"] {
                padding-left: 0.35rem !important;
                padding-right: 0.35rem !important;
            }
            div[class*="st-key-sb-toggle-wrap"] button {
                padding: 0.3rem 0 !important;
                min-width: 0 !important;
                font-size: 1rem !important;
                justify-content: center !important;
            }
            .sb-footer {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="sb-footer">
          <div class="sb-footer-title">
            <span class="sb-dot"></span>Đồ án cuối kỳ — DSS
          </div>
          <div class="sb-footer-authors">
            Phan Gia Bảo · 102220265<br>
            Nguyễn Văn Chương · 102220267
          </div>
          <div class="sb-footer-badge">
            CareerBuilder + O*NET · 9.116 nodes · 264.995 nút
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

nav.run()
