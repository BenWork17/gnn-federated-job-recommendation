# -*- coding: utf-8 -*-
"""Đánh giá các phương án phân vùng client cho FL + khả thi temporal split."""
import os, collections, json, hashlib
from datetime import datetime

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"

user_state = {}
user_deg = {}
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        user_state[int(p[0])] = p[4]
        user_deg[int(p[0])] = p[7]

user_apps = collections.Counter()
user_dates = collections.defaultdict(list)
job_state = {}
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 11:
            job_state[int(p[0])] = p[6]

with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        u = int(p[0]); user_apps[u] += 1
        user_dates[u].append(p[3])

print('=== Phương án phân vùng client ===')
print('\n[A] Theo STATE của user (top 8 + phần còn lại)')
sc = collections.Counter(user_state.get(u, '?') for u in user_apps)
tot = sum(sc.values())
for s, c in sc.most_common(8):
    us = [u for u in user_apps if user_state.get(u) == s]
    print('   %-3s n_users=%6d n_apps=%8d (%.1f%%)' % (s, len(us), c, 100.0*c/tot))
print('   distinct state:', len(sc))

print('\n[B] Hash user_id % C')
for C in (5, 8, 12, 20):
    cc = collections.Counter(hashlib.md5(str(u).encode()).digest()[0] % C for u in user_apps)
    apps = collections.Counter()
    for u in user_apps:
        apps[hashlib.md5(str(u).encode()).digest()[0] % C] += user_apps[u]
    print('   C=%-3d users/client min %6d max %6d | apps/client min %7d max %8d'
          % (C, min(cc.values()), max(cc.values()), min(apps.values()), max(apps.values())))

print('\n[C] Theo JobID block (giả định mỗi block = một nguồn)')
# không có thông tin employer -> chỉ có state của job
print('   -> không khả thi: jobs.tsv không có cột employer/company')

print('\n=== Temporal split khả thi? ===')
deltas = []
for u, ds in user_dates.items():
    if len(ds) >= 5:
        ds = sorted(ds)
        try:
            a = datetime.strptime(ds[0][:10], '%Y-%m-%d')
            b = datetime.strptime(ds[-1][:10], '%Y-%m-%d')
            deltas.append((b - a).days)
        except ValueError:
            pass
deltas.sort()
print('users >=5 app có đo được span:', len(deltas))
if deltas:
    print('khoảng thời gian từ app đầu đến app cuối (ngày): median %d p25 %d p75 %d p90 %d'
          % (deltas[len(deltas)//2], deltas[len(deltas)//4], deltas[3*len(deltas)//4],
             deltas[int(len(deltas)*.9)]))
print('=> TOÀN BỘ dữ liệu app chỉ trải 2012-04-01..2012-06-26 (87 ngày)')

print('\n=== users có profile dùng được ===')
deg_ok = sum(1 for d in user_deg.values() if d and d != 'None')
print('user có DegreeType (khác None): %d / %d (%.1f%%)'
      % (deg_ok, len(user_deg), 100.0*deg_ok/len(user_deg)))

print('\n=== Ứng viên cold-start: test user không có app nào ===')
test_users = set()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 15 and p[2] == 'Test':
            test_users.add(int(p[0]))
print('test users:', len(test_users), '| trong đó không có app:',
      len(test_users - set(user_apps)))
