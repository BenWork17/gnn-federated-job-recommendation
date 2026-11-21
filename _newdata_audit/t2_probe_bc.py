"""t2: tai that cac nguon nho (<500MB) de do cot thuc te.
(C) JobHop 11.5MB parquet + resume-job-description-fit (68MB)
(B) Arbeitnow API, USAJobs API (khong can key?), Adzuna
"""
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_data")
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research audit)"}


def dl(url, dest, timeout=300):
    if dest.exists() and dest.stat().st_size > 1000:
        return {"cached": True, "bytes": dest.stat().st_size}
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    dest.write_bytes(data)
    return {"cached": False, "bytes": len(data)}


report = {}

# ---------- JobHop parquet ----------
try:
    r = dl("https://huggingface.co/datasets/aida-ugent/JobHop/resolve/main/JobHop_v2_train.parquet",
           OUT / "JobHop_v2_train.parquet")
    report["jobhop_train"] = r
except Exception as e:
    report["jobhop_train"] = {"err": f"{type(e).__name__}: {e}"}

# ---------- ESCO Groups folder listing (JobHop) ----------
try:
    req = urllib.request.Request("https://huggingface.co/api/datasets/aida-ugent/JobHop/tree/main/ESCO%20Groups", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as rr:
        report["jobhop_esco_groups_tree"] = json.loads(rr.read().decode())
except Exception as e:
    report["jobhop_esco_groups_tree"] = {"err": str(e)}

# ---------- Arbeitnow public API ----------
try:
    req = urllib.request.Request("https://www.arbeitnow.com/api/job-board-api", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as rr:
        j = json.loads(rr.read().decode())
    d0 = (j.get("data") or [{}])[0]
    report["arbeitnow"] = {
        "ok": True,
        "n_items_page1": len(j.get("data") or []),
        "links": j.get("links"),
        "meta": j.get("meta"),
        "columns_on_item": sorted(d0.keys()) if d0 else [],
        "sample_item": {k: (str(v)[:120] if not isinstance(v, (int, float, bool)) else v) for k, v in d0.items()} if d0 else {},
    }
except Exception as e:
    report["arbeitnow"] = {"err": f"{type(e).__name__}: {e}"}

# ---------- USAJobs API (can key) ----------
try:
    req = urllib.request.Request("https://data.usajobs.gov/api/search?ResultsPerPage=1",
                                 headers={"User-Agent": "audit@example.org", "Host": "data.usajobs.gov"})
    with urllib.request.urlopen(req, timeout=60) as rr:
        j = json.loads(rr.read().decode())
    report["usajobs"] = {"ok": True, "keys": list(j.keys())[:10]}
except urllib.error.HTTPError as e:
    report["usajobs"] = {"ok": False, "status": e.code, "body": e.read()[:300].decode("utf-8", "replace")}
except Exception as e:
    report["usajobs"] = {"ok": False, "err": f"{type(e).__name__}: {e}"}

# ---------- Adzuna API (can app_id + app_key) ----------
try:
    req = urllib.request.Request("https://api.adzuna.com/v1/api/jobs/gb/search/1?results_per_page=1",
                                 headers=UA)
    with urllib.request.urlopen(req, timeout=60) as rr:
        j = json.loads(rr.read().decode())
    report["adzuna_nokey"] = {"ok": True, "keys": list(j.keys())}
except urllib.error.HTTPError as e:
    report["adzuna_nokey"] = {"ok": False, "status": e.code, "body": e.read()[:400].decode("utf-8", "replace")}
except Exception as e:
    report["adzuna_nokey"] = {"ok": False, "err": f"{type(e).__name__}: {e}"}

(OUT.parent / "t2_api_probe.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False)[:5000])
