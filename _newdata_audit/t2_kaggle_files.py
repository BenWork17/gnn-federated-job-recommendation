"""t2: liet ke file cua dataset Kaggle qua nhieu endpoint khac nhau."""
import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def try_url(u, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    try:
        req = urllib.request.Request(u, headers=h)
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            return {"ok": True, "status": r.status, "len": len(body),
                    "json": json.loads(body.decode("utf-8")) if body[:1] in b"{[" else None,
                    "text": body[:500].decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "text": e.read()[:200].decode("utf-8", "replace")}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}"}


ENDPOINTS = [
    "https://www.kaggle.com/api/v1/datasets/list/asaniczka/1-3m-linkedin-jobs-and-skills-2024",
    "https://www.kaggle.com/api/v1/datasets/data-view/asaniczka/1-3m-linkedin-jobs-and-skills-2024",
    "https://www.kaggle.com/api/v1/datasets/view/asaniczka/1-3m-linkedin-jobs-and-skills-2024/versions/2",
    "https://www.kaggle.com/api/v1/datasets/download/asaniczka/1-3m-linkedin-jobs-and-skills-2024",
    "https://www.kaggle.com/api/v1/datasets/data-list/ravindrasinghrana/job-description-dataset",
    "https://www.kaggle.com/api/v1/datasets/list/ravindrasinghrana/job-description-dataset",
]

for u in ENDPOINTS:
    r = try_url(u)
    out = {k: v for k, v in r.items() if k not in ("json", "text")}
    if r.get("json") is not None:
        j = r["json"]
        if isinstance(j, dict):
            out["json_keys"] = list(j.keys())[:25]
            for k in ("files", "datasetFiles", "versions"):
                if k in j:
                    out[k] = json.dumps(j[k])[:800]
        else:
            out["json_len"] = len(j)
            out["json_sample"] = json.dumps(j)[:600]
    else:
        out["text"] = r.get("text", "")
    print(u)
    print("  ", json.dumps(out, ensure_ascii=False)[:900])
    print()
