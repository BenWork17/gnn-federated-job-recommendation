# -*- coding: utf-8 -*-
"""Kiểm tra tính toàn vẹn tham chiếu + phủ dữ liệu giữa 4 bảng."""
import os, collections, json, statistics

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

# --- jobs: id -> (window, start, end)
jobs_info = {}
max_jid = 0
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        jid = int(p[0])
        jobs_info[jid] = (p[1], p[9], p[10])
        if jid > max_jid:
            max_jid = jid
print('jobs:', len(jobs_info), '| max JobID:', max_jid,
      '| missing ids in 1..max:', max_jid - len(jobs_info))

# --- users: id -> (window, split)
users_info = {}
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        users_info[int(p[0])] = (p[1], p[2])
print('users:', len(users_info))

# --- apps
n = 0
job_not_found = 0
user_not_found = 0
win_mismatch_user = 0
win_mismatch_job = 0
date_outside = 0
date_before_start = 0
test_rows = 0
split_user_mismatch = 0
user_windows = collections.defaultdict(set)
user_apps = collections.Counter()
job_apps = collections.Counter()
job_windows_via_apps = collections.defaultdict(set)
ex_first = []
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        n += 1
        u, w, s, d, j = p
        uid, jid = int(u), int(j)
        user_apps[uid] += 1
        job_apps[jid] += 1
        user_windows[uid].add(w)
        job_windows_via_apps[jid].add(w)
        if jid not in jobs_info:
            job_not_found += 1
            if len(ex_first) < 5:
                ex_first.append(('job-missing', jid))
        else:
            jw, jsd, jed = jobs_info[jid]
            if jw != w:
                win_mismatch_job += 1
        if uid not in users_info:
            user_not_found += 1
        else:
            uw, usp = users_info[uid]
            if uw != w:
                win_mismatch_user += 1
            if s != usp and s == 'Test':
                split_user_mismatch += 1
        if s == 'Test':
            test_rows += 1
        if jid in jobs_info:
            if not (jobs_info[jid][1] <= d <= jobs_info[jid][2]):
                date_outside += 1
            elif d < jobs_info[jid][1]:
                date_before_start += 1
        if n % 400000 == 0:
            print('  ...%d' % n, flush=True)

print('\n=== REFERENTIAL INTEGRITY ===')
print('apps rows:', n)
print('JobID not in jobs.tsv:', job_not_found, '| UserID not in users.tsv:', user_not_found)
print('WindowID mismatch (app vs job):', win_mismatch_job,
      '| (app vs user):', win_mismatch_user)
print('Split mismatch (app=Test but user split=Train):', split_user_mismatch)
print('ApplicationDate outside [StartDate, EndDate]:', date_outside)
print('Test rows:', test_rows, '(%.1f%%)' % (100.0*test_rows/n))
print('users appearing in >1 window:', sum(1 for v in user_windows.values() if len(v) > 1))
print('jobs applied from apps:', len(job_apps), '| jobs never applied:',
      len(jobs_info) - len(job_apps))
print('jobs with apps in >1 window:', sum(1 for v in job_windows_via_apps.values() if len(v) > 1))

density = n / (len(user_apps) * len(job_apps))
print('\nDensity (users_with_apps x jobs_with_apps): %.6f%%' % (100*density))
print('Density (all users x all jobs): %.6f%%' % (100*n/(len(users_info)*len(jobs_info))))

c = sorted(job_apps.values())
print('apps/job: median %d p75 %d p90 %d p95 %d p99 %d max %d'
      % (c[len(c)//2], c[3*len(c)//4], c[int(len(c)*.9)], c[int(len(c)*.95)],
         c[int(len(c)*.99)], c[-1]))
print('jobs with >=1 app: %d | >=5: %d | >=10: %d' % (
    len(c), sum(1 for x in c if x >= 5), sum(1 for x in c if x >= 10)))
cu = sorted(user_apps.values())
print('users with apps >= 5: %d (%.1f%% of %d) | >=10: %d | >=20: %d' % (
    sum(1 for x in cu if x >= 5), 100.0*sum(1 for x in cu if x >= 5)/len(cu), len(cu),
    sum(1 for x in cu if x >= 10), sum(1 for x in cu if x >= 20)))
print('users with 1 app: %d (%.1f%%)' % (sum(1 for x in cu if x == 1),
      100.0*sum(1 for x in cu if x == 1)/len(cu)))
json.dump({'apps': n, 'users_with_apps': len(user_apps), 'jobs_with_apps': len(job_apps),
           'density_pct': round(100*density, 6),
           'job_not_found': job_not_found, 'user_not_found': user_not_found,
           'win_mismatch_job': win_mismatch_job, 'win_mismatch_user': win_mismatch_user,
           'date_outside': date_outside, 'test_rows': test_rows,
           'jobs_total': len(jobs_info), 'max_jobid': max_jid,
           'users_total': len(users_info)},
          open(os.path.join(OUT, 'integrity.json'), 'w'), indent=1)
print('\nexamples:', ex_first)
