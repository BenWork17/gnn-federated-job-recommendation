"""t5: TU KIEM CHUNG nhom 3 repo "job-postings-applications" — ban SUA.

Lan truoc bi lay nham file AppleDouble (._applications.csv) va loi encoding console.
Lan nay:
  - chi lay data/<name>.csv (bo qua ._)
  - bam SHA-256 tung file -> so sanh TRUNG BYTE giua 3 repo
  - dem dong tung bang
  - in categorical + vai dong mau (qua file JSON, khong in console de tranh cp1252)
"""
import csv
import hashlib
import io
import json
import urllib.error
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit\t5_verify")
REPOS = [
    "mindweave/job-postings-applications",
    "Arivalagan2025/job-postings-applications",
    "kunkrm/job-postings-applications",
]
TABLES = ["applications", "candidates", "companies", "jobs", "interviews", "offers"]


def fetch_bytes(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


res = {"repos": {}, "hash_comparison": {}, "row_counts": {}, "samples": {}}
for repo in REPOS:
    info = json.loads(fetch_bytes(f"https://huggingface.co/api/datasets/{repo}").decode())
    card = info.get("cardData") or {}
    res["repos"][repo] = {
        "created": info.get("createdAt"),
        "lastModified": info.get("lastModified"),
        "downloads": info.get("downloads"),
        "likes": info.get("likes"),
        "license": card.get("license"),
    }
    print(f"== {repo}: created={info.get('createdAt')} downloads={info.get('downloads')} "
          f"license={card.get('license')}")

    hashes, counts, samples = {}, {}, {}
    for t in TABLES:
        url = f"https://huggingface.co/datasets/{repo}/resolve/main/data/{t}.csv"
        try:
            b = fetch_bytes(url)
        except urllib.error.HTTPError as e:
            hashes[t] = f"HTTP {e.code}"
            continue
        except Exception as e:
            hashes[t] = f"ERR {str(e)[:60]}"
            continue
        hashes[t] = hashlib.sha256(b).hexdigest()
        txt = b.decode("utf-8", "replace")
        rd = list(csv.reader(io.StringIO(txt)))
        counts[t] = len(rd) - 1 if rd else 0
        if rd:
            samples[t] = {"header": rd[0], "first_row": rd[1] if len(rd) > 1 else None}
    res["hash_comparison"][repo] = hashes
    res["row_counts"][repo] = counts
    res["samples"][repo] = samples
    print(f"   rows: {counts}")

# so sanh hash
all_hashes = {}
for repo in REPOS:
    for t, h in res["hash_comparison"].get(repo, {}).items():
        all_hashes.setdefault(t, []).append(h)

identical = {}
for t, hs in all_hashes.items():
    identical[t] = {"n_repos": len(hs), "n_distinct_hashes": len(set(hs)),
                    "all_identical": len(set(hs)) == 1 and len(hs) > 1}
res["identical_files"] = identical
print("\n=== TRUNG BYTE GIUA 3 REPO? ===")
for t, v in identical.items():
    print(f"  {t:12s}: {v['n_repos']} repo, {v['n_distinct_hashes']} hash khac nhau "
          f"-> giong het: {v['all_identical']}")

# kiem tra chat luong du lieu tong hop
app = res["samples"].get(REPOS[0], {}).get("applications")
if app:
    print("\n=== applications header:", app["header"])
    print("    first row:", app["first_row"])

# doc toan bo applications cua repo dau de kiem categorical + score
try:
    b = fetch_bytes(f"https://huggingface.co/datasets/{REPOS[0]}/resolve/main/data/applications.csv")
    rd = list(csv.reader(io.StringIO(b.decode("utf-8", "replace"))))
    h = rd[0]
    body = rd[1:]
    cat = {}
    for col in h:
        i = h.index(col)
        vals = [r[i] for r in body if i < len(r)]
        d = len(set(vals))
        if d <= 12:
            cat[col] = {"distinct": d, "values": sorted(set(vals))[:12]}
    res["categorical_applications"] = cat
    print("\n=== categorical (applications) ===")
    for k, v in cat.items():
        print(f"   {k}: {v['distinct']} gia tri {v['values'][:6]}")
    # score distribution
    if "score" in h:
        i = h.index("score")
        try:
            vals = sorted(float(r[i]) for r in body if i < len(r) and r[i].strip())
            n = len(vals)
            res["score_stats"] = {
                "n": n, "min": vals[0], "max": vals[-1],
                "mean": round(sum(vals) / n, 4),
                "distinct": len(set(vals)),
                "deciles": [vals[int(q * (n - 1))] for q in [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0]],
            }
            print(f"\n=== score: n={n} min={vals[0]:.3f} max={vals[-1]:.3f} "
                  f"mean={sum(vals)/n:.4f} distinct={len(set(vals))}")
            print(f"    deciles: {[round(x,3) for x in res['score_stats']['deciles']]}")
        except Exception as e:
            print("score err", e)
except Exception as e:
    print("read applications err", str(e)[:150])

with open(OUT / "t5_synthetic_check.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("\ndone -> t5_synthetic_check.json")
