# -*- coding: utf-8 -*-
"""t2: do cot 'skills' cua job-description-dataset (1.74 GB CSV) bang HTTP Range, khong tai het."""
import csv
import io
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}
URL = "https://huggingface.co/datasets/lof223/job_description/resolve/main/job_descriptions.csv"
TOTAL = 1743166140


def rng(a, b, timeout=180):
    req = urllib.request.Request(URL, headers=dict(UA, Range=f"bytes={a}-{b}"))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Range"), r.read()


st, cr, head = rng(0, 400_000)
print("range status", st, "| Content-Range", cr)
txt = head.decode("utf-8", "replace")
lines = txt.split("\n")
header = next(csv.reader([lines[0]]))
print("n_columns:", len(header))
print("columns:", header)

out = {"url": URL, "total_bytes": TOTAL, "n_columns": len(header), "columns": header, "samples": []}

import random
random.seed(3)
offsets = [0, TOTAL // 5, 2 * TOTAL // 5, 3 * TOTAL // 5, 4 * TOTAL // 5, TOTAL - 3_000_000]
for a in offsets:
    a = max(0, a)
    b = min(TOTAL - 1, a + 4_000_000)
    try:
        st, cr, raw = rng(a, b)
    except Exception as e:
        out["samples"].append({"offset": a, "err": str(e)})
        continue
    t = raw.decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(t)))
    rows = [r for r in rows if len(r) == len(header)]
    if a > 0:
        rows = rows[1:]  # bo dong dau bi cat
    if not rows:
        out["samples"].append({"offset": a, "n": 0})
        continue
    stats = {}
    for i, c in enumerate(header):
        vals = [r[i] for r in rows]
        nn = [v for v in vals if v.strip() not in ("", "nan", "None", "NaN")]
        stats[c] = {"fill_pct": round(100 * len(nn) / len(vals), 1),
                    "example": (nn[0][:180] if nn else None)}
    out["samples"].append({"offset": a, "n_rows_parsed": len(rows), "fill": stats})
    print(f"\noffset={a}: parsed {len(rows)} rows")
    for c in ["Job Title", "skills", "Responsibilities", "Qualifications", "Company", "Country", "Role"]:
        if c in stats:
            print(f"   {c}: {stats[c]['fill_pct']}%  e.g. {str(stats[c]['example'])[:100]}")

open(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_ravindra_fill.json", "w", encoding="utf-8").write(
    json.dumps(out, indent=2, ensure_ascii=False))
print("\nwritten")
