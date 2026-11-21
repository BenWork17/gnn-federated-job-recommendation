# -*- coding: utf-8 -*-
"""In raw response để hiểu cấu trúc, rồi mới parse."""
import urllib.request, urllib.parse, json, sys

UA = {'User-Agent': 'Mozilla/5.0'}
BASE = 'https://datasets-server.huggingface.co'

def raw(path, **params):
    url = f'{BASE}/{path}?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode('utf-8', 'replace')), None
    except Exception as e:
        return None, f'{type(e).__name__}: {str(e)[:150]}'

for repo in ['aida-ugent/JobHop', 'xanderios/linkedin-job-postings']:
    print('=' * 90)
    print(repo)
    d, err = raw('info', dataset=repo)
    if err:
        print('  FAIL', err)
        continue
    print('  keys:', list(d.keys()))
    di = d.get('dataset_info')
    print('  dataset_info type:', type(di).__name__)
    if isinstance(di, dict):
        di = [di]
    for fi in (di or [])[:1]:
        print('  config keys:', list(fi.keys()) if isinstance(fi, dict) else type(fi))
        feats = fi.get('features') if isinstance(fi, dict) else None
        print('  features type:', type(feats).__name__)
        if isinstance(feats, dict):
            for k, v in feats.items():
                print('    %-32s %s' % (k, json.dumps(v)[:90]))
        elif isinstance(feats, list):
            for f in feats:
                print('    ', json.dumps(f)[:120])
        print('  splits:', json.dumps(fi.get('splits'))[:300] if isinstance(fi, dict) else '')
    # thử splits endpoint
    d2, err2 = raw('splits', dataset=repo)
    if not err2:
        print('  splits endpoint:', json.dumps(d2)[:400])
    else:
        print('  splits FAIL', err2)
