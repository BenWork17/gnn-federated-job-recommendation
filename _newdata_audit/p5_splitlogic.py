# -*- coding: utf-8 -*-
"""Kiểm tra cấu trúc chia Train/Test theo user, và khả năng dựng lại employer/skill."""
import os, re, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

# ---- apps: user -> set(split), window
user_splits = collections.defaultdict(set)
user_apps = collections.Counter()
user_train = collections.Counter()
user_test = collections.Counter()
user_window = {}
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        u, w, s, d, j = p
        uid = int(u)
        user_splits[uid].add(s)
        user_apps[uid] += 1
        user_window[uid] = w
        if s == 'Train':
            user_train[uid] += 1
        else:
            user_test[uid] += 1

both = [u for u, s in user_splits.items() if len(s) > 1]
only_test = sum(1 for u, s in user_splits.items() if s == {'Test'})
only_train = sum(1 for u, s in user_splits.items() if s == {'Train'})
print('users total (with apps):', len(user_splits))
print('users with BOTH Train & Test apps:', len(both),
      '(%.1f%%)' % (100.0*len(both)/len(user_splits)))
print('users only Train:', only_train, '| users only Test:', only_test)

# Phân bố số app test của các user có cả 2
cnt_test = [user_test[u] for u in both]
cnt_test.sort()
if cnt_test:
    print('test apps/user (nhóm có cả 2): median %d p25 %d p75 %d max %d'
          % (cnt_test[len(cnt_test)//2], cnt_test[len(cnt_test)//4],
             cnt_test[3*len(cnt_test)//4], cnt_test[-1]))
cnt_tr = [user_train[u] for u in both]
print('users có >=1 train và >=1 test:', len(both))
print('users đủ điều kiện (train>=2, test>=1):',
      sum(1 for u in both if user_train[u] >= 2))
print('users đủ điều kiện (train>=5, test>=1):',
      sum(1 for u in both if user_train[u] >= 5))
print('users đủ điều kiện (train>=10, test>=1):',
      sum(1 for u in both if user_train[u] >= 10))

# Quan hệ Test-row và thứ tự thời gian
# lấy mẫu 1 user xem
sample_u = both[0] if both else None
print('\nví dụ user', sample_u, 'train', user_train[sample_u], 'test', user_test[sample_u],
      'window', user_window[sample_u])

# ---- Dựng lại employer từ Description: tìm mẫu "Source -" và footer
pat_src = re.compile(r'Source\s*[-–—]\s*([^\r\n]{3,60})', re.I)
pat_company = re.compile(r'\b(Inc\.|LLC|L\.L\.C\.|Corp\.|Corporation|Company|Ltd\.?|LP|LLP|Group)\b')
n = 0
has_src = 0
has_company_hint = 0
src_names = collections.Counter()
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for i, raw in enumerate(fh):
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        desc = p[3]
        m = pat_src.search(desc)
        if m:
            has_src += 1
            src_names[m.group(1).strip().lower()[:40]] += 1
        if pat_company.search(desc[:800]):
            has_company_hint += 1
        if n >= 200000:
            break
print('\n[200k jobs đầu] có mẫu "Source - X":', has_src,
      '(%.1f%%)' % (100.0*has_src/n))
print('có dấu hiệu tên công ty ở 800 ký tự đầu:', has_company_hint,
      '(%.1f%%)' % (100.0*has_company_hint/n))
print('top "Source -":', src_names.most_common(10))

json.dump({'users_with_both': len(both), 'only_train': only_train,
           'only_test': only_test, 'with_apps': len(user_splits),
           'meets_2_1': sum(1 for u in both if user_train[u] >= 2),
           'meets_5_1': sum(1 for u in both if user_train[u] >= 5),
           'meets_10_1': sum(1 for u in both if user_train[u] >= 10),
           'src_pattern_pct': round(100.0*has_src/n, 2)},
          open(os.path.join(OUT, 'splits.json'), 'w'), indent=1)
