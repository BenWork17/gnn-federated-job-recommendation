"""t4: (a) thu tim mirror cong khai cua arshkon jobs/job_skills.csv
       (b) do PIPELINE phuong an 1 de xuat: CareerBuilder + ky nang MUC NGHE (O*NET)
           + chia client theo t3 (top-20 bang + Rest), bao cao giu duoc bao nhieu.
"""
import csv
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit/t4_verify")
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
APPS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\apps.tsv")
USERS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\users.tsv")
ZIP = OUT / "db_29_3_text.zip"

res = {}

# ---------- (a) tim job_skills cua arshkon ----------
cands = [
    ("hf_search_jobskills", "https://huggingface.co/api/datasets?search=job_skills&limit=50"),
    ("hf_arshkon2", "https://huggingface.co/api/datasets?search=arshkon&limit=20"),
    ("kaggle_arshkon_files", "https://www.kaggle.com/api/v1/datasets/list/arshkon/linkedin-job-postings"),
]
res["arshkon_skills_probe"] = {}
for name, url in cands:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
            body = r.read(4000).decode("utf-8", "replace")
        res["arshkon_skills_probe"][name] = {"status": 200, "head": body[:800]}
        print("==", name, "OK", body[:200].replace("\n", " "))
    except urllib.error.HTTPError as e:
        res["arshkon_skills_probe"][name] = {"status": e.code}
        print("==", name, e.code)
    except Exception as e:
        res["arshkon_skills_probe"][name] = {"err": str(e)[:120]}
        print("==", name, "ERR", str(e)[:120])

# ---------- (b) pipeline phuong an 1 ----------
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
    alt = z.read([n for n in z.namelist() if n.endswith("Alternate Titles.txt")][0]).decode("utf-8", "replace")
    occ = z.read([n for n in z.namelist() if n.endswith("Occupation Data.txt")][0]).decode("utf-8", "replace")
    skl = z.read([n for n in z.namelist() if n.endswith("/Skills.txt")][0]).decode("utf-8", "replace")

idx = {}
ar = list(csv.reader(alt.splitlines(), delimiter="\t"))
h = ar[0]
ic, it_, ish = h.index("O*NET-SOC Code"), h.index("Alternate Title"), h.index("Short Title")
for r in ar[1:]:
    if len(r) > max(ic, it_):
        for raw in (r[it_], r[ish] if ish < len(r) else ""):
            t = norm(raw)
            if t:
                idx.setdefault(t, r[ic])
oc = list(csv.reader(occ.splitlines(), delimiter="\t"))
h = oc[0]
ic, it_ = h.index("O*NET-SOC Code"), h.index("Title")
for r in oc[1:]:
    if len(r) > max(ic, it_):
        t = norm(r[it_])
        if t:
            idx.setdefault(t, r[ic])
idx_loose = {}
for t, soc in idx.items():
    idx_loose.setdefault(loose(t), soc)

sk = list(csv.reader(skl.splitlines(), delimiter="\t"))
h = sk[0]
ic, ie = h.index("O*NET-SOC Code"), h.index("Element Name")
skills_per = defaultdict(set)
for r in sk[1:]:
    if len(r) > max(ic, ie):
        skills_per[r[ic][:7]].add(r[ie])
print("O*NET index", len(idx), "occs with skills", len(skills_per))

# CB job -> title, and title -> soc
cb_title = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it_ = h.index("JobID"), h.index("Title")
    for row in rd:
        if it_ < len(row):
            cb_title[row[ij]] = norm(row[it_])
soc_of_job = {j: (idx.get(t) or idx_loose.get(loose(t))) for j, t in cb_title.items()}

# user home state (t3 style)
home_state = {}
with open(USERS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ist = h.index("UserID"), h.index("State")
    for row in rd:
        if len(row) > max(iu, ist):
            home_state[row[iu]] = row[ist].strip()

# apps
triples = []
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        triples.append((row[iu], row[ij]))
total_apps = len(triples)

state_apps = Counter(home_state.get(u, "") for u, _ in triples)
top20 = [s for s, _ in state_apps.most_common(20) if s]
def client_of(u):
    s = home_state.get(u, "")
    return s if s in top20 else "REST"
clients = sorted({client_of(u) for u, _ in triples})
print("clients:", len(clients), "top20 states:", len(top20))

# ba bien the: (P0) toan bo CB; (P1) giu job co SOC; (P2) P1 + user>=5 + job>=5
def stats(rows, label):
    users = {u for u, j in rows}
    jobs = {j for u, j in rows}
    with_skill = {j for u, j in rows if j in soc_of_job_set and soc_of_job.get(j)
                  and skills_per.get(soc_of_job[j][:7])}
    per_client = Counter(client_of(u) for u, _ in rows)
    return {
        "label": label,
        "interactions": len(rows),
        "users": len(users),
        "jobs": len(jobs),
        "density_pct": round(100.0 * len(rows) / (len(users) * len(jobs)), 6) if users and jobs else None,
        "jobs_with_occupation": len({j for _, j in rows if soc_of_job.get(j)}),
        "jobs_with_ge1_skill": len(with_skill),
        "pct_jobs_with_skill": round(100.0 * len(with_skill) / len(jobs), 2) if jobs else None,
        "clients": len(per_client),
        "client_min": min(per_client.values()) if per_client else None,
        "client_median": sorted(per_client.values())[len(per_client) // 2] if per_client else None,
        "client_max": max(per_client.values()) if per_client else None,
    }


soc_of_job_set = set(soc_of_job)
p0 = stats(triples, "P0 = toan bo CareerBuilder (moc)")

mapped = [(u, j) for u, j in triples if soc_of_job.get(j)]
p1 = stats(mapped, "P1 = chi giu tin map duoc sang nghe O*NET (co ky nang)")

udeg = Counter(u for u, _ in mapped)
jdeg = Counter(j for _, j in mapped)
keep_u = {u for u, c in udeg.items() if c >= 5}
keep_j = {j for j, c in jdeg.items() if c >= 5}
p2 = stats([(u, j) for u, j in mapped if u in keep_u and j in keep_j],
           "P2 = P1 + user>=5 & job>=5")

res["pipeline_option1"] = {"P0": p0, "P1": p1, "P2": p2,
                           "notes": "client = top-20 home state + REST (cau hinh G1 K=20 cua t3)"}

with open(OUT / "t4_pipeline_option1.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res["pipeline_option1"], indent=1, ensure_ascii=False))
