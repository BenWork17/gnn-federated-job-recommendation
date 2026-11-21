"""check_determinism_v3.py — so sánh 2 lần chạy prepare_v3.py.

Dùng:
    python src/prepare_v3.py --out-dir artifacts/v3_rerun
    python tools/check_determinism_v3.py                     # v3 vs v3_rerun
    python tools/check_determinism_v3.py artifacts/v3 artifacts/v3_rerun

Chỉ bỏ qua các trường THAY ĐỔI THEO LẦN CHẠY trong meta.json
(`generated_at`, `runtime_seconds`, `memory_peak_mb`, `memory_peak_gb`, `artifacts`).
Mọi mảng trong graph.npz và 3 file JSON phải trùng khít từng byte.

Exit code 0 = tất định, 1 = có khác biệt.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
META_VOLATILE = ("generated_at", "runtime_seconds", "memory_peak_mb", "memory_peak_gb", "artifacts")
JSON_FILES = ("clients.json", "job_titles.json", "user_titles.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    a = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts" / "v3"
    b = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "artifacts" / "v3_rerun"
    if not (a / "graph.npz").exists() or not (b / "graph.npz").exists():
        print(f"Thiếu graph.npz trong {a} hoặc {b}.\n"
              f"Chạy: python src/prepare_v3.py --out-dir {b}", file=sys.stderr)
        return 2

    ok = True
    with np.load(a / "graph.npz", allow_pickle=False) as za, \
            np.load(b / "graph.npz", allow_pickle=False) as zb:
        if sorted(za.files) != sorted(zb.files):
            print("FAIL  danh sách key khác nhau")
            ok = False
        n_same = 0
        for k in za.files:
            x, y = za[k], zb[k]
            same = (x.tolist() == y.tolist()) if x.dtype.kind in ("U", "S") \
                else (x.shape == y.shape and bool(np.array_equal(x, y)))
            if same:
                n_same += 1
            else:
                print(f"FAIL  graph.npz[{k}] khác")
                ok = False
        print(f"{'OK  ' if ok else 'FAIL'} graph.npz: {n_same}/{len(za.files)} mảng giống hệt")

    for name in JSON_FILES:
        pa, pb = a / name, b / name
        if not pa.exists() or not pb.exists():
            print(f"SKIP  {name} (thiếu ở một bên)")
            continue
        ha, hb = sha(pa), sha(pb)
        same = ha == hb
        ok &= same
        print(f"{'OK  ' if same else 'FAIL'} {name:18s} {ha[:16]} / {hb[:16]}")

    ma = json.loads((a / "meta.json").read_text(encoding="utf-8"))
    mb = json.loads((b / "meta.json").read_text(encoding="utf-8"))
    for d in (ma, mb):
        for k in META_VOLATILE:
            d.pop(k, None)
        # paths.artifacts = chính thư mục ra -> khác khi so 2 out-dir khác nhau
        if isinstance(d.get("paths"), dict):
            d["paths"].pop("artifacts", None)
    meta_same = ma == mb
    ok &= meta_same
    print(f"{'OK  ' if meta_same else 'FAIL'} meta.json (bỏ {', '.join(META_VOLATILE)})")
    if not meta_same:
        for k in sorted(set(ma) | set(mb)):
            if ma.get(k) != mb.get(k):
                print(f"      khác ở '{k}'")

    print("\nKẾT LUẬN:", "TẤT ĐỊNH (giống hệt)" if ok else "CÓ KHÁC BIỆT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
