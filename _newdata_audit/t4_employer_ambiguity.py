"""t4: do TINH MO HO cua employer khi ghep CareerBuilder <-> arshkon THEO TITLE.

Van de cot (4): ghep theo title la NHIEU-NHIEU. 1 title CareerBuilder ('receptionist')
khop voi NHIEU job_id LinkedIn, moi job_id 1 company_id khac nhau.
=> khong co employer_id xac dinh cho tung tin CareerBuilder.

Do:
 - voi moi title arshkon: so company_id phan biet
 - % application CareerBuilder roi vao title ma title do chi ung voi DUNG 1 company
 - so company phan biet tren toan bo tap khop
 - Voi title mo ho: so company trung binh / title
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
ARSH_POST = OUT / "datastax_postings_slim.csv"

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
    s = re.split(r"[-/|,]", s)[0]
    toks = s.split()
    if len(toks) > 2:
        toks = toks[:-1]
    return " ".join(toks)


# ---- tai postings arshkon (mirror datastax, 516 MB) va giu (title, company_id, company_name, skills_desc)
if not ARSH_POST.exists() or ARSH_POST.stat().st_size < 10_000_000:
    import urllib.request
    url = "https://huggingface.co/datasets/datastax/linkedin_job_listings/resolve/main/postings.csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=1800) as r, open(OUT / "postings_raw.csv", "wb") as f:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            f.write(c)
    # giu lai chi 4 cot
    with open(OUT / "postings_raw.csv", encoding="utf-8", errors="replace", newline="") as f, \
            open(ARSH_POST, "w", encoding="utf-8", newline="") as g:
        rd = csv.reader(f)
        h = next(rd)
        idx = {"title": h.index("title"), "company_id": h.index("company_id"),
               "company_name": h.index("company_name"), "skills_desc": h.index("skills_desc"),
               "job_id": h.index("job_id")}
        w = csv.writer(g)
        w.writerow(list(idx))
        for row in rd:
            w.writerow([row[idx[k]] if idx[k] < len(row) else "" for k in idx])
    (OUT / "postings_raw.csv").unlink()

title2companies = defaultdict(set)
title2names = defaultdict(set)
title2ids = defaultdict(set)
skills_filled = 0
rows = 0
with open(ARSH_POST, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f)
    h = next(rd)
    for row in rd:
        rows += 1
        t = norm(row[h.index("title")])
        if not t:
            continue
        cid = row[h.index("company_id")].strip()
        cname = row[h.index("company_name")].strip()
        if cid:
            title2companies[t].add(cid)
        elif cname:
            title2companies[t].add("name:" + cname)
        if cname:
            title2names[t].add(cname)
        title2ids[t].add(row[h.index("job_id")])
        if row[h.index("skills_desc")].strip():
            skills_filled += 1
print("arshkon rows:", rows, "distinct titles:", len(title2companies),
      "skills_desc filled:", skills_filled)

# ---- CB jobs + apps
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
tot = sum(apps_by_job.values())

# map CB title -> arshkon title (exact or loose)
arsh_titles = set(title2companies) | set(title2names)
arsh_loose = defaultdict(set)
for t in arsh_titles:
    arsh_loose[loose(t)].add(t)

stats = Counter()
app_by_amb = Counter()
users_by_amb = defaultdict(set)
companies_all = set()
n_multi = 0
multi_sizes = []
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        jid, uid = row[ij], row[iu]
        a = 1
        t = norm(cb_title.get(jid, ""))
        if t in title2companies:
            comps = title2companies[t]
            key = "exact"
        elif loose(t) in arsh_loose:
            comps = set()
            for tt in arsh_loose[loose(t)]:
                comps |= title2companies.get(tt, set())
            key = "loose"
        else:
            app_by_amb["unmatched"] += a
            stats["unmatched_jobs"] = stats.get("unmatched_jobs", 0)
            continue
        if len(comps) == 1:
            app_by_amb["unique_company"] += a
            users_by_amb["unique_company"].add(uid)
            stats["jobs_unique"] += 1
        elif len(comps) == 0:
            app_by_amb["no_company"] += a
        else:
            app_by_amb["multi_company"] += a
            users_by_amb["multi_company"].add(uid)
            n_multi += 1
            multi_sizes.append(len(comps))
        companies_all |= comps
        stats[key] += 1

res = {
    "arshkon_rows": rows,
    "arshkon_distinct_titles_with_company": len(title2companies),
    "arshkon_skills_desc_filled": skills_filled,
    "arshkon_skills_desc_fill_pct": round(100.0 * skills_filled / rows, 3),
    "arshkon_distinct_company_ids": len(companies_all),
    "cb_apps_total": tot,
    "employer_attribution": {
        "apps_unique_company": app_by_amb["unique_company"],
        "pct_unique": round(100.0 * app_by_amb["unique_company"] / tot, 3),
        "users_unique": len(users_by_amb["unique_company"]),
        "apps_multi_company": app_by_amb["multi_company"],
        "pct_multi": round(100.0 * app_by_amb["multi_company"] / tot, 3),
        "users_multi": len(users_by_amb["multi_company"]),
        "apps_unmatched": app_by_amb["unmatched"],
        "pct_unmatched": round(100.0 * app_by_amb["unmatched"] / tot, 3),
        "median_companies_per_multi_title": sorted(multi_sizes)[len(multi_sizes) // 2] if multi_sizes else None,
        "max_companies_per_title": max(multi_sizes) if multi_sizes else None,
    },
}
with open(OUT / "t4_employer_ambiguity.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
