# -*- coding: utf-8 -*-
"""Đọc schema thật qua HF datasets-server: dataset_info[config]."""
import urllib.request, urllib.parse, json

UA = {'User-Agent': 'Mozilla/5.0'}
BASE = 'https://datasets-server.huggingface.co'

def get(path, **params):
    url = f'{BASE}/{path}?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=50) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))

def probe(repo):
    print('=' * 100)
    print('DATASET:', repo)
    try:
        d = get('info', dataset=repo)
    except Exception as e:
        print('  info FAIL:', type(e).__name__, str(e)[:130]); return
    di = d.get('dataset_info') or {}
    for cfg, fi in di.items():
        print(f'  [config {cfg}]')
        feats = fi.get('features') or {}
        for k, v in feats.items():
            print(f'    - {k:32s} {json.dumps(v)[:100]}')
        for sp, sd in (fi.get('splits') or {}).items():
            print(f'    split {sp}: {sd.get("num_examples"):,} rows  bytes={sd.get("num_bytes")}')
        ds = (fi.get('dataset_size') or 0)
        print(f'    dataset_size: {ds/1e6:.1f} MB')
    try:
        sp = get('splits', dataset=repo)['splits'][0]
        fr = get('first-rows', dataset=repo, config=sp['config'], split=sp['split'])
        rows = fr.get('rows', [])[:1]
        if rows:
            print('  --- SAMPLE ROW ---')
            for k, v in rows[0]['row'].items():
                print(f'    {k:28s} = {str(v)[:100]!r}')
    except Exception as e:
        print('  first-rows FAIL:', type(e).__name__, str(e)[:110])

for repo in ['aida-ugent/JobHop', 'xanderios/linkedin-job-postings',
             'lukebarousse/data_jobs', 'cnamuangtoun/resume-job-description-fit']:
    try:
        probe(repo)
    except Exception as e:
        print('TOP FAIL', repo, type(e).__name__, str(e)[:110])
