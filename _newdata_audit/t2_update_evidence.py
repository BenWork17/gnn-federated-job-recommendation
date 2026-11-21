# -*- coding: utf-8 -*-
"""t2: bo sung data_jobs + jobhop join vao T2_EVIDENCE.json."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
ev = json.loads((A / "T2_EVIDENCE.json").read_text(encoding="utf-8"))
dj = json.loads((A / "t2_datajobs_full.json").read_text(encoding="utf-8"))
jj = json.loads((A / "t2_jobhop_join.json").read_text(encoding="utf-8"))

ev["B_job_corpus"]["lukebarousse_data_jobs"] = {
    "hf_id": "lukebarousse/data_jobs",
    "license": dj["license"],
    "csv_bytes": dj["csv_bytes"],
    "n_rows": dj["n_rows"],
    "n_columns": len(dj["columns"]),
    "columns": dj["columns"],
    "job_skills": dj["job_skills"],
    "job_type_skills_nonnull_pct": dj["job_type_skills_nonnull_pct"],
    "job_type_skills_example": "{'analyst_tools': ['power bi','tableau'], 'programming': ['r','python','sql','nosql']}",
    "company_name": dj["company_name"],
    "job_posted_range": [dj.get("job_posted_date_min"), dj.get("job_posted_date_max")],
    "has_user_column": dj["has_user_column"],
    "has_interaction_column": dj["has_interaction_column"],
    "has_industry_column": False,
    "verification": "downloaded the whole 231 MB CSV and measured 100% of rows, then deleted the file",
    "market": "data/analytics roles, worldwide (Data Analyst / Data Engineer / Data Scientist)",
}

ev["C_profile"]["jobhop_v2"]["join_to_esco_occupation"] = jj

(A / "T2_EVIDENCE.json").write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8")
print("T2_EVIDENCE.json updated:", (A / "T2_EVIDENCE.json").stat().st_size, "bytes")
print(json.dumps(ev["B_job_corpus"]["lukebarousse_data_jobs"]["job_skills"], ensure_ascii=False))
print(json.dumps(jj, ensure_ascii=False)[:300])
