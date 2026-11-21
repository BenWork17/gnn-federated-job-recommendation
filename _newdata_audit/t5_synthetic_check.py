"""t5: TU KIEM CHUNG nhom 3 repo "job-postings-applications" (captain nghi tong hop).

Vai tro cua toi la KHONG TIN mo ta — ke ca mo ta cua captain. Do lai:
  1. 3 repo co dung cung schema + cung so dong khong?
  2. Dong dau co TRUNG TUNG BYTE khong?
  3. Ten cong ty/nguoi co kieu Faker khong?
  4. Categorical co qua sach khong?
  5. Cot score co phan bo deu vo nghia khong?
"""
import json
import re
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


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


res = {}
for repo in REPOS:
    d = {"repo": repo}
    try:
        meta = json.loads(get(f"https://huggingface.co/api/datasets/{repo}"))
        d["created"] = meta.get("createdAt")
        d["lastModified"] = meta.get("lastModified")
        d["downloads"] = meta.get("downloads")
        d["likes"] = meta.get("likes")
        d["license"] = (meta.get("cardData") or {}).get("license")
        d["files"] = [(s["rfilename"], s.get("size")) for s in (meta.get("siblings") or [])]
        print(f"== {repo}")
        print(f"   created={d['created']} downloads={d['downloads']} license={d['license']}")
        for f, s in d["files"]:
            print(f"     {str(s):>12} {f}")
    except Exception as e:
        d["err"] = type(e).__name__ + ": " + str(e)[:150]
        print(f"== {repo} ERR {str(e)[:120]}")
    res[repo] = d

# doc dong dau cua bang applications trong tung repo
samples = {}
for repo in REPOS:
    files = [f for f, _ in res.get(repo, {}).get("files", []) if "application" in f.lower()]
    if not files:
        continue
    f = files[0]
    try:
        url = f"https://huggingface.co/datasets/{repo}/resolve/main/{f}"
        req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-1200"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
        samples[repo] = {"file": f, "head": body[:1200]}
        print(f"== {repo} / {f} head:")
        print("   " + body[:400].replace("\n", " | "))
    except Exception as e:
        samples[repo] = {"file": f, "err": str(e)[:120]}
        print(f"== {repo} sample ERR {str(e)[:120]}")

# so sanh dong dau giua cac repo
heads = {k: v.get("head", "") for k, v in samples.items()}
uniq = set(re.sub(r"\s+", " ", h).strip() for h in heads.values() if h)
res["_comparison"] = {
    "n_repos_with_sample": len(heads),
    "n_distinct_first_rows": len(uniq),
    "identical_across_repos": len(uniq) == 1 and len(heads) > 1,
    "first_rows": {k: v[:300] for k, v in heads.items()},
}
print("\n=== KET LUAN ===")
print("so repo lay duoc mau:", len(heads))
print("so dong dau KHAC NHAU:", len(uniq))
print("trung nhau 100%:", res["_comparison"]["identical_across_repos"])

with open(OUT / "t5_synthetic_check.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("done")
