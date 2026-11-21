# -*- coding: utf-8 -*-
"""Lượt quét cuối: mojibake toàn file, tập con khả thi, mức chồng lấn item train/test."""
import os, re, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

# ---- 1. mojibake & ký tự lạ trên TOÀN BỘ jobs
bad_rows = 0
bad_chars = collections.Counter()
nrep = 0
n = 0
CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        t = p[2] + p[3] + p[4]
        if '\ufffd' in t:
            bad_rows += 1
            nrep += t.count('\ufffd')
        if CTRL.search(t):
            bad_chars['control'] += 1
        if n % 300000 == 0:
            print('  ...%d' % n, flush=True)
print('=== Ký tự hỏng (toàn bộ %d job) ===' % n)
print('row chứa U+FFFD (mojibake):', bad_rows, '(%.2f%%)' % (100.0*bad_rows/n),
      '| tổng ký tự hỏng:', nrep)
print('row chứa control char:', dict(bad_chars))

# ---- 2. tập con khả thi
user_apps = collections.Counter()
job_apps = collections.Counter()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        user_apps[int(p[0])] += 1
        job_apps[int(p[4])] += 1

print('\n=== Tập con khả thi cho thực nghiệm ===')
for u_min in (5, 10):
    for j_min in (0, 5, 10):
        users = {u for u, c in user_apps.items() if c >= u_min}
        jobs = {j for j, c in job_apps.items() if c >= j_min}
        # đếm app nằm trong giao
        cnt = 0
        with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
            fh.readline()
            for raw in fh:
                p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
                if len(p) != 5:
                    continue
                if int(p[0]) in users and int(p[4]) in jobs:
                    cnt += 1
        dens = 100.0 * cnt / (len(users) * len(jobs)) if users and jobs else 0
        print('user>=%2d, job>=%2d -> users %7d | jobs %7d | apps %8d | density %.4f%%'
              % (u_min, j_min, len(users), len(jobs), cnt, dens))

# ---- 3. chồng lấn item giữa train-user và test-user
train_users, test_users = set(), set()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        (test_users if p[2] == 'Test' else train_users).add(int(p[0]))
train_items, test_items = set(), set()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        uid, jid = int(p[0]), int(p[4])
        (test_items if uid in test_users else train_items).add(jid)
print('\n=== Chồng lấn item train-user vs test-user ===')
print('item có app từ train-user:', len(train_items))
print('item có app từ test-user :', len(test_items))
print('giao:', len(train_items & test_items),
      '(%.1f%% của item test)' % (100.0*len(train_items & test_items)/len(test_items)))
