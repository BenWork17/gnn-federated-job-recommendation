"""t2: xac minh (1) danh sach file Kaggle asaniczka, (2) link tai ESCO CSV/RDF truc tiep."""
import json
import re
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121"}


def fetch(u, timeout=120):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"ok": True, "status": r.status, "body": r.read(), "ct": r.headers.get("Content-Type"),
                    "cl": r.headers.get("Content-Length")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}"}


print("=== 1) Kaggle asaniczka: ten file qua jina ===")
r = fetch("https://r.jina.ai/https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024")
if r["ok"]:
    t = r["body"].decode("utf-8", "replace")
    csvs = sorted(set(re.findall(r"([A-Za-z0-9_\-]+\.csv)", t)))
    print("  .csv names:", csvs)
    for kw in ["job_skills", "job_summary", "linkedin_job_postings", "About this file", "split("]:
        i = t.find(kw)
        print(f"  '{kw}' -> idx {i}")
        if i > 0:
            print("     ...", t[max(0, i - 200):i + 350].replace("\n", " ")[:520])
else:
    print("  jina failed", r)

print()
print("=== 2) ESCO: thu link tai CSV/RDF truc tiep ===")
CAND = [
    "https://esco.ec.europa.eu/sites/default/files/esco_dataset/ESCO%20dataset%20-%20v1.2.1%20-%20classification%20-%20en.csv.zip",
    "https://esco.ec.europa.eu/sites/default/files/esco_dataset/1.2.1/ESCO%20dataset%20-%20v1.2.1%20-%20classification%20-%20en.csv.zip",
    "https://ec.europa.eu/esco/api/resource/taxonomy?uri=http://data.europa.eu/esco/concept-scheme/occupations&language=en",
]
for u in CAND:
    r = fetch(u, timeout=60)
    print(" ", u[:110], "->", {k: v for k, v in r.items() if k != "body"})
