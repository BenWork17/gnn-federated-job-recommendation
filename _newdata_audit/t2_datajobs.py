# -*- coding: utf-8 -*-
"""t2: kiem chung doc lap lukebarousse/data_jobs - corpus job CO cot skill TUONG MINH + employer."""
import ast
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}


def getj(u, timeout=120):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


CID = "lukebarousse/data_jobs"
out = {"dataset": CID}

info = getj(f"https://datasets-server.huggingface.co/info?dataset={urllib.parse.quote(CID)}")
for cfg, c in (info.get("dataset_info") or {}).items():
    out["config"] = cfg
    out["columns"] = list((c.get("features") or {}).keys())
    out["splits"] = {k: v.get("num_examples") for k, v in (c.get("splits") or {}).items()}
    out["download_size"] = c.get("download_size")
print("columns:", out["columns"])
print("splits:", out["splits"], "| download_size:", out.get("download_size"))

meta = getj(f"https://huggingface.co/api/datasets/{CID}?full=true")
out["license"] = [t for t in (meta.get("tags") or []) if t.startswith("license")]
out["cardData"] = meta.get("cardData")
out["lastModified"] = meta.get("lastModified")
out["downloads"] = meta.get("downloads")
print("license:", out["license"], "| cardData:", json.dumps(out["cardData"])[:200])

# do fill cua job_skills tren nhieu offset
fills = []
for off in [0, 100000, 400000, 700000]:
    try:
        d = getj(f"https://datasets-server.huggingface.co/rows?dataset={urllib.parse.quote(CID)}"
                 f"&config=default&split=train&offset={off}&length=100", 150)
    except Exception as e:
        fills.append({"offset": off, "err": str(e)[:60]})
        continue
    rows = [r["row"] for r in d["rows"]]
    n = len(rows)
    sk = [r.get("job_skills") for r in rows]
    nn = [v for v in sk if v not in (None, "", "nan")]
    ok = 0
    parsed_ok = 0
    for v in nn:
        try:
            p = ast.literal_eval(v) if isinstance(v, str) else v
            if isinstance(p, list) and p:
                ok += 1
            parsed_ok += 1
        except Exception:
            pass
    comp = [r.get("company_name") for r in rows]
    cn = [v for v in comp if v not in (None, "", "nan")]
    fills.append({"offset": off, "n": n,
                  "job_skills_nonnull_pct": round(100 * len(nn) / n, 1),
                  "job_skills_parses_to_nonempty_list_pct": round(100 * ok / n, 1),
                  "skill_example": str(nn[0])[:150] if nn else None,
                  "company_name_fill_pct": round(100 * len(cn) / n, 1),
                  "company_example": str(cn[0])[:60] if cn else None,
                  "title_example": str(rows[0].get("job_title"))[:60],
                  "cols_present": [c for c in ["job_skills", "job_type_skills", "company_name", "job_title",
                                               "job_location", "job_posted_date", "salary_year_avg"] if c in rows[0]]})
    print(f"  offset {off}:", json.dumps(fills[-1], ensure_ascii=False)[:400])

out["fills"] = fills
Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_datajobs_verify.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nwritten")
