"""t2: thu POST len Kaggle DatasetService de lay danh sach file (khong auth)."""
import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json",
      "Accept": "application/json", "Origin": "https://www.kaggle.com",
      "Referer": "https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024"}

BODY = {"datasetRef": "asaniczka/1-3m-linkedin-jobs-and-skills-2024"}
URLS = [
    "https://www.kaggle.com/api/i/datasets.DatasetService/GetDatasetFiles",
    "https://www.kaggle.com/api/i/datasets.DatasetService/GetDatasetMetadata",
    "https://www.kaggle.com/api/i/datasets.DatasetService/GetDataset",
    "https://www.kaggle.com/api/i/datasets.DatasetService/ListDatasetFiles",
]
for u in URLS:
    try:
        req = urllib.request.Request(u, data=json.dumps(BODY).encode(), headers=UA, method="POST")
        with urllib.request.urlopen(req, timeout=45) as r:
            b = r.read()
        print(u, "->", r.status, b[:600])
    except urllib.error.HTTPError as e:
        print(u, "-> HTTP", e.code, e.read()[:200])
    except Exception as e:
        print(u, "-> ERR", type(e).__name__, e)
