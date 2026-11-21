# -*- coding: utf-8 -*-
"""t2: (1) JobHop ESCO Groups, (2) mirror ravindra job-description, (3) Adzuna docs."""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}


def gett(u, timeout=90, head_only=None):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read() if head_only is None else r.read(head_only)
            return b.decode("utf-8", "replace")
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


def getj(u, timeout=90):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


print("=== 1) JobHop 'ESCO Groups' file (515 bytes) ===")
print(gett("https://huggingface.co/datasets/aida-ugent/JobHop/resolve/main/ESCO%20Groups"))

print()
print("=== 2) mirror cua ravindrasinghrana job-description-dataset tren HF ===")
for cid in ["lof223/job_description", "jacob-hugging-face/job-descriptions", "Aneeth/job_description_7k"]:
    try:
        d = getj(f"https://datasets-server.huggingface.co/info?dataset={cid}", 60)
        for cfg, c in (d.get("dataset_info") or {}).items():
            print(f"  {cid} [{cfg}] cols:", list((c.get('features') or {}).keys()),
                  "| rows:", sum(s.get("num_examples", 0) for s in (c.get("splits") or {}).values()))
    except Exception as e:
        print("  ", cid, "ERR", e)

print()
print("=== 3) Adzuna API docs (co can key?) ===")
t = gett("https://developer.adzuna.com/overview", 60)
t2 = re.sub(r"<[^>]+>", " ", t)
t2 = re.sub(r"\s+", " ", t2)
for kw in ["API key", "app_id", "app_key", "free", "register", "terms"]:
    i = t2.lower().find(kw.lower())
    print(f"  {kw!r} idx={i}", "|", t2[max(0, i - 150):i + 250] if i > 0 else "")
