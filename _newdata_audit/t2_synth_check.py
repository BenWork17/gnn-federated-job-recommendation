# -*- coding: utf-8 -*-
"""t2: kiem chung tinh TONG HOP cua job-description-dataset (1.74 GB, cot skills 100%)."""
import csv
import io
import json
import sys
import urllib.request
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}
URL = "https://huggingface.co/datasets/lof223/job_description/resolve/main/job_descriptions.csv"
TOTAL = 1743166140
HDR = ['Job Id', 'Experience', 'Qualifications', 'Salary Range', 'location', 'Country', 'latitude',
       'longitude', 'Work Type', 'Company Size', 'Job Posting Date', 'Preference', 'Contact Person',
       'Contact', 'Job Title', 'Role', 'Job Portal', 'Job Description', 'Benefits', 'skills',
       'Responsibilities', 'Company', 'Company Profile']
idx = {c: i for i, c in enumerate(HDR)}

req = urllib.request.Request(URL, headers=dict(UA, Range=f"bytes={TOTAL//2}-{TOTAL//2+6_000_000}"))
with urllib.request.urlopen(req, timeout=180) as r:
    raw = r.read()
rows = [x for x in csv.reader(io.StringIO(raw.decode("utf-8", "replace"))) if len(x) == 23][1:]
print("rows parsed:", len(rows))
for c in ["Job Title", "Role", "Company", "Country", "location", "Company Size", "Qualifications", "Work Type"]:
    print(f"  {c:15s} unique={len({x[idx[c]] for x in rows}):6d}")
print("Job Portal:", Counter(x[idx['Job Portal']] for x in rows).most_common(4))
print("Preference:", Counter(x[idx['Preference']] for x in rows).most_common(4))
print("Experience:", Counter(x[idx['Experience']] for x in rows).most_common(4))
print("Contact Person:", Counter(x[idx['Contact Person']] for x in rows).most_common(3))
print()
print("row0 fields:")
for c in ["Job Id", "Job Title", "Role", "Company", "Country", "location", "latitude", "Contact", "Benefits"]:
    print(f"  {c:15s}= {rows[0][idx[c]][:90]}")
print()
print("Job Description[0][:400]:", rows[0][idx['Job Description']][:400])
print()
print("skills[0][:300]:", rows[0][idx['skills']][:300])
print()
# Cafe: dem so cap (Company, Country) lap lai -> dau hieu sinh ngau nhien
print("sample (Company, Country, Role) combos:")
for t in Counter((x[idx['Company']], x[idx['Country']]) for x in rows).most_common(6):
    print("   ", t)
