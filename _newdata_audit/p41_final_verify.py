# -*- coding: utf-8 -*-
"""KIEM CHUNG DOC LAP cac so doc-writer dua ra sau khi sua.
Cau hinh chot: ma GOC [:7] xuyen suot + loc P1 bang Technology Skills.
Kiem: 636.896 / 213.793 / 127.784 / 709 nghề / 28.416 Occupation-Skill / 8.316 skill.
"""
import csv, json, re, sys, unicodedata, zipfile
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
BASE = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData")
ZIP = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t4_verify\db_29_3_text.zip")
JOBS, APPS, UHIST = BASE / "jobs.tsv", BASE / "apps.tsv", BASE / "user_history.tsv"

GENDER = re.compile(r"\((?:m|f|d|w|m/w/d|m/f/d|m/f|x|gn|all genders)\)", re.I)
REMOTE = re.compile(r"\((?:remote|hybrid|onsite|on-site)\)", re.I)
YEAR = re.compile(r"\b(19|20)\d{2}\b")
NONWORD = re.compile(r"[^a-z0-9+#. ]+")
WS = re.compile(r"\s+")

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = GENDER.sub(" ", s); s = REMOTE.sub(" ", s); s = YEAR.sub(" ", s)
    s = s.replace("&", " and "); s = NONWORD.sub(" ", s)
    return WS.sub(" ", s).strip()

def loose(s):
    s = re.split(r"[-/|,]", s)[0]
    toks = s.split()
    if len(toks) > 2:
        toks = toks[:-1]
    return " ".join(toks)

with zipfile.ZipFile(ZIP) as z:
    def read(suf):
        return z.read([x for x in z.namelist() if x.endswith(suf)][0]).decode("latin-1")
    alt, occ, tch = read("Alternate Titles.txt"), read("Occupation Data.txt"), read("Technology Skills.txt")

title2soc = {}
ar = list(csv.reader(alt.splitlines(), delimiter="\t")); h = ar[0]
ic, it_, ish = h.index("O*NET-SOC Code"), h.index("Alternate Title"), h.index("Short Title")
for r in ar[1:]:
    if len(r) > max(ic, it_):
        for raw in (r[it_], r[ish] if ish < len(r) else ""):
            t = norm(raw)
            if t:
                title2soc.setdefault(t, r[ic])
oc = list(csv.reader(occ.splitlines(), delimiter="\t")); h = oc[0]
ic, it_ = h.index("O*NET-SOC Code"), h.index("Title")
for r in oc[1:]:
    t = norm(r[it_])
    if t:
        title2soc.setdefault(t, r[ic])
t2s_loose = {}
for t, s in title2soc.items():
    t2s_loose.setdefault(loose(t), s)

# Technology Skills, MA GOC
tk = list(csv.reader(tch.splitlines(), delimiter="\t")); h = tk[0]
ic, ie = h.index("O*NET-SOC Code"), h.index("Example")
tech = defaultdict(set)
for r in tk[1:]:
    if len(r) > max(ic, ie):
        tech[r[ic][:7]].add(r[ie])
print("Technology: ma goc =", len(tech), "| tong cong cu =", len({e for v in tech.values() for e in v}))

# job -> soc (ma day du) -> goc
job2soc = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t"); h = next(rd)
    ij, it_ = h.index("JobID"), h.index("Title")
    for row in rd:
        if it_ < len(row):
            t = norm(row[it_])
            job2soc[row[ij]] = title2soc.get(t) or t2s_loose.get(loose(t))
print("job2soc:", sum(1 for v in job2soc.values() if v), "/", len(job2soc))

# P1: app tren job co soc VA soc(goc) co tech
p1 = []
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t"); h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        s = job2soc.get(row[ij])
        if s and tech.get(s[:7]):
            p1.append((row[iu], row[ij], s[:7]))
print("P1 edges:", len(p1))

p1_users = {u for u, _, _ in p1}
p1_jobs = {j for _, j, _ in p1}
p1_occs = {o for _, _, o in p1}
occ_skill = sum(len(tech[o]) for o in p1_occs)
skill_nodes = set().union(*[tech[o] for o in p1_occs])

# user -> occ (goc) -> skill
uocc = defaultdict(set)
with open(UHIST, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t"); h = next(rd)
    iu, ijt = h.index("UserID"), h.index("JobTitle")
    for row in rd:
        if len(row) > max(iu, ijt):
            t = norm(row[ijt])
            s = title2soc.get(t) or t2s_loose.get(loose(t))
            if s:
                uocc[row[iu]].add(s[:7])
p1_uocc = {u: uocc[u] for u in p1_users if u in uocc}
p1_uskill = {}
for u, ss in p1_uocc.items():
    st = set()
    for o in ss:
        st |= tech[o]
    if st:
        p1_uskill[u] = st
user_occ_edges = sum(len(v) for v in p1_uocc.values())

res = {
  "P1": {"edges_user_job": len(p1), "nodes_user": len(p1_users),
         "nodes_job": len(p1_jobs), "nodes_occupation": len(p1_occs)},
  "skill_layer": {"nodes_skill_tech": len(skill_nodes),
                  "edges_occupation_skill": occ_skill,
                  "mean_skill_per_occupation": round(occ_skill/len(p1_occs), 2)},
  "user_side": {"user_occupation_edges": user_occ_edges,
                "p1_users_with_skill": len(p1_uskill),
                "pct_p1_users_with_skill": round(100.0*len(p1_uskill)/len(p1_users), 2),
                "user_skill_edges": sum(len(v) for v in p1_uskill.values())},
}
print(json.dumps(res, indent=1, ensure_ascii=False))
print("\n=== DOI CHIEU VOI doc-writer ===")
claim = {"edges_user_job": 636896, "nodes_user": 213793, "nodes_job": 127784,
         "nodes_occupation": 709, "nodes_skill_tech": 8316,
         "edges_occupation_skill": 28416, "user_occupation_edges": 352306,
         "pct_p1_users_with_skill": 79.62}
got = {"edges_user_job": len(p1), "nodes_user": len(p1_users), "nodes_job": len(p1_jobs),
       "nodes_occupation": len(p1_occs), "nodes_skill_tech": len(skill_nodes),
       "edges_occupation_skill": occ_skill, "user_occupation_edges": user_occ_edges,
       "pct_p1_users_with_skill": round(100.0*len(p1_uskill)/len(p1_users), 2)}
for k in claim:
    a, b = got[k], claim[k]
    ok = (abs(a-b) < 0.01) if isinstance(a, float) else (a == b)
    print(f"  {k:28s} toi_do={a:>12}  doc-writer={b:>12}  {'KHOP' if ok else 'LECH'}")
