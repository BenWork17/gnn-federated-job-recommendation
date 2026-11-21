"""t4: KIEM CHUNG GIA DINH 'data_jobs chi co job data/analytics'.

Cach kiem:
 1. Phan bo job_title_short cua data_jobs (10 gia tri) + so dong.
 2. Lay mau title cua data_jobs va kiem % title chua tu khoa data (data|analyst|
    scientist|engineer|analytics|machine learning|bi|business intelligence).
 3. Lay TOP title CareerBuilder khop CHINH XAC voi data_jobs, xep theo so application
    -> neu top toan 'Registered Nurse'/'Truck Driver' thi gia dinh 'data-only' SAI
    (hoac do chuan hoa qua tay). In ra de nguoi doc tu phan doan.
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
OUT = Path(r"_newdata_audit/t4_verify")
DATA_JOBS = OUT / "data_jobs.csv"
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
APPS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\apps.tsv")

GENDER = re.compile(r"\((?:m|f|d|w|m/w/d|m/f/d|m/f|x|gn|all genders)\)", re.I)
REMOTE = re.compile(r"\((?:remote|hybrid|onsite|on-site)\)", re.I)
YEAR = re.compile(r"\b(19|20)\d{2}\b")
NONWORD = re.compile(r"[^a-z0-9+#. ]+")
WS = re.compile(r"\s+")
DATAKW = re.compile(r"data|analyst|scientist|engineer|analytics|machine learning|"
                    r"business intelligence|\bbi\b|statistic|database|etl|warehouse", re.I)


def norm(s):
    s = (s or "").lower()
    s = GENDER.sub(" ", s)
    s = REMOTE.sub(" ", s)
    s = YEAR.sub(" ", s)
    s = s.replace("&", " and ")
    s = NONWORD.sub(" ", s)
    return WS.sub(" ", s).strip()


short_dist = Counter()
dj_titles = set()
raw_titles = []
n = 0
data_kw_hits = 0
with open(DATA_JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f)
    h = next(rd)
    it, ish = h.index("job_title"), h.index("job_title_short")
    for row in rd:
        n += 1
        if ish < len(row):
            short_dist[row[ish]] += 1
        if it < len(row):
            raw = row[it]
            raw_titles.append(raw)
            if DATAKW.search(raw):
                data_kw_hits += 1
            t = norm(raw)
            if t:
                dj_titles.add(t)

print("data_jobs rows:", n)
print("job_title_short distribution:", short_dist.most_common())
print("pct raw titles containing data-role keyword:", round(100.0 * data_kw_hits / n, 2))
print("sample 20 raw titles:", raw_titles[:20])
print("20 random raw titles:", raw_titles[::max(1, n // 20)][:20])

# CB: title -> so app, khop exact
cb_title = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it = h.index("JobID"), h.index("Title")
    for row in rd:
        if it < len(row):
            cb_title[row[ij]] = norm(row[it])

apps_by_title = Counter()
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij = h.index("JobID")
    for row in rd:
        apps_by_title[cb_title.get(row[ij], "")] += 1

matched = [(t, c) for t, c in apps_by_title.items() if t and t in dj_titles]
matched.sort(key=lambda x: -x[1])
matched_apps = sum(c for _, c in matched)
total_apps = sum(apps_by_title.values())

res = {
    "data_jobs": {
        "rows": n,
        "job_title_short_dist": short_dist.most_common(),
        "pct_titles_with_data_keyword": round(100.0 * data_kw_hits / n, 2),
        "sample_titles": raw_titles[:25],
        "sampled_every": max(1, n // 20),
        "sampled_titles": raw_titles[::max(1, n // 20)][:20],
        "distinct_normalized_titles": len(dj_titles),
    },
    "cb_exact_title_match": {
        "distinct_cb_titles_matched": len(matched),
        "apps_covered": matched_apps,
        "pct_apps": round(100.0 * matched_apps / total_apps, 3),
        "top30_by_apps": matched[:30],
        "pct_matched_titles_with_data_keyword": round(
            100.0 * sum(1 for t, _ in matched if DATAKW.search(t)) / len(matched), 2) if matched else None,
    },
    "verdict_note": ("neu top30 toan nghe data -> gia dinh data-only dung; "
                     "neu lan ca nghe khac -> data_jobs khong chi data, phai sua lai ket luan"),
}
with open(OUT / "t4_datajobs_scope_check.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:4000])
