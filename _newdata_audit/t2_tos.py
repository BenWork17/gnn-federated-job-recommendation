# -*- coding: utf-8 -*-
"""t2: doc dieu khoan Adzuna + USAJobs (dieu kien luu tru / giay phep)."""
import re
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121"}


def strip(h):
    h = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", h)


def g(u):
    try:
        return strip(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90)
                     .read().decode("utf-8", "replace"))
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


for name, u, kws in [
    ("Adzuna ToS", "https://www.adzuna.com/terms", ["attribution", "store", "cache", "research", "licen", "API"]),
    ("USAJobs ToS", "https://developer.usajobs.gov/terms-of-service", ["public domain", "free", "attribution", "rate", "API key"]),
    ("USAJobs API-Reference", "https://developer.usajobs.gov/API-Reference/", ["Authorization-ApiKey", "API Key", "email"]),
]:
    t = g(u)
    print("=" * 70)
    print(name, "| len", len(t), "|", t[:80])
    if t.startswith("ERR"):
        continue
    for kw in kws:
        i = t.lower().find(kw.lower())
        print(f"  [{kw}] idx={i}", "|", t[max(0, i - 200):i + 400] if i > 0 else "")
