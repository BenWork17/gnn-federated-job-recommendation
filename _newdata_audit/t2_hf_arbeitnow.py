"""t2: tim mirror HuggingFace cua LinkedIn jobs dataset + kiem tra Arbeitnow do sau phan trang."""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def get(u, timeout=60):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


print("== HF search: linkedin jobs ==")
for q in ["linkedin jobs skills", "linkedin job postings", "job skills 2024"]:
    try:
        j = get(f"https://huggingface.co/api/datasets?search={urllib.parse.quote(q)}&limit=15&full=false")
        print(f"-- q={q!r}")
        for d in j:
            print("   ", d.get("id"), "| dl:", d.get("downloads"), "|", d.get("lastModified", "")[:10])
    except Exception as e:
        print(q, "ERR", e)

print()
print("== Arbeitnow: do sau phan trang ==")
page = 1
total = 0
last_page_with_data = 0
while page <= 60:
    try:
        j = get(f"https://www.arbeitnow.com/api/job-board-api?page={page}", timeout=45)
        n = len(j.get("data") or [])
    except Exception as e:
        print("  stop at page", page, "err", type(e).__name__, e)
        break
    if n == 0:
        print("  page", page, "EMPTY")
        break
    total += n
    last_page_with_data = page
    if page % 10 == 0:
        print(f"  page {page}: n={n}, cumulative={total}")
    page += 1
print("  last page with data:", last_page_with_data, "approx total items:", total)
