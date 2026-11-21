"""t2: do cot thuc te cua JobHop (C) va resume-job-description-fit (C)."""
import json
from pathlib import Path

import pandas as pd

OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_data")
rep = {}

p = OUT / "JobHop_v2_train.parquet"
df = pd.read_parquet(p)
rep["jobhop"] = {
    "file_bytes": p.stat().st_size,
    "n_rows": int(len(df)),
    "columns": list(df.columns),
    "dtypes": {c: str(t) for c, t in df.dtypes.items()},
    "n_unique_resume_id": int(df["resume_id"].nunique()) if "resume_id" in df else None,
    "head5": df.head(5).astype(str).to_dict("records"),
    "matched_code_null_frac": float(df["matched_code"].isna().mean()) if "matched_code" in df else None,
    "sample_matched_codes": df["matched_code"].dropna().astype(str).head(10).tolist(),
    "n_unique_matched_code": int(df["matched_code"].nunique()) if "matched_code" in df else None,
    "university_level_counts": df["university_level"].astype(str).value_counts().head(10).to_dict() if "university_level" in df else None,
    "start_date_sample": df["start_date"].astype(str).head(5).tolist() if "start_date" in df else None,
    "n_start_date_nonnull": int(df["start_date"].notna().sum()) if "start_date" in df else None,
}
print(json.dumps(rep["jobhop"], indent=2, ensure_ascii=False)[:3000])

# ---- resume-job-description-fit ----
import urllib.request
UA = {"User-Agent": "Mozilla/5.0"}
base = "https://huggingface.co/datasets/cnamuangtoun/resume-job-description-fit/resolve/main/"
for split in ["train.csv", "test.csv"]:
    dest = OUT / f"rjdf_{split}"
    if not dest.exists():
        req = urllib.request.Request(base + split, headers=UA)
        with urllib.request.urlopen(req, timeout=300) as r:
            dest.write_bytes(r.read())
    d = pd.read_csv(dest)
    rep.setdefault("resume_fit", {})[split] = {
        "bytes": dest.stat().st_size,
        "n_rows": int(len(d)),
        "columns": list(d.columns),
        "label_counts": d["label"].astype(str).value_counts().to_dict() if "label" in d else None,
        "sample": {c: str(d[c].iloc[0])[:200] for c in d.columns},
        "n_unique_resume_text": int(d["resume_text"].nunique()) if "resume_text" in d else None,
        "n_unique_jd": int(d["job_description_text"].nunique()) if "job_description_text" in d else None,
    }
    print(split, rep["resume_fit"][split]["n_rows"], rep["resume_fit"][split]["columns"],
          rep["resume_fit"][split]["label_counts"])

(OUT.parent / "t2_c_stats.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
print("written")
