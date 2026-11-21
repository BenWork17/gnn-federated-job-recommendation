"""
Chạy notebook để kiểm tra không lỗi, không cần nbconvert (máy này không cài được).

Dùng nbclient (có sẵn) thay vì nbconvert. Nếu nbclient không chạy được vì
kernel cần ghi vào thư mục tạm bị chặn, script sẽ chuyển sang chế độ chạy
từng cell bằng exec() trong cùng process — đủ để bắt lỗi cú pháp và lỗi
runtime của code trong notebook.

Chạy: python notebooks/run_notebooks.py
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / ".mplcache"))
os.environ.setdefault("TMP", str(ROOT / "artifacts" / ".tmp"))
os.environ.setdefault("TEMP", str(ROOT / "artifacts" / ".tmp"))
sys.path.insert(0, str(ROOT))


def run_with_nbclient(path: Path) -> bool:
    from nbclient import NotebookClient
    import nbformat

    nb = nbformat.read(str(path), as_version=4)
    client = NotebookClient(nb, timeout=900, kernel_name="python3",
                            resources={"metadata": {"path": str(ROOT)}})
    client.execute()
    nbformat.write(nb, str(path))
    return True


def run_with_exec(path: Path) -> bool:
    """Chạy từng cell code bằng exec; bỏ qua cell magic của Jupyter."""
    import nbformat

    nb = nbformat.read(str(path), as_version=4)
    ns: dict = {"__name__": "__main__"}
    ok = True
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        src = cell.source
        # bỏ các dòng magic (%... , !...)
        lines = [ln for ln in src.split("\n")
                 if not ln.lstrip().startswith(("%", "!"))]
        code = "\n".join(lines)
        try:
            exec(compile(code, f"{path.name}:cell{i}", "exec"), ns)
        except Exception:
            print(f"  LỖI ở cell {i}:")
            traceback.print_exc(limit=3)
            ok = False
            break
    return ok


def main() -> int:
    # notebook dùng display() của IPython; trong chế độ exec cần shim
    try:
        from IPython.display import display  # noqa: F401
    except Exception:
        pass
    if "display" not in dir(__builtins__):
        import builtins
        builtins.display = lambda *a, **k: print(*a) if a else None

    notebooks = sorted((ROOT / "notebooks").glob("0*.ipynb"))
    if not notebooks:
        print("Không tìm thấy notebook nào")
        return 1

    failed = 0
    for path in notebooks:
        print(f"\n=== {path.name} ===")
        try:
            run_with_nbclient(path)
            print("  OK (nbclient)")
        except Exception as exc:
            print(f"  nbclient thất bại ({type(exc).__name__}: {str(exc)[:90]})")
            print("  chuyển sang chế độ exec từng cell…")
            if run_with_exec(path):
                print("  OK (exec)")
            else:
                failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
