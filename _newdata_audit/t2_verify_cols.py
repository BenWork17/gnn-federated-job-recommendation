"""t2: thu Bing/Startpage + HF de xac minh cot that cua 2 dataset Kaggle."""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"}


def fetch(u, timeout=60):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


def get(u, timeout=60):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


print("== Bing ==")
h = fetch("https://www.bing.com/search?q=" + urllib.parse.quote('"job_skills" "got_summary" linkedin kaggle dataframe columns'))
print("len", len(h), h[:120].replace("\n", " "))
if not h.startswith("ERR"):
    for m in re.findall(r"<h2><a href=\"(http[^\"]+)\"[^>]*>(.*?)</a>", h)[:8]:
        print("  ", m[0][:110], "|", re.sub("<[^>]+>", "", m[1])[:90])

print()
print("== HF: datasets co ten lien quan job description ==")
for q in ["job description", "job posting", "recruitment"]:
    try:
        j = get(f"https://huggingface.co/api/datasets?search={urllib.parse.quote(q)}&limit=30")
        print(f"-- {q!r}: {len(j)}")
        for d in j[:30]:
            print("     ", d.get("id"), d.get("downloads"))
    except Exception as e:
        print(q, "ERR", e)
