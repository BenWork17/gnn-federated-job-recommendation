"""t5: SUA SAI tu t4 — Kaggle 404 la do CHAN UA, khong phai dataset bi xoa.

Phep doi chung o t5_control.py da chung minh: cung URL
  https://www.kaggle.com/datasets/olxdatascience/olx-jobs-interactions
  - python UA  -> 404
  - browser UA -> 200, 20.549 chars
=> phai doc lai bang browser UA moi biet license THAT va biet file co ton tai khong.

Viec:
  A. OLX: doc license that tren trang dataset.
  B. arshkon: doc danh sach FILE that (co jobs/job_skills.csv khong?), va license.
  C. Zhaopin: doc license that (trang Tianchi).
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(r"_newdata_audit/t5_verify")
OUT.mkdir(parents=True, exist_ok=True)
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url, timeout=60, nbytes=3_000_000):
    rec = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(nbytes).decode("utf-8", "replace")
        rec.update(status=200, n_chars=len(body), body=body)
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, body="")
    except Exception as e:
        rec.update(status=None, err=type(e).__name__ + ": " + str(e)[:150], body="")
    return rec


def text_of(html):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "\n", t)
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


res = {}

# ---------- A. OLX ----------
r = fetch("https://www.kaggle.com/datasets/olxdatascience/olx-jobs-interactions")
olx = {"status": r["status"], "n_chars": r.get("n_chars")}
if r["body"]:
    b = r["body"]
    (OUT / "olx_page.html").write_text(b, encoding="utf-8")
    # Kaggle nhung license trong JSON state
    for pat in [r'"licenseName"\s*:\s*"([^"]{1,80})"',
                r'"license"\s*:\s*\{[^}]{0,200}?"name"\s*:\s*"([^"]{1,80})"',
                r'"licenseUrl"\s*:\s*"([^"]{1,200})"',
                r'"name"\s*:\s*"(CC[^"]{1,60}|MIT|Apache[^"]{0,30}|ODC[^"]{0,40}|Other)"']:
        m = re.findall(pat, b)
        if m:
            olx.setdefault("license_matches", {})[pat[:30]] = sorted(set(m))[:6]
    txt = text_of(b)
    hits = [l for l in txt.split("\n")
            if re.search(r"licen|commercial|research|academic|CC0|ODbL|attribution|"
                         r"attribution|Other|Dataset Files|interactions\.csv", l, re.I)]
    olx["text_lines"] = hits[:25]
    olx["mentions_files"] = re.findall(r"[\w./-]+\.(?:csv|txt|zip|parquet)", b)[:20]
    print("== OLX page", r["status"], "chars", r.get("n_chars"))
    for k, v in olx.get("license_matches", {}).items():
        print("   LIC:", v)
    for l in hits[:14]:
        print("   |", l[:200].encode("ascii", "replace").decode("ascii"))
res["olx"] = olx

# ---------- B. arshkon ----------
r = fetch("https://www.kaggle.com/datasets/arshkon/linkedin-job-postings")
ar = {"status": r["status"], "n_chars": r.get("n_chars")}
if r["body"]:
    b = r["body"]
    (OUT / "arshkon_page.html").write_text(b, encoding="utf-8")
    ar["files_mentioned"] = sorted(set(re.findall(r"[\w./-]+\.(?:csv|zip|parquet|json)", b)))[:40]
    for pat in [r'"licenseName"\s*:\s*"([^"]{1,80})"',
                r'"licenseUrl"\s*:\s*"([^"]{1,200})"']:
        m = re.findall(pat, b)
        if m:
            ar.setdefault("license_matches", {})[pat[:20]] = sorted(set(m))[:6]
    txt = text_of(b)
    ar["has_job_skills"] = "job_skills" in b
    ar["text_lines"] = [l for l in txt.split("\n")
                        if re.search(r"job_skills|skills\.csv|licen|CC BY|attribution", l, re.I)][:15]
    print("== arshkon page", r["status"], "chars", r.get("n_chars"),
          "| job_skills mentioned:", ar["has_job_skills"])
    for l in ar["text_lines"][:10]:
        print("   |", l[:200].encode("ascii", "replace").decode("ascii"))
res["arshkon"] = ar

# ---------- C. Kaggle API voi browser UA (co the van 404 vi can auth) ----------
for name, url in [
    ("olx_view", "https://www.kaggle.com/api/v1/datasets/view/olxdatascience/olx-jobs-interactions"),
    ("arshkon_view", "https://www.kaggle.com/api/v1/datasets/view/arshkon/linkedin-job-postings"),
    ("arshkon_files", "https://www.kaggle.com/api/v1/datasets/list/arshkon/linkedin-job-postings"),
]:
    rr = fetch(url, nbytes=500000)
    rec = {"status": rr["status"], "n_chars": rr.get("n_chars")}
    if rr["body"]:
        rec["head"] = rr["body"][:500]
        try:
            j = json.loads(rr["body"])
            rec["json_keys"] = list(j)[:20] if isinstance(j, dict) else f"list len {len(j)}"
        except Exception:
            pass
    res.setdefault("kaggle_api_browser_ua", {})[name] = rec
    print(f"== API {name}: {rr['status']} chars={rr.get('n_chars')}")

with open(OUT / "t5_license_real.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("done")
