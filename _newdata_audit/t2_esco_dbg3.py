"""t2: debug tai sao 500 occupation dau tien khong co skill link."""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research audit)"}
BASE = "https://ec.europa.eu/esco/api"


def get(u):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


d = get(f"{BASE}/search?type=occupation&limit=5&offset=0&language=en&full=false")
for r in d["_embedded"]["results"]:
    print(json.dumps({k: r.get(k) for k in ("title", "code", "isInScheme", "className")}, ensure_ascii=False))
print()

# chi tiet day du cua 1 cai
u = d["_embedded"]["results"][0]["uri"]
full = get(f"{BASE}/resource/occupation?uri={urllib.parse.quote(u)}&language=en")
print("uri:", u)
print("all keys:", sorted(full.keys()))
print("hasEssentialSkill present:", "hasEssentialSkill" in full)
print("links keys:", sorted((full.get("_links") or {}).keys()))
print()

# so sanh voi calculation engineer (da biet co skill)
ce = "http://data.europa.eu/esco/occupation/fbceeac6-798b-4307-a825-626707a753ad"
f2 = get(f"{BASE}/resource/occupation?uri={urllib.parse.quote(ce)}&language=en")
print("calculation engineer links keys:", sorted((f2.get("_links") or {}).keys()))
print("  ess:", len(f2.get("hasEssentialSkill") or []))
print()
print("== isInScheme cua 2 cai ==")
print("first:", full.get("isInScheme"))
print("calc :", f2.get("isInScheme"))
