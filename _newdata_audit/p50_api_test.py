# -*- coding: utf-8 -*-
"""Test train endpoint that bang urllib (tranh PS cat chuoi)."""
import urllib.request, json, time, sys

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8012'

def post(u, b):
    req = urllib.request.Request(u, data=json.dumps(b).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())

def get(u):
    return json.loads(urllib.request.urlopen(u, timeout=30).read().decode())

j = post(BASE + '/api/train/start',
         {'n_clients': 10, 'rounds': 6, 'algorithm': 'fedavg', 'local_epochs': 1})
rid = j['run_id']
print('run_id:', rid)

s = None
for i in range(15):
    time.sleep(2)
    s = get(f'{BASE}/api/train/status/{rid}')
    parts = s.get('participants') or []
    print(f"  t={2*(i+1):2d}s status={s.get('status'):8s} round={s.get('round')}/{s.get('total_rounds')} "
          f"p50={s.get('latency_p50_ms')} p95={s.get('latency_p95_ms')} participants={len(parts)}")
    if s.get('status') in ('done', 'stopped', 'failed'):
        break

m = s.get('metrics') or []
print('\nso diem metric:', len(m))
if m:
    print('  dau :', m[0])
    print('  cuoi:', m[-1])

print('\ndata_source:', s.get('data_source'))
print('simulated_metrics:', s.get('simulated_metrics'))

# test stop
print('\n=== TEST STOP ===')
j2 = post(BASE + '/api/train/start', {'n_clients': 10, 'rounds': 40, 'algorithm': 'fedavg', 'local_epochs': 1})
rid2 = j2['run_id']
time.sleep(6)
r = post(f'{BASE}/api/train/stop/{rid2}', {})
print('stop ->', r)
s2 = get(f'{BASE}/api/train/status/{rid2}')
print('status sau stop:', s2.get('status'), '| stopped:', s2.get('stopped'),
      '| stopped_at_round:', s2.get('stopped_at_round'))
