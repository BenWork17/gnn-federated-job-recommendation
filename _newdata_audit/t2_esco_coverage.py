# -*- coding: utf-8 -*-
"""t2: do coverage cua ESCO: bao nhieu % skill co lien ket toi it nhat 1 nghe."""
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
UA = {"User-Agent": "Mozilla/5.0 (research audit)"}
BASE = "https://ec.europa.eu/esco/api"


def get(u, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.0)


# Lay 500 skill dau (giong lan truoc) roi sample 80
skills = {}
for off in range(0, 1000, 500):
    d = get(f"{BASE}/search?type=skill&limit=500&offset={off}&language=en&full=false")
    r = d.get("_embedded", {}).get("results", [])
    for x in r:
        skills[x["uri"]] = x
    if len(r) < 500:
        break
print("skills collected:", len(skills))

random.seed(23)
sample = random.sample(list(skills), 80)
linked, unlinked, n_err = 0, 0, 0
occupations_touched = set()
for u in sample:
    try:
        d = get(f"{BASE}/resource/skill?uri={urllib.parse.quote(u)}&language=en")
    except Exception:
        n_err += 1
        continue
    L = d.get("_links") or {}
    ess = L.get("isEssentialForOccupation") or []
    opt = L.get("isOptionalForOccupation") or []
    if ess or opt:
        linked += 1
        for o in (ess + opt):
            occupations_touched.add(o.get("uri"))
    else:
        unlinked += 1

res = {
    "n_sampled_skills": len(sample),
    "skills_linked_to_ge1_occupation": linked,
    "skills_linked_to_0_occupation": unlinked,
    "errors": n_err,
    "pct_linked": round(100 * linked / max(1, linked + unlinked), 1),
    "distinct_occupations_touched_by_sample": len(occupations_touched),
}
print(json.dumps(res, indent=2, ensure_ascii=False))
OUT.joinpath("t2_esco_coverage.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
