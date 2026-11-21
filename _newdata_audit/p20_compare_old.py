# -*- coding: utf-8 -*-
"""So sánh nhanh bộ cũ (MEDAJob) với bộ mới trên cùng các tiêu chí."""
import os, json, statistics

art = r"E:\2026\DUT\DSS\SauGK\CuoiKi\artifacts\medajob"
import csv
jobs, users = [], []
with open(os.path.join(art, 'jobs.csv'), encoding='utf-8-sig') as fh:
    for r in csv.DictReader(fh):
        jobs.append(r)
with open(os.path.join(art, 'users.csv'), encoding='utf-8-sig') as fh:
    for r in csv.DictReader(fh):
        users.append(r)

sk = [len(r['skills'].split('|')) if r['skills'] else 0 for r in jobs]
print('=== BỘ CŨ (MEDAJob, sau làm sạch) ===')
print('jobs:', len(jobs), '| users:', len(users))
print('skills/job: mean %.2f median %d max %d | job 0 skill: %d'
      % (statistics.mean(sk), statistics.median(sk), max(sk), sum(1 for x in sk if x == 0)))
print('cột có sẵn:', list(jobs[0].keys()))
print('user có skills tường minh: %d/%d (%.0f%%)'
      % (sum(1 for u in users if u['skills']), len(users),
         100.0*sum(1 for u in users if u['skills'])/len(users)))
usk = [len(u['skills'].split('|')) if u['skills'] else 0 for u in users]
print('skills/user: mean %.2f median %d' % (statistics.mean(usk), statistics.median(usk)))
print('employer_id distinct: %d | company_name distinct: %d'
      % (len({r['employer_id'] for r in jobs}), len({r['company_name'] for r in jobs})))

meta = json.load(open(os.path.join(art, 'meta.json'), encoding='utf-8'))
print('\nmeta:', json.dumps({'raw': meta['raw'], 'clean': meta['clean'],
                             'sparsity_pct': meta['sparsity_pct']}, ensure_ascii=False, indent=1))
