"""t5: do lai JSD tren DUNG co so graph_final, dung PHUONG PHAP CUA t3.

Vi sao: t5_clients_final.py tinh JSD kieu "pairwise to mean" (generalized JSD),
con t3 (p28_noniid.py) tinh "moi client so voi PHAN BO TOAN CUC, roi trung binh
co trong so". Hai dai luong KHAC NHAU -> khong duoc so sanh truc tiep.

Ham jsd o day chep NGUYEN VAN tu p28_noniid.py dong 55-65 de bao dam cung thuoc do.

Co so: graph_final (Technology Skills) — 636.896 canh.
Client: top-20 bang + REST (21 client), doi chung hash%21.
Bao cao them: JSD tren nhom nganh tho (de thay no ~IID).
"""
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
BASE = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData")
ZIP = Path(r"_newdata_audit/t4_verify/db_29_3_text.zip")
OUT = Path(r"_newdata_audit\t5_verify")

GENDER = re.compile(r"\((?:m|f|d|w|m/w/d|m/f/d|m/f|x|gn|all genders)\)", re.I)
REMOTE = re.compile(r"\((?:remote|hybrid|onsite|on-site)\)", re.I)
YEAR = re.compile(r"\b(19|20)\d{2}\b")
NONWORD = re.compile(r"[^a-z0-9+#. ]+")
WS = re.compile(r"\s+")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    for rx in (GENDER, REMOTE, YEAR):
        s = rx.sub(" ", s)
    s = NONWORD.sub(" ", s.replace("&", " and "))
    return WS.sub(" ", s).strip()


def loose(s):
    s = re.split(r"[-/|,]", s)[0]
    t = s.split()
    return " ".join(t[:-1] if len(t) > 2 else t)


# ---- O*NET ----
with zipfile.ZipFile(ZIP) as z:
    alt = z.read([n for n in z.namelist() if n.endswith("Alternate Titles.txt")][0]).decode("utf-8", "replace")
    occd = z.read([n for n in z.namelist() if n.endswith("Occupation Data.txt")][0]).decode("utf-8", "replace")
    tch = z.read([n for n in z.namelist() if n.endswith("Technology Skills.txt")][0]).decode("utf-8", "replace")

t2s = {}
ar = list(csv.reader(alt.splitlines(), delimiter="\t"))
h = ar[0]
ic, it_, ish = h.index("O*NET-SOC Code"), h.index("Alternate Title"), h.index("Short Title")
for r in ar[1:]:
    if len(r) > max(ic, it_):
        for raw in (r[it_], r[ish] if ish < len(r) else ""):
            t = norm(raw)
            if t:
                t2s.setdefault(t, r[ic])
oc = list(csv.reader(occd.splitlines(), delimiter="\t"))
h = oc[0]
ic, it_ = h.index("O*NET-SOC Code"), h.index("Title")
for r in oc[1:]:
    if len(r) > max(ic, it_):
        t = norm(r[it_])
        if t:
            t2s.setdefault(t, r[ic])
t2s_l = {}
for t, s in t2s.items():
    t2s_l.setdefault(loose(t), s)

tk = list(csv.reader(tch.splitlines(), delimiter="\t"))
h = tk[0]
ic, ie = h.index("O*NET-SOC Code"), h.index("Example")
tech = {}
for r in tk[1:]:
    if len(r) > max(ic, ie):
        tech.setdefault(r[ic][:7], set()).add(r[ie])

