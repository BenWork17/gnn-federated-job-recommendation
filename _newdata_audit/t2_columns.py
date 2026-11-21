# -*- coding: utf-8 -*-
"""t2: trich TEN COT THAT cua dataset asaniczka tu data card HTML (jina)."""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
UA = {"User-Agent": "Mozilla/5.0", "X-Return-Format": "html"}

BASE = "https://r.jina.ai/https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024/data"


def card(sel):
    u = f"{BASE}?select={sel}"
    t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read().decode("utf-8", "replace")
    return t


out = {}
for sel in ["linkedin_job_postings.csv", "job_skills.csv", "job_summary.csv"]:
    try:
        t = card(sel)
    except Exception as e:
        out[sel] = {"err": str(e)}
        continue
    i = t.find("About this file")
    seg = t[i:i + 20000] if i > 0 else t[:20000]
    txt = re.sub(r"<[^>]+>", " | ", seg)
    txt = re.sub(r"\s*\|\s*(\|\s*)+", " | ", txt)
    # ten cot nam ngay truoc "(type:"
    fields = re.findall(r"\|\s*([A-Za-z_][A-Za-z0-9_]{1,60})\s*\|\s*(?:sort)?\s*\|?\s*(?:[^|]{0,40}\|)?\s*[^|]{0,200}?\(type:(str|datetime|bool|int|float)\)", txt)
    # cach 2: tim moi "(type:xxx)" roi lay tu truoc
    fields2 = []
    for m in re.finditer(r"\(type:(str|datetime|bool|int|float|object)\)", txt):
        pre = txt[max(0, m.start() - 400):m.start()]
        toks = [x.strip() for x in pre.split("|") if x.strip()]
        if toks:
            fields2.append((toks[-1], m.group(1)))
    out[sel] = {"len_html": len(t), "n_fields": len(fields2),
                "fields": fields2, "card_text_head": txt[:1200]}

print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "card_text_head"} for k, v in out.items()},
                 indent=2, ensure_ascii=False)[:4000])
OUT.joinpath("t2_kaggle_columns.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
