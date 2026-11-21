# -*- coding: utf-8 -*-
"""Kiểm 3 bộ 'job-postings-applications' — có tương tác user-job + license gì?"""
import urllib.request, urllib.parse, json

UA = {'User-Agent': 'Mozilla/5.0'}

def get(u):
    r = urllib.request.Request(u, headers=UA)
    return json.loads(urllib.request.urlopen(r, timeout=50).read().decode('utf-8', 'replace'))

for repo in ['mindweave/job-postings-applications',
             'Arivalagan2025/job-postings-applications',
             'kunkrm/job-postings-applications']:
    print('=' * 96)
    print('DATASET:', repo)
    try:
        meta = get(f'https://huggingface.co/api/datasets/{repo}')
        cd = meta.get('cardData') or {}
        print('  license:', cd.get('license'), '| tags:', [t for t in meta.get('tags', []) if 'license' in t or 'size' in t][:6])
        print('  lastModified:', meta.get('lastModified'), '| downloads:', meta.get('downloads'))
    except Exception as e:
        print('  meta FAIL', type(e).__name__, str(e)[:90])
    try:
        info = get(f'https://datasets-server.huggingface.co/info?dataset={repo}')
        for cfg, fi in (info.get('dataset_info') or {}).items():
            print(f'  [config {cfg}]')
            for k, v in (fi.get('features') or {}).items():
                print(f'    - {k:30s} {json.dumps(v)[:80]}')
            for sp, sd in (fi.get('splits') or {}).items():
                print(f'    split {sp}: {sd.get("num_examples"):,}')
    except Exception as e:
        print('  info FAIL', type(e).__name__, str(e)[:90])
    try:
        sp = get(f'https://datasets-server.huggingface.co/splits?dataset={repo}')['splits'][0]
        fr = get(f'https://datasets-server.huggingface.co/rows?dataset={repo}&config={sp["config"]}&split={sp["split"]}&offset=0&length=2')
        for row in fr.get('rows', [])[:1]:
            print('  --- SAMPLE ---')
            for k, v in row['row'].items():
                print(f'    {k:28s} = {str(v)[:110]!r}')
    except Exception as e:
        print('  rows FAIL', type(e).__name__, str(e)[:90])
