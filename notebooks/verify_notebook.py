"""
Kiểm tra tĩnh notebook 01_gnn_fl.ipynb — 6 kiểm tra theo yêu cầu của captain.

Không chạy notebook, chỉ kiểm tra:
  1. JSON hợp lệ + mọi code cell parse được (bỏ magic/shell)
  2. Không còn đường dẫn tuyệt đối local (E:\\, C:\\Users)
  3. Biến dùng trước khi gán (pyflakes nếu có, nếu không thì rà tay có kiểm soát)
  4. Mọi key truy cập trên graph.npz đều tồn tại thật
  5. Hằng số trong assert/in khớp số liệu thật
  6. Cell phụ thuộc test_clean_index.npz có fallback

Chạy: python notebooks/verify_notebook.py
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NB_PATH = HERE / "01_gnn_fl.ipynb"
PY_PATH = HERE / "01_gnn_fl_source.py"

RESULTS = []


def report(name: str, ok: bool, note: str = "") -> None:
    RESULTS.append(dict(name=name, ok=ok, note=note))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {note}" if note else ""))


def load_nb() -> dict:
    with open(NB_PATH, encoding="utf-8") as f:
        return json.load(f)


def cell_src(cell: dict) -> str:
    src = cell["source"]
    return "".join(src) if isinstance(src, list) else src


def strip_magic(src: str) -> str:
    """Bỏ dòng magic (%...) và shell (!...) để compile được."""
    out = []
    for line in src.splitlines():
        s = line.lstrip()
        if s.startswith(("%", "!")):
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


def check1_syntax(nb: dict) -> None:
    """1. Mọi code cell parse được."""
    assert nb["nbformat"] == 4, f"nbformat={nb['nbformat']}"
    n_code = 0
    errors = []
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        n_code += 1
        cleaned = strip_magic(cell_src(cell))
        try:
            compile(cleaned, f"<cell {i}>", "exec")
        except SyntaxError as e:
            errors.append(f"cell {i}: {e.msg} (dòng {e.lineno})")
    total_lines = sum(len(cell_src(c).splitlines()) for c in nb["cells"] if c["cell_type"] == "code")
    report("1. JSON hợp lệ + mọi code cell parse được", not errors,
           f"{n_code} code cell, {total_lines} dòng code"
           + ("; LỖI: " + "; ".join(errors) if errors else ""))


def check2_paths(nb: dict, py_text: str) -> None:
    """2. Không còn đường dẫn tuyệt đối local."""
    pat = re.compile(r"E:\\|E:/2026|C:\\Users|D:\\|/Users/[A-Za-z]")
    bad = []
    for i, cell in enumerate(nb["cells"]):
        src = cell_src(cell)
        for m in pat.finditer(src):
            line = src[:m.start()].count("\n") + 1
            bad.append(f"cell {i} dòng {line}: {m.group(0)}")
    for m in pat.finditer(py_text):
        line = py_text[:m.start()].count("\n") + 1
        bad.append(f"source.py dòng {line}: {m.group(0)}")
    report("2. Không có đường dẫn tuyệt đối local", not bad,
           "sạch" if not bad else "; ".join(bad[:5]))


def check3_undefined(nb: dict, py_text: str) -> None:
    """3. Biến dùng trước khi gán — pyflakes nếu có, nếu không thì rà tay."""
    try:
        from pyflakes.api import check as pf_check  # type: ignore
        from pyflakes.reporter import Reporter  # type: ignore
        import io

        buf = io.StringIO()
        rep = Reporter(buf, buf)
        pf_check(py_text, "01_gnn_fl_source.py", rep)
        text = buf.getvalue()
        undef = [ln for ln in text.splitlines() if "undefined name" in ln]
        report("3. Không có biến dùng trước khi gán (pyflakes)", not undef,
               "sạch" if not undef else "; ".join(undef[:6]))
        return
    except ImportError:
        pass

    # --- fallback: kiểm tra thủ công danh sách biến then chốt ---
    required_before_use = ["ART", "OUT", "FIG", "g", "EDGE_INDEX", "EDGE_TYPE",
                           "TRAIN_MASK", "TEST_MASK", "CLIENT_OF_JOB", "CLIENT_OF_USER",
                           "N_NODES", "N_USERS", "N_JOBS", "device", "SCALE", "CFG"]
    code_cells = [(i, cell_src(c)) for i, c in enumerate(nb["cells"])
                  if c["cell_type"] == "code"]
    problems = []
    # ghép toàn bộ code theo thứ tự để biết biến nào được gán ở đâu
    for var in required_before_use:
        assign_idx = None
        for i, src in code_cells:
            tree = ast.parse(strip_magic(src))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == var:
                            assign_idx = i
                            break
                elif isinstance(node, (ast.AnnAssign,)):
                    if isinstance(node.target, ast.Name) and node.target.id == var:
                        assign_idx = i
            if assign_idx is not None:
                break
        if assign_idx is None:
            problems.append(f"{var} không được gán ở cell code nào")
            continue
        # xem cell nào DÙNG var trước cell gán
        for i, src in code_cells:
            if i >= assign_idx:
                continue
            if re.search(rf"\b{re.escape(var)}\b", src):
                problems.append(f"{var} dùng ở cell {i} nhưng gán ở cell {assign_idx}")
                break
    report("3. Biến then chốt được gán trước khi dùng (rà tay)", not problems,
           f"đã kiểm {len(required_before_use)} biến" + ("; " + "; ".join(problems) if problems else ""))


def check4_npz_keys(nb: dict, py_text: str) -> None:
    """4. Mọi key truy cập trên graph.npz đều tồn tại thật."""
    import numpy as np

    g = np.load(ROOT / "artifacts" / "v3" / "graph.npz", allow_pickle=False)
    real = set(g.files)
    print(f"      key thật trong graph.npz: {len(real)}")

    # tìm mọi truy cập g["..."] / g['...']
    used = set(re.findall(r"""\bg\[\s*["']([A-Za-z0-9_]+)["']\s*\]""", py_text))
    missing = sorted(used - real)
    report("4. Key graph.npz dùng trong notebook đều tồn tại", not missing,
           f"{len(used)} key dùng, thiếu: {missing}" if missing else
           f"{len(used)} key dùng, tất cả tồn tại")

    # kiểm tra tên biến phái sinh (không phải g[...]) có khớp key không
    derived = ["N_NODES", "N_USERS", "N_JOBS", "N_OCC", "N_SKILL", "O_U", "O_J", "O_O",
               "O_S", "EDGE_INDEX", "EDGE_TYPE", "TRAIN_MASK", "TEST_MASK",
               "CLIENT_OF_JOB", "CLIENT_OF_USER", "IS_CATALOG_NODE", "OCC_IDS",
               "SKILL_NAMES", "EDGE_TYPE_NAMES"]
    used_derived = [d for d in derived if re.search(rf"\b{d}\b", py_text)]
    print(f"      biến phái sinh dùng: {len(used_derived)}")


def check5_constants(nb: dict, py_text: str) -> None:
    """5. Hằng số trong assert/in khớp số liệu thật của artifacts."""
    import numpy as np

    g = np.load(ROOT / "artifacts" / "v3" / "graph.npz", allow_pickle=False)
    meta = json.loads((ROOT / "artifacts" / "v3" / "meta.json").read_text(encoding="utf-8"))
    ei = g["edge_index"]
    et = g["edge_type"]
    tr = g["train_mask"]
    te = g["test_mask"]

    truth = {
        "n_nodes": int(g["n_nodes"]), "n_users": int(g["n_users"]),
        "n_jobs": int(g["n_jobs"]), "n_occ": int(g["n_occupations"]),
        "n_skill": int(g["n_skills"]),
        "n_edges": int(et.size),
        "et0": int((et == 0).sum()), "et1": int((et == 1).sum()),
        "et2": int((et == 2).sum()), "et3": int((et == 3).sum()),
        "n_train": int(tr.sum()), "n_test": int(te.sum()),
        "n_train_uj": int((tr & (et == 0)).sum()),
        "n_test_uj": int((te & (et == 0)).sum()),
        "n_clients": len(json.loads((ROOT / "artifacts" / "v3" / "clients.json").read_text(encoding="utf-8"))),
        "offsets": [int(x) for x in g["offsets"]],
        "catalog": int((np.bincount(ei[1][tr & (et == 0)] - int(g["offsets"][1]),
                                    minlength=int(g["n_jobs"])) >= 1).sum()),
        "cold": int((np.bincount(ei[1][tr & (et == 0)] - int(g["offsets"][1]),
                                 minlength=int(g["n_jobs"])) == 0).sum()),
    }
    print(f"      số thật: {truth['n_nodes']} nút | {truth['n_edges']} cạnh | "
          f"train {truth['n_train']} | test {truth['n_test']} | "
          f"et {truth['et0']}/{truth['et1']}/{truth['et2']}/{truth['et3']} | "
          f"client {truth['n_clients']} | catalog {truth['catalog']} | cold {truth['cold']}")

    problems = []
    # các assert phải khớp
    pairs = [
        (r"==\s*764364", truth["n_edges"] == 764364, "764364 cạnh"),
        (r"==\s*264995", truth["n_nodes"] == 264995, "264995 nút"),
        (r"==\s*171807", truth["n_users"] == 171807, "171807 user"),
        (r"==\s*84845", truth["n_jobs"] == 84845, "84845 job"),
        (r"==\s*583", truth["n_occ"] == 583, "583 nghề"),
        (r"==\s*7760", truth["n_skill"] == 7760, "7760 skill"),
        (r"==\s*9116", truth["n_clients"] == 9116, "9116 client"),
        (r"==\s*726407", truth["n_train"] == 726407, "726407 train"),
        (r"==\s*37957", truth["n_test_uj"] == 37957, "37957 test uj"),
        (r"==\s*398936", truth["n_train_uj"] == 398936, "398936 train uj"),
    ]
    for pattern, is_true, label in pairs:
        in_nb = re.search(pattern, py_text) is not None
        if in_nb and not is_true:
            problems.append(f"notebook assert {label} nhưng số thật khác")
    # dict edge_type
    if re.search(r"\{0:\s*436893", py_text):
        if (truth["et0"], truth["et1"], truth["et2"], truth["et3"]) != (436893, 26678, 25866, 274927):
            problems.append("dict edge_type không khớp")
    # offsets
    if re.search(r"\[\s*0,\s*171807,\s*256652,\s*257235\s*\]", py_text):
        if truth["offsets"] != [0, 171807, 256652, 257235]:
            problems.append("offsets không khớp")
    # catalog 82.876 và cold 1.969 (in dạng "82.876" / "1.969")
    if "82.876" in py_text or "82876" in py_text:
        if truth["catalog"] != 82876:
            problems.append(f"catalog thật = {truth['catalog']}, không phải 82.876")
    if "1.969" in py_text or "1969" in py_text:
        if truth["cold"] != 1969:
            problems.append(f"cold-start thật = {truth['cold']}, không phải 1.969")

    report("5. Hằng số trong notebook khớp số liệu thật", not problems,
           "; ".join(problems) if problems else
           f"đã đối chiếu {len(pairs) + 3} nhóm hằng số")


def check6_fallback(nb: dict, py_text: str) -> None:
    """6. Cell phụ thuộc test_clean_index.npz phải có fallback."""
    has_load = "test_clean_index.npz" in py_text
    has_try = bool(re.search(r"if CLEAN_SOURCE is None|try:\s*\n.*test_clean_index", py_text, re.S))
    has_compute = "TỰ TÍNH" in py_text or "tự tính" in py_text
    has_assert_guarded = bool(re.search(
        r'assert N_LEAK == 880 or "tự tính" in CLEAN_SOURCE', py_text))
    # np.load trần (không bọc điều kiện) là lỗi
    naked = re.findall(r"^_cl = np\.load\(CLEAN_PATH", py_text, re.M)
    ok = has_load and has_try and has_compute and has_assert_guarded and not naked
    report("6. Có fallback khi thiếu test_clean_index.npz", ok,
           f"nạp file={has_load}, fallback={has_try}, tự tính={has_compute}, "
           f"assert có điều kiện={has_assert_guarded}, np.load trần={bool(naked)}")


def check_extra_kaggle(nb: dict, py_text: str) -> None:
    """Kiểm tra thêm: Kaggle portability."""
    checks = {
        "dò ART tự động (find_artifacts)": "def find_artifacts()" in py_text,
        "/kaggle/input trong CANDIDATES": "/kaggle/input/dss-gnn-fl-v3" in py_text,
        "/kaggle/working cho OUT": "/kaggle/working" in py_text,
        "device tự chọn": 'device = "cuda" if torch.cuda.is_available() else "cpu"' in py_text,
        "SCALE có 3 mức": all(s in py_text for s in ('"tiny"', '"small"', '"full"')),
        "hướng dẫn upload 5 bước": "HƯỚNG DẪN UPLOAD" in py_text,
        "mount Drive (tuỳ chọn)": "MOUNT_DRIVE" in py_text,
        "không dùng torch_geometric": "import torch_geometric" not in py_text,
        "không dùng multiprocessing/joblib": not re.search(
            r"^\s*(import|from)\s+(multiprocessing|joblib)", py_text, re.M),
        "lưu hình vào FIG": 'os.path.join(FIG,' in py_text,
        "ghi notebook_metrics.json": "notebook_metrics.json" in py_text,
        "bảng tổng kết yêu cầu": "BẢNG TỔNG KẾT" in py_text,
        "đo thời gian từng section": "TIMINGS" in py_text and "def mark(" in py_text,
        "seed cố định 42": "set_seed(42)" in py_text,
        "10 heading [1]..[10]": all(f"# [{i}]" in py_text for i in range(1, 11)),
    }
    failed = [k for k, v in checks.items() if not v]
    report("EXTRA. Yêu cầu Kaggle + kỹ thuật", not failed,
           f"{len(checks)} mục" + ("; THIẾU: " + ", ".join(failed) if failed else ", tất cả đạt"))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not NB_PATH.exists():
        print("Chưa có notebook — chạy build_notebooks.py trước")
        return 1
    nb = load_nb()
    py_text = PY_PATH.read_text(encoding="utf-8") if PY_PATH.exists() else ""

    print("=" * 78)
    print("KIỂM TRA TĨNH — 01_gnn_fl.ipynb")
    print("=" * 78)
    check1_syntax(nb)
    check2_paths(nb, py_text)
    check3_undefined(nb, py_text)
    check4_npz_keys(nb, py_text)
    check5_constants(nb, py_text)
    check6_fallback(nb, py_text)
    check_extra_kaggle(nb, py_text)

    n_fail = sum(1 for r in RESULTS if not r["ok"])
    print("=" * 78)
    print(f"KẾT QUẢ: {len(RESULTS) - n_fail}/{len(RESULTS)} PASS, {n_fail} FAIL")
    print("=" * 78)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
