"""t4: do KHA NANG GHEP CareerBuilder <-> lukebarousse/data_jobs qua TIEU DE tin.

Khong co khoa ngoai that (da biet tu t1). Do:
  - tap title chuan hoa cua CareerBuilder (jobs.tsv, quet toan bo Title, KHONG doc Description)
  - tap title chuan hoa cua data_jobs (data_jobs.csv, cot job_title)
  - % title CareerBuilder khop CHINH XAC voi >=1 title data_jobs
  - % APPLICATION (trong apps.tsv) roi vao job co title khop
  - % title khop sau khi chuan hoa manh (bo hau to (m/f/d), ky tu dac biet)
Ket qua la CAN DUOI cua kha nang ghep: khop chinh xac chuoi la cach chat nhat.
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
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
APPS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\apps.tsv")
DJ = OUT / "data_jobs.csv"

SUFFIX = re.compile(r"\((m|f|d|w|m/w/d|m/f/d|gn)\)|\b(m|f|d)/{1}(w|m|d)\b", re.I)
NONWORD = re.compile(r"[^a-z0-9+#. ]+")
WS = re.compile(r"\s+")


def norm(t):
    t = unicodedata.normalize("NFKD", t)
    t = t.lower()
    t = SUFFIX.sub(" ", t)
    t = NONWORD.sub(" ", t)
    t = WS.sub(" ", t).strip()
    return t


# 1) titles data_jobs
dj_titles = set()
with open(DJ, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f)
    h = next(rd)
    it = h.index("job_title")
    for row in rd:
        if it < len(row):
            n = norm(row[it])
            if n:
                dj_titles.add(n)
print("data_jobs distinct normalized titles:", len(dj_titles))
dj_words = set()
for t in dj_titles:
    dj_words.update(t.split())

# 2) titles CareerBuilder + so application theo job
cb_title = {}
apps_per_job = Counter()
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it = h.index("JobID"), h.index("Title")
    for row in rd:
        if it < len(row):
            cb_title[row[ij]] = norm(row[it])
print("CareerBuilder jobs:", len(cb_title))
cb_distinct = Counter(cb_title.values())
print("CareerBuilder distinct normalized titles:", len(cb_distinct))

with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij = h.index("JobID")
    for row in rd:
        apps_per_job[row[ij]] += 1
total_apps = sum(apps_per_job.values())
print("apps:", total_apps)

# 3) khop
exact_titles = {t for t in cb_distinct if t in dj_titles}
apps_exact = sum(a for jid, a in apps_per_job.items() if cb_title.get(jid) in dj_titles)
# khop long hon: title CB la substring cua 1 title DJ
dj_sub = " || ".join(dj_titles)
sub_titles = {t for t in cb_distinct if t not in exact_titles and len(t) >= 8 and (" " + t + " ") in (" " + dj_sub + " ")}
apps_sub = sum(a for jid, a in apps_per_job.items()
               if cb_title.get(jid) in sub_titles)
# khop token: >=80% token cua title CB nam trong title DJ? Dung token-set trick
dj_token_sets = {frozenset(t.split()) for t in dj_titles}
tok_titles = set()
for t in cb_distinct:
    if t in exact_titles or t in sub_titles:
        continue
    toks = frozenset(t.split())
    if len(toks) >= 2 and toks in dj_token_sets:
        tok_titles.add(t)
apps_tok = sum(a for jid, a in apps_per_job.items() if cb_title.get(jid) in tok_titles)


def pct(a, b):
    return round(100.0 * a / b, 3) if b else None


res = {
    "careerbuilder": {
        "jobs": len(cb_title),
        "distinct_titles_normalized": len(cb_distinct),
        "apps_total": total_apps,
    },
    "data_jobs": {"distinct_titles_normalized": len(dj_titles)},
    "title_match": {
        "exact_titles": len(exact_titles),
        "exact_pct_of_cb_distinct": pct(len(exact_titles), len(cb_distinct)),
        "exact_apps_covered": apps_exact,
        "exact_pct_of_apps": pct(apps_exact, total_apps),
        "substring_titles": len(sub_titles),
        "substring_pct_of_cb_distinct": pct(len(sub_titles), len(cb_distinct)),
        "substring_pct_of_apps": pct(apps_sub, total_apps),
        "tokenset_titles": len(tok_titles),
        "tokenset_pct_of_apps": pct(apps_tok, total_apps),
        "union_titles": len(exact_titles | sub_titles | tok_titles),
        "union_pct_of_cb_distinct": pct(len(exact_titles | sub_titles | tok_titles), len(cb_distinct)),
        "union_pct_of_apps": pct(apps_exact + apps_sub + apps_tok, total_apps),
    },
    "examples_exact": sorted(exact_titles)[:25],
    "caveat": "khop chuoi tieu de KHONG phai khoa ngoai; la can duoi cua kha nang ghep",
}
with open(OUT / "t4_title_join.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:3000])
