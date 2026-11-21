"""t2: debug vi sao resource occupation tu danh sach search khong co hasEssentialSkill."""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research audit)"}
BASE = "https://ec.europa.eu/esco/api"


def get(u):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


d = get(f"{BASE}/search?type=occupation&limit=100&offset=0&language=en&full=false")
res = d["_embedded"]["results"]
print("n results", len(res))
for r in res[:3]:
    print("  uri:", r["uri"], "| keys:", list(r.keys()))

print()
for r in res[:5]:
    u = f"{BASE}/resource/occupation?uri={urllib.parse.quote(r['uri'])}&language=en"
    dd = get(u)
    print(r["uri"].rsplit("/", 1)[-1], "->",
          "ess:", len(dd.get("hasEssentialSkill") or []),
          "opt:", len(dd.get("hasOptionalSkill") or []),
          "| keys:", [k for k in dd if k.startswith("has") or k.startswith("_l")])
