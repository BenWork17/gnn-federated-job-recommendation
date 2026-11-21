"""t2: lay metadata ESCO dataset tren EU Open Data Portal (license + distributions)."""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def getj(u, timeout=90):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


CATALOGUE = [
    "https://data.europa.eu/api/hub/search/datasets/european-skills-competences-qualifications-and-occupations",
]
for u in CATALOGUE:
    try:
        j = getj(u)
    except Exception as e:
        print(u, "ERR", e)
        continue
    res = j.get("result", j)
    print("id:", res.get("id"))
    print("title:", res.get("title"))
    print("license:", json.dumps(res.get("license"), ensure_ascii=False))
    print("publisher:", json.dumps(res.get("publisher"), ensure_ascii=False)[:200])
    print("modified:", res.get("modified"))
    dists = res.get("distributions") or []
    print("n_distributions:", len(dists))
    for d in dists[:12]:
        acc = d.get("access_url") or d.get("accessURL")
        fmt = d.get("format")
        print("   -", (d.get("title") or "")[:70], "|", fmt, "|", str(acc)[:130],
              "| bytes:", d.get("byte_size") or d.get("byteSize"))
    # in toan bo key
    print("keys:", sorted(res.keys()))
