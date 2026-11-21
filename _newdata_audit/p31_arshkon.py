# -*- coding: utf-8 -*-
"""Kiểm arshkon/linkedin-job-postings (bộ nổi tiếng có job_skills.csv) qua HF API thường."""
import urllib.request, json

UA = {'User-Agent': 'Mozilla/5.0'}

def api(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))

for repo in ['arshkon/linkedin-job-postings']:
    print('=' * 90, '\n', repo)
    try:
        meta = api(f'https://huggingface.co/api/datasets/{repo}')
        print('  license:', (meta.get('cardData') or {}).get('license'))
        print('  downloads:', meta.get('downloads'), '| likes:', meta.get('likes'))
    except Exception as e:
        print('  api FAIL', type(e).__name__, str(e)[:100])
    for branch in ('main', 'refs%2Fconvert%2Fparquet'):
        try:
            tree = api(f'https://huggingface.co/api/datasets/{repo}/tree/{branch}?recursive=true')
            files = [(t['path'], t.get('size')) for t in tree if t['type'] == 'file']
            print(f'  [{branch}] {len(files)} files')
            for p, s in files[:40]:
                print(f'     {p:60s} {(s or 0)/1e6:8.2f} MB')
            break
        except Exception as e:
            print(f'  tree {branch} FAIL', type(e).__name__, str(e)[:90])
