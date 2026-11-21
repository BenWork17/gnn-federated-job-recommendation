# -*- coding: utf-8 -*-
"""Ba bá»™ 'job-postings-applications' trÃ´ng hoÃ n háº£o â€” kiá»ƒm xem cÃ³ pháº£i dá»¯ liá»‡u Tá»”NG Há»¢P."""
import urllib.request, urllib.parse, json, collections

UA = {'User-Agent': 'Mozilla/5.0'}
BASE = 'https://datasets-server.huggingface.co'

def get(u):
    r = urllib.request.Request(u, headers=UA)
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode('utf-8', 'replace'))

def rows(repo, cfg, n=100):
    spl = get(f'{BASE}/splits?dataset={repo}')['splits']
    match = [s for s in spl if s['config'] == cfg]
    if not match:
        print(f'  [khong co config {cfg}; co: {[s["config"] for s in spl]}]')
        return []
    s = match[0]
    return get(f'{BASE}/rows?dataset={repo}&config={s["config"]}&split={s["split"]}'
               f'&offset=0&length={n}')['rows']

R = 'mindweave/job-postings-applications'
print('=' * 96)
print('DAU HIEU TONG HOP â€”', R)

apps = [x['row'] for x in rows(R, 'applications', 100)]
cands = [x['row'] for x in rows(R, 'candidates', 100)]
jobs = [x['row'] for x in rows(R, 'jobs', 100)]
comps = [x['row'] for x in rows(R, 'companies', 100)]

print('\n1) applications: stage / source / score')
print('  stage :', collections.Counter(a['stage'] for a in apps).most_common())
print('  source:', collections.Counter(a['source'] for a in apps).most_common())
sc = [a['score'] for a in apps if a['score'] is not None]
print(f'  score : min={min(sc):.3f} max={max(sc):.3f} distinct={len(set(sc))}/{len(sc)}')
print('    score values (first 12):', sc[:12])

print('\n2) candidates: tÃªn + top_skill_area')
print('  top_skill_area:', collections.Counter(c['top_skill_area'] for c in cands).most_common())
print('  ten mau:', [c['candidate_name'] for c in cands[:8]])
print('  city:', collections.Counter(c['current_city'] for c in cands).most_common(6))
yr = [c['years_experience'] for c in cands]
print(f'  years_experience: min={min(yr)} max={max(yr)} distinct={len(set(yr))}')

print('\n3) companies: industry / company_size / hq_city')
print('  industry:', collections.Counter(c['industry'] for c in comps).most_common(8))
print('  company_size:', collections.Counter(c['company_size'] for c in comps).most_common())
print('  hq_city top:', collections.Counter(c['hq_city'] for c in comps).most_common(6))
print('  ten cong ty mau:', [c['company_name'] for c in comps[:8]])

print('\n4) jobs: role_family / level / employment_type')
print('  role_family:', collections.Counter(j['role_family'] for j in jobs).most_common())
print('  level:', collections.Counter(j['level'] for j in jobs).most_common())
print('  employment_type:', collections.Counter(j['employment_type'] for j in jobs).most_common())
print('  status:', collections.Counter(j['status'] for j in jobs).most_common())
print('  title mau:', [j['title'] for j in jobs[:8]])
sal = [(j['salary_low'], j['salary_high']) for j in jobs if j['salary_low']]
print('  salary mau:', sal[:6])

print('\n5) DANH GIA')
issues = []
if len(set(sc)) < len(sc) * 0.3:
    issues.append(f'score chi co {len(set(sc))} gia tri phan biet tren {len(sc)} dong -> qua deu')
if len(set(c['candidate_name'] for c in cands)) < len(cands):
    issues.append('candidate_name bi lap')
if len(set(j['title'] for j in jobs)) < 10:
    issues.append(f"chi {len(set(j['title'] for j in jobs))} title khac nhau")
print('  VAN DE:', issues if issues else 'khong thay dau hieu ro rang')
print('\n  => So sanh: du lieu that KHONG bao gio co score tron nhu vay,')
print('     va 3 repo khac ten (mindweave/Arivalagan2025/kunkrm) co DU LIEU Y HET nhau')
print('     => dau hieu ro rang cua du lieu TONG HOP / sinh tu dong.')

