"""t5: (a) kiem license OLX qua duong khac (Kaggle bi reCAPTCHA chan),
       (b) kiem ten cong ty/nguoi kieu Faker trong 3 repo tong hop,
       (c) do thoi gian xu ly that de uoc luong chi phi ky thuat.
"""
import csv
import io
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
UA_BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}
OUT = Path(r"_newdata_audit\t5_verify")
res = {}


def try_fetch(url, headers=None, timeout=60, nbytes=400000):
    rec = {"url": url}
    try:
        req = urllib.request.Request(url, headers=headers or UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read(nbytes).decode("utf-8", "replace")
        rec.update(status=200, body=b, n_chars=len(b))
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, body="")
    except Exception as e:
        rec.update(status=None, err=str(e)[:120], body="")
    return rec


# ---------- (a) OLX license qua nhieu duong ----------
print("=== OLX license: thu nhieu duong ===")
olx = {}
# a1. HF mirror
for q in ["olx", "olx-jobs"]:
    r = try_fetch(f"https://huggingface.co/api/datasets?search={q}&limit=50")
    ids = []
    if r.get("body"):
        try:
            ids = [d.get("id") for d in json.loads(r["body"])]
        except Exception:
            pass
    olx[f"hf_search_{q}"] = ids[:10]
    print(f"  HF '{q}': {len(ids)} -> {ids[:5]}")

# a2. Kaggle qua API voi browser UA (thu lai, co the van reCAPTCHA)
for name, url in [
    ("kaggle_api_view", "https://www.kaggle.com/api/v1/datasets/view/olxdatascience/olx-jobs-interactions"),
    ("kaggle_api_list", "https://www.kaggle.com/api/v1/datasets/list?search=olx-jobs-interactions"),
]:
    r = try_fetch(url, headers=UA_BROWSER, nbytes=200000)
    body = r.get("body", "")
    is_challenge = "recaptcha" in body.lower() or "Checking your browser" in body
    olx[name] = {"status": r.get("status"), "n_chars": r.get("n_chars"),
                 "is_recaptcha": is_challenge}
    print(f"  {name}: status={r.get('status')} chars={r.get('n_chars')} recaptcha={is_challenge}")

# a3. web archive
for name, url in [
    ("wayback_page", "http://archive.org/wayback/available?url=kaggle.com/datasets/olxdatascience/olx-jobs-interactions"),
]:
    r = try_fetch(url)
    olx[name] = {"status": r.get("status"), "body": (r.get("body") or "")[:400]}
    print(f"  {name}: status={r.get('status')} {(r.get('body') or '')[:200]}")

res["olx_license_attempt"] = olx

# ---------- (b) Faker check ----------
print("\n=== Kiem ten Faker trong 3 repo tong hop ===")
REPO = "mindweave/job-postings-applications"


def fetch_csv(table):
    url = f"https://huggingface.co/datasets/{REPO}/resolve/main/data/{table}.csv"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return list(csv.reader(io.StringIO(r.read().decode("utf-8", "replace"))))


fake = {}
try:
    comp = fetch_csv("companies")
    h = comp[0]
    body = comp[1:]
    ci = h.index("company_name") if "company_name" in h else 0
    names = [r[ci] for r in body if ci < len(r)]
    fake["companies_header"] = h
    fake["n_companies"] = len(names)
    fake["sample_10"] = names[:10]
    # dau hieu Faker: "X, Y and Z" / "X Ltd" / "X and Sons"
    pat = re.compile(r",\s.*\band\b|\band Sons\b|\bLtd\b|\bLLC\b|\bGroup\b|\bInc\b", re.I)
    fake["pct_stereotypical_pattern"] = round(100.0 * sum(1 for n in names if pat.search(n)) / len(names), 2)
    # so tu trong ten (Faker hay 2-4 tu ghep)
    fake["distinct_names"] = len(set(names))
    fake["pct_names_with_comma"] = round(100.0 * sum(1 for n in names if "," in n) / len(names), 2)
    print(f"  companies: {len(names)} dong, {len(set(names))} ten phan biet")
    print(f"  % ten co dau phay: {fake['pct_names_with_comma']}")
    print(f"  % khop pattern kieu Faker: {fake['pct_stereotypical_pattern']}")
    print("  mau:", names[:8])
except Exception as e:
    fake["err"] = str(e)[:150]
    print("  ERR", str(e)[:120])
res["faker_check"] = fake

# ---------- (c) do thoi gian xu ly ----------
print("\n=== Do thoi gian xu ly that ===")
timings = {}
# doc apps.tsv (75 MB) + dem
t0 = time.time()
n = 0
with open(r"E:\2026\DUT\IOT\Cuoiki\NewData\apps.tsv", encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    next(rd)
    for _ in rd:
        n += 1
timings["apps_tsv_read_75MB"] = {"rows": n, "sec": round(time.time() - t0, 2),
                                 "MBps": round(75.03 / (time.time() - t0), 2)}
print(f"  apps.tsv: {n} dong trong {timings['apps_tsv_read_75MB']['sec']}s")

# doc jobs.tsv (3,4 GB) — chi doc 200k dong dau de uoc luong
t0 = time.time()
n = 0
with open(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv", encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    next(rd)
    for _ in rd:
        n += 1
        if n >= 200000:
            break
dt = time.time() - t0
timings["jobs_tsv_200k_rows"] = {"rows": n, "sec": round(dt, 2), "rows_per_sec": round(n / dt)}
# uoc luong toan bo 1.092.096 dong
est_full = 1092096 / (n / dt)
timings["jobs_tsv_estimated_full_sec"] = round(est_full, 1)
print(f"  jobs.tsv 200k dong: {dt:.2f}s -> uoc toan bo {est_full:.0f}s ({est_full/60:.1f} phut)")
res["timings"] = timings

with open(OUT / "t5_synthetic_faker_and_timing.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("\ndone")
