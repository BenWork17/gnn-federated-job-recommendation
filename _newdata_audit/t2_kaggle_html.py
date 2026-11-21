"""t2: doc trang Kaggle HTML de tim danh sach file (embedded JSON)."""
import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
URLS = [
    "https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024",
    "https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset",
]
for u in URLS:
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        html = r.read().decode("utf-8", "replace")
    print("=" * 70)
    print(u, "html_len", len(html))
    # tim ten file .csv/.parquet/.json
    names = sorted(set(re.findall(r'"name"\s*:\s*"([^"]+\.(?:csv|parquet|json|jsonl|xlsx|zip|db|sqlite))"', html)))
    print("files found (by \"name\" key):", names)
    # tim totalBytes
    for m in re.findall(r'"totalBytes"\s*:\s*(\d+)', html)[:5]:
        print("  totalBytes:", m)
    # tim columns
    cols = re.findall(r'"columns"\s*:\s*\[([^\]]{0,400})\]', html)
    if cols:
        print("  columns entries:", cols[:3])
    # tim description/text snippet
    for key in ["descriptionPlainText", "subtitle", "usabilityRating", "licenseName"]:
        m = re.search(rf'"{key}"\s*:\s*("([^"]{{0,300}})"|([0-9.]+))', html)
        if m:
            print(f"  {key}:", m.group(0)[:320])
    # neu co blob JSON lon chua datasetVersionId
    m = re.search(r'"datasetFilesResolved"', html)
    print("  has datasetFilesResolved:", bool(m))
