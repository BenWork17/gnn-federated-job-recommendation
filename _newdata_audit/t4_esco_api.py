"""t4: kiem chung lai taxonomy ESCO bang API (dem that, khong tin tri nho).

Do: total occupation, total skill, so ngon ngu trong preferredLabel cua 1 occupation,
    co 'vi' hay khong, va 1 occupation co essential/optional skill that.
"""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
BASE = "https://ec.europa.eu/esco/api"


def api(path, **params):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


out = {}
for t in ["occupation", "skill", "skill-group", "concept-scheme", "isco-group"]:
    try:
        d = api("/search", type=t, limit=1, language="en")
        out[f"total_{t}"] = d.get("total")
        print("total", t, d.get("total"))
    except Exception as e:
        out[f"total_{t}"] = "ERR " + str(e)[:80]
        print("total", t, "ERR", str(e)[:80])

# 1 occupation chi tiet: lay tu search
occ = api("/search", type="occupation", limit=3, language="en")
first = occ["_embedded"]["results"][0]
uri = first["uri"]
print("occupation sample:", first.get("title"), uri)
det = api("/resource/occupation", uri=uri, language="en")
labels = det.get("preferredLabel", {})
out["sample_occupation"] = {
    "title": det.get("title"),
    "uri": uri,
    "n_preferredLabel_langs": len(labels),
    "langs": sorted(labels),
    "has_vi": "vi" in labels,
}
print("n langs:", len(labels), "has vi:", "vi" in labels)

links = det.get("_links", {})
for k in ["hasEssentialSkill", "hasOptionalSkill", "isEssentialForOccupation", "hasSkill"]:
    if k in links:
        out["sample_occupation"][k] = (links[k].get("title"), links[k].get("uri"))

# dem essential/optional cua 1 occupation: goi resource voi full? thu lay tu search theo occupation
try:
    rel = api("/resource/occupation", uri=uri, language="en")
    ess = rel.get("_links", {}).get("hasEssentialSkill")
    print("essential link:", ess)
except Exception as e:
    print("err", e)

# so nghe trong 1 skill-group va ma ISCO
out["api_note"] = "total = so concept trong search index"

with open(r"_newdata_audit/t4_verify/t4_esco_api.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False)[:2000])
