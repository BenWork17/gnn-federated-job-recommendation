# -*- coding: utf-8 -*-
"""Các kiểm tra bổ sung: Zip5, phủ profile của test-user, trùng tiêu đề giữa window."""
import os, re, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

# ---- 1. Zip5 không hợp lệ trông thế nào
bad_zip = collections.Counter()
n = 0
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        z = p[8]
        if not re.fullmatch(r'\d{5}', z or ''):
            if z == '':
                bad_zip['<empty>'] += 1
            elif re.fullmatch(r'\d{5}-\d{4}', z):
                bad_zip['zip+4'] += 1
            elif re.fullmatch(r'\d{4}', z):
                bad_zip['4-digit'] += 1
            elif re.fullmatch(r'\d+', z):
                bad_zip['all-digits-but-not-5'] += 1
            else:
                bad_zip['other-alpha'] += 1
        if n >= 400000:
            break
print('=== Zip5 (400k job đầu) ===', bad_zip.most_common())

# ---- 2. Test users có profile/history?
test_users, train_users = set(), set()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        (test_users if p[2] == 'Test' else train_users).add(p[0])
hist_users = set()
with open(os.path.join(BASE, 'user_history.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 5:
            hist_users.add(p[0])
print('\n=== Phủ hồ sơ ===')
print('Test users:', len(test_users), '| có user_history:', len(test_users & hist_users))
print('Train users:', len(train_users), '| có user_history:', len(train_users & hist_users))
print('Tỉ lệ phủ history: test %.1f%%, train %.1f%%' % (
    100.0*len(test_users & hist_users)/len(test_users),
    100.0*len(train_users & hist_users)/len(train_users)))

# ---- 3. trùng tiêu đề giữa window (posting lặp lại)
title_windows = collections.defaultdict(set)
n = 0
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        title_windows[p[2].strip().lower()].add(p[1])
        if n >= 300000:
            break
multi = sum(1 for v in title_windows.values() if len(v) > 1)
print('\n=== Trùng tiêu đề xuyên window (300k job đầu) ===')
print('tiêu đề xuất hiện ở >1 window: %d / %d (%.1f%%)' % (
    multi, len(title_windows), 100.0*multi/len(title_windows)))

# ---- 4. apps/job top để xem long tail
job_apps = collections.Counter()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 5:
            job_apps[int(p[4])] += 1
tot = sum(job_apps.values())
vals = sorted(job_apps.values(), reverse=True)
print('\n=== Tập trung tương tác ===')
for k in (10, 100, 1000, 10000):
    print('  top %6d job chiếm %5.1f%% tổng app' % (k, 100.0*sum(vals[:k])/tot))
print('  job có 1 app: %d (%.1f%% trong số job có app)' % (
    sum(1 for v in vals if v == 1), 100.0*sum(1 for v in vals if v == 1)/len(vals)))
print('  job có <=2 app: %.1f%%' % (100.0*sum(1 for v in vals if v <= 2)/len(vals)))
