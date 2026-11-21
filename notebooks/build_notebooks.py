"""
Ghép các phần nguồn `_p*.py` thành file nguồn percent-format và notebook .ipynb.

Vì sao làm thế này thay vì viết .ipynb trực tiếp: file .py dễ đọc, dễ so sánh diff,
và không bị hỏng cấu trúc JSON. Sinh notebook bằng nbformat đảm bảo tính hợp lệ.

Chạy: python notebooks/build_notebooks.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).resolve().parent

# Thứ tự ghép: phải khớp thứ tự section 1 → 10 → tổng kết
PARTS = [
    "_p1.py",      # cell 0 (bootstrap), [1], [2], [3]
    "_p2.py",      # [4] kiến trúc + chia client + FL loop
    "_p3.py",      # [5] sweep + hạ tầng đánh giá, [6], [7] baseline + biểu đồ
    "_p3b.py",     # [7f] tách nhóm client
    "_p4.py",      # [8] ablation, [9] WebAPI, [10] UI + latency
    "_p5.py",      # [7h] ghi metrics, bảng tổng kết, hạn chế
]

SRC = HERE / "01_gnn_fl_source.py"
DST = HERE / "01_gnn_fl.ipynb"


def build_source() -> str:
    """Ghép các phần thành một file .py duy nhất (percent format)."""
    chunks = []
    for name in PARTS:
        p = HERE / name
        if not p.exists():
            raise FileNotFoundError(f"thiếu phần nguồn: {p}")
        chunks.append(p.read_text(encoding="utf-8").rstrip() + "\n")
    return "\n".join(chunks)


def to_notebook(text: str) -> nbf.NotebookNode:
    """Tách file .py theo marker `# %%` thành các cell notebook."""
    nb = nbf.v4.new_notebook()
    nb.metadata.update({
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    })
    cells = []
    for block in text.split("# %%"):
        block = block.rstrip()
        if not block.strip():
            continue
        is_markdown = block.lstrip().startswith("[markdown]")
        if is_markdown:
            body = block.lstrip()[len("[markdown]"):].lstrip("\n")
            body = "\n".join(
                line[2:] if line.startswith("# ") else
                ("" if line.strip() == "#" else line)
                for line in body.split("\n"))
            cells.append(nbf.v4.new_markdown_cell(body.strip()))
        else:
            body = block.lstrip("\n")
            cells.append(nbf.v4.new_code_cell(body.rstrip()))
    nb["cells"] = cells
    return nb


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        text = build_source()
    except FileNotFoundError as exc:
        print(exc)
        return 1
    SRC.write_text(text, encoding="utf-8")

    nb = to_notebook(text)
    nbf.write(nb, str(DST))

    n_code = sum(1 for c in nb.cells if c.cell_type == "code")
    n_md = sum(1 for c in nb.cells if c.cell_type == "markdown")
    n_lines = text.count("\n") + 1
    print(f"{SRC.name}: {n_lines} dòng")
    print(f"{DST.name}: {len(nb.cells)} cell ({n_code} code, {n_md} markdown)")

    # kiểm tra JSON hợp lệ
    with open(DST, encoding="utf-8") as f:
        reloaded = json.load(f)
    assert reloaded["nbformat"] == 4
    assert len(reloaded["cells"]) == len(nb.cells)
    print("JSON hợp lệ: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
