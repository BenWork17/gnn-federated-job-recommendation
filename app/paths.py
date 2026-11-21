"""
Đường dẫn và nạp dữ liệu cho app. Tách riêng để mọi trang dùng chung và
để app chạy được cả khi đứng ở thư mục khác.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ép matplotlib/streamlit dùng thư mục nội bộ dự án: trên máy này
# C:\Users\<user>\.matplotlib và ~/.streamlit không ghi được.
ROOT = Path(__file__).resolve().parent.parent
for sub in (".mplcache", ".streamlit", ".cache"):
    (ROOT / "artifacts" / sub).mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / ".mplcache"))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PATHS = {
    "v3": ROOT / "artifacts" / "v3",
    "v3_metrics": str(ROOT / "results" / "v3" / "notebook_metrics.json"),
    "v3_figures": ROOT / "results" / "v3" / "figures",
    # Giữ lại các key cũ để không làm gãy import/test cũ
    "reco": str(ROOT / "results" / "reco_main.json"),
    "figures": ROOT / "results" / "figures",
    "artifacts": ROOT / "artifacts",
    "medajob": ROOT / "artifacts" / "medajob",
}

REQUIRED = {
    "v3_graph": ROOT / "artifacts" / "v3" / "graph.npz",
    "v3_meta": ROOT / "artifacts" / "v3" / "meta.json",
    "v3_metrics": ROOT / "results" / "v3" / "notebook_metrics.json",
}


def missing_artifacts() -> list[str]:
    """Liệt kê artifact còn thiếu để hiện hướng dẫn thay vì lỗi khó hiểu."""
    hints = {
        "v3_graph": "python src/prepare_v3.py",
        "v3_meta": "python src/prepare_v3.py",
        "v3_metrics": "jupyter nbconvert --to notebook --execute notebooks/01_gnn_fl.ipynb",
    }
    out = []
    for key, path in REQUIRED.items():
        if not Path(path).exists():
            out.append(f"`{path}` → chạy `{hints[key]}`")
    return out


def run_all_command() -> str:
    return "powershell -ExecutionPolicy Bypass -File run_all.ps1"
