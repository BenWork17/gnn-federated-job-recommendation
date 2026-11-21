"""t4: do DO PHU cua phuong an 'gan ky nang o MUC NGHE' tren TOAN BO CareerBuilder.

Khac voi t4_join_retention (chi do lop C sau khi A/B da lay truoc), o day do:
  - trong TOAN BO 365.668 job co application, bao nhieu % map duoc sang 1 nghe O*NET
  - bao nhieu % co >=1 ky nang gan duoc (Skills.txt 35 element) va >=1 tech skill
  - va tren 1.603.111 application: bao nhieu % duoc phu
Day la con so quyet dinh cho phuong an du phong "khong ghep job_id".
"""
import csv
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
OUT = Path(r"_newdata_audit/t4_verify")
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
APPS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\apps.tsv")
ZIP = OUT / "db_29_3_text.zip"

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


with zipfile.ZipFile(ZIP) as z:
    alt_raw = z.read([n for n in z.namelist() if n.endswith("Alternate Titles.txt")][0]).decode("utf-8", "replace")
    occ_raw = z.read([n for n in z.namelist() if n.endswith("Occupation Data.txt")][0]).decode("utf-8", "replace")
    skill_raw = z.read([n for n in z.namelist() if n.endswith("/Skills.txt")][0]).decode("utf-8", "replace")
    tech_raw = z.read([n for n in z.namelist() if n.endswith("Technology Skills.txt")][0]).decode("utf-8", "replace")

onet_title = {}
alt_rows = list(csv.reader(alt_raw.splitlines(), delimiter="\t"))
ah = alt_rows[0]
aic, ait, aish = ah.index("O*NET-SOC Code"), ah.index("Alternate Title"), ah.index("Short Title")
for r in alt_rows[1:]:
    if len(r) > max(aic, ait):
        soc = r[aic]
        for raw in (r[ait], r[aish] if aish < len(r) else ""):
            t = norm(raw)
            if t:
                onet_title.setdefault(t, soc)
occ_rows = list(csv.reader(occ_raw.splitlines(), delimiter="\t"))
oh = occ_rows[0]
oic, oit = oh.index("O*NET-SOC Code"), oh.index("Title")
for r in occ_rows[1:]:
    if len(r) > max(oic, oit):
        t = norm(r[oit])
        if t:
            onet_title.setdefault(t, r[oic])
onet_loose = {}
for t, soc in onet_title.items():
    onet_loose.setdefault(loose(t), soc)
print("O*NET title index:", len(onet_title), "loose:", len(onet_loose))

sk = list(csv.reader(skill_raw.splitlines(), delimiter="\t"))
sh = sk[0]
sic, sie = sh.index("O*NET-SOC Code"), sh.index("Element Name")
skills_per = defaultdict(set)
for r in sk[1:]:
    if len(r) > max(sic, sie):
        skills_per[r[sic][:7]].add(r[sie])
tk = list(csv.reader(tech_raw.splitlines(), delimiter="\t"))
th = tk[0]
tic, tie = th.index("O*NET-SOC Code"), th.index("Example")
tech_per = defaultdict(set)
for r in tk[1:]:
    if len(r) > max(tic, tie):
        tech_per[r[tic][:7]].add(r[tie])
print("occupations with skills:", len(skills_per), " with tech:", len(tech_per))

# CB jobs -> title -> soc
cb_title = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it = h.index("JobID"), h.index("Title")
    for row in rd:
        if it < len(row):
            cb_title[row[ij]] = norm(row[it])

soc_of = {}
for j, t in cb_title.items():
    soc_of[j] = onet_title.get(t) or onet_loose.get(loose(t))

jobs_with_apps = set()
app_by_job = Counter()
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij = h.index("JobID")
    for row in rd:
        jobs_with_apps.add(row[ij])
        app_by_job[row[ij]] += 1
total_apps = sum(app_by_job.values())

mapped_jobs = [j for j in jobs_with_apps if soc_of.get(j)]
mapped_apps = sum(app_by_job[j] for j in mapped_jobs)
with_skill = [j for j in mapped_jobs if len(skills_per.get(soc_of[j][:7], ())) > 0]
with_tech = [j for j in mapped_jobs if len(tech_per.get(soc_of[j][:7], ())) > 0]
apps_with_skill = sum(app_by_job[j] for j in with_skill)
apps_with_tech = sum(app_by_job[j] for j in with_tech)

res = {
    "source": "O*NET 29.3 (CC BY 4.0) — Securities: Alternate Titles + Occupation Data + Skills + Technology Skills",
    "cb_jobs_total": len(cb_title),
    "cb_jobs_with_apps": len(jobs_with_apps),
    "cb_apps_total": total_apps,
    "jobs_mapped_to_onet_occupation": len(mapped_jobs),
    "pct_jobs_mapped": round(100.0 * len(mapped_jobs) / len(jobs_with_apps), 3),
    "apps_mapped": mapped_apps,
    "pct_apps_mapped": round(100.0 * mapped_apps / total_apps, 3),
    "jobs_with_onet_skills": len(with_skill),
    "pct_jobs_with_skill_of_mapped": round(100.0 * len(with_skill) / len(mapped_jobs), 3) if mapped_jobs else None,
    "apps_with_onet_skill": apps_with_skill,
    "pct_apps_with_onet_skill": round(100.0 * apps_with_skill / total_apps, 3),
    "jobs_with_onet_tech": len(with_tech),
    "apps_with_onet_tech": apps_with_tech,
    "pct_apps_with_onet_tech": round(100.0 * apps_with_tech / total_apps, 3),
    "note": ("phuong an MUC NGHE: khong can job_id chung, chi can title -> nghe. "
             "Do phu cao hon nhieu so voi ghep job_id, nhung ky nang la cua NGHE chu khong phai cua TIN."),
}
with open(OUT / "t4_onet_occupation_coverage.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
