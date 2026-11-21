# -*- coding: utf-8 -*-
"""t2: kiem chung join JobHop.matched_code -> ESCO occupation.code (dieu kien de noi User-Skill)."""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0 (research audit)"}
BASE = "https://ec.europa.eu/esco/api"
D = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_data")

df = pd.read_parquet(D / "JobHop_v2_train.parquet", columns=["resume_id", "matched_code"])
codes = df["matched_code"].astype(str)
vc = codes.value_counts()
print("distinct matched_code:", len(vc))
print("top10:", vc.head(10).to_dict())
print("'unknown' rows:", int((codes == "unknown").sum()),
      f"({100*(codes=='unknown').mean():.2f}%)")

# lay toan bo occupation code tu ESCO API (500/trang)
api_codes = {}
for off in range(0, 3000, 500):
    u = f"{BASE}/search?type=occupation&limit=500&offset={off}&language=en&full=false"
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    res = d.get("_embedded", {}).get("results", [])
    print(f"  offset {off} -> {len(res)}")
    for x in res:
        if x.get("code"):
            api_codes[x["code"]] = x["title"]
    if len(res) < 500:
        break

print("ESCO occupation codes fetched:", len(api_codes))

# so sanh tren tap code xuat hien nhieu nhat
top = [c for c in vc.index if c != "unknown"][:3000]
hit = [c for c in top if c in api_codes]
print(f"\nJobHop distinct codes checked: {len(top)}")
print(f"khong co trong 500 occupation dau cua API: {len(top)-len(hit)}")
print(f"match: {len(hit)} ({100*len(hit)/max(1,len(top)):.1f}%)")
sample = [(c, api_codes[c]) for c in hit[:8]]
print("sample join:", sample)
print("sample miss:", [c for c in top if c not in api_codes][:8])

# thu tra truc tiep 1 code bang search
for c in [c for c in top if c not in api_codes][:3] + [hit[0] if hit else None]:
    if not c:
        continue
    u = f"{BASE}/search?type=occupation&limit=3&language=en&text={urllib.parse.quote(c)}"
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8"))
        print(f"  search {c!r} -> total {d.get('total')}, first:",
              [(x.get('code'), x.get('title')) for x in (d.get('_embedded', {}).get('results') or [])[:2]])
    except Exception as e:
        print("  search err", c, e)

Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_jobhop_join.json").write_text(
    json.dumps({"distinct_codes": len(vc), "unknown_pct": round(100 * (codes == 'unknown').mean(), 2),
                "esco_codes_fetched": len(api_codes), "checked": len(top), "matched": len(hit),
                "matched_pct": round(100 * len(hit) / max(1, len(top)), 1),
                "sample_join": sample, "top10_codes": vc.head(10).to_dict()},
               indent=2, ensure_ascii=False), encoding="utf-8")
