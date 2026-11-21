# -*- coding: utf-8 -*-
"""Kiểm license các bộ có TƯƠNG TÁC thật — tiêu chí hạng nhất sau khi lộ license CareerBuilder."""
import urllib.request, urllib.parse, json

UA = {'User-Agent': 'Mozilla/5.0'}

def api(u):
    r = urllib.request.Request(u, headers=UA)
    return json.loads(urllib.request.urlopen(r, timeout=45).read().decode('utf-8', 'replace'))

print('=' * 96)
print('A) LICENSE CÁC BỘ HF CÓ TƯƠNG TÁC / RECRUITMENT')
for q in ['job interactions', 'job clicks', 'recruitment interaction',
          'olx jobs', 'job applications', 'hiring']:
    try:
        d = api('https://huggingface.co/api/datasets?search=' + urllib.parse.quote(q) + '&limit=8')
        print(f'\n--- search: {q} ({len(d)} ket qua) ---')
        for x in d:
            lic = (x.get('cardData') or {}).get('license', '?')
            print(f"  {x['id'][:52]:52s} lic={str(lic)[:16]:16s} dl={x.get('downloads')}")
    except Exception as e:
        print('  FAIL', q, type(e).__name__, str(e)[:80])

print('\n' + '=' * 96)
print('B) BO DA BIET — license chi tiet')
for repo in ['aida-ugent/JobHop', 'lukebarousse/data_jobs',
             'xanderios/linkedin-job-postings', 'xanderios/olx-jobs-interactions',
             'cnamuangtoun/resume-job-description-fit', 'arshkon/linkedin-job-postings']:
    try:
        d = api(f'https://huggingface.co/api/datasets/{repo}')
        cd = d.get('cardData') or {}
        print(f"  {repo:46s} license={cd.get('license')} / {cd.get('license_name')}")
        print(f"    {'':46s} downloads={d.get('downloads')} gated={d.get('gated')} private={d.get('private')}")
    except Exception as e:
        print(f'  {repo:46s} FAIL {type(e).__name__}: {str(e)[:70]}')
