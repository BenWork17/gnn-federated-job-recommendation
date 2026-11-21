# -*- coding: utf-8 -*-
"""Profiling các bảng nhỏ: apps, users, user_history."""
import csv, os, sys, collections, json, re
from datetime import datetime

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

def read_tsv(path, ncols):
    bad = 0
    with open(path, 'rb') as fh:
        header = fh.readline().decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        for raw in fh:
            line = raw.decode('utf-8', 'replace').rstrip('\r\n')
            parts = line.split('\t')
            if len(parts) != ncols:
                bad += 1
                if bad <= 3:
                    print('  BADLINE', ncols, len(parts), line[:200], flush=True)
                continue
            yield parts
    print(f'  [{os.path.basename(path)}] bad lines: {bad}', flush=True)

# ---------------- apps ----------------
print('=== apps.tsv ===', flush=True)
apps_n = 0
split_cnt = collections.Counter()
win_cnt = collections.Counter()
split_win = collections.Counter()
users = collections.Counter()
jobs = set()
pairs = set()
dup_pairs = 0
uids_set = set()
date_min, date_max = None, None
apps_bad_jobid = 0
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for i, raw in enumerate(fh):
        line = raw.decode('utf-8', 'replace').rstrip('\r\n')
        p = line.split('\t')
        if len(p) != 5:
            apps_bad_jobid += 1
            continue
        apps_n += 1
        u, w, s, d, j = p
        split_cnt[s] += 1
        win_cnt[w] += 1
        split_win[(s, w)] += 1
        users[u] += 1
        uids_set.add(u)
        try:
            jobs.add(int(j))
        except ValueError:
            apps_bad_jobid += 1
        key = (u, j)
        if key in pairs:
            dup_pairs += 1
        else:
            pairs.add(key)
        if i % 200000 == 0:
            date_min = d if date_min is None or d < date_min else date_min
            date_max = d if date_max is None or d > date_max else date_max
print('rows:', apps_n, '| unique users:', len(uids_set), '| unique jobs:', len(jobs))
print('split:', dict(split_cnt))
print('window:', dict(sorted(win_cnt.items(), key=lambda kv: int(kv[0]))))
print('split x window:', dict(sorted(split_win.items(), key=lambda kv: (kv[0][0], int(kv[0][1])))))
print('duplicate (user,job) pairs:', dup_pairs, '| unique pairs:', len(pairs))
print('bad rows:', apps_bad_jobid)
print('date range (sampled check):', date_min, '->', date_max)
import statistics
cnts = sorted(users.values())
print('apps/user: min %d p25 %d median %d p75 %d p95 %d max %d mean %.2f' % (
    cnts[0], cnts[len(cnts)//4], cnts[len(cnts)//2], cnts[3*len(cnts)//4],
    cnts[int(len(cnts)*0.95)], cnts[-1], statistics.mean(cnts)))
print('users with >=5 apps:', sum(1 for c in users.values() if c >= 5),
      '| >=10:', sum(1 for c in users.values() if c >= 10))
print('users file:', os.path.getsize(os.path.join(BASE, 'apps.tsv')))
json.dump({'apps_rows': apps_n, 'uniq_users_apps': len(uids_set),
           'uniq_jobs_apps': len(jobs), 'dup_pairs': dup_pairs},
          open(os.path.join(OUT, 'apps_stats.json'), 'w'), indent=1)

# ---------------- users ----------------
print('\n=== users.tsv ===', flush=True)
rows = 0
uid = collections.Counter()
splitc = collections.Counter()
win = collections.Counter()
deg = collections.Counter()
major = collections.Counter()
country = collections.Counter()
state = collections.Counter()
zip_bad = 0
graduation_empty = 0
years = collections.Counter()
employed = collections.Counter()
managed = collections.Counter()
raw_uid_set = set()
win_split = collections.Counter()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    hdr = fh.readline().decode('utf-8', 'replace').rstrip().split('\t')
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        rows += 1
        (u, w, s, city, st, cou, zc, dg, mj, grad, whc, tye, ce, mo, mh) = p
        uid[u] += 1
        raw_uid_set.add(u)
        splitc[s] += 1
        win[w] += 1
        win_split[(w, s)] += 1
        deg[dg] += 1
        major[mj] += 1
        country[cou] += 1
        state[st] += 1
        if not re.fullmatch(r'\d{5}', zc or ''):
            zip_bad += 1
        if not grad.strip():
            graduation_empty += 1
        years[tye] += 1
        employed[ce] += 1
        managed[mo] += 1
print('rows:', rows, '| unique UserID:', len(raw_uid_set),
      '| duplicate rows per user:', sum(1 for v in uid.values() if v > 1))
print('split:', dict(splitc), '| window:', dict(sorted(win.items(), key=lambda kv: int(kv[0]))))
print('window x split:', dict(sorted(win_split.items(), key=lambda kv: (int(kv[0][0]), kv[0][1]))))
print('DegreeType:', dict(deg.most_common(15)))
print('Country:', dict(country.most_common(10)))
print('State top15:', dict(state.most_common(15)))
print('Major: empty=%d distinct=%d top10=%s' % (major[''], len(major), major.most_common(10)))
print('ZipCode not 5-digit:', zip_bad)
print('GraduationDate empty:', graduation_empty)
print('TotalYearsExperience:', dict(sorted(years.items(), key=lambda kv: (kv[0] == '', kv[0]))[:12]))
print('CurrentlyEmployed:', dict(employed))
print('ManagedOthers:', dict(managed))
print('users vs apps: users in apps =', len(uids_set), '; users rows =', rows,
      '; overlap uid =', len(raw_uid_set & uids_set))

# ---------------- user_history ----------------
print('\n=== user_history.tsv ===', flush=True)
rows = 0
h_users = collections.Counter()
seqs = collections.Counter()
titles = collections.Counter()
splitc = collections.Counter()
seq_gaps = 0
maxseq = 0
with open(os.path.join(BASE, 'user_history.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        rows += 1
        u, w, s, seq, title = p
        h_users[u] += 1
        splitc[s] += 1
        titles[title.strip().lower()] += 1
        try:
            seqs[int(seq)] += 1
            maxseq = max(maxseq, int(seq))
        except ValueError:
            seq_gaps += 1
print('rows:', rows, '| unique users:', len(h_users), '| max sequence:', maxseq)
print('split:', dict(splitc))
print('history rows/user: min %d median %d max %d' % (
    min(h_users.values()), sorted(h_users.values())[len(h_users)//2], max(h_users.values())))
print('bad sequence values:', seq_gaps)
print('unique titles:', len(titles), '| top10:', titles.most_common(10))
print('title empty:', titles.get('', 0))
print('users only in history (not in users.tsv):', len(set(h_users) - raw_uid_set))
