"""t2: lay data card cua tung file trong dataset Kaggle qua jina + select param."""
import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def txt(u, timeout=120):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


BASE = "https://r.jina.ai/https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024"
for sel in ["job_skills.csv", "linkedin_job_postings.csv"]:
    t = txt(f"{BASE}/data?select={sel}", timeout=150)
    print("=" * 70)
    print("select =", sel, "| len", len(t), "| starts:", t[:60].replace("\n", " "))
    if t.startswith("ERR"):
        continue
    # tim phan "About this file"
    for kw in ["About this file", "Columns", "job_link", "job_skills", "job_summary", "Rows"]:
        i = t.find(kw)
        print(f"  {kw!r}: idx={i}")
    i = t.find("About this file")
    print("  ---- card ----")
    print(t[max(0, i - 500):i + 900] if i > 0 else t[:1500])
