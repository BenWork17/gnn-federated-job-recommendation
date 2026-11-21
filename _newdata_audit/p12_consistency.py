# -*- coding: utf-8 -*-
"""Kiểm tra nhất quán nội bộ users.tsv <-> user_history.tsv và các giá trị bất thường."""
import os, collections, re

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"

# WorkHistoryCount khai báo vs số dòng history thực tế
decl = {}
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        try:
            decl[int(p[0])] = int(p[10])
        except ValueError:
            decl[int(p[0])] = None
actual = collections.Counter()
with open(os.path.join(BASE, 'user_history.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 5:
            actual[int(p[0])] += 1

mismatch = same = nohist = both_missing = 0
diff_dist = collections.Counter()
for u, d in decl.items():
    a = actual.get(u, 0)
    if a == 0:
        nohist += 1
        if d == 0:
            both_missing += 1
        continue
    if d is None:
        continue
    if a == d:
        same += 1
    else:
        mismatch += 1
        diff_dist[a - d] += 1
print('=== WorkHistoryCount vs số dòng user_history ===')
print('user không có history:', nohist, '| khớp:', same, '| lệch:', mismatch)
print('phân bố lệch (actual - declared):', diff_dist.most_common(6))

# TotalYearsExperience bất thường
yrs = collections.Counter()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        try:
            yrs[int(p[11])] += 1
        except ValueError:
            yrs[-1] += 1
print('\n=== TotalYearsExperience ===')
print('âm/không parse:', yrs.get(-1, 0))
print('> 50 năm:', sum(v for k, v in yrs.items() if k > 50))
print('> 60 năm:', sum(v for k, v in yrs.items() if k > 60))
print('max:', max(k for k in yrs if k >= 0), '| rỗng(?) 0:', yrs.get(0, 0))

# Major rác
mj = collections.Counter()
mj_missing = 0
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        if not p[8].strip():
            mj_missing += 1
        else:
            mj[p[8].strip()] += 1
print('\n=== Major ===')
print('rỗng:', mj_missing, '| "Not Applicable":', mj.get('Not Applicable', 0),
      '| distinct:', len(mj))

# DegreeType theo major rỗng?
print('\nVí dụ tổ hợp DegreeType + Major:')
seen = set()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        k = (p[7], p[8][:30])
        if k not in seen and len(seen) < 12:
            seen.add(k)
            print('   ', k)
