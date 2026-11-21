"""t4: doc trang RecSys Challenge 2017 + README RecoHut xing de kiem so lieu XING.

Khong tin tri nho: tai trang va grep so lieu. In ra cac dong chua so lieu.
"""
import json
import re
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit/t4_verify")
OUT.mkdir(parents=True, exist_ok=True)


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


res = {}

# 1) trang challenge 2017
html = get("https://recsyschallenge.com/2017/")
(OUT / "c2017_home.html").write_text(html, encoding="utf-8")
txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
txt = re.sub(r"<[^>]+>", "\n", txt)
lines = [l.strip() for l in txt.split("\n") if l.strip()]
res["c2017_n_lines"] = len(lines)
kw = re.compile(r"interaction|impression|user|item|job|dataset|approv|XING|licen|download|"
                r"million|\d{3}[.,]\d{3}|\d{6,}", re.I)
hits = [l for l in lines if kw.search(l)]
res["c2017_hits"] = hits[:80]
print("=== c2017 page hits ===")
for h in hits[:80]:
    print("-", h[:300])

# 2) README RecoHut xing
rd = get("https://cdn.jsdelivr.net/gh/RecoHut-Datasets/xing@main/README.md")
(OUT / "recohut_xing_README.md").write_text(rd, encoding="utf-8")
res["recohut_readme"] = rd
print("\n=== RecoHut xing README ===")
print(rd[:2000])

# 3) file list
tree = get("https://data.jsdelivr.com/v1/packages/gh/RecoHut-Datasets/xing@main?structure=flat")
tj = json.loads(tree)
res["recohut_files"] = [(f["name"], f["size"]) for f in tj.get("files", [])]
print("\n=== RecoHut xing files ===")
for n, s in res["recohut_files"]:
    print(f"{s:>12} {n}")

# 4) 2016 training dataset md
md = get("https://raw.githubusercontent.com/recsyschallenge/2016/master/TrainingDataset.md")
(OUT / "c2016_TrainingDataset.md").write_text(md, encoding="utf-8")
res["c2016_md_lines"] = md.count("\n")
print("\n=== 2016 TrainingDataset.md (first 2500) ===")
print(md[:2500])

with open(OUT / "t4_xing_docs.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("\ndone")
