"""t5: sua truy van ESCO + do lai do thi voi lop skill PHAN BIET duoc.

Van de 1: ESCO offset=100 tra 0 -> API chan phan trang (da ghi o t2: chan o 500,
nhung co the chan som hon). Thu lai nhieu cach.

Van de 2 (QUYET DINH): O*NET Skills.txt cho MOI nghe du 35/35 ky nang
=> nut Skill vo dung. Phai dung:
   - O*NET Technology Skills (8775 cong nghe, 1..594/nghe, mean 37,93) -> PHAN BIET
   - hoac ESCO occupationSkillRelations (neu lay duoc)
Do lai do thi P1 voi lop Technology Skills.
"""
import csv
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

UA = {"User-Agent": "Mozilla/5.0"}
BASE = "https://ec.europa.eu/esco/api"
OUT = Path(r"_newdata_audit\t5_verify")
res = {"esco": {}}


def api(path, **params):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


# ---------- ESCO: thu nhieu cach lay ----------
print("=== ESCO probes ===")
for label, kwargs in [
    ("limit40_offset0", dict(type="occupation", limit=40, offset=0, language="en")),
    ("limit100_offset0", dict(type="occupation", limit=100, offset=0, language="en")),
    ("limit20_offset20", dict(type="occupation", limit=20, offset=20, language="en")),
    ("limit20_offset100", dict(type="occupation", limit=20, offset=100, language="en")),
]:
    try:
        d = api("/search", **kwargs)
        n = len((d.get("_embedded") or {}).get("results") or [])
        res["esco"][label] = {"total": d.get("total"), "returned": n}
        print(f"  {label}: total={d.get('total')} returned={n}")
    except Exception as e:
        res["esco"][label] = {"err": type(e).__name__ + ":" + str(e)[:120]}
        print(f"  {label}: ERR {str(e)[:100]}")

# lay danh sach nghe tu limit=100 roi do tung nghe
try:
    d = api("/search", type="occupation", limit=100, offset=0, language="en")
    results = (d.get("_embedded") or {}).get("results") or []
    print(f"\nESCO: do chi tiet {len(results)} nghe")
    ess, opt, titles = [], [], []
    for o in results:
        det = api("/resource/occupation", uri=o["uri"], language="en")
        links = det.get("_links", {})
        e = links.get("hasEssentialSkill") or []
        p = links.get("hasOptionalSkill") or []
        e = e if isinstance(e, list) else [e]
        p = p if isinstance(p, list) else [p]
        ess.append(len(e))
        opt.append(len(p))
        titles.append(det.get("title"))
    if ess:
        res["esco"]["detail"] = {
            "n": len(ess),
            "essential_mean": round(sum(ess) / len(ess), 2),
            "essential_min": min(ess), "essential_max": max(ess),
            "optional_mean": round(sum(opt) / len(opt), 2),
            "optional_min": min(opt), "optional_max": max(opt),
            "edges_per_occ_mean": round((sum(ess) + sum(opt)) / len(ess), 2),
            "sample_titles": titles[:6],
        }
        print(f"  essential mean={sum(ess)/len(ess):.2f} (min {min(ess)}, max {max(ess)})")
        print(f"  optional  mean={sum(opt)/len(opt):.2f} (min {min(opt)}, max {max(opt)})")
        print(f"  canh/nghe mean={(sum(ess)+sum(opt))/len(ess):.2f}")
except Exception as e:
    res["esco"]["detail"] = {"err": type(e).__name__ + ":" + str(e)[:200]}
    print("  ERR", str(e)[:200])

# ---------- do lai do thi P1 voi Technology Skills ----------
ZIP = Path(r"_newdata_audit/t4_verify/db_29_3_text.zip")
import re
import unicodedata

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
t2s_loose = {}
for t, s in t2s.items():
    t2s_loose.setdefault(loose(t), s)

tk = list(csv.reader(tch.splitlines(), delimiter="\t"))
h = tk[0]
ic, ie = h.index("O*NET-SOC Code"), h.index("Example")
tech = defaultdict(set)
for r in tk[1:]:
    if len(r) > max(ic, ie):
        tech[r[ic][:7]].add(r[ie])

BASE_DIR = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData")
job2soc = {}
with open(BASE_DIR / "jobs.tsv", encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    ij, it_ = h.index("JobID"), h.index("Title")
    for row in rd:
        if it_ < len(row):
            t = norm(row[it_])
            job2soc[row[ij]] = t2s.get(t) or t2s_loose.get(loose(t))

p1 = []
with open(BASE_DIR / "apps.tsv", encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    iu, ij = h.index("UserID"), h.index("JobID")
    for row in rd:
        soc = job2soc.get(row[ij])
        if soc and tech.get(soc[:7]):
            p1.append((row[iu], row[ij], soc))

p1_users = {u for u, _, _ in p1}
p1_jobs = {j for _, j, _ in p1}
p1_socs = {s for _, _, s in p1}
job_skill = sum(len(tech.get(s[:7], ())) for s in p1_socs)
skills_in_graph = set()
for s in p1_socs:
    skills_in_graph |= tech.get(s[:7], set())
res["graph_with_technology_skills"] = {
    "edges_user_job": len(p1),
    "nodes_user": len(p1_users),
    "nodes_job": len(p1_jobs),
    "nodes_occupation": len(p1_socs),
    "nodes_skill_technology": len(skills_in_graph),
    "edges_job_skill": job_skill,
    "density_pct": round(100.0 * len(p1) / (len(p1_users) * len(p1_jobs)), 6),
    "skills_per_job_mean": round(job_skill / len(p1_socs), 2),
    "pct_of_all_tech_vocab": round(100.0 * len(skills_in_graph) / 8775, 2),
}
print("\n=== Do thi P1 voi Technology Skills ===")
print(json.dumps(res["graph_with_technology_skills"], indent=1, ensure_ascii=False))

with open(OUT / "t5_esco_and_graph2.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
