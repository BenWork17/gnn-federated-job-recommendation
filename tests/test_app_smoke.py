"""
Smoke test cho app: chạy từng trang bằng AppTest và đòi 0 exception.

Vì sao cần: Streamlit chỉ báo lỗi khi có người mở đúng trang đó. Test này
chạy hết 5 trang trong CI để không phát hành app có trang trắng.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / ".mplcache"))
sys.path.insert(0, str(ROOT))

import pytest

VIEWS = ["tong_quan", "do_thi_viec_lam", "fl_sim", "goi_y",
         "giam_sat_node", "ket_luan"]


@pytest.mark.parametrize("view", VIEWS)
def test_view_runs_without_exception(view: str) -> None:
    """Mỗi trang phải render được mà không ném exception.

    Truyền tên trang qua biến môi trường: AppTest.run() không nhận tham số
    tuỳ ý, và mỗi trang cần một lần chạy script riêng.
    """
    from streamlit.testing.v1 import AppTest

    os.environ["DSH_VIEW"] = view
    script = ROOT / "tests" / "_view_runner.py"
    at = AppTest.from_file(str(script), default_timeout=180)
    at.run()
    assert not at.exception, f"{view} ném lỗi: {[e.value for e in at.exception]}"


def test_app_entrypoint_loads() -> None:
    """Điểm vào phải nạp được và có ít nhất một tiêu đề."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"),
                           default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
