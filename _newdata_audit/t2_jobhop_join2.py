# -*- coding: utf-8 -*-
"""t2: do ty le join THAT cua JobHop.matched_code -> ESCO occupation bang search theo tung code."""
import json
import random
import sys
import time
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
codes = codes[codes != "unknown"]
uniq = sorted(codes.unique())

random.seed(99)
sample = random.sample(uniq, 60)
hit, miss, err = [], [], []
for i, c in enumerate(sample):
    u = f"{BASE}/search?type=occupation&limit=2&language=en&text={urllib.parse.quote(c)}"
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.loads(r.read().decode("utf-8"))
        res = d.get("_embedded", {}).get("results") or []
        if any(x.get("code") == c for x in res):
            hit.append(c)
        else:
            miss.append(c)
    except Exception as e:
        err.append((c, str(e)[:40]))
    time.sleep(0.2)
    if (i + 1) % 20 == 0:
        print(f"  {i+1}/{len(sample)} hit={len(hit)} miss={len(miss)} err={len(err)}")

res = {"n_sampled": len(sample), "hit": len(hit), "miss": len(miss), "err": len(err),
       "join_pct": round(100 * len(hit) / max(1, len(hit) + len(miss)), 1),
       "miss_examples": miss[:10], "hit_examples": hit[:10],
       "note": "ESCO API /search caps pagination at 500 rows (offset>0 returns empty), so codes were resolved by exact-code text search"}
print(json.dumps(res, indent=2, ensure_ascii=False))
Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_jobhop_join.json").write_text(
    json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
