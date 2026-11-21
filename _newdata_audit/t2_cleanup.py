# -*- coding: utf-8 -*-
"""t2: dep file nang - giu header + so dong, xoa du lieu tho theo rang buoc <500MB."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
D = A / "t2_data"
kept = {}

# 1) header + so dong cua cac file O*NET quan trong
B = D / "onet" / "db_29_3_text"
for f in ["Skills.txt", "Occupation Data.txt", "Technology Skills.txt", "Tools Used.txt",
          "Alternate Titles.txt", "Knowledge.txt", "IWA Reference.txt", "DWA Reference.txt"]:
    p = B / f
    if not p.exists():
        continue
    with p.open(encoding="utf-8", errors="replace") as fh:
        header = fh.readline().rstrip("\n")
        n = 1 + sum(1 for _ in fh)
    kept[f] = {"header": header, "n_lines_incl_header": n}

# 2) header CSV da tai
for f in ["rjdf_train.csv", "rjdf_test.csv"]:
    p = D / f
    if p.exists():
        with p.open(encoding="utf-8", errors="replace") as fh:
            header = fh.readline().rstrip("\n")
            n = 1 + sum(1 for _ in fh)
        kept[f] = {"header": header, "n_lines_incl_header": n}

(A / "t2_HEADERS_KEPT.json").write_text(json.dumps(kept, indent=2, ensure_ascii=False, default=str),
                                        encoding="utf-8")

# 3) xoa du lieu tho
import shutil
freed = 0
if D.exists():
    freed = sum(p.stat().st_size for p in D.rglob("*") if p.is_file())
    shutil.rmtree(D, ignore_errors=True)

print(f"freed {freed} bytes ({freed/1e6:.1f} MB); headers -> t2_HEADERS_KEPT.json")
print("kept entries:", list(kept.keys()))
