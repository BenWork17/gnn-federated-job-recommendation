"""t4: DO THAT hau-join — con bao nhieu user/job/tuong tac sau khi loc.

Voi tung phuong an ghep, loc nguong user>=K va job>=K (K=5 va K=10) tren phan da join,
roi bao cao: so user, so job, so tuong tac con lai, mat do.

Phuong an:
  A  data_jobs  (title khop exact HOAC loose HOAC short)  -> co company_name + job_skills
  B  arshkon    (title khop exact HOAC loose)              -> co company_id + job_skills(job_id,skill_abr)
  C  O*NET occupation (title khop alternate title / occupation title)
     -> gan ky nang theo NGHE, khong can job_id -> do phu cao hon

Dau vao: t4_join_rates da phan loai tung distinct title; o day lam lai gon hon
(dung lai ham chuan hoa) nhung chi giu title -> nhan.

Ghi ro: "join duoc" KHONG co nghia la dung nghia (title 2012 vs 2023 khac nhau).
"""
import csv
import io
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
DATA_JOBS = OUT / "data_jobs.csv"
ARSH = OUT / "arshkon_titles.txt"
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


# ---- title sets ----
dj_titles = set()
dj_short = set()
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
dj_loose = {loose(t) for t in dj_titles} - {""}
short_tokens = {sh: {x for x in sh.split() if len(x) >= 4} for sh in dj_short}
short_tokens = {k: v for k, v in short_tokens.items() if v}

arsh_titles = {norm(l.strip()) for l in open(ARSH, encoding="utf-8") if l.strip()}
arsh_loose = {loose(t) for t in arsh_titles} - {""}

# ---- O*NET occupation titles ----
with zipfile.ZipFile(ZIP) as z:
    alt_name = [n for n in z.namelist() if n.endswith("Alternate Titles.txt")][0]
    occ_name = [n for n in z.namelist() if n.endswith("Occupation Data.txt")][0]
    skill_name = [n for n in z.namelist() if n.endswith("/Skills.txt")][0]
    tech_name = [n for n in z.namelist() if n.endswith("Technology Skills.txt")][0]
    alt_raw = z.read(alt_name).decode("utf-8", "replace")
    occ_raw = z.read(occ_name).decode("utf-8", "replace")
    skill_raw = z.read(skill_name).decode("utf-8", "replace")
    tech_raw = z.read(tech_name).decode("utf-8", "replace")

alt_rows = list(csv.reader(alt_raw.splitlines(), delimiter="\t"))
ah = alt_rows[0]
aic, ait = ah.index("O*NET-SOC Code"), ah.index("Alternate Title")
onet_title = {}
for r in alt_rows[1:]:
    if len(r) > max(aic, ait):
        t = norm(r[ait])
        if t:
            onet_title.setdefault(t, r[aic])
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

# so ky nang / nghe tu O*NET (Skills.txt: 35 element/nghe; Technology Skills: nhieu hon)
sk_rows = list(csv.reader(skill_raw.splitlines(), delimiter="\t"))
sh = sk_rows[0]
sic, sie = sh.index("O*NET-SOC Code"), sh.index("Element Name")
skills_per_occ = defaultdict(set)
for r in sk_rows[1:]:
    if len(r) > max(sic, sie):
        skills_per_occ[r[sic][:7]].add(r[sie])
tech_rows = list(csv.reader(tech_raw.splitlines(), delimiter="\t"))
th = tech_rows[0]
tic, tie = th.index("O*NET-SOC Code"), th.index("Example")
tech_per_occ = defaultdict(set)
for r in tech_rows[1:]:
    if len(r) > max(tic, tie):
        tech_per_occ[r[tic][:7]].add(r[tie])
print("O*NET: alt/occ titles", len(onet_title), "occ with skills", len(skills_per_occ),
      "occ with tech", len(tech_per_occ))

# ---- CB titles ----
cb_title = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it = h.index("JobID"), h.index("Title")
    for row in rd:
        if it < len(row):
            cb_title[row[ij]] = norm(row[it])
cb_distinct = set(cb_title.values())
print("CB jobs", len(cb_title), "distinct titles", len(cb_distinct))


