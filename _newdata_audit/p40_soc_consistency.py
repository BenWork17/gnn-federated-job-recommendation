# -*- coding: utf-8 -*-
"""t5_graph_design.py TRON HAI CAP MA SOC. Do lai ca hai cap nhat quan, so sanh.

Van de (doc-writer phat hien, toi xac nhan bang cach doc code):
  dong 73,83 : title2soc -> ma DAY DU (vd 11-1011.00)
  dong 94,101,134,168 : skills_per_soc[r[ic][:7]] -> ma GOC (vd 11-1011)
  dong 181   : p1_socs = {s for _,_,s in p1} -> ma DAY DU
  dong 182   : skills_per_soc.get(s[:7]) -> tra bang ma GOC, nhung CONG DON qua 832 ma day du
  => hai ma day du khac nhau cung [:7] se bi cong hai lan vao job_skill_edges.

Script nay tinh lai CA HAI cap nhat quan:
  A) ma GOC [:7]  : nut Occupation = so ma goc phan biet
  B) ma DAY DU    : nut Occupation = so ma day du phan biet
Va do he qua len tung con so.
"""
import csv, json, re, sys, unicodedata, zipfile
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
BASE = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData")
ZIP = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t4_verify\db_29_3_text.zip")
OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t5_verify")
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
    def read(suffix):
        n = [x for x in z.namelist() if x.endswith(suffix)][0]
        return z.read(n).decode("latin-1")
    alt, occ, skl, tch = (read("Alternate Titles.txt"), read("Occupation Data.txt"),
                          read("/Skills.txt"), read("Technology Skills.txt"))

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
soc_title = {}
for r in oc[1:]:
    soc_title[r[ic]] = r[it_]
    t = norm(r[it_])
    if t:
        title2soc.setdefault(t, r[ic])
title2soc_loose = {}
for t, soc in title2soc.items():
    title2soc_loose.setdefault(loose(t), soc)

def build(text, valcol):
    rows = list(csv.reader(text.splitlines(), delimiter="\t")); h = rows[0]
    ic, iv = h.index("O*NET-SOC Code"), h.index(valcol)
    full, trunc = defaultdict(set), defaultdict(set)
    for r in rows[1:]:
        if len(r) > max(ic, iv):
            full[r[ic]].add(r[iv])
            trunc[r[ic][:7]].add(r[iv])
    return full, trunc

sk_full, sk_trunc = build(skl, "Element Name")
tk_full, tk_trunc = build(tch, "Example")
print("Skills.txt : ma day du=%d | ma goc=%d | ma day du=/=goc (gop)=%d"
      % (len(sk_full), len(sk_trunc), len(sk_full) - len(sk_trunc)))
print("Tech Skills: ma day du=%d | ma goc=%d | gop=%d"
      % (len(tk_full), len(tk_trunc), len(tk_full) - len(tk_trunc)))

# job -> soc (ma DAY DU)
job2soc = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t"); h = next(rd)
    ij, it_ = h.index("JobID"), h.index("Title")
    for row in rd:
        if it_ < len(row):
            t = norm(row[it_])
            job2soc[row[ij]] = title2soc.get(t) or title2soc_loose.get(loose(t))
print("job2soc:", sum(1 for v in job2soc.values() if v))

