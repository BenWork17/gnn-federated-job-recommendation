"""t5: doc license OLX THAT qua Wayback (Kaggle chan bang reCAPTCHA),
va hoan tat do thoi gian xu ly (jobs.tsv).
"""
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit\t5_verify")
res = {}


def try_fetch(url, timeout=90, nbytes=2_000_000):
    rec = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read(nbytes).decode("utf-8", "replace")
        rec.update(status=200, body=b, n_chars=len(b))
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, body="")
    except Exception as e:
        rec.update(status=None, err=str(e)[:150], body="")
    return rec


def text_of(html):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "\n", t)
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


# ---------- OLX qua Wayback ----------
r = try_fetch("http://archive.org/wayback/available?url=kaggle.com/datasets/olxdatascience/olx-jobs-interactions")
snap = None
if r.get("body"):
    try:
        snap = json.loads(r["body"])["archived_snapshots"]["closest"]["url"]
    except Exception:
        pass
print("wayback snapshot:", snap)
olx = {"snapshot": snap}
if snap:
    rr = try_fetch(snap)
    olx["status"] = rr.get("status")
    olx["n_chars"] = rr.get("n_chars")
    body = rr.get("body", "")
    if body:
        (OUT / "olx_wayback.html").write_text(body, encoding="utf-8")
        for pat in [r'"licenseName"\s*:\s*"([^"]{1,80})"',
                    r'"licenseUrl"\s*:\s*"([^"]{1,200})"',
                    r'(CC0[^"<,;]{0,40})', r'(CC-BY[^"<,;]{0,40})',
                    r'(ODC[^"<,;]{0,40})', r'"(Other)"']:
            m = sorted(set(re.findall(pat, body)))
            if m:
                olx.setdefault("license_matches", {})[pat[:24]] = m[:6]
        txt = text_of(body)
        olx["text_lines"] = [l for l in txt.split("\n")
                             if re.search(r"licen|commercial|research|academic|CC0|CC-BY|ODbL|"
                                          r"attribution|Other|interactions\.csv|usability", l, re.I)][:30]
        olx["files_mentioned"] = sorted(set(re.findall(r"[\w./-]+\.(?:csv|txt|zip|parquet)", body)))[:20]
    print("  status:", olx.get("status"), "chars:", olx.get("n_chars"))
    for k, v in olx.get("license_matches", {}).items():
        print("  LIC:", v)
    for l in olx.get("text_lines", [])[:16]:
        print("  |", l[:200].encode("ascii", "replace").decode("ascii"))
    print("  files:", olx.get("files_mentioned"))
res["olx"] = olx

# ---------- thoi gian xu ly jobs.tsv ----------
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
full_est = 1092096 / (n / dt)
res["timings"] = {
    "jobs_tsv_200k_rows": {"rows": n, "sec": round(dt, 2), "rows_per_sec": round(n / dt)},
    "jobs_tsv_estimated_full_sec": round(full_est, 1),
    "jobs_tsv_estimated_full_min": round(full_est / 60, 1),
    "apps_tsv_full_sec": 1.93,
    "note": "do tren may 12 luong; RAM kha dung luc do ~3,9 GB",
}
print(f"\njobs.tsv: 200k dong / {dt:.2f}s -> toan bo ~{full_est:.0f}s = {full_est/60:.1f} phut")

with open(OUT / "t5_olx_and_timing.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("done")