def classify(t):
    """-> nhan phuong an (uu tien A > B > C)"""
    if t in dj_titles:
        return "A"
    if loose(t) in dj_loose:
        return "A"
    toks = set(t.split())
    for k, strong in short_tokens.items():
        if strong <= toks:
            return "A"
    if t in arsh_titles or loose(t) in arsh_loose:
        return "B"
    if t in onet_title or loose(t) in onet_loose:
        return "C"
    return "none"


cls = {t: classify(t) for t in cb_distinct}
print("class distribution over DISTINCT titles:", Counter(cls.values()))

# ---- quet apps ----
pairs_by_cls = Counter()
docs = defaultdict(Counter)
users = defaultdict(set)
jobcls = {}
for jid, t in cb_title.items():
    jobcls[jid] = cls.get(t, "none")
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        k = jobcls.get(row[ij], "none")
        pairs_by_cls[k] += 1
        docs[k][row[iu]] += 1
        users[k].add(row[iu])

total_apps = sum(pairs_by_cls.values())

# tinh job degree theo lop 1 lan
jobdeg = defaultdict(Counter)
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        jobdeg[jobcls.get(row[ij], "none")][row[ij]] += 1

res = {"apps_total": total_apps, "per_class_raw": {}, "after_filter": {}}
for k in ["A", "B", "C", "none"]:
    res["per_class_raw"][k] = {
        "apps": pairs_by_cls[k],
        "pct_apps": round(100.0 * pairs_by_cls[k] / total_apps, 3),
        "users": len(users[k]),
        "jobs": len(jobdeg[k]),
    }

for Ku, Kj in [(5, 5), (10, 10)]:
    key = f"user>={Ku}_job>={Kj}"
    res["after_filter"][key] = {}
    for k in ["A", "B", "C"]:
        keep_u = {u for u, c in docs[k].items() if c >= Ku}
        keep_j = {j for j, c in jobdeg[k].items() if c >= Kj}
        apps = 0
        us = set()
        js = set()
        with open(APPS, encoding="utf-8", newline="") as f:
            rd = csv.reader(f, delimiter="\t")
            h = next(rd)
            iu, ij = h.index("UserID"), h.index("JobID")
            for row in rd:
                if row[iu] in keep_u and row[ij] in keep_j:
                    apps += 1
                    us.add(row[iu])
                    js.add(row[ij])
        res["after_filter"][key][k] = {
            "users": len(us), "jobs": len(js), "interactions": apps,
            "density_pct": round(100.0 * apps / (len(us) * len(js)), 6) if us and js else None,
        }

# O*NET: so ky nang gan duoc cho lop C (theo nghe)
c_jobs = [j for j, t in cb_title.items() if cls.get(t) == "C"]
soc_hit = 0
sk_counts = []
tech_counts = []
for j in c_jobs:
    t = cb_title[j]
    soc = onet_title.get(t) or onet_loose.get(loose(t))
    if soc:
        soc_hit += 1
        s7 = soc[:7]
        sk_counts.append(len(skills_per_occ.get(s7, ())))
        tech_counts.append(len(tech_per_occ.get(s7, ())))
res["onet_occupation_level"] = {
    "class_C_jobs": len(c_jobs),
    "jobs_with_onet_soc": soc_hit,
    "pct_jobs_with_soc": round(100.0 * soc_hit / len(c_jobs), 2) if c_jobs else None,
    "jobs_with_ge1_onet_skill": sum(1 for x in sk_counts if x > 0),
    "pct_with_ge1_skill": round(100.0 * sum(1 for x in sk_counts if x > 0) / len(sk_counts), 2) if sk_counts else None,
    "jobs_with_ge1_tech_skill": sum(1 for x in tech_counts if x > 0),
    "pct_with_ge1_tech": round(100.0 * sum(1 for x in tech_counts if x > 0) / len(tech_counts), 2) if tech_counts else None,
    "mean_onet_skills": round(sum(sk_counts) / len(sk_counts), 2) if sk_counts else None,
    "mean_tech": round(sum(tech_counts) / len(tech_counts), 2) if tech_counts else None,
    "occupation_index_sizes": {"titles": len(onet_title), "occupations_with_skills": len(skills_per_occ),
                               "occupations_with_tech": len(tech_per_occ)},
}
with open(OUT / "t4_join_retention.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