# user_history -> soc
user_socs = defaultdict(set)
with open(UHIST, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t"); h = next(rd)
    iu, ijt = h.index("UserID"), h.index("JobTitle")
    for row in rd:
        if len(row) > max(iu, ijt):
            t = norm(row[ijt])
            s = title2soc.get(t) or title2soc_loose.get(loose(t))
            if s:
                user_socs[row[iu]].add(s)

# P1 edges (dung ma GOC de kiem tra co skill, nhu t5)
p1 = []
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t"); h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        soc = job2soc.get(row[ij])
        if soc and sk_trunc.get(soc[:7]):
            p1.append((row[iu], row[ij], soc))
print("P1 edges:", len(p1))

p1_users = {u for u, _, _ in p1}
p1_jobs = {j for _, j, _ in p1}
p1_socs_full = {s for _, _, s in p1}
p1_socs_trunc = {s[:7] for s in p1_socs_full}
print("\nnut Occupation: ma DAY DU=%d | ma GOC=%d | chenh=%d"
      % (len(p1_socs_full), len(p1_socs_trunc), len(p1_socs_full) - len(p1_socs_trunc)))

# --- A) nhat quan ma GOC ---
A_job_skill = sum(len(sk_trunc[s]) for s in p1_socs_trunc)
A_job_tech = sum(len(tk_trunc[s]) for s in p1_socs_trunc)
A_skills_in_graph = set().union(*[sk_trunc[s] for s in p1_socs_trunc]) if p1_socs_trunc else set()
A_tech_in_graph = set().union(*[tk_trunc[s] for s in p1_socs_trunc]) if p1_socs_trunc else set()
A_user_socs = {u: {s[:7] for s in user_socs[u]} for u in p1_users if u in user_socs}
A_user_occ_edges = sum(len(v) for v in A_user_socs.values())
A_user_skill = {}
for u, ss in A_user_socs.items():
    st = set()
    for s in ss:
        st |= sk_trunc[s]
    if st:
        A_user_skill[u] = st
A_user_skill_edges = sum(len(v) for v in A_user_skill.values())

# --- B) nhat quan ma DAY DU (nhu ban goc, nhung CONG DON dung: lap qua tap PHAN BIET) ---
B_job_skill = sum(len(sk_full.get(s, set())) for s in p1_socs_full)
B_job_tech = sum(len(tk_full.get(s, set())) for s in p1_socs_full)
B_skills_in_graph = set().union(*[sk_full.get(s, set()) for s in p1_socs_full]) if p1_socs_full else set()
B_tech_in_graph = set().union(*[tk_full.get(s, set()) for s in p1_socs_full]) if p1_socs_full else set()
B_user_socs = {u: user_socs[u] for u in p1_users if u in user_socs}
B_user_occ_edges = sum(len(v) for v in B_user_socs.values())
B_user_skill = {}
for u, ss in B_user_socs.items():
    st = set()
    for s in ss:
        st |= sk_full.get(s, set())
    if st:
        B_user_skill[u] = st
B_user_skill_edges = sum(len(v) for v in B_user_skill.values())

# C) ban t5 hien tai (TRON): cong don qua 832 ma day du nhung tra bang ma goc
C_job_skill = sum(len(sk_trunc.get(s[:7], ())) for s in p1_socs_full)
C_job_tech = sum(len(tk_trunc.get(s[:7], ())) for s in p1_socs_full)

res = {
  "P1_co_ban": {"edges_user_job": len(p1), "nodes_user": len(p1_users),
                "nodes_job": len(p1_jobs)},
  "A_nhat_quan_MA_GOC": {
      "nodes_occupation": len(p1_socs_trunc),
      "edges_job_skill_35": A_job_skill, "edges_job_tech": A_job_tech,
      "skill_nodes_in_graph": len(A_skills_in_graph),
      "tech_nodes_in_graph": len(A_tech_in_graph),
      "user_occupation_edges": A_user_occ_edges,
      "user_skill_edges": A_user_skill_edges,
      "p1_users_with_skill": len(A_user_skill),
      "pct_p1_users_with_skill": round(100.0*len(A_user_skill)/len(p1_users), 2),
  },
  "B_nhat_quan_MA_DAY_DU": {
      "nodes_occupation": len(p1_socs_full),
      "edges_job_skill_35": B_job_skill, "edges_job_tech": B_job_tech,
      "skill_nodes_in_graph": len(B_skills_in_graph),
      "tech_nodes_in_graph": len(B_tech_in_graph),
      "user_occupation_edges": B_user_occ_edges,
      "user_skill_edges": B_user_skill_edges,
      "p1_users_with_skill": len(B_user_skill),
      "pct_p1_users_with_skill": round(100.0*len(B_user_skill)/len(p1_users), 2),
  },
  "C_ban_t5_tron_cap_KHONG_DUNG": {
      "nodes_occupation": len(p1_socs_full),
      "edges_job_skill_35": C_job_skill, "edges_job_tech": C_job_tech,
      "ghi_chu": "cong don qua 832 ma day du nhung tra bang ma goc -> dem trung",
      "chenh_so_voi_A": C_job_skill - A_job_skill,
  },
}
OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "t5_soc_consistency_fix.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
