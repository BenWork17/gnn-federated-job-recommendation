# -*- coding: utf-8 -*-
"""t2: (1) ten cot THAT cua asaniczka dataset, (2) kiem chung tinh tong hop cua job-description-dataset."""
import csv
import io
import json
import re
import sys
import urllib.request
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}


def gett(u, timeout=150):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


print("=== 1) asaniczka: data card cua linkedin_job_postings.csv ===")
t = gett("https://r.jina.ai/https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024/data?select=linkedin_job_postings.csv")
i = t.find("About this file")
card = t[i:i + 3000] if i > 0 else t[:3000]
print(card)
# trich ten cot: mau "... (type:str)" -> ten cot nam truoc dau " (type:"
fields = re.findall(r"([A-Za-z_][A-Za-z0-9_ ]{2,60})\s*\(type:(str|datetime|bool|int|float)\)", card)
print("\nFIELDS PARSED:", [f[0].strip() for f in fields])

print()
print("=== 2) job-description-dataset: kiem chung synthetic ===")
URL = "https://huggingface.co/datasets/lof223/job_description/resolve/main/job_descriptions.csv"
TOTAL = 1743166140
req = urllib.request.Request(URL, headers=dict(UA, Range=f"bytes={TOTAL//2}-{TOTAL//2+4_000_000}"))
with urllib.request.urlopen(req, timeout=180) as r:
    raw = r.read()
txt = raw.decode("utf-8", "replace")
rows = list(csv.reader(io.StringIO(txt)))
rows = [x for x in rows if len(x) == 23][1:]
hdr = ['Job Id','Experience','Qualifications','Salary Range','location','Country','latitude','longitude','Work Type','Company Size','Job Posting Date','Preference','Contact Person','Contact','Job Title','Role','Job Portal','Job Description','Benefits','skills','Responsibilities','Company','Company Profile']
idx = {c: i for i, c in enumerate(hdr)}
print("rows parsed:", len(rows))
print("unique Job Title:", len({x[idx['Job Title']] for x in rows}))
print("unique Role     :", len({x[idx['Role']] for x in rows}))
print("unique Company  :", len({x[idx['Company']] for x in rows}))
print("unique Country  :", len({x[idx['Country']] for x in rows}))
print("unique City     :", len({x[idx['location']] for x in rows}))
print("unique Job Id   :", len({x[idx['Job Id']] for x in rows}), "/", len(rows))
print("Job Portal vals :", Counter(x[idx['Job Portal']] for x in rows).most_common(5))
print("Preference vals :", Counter(x[idx['Preference']] for x in rows).most_common(5))
print("Work Type vals  :", Counter(x[idx['Work Type']] for x in rows).most_common(5))
# trung lap company-role cap vo ly?
pairs = Counter((x[idx['Company']], x[idx['Country']]) for x in rows)
print("sample company-country pairs:", pairs.most_common(5))
print("\nrow0:", {k: rows[0][idx[k]][:70] for k in ['Job Title','Company','Country','location','Qualifications','skills']})
print("\nJob Description template check (first 300 chars):")
print(rows[0][idx['Job Description']][:300])
print("\nskills sample (3 rows):")
for x in rows[:3]:
    print("  -", x[idx['skills']][:220])
