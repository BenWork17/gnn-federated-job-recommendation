"""t2: 3 viec: (1) tim mirror asaniczka tren HF, (2) ESCO tren EU ODP, (3) crosswalk O*NET."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121"}


def getj(u, timeout=60):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def gett(u, timeout=90):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


print("=== 1) HF full-text search 'got_summary' (cot dac trung cua asaniczka) ===")
for q in ["got_summary", "linkedin_job_postings", "search_city"]:
    try:
        j = getj(f"https://huggingface.co/api/datasets?search={urllib.parse.quote(q)}&limit=20")
        print(f"  {q!r}: {[d.get('id') for d in j]}")
    except Exception as e:
        print("  ", q, "ERR", e)

print()
print("=== 2) EU Open Data Portal: tim ESCO ===")
for u in ["https://data.europa.eu/api/hub/search/search?q=ESCO%20classification&limit=5",
          "https://data.europa.eu/api/hub/search/search?q=esco&filters=%7B%7D&limit=5"]:
    t = gett(u, timeout=60)
    if t.startswith("ERR"):
        print("  ", u, "->", t)
        continue
    print("  ", u, "-> len", len(t))
    try:
        j = json.loads(t)
        for r in (j.get("result", {}).get("results") or [])[:6]:
            ti = r.get("title")
            print("     ", r.get("id"), "|", ti if isinstance(ti, str) else (ti or {}).get("en"))
    except Exception as e:
        print("     parse err", e, t[:300])

print()
print("=== 3) crosswalk O*NET-ESCO ===")
t = gett("https://esco.ec.europa.eu/en/about-esco/escopedia/escopedia/crosswalk-between-onet-and-esco", 90)
i = t.find("Crosswalk between O")
body = t[t.find("Crosswalk between O\\*NET and ESCO", 3000):][:3500] if i > 0 else t[:3000]
body = re.sub(r"<[^>]+>", " ", body)
body = re.sub(r"\s+", " ", body)
print(body[:2500])
