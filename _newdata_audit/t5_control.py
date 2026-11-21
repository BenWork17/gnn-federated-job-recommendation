"""t5: KIEM CHUNG hai ket qua DANG NGO o tren bang PHEP DOI CHUNG (control).

Nghi van 1: HF search moi truy van nhieu tu deu tra 0 -> co the do API, khong phai
            do khong co dataset. Kiem: (a) query 1 tu da biet la co ket qua
            ("linkedin"), (b) query tung tu rieng, (c) endpoint full-text khac.
Nghi van 2: Kaggle tra 404 cho MOI url -> co the do chan UA/geo, khong phai dataset bi xoa.
            Kiem: (a) kaggle.com trang chu, (b) dataset da biet TON TAI (arshkon) lam control,
            (c) thu voi UA giong trinh duyet + Accept header.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(r"_newdata_audit/t5_verify")
res = {}
UA_PY = {"User-Agent": "Mozilla/5.0"}
UA_BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def probe(url, headers=None, timeout=45, nbytes=200000):
    h = headers or UA_PY
    rec = {"url": url}
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(nbytes).decode("utf-8", "replace")
        rec["status"] = 200
        rec["n_chars"] = len(body)
        rec["body"] = body
    except urllib.error.HTTPError as e:
        rec["status"] = e.code
        rec["body"] = ""
    except Exception as e:
        rec["status"] = None
        rec["err"] = type(e).__name__ + ": " + str(e)[:150]
        rec["body"] = ""
    return rec


# ---------- A. HF search: control 1 tu ----------
res["hf_control"] = {}
for q in ["linkedin", "recruitment", "jobs", "interaction", "djinni"]:
    r = probe(f"https://huggingface.co/api/datasets?search={urllib.parse.quote(q)}&limit=100")
    ids = []
    if r["body"]:
        try:
            ids = [d.get("id") for d in json.loads(r["body"])]
        except Exception:
            pass
    res["hf_control"][q] = {"status": r["status"], "n_results": len(ids), "first5": ids[:5]}
    print(f"HF search '{q}': status={r['status']} n={len(ids)} {ids[:3]}")

# thu full-text search endpoint khac
res["hf_fulltext"] = {}
for q in ["job interaction", "recruitment interaction"]:
    u = ("https://huggingface.co/api/datasets?search=" + urllib.parse.quote(q)
         + "&limit=100&full=true&sort=downloads&direction=-1")
    r = probe(u)
    ids = []
    if r["body"]:
        try:
            ids = [d.get("id") for d in json.loads(r["body"])]
        except Exception:
            pass
    res["hf_fulltext"][q] = {"n_results": len(ids), "first5": ids[:5]}
    print(f"HF fulltext '{q}': n={len(ids)} {ids[:3]}")

# ---------- B. Kaggle: control dataset TON TAI ----------
res["kaggle_control"] = {}
CONTROLS = [
    ("homepage", "https://www.kaggle.com/"),
    ("arshkon_page", "https://www.kaggle.com/datasets/arshkon/linkedin-job-postings"),
    ("arshkon_api", "https://www.kaggle.com/api/v1/datasets/view/arshkon/linkedin-job-postings"),
    ("olx_page_py_ua", "https://www.kaggle.com/datasets/olxdatascience/olx-jobs-interactions"),
]
for name, url in CONTROLS:
    r = probe(url)
    res["kaggle_control"][name] = {"status": r["status"], "n_chars": r.get("n_chars"), "err": r.get("err")}
    print(f"Kaggle {name} [python UA]: status={r['status']} chars={r.get('n_chars')} err={r.get('err','')}")

res["kaggle_browser_ua"] = {}
for name, url in [("olx_page", "https://www.kaggle.com/datasets/olxdatascience/olx-jobs-interactions"),
                  ("arshkon_page", "https://www.kaggle.com/datasets/arshkon/linkedin-job-postings")]:
    r = probe(url, headers=UA_BROWSER)
    body = r.get("body", "")
    res["kaggle_browser_ua"][name] = {
        "status": r["status"], "n_chars": r.get("n_chars"),
        "has_404_text": ("404" in body[:4000] or "not found" in body[:4000].lower()),
        "has_dataset_word": "dataset" in body.lower(),
    }
    print(f"Kaggle {name} [browser UA]: status={r['status']} chars={r.get('n_chars')}")

with open(OUT / "t5_control.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("done")
