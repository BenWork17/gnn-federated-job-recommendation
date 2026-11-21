"""t2: thu cac endpoint kaggle api khac de lay danh sach file."""
import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def t(u):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        try:
            j = json.loads(b.decode("utf-8"))
            return {"ok": True, "status": r.status, "json": j}
        except Exception:
            return {"ok": True, "status": r.status, "text": b[:300].decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code}
    except Exception as e:
        return {"ok": False, "err": str(e)}


CANDS = [
    "https://www.kaggle.com/api/v1/datasets/data-view/4418374",
    "https://www.kaggle.com/api/v1/datasets/view/4418374",
    "https://www.kaggle.com/api/v1/datasets/data-list/4418374",
    "https://www.kaggle.com/api/v1/datasets/data-summary/asaniczka/1-3m-linkedin-jobs-and-skills-2024",
    "https://www.kaggle.com/api/v1/datasets/data-list/asaniczka/1-3m-linkedin-jobs-and-skills-2024/versions/2",
    "https://www.kaggle.com/api/v1/datasets/view/asaniczka/1-3m-linkedin-jobs-and-skills-2024/versions/1",
    "https://www.kaggle.com/api/i/datasets.DatasetService/GetDataset",
]
for u in CANDS:
    r = t(u)
    print(u, "->", json.dumps({k: v for k, v in r.items() if k != "json"}, ensure_ascii=False))
    if r.get("json"):
        j = r["json"]
        if isinstance(j, dict):
            print("   keys:", list(j.keys())[:20])
            for k in ("datasetFiles", "files"):
                if k in j:
                    for f in j[k]:
                        print("   FILE:", f.get("name"), f.get("totalBytes"), f.get("columns"))
        else:
            print("   list len:", len(j), json.dumps(j)[:300])
    print()
