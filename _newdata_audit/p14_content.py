# -*- coding: utf-8 -*-
"""Lượt cuối: tín hiệu nội dung thay thế (history title, major), employer từ block trùng."""
import os, re, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

# ---- 1. Trùng lặp giữa JobTitle lịch sử và Title tin tuyển dụng
job_titles = set()
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 11:
            job_titles.add(p[2].strip().lower())
print('distinct job Title (lower):', len(job_titles))

hist_titles = collections.Counter()
n = 0
with open(os.path.join(BASE, 'user_history.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        n += 1
        t = p[4].strip().lower()
        if t:
            hist_titles[t] += 1
print('history rows:', n, '| distinct history titles:', len(hist_titles))
inter = set(hist_titles) & job_titles
print('history title trùng chính xác với job title: %d (%.1f%% theo loại, %.1f%% theo dòng)'
      % (len(inter), 100.0*len(inter)/len(hist_titles),
         100.0*sum(hist_titles[t] for t in inter)/n))

# ---- 2. Employer từ block Description trùng lặp
desc_block = collections.Counter()
samples = {}
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        d = re.sub(r'\s+', ' ', re.sub(r'<[^>]{0,300}>', ' ', p[3])).strip()[:500].lower()
        desc_block[d] += 1
        if d not in samples:
            samples[d] = p[2]
print('\n=== Block Description trùng (toàn bộ) ===')
print('distinct block:', len(desc_block))
top = desc_block.most_common(6)
for d, c in top:
    print('  %5d x  title=%s' % (c, samples[d][:40]))
    print('        %s' % d[:220])
share = sum(c for _, c in top) / 1092096
print('6 block lớn nhất chiếm %.2f%% toàn bộ job' % (100*share))

# ---- 3. Profile test-user: degree + major khả dụng
test_users = set()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        if p[2] == 'Test':
            test_users.add(p[0])
deg = collections.Counter()
major_ok = 0
for_split = collections.Counter()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        if p[0] in test_users:
            deg[p[7]] += 1
            if p[8].strip() and p[8].strip() != 'Not Applicable':
                major_ok += 1
print('\n=== Test users (n=%d) ===' % len(test_users))
print('DegreeType:', dict(deg.most_common()))
print('có Major dùng được: %d (%.1f%%)' % (major_ok, 100.0*major_ok/len(test_users)))

# ---- 4. 87k app trước StartDate tập trung ở window nào / job nào
job_sd = {}
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 11:
            job_sd[p[0]] = (p[1], p[9][:10])
win_before = collections.Counter()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        jid = p[4]
        if jid in job_sd and p[3][:10] < job_sd[jid][1]:
            win_before[p[1]] += 1
print('\n=== App trước StartDate theo window ===')
print(dict(sorted(win_before.items(), key=lambda kv: int(kv[0]))))
