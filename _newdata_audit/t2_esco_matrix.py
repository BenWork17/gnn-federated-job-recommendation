"""t2: do mat do ma tran ESCO occupation-skill bang cach sample N occupation qua API."""
import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
UA = {"User-Agent": "Mozilla/5.0 (research audit)"}
BASE = "https://ec.europa.eu/esco/api"


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.2)


# 1) lay danh sach occupation (phan trang dung offset lon)
uris = []
for off in range(0, 3000, 100):
    try:
        d = get(f"{BASE}/search?type=occupation&limit=100&offset={off}&language=en&full=false")
        res = d.get("_embedded", {}).get("results", [])
        if not res:
            break
        uris += [r["uri"] for r in res]
    except Exception as e:
        print("list err at", off, e)
        break
print("occupation uris fetched:", len(uris))
uris = list(dict.fromkeys(uris))

# 2) sample
random.seed(42)
sample = random.sample(uris, min(200, len(uris)))
ess, opt, has_skill_type = [], [], {}
nace_found = 0
for i, u in enumerate(sample):
    try:
        d = get(f"{BASE}/resource/occupation?uri={urllib.parse.quote(u)}&language=en")
    except Exception:
        continue
    e = len(d.get("hasEssentialSkill") or [])
    o = len(d.get("hasOptionalSkill") or [])
    ess.append(e)
    opt.append(o)
    for s in (d.get("hasEssentialSkill") or []):
        st = s.get("skillType", "").rsplit("/", 1)[-1]
        has_skill_type[st] = has_skill_type.get(st, 0) + 1
    if "_links" in d and any("nace" in k.lower() for k in (d.get("_links") or {})):
        nace_found += 1
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(sample)} done")

import statistics as st


def summ(a):
    return {"n": len(a), "mean": round(st.mean(a), 2), "median": st.median(a),
            "min": min(a), "max": max(a), "zero_frac": round(sum(1 for x in a if x == 0) / len(a), 3)} if a else None


res = {
    "n_occupations_listed": len(uris),
    "n_sampled": len(sample),
    "essential_skill_per_occ": summ(ess),
    "optional_skill_per_occ": summ(opt),
    "total_edges_estimate": (st.mean(ess) + st.mean(opt)) * len(uris) if ess else None,
    "skill_type_distribution_in_essential": has_skill_type,
    "occupations_with_nace_link": nace_found,
}
print(json.dumps(res, indent=2, ensure_ascii=False))
OUT.joinpath("t2_esco_matrix.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
