"""
Tiện ích dùng chung cho toàn bộ dự án.

Ba việc quan trọng ở đây:
  1. Ép matplotlib dùng thư mục cache NỘI BỘ dự án. Trên máy này
     C:\\Users\\<user>\\.matplotlib không ghi được, nếu không ép sẽ lỗi
     "Matplotlib cannot write to its cache directory".
  2. Cố định seed cho numpy / torch / random để kết quả tái lập được.
  3. Chuẩn hoá cách ghi kết quả: mọi con số trong báo cáo và biểu đồ đều
     đọc từ file JSON do các module này sinh ra, không hard-code.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

# ---------------------------------------------------------------------
# 0. Thư mục gốc và biến môi trường phải set TRƯỚC khi import matplotlib
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
_MPL_DIR = ROOT / "artifacts" / ".mplcache"
_MPL_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_DIR))
# ipykernel/zmq đôi khi cần HOME hợp lệ; trỏ về thư mục dự án
os.environ.setdefault("IPYTHONDIR", str(ROOT / "artifacts" / ".ipython"))


# ---------------------------------------------------------------------
# 1. Cấu hình
# ---------------------------------------------------------------------
def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Đọc config.yaml, chuyển các đường dẫn tương đối về tuyệt đối."""
    import yaml

    cfg_path = Path(path) if path else ROOT / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    for key, value in list(cfg["paths"].items()):
        p = Path(value)
        # medajob_raw là đường dẫn tuyệt đối bên ngoài dự án, giữ nguyên
        cfg["paths"][key] = str(p if p.is_absolute() else ROOT / p)

    for key in ("artifacts", "results", "figures", "tmp"):
        Path(cfg["paths"][key]).mkdir(parents=True, exist_ok=True)
    return cfg


def set_seed(seed: int) -> None:
    """Cố định seed cho cả 4 thư viện ngẫu nhiên đang dùng."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.use_deterministic_algorithms(False)
    except ImportError:  # pragma: no cover
        pass


# ---------------------------------------------------------------------
# 2. Ghi / đọc kết quả
# ---------------------------------------------------------------------
def save_json(path: str | Path, payload: dict[str, Any]) -> Path:
    """Ghi JSON an toàn: numpy scalar, ndarray, Path đều được chuyển kiểu."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_jsonable(payload), f, ensure_ascii=False, indent=2)
    return path


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (np.isnan(v) or np.isinf(v)) else v
    if isinstance(obj, np.ndarray):
        return [_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, float):
        return None if (np.isnan(obj) or np.isinf(obj)) else obj
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


# ---------------------------------------------------------------------
# 3. Khoảng tin cậy bằng bootstrap
# ---------------------------------------------------------------------
def bootstrap_ci(
    values: Sequence[float],
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, float]:
    """CI 95% cho trung bình, resample ở mức ĐƠN VỊ ĐÁNH GIÁ (user).

    Vì sao bootstrap mà không phải t-test: phân phối Recall/NDCG lệch mạnh
    (nhiều user có 0 hit), và n nhỏ. Bootstrap không giả định phân phối chuẩn.
    """
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0}
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    n = arr.size
    for b in range(n_boot):
        means[b] = arr[rng.integers(0, n, n)].mean()
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {"mean": float(arr.mean()), "lo": float(lo), "hi": float(hi), "n": int(n)}


# ---------------------------------------------------------------------
# 4. In ấn
# ---------------------------------------------------------------------
def banner(title: str) -> None:
    line = "=" * 78
    print(f"\n{line}\n{title}\n{line}", flush=True)


def step(msg: str) -> None:
    print(f"  · {msg}", flush=True)


class Timer:
    """with Timer() as t: ...  ->  t.seconds"""

    def __enter__(self) -> "Timer":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.seconds = time.perf_counter() - self._t0

    @property
    def human(self) -> str:
        return f"{self.seconds:.1f}s"


def setup_console() -> None:
    """Console Windows mặc định cp1252 -> ép UTF-8 để in tiếng Việt."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        pass


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def percentile(values: Iterable[float], q: float) -> float:
    arr = np.asarray(list(values), dtype=float)
    return float(np.quantile(arr, q)) if arr.size else float("nan")
