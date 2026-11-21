"""t2: do ty le dien THAT cua cot skills_desc (LinkedIn postings) qua datasets-server rows API.
Day la cach kiem chung 'cot skill tuong minh' ma KHONG phai tai 500MB.
"""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def get(u, timeout=90):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def probe_rows(cid, n=100, split="train", offset=0, config="default"):
    u = (f"https://datasets-server.huggingface.co/rows?dataset={urllib.parse.quote(cid)}"
         f"&config={config}&split={split}&offset={offset}&length={n}")
    return get(u)


def fill_stats(rows, cols):
    out = {}
    n = len(rows)
    for c in cols:
        vals = [r["row"].get(c) for r in rows]
        nonnull = [v for v in vals if v not in (None, "", "nan", "None", "[]", "{}")]
        out[c] = {"present_pct": round(100 * len(nonnull) / n, 1) if n else 0,
                  "example": str(nonnull[0])[:160] if nonnull else None}
    return out


report = {}

# --- 1) arshkon-style LinkedIn postings: co skills_desc + company_id ---
for cid in ["datastax/linkedin_job_listings", "xanderios/linkedin-job-postings"]:
    try:
        d = probe_rows(cid, n=100, offset=0)
        rows = d["rows"]
        cols = ["job_id", "company_id", "company_name", "title", "skills_desc",
                "formatted_experience_level", "location", "description"]
        cols = [c for c in cols if c in rows[0]["row"]]
        report[cid] = {"n_sampled": len(rows), "fill": fill_stats(rows, cols)}
    except Exception as e:
        report[cid] = {"err": f"{type(e).__name__}: {e}"}

print(json.dumps(report, indent=2, ensure_ascii=False)[:4000])

with open(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_skillsdesc_fill.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
