"""t4: liet ke file that cua 2 repo Djinni qua API repo info (siblings)."""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
out = {}
for repo in [
    "lang-uk/recruitment-dataset-job-descriptions-english",
    "lang-uk/recruitment-dataset-candidate-profiles-english",
]:
    url = f"https://huggingface.co/api/datasets/{repo}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        d = json.load(r)
    sib = [(s["rfilename"], s.get("size")) for s in d.get("siblings", [])]
    out[repo] = {
        "siblings": sib,
        "cardData": d.get("cardData"),
        "lastModified": d.get("lastModified"),
        "downloads": d.get("downloads"),
    }
    print(repo)
    for n, s in sib:
        print(f"   {str(s):>12} {n}")
    print("   license:", (d.get("cardData") or {}).get("license"))

with open(r"_newdata_audit/t4_verify/t4_djinni_files.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
