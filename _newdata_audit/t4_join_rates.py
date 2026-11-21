"""t4: DO THAT ti le JOIN theo 3 muc (chat / long / khong khop) cho 2 phuong an ghep.

Phuong an A: CareerBuilder <-> lukebarousse/data_jobs (job_title, job_title_short)
Phuong an B: CareerBuilder <-> arshkon/linkedin-job-postings (title)

Voi moi phuong an, bao cao tren 3 don vi: so application, so user, so job.

Chuan hoa (muc CHAT):
  - lowercase, NFKD, bo ky tu dac biet, gop khoang trang
  - bo hau to gioi tinh (m/f/d), bo "(Remote)", bo nam o cuoi
Muc LONG (data_jobs): khop theo job_title_short (100% dien, 1 trong N nhom ngan)
   -> do phu theo NHOM: 1 title CareerBuilder khop voi title_short nao? Dung tu dien
   tu khoa cua title_short: lay tap token cua moi title_short, roi kiem title CB co chua
   token dac trung do khong.
Muc LONG2 (arshkon): khop sau khi bo phan sau dau '-' hoac '/' va bo token cuoi.

Chay streaming, khong giu ca bang trong RAM.
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

OUT = Path(r"_newdata_audit/t4_verify")
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
APPS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\apps.tsv")
DATA_JOBS = OUT / "data_jobs.csv"

GENDER = re.compile(r"\((?:m|f|d|w|m/w/d|m/f/d|m/f|x|gn|all genders)\)", re.I)
REMOTE = re.compile(r"\((?:remote|hybrid|onsite|on-site)\)", re.I)
YEAR = re.compile(r"\b(19|20)\d{2}\b")
NONWORD = re.compile(r"[^a-z0-9+#. ]+")
WS = re.compile(r"\s+")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = GENDER.sub(" ", s)
    s = REMOTE.sub(" ", s)
    s = YEAR.sub(" ", s)
    s = s.replace("&", " and ")
    s = NONWORD.sub(" ", s)
    return WS.sub(" ", s).strip()


def loose(s):
    """bo phan sau '-' hoac '/' va bo token cuoi (seniority)"""
    s = re.split(r"[-/|,]", s)[0]
    toks = s.split()
    if len(toks) > 2:
        toks = toks[:-1]
    return " ".join(toks)


# ---------- 1) title space cua data_jobs ----------
dj_titles = set()
dj_short = set()
dj_short_tokens = defaultdict(set)
with open(DATA_JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f)
    h = next(rd)
    it, ish = h.index("job_title"), h.index("job_title_short")
    for row in rd:
        if it < len(row):
            t = norm(row[it])
            if t:
                dj_titles.add(t)
        if ish < len(row):
            sh = norm(row[ish])
            if sh:
                dj_short.add(sh)
print("data_jobs: titles", len(dj_titles), " title_short", len(dj_short))
print("job_title_short values:", sorted(dj_short))

# token dac trung cho tung title_short (dung de khop LONG)
short_tokens = {sh: set(sh.split()) for sh in dj_short}

# ---------- 2) arshkon titles ----------
ARSH = OUT / "arshkon_titles.txt"
arsh_titles = set()
if ARSH.exists():
    with open(ARSH, encoding="utf-8") as f:
        for line in f:
            t = norm(line.rstrip("\n"))
            if t:
                arsh_titles.add(t)
print("arshkon titles loaded:", len(arsh_titles))

# ---------- 3) CareerBuilder: title per job ----------
cb_title = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it = h.index("JobID"), h.index("Title")
    for row in rd:
        if it < len(row):
            cb_title[row[ij]] = norm(row[it])
print("CB jobs:", len(cb_title))

cb_distinct = Counter(cb_title.values())
dj_loose = {loose(t) for t in dj_titles}
dj_loose.discard("")
arsh_loose = {loose(t) for t in arsh_titles}
arsh_loose.discard("")
print("dj loose titles:", len(dj_loose), " arsh loos:", len(arsh_loose))

# phan loai tung distinct title CB (quyet dinh 1 lan -> nhanh)
cls_exact_dj = {}
cls_loose_dj = {}
cls_short_dj = {}
cls_exact_ar = {}
cls_loose_ar = {}
for t in cb_distinct:
    cls_exact_dj[t] = t in dj_titles
    cls_loose_dj[t] = (not cls_exact_dj[t]) and loose(t) in dj_loose
    # short: title CB chua >=1 token dac trung cua 1 title_short (va token do dai >=4)
    hit = None
    toks = set(t.split())
    for sh, st in short_tokens.items():
        strong = {x for x in st if len(x) >= 4}
        if strong and strong <= toks:
            hit = sh
            break
    cls_short_dj[t] = hit
    cls_exact_ar[t] = (not (cls_exact_dj[t] or cls_loose_dj[t] or hit)) and t in arsh_titles
    cls_loose_ar[t] = (not (cls_exact_dj[t] or cls_loose_dj[t] or hit or cls_exact_ar[t])) and loose(t) in arsh_loose

# ---------- 4) quet applications: dem theo 4 muc ----------
apps = {"total": 0}
users_by_class = defaultdict(set)
jobs_by_class = Counter()
for key in ["dj_exact", "dj_loose", "dj_short", "ar_exact", "ar_loose", "none"]:
    apps[key] = 0
    jobs_by_class[key] = 0
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    seen_job = set()
    for row in rd:
        apps["total"] += 1
        jid = row[ij]
        uid = row[iu]
        t = cb_title.get(jid, "")
        if cls_exact_dj.get(t):
            k = "dj_exact"
        elif cls_loose_dj.get(t):
            k = "dj_loose"
        elif cls_short_dj.get(t):
            k = "dj_short"
        elif cls_exact_ar.get(t):
            k = "ar_exact"
        elif cls_loose_ar.get(t):
            k = "ar_loose"
        else:
            k = "none"
        apps[k] += 1
        users_by_class[k].add(uid)
        if jid not in seen_job:
            seen_job.add(jid)
            jobs_by_class[k] += 1

total = apps.pop("total")
tot_users = len(set().union(*users_by_class.values())) if users_by_class else 0
tot_jobs = sum(jobs_by_class.values())


def pct(a, b):
    return round(100.0 * a / b, 3) if b else None


res = {
    "careerbuilder": {"apps": total, "jobs": tot_jobs, "users": tot_users,
                      "distinct_titles": len(cb_distinct)},
    "data_jobs": {"titles": len(dj_titles), "title_short": len(dj_short),
                  "title_short_values": sorted(dj_short), "loose_titles": len(dj_loose)},
    "arshkon": {"titles": len(arsh_titles), "loose_titles": len(arsh_loose)},
    "join_levels": {
        "dj_exact": {"apps": apps["dj_exact"], "pct_apps": pct(apps["dj_exact"], total),
                     "users": len(users_by_class["dj_exact"]),
                     "pct_users": pct(len(users_by_class["dj_exact"]), tot_users),
                     "jobs": jobs_by_class["dj_exact"],
                     "pct_jobs": pct(jobs_by_class["dj_exact"], tot_jobs)},
        "dj_loose": {"apps": apps["dj_loose"], "pct_apps": pct(apps["dj_loose"], total),
                     "users": len(users_by_class["dj_loose"]),
                     "jobs": jobs_by_class["dj_loose"],
                     "pct_jobs": pct(jobs_by_class["dj_loose"], tot_jobs)},
        "dj_short": {"apps": apps["dj_short"], "pct_apps": pct(apps["dj_short"], total),
                     "users": len(users_by_class["dj_short"]),
                     "jobs": jobs_by_class["dj_short"],
                     "pct_jobs": pct(jobs_by_class["dj_short"], tot_jobs)},
        "ar_exact": {"apps": apps["ar_exact"], "pct_apps": pct(apps["ar_exact"], total),
                     "users": len(users_by_class["ar_exact"]),
                     "jobs": jobs_by_class["ar_exact"],
                     "pct_jobs": pct(jobs_by_class["ar_exact"], tot_jobs)},
        "ar_loose": {"apps": apps["ar_loose"], "pct_apps": pct(apps["ar_loose"], total),
                     "users": len(users_by_class["ar_loose"]),
                     "jobs": jobs_by_class["ar_loose"],
                     "pct_jobs": pct(jobs_by_class["ar_loose"], tot_jobs)},
        "none": {"apps": apps["none"], "pct_apps": pct(apps["none"], total),
                 "jobs": jobs_by_class["none"], "pct_jobs": pct(jobs_by_class["none"], tot_jobs)},
    },
    "cumulative": {
        "data_jobs_any": {
            "apps": apps["dj_exact"] + apps["dj_loose"] + apps["dj_short"],
            "pct_apps": pct(apps["dj_exact"] + apps["dj_loose"] + apps["dj_short"], total),
            "users": len(users_by_class["dj_exact"] | users_by_class["dj_loose"] | users_by_class["dj_short"]),
            "jobs": jobs_by_class["dj_exact"] + jobs_by_class["dj_loose"] + jobs_by_class["dj_short"],
        },
        "arshkon_any": {
            "apps": apps["ar_exact"] + apps["ar_loose"],
            "pct_apps": pct(apps["ar_exact"] + apps["ar_loose"], total),
            "users": len(users_by_class["ar_exact"] | users_by_class["ar_loose"]),
            "jobs": jobs_by_class["ar_exact"] + jobs_by_class["ar_loose"],
        },
        "either": {
            "apps": total - apps["none"],
            "pct_apps": pct(total - apps["none"], total),
            "users": tot_users - len(users_by_class["none"]),
            "jobs": tot_jobs - jobs_by_class["none"],
        },
    },
    "notes": {
        "dj_exact": "title CB == title data_jobs sau chuan hoa manh",
        "dj_loose": "bo phan sau -/ va bo token cuoi (seniority) roi so",
        "dj_short": "title CB chua TOAN BO token dac trung (>=4 ky tu) cua 1 gia tri job_title_short",
        "ar_exact": "title CB == title arshkon sau chuan hoa",
        "ar_loose": "title arshkon sau khi bo duoi -/ va token cuoi",
        "none": "khong khop muc nao",
    },
}
with open(OUT / "t4_join_rates.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
