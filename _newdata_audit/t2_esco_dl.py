"""t2: thu tai ESCO CSV qua cong EU Open Data Portal + xac minh cot dataset Kaggle #2."""
import json
import re
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121"}


def fetch(u, timeout=120, limit=None):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read() if limit is None else r.read(limit)
            return {"ok": True, "status": r.status, "body": b, "ct": r.headers.get("Content-Type"),
                    "cl": r.headers.get("Content-Length"), "url": r.geturl()}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}"}


print("=== A) data.europa.eu ESCO dataset page ===")
for u in ["https://data.europa.eu/data/datasets/esco-classification",
          "https://data.europa.eu/api/hub/search/datasets/esco-classification"]:
    r = fetch(u, timeout=60, limit=200000)
    print(" ", u, "->", {k: v for k, v in r.items() if k not in ("body",)})
    if r["ok"]:
        t = r["body"].decode("utf-8", "replace")
        urls = sorted(set(re.findall(r"https://[^\"'\s<>]+\.(?:csv|zip|rdf|ttl)", t)))
        print("    distribution urls:", urls[:10])
        print("    license mentions:", re.findall(r"(CC[ -]BY[^\"<,]{0,20}|EUPL[^\"<,]{0,10}|licen[cs]e[^\"<]{0,40})", t, re.I)[:8])

print()
print("=== B) ravindrasinghrana job-description-dataset: cot that qua jina ===")
r = fetch("https://r.jina.ai/https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset", timeout=120)
if r["ok"]:
    t = r["body"].decode("utf-8", "replace")
    print("len", len(t))
    for kw in ["Skills", "Responsibilities", "Benefits", "Job Title", "Job Description", "Qualifications", "Company Size", "Preference"]:
        i = t.find(kw)
        print(f"  {kw!r}: idx={i}")
    # in phan data dictionary neu co
    i = t.find("Data Card")
    print("--- first 3000 chars ---")
    print(t[:3000])
else:
    print("fail", r)
