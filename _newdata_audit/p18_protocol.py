# -*- coding: utf-8 -*-
"""Kiểm chứng giao thức đánh giá của bộ dữ liệu: test user + cửa sổ thời gian."""
import os, collections, json
from datetime import datetime

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"

test_u = set()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 15 and p[2] == 'Test':
            test_u.add(int(p[0]))

per_user = collections.defaultdict(list)
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        u = int(p[0])
        if u in test_u:
            per_user[u].append((p[3], int(p[1]), int(p[4])))

print('test users:', len(test_u), '| có app:', len(per_user))
c = sorted(len(v) for v in per_user.values())
print('số app/user (test): median %d p25 %d p90 %d max %d' %
      (c[len(c)//2], c[len(c)//4], c[int(len(c)*.9)], c[-1]))
print('test user có >=2 app:', sum(1 for x in c if x >= 2),
      '| >=3:', sum(1 for x in c if x >= 3), '| >=5:', sum(1 for x in c if x >= 5))

# Thứ tự thời gian có tăng dần theo window?
mono = nonmono = 0
for u, rows in per_user.items():
    rows2 = sorted(rows, key=lambda r: r[1])
    wins = [r[1] for r in rows2]
    dates = [r[0] for r in rows2]
    if dates == sorted(dates) and wins == sorted(wins):
        mono += 1
    else:
        nonmono += 1
print('\nuser có app sắp theo thời gian tăng dần:', mono, '| không:', nonmono)

# Nếu protocol "dự đoán app cuối cùng": cần >=1 history + 1 target
ok_last = sum(1 for u, v in per_user.items() if len(v) >= 2)
print('user đủ cho leave-last-out (>=2 app): %d (%.1f%%)'
      % (ok_last, 100.0*ok_last/len(per_user)))

# Window cuối cùng của mỗi test user
last_win = collections.Counter(max(r[1] for r in v) for v in per_user.values())
print('\nwindow của app cuối cùng (test user):',
      dict(sorted(last_win.items(), key=lambda kv: kv[0])))
first_win = collections.Counter(min(r[1] for r in v) for v in per_user.values())
print('window của app đầu tiên (test user):',
      dict(sorted(first_win.items(), key=lambda kv: kv[0])))

# Ứng viên mỗi window: job còn mở
print('\n=== Job "còn mở" theo ngày (dùng được làm tập ứng viên) ===')
# đếm theo EndDate >= 2012-04-01 v.v. -- quá nặng, ước lượng bằng sample
import random
rows = []
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        if random.random() < 0.02:
            rows.append((p[9][:10], p[10][:10]))
print('sample %d job; tỉ lệ EndDate >= 2012-05-19: %.1f%%'
      % (len(rows), 100.0*sum(1 for s, e in rows if e >= '2012-05-19')/max(len(rows), 1)))
