# -*- coding: utf-8 -*-
"""t2: Arbeitnow - do ty le dien cua tags/job_types va do sau phan trang (co delay)."""
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}


def getj(u, timeout=45):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


items = []
page = 1
while page <= 40:
    try:
        j = getj(f"https://www.arbeitnow.com/api/job-board-api?page={page}")
    except urllib.error.HTTPError as e:
        print("  stop page", page, "HTTP", e.code)
        break
    except Exception as e:
        print("  stop page", page, type(e).__name__)
        break
    d = j.get("data") or []
    if not d:
        break
    for it in d:
        it["_page"] = page
        items.append(it)
    page += 1
    time.sleep(0.35)

print("pages fetched:", page - 1, "| items:", len(items))
n = len(items)
out = {"n_items": n, "pages": page - 1}
for c in ["slug", "company_name", "title", "description", "remote", "url", "tags", "job_types", "location", "created_at"]:
    vals = [it.get(c) for it in items]
    nn = [v for v in vals if v not in (None, "", [], "[]")]
    out[c] = {"fill_pct": round(100 * len(nn) / n, 1),
              "example": str(nn[0])[:120] if nn else None}
# tags co phai ky nang khong?
tagc = Counter()
for it in items:
    for t in (it.get("tags") or []):
        tagc[t] += 1
out["distinct_tags"] = len(tagc)
out["top_tags"] = tagc.most_common(15)
jc = Counter()
for it in items:
    for t in (it.get("job_types") or []):
        jc[t] += 1
out["job_types"] = jc.most_common(10)
out["distinct_companies"] = len({it.get("company_name") for it in items})
print(json.dumps(out, indent=2, ensure_ascii=False)[:2500])
open(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_arbeitnow.json", "w", encoding="utf-8").write(
    json.dumps(out, indent=2, ensure_ascii=False))
