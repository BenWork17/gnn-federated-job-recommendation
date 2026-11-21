"""t4: lay danh sach title cua LinkedIn postings (mirror CONG KHAI cua arshkon).

Kaggle API khong auth tra 404 (da kiem). Mirror cong khai: HF datastax/linkedin_job_listings
(516 MB, t1 da do 123.849 dong). O day CHI can cot 'title' -> uu tien file parquet neu co,
khong thi stream CSV va chi giu cot title.
"""
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit/t4_verify")
REPO = "datastax/linkedin_job_listings"

info = json.load(urllib.request.urlopen(
    urllib.request.Request(f"https://huggingface.co/api/datasets/{REPO}", headers=UA), timeout=60))
sibs = [s["rfilename"] for s in info.get("siblings", [])]
print("files:", sibs)

dest_titles = OUT / "arshkon_titles.txt"
if dest_titles.exists() and dest_titles.stat().st_size > 1000:
    print("already have", dest_titles.stat().st_size)
    sys.exit(0)

cand = [s for s in sibs if s.endswith(".parquet")]
if cand:
    url = f"https://huggingface.co/datasets/{REPO}/resolve/main/{cand[0]}"
    p = OUT / "datastax.parquet"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900) as r, open(p, "wb") as f:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            f.write(c)
    print("parquet bytes:", p.stat().st_size)
    pf = pq.ParquetFile(p)
    print("rows:", pf.metadata.num_rows, "cols:", pf.schema_arrow.names)
    titles = pf.read(columns=["title"])["title"].to_pylist()
else:
    csvname = [s for s in sibs if s.endswith(".csv")][0]
    url = f"https://huggingface.co/datasets/{REPO}/resolve/main/{csvname}"
    print("streaming csv:", url)
    titles = []
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=1800) as r:
        rd = csv.reader(io.TextIOWrapper(r, encoding="utf-8", errors="replace", newline=""))
        h = next(rd)
        it = h.index("title")
        print("header:", h)
        for row in rd:
            if it < len(row):
                titles.append(row[it])

dest_titles.write_text("\n".join(t for t in titles if isinstance(t, str)), encoding="utf-8")
print("titles written:", len(titles), "bytes:", dest_titles.stat().st_size)
print("sample:", [t for t in titles[:10]])
