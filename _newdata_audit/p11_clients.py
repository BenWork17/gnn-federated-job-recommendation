# -*- coding: utf-8 -*-
"""Kiểm tra khả năng phân vùng KHÁCH HÀNG (client) khi không có cột employer."""
import os, re, collections, json, random

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

# ---- A. JobID block ↔ nội dung: có dấu hiệu "nguồn" khác nhau không?
ranges = [(1, 200000), (200000, 400000), (400000, 600000), (600000, 800000),
          (800000, 1000000), (1000000, 1200000)]
agg = {r: collections.Counter() for r in ranges}
n_in = {r: 0 for r in ranges}
pat_src = re.compile(r'Source\s*[-\u2013\u2014]\s*([^\r\n]{3,50})', re.I)
n = 0
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        jid = int(p[0])
        for r in ranges:
            if r[0] <= jid < r[1]:
                n_in[r] += 1
                m = pat_src.search(p[3] + p[4])
                if m:
                    agg[r][m.group(1).strip().lower()[:35]] += 1
                break
print('=== JobID block vs "Source" ===')
for r in ranges:
    top = agg[r].most_common(3)
    print(' %8d-%8d n=%7d  src=%6d  top=%s' % (r[0], r[1], n_in[r], sum(agg[r].values()), top))

# ---- B. PII trong text job
pat_mail = re.compile(r'[\w\.\-+]+@[\w\-]+\.[\w\.]{2,}')
pat_phone = re.compile(r'\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b')
mail = phone = 0
m = 0
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        m += 1
        t = p[3] + ' ' + p[4]
        if pat_mail.search(t):
            mail += 1
        if pat_phone.search(t):
            phone += 1
        if m >= 200000:
            break
print('\n=== PII trong text job (%d job) ===' % m)
print('có email: %d (%.1f%%) | có số điện thoại: %d (%.1f%%)'
      % (mail, 100.0*mail/m, phone, 100.0*phone/m))

# ---- C. Ứng viên apply có "gần nhà" không (cùng state)?
user_state = {}
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        user_state[p[0]] = p[4]
job_state = {}
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        job_state[p[0]] = p[6]
same = diff = unknown = 0
st_pairs = collections.Counter()
napps = 0
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        napps += 1
        us, js = user_state.get(p[0]), job_state.get(p[4])
        if not us or not js:
            unknown += 1
        elif us == js:
            same += 1
            st_pairs[us] += 1
        else:
            diff += 1
print('\n=== Ứng tuyển cùng bang? (n=%d) ===' % napps)
print('cùng state: %d (%.1f%%) | khác: %d (%.1f%%) | thiếu: %d'
      % (same, 100.0*same/napps, diff, 100.0*diff/napps, unknown))
print('top state có app nội bang:', st_pairs.most_common(8))

# ---- D. Mỗi user có tập trung vào ít job không (baseline popularity)?
json.dump({'same_state_pct': round(100.0*same/napps, 2)}, open(os.path.join(OUT, 'geo.json'), 'w'))
