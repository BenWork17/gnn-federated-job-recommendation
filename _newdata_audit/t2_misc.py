# -*- coding: utf-8 -*-
"""t2: Lightcast Open Skills + JobHop README + ESCO Groups."""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}


def gett(u, timeout=90):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


print("=== Lightcast Open Skills ===")
for q in ["open-skills", "lightcast open skills", "skills-api"]:
    t = gett(f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}", 60)
    if t.startswith("ERR"):
        print(" ", q, t)
        continue
    try:
        j = json.loads(t)
        for it in (j.get("items") or [])[:8]:
            print("  ", it["full_name"], "|", (it.get("description") or "")[:90], "|", (it.get("license") or {}).get("spdx_id"))
    except Exception as e:
        print("  ", q, "parse err", t[:200])

print()
print("=== JobHop README ===")
t = gett("https://huggingface.co/datasets/aida-ugent/JobHop/resolve/main/README.md", 90)
print(t[:4000] if not t.startswith("ERR") else t)

print()
print("=== JobHop ESCO Groups folder ===")
t = gett("https://huggingface.co/api/datasets/aida-ugent/JobHop/tree/main?recursive=true", 60)
if not t.startswith("ERR"):
    try:
        j = json.loads(t)
        for it in j:
            print("  ", it.get("type"), it.get("path"), it.get("size"))
    except Exception as e:
        print("  parse err", e)
else:
    print(t)
