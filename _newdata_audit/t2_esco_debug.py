"""t2: debug phan trang ESCO API + xac nhan ngon ngu VI khong co."""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research audit)"}
BASE = "https://ec.europa.eu/esco/api"


def get(u):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


for off in [0, 100, 200, 1000, 2000, 2900]:
    u = f"{BASE}/search?type=occupation&limit=100&offset={off}&language=en&full=false&viewObsolete=false"
    d = get(u)
    n = len(d.get("_embedded", {}).get("results", []))
    print("offset", off, "total", d.get("total"), "returned", n)

# thu limit lon hon
for lim in [100, 200, 500]:
    u = f"{BASE}/search?type=occupation&limit={lim}&offset=0&language=en&full=false&viewObsolete=false"
    d = get(u)
    print("limit", lim, "returned", len(d.get("_embedded", {}).get("results", [])))

# --- kiem tra ngon ngu: so sanh label cua 1 occupation khi language=vi vs en ---
occ = "http://data.europa.eu/esco/occupation/fbceeac6-798b-4307-a825-626707a753ad"
for lang in ["en", "vi", "fr", "de"]:
    d = get(f"{BASE}/resource/occupation?uri={urllib.parse.quote(occ)}&language={lang}")
    pl = d.get("preferredLabel") or {}
    alt = d.get("alternativeLabel") or {}
    print(f"lang={lang}: title={d.get('title')!r} n_prefLabel={len(pl)} vi_in_pref={'vi' in pl} vi_in_alt={'vi' in alt}")
