# -*- coding: utf-8 -*-
"""Mô phỏng nhanh tính khả thi của split leave-one-out theo user + đo số liệu gợi ý."""
import os, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

# users theo split, apps
user_split = {}
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        user_split[int(p[0])] = p[2]

train_users = set()
test_users = set()
apps_by_user = collections.Counter()
for raw in open(os.path.join(BASE, 'apps.tsv'), 'rb').readlines()[1:0]:
    pass
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        uid = int(p[0])
        apps_by_user[uid] += 1
        if p[2] == 'Train':
            train_users.add(uid)
        else:
            test_users.add(uid)

print('Train users:', len(train_users), '| Test users:', len(test_users))
print('giao:', len(train_users & test_users))
print('user có app trong Train nhưng split=Test:',
      sum(1 for u in train_users if user_split.get(u) == 'Test'))

# Nếu ta bỏ split có sẵn và tự chia theo user, sẽ có bao nhiêu user dùng được?
cnts = [apps_by_user[u] for u in train_users]
cnts.sort()
print('\nTrong %d user có app: phân bố như bảng trên' % len(cnts))
for k in (1, 2, 3, 5, 10, 20):
    print('  >= %2d app: %7d users (%.1f%%)' % (k, sum(1 for c in cnts if c >= k),
          100.0*sum(1 for c in cnts if c >= k)/len(cnts)))

# Số item (job) ứng viên cho ranking: job có ít nhất 1 app
jobs_applied = set()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 5:
            jobs_applied.add(int(p[4]))
print('\njob ứng viên (>=1 app):', len(jobs_applied), '/ 1,092,096')
print('tỉ lệ phủ item: %.1f%%' % (100.0*len(jobs_applied)/1092096))

# ước lượng mật độ train sau khi chia
print('\nƯớc lượng: nếu dùng toàn bộ 1.603.111 app, 321.235 user, 365.668 job ->')
print('  density = %.6f%%' % (100.0*1603111/(321235*365668)))
print('Lọc user>=5 app -> users=%d, apps=%d' % (
    sum(1 for c in cnts if c >= 5), sum(c for c in cnts if c >= 5)))
print('  density = %.6f%%' % (
    100.0*sum(c for c in cnts if c >= 5)/(sum(1 for c in cnts if c >= 5)*365668)))
