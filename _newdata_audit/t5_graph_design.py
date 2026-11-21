"""t5: do cac so CON THIEU cho thiet ke cuoi.

t4 da do: tuong tac (641.952 P1), job->occupation (129.120), occupation->skill (O*NET).
t5 can do them:
  1. PHIA USER: user_history.JobTitle -> occupation -> skill. Bao nhieu % user co >=1 skill?
     (day la yeu cau (3) "ho so/ky nang phia ung vien" — t4 moi do ho so CAU TRUC, chua do KY NANG)
  2. KICH THUOC DO THI that: so nut User/Job/Occupation/Skill va so canh tung loai.
  3. LOP SKILL nao nen dung: Skills.txt (35 element, tho) hay Technology Skills (8775 phan mem)?
     Do ca hai de so sanh.
  4. So ky nang / job va / user (do sau embedding).
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
NEW = Path(r"_newdata_audit/t5_verify")
NEW.mkdir(parents=True, exist_ok=True)
BASE = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData")
JOBS = BASE / "jobs.tsv"
APPS = BASE / "apps.tsv"
USERS = BASE / "users.tsv"
UHIST = BASE / "user_history.tsv"
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


# ---------- O*NET indexes ----------
with zipfile.ZipFile(ZIP) as z:
    alt = z.read([n for n in z.namelist() if n.endswith("Alternate Titles.txt")][0]).decode("utf-8", "replace")
    occ = z.read([n for n in z.namelist() if n.endswith("Occupation Data.txt")][0]).decode("utf-8", "replace")
    skl = z.read([n for n in z.namelist() if n.endswith("/Skills.txt")][0]).decode("utf-8", "replace")
    tch = z.read([n for n in z.namelist() if n.endswith("Technology Skills.txt")][0]).decode("utf-8", "replace")

title2soc = {}
ar = list(csv.reader(alt.splitlines(), delimiter="\t"))
h = ar[0]
ic, it_, ish = h.index("O*NET-SOC Code"), h.index("Alternate Title"), h.index("Short Title")
for r in ar[1:]:
    if len(r) > max(ic, it_):
        for raw in (r[it_], r[ish] if ish < len(r) else ""):
            t = norm(raw)
            if t:
                title2soc.setdefault(t, r[ic])
oc = list(csv.reader(occ.splitlines(), delimiter="\t"))
h = oc[0]
ic, it_ = h.index("O*NET-SOC Code"), h.index("Title")
soc_title = {}
for r in oc[1:]:
    if len(r) > max(ic, it_):
        soc_title[r[ic]] = r[it_]
        t = norm(r[it_])
        if t:
            title2soc.setdefault(t, r[ic])
title2soc_loose = {}
for t, soc in title2soc.items():
    title2soc_loose.setdefault(loose(t), soc)

sk = list(csv.reader(skl.splitlines(), delimiter="\t"))
h = sk[0]
ic, ie = h.index("O*NET-SOC Code"), h.index("Element Name")
skills_per_soc = defaultdict(set)
for r in sk[1:]:
    if len(r) > max(ic, ie):
        skills_per_soc[r[ic][:7]].add(r[ie])
tk = list(csv.reader(tch.splitlines(), delimiter="\t"))
h = tk[0]
ic, ie = h.index("O*NET-SOC Code"), h.index("Example")
tech_per_soc = defaultdict(set)
for r in tk[1:]:
    if len(r) > max(ic, ie):
        tech_per_soc[r[ic][:7]].add(r[ie])

print("O*NET: title keys", len(title2soc), "| soc with Skills", len(skills_per_soc),
      "| soc with Tech", len(tech_per_soc))

# tap skill phan biet
all_skills = set()
for s in skills_per_soc.values():
    all_skills |= s
all_tech = set()
for s in tech_per_soc.values():
    all_tech |= s
print("distinct Skills elements", len(all_skills), "| distinct technology", len(all_tech))

# ---------- job -> soc ----------
job2soc = {}
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it_ = h.index("JobID"), h.index("Title")
    for row in rd:
        if it_ < len(row):
            t = norm(row[it_])
            job2soc[row[ij]] = title2soc.get(t) or title2soc_loose.get(loose(t))

# ---------- P1 = apps tren job co soc VA soc co skill ----------
p1 = []
with open(APPS, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        soc = job2soc.get(row[ij])
        if soc and skills_per_soc.get(soc[:7]):
            p1.append((row[iu], row[ij], soc))
print("P1 edges:", len(p1))

# ---------- USER side: user_history.JobTitle -> soc -> skills ----------
user_hist_titles = defaultdict(list)
n_hist = 0
with open(UHIST, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ijt = h.index("UserID"), h.index("JobTitle")
    for row in rd:
        n_hist += 1
        if len(row) > max(iu, ijt):
            user_hist_titles[row[iu]].append(row[ijt])
print("user_history rows:", n_hist, "users:", len(user_hist_titles))

hist_mapped = 0
hist_titles_total = 0
user_skills = {}
user_socs = {}
for u, titles in user_hist_titles.items():
    socs = set()
    for raw in titles:
        hist_titles_total += 1
        t = norm(raw)
        soc = title2soc.get(t) or title2soc_loose.get(loose(t))
        if soc:
            hist_mapped += 1
            socs.add(soc)
    if socs:
        user_socs[u] = socs
        s = set()
        for soc in socs:
            s |= skills_per_soc.get(soc[:7], set())
        if s:
            user_skills[u] = s

p1_users = {u for u, _, _ in p1}
users_with_skill_any = len(user_skills)
users_p1_with_skill = len([u for u in p1_users if u in user_skills])
print("user_history titles mapped:", hist_mapped, "/", hist_titles_total)
print("users with soc from history:", len(user_socs), "| with skill:", users_with_skill_any)
print("P1 users:", len(p1_users), "| of which have skill:", users_p1_with_skill)

# ---------- kich thuoc do thi ----------
p1_jobs = {j for _, j, _ in p1}
p1_socs = {s for _, _, s in p1}
job_skill_edges = sum(len(skills_per_soc.get(s[:7], ())) for s in p1_socs)
job_tech_edges = sum(len(tech_per_soc.get(s[:7], ())) for s in p1_socs)
user_skill_edges = sum(len(v) for u, v in user_skills.items() if u in p1_users)
user_soc_edges = sum(len(user_socs[u]) for u in p1_users if u in user_socs)
skills_in_graph = set()
for s in p1_socs:
    skills_in_graph |= skills_per_soc.get(s[:7], set())
tech_in_graph = set()
for s in p1_socs:
    tech_in_graph |= tech_per_soc.get(s[:7], set())

# so skill/job va /user tren P1
sj = [len(skills_per_soc.get(s[:7], ())) for s in p1_socs]
su = [len(user_skills[u]) for u in p1_users if u in user_skills]

res = {
    "base_graph_P1": {
        "edges_user_job": len(p1),
        "nodes_user": len(p1_users),
        "nodes_job": len(p1_jobs),
        "nodes_occupation": len(p1_socs),
        "density_pct": round(100.0 * len(p1) / (len(p1_users) * len(p1_jobs)), 6),
    },
    "skill_layer_option_A_ONET_Skills": {
        "source": "O*NET Skills.txt (35 element: 10 Basic 2.A + 25 Cross-Functional 2.B)",
        "distinct_skill_nodes_in_graph": len(skills_in_graph),
        "distinct_skill_all_onet": len(all_skills),
        "edges_job_skill": job_skill_edges,
        "edges_user_skill": user_skill_edges,
        "skills_per_job_mean": round(sum(sj) / len(sj), 2) if sj else None,
        "skills_per_user_mean": round(sum(su) / len(su), 2) if su else None,
    },
    "skill_layer_option_B_ONET_Technology": {
        "source": "O*NET Technology Skills.txt (8775 phan mem/cong nghe)",
        "distinct_skill_nodes_in_graph": len(tech_in_graph),
        "distinct_skill_all_onet": len(all_tech),
        "edges_job_skill": job_tech_edges,
    },
    "user_side_skills": {
        "user_history_rows": n_hist,
        "user_history_users": len(user_hist_titles),
        "history_titles_total": hist_titles_total,
        "history_titles_mapped_to_occupation": hist_mapped,
        "pct_history_titles_mapped": round(100.0 * hist_mapped / hist_titles_total, 2),
        "users_with_occupation": len(user_socs),
        "users_with_ge1_skill": users_with_skill_any,
        "pct_users_all_with_skill": round(100.0 * users_with_skill_any / len(user_hist_titles), 2),
        "p1_users": len(p1_users),
        "p1_users_with_skill": users_p1_with_skill,
        "pct_p1_users_with_skill": round(100.0 * users_p1_with_skill / len(p1_users), 2),
        "user_occupation_edges": user_soc_edges,
    },
    "note": ("skill phia USER la SUY QUA NGHE (user_history.JobTitle -> occupation -> skill), "
             "KHONG phai ky nang tu khai. Phai khai bao ro."),
}
with open(NEW / "t5_graph_design.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
