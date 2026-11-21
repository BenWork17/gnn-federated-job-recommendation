# -*- coding: utf-8 -*-
"""t2: (a) licence ESCO chinh thuc, (b) Lightcast Open Skills, (c) cot dataset ravindra."""
import json
import re
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121"}


def gett(u, timeout=90):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


def strip(h):
    h = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"[ \t]+", " ", h)


print("=== (a) ESCO licence: FAQ ===")
t = strip(gett("https://esco.ec.europa.eu/en/about-esco/faq"))
for kw in ["licen", "CC BY", "Creative Commons", "free of charge", "reuse", "re-use"]:
    for m in re.finditer(kw, t, re.I):
        s = max(0, m.start() - 350)
        print(f"  [{kw}] ...", t[s:m.start() + 500].replace("\n", " "))
        break

print()
print("=== (a2) ESCO legal notice ===")
t2 = strip(gett("https://esco.ec.europa.eu/en/legal-notice"))
i = t2.lower().find("licen")
print(" len", len(t2), "| licen idx", i)
if i > 0:
    print(t2[max(0, i - 600):i + 900])

print()
print("=== (b) Lightcast Open Skills (GitHub) ===")
for u in ["https://api.github.com/repos/lightcast-io/open-skills",
          "https://api.github.com/repos/lightcast-io/graph-open-skills"]:
    tt = gett(u, 60)
    print(" ", u, "->", tt[:300].replace("\n", " "))
