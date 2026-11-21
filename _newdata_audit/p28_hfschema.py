# -*- coding: utf-8 -*-
"""Đọc schema + dòng thật của dataset HF qua datasets-server (không cần tải file)."""
import urllib.request, urllib.parse, json

UA = {'User-Agent': 'Mozilla/5.0'}
BASE = 'https://datasets-server.huggingface.co'

def get(path, **params):
    url = f'{BASE}/{path}?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))

def probe(repo):
    print('=' * 100)
    print('DATASET:', repo)
    try:
        info = get('info', dataset=repo)
    except Exception as e:
        print('  info FAIL:', type(e).__name__, str(e)[:120])
        return
    rows = 0
    for fi in info.get('dataset_info', [{}]):
        feats = fi.get('features') or {}
        print('  features:')
        for k, v in feats.items():
            t = v.get('_type', v.get('dtype', '?'))
            print(f'    - {k:32s} {t}')
        for sp, sd in (fi.get('splits') or {}).items():
            n = sd.get('num_examples')
            print(f'  split {sp}: {n:,} rows' if n else f'  split {sp}: ?')
            rows = max(rows, n or 0)
        print('  size_bytes:', fi.get('size', {}).get('dataset'), '| download:', fi.get('download_size'))
    # rows thật
    for split in ('train',):
        try:
            fr = get('first-rows', dataset=repo, config='default', split=split)
            rws = fr.get('rows', [])[:2]
            if rws:
                print('  SAMPLE ROW 0:')
                for k, v in rws[0]['row'].items():
                    s = str(v).replace('\n', ' ')
                    print(f'    {k:28s} = {s[:110]}')
        except Exception as e:
            print('  first-rows FAIL:', type(e).__name__, str(e)[:100])

for repo in [
    'aida-ugent/JobHop',
    'arshkon/linkedin-job-postings',
    'xanderios/linkedin-job-postings',
    'lukebarousse/data_jobs',
    'cnamuangtoun/resume-job-description-fit',
    'akzaidan/Profile-Jobs-Ranked',
]:
    try:
        probe(repo)
    except Exception as e:
        print('TOP-LEVEL FAIL', repo, type(e).__name__, str(e)[:100])
