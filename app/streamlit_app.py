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
    page_title="GNN + Federated Learning · Demo",
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
        "App này đọc số liệu từ `results/*.json` và `artifacts/`, do pipeline "
        "sinh ra. Hiện còn thiếu:\n\n"
        + "\n".join(f"- {m}" for m in missing)
        + f"\n\n**Cách nhanh nhất** — chạy một lệnh:\n\n```powershell\n"
        f"{run_all_command()}\n```\n\n"
        "Lần đầu cần dữ liệu MEDAJob trong thư mục Lab03 của môn học."
    )
    st.stop()

from app.views import (do_thi_viec_lam, fl_sim, giam_sat_node,  # noqa: E402
                       goi_y, ket_luan, tong_quan)

# ---------------------------------------------------------------------
# Điều hướng
# ---------------------------------------------------------------------
PAGES = [
    st.Page(tong_quan.render, title="Tổng quan", icon=None,
            url_path="tong-quan", default=True),
    st.Page(do_thi_viec_lam.render, title="Đồ thị việc làm", icon=None,
            url_path="do-thi"),
    st.Page(fl_sim.render, title="Federated Learning simulation", icon=None,
            url_path="lien-bang"),
    st.Page(goi_y.render, title="Gợi ý cho ứng viên", icon=None,
            url_path="goi-y"),
    st.Page(giam_sat_node.render, title="Giám sát node FL", icon=None,
            url_path="giam-sat-node", default=False),
    st.Page(ket_luan.render, title="Kết luận & hạn chế", icon=None,
            url_path="ket-luan"),
]

nav = st.navigation(PAGES, position="sidebar")

with st.sidebar:
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
            MEDAJob · CareerBuilder 9.116 nodes
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

nav.run()
