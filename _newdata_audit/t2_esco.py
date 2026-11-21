"""t2: dem occupation/skill ESCO qua Web API; kiem tra phan cap skill-group va ISCO."""
import json
import time
import urllib.error
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
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(1.5)


def page_all(typ, lang="en", page=100, cap=40000):
    """Tra ve (total, so uri duy nhat, so ban ghi co hasEssentialSkill...)."""
    total = None
    uris = set()
    offset = 0
    while offset < cap:
        u = (f"{BASE}/search?type={typ}&limit={page}&offset={offset}&language={lang}"
             f"&full=false&viewObsolete=false")
        d = get(u)
        total = d.get("total", total)
        res = d.get("_embedded", {}).get("results", [])
        if not res:
            break
        for r in res:
            uris.add(r["uri"])
        offset += page
        if total is not None and offset >= total:
            break
    return total, len(uris)


res = {}
for typ in ["occupation", "skill", "skill-group", "concept-scheme", "isco-group"]:
    try:
        t, n = page_all(typ)
        res[typ] = {"total": t, "unique_fetched": n}
        print(typ, res[typ])
    except Exception as e:
        res[typ] = {"err": f"{type(e).__name__}: {e}"}
        print(typ, "ERR", e)

# ---- 1 skill detail: co skillType, co broader (skill group) khong? ----
sample_skill = "http://data.europa.eu/esco/skill/81a2db2c-7e55-44d0-9cd9-74c25147d7cd"  # analyse test data
d = get(f"{BASE}/resource/skill?uri={urllib.parse.quote(sample_skill)}&language=en")
res["skill_detail_keys"] = sorted(d.keys())
res["skill_detail"] = {k: d[k] for k in ["title", "skillType", "reuseLevel", "code"] if k in d}
res["skill_has_broader"] = "broaderSkill" in d or "broader" in d
res["skill_rel_keys"] = [k for k in d if k.startswith("_links") or k.startswith("has")]
res["skill_links_keys"] = sorted((d.get("_links") or {}).keys())

# ---- skill-group detail: co phan cap khong ----
sg_uri = "http://data.europa.eu/esco/skill/2.A"
try:
    sg = get(f"{BASE}/resource/skill?uri={urllib.parse.quote(sg_uri)}&language=en")
    res["skill_group_2A"] = {k: sg.get(k) for k in ["title", "className", "code"]}
    res["skill_group_2A_links"] = sorted((sg.get("_links") or {}).keys())
except Exception as e:
    res["skill_group_2A_err"] = str(e)

# ---- kiem tra ngon ngu vi ----
vi = get(f"{BASE}/search?type=occupation&limit=1&language=vi&text=engineer")
res["lang_vi_search"] = {"total": vi.get("total")}
# thu language=vi tren resource
try:
    dvi = get(f"{BASE}/resource/occupation?uri=http://data.europa.eu/esco/occupation/fbceeac6-798b-4307-a825-626707a753ad&language=vi")
    res["lang_vi_occupation"] = {"title": dvi.get("title"), "has_vi_label": "vi" in (dvi.get("preferredLabel") or {})}
except Exception as e:
    res["lang_vi_occupation_err"] = str(e)

# ---- so skill gan voi 1 occupation (be rong ma tran) ----
occ = get(f"{BASE}/resource/occupation?uri=http://data.europa.eu/esco/occupation/fbceeac6-798b-4307-a825-626707a753ad&language=en")
res["one_occupation_essential"] = len(occ.get("hasEssentialSkill") or [])
res["one_occupation_optional"] = len(occ.get("hasOptionalSkill") or [])

OUT.joinpath("t2_esco_stats.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(res, indent=2, ensure_ascii=False)[:3000])
