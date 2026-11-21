# -*- coding: utf-8 -*-
"""Đo TỈ LỆ LẤP ĐẦY thật của các cột then chốt, qua 100 dòng mẫu."""
import urllib.request, urllib.parse, json

UA = {'User-Agent': 'Mozilla/5.0'}
BASE = 'https://datasets-server.huggingface.co'

def get(path, **params):
    url = f'{BASE}/{path}?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))

def fill_rate(repo, cols, offset=0, length=100):
    sp = get('splits', dataset=repo)['splits'][0]
    rows = get('rows', dataset=repo, config=sp['config'], split=sp['split'],
               offset=offset, length=length)['rows']
    total = len(rows)
    print('=' * 92)
    print(f'{repo}  ({total} dòng lấy ở offset {offset}, split {sp["split"]})')
    for c in cols:
        vals = [r['row'].get(c) for r in rows]
        nonnull = [v for v in vals
                   if v is not None and str(v).strip() not in ('', 'None', 'nan')]
        pct = 100.0 * len(nonnull) / max(total, 1)
        ex = str(nonnull[0])[:80].replace('\n', ' ') if nonnull else '—'
        print(f'  {c:26s} {len(nonnull):3d}/{total}  {pct:5.1f}%   vd: {ex}')
    return rows

r = fill_rate('lukebarousse/data_jobs',
              ['company_name', 'job_skills', 'job_type_skills', 'job_location',
               'salary_year_avg', 'job_title_short'])

print('\n--- phân tích cột job_skills (dạng dict/text) ---')
import collections
kinds = collections.Counter()
for row in r:
    v = row['row'].get('job_skills')
    if v is None or str(v).strip() in ('', 'None', 'nan'):
        kinds['(rỗng)'] += 1
    else:
        s = str(v)
        kinds['json/dict' if s.strip().startswith('{') else 'text'] += 1
print(' ', dict(kinds))
for row in r[:3]:
    print('  job_skills raw:', str(row['row'].get('job_skills'))[:220])

fill_rate('xanderios/linkedin-job-postings',
          ['company_id', 'skills_desc', 'applies', 'views', 'title', 'location'])

print('\n--- company_id: bao nhiêu công ty phân biệt trong 100 dòng ---')
sp = get('splits', dataset='xanderios/linkedin-job-postings')['splits'][0]
rows = get('rows', dataset='xanderios/linkedin-job-postings', config=sp['config'],
           split=sp['split'], offset=0, length=100)['rows']
cids = {r['row'].get('company_id') for r in rows if r['row'].get('company_id') is not None}
print('  distinct company_id:', len(cids), '/ 100 dòng')
