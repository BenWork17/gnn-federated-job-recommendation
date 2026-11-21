"""t2: do not so lieu ESCO con thieu: phan cap skill, skillType, skill-group, crosswalk O*NET."""
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
            time.sleep(1.0)


res = {}
# 1) lay 500 skill dau tien
skills = {}
for off in range(0, 2000, 500):
    d = get(f"{BASE}/search?type=skill&limit=500&offset={off}&language=en&full=false")
    r = d.get("_embedded", {}).get("results", [])
    print("skill offset", off, "->", len(r))
    for x in r:
        skills[x["uri"]] = x
    if len(r) < 500:
        break
res["n_skill_concepts_collected"] = len(skills)

# 2) chi tiet 60 skill: co broaderSkill / narrowerSkill khong; co skillType khong
random.seed(11)
sample = random.sample(list(skills), 60)
hier = {"has_broader": 0, "has_narrower": 0, "has_skill_group": 0}
stype, reuse, scheme = {}, {}, {}
for i, u in enumerate(sample):
    try:
        d = get(f"{BASE}/resource/skill?uri={urllib.parse.quote(u)}&language=en")
    except Exception:
        continue
    L = d.get("_links") or {}
    if L.get("broaderSkill"):
        hier["has_broader"] += 1
    if L.get("narrowerSkill"):
        hier["has_narrower"] += 1
    if L.get("broaderHierarchyConcept"):
        hier["has_skill_group"] += 1
    def first(x):
        if isinstance(x, list):
            return x[0] if x else None
        return x

    st = (first(L.get("hasSkillType")) or {}).get("uri", "")
    if st:
        t = st.rsplit("/", 1)[-1]
        stype[t] = stype.get(t, 0) + 1
    rl = (first(L.get("hasReuseLevel")) or {}).get("uri", "")
    if rl:
        reuse[rl.rsplit("/", 1)[-1]] = reuse.get(rl.rsplit("/", 1)[-1], 0) + 1
    for s in (L.get("isInScheme") or []):
        k = (s.get("uri") if isinstance(s, dict) else str(s)).rsplit("/", 1)[-1]
        scheme[k] = scheme.get(k, 0) + 1
res["hierarchy_on_60_sample"] = hier
res["skillType_distribution"] = stype
res["reuseLevel_distribution"] = reuse
res["isInScheme_distribution"] = scheme

# 3) vi du ve 1 skill co narrowerSkill
ex = []
for u in random.sample(list(skills), 30):
    try:
        d = get(f"{BASE}/resource/skill?uri={urllib.parse.quote(u)}&language=en")
    except Exception:
        continue
    L = d.get("_links") or {}
    if L.get("narrowerSkill"):
        ex.append({"title": d.get("title"),
                   "narrower": [s.get("title") for s in L["narrowerSkill"]][:5],
                   "broaderHierarchyConcept": [x.get("title") for x in (L.get("broaderHierarchyConcept") or [])][:5]})
        if len(ex) >= 3:
            break
res["hierarchy_examples"] = ex

# 4) skill-group concept: thu lay 1 nhom
for uri in ["http://data.europa.eu/esco/skill/S", "http://data.europa.eu/esco/skill/2.A.1"]:
    try:
        d = get(f"{BASE}/resource/skill?uri={urllib.parse.quote(uri)}&language=en")
        res.setdefault("skill_group_probe", {})[uri] = {"title": d.get("title"),
                                                       "keys": sorted(d.keys())[:15],
                                                       "n_narrower": len(((d.get("_links") or {}).get("narrowerSkill") or []))}
    except Exception as e:
        res.setdefault("skill_group_probe", {})[uri] = str(e)

OUT.joinpath("t2_esco_skill_detail.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])
