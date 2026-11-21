"""t4: DO TINH HOP LE NGU NGHIA cua join theo title — day la phan QUYET DINH.

Van de: data_jobs la bo DATA-ROLE (98,61% job_title chua tu khoa data). Nhung
title khop CHINH XAC voi CareerBuilder lai gom ca 'administrative assistant'
(35.604 app), 'receptionist' (16.419), 'executive assistant' (9.994)...
=> day la DUONG TINH GIA: title trung chuoi nhung KHONG cung nghe.

Do:
  - Voi tung title CareerBuilder: co tu khoa data khong? co khop data_jobs khong?
    co khop arshkon khong?
  - Bao cao % application theo 4 o: (data-kw, matched) / (data-kw, unmatched) /
    (non-data, matched) / (non-data, unmatched)
  - Ty le "match nhung vo nghia" = matched & non-data / matched

arshkon la LinkedIn MOI NGANH -> match non-data van co the dung nghia.
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
OUT = Path(r"_newdata_audit/t4_verify")
DATA_JOBS = OUT / "data_jobs.csv"
ARSH = OUT / "arshkon_titles.txt"
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
APPS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\apps.tsv")

GENDER = re.compile(r"\((?:m|f|d|w|m/w/d|m/f/d|m/f|x|gn|all genders)\)", re.I)
REMOTE = re.compile(r"\((?:remote|hybrid|onsite|on-site)\)", re.I)
YEAR = re.compile(r"\b(19|20)\d{2}\b")
NONWORD = re.compile(r"[^a-z0-9+#. ]+")
WS = re.compile(r"\s+")
DATAKW = re.compile(r"\bdata\b|analyst|scientist|analytics|machine learning|"
                    r"business intelligence|\bbi\b|statistic|database|etl|warehouse|"
                    r"sql|informatics", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = GENDER.sub(" ", s)
    s = REMOTE.sub(" ", s)
    s = YEAR.sub(" ", s)
    s = s.replace("&", " and ")
    s = NONWORD.sub(" ", s)
    return WS.sub(" ", s).strip()


def loose(s):
    s = re.split(r"[-/|,]", s)[0]
    toks = s.split()
    if len(toks) > 2:
        toks = toks[:-1]
    return " ".join(toks)


dj_titles = set()
with open(DATA_JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f)
    h = next(rd)
    it = h.index("job_title")
    for row in rd:
        if it < len(row):
            t = norm(row[it])
            if t:
                dj_titles.add(t)
dj_loose = {loose(t) for t in dj_titles} - {""}

arsh_titles = {norm(l.strip()) for l in open(ARSH, encoding="utf-8") if l.strip()}
arsh_loose = {loose(t) for t in arsh_titles} - {""}
print("dj titles", len(dj_titles), "dj loose", len(dj_loose),
      "arsh titles", len(arsh_titles), "arsh loose", len(arsh_loose))

# CB titles + app count
cb_title = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it = h.index("JobID"), h.index("Title")
    for row in rd:
        if it < len(row):
            cb_title[row[ij]] = row[it]
apps_by_job = Counter()
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij = h.index("JobID")
    for row in rd:
        apps_by_job[row[ij]] += 1
total_apps = sum(apps_by_job.values())

# phan loai tung job theo 2 truc
cells = Counter()
apps_cells = Counter()
matched_titles_dj = Counter()
matched_titles_ar = Counter()
for jid, raw in cb_title.items():
    a = apps_by_job.get(jid, 0)
    t = norm(raw)
    l = loose(t)
    is_data = bool(DATAKW.search(raw))
    m_dj = (t in dj_titles) or (l in dj_loose)
    m_ar = (t in arsh_titles) or (l in arsh_loose)
    cells[(is_data, m_dj)] += 1
    apps_cells[("dj", is_data, m_dj)] += a
    apps_cells[("ar", is_data, m_ar)] += a
    if m_dj and a:
        matched_titles_dj[t] += a
    if m_ar and a:
        matched_titles_ar[t] += a

# tong app chi tren job CO application
tot = sum(apps_cells[k] for k in apps_cells if k[0] == "dj")


def pct(a, b):
    return round(100.0 * a / b, 3) if b else None


res = {
    "apps_total_on_jobs_with_apps": tot,
    "axis_definition": "'data-kw' = Title khop regex data/analyst/scientist/BI/database/etl/sql/warehouse/statistic",
    "data_jobs_join": {
        "apps_data_matched": apps_cells[("dj", True, True)],
        "pct": pct(apps_cells[("dj", True, True)], tot),
        "apps_data_unmatched": apps_cells[("dj", True, False)],
        "apps_nondata_matched": apps_cells[("dj", False, True)],
        "pct_nondata_matched": pct(apps_cells[("dj", False, True)], tot),
        "apps_nondata_unmatched": apps_cells[("dj", False, False)],
        "total_matched_apps": apps_cells[("dj", True, True)] + apps_cells[("dj", False, True)],
        "pct_total_matched": pct(apps_cells[("dj", True, True)] + apps_cells[("dj", False, True)], tot),
        "share_of_matches_that_are_nondata_pct": pct(
            apps_cells[("dj", False, True)],
            apps_cells[("dj", True, True)] + apps_cells[("dj", False, True)]),
        "top15_matched_titles": matched_titles_dj.most_common(15),
    },
    "arshkon_join": {
        "apps_data_matched": apps_cells[("ar", True, True)],
        "apps_data_unmatched": apps_cells[("ar", True, False)],
        "apps_nondata_matched": apps_cells[("ar", False, True)],
        "apps_nondata_unmatched": apps_cells[("ar", False, False)],
        "total_matched_apps": apps_cells[("ar", True, True)] + apps_cells[("ar", False, True)],
        "pct_total_matched": pct(apps_cells[("ar", True, True)] + apps_cells[("ar", False, True)], tot),
        "top15_matched_titles": matched_titles_ar.most_common(15),
    },
    "interpretation": {
        "data_jobs": "bo data-only. Match NON-data la TRUNG CHUOI, khong phai cung nghe -> phai loai.",
        "arshkon": "LinkedIn moi nganh nen match non-data van co the dung nghe.",
    },
}
with open(OUT / "t4_join_semantic.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
