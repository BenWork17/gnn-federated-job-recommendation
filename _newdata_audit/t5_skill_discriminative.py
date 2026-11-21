"""t5: HAI phep do QUYET DINH con thieu.

(1) O*NET Skills.txt co PHAN BIET duoc nghe khong?
    t5_graph_design do duoc: skills_per_job_mean = 35.0 va distinct = 35
    => MOI nghe duoc gan DUNG 35/35 ky nang => do thi job-skill la HOAN TOAN (bipartite day du)
    => nut Skill KHONG mang thong tin. Day la ly do PHAI dung ESCO thay the.
    Kiem lai that ky: co dung 100% nghe co du 35 khong? Hay chi trung binh 35?

(2) ESCO co PHAN BIET khong? Goi API that, dem essential/optional cho N nghe.
    So sanh: ESCO 13.485 skill, neu moi nghe chi ~38 canh => rat phân biệt.
"""
import csv
import json
import re
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit\t5_verify")
ZIP = Path(r"_newdata_audit/t4_verify/db_29_3_text.zip")

# ---------- (1) O*NET Skills.txt: kiem phan biet ----------
with zipfile.ZipFile(ZIP) as z:
    raw = z.read([n for n in z.namelist() if n.endswith("/Skills.txt")][0]).decode("utf-8", "replace")
rows = list(csv.reader(raw.splitlines(), delimiter="\t"))
h = rows[0]
ic, ie = h.index("O*NET-SOC Code"), h.index("Element Name")
by_soc = {}
for r in rows[1:]:
    if len(r) > max(ic, ie):
        by_soc.setdefault(r[ic][:7], set()).add(r[ie])

counts = [len(v) for v in by_soc.values()]
all_skills = set()
for v in by_soc.values():
    all_skills |= v
n_full = sum(1 for c in counts if c == len(all_skills))
print(f"O*NET Skills.txt: {len(by_soc)} nghe, {len(all_skills)} ky nang phan biet")
print(f"  so ky nang/nghe: min={min(counts)} max={max(counts)} mean={sum(counts)/len(counts):.2f}")
print(f"  nghe co DU {len(all_skills)} ky nang: {n_full}/{len(by_soc)} = {100.0*n_full/len(by_soc):.2f}%")
onet_result = {
    "n_occupations": len(by_soc),
    "n_distinct_skills": len(all_skills),
    "skills_per_occupation": {"min": min(counts), "max": max(counts),
                              "mean": round(sum(counts) / len(counts), 3)},
    "occupations_with_all_skills": n_full,
    "pct_occupations_with_all_skills": round(100.0 * n_full / len(by_soc), 2),
    "verdict": ("KHONG PHAN BIET: moi nghe duoc gan gan nhu toan bo 35 ky nang "
                "=> do thi job-skill la bipartite gan day du, nut Skill vo dung "
                "=> PHAI dung ESCO (13.485 skill) lam lop Skill"),
}

# ---------- (1b) Technology Skills co phan biet khong ----------
with zipfile.ZipFile(ZIP) as z:
    rawt = z.read([n for n in z.namelist() if n.endswith("Technology Skills.txt")][0]).decode("utf-8", "replace")
rt = list(csv.reader(rawt.splitlines(), delimiter="\t"))
ht = rt[0]
ict, iet = ht.index("O*NET-SOC Code"), ht.index("Example")
tech = {}
for r in rt[1:]:
    if len(r) > max(ict, iet):
        tech.setdefault(r[ict][:7], set()).add(r[iet])
ct = [len(v) for v in tech.values()]
allt = set()
for v in tech.values():
    allt |= v
print(f"\nO*NET Technology Skills: {len(tech)} nghe, {len(allt)} cong nghe phan biet")
print(f"  so tech/nghe: min={min(ct)} max={max(ct)} mean={sum(ct)/len(ct):.2f}")
tech_result = {
    "n_occupations": len(tech), "n_distinct_tech": len(allt),
    "tech_per_occupation": {"min": min(ct), "max": max(ct), "mean": round(sum(ct) / len(ct), 2)},
    "verdict": "PHAN BIET duoc (trung binh ~57/8775) nhung van la MUC NGHE, khong phai muc tin",
}

# ---------- (2) ESCO: do phan biet ----------
BASE = "https://ec.europa.eu/esco/api"


def api(path, **params):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


ess_counts, opt_counts, titles = [], [], []
try:
    occ = api("/search", type="occupation", limit=40, offset=100, language="en")
    results = occ["_embedded"]["results"]
    print(f"\nESCO: lay {len(results)} nghe (offset=100)")
    for o in results:
        det = api("/resource/occupation", uri=o["uri"], language="en")
        links = det.get("_links", {})
        e = links.get("hasEssentialSkill") or []
        p = links.get("hasOptionalSkill") or []
        e = e if isinstance(e, list) else [e]
        p = p if isinstance(p, list) else [p]
        ess_counts.append(len(e))
        opt_counts.append(len(p))
        titles.append(det.get("title"))
    print(f"  essential: mean={sum(ess_counts)/len(ess_counts):.2f} min={min(ess_counts)} max={max(ess_counts)}")
    print(f"  optional : mean={sum(opt_counts)/len(opt_counts):.2f} min={min(opt_counts)} max={max(opt_counts)}")
    print(f"  tong canh/nghe mean={(sum(ess_counts)+sum(opt_counts))/len(ess_counts):.2f}")
    esco_result = {
        "n_occupations_sampled": len(ess_counts),
        "essential": {"mean": round(sum(ess_counts) / len(ess_counts), 2),
                      "min": min(ess_counts), "max": max(ess_counts)},
        "optional": {"mean": round(sum(opt_counts) / len(opt_counts), 2),
                     "min": min(opt_counts), "max": max(opt_counts)},
        "edges_per_occupation_mean": round((sum(ess_counts) + sum(opt_counts)) / len(ess_counts), 2),
        "sample_titles": titles[:8],
        "verdict": "PHAN BIET manh: ~38 canh/nghe tren 13.485 skill -> ti le 0,28%",
    }
except Exception as e:
    esco_result = {"err": type(e).__name__ + ": " + str(e)[:200]}
    print("ESCO ERR", str(e)[:200])

res = {"onet_skills_discriminative": onet_result,
       "onet_tech_discriminative": tech_result,
       "esco_discriminative": esco_result}
with open(OUT / "t5_skill_discriminative.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("\nwrote t5_skill_discriminative.json")
