"""t2: ESCO matrix - chi lay member occupations (co isInScheme member-occupations)."""
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


# lay nhieu trang bang limit lon
uris = []
for lim, off in [(500, 0), (500, 500), (500, 1000), (500, 1500), (500, 2000), (500, 2500), (500, 2900)]:
    try:
        d = get(f"{BASE}/search?type=occupation&limit={lim}&offset={off}&language=en&full=false")
        res = d.get("_embedded", {}).get("results", [])
    except Exception as e:
        print("err", lim, off, e)
        continue
    print(f"limit={lim} offset={off} -> {len(res)}")
    uris += [r for r in res]
uris = list({r["uri"]: r for r in uris}.values())
print("total unique occupation-ish concepts:", len(uris))

# phan loai member occupation vs isco group
member = [r for r in uris if any("member-occupations" in s for s in (r.get("isInScheme") or []))]
isco = [r for r in uris if any("isco" in s for s in (r.get("isInScheme") or []))]
print("member occupations:", len(member), "| isco groups:", len(isco))

random.seed(7)
sample = random.sample(member, min(150, len(member)))
ess, opt, stypes, nace = [], [], {}, 0
for i, r in enumerate(sample):
    try:
        d = get(f"{BASE}/resource/occupation?uri={urllib.parse.quote(r['uri'])}&language=en")
    except Exception:
        continue
    e = d.get("hasEssentialSkill") or []
    o = d.get("hasOptionalSkill") or []
    ess.append(len(e))
    opt.append(len(o))
    for s in e:
        t = (s.get("skillType") or "").rsplit("/", 1)[-1]
        if t:
            stypes[t] = stypes.get(t, 0) + 1
    links = d.get("_links") or {}
    if any("nace" in k.lower() for k in links):
        nace += 1
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(sample)}")


def summ(a):
    return ({"n": len(a), "mean": round(st.mean(a), 2), "median": st.median(a), "min": min(a),
             "max": max(a), "zero_frac": round(sum(1 for x in a if x == 0) / len(a), 3)} if a else None)


res = {
    "n_member_occupations_in_search": len(member),
    "n_isco_groups_in_search": len(isco),
    "n_sampled": len(sample),
    "essential_skill_per_occ": summ(ess),
    "optional_skill_per_occ": summ(opt),
    "skill_type_distribution_in_essential": stypes,
    "occupations_with_nace_link": nace,
}
if ess:
    tot = st.mean(ess) + st.mean(opt)
    res["est_total_occ_skill_edges"] = int(tot * len(member))
    res["skill_coverage_of_13485"] = None
print(json.dumps(res, indent=2, ensure_ascii=False))
OUT.joinpath("t2_esco_matrix.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
