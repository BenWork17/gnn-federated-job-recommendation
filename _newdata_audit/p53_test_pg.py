# -*- coding: utf-8 -*-
"""Test API chay voi Docker PostgreSQL that."""
import urllib.request, json, time, sys

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8020'

def get(u):
    with urllib.request.urlopen(u, timeout=90) as r:
        return json.loads(r.read().decode())

def post(u, b):
    req = urllib.request.Request(u, data=json.dumps(b).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())

print('=== /health ===')
h = get(BASE + '/health')
print(' ', h)

print('\n=== /api/graph/summary ===')
s = get(BASE + '/api/graph/summary')
print(' ', json.dumps(s, ensure_ascii=False))

print('\n=== /api/clients (3 dau) ===')
c = get(BASE + '/api/clients?limit=3')
print('  total:', c.get('total'), '| data_source:', c.get('data_source'))
for it in (c.get('items') or [])[:3]:
    print('   ', it)

print('\n=== /api/recommend user=1133690 ===')
t = time.perf_counter()
r = post(BASE + '/api/recommend', {'user_id': 1133690, 'k': 5})
el = (time.perf_counter() - t) * 1000
print(f'  thoi gian: {el:.0f} ms | so item: {len(r.get("items") or [])}')
for it in (r.get('items') or [])[:5]:
    print('   ', it.get('job_id'), '|', str(it.get('title'))[:40], '| score', round(it.get('score', 0), 3),
          '| skills', len(it.get('matched_skills') or []))

print('\n=== /api/train/start 10x4 (PG that) ===')
t = time.perf_counter()
j = post(BASE + '/api/train/start', {'n_clients': 10, 'rounds': 4, 'algorithm': 'fedavg', 'local_epochs': 1})
rid = j['run_id']
print('  run_id:', rid)
for i in range(20):
    time.sleep(2)
    st = get(f'{BASE}/api/train/status/{rid}')
    print(f"  t={(i+1)*2:2d}s status={st.get('status'):8s} round={st.get('round')}/{st.get('total_rounds')} "
          f"p50={st.get('latency_p50_ms')} participants={len(st.get('participants') or [])}")
    if st.get('status') in ('done', 'stopped', 'failed'):
        break
m = st.get('metrics') or []
if m:
    print('  metric dau :', m[0])
    print('  metric cuoi:', m[-1])
print('  data_source:', st.get('data_source'), '| simulated:', st.get('simulated_metrics'))
