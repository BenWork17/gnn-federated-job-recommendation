"""t4: do toan bo lukebarousse/data_jobs (231 MB) bang csv.reader + ast.literal_eval.

Do:
  1. so dong that, so job, so cong ty phan biet (dau vao 'job' + 'employer')
  2. fill rate cua job_skills / job_type_skills / company_name
  3. % job co >=1 ky nang trich duoc (list parse duoc, khong rong)
  4. phan bo so job / cong ty (median, p90, max) -> kha thi chia client FL
  5. so ky nang phan biet, so ky nang / job
"""
import ast
import csv
import io
import json
import statistics
import sys
import urllib.request
from collections import Counter
from pathlib import Path

OUT = Path(r"_newdata_audit/t4_verify")
OUT.mkdir(parents=True, exist_ok=True)
CSV_PATH = OUT / "data_jobs.csv"
URL = "https://huggingface.co/datasets/lukebarousse/data_jobs/resolve/main/data_jobs.csv"

if not CSV_PATH.exists() or CSV_PATH.stat().st_size < 200_000_000:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(CSV_PATH, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
print("bytes:", CSV_PATH.stat().st_size)

n = 0
fill = Counter()
company = Counter()
skills_counter = Counter()
per_job_skill_counts = []
bad_parse = 0
empty_list = 0
header = None
dates_min = dates_max = None
with open(CSV_PATH, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f)
    header = next(rd)
    idx = {h: i for i, h in enumerate(header)}
    for row in rd:
        n += 1
        for h, i in idx.items():
            if i < len(row) and row[i].strip():
                fill[h] += 1
        comp = row[idx["company_name"]].strip() if idx["company_name"] < len(row) else ""
        if comp:
            company[comp] += 1
        raw = row[idx["job_skills"]] if idx["job_skills"] < len(row) else ""
        if raw.strip():
            try:
                val = ast.literal_eval(raw)
                if isinstance(val, (list, tuple)) and len(val) > 0:
                    per_job_skill_counts.append(len(val))
                    for s in val:
                        skills_counter[str(s).strip()] += 1
                else:
                    empty_list += 1
            except Exception:
                bad_parse += 1
        d = row[idx["job_posted_date"]] if idx["job_posted_date"] < len(row) else ""
        if d.strip():
            if dates_min is None or d < dates_min:
                dates_min = d
            if dates_max is None or d > dates_max:
                dates_max = d


def pct(a, b):
    return round(100.0 * a / b, 4) if b else None


def q(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


jobs_per_company = list(company.values())
jobs_in_companies_ge = {k: sum(v for v in jobs_per_company if v >= k) for k in (2, 5, 10, 20, 50, 100)}

res = {
    "source": "lukebarousse/data_jobs",
    "url": "https://huggingface.co/datasets/lukebarousse/data_jobs",
    "byte_size": CSV_PATH.stat().st_size,
    "header": header,
    "rows_total": n,
    "jobs_total": n,
    "users_total": 0,
    "interactions_total": 0,
    "fill_rate_pct": {h: round(100.0 * fill[h] / n, 2) for h in header},
    "company_name_distinct": len(company),
    "company_name_fill_pct": round(100.0 * fill["company_name"] / n, 2),
    "jobs_per_company": {
        "n_companies": len(jobs_per_company),
        "min": min(jobs_per_company),
        "median": statistics.median(jobs_per_company),
        "p90": q(jobs_per_company, 90),
        "p99": q(jobs_per_company, 99),
        "max": max(jobs_per_company),
        "top10": company.most_common(10),
        "jobs_in_companies_ge_k": {str(k): v for k, v in jobs_in_companies_ge.items()},
        "pct_jobs_in_companies_ge20": pct(jobs_in_companies_ge[20], n),
        "pct_jobs_in_top20_companies": pct(sum(v for _, v in company.most_common(20)), n),
    },
    "skills": {
        "job_skills_fill_pct": round(100.0 * fill["job_skills"] / n, 2),
        "job_type_skills_fill_pct": round(100.0 * fill["job_type_skills"] / n, 2),
        "parsed_nonempty": len(per_job_skill_counts),
        "pct_jobs_with_ge1_skill": pct(len(per_job_skill_counts), n),
        "pct_jobs_with_ge1_skill_over_filled": pct(len(per_job_skill_counts), fill["job_skills"]),
        "bad_parse": bad_parse,
        "empty_list": empty_list,
        "distinct_skills": len(skills_counter),
        "skills_per_job_mean": round(statistics.fmean(per_job_skill_counts), 3) if per_job_skill_counts else None,
        "skills_per_job_median": statistics.median(per_job_skill_counts) if per_job_skill_counts else None,
        "skills_per_job_max": max(per_job_skill_counts) if per_job_skill_counts else None,
        "top20_skills": skills_counter.most_common(20),
    },
    "date_range": {"min": dates_min, "max": dates_max},
    "density": None,
}
with open(OUT / "t4_lukebarousse.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:4000])
