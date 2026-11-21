"""t5: recompute phan bo 21 client tren DUNG co so graph_final (Technology Skills).

Ly do: t4 do 21 client tren P1 co so Skills.txt (641.952 canh);
t5 doi sang co so Technology Skills (636.896 canh) -> phai do lai client
tren cung co so de bao cao khong bi tron hai co so.
"""
import csv
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter
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


with zipfile.ZipFile(ZIP) as z:
    alt = z.read([n for n in z.namelist() if n.endswith("Alternate Titles.txt")][0]).decode("utf-8", "replace")
    occ = z.read([n for n in z.namelist() if n.endswith("Occupation Data.txt")][0]).decode("utf-8", "replace")
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
oc = list(csv.reader(occ.splitlines(), delimiter="\t"))
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

job2soc = {}
with open(BASE / "jobs.tsv", encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it_ = h.index("JobID"), h.index("Title")
    for row in rd:
        if it_ < len(row):
            t = norm(row[it_])
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

users = {u for u, _, _ in edges}
jobs = {j for _, j, _ in edges}
socs = {s for _, _, s in edges}

# 21 client: top-20 bang theo SO TUONG TAC trong do thi + REST
state_cnt = Counter(home.get(u, "") for u, _, _ in edges)
top20 = [s for s, _ in state_cnt.most_common(20) if s]
def cl(u):
    s = home.get(u, "")
    return s if s in top20 else "REST"
cc = Counter(cl(u) for u, _, _ in edges)

# doi chung hash
import hashlib
def hcl(u):
    return int(hashlib.md5(u.encode()).hexdigest(), 16) % 21
hc = Counter(hcl(u) for u, _, _ in edges)

# non-IID: JSD tren job_id cho state vs hash
import math
def jsd(part, keyf, K):
    counts = {}
    for e in part:
        c = keyf(e[0])
        counts.setdefault(c, Counter())[keyf(e[1])] += 1
    dists = []
    for c, cnt in counts.items():
        tot = sum(cnt.values())
        dists.append({k: v / tot for k, v in cnt.items()})
    keys = set()
    for d in dists:
        keys |= set(d)
    m = {k: sum(d.get(k, 0) for d in dists) / len(dists) for k in keys}
    def kl(d):
        return sum(p * math.log2(p / m[k]) for k, p in d.items() if p > 0 and m[k] > 0)
    return round(sum(kl(d) for d in dists) / len(dists), 4)

jsd_state = jsd(edges, lambda u: cl(u), 21)
jsd_hash = jsd(edges, lambda u: hcl(u), 21)

vals = sorted(cc.values())
res = {
    "basis": "graph_final: Technology Skills, 636.896 canh",
    "edges": len(edges), "users": len(users), "jobs": len(jobs), "occupations": len(socs),
    "clients_state_top20_rest": {
        "n_clients": len(cc), "min": vals[0], "median": vals[len(vals) // 2],
        "max": vals[-1], "max_min_ratio": round(vals[-1] / vals[0], 2),
        "top1_share_pct": round(100.0 * vals[-1] / len(edges), 2),
    },
    "clients_hash_mod21": {
        "n_clients": len(hc), "min": min(hc.values()),
        "median": sorted(hc.values())[len(hc) // 2], "max": max(hc.values()),
        "max_min_ratio": round(max(hc.values()) / min(hc.values()), 2),
    },
    "jsd_on_job_id": {"state": jsd_state, "hash_baseline": jsd_hash,
                      "uplift_pct": round(100.0 * (jsd_state - jsd_hash) / jsd_hash, 1)},
}
with open(OUT / "t5_clients_final.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
