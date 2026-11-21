# -*- coding: utf-8 -*-
"""t2: (1) ten cot asaniczka qua github code search, (2) licence/tos USAJobs + Arbeitnow."""
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


print("=== 1) asaniczka column names: google/bing search ===")
for eng in ["https://lite.duckduckgo.com/lite/?q=",
            "https://search.marcia.cc/search?q="]:
    pass
q = urllib.parse.quote('asaniczka linkedin_job_postings.csv "got_summary" columns pandas')
for u in [f"https://lite.duckduckgo.com/lite/?q={q}", f"https://www.mojeek.com/search?q={q}"]:
    t = gett(u, 60)
    print(" ", u[:50], "->", "ERR" if t.startswith("ERR") else f"len {len(t)}")
    if t.startswith("ERR"):
        continue
    for kw in ["got_summary", "job_link", "search_city", "job_skills"]:
        i = t.find(kw)
        if i > 0:
            print(f"    {kw}: ...", strip(t[max(0, i - 300):i + 400])[:600])

print()
print("=== 1b) GitHub raw search qua jina ===")
t = gett("https://r.jina.ai/https://github.com/search?q=%22job_skills.csv%22+asaniczka&type=code", 90)
print("  ", "ERR" if t.startswith("ERR") else f"len {len(t)}")
if not t.startswith("ERR"):
    for kw in ["job_skills", "got_summary", "linkedin_job_postings"]:
        i = t.find(kw)
        print(f"    {kw} idx={i}")

print()
print("=== 2) USAJobs API terms ===")
t = strip(gett("https://developer.usajobs.gov/API-Reference/", 90))
print("  len", len(t))
for kw in ["API Key", "api key", "free", "rate limit", "attribution", "public domain", "terms"]:
    i = t.lower().find(kw.lower())
    print(f"    {kw!r} idx={i}", "|", t[max(0, i - 120):i + 260] if i > 0 else "")

print()
print("=== 3) Arbeitnow ToS ===")
t = strip(gett("https://www.arbeitnow.com/blog/job-board-api", 90))
print("  len", len(t))
for kw in ["free", "terms", "attribution", "link back", "license"]:
    i = t.lower().find(kw.lower())
    print(f"    {kw!r} idx={i}", "|", t[max(0, i - 150):i + 300] if i > 0 else "")
