# -*- coding: utf-8 -*-
"""Kiem CHAT LUONG ten employer trich duoc: co phai cong ty that khong?"""
import csv, os, re, sys, collections

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
sys.path.insert(0, r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
from p44_employer_clients import employer_from  # tai su dung ham

job_emp = {}
with open(os.path.join(BASE, 'jobs.tsv'), encoding='utf-8', errors='replace', newline='') as f:
    rd = csv.reader(f, delimiter='\t'); h = next(rd)
    ij, idesc, ireq = h.index('JobID'), h.index('Description'), h.index('Requirements')
    n = 0
    for row in rd:
        if len(row) < 11: continue
        n += 1
        e, s = employer_from(row[idesc], row[ireq])
        if e:
            job_emp[row[ij]] = e.lower()
        if n >= 400000: break
print(f'quet {n} job, co employer: {len(job_emp)}')

emp_apps = collections.Counter()
with open(os.path.join(BASE, 'apps.tsv'), encoding='utf-8', newline='') as f:
    rd = csv.reader(f, delimiter='\t'); h = next(rd)
    iu, ijm = h.index('UserID'), h.index('JobID')
    for row in rd:
        if len(row) < 5: continue
        e = job_emp.get(row[ijm])
        if e: emp_apps[e] += 1

print(f'\n=== TOP 40 EMPLOYER THEO SO APPLICATION ===')
for e, c in emp_apps.most_common(40):
    print(f'  {c:6d}  {e[:75]}')

vals = list(emp_apps.values())
vals.sort(reverse=True)
print(f'\ntong employer: {len(emp_apps)} | tong app: {sum(vals)}')
for k in (10, 50, 100, 500):
    print(f'  top {k:4d} employer chiem {100.0*sum(vals[:k])/sum(vals):5.1f}% app')
print(f'  employer chi co 1 app: {sum(1 for v in vals if v==1)} ({100.0*sum(1 for v in vals if v==1)/len(vals):.1f}%)')
