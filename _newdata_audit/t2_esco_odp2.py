# -*- coding: utf-8 -*-
"""t2: metadata ESCO tren EU ODP - ghi UTF-8 ra file, khong in console."""
import json
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
UA = {"User-Agent": "Mozilla/5.0"}


def getj(u, timeout=90):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


j = getj("https://data.europa.eu/api/hub/search/datasets/european-skills-competences-qualifications-and-occupations")
res = j.get("result", j)
OUT.joinpath("t2_esco_odp_raw.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

print("id:", res.get("id"))
for k in ("title", "description"):
    v = res.get(k)
    if isinstance(v, dict):
        v = v.get("en") or list(v.values())[0]
    print(f"{k}:", str(v)[:300])
print("license:", json.dumps(res.get("license"), ensure_ascii=False))
print("publisher:", json.dumps((res.get("publisher") or {}).get("name"), ensure_ascii=False))
print("modified:", res.get("modified"), "| issued:", res.get("issued"))
print("n_distributions:", len(res.get("distributions") or []))
for d in (res.get("distributions") or [])[:15]:
    t = d.get("title")
    if isinstance(t, dict):
        t = t.get("en") or list(t.values())[0]
    print("  -", str(t)[:80], "|", d.get("format"), "|", str(d.get("access_url"))[:140])
print("all top keys:", sorted(res.keys()))