job_title_raw = {}
job2soc = {}
with open(BASE / "jobs.tsv", encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it_ = h.index("JobID"), h.index("Title")
    for row in rd:
        if it_ < len(row):
            raw = row[it_]
            job_title_raw[row[ij]] = raw.strip().lower()
            t = norm(raw)
            job2soc[row[ij]] = t2s.get(t) or t2s_l.get(loose(t))

home = {}
with open(BASE / "users.tsv", encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ist = h.index("UserID"), h.index("State")
    for row in rd:
        if len(row) > max(iu, ist):
            home[row[iu]] = row[ist].strip()

edges = []
with open(BASE / "apps.tsv", encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        soc = job2soc.get(row[ij])
        if soc and tech.get(soc[:7]):
            edges.append((row[iu], row[ij], soc))

# ---- t3 method, chep nguyen van ----
def jsd(p, q):
    keys = set(p) | set(q)
    sp, sq = sum(p.values()), sum(q.values())
    if sp == 0 or sq == 0:
        return 0.0
    d = 0.0
    for k in keys:
        a, b = p.get(k, 0) / sp, q.get(k, 0) / sq
        m = 0.5 * (a + b)
        if a > 0:
            d += 0.5 * a * math.log2(a / m)
        if b > 0:
            d += 0.5 * b * math.log2(b / m)
    return d


def client_dists(client_apps, labeler):
    glob = Counter()
    per = {}
    for cid, lst in client_apps.items():
        cc = Counter(labeler(j) for _, j in lst)
        per[cid] = cc
        glob.update(cc)
    ds, ws = [], []
    for cc in per.values():
        ds.append(jsd(cc, glob))
        ws.append(sum(cc.values()))
    return sum(d * w for d, w in zip(ds, ws)) / sum(ws)


# ---- phan vung ----
state_cnt = Counter(home.get(u, "") for u, _, _ in edges)
top20 = [s for s, _ in state_cnt.most_common(20) if s]
def cl(u):
    s = home.get(u, "")
    return s if s in top20 else "REST"
def hcl(u):
    return int(hashlib.md5(u.encode()).hexdigest()[:8], 16) % 21

by_state = defaultdict(list)
by_hash = defaultdict(list)
for u, j, s in edges:
    by_state[cl(u)].append((u, j))
    by_hash[hcl(u)].append((u, j))

# nhom nganh tho (bucket theo tu khoa title) — de thay ~IID
BUCKETS = [
    ("IT/Software", re.compile(r"software|developer|programmer|engineer|analyst|data|sys|network|web|it\b|computer", re.I)),
    ("Healthcare", re.compile(r"nurse|medical|health|therap|pharm|dental|clinic|patient|care", re.I)),
    ("Office/Admin", re.compile(r"admin|assistant|clerk|secretar|reception|office|coordinator", re.I)),
    ("Sales/Retail", re.compile(r"sales|retail|store|cashier|account manager|account executive", re.I)),
    ("Management", re.compile(r"manager|director|supervisor|president|officer|head", re.I)),
    ("Driving/Logistics", re.compile(r"driver|truck|warehouse|logistic|delivery|forklift", re.I)),
    ("Engineering/Industrial", re.compile(r"mechanic|machin|electric|weld|hvac|maintenance|technician|operator", re.I)),
    ("Finance", re.compile(r"account|financ|audit|tax|bookkeep|payroll|credit", re.I)),
    ("Education", re.compile(r"teacher|instructor|professor|tutor|education", re.I)),
    ("Food/Hospitality", re.compile(r"cook|chef|server|restaurant|food|bartend|host", re.I)),
]
def bucket(j):
    t = job_title_raw.get(j, "")
    for name, rx in BUCKETS:
        if rx.search(t):
            return name
    return "Other"

res = {
    "basis": "graph_final (Technology Skills), 636.896 canh",
    "method": "JSD moi client vs phan bo TOAN CUC, trung binh co trong so (chep tu p28_noniid.py)",
    "n_clients": 21,
    "jsd_by_state": {
        "on_exact_job_id": round(client_dists(by_state, lambda j: j), 4),
        "on_exact_title": round(client_dists(by_state, lambda j: job_title_raw.get(j, "")), 4),
        "on_industry_bucket": round(client_dists(by_state, bucket), 4),
    },
    "jsd_by_hash": {
        "on_exact_job_id": round(client_dists(by_hash, lambda j: j), 4),
        "on_exact_title": round(client_dists(by_hash, lambda j: job_title_raw.get(j, "")), 4),
        "on_industry_bucket": round(client_dists(by_hash, bucket), 4),
    },
}
s_j, h_j = res["jsd_by_state"]["on_exact_job_id"], res["jsd_by_hash"]["on_exact_job_id"]
s_t, h_t = res["jsd_by_state"]["on_exact_title"], res["jsd_by_hash"]["on_exact_title"]
res["uplift_pct"] = {
    "on_job_id": round(100.0 * (s_j - h_j) / h_j, 1),
    "on_title": round(100.0 * (s_t - h_t) / h_t, 1),
}
with open(OUT / "t5_jsd_t3method.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
