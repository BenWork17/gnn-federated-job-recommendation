# -*- coding: utf-8 -*-
"""t2: (1) Lightcast open skills that, (2) LinkedIn taxonomy public?, (3) O*NET<->ESCO crosswalk."""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121"}


def gett(u, timeout=90):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return f"ERR HTTP {e.code}"
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


def strip(h):
    h = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", h)


print("=== 1) Lightcast open skills tren GitHub ===")
for q in ["lightcast", "lightcast-io"]:
    t = gett(f"https://api.github.com/search/repositories?q={q}+in:name&per_page=10", 60)
    if t.startswith("ERR"):
        print(" ", q, t); continue
    try:
        j = json.loads(t)
        for it in (j.get("items") or [])[:10]:
            print("  ", it["full_name"], "|", (it.get("description") or "")[:80], "|", (it.get("license") or {}).get("spdx_id"), "|★", it.get("stargazers_count"))
    except Exception as e:
        print("  parse err", t[:200])

print()
print("=== 2) LinkedIn skills taxonomy co public khong? ===")
t = strip(gett("https://learn.microsoft.com/en-us/linkedin/talent/", 60))
print("  learn.microsoft.com/linkedin/talent ->", t[:400])
for u in ["https://developer.linkedin.com/docs/v2/skills", "https://learn.microsoft.com/en-us/linkedin/shared/references/reference-tables/skills"]:
    t = strip(gett(u, 60))
    print(" ", u[-55:], "->", t[:300])

print()
print("=== 3) O*NET <-> ESCO crosswalk ===")
t = strip(gett("https://esco.ec.europa.eu/en/about-esco/escopedia/escopedia/crosswalk-between-onet-and-esco", 90))
i = t.find("The crosswalk")
j = t.find("O*NET")
print("  len", len(t), "| 'O*NET' first idx", j)
k = t.find("Crosswalk between O", 2000)
print(t[max(0, k):k + 2500] if k > 0 else t[j:j + 2500])
