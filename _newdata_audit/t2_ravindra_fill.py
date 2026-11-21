# -*- coding: utf-8 -*-
"""t2: do ty le dien THAT cua cot 'skills' trong job-description-dataset (mirror HF cua ravindra)."""
import json
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}


def getj(u, timeout=90):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


CID = "lof223/job_description"
out = {"dataset": CID, "samples": []}
for off in [0, 1000, 100000, 800000, 1500000]:
    try:
        d = getj(f"https://datasets-server.huggingface.co/rows?dataset={urllib.parse.quote(CID)}"
                 f"&config=default&split=train&offset={off}&length=100", 120)
    except Exception as e:
        out["samples"].append({"offset": off, "err": str(e)})
        continue
    rows = d["rows"]
    cols = ["Job Id", "Job Title", "Role", "skills", "Responsibilities", "Qualifications",
            "Company", "Country", "Work Type", "Experience", "Job Description"]
    stats = {}
    for c in cols:
        if c not in rows[0]["row"]:
            continue
        vals = [r["row"].get(c) for r in rows]
        nn = [v for v in vals if v not in (None, "", "nan", "None")]
        stats[c] = {"fill_pct": round(100 * len(nn) / len(vals), 1),
                    "example": str(nn[0])[:200] if nn else None}
    out["samples"].append({"offset": off, "n": len(rows), "fill": stats})

print(json.dumps(out, indent=2, ensure_ascii=False)[:5000])
open(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_ravindra_fill.json", "w", encoding="utf-8").write(
    json.dumps(out, indent=2, ensure_ascii=False))
