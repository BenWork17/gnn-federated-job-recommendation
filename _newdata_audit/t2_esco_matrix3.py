"""t2: ESCO matrix - skill links nam trong _links (API v6.x). Do lai cho dung."""
import json
import random
import statistics as st
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
            time.sleep(1.0)


# --- lay danh sach occupation theo trang (limit 500, page 1..6) ---
found = {}
for off in range(0, 3000, 500):
    try:
        d = get(f"{BASE}/search?type=occupation&limit=500&offset={off}&language=en&full=false")
    except Exception as e:
        print("err", off, e)
        continue
    res = d.get("_embedded", {}).get("results", [])
    print(f"offset={off} -> {len(res)} (total={d.get('total')})")
    for r in res:
        found[r["uri"]] = r
    if len(res) < 500:
        break
print("unique occupations collected:", len(found))

random.seed(7)
sample = random.sample(list(found.values()), min(200, len(found)))
ess, opt, stypes, reuse = [], [], {}, {}
n_err = 0
for i, r in enumerate(sample):
    try:
        d = get(f"{BASE}/resource/occupation?uri={urllib.parse.quote(r['uri'])}&language=en")
    except Exception:
        n_err += 1
        continue
    L = d.get("_links") or {}
    e = L.get("hasEssentialSkill") or []
    o = L.get("hasOptionalSkill") or []
    ess.append(len(e))
    opt.append(len(o))
    for s in e:
        t = (s.get("skillType") or "").rsplit("/", 1)[-1]
        if t:
            stypes[t] = stypes.get(t, 0) + 1
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(sample)}  (err={n_err})")


def summ(a):
    return ({"n": len(a), "mean": round(st.mean(a), 2), "median": st.median(a), "min": min(a),
             "max": max(a), "zero_frac": round(sum(1 for x in a if x == 0) / len(a), 3),
             "p95": sorted(a)[int(0.95 * (len(a) - 1))]} if a else None)


res = {
    "n_occupations_collected": len(found),
    "n_sampled": len(sample),
    "n_errors": n_err,
    "essential_skill_per_occ": summ(ess),
    "optional_skill_per_occ": summ(opt),
    "skill_type_distribution_in_essential": stypes,
}
if ess:
    tot = st.mean(ess) + st.mean(opt)
    res["mean_edges_per_occ"] = round(tot, 2)
    res["est_total_occ_skill_edges_for_2942"] = int(tot * 2942)
print(json.dumps(res, indent=2, ensure_ascii=False))
OUT.joinpath("t2_esco_matrix.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
