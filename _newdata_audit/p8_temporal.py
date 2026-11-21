# -*- coding: utf-8 -*-
"""Kiểm tra temporal: ApplicationDate vs cửa sổ job, và tính leakage."""
import os, collections, json, re

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

job_win, job_sd, job_ed = {}, {}, {}
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        job_win[p[0]] = p[1]; job_sd[p[0]] = p[9][:10]; job_ed[p[0]] = p[10][:10]
print('jobs loaded:', len(job_win))

before_start = after_end = 0
n = 0
delta_before = collections.Counter()
delta_after = collections.Counter()
from datetime import datetime
def d(s):
    return datetime.strptime(s[:10], '%Y-%m-%d')

with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        n += 1
        jid, dt = p[4], p[3]
        if jid not in job_sd:
            continue
        try:
            a = d(dt)
        except ValueError:
            continue
        s, e = d(job_sd[jid]), d(job_ed[jid])
        if a < s:
            before_start += 1
            delta_before[(s - a).days] += 1
        elif a > e:
            after_end += 1
            delta_after[(a - e).days] += 1
print('apps:', n)
print('apply TRƯỚC StartDate:', before_start, '(%.2f%%)' % (100.0*before_start/n))
print('apply SAU EndDate   :', after_end, '(%.2f%%)' % (100.0*after_end/n))
print('  phân bố lệch trước (ngày):', delta_before.most_common(8))
print('  phân bố lệch sau (ngày) :', delta_after.most_common(8))

# App date range theo window
win_date_min, win_date_max = {}, {}
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        w, dt = p[1], p[3][:10]
        if w not in win_date_min or dt < win_date_min[w]:
            win_date_min[w] = dt
        if w not in win_date_max or dt > win_date_max[w]:
            win_date_max[w] = dt
print('\nKhoảng ngày application theo window:')
for w in sorted(win_date_min, key=int):
    print('  Window %s: %s -> %s' % (w, win_date_min[w], win_date_max[w]))

# Job posting theo window
jw_min, jw_max = {}, {}
for k in job_win:
    w = job_win[k]
    if w not in jw_min or job_sd[k] < jw_min[w]:
        jw_min[w] = job_sd[k]
    if w not in jw_max or job_ed[k] > jw_max[w]:
        jw_max[w] = job_ed[k]
print('\nKhoảng StartDate/EndDate của job theo window:')
for w in sorted(jw_min, key=int):
    print('  Window %s: start %s.. | end ..%s' % (w, jw_min[w], jw_max[w]))
