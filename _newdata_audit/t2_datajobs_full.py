# -*- coding: utf-8 -*-
"""t2: tai TOAN BO lukebarousse/data_jobs (231 MB parquet) va do tren 100% so dong."""
import json
import sys
import tarfile
import io
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0"}
D = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\_dl")
D.mkdir(parents=True, exist_ok=True)
DEST = D / "data_jobs.csv"
URL = "https://huggingface.co/datasets/lukebarousse/data_jobs/resolve/main/data_jobs.csv"

if not DEST.exists() or DEST.stat().st_size < 200_000_000:
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=900) as r, DEST.open("wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
print("csv bytes:", DEST.stat().st_size)

df = pd.read_csv(DEST, low_memory=False)
print("rows:", len(df), "| cols:", len(df.columns))
print("columns:", list(df.columns))

out = {"hf_id": "lukebarousse/data_jobs", "license": "apache-2.0",
       "csv_bytes": DEST.stat().st_size, "n_rows": int(len(df)),
       "columns": list(df.columns)}

sk = df["job_skills"]
nonnull = sk.notna()
print("\njob_skills non-null:", int(nonnull.sum()), f"({100*nonnull.mean():.2f}%)")

import ast
n_ok = 0
n_list = 0
n_empty = 0
for v in sk[nonnull]:
    n_list += 1
    try:
        p = ast.literal_eval(v) if isinstance(v, str) else v
        if isinstance(p, list):
            if p:
                n_ok += 1
            else:
                n_empty += 1
    except Exception:
        pass
print("job_skills parse to non-empty list:", n_ok, f"({100*n_ok/len(df):.2f}% of all rows)")
print("empty list:", n_empty, "| parse fail:", n_list - n_ok - n_empty)

out["job_skills"] = {
    "nonnull": int(nonnull.sum()), "nonnull_pct": round(100 * nonnull.mean(), 2),
    "parses_to_nonempty_list": n_ok, "pct_of_all_rows": round(100 * n_ok / len(df), 2),
    "parse_fail": n_list - n_ok - n_empty, "empty_list": n_empty,
}
# so ky nang trung binh / job
import collections
cnt = collections.Counter()
lens = []
for v in sk[nonnull].head(200000):
    try:
        p = ast.literal_eval(v) if isinstance(v, str) else v
        if isinstance(p, list):
            lens.append(len(p))
            for s in p:
                cnt[s] += 1
    except Exception:
        pass
out["job_skills"]["mean_skills_per_job_sampled_200k"] = round(sum(lens) / max(1, len(lens)), 2)
out["job_skills"]["distinct_skills_sampled_200k"] = len(cnt)
out["job_skills"]["top_skills_sampled_200k"] = cnt.most_common(12)
print("mean skills/job:", out["job_skills"]["mean_skills_per_job_sampled_200k"],
      "| distinct (200k sample):", len(cnt))
print("top:", cnt.most_common(10))

# job_type_skills
jts = df["job_type_skills"].notna()
out["job_type_skills_nonnull_pct"] = round(100 * jts.mean(), 2)
print("\njob_type_skills non-null pct:", out["job_type_skills_nonnull_pct"])
ex = df.loc[jts, "job_type_skills"].iloc[0]
print("job_type_skills example:", str(ex)[:300])

# employer
cn = df["company_name"].notna() & (df["company_name"].astype(str).str.strip() != "") & (df["company_name"].astype(str) != "nan")
out["company_name"] = {"fill_pct": round(100 * cn.mean(), 2),
                       "distinct": int(df.loc[cn, "company_name"].nunique())}
print("company_name fill:", out["company_name"]["fill_pct"], "% | distinct:", out["company_name"]["distinct"])

# khong co user
out["has_user_column"] = any("user" in c.lower() or "applicant" in c.lower() for c in df.columns)
out["has_interaction_column"] = any(c in df.columns for c in ["applies", "views", "clicks", "rating"])

# ngay
try:
    out["job_posted_date_min"] = str(df["job_posted_date"].min())
    out["job_posted_date_max"] = str(df["job_posted_date"].max())
except Exception:
    pass
print("dates:", out.get("job_posted_date_min"), "->", out.get("job_posted_date_max"))

Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_datajobs_full.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

# xoa file nang theo rang buoc
DEST.unlink(missing_ok=True)
print("\nparquet deleted; results written to t2_datajobs_full.json")
