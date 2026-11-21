"""t2: nhieu duong lay metadata file Kaggle khong can auth."""
import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
      "Accept": "application/json"}


def t(u):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        try:
            return {"ok": True, "status": r.status, "json": json.loads(b.decode("utf-8"))}
        except Exception:
            return {"ok": True, "status": r.status, "text": b[:400].decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "text": e.read()[:200].decode("utf-8", "replace")}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}"}


CANDS = [
    "https://www.kaggle.com/api/v1/datasets/list?user=asaniczka&pageSize=20",
    "https://www.kaggle.com/api/v1/datasets/list?search=1.3M%20Linkedin&pageSize=10",
    "https://www.kaggle.com/api/v1/datasets/view/asaniczka/1-3m-linkedin-jobs-and-skills-2024?includeFiles=true",
    "https://www.kaggle.com/api/i/datasets.DatasetService/DatasetApiService/GetDataset",
    "https://www.kaggle.com/api/v1/datasets/metadata/asaniczka/1-3m-linkedin-jobs-and-skills-2024",
]
for u in CANDS:
    r = t(u)
    print(u)
    if r.get("json") is not None:
        j = r["json"]
        if isinstance(j, list):
            print("   list len", len(j))
            for d in j[:15]:
                print("     ", d.get("ref") or d.get("title"), d.get("totalBytes"), d.get("licenseName"))
        else:
            print("   keys:", list(j.keys())[:30])
            print("   files:", json.dumps(j.get("files") or j.get("datasetFiles"))[:400])
    else:
        print("   ", json.dumps({k: v for k, v in r.items() if k != "json"})[:400])
    print()
