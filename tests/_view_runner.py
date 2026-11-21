"""Helper cho AppTest: render đúng một trang theo tham số `view`."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / ".mplcache"))
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.paths import missing_artifacts  # noqa: E402

view = os.environ.get("DSH_VIEW", "tong_quan")

missing = missing_artifacts()
if missing:
    st.error("Thiếu artifact: " + "; ".join(missing))
    st.stop()

from app.views import (do_thi_viec_lam, fl_sim, giam_sat_node,  # noqa: E402
                       goi_y, ket_luan, tong_quan)

MODULES = {
    "tong_quan": tong_quan,
    "do_thi_viec_lam": do_thi_viec_lam,
    "fl_sim": fl_sim,
    "goi_y": goi_y,
    "giam_sat_node": giam_sat_node,
    "ket_luan": ket_luan,
}

MODULES[view].render()
