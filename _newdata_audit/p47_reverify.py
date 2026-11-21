# -*- coding: utf-8 -*-
"""KIEM CHUNG DOC LAP artifacts/v3 SAU KHI SUA.
Xac nhan: edge_type == edge_index[1] == mask; occupation coverage; client hop le.
"""
import json, os
import numpy as np

V3 = r"E:\2026\DUT\DSS\SauGK\CuoiKi\artifacts\v3"
g = np.load(os.path.join(V3, 'graph.npz'), allow_pickle=True)

print('=== SHAPE ===')
for k in ('edge_index', 'edge_type', 'train_mask', 'test_mask',
          'client_of_job', 'client_of_user', 'occ_ids', 'skill_names'):
    a = g[k]
    print(f'  {k:16s} {str(a.shape):16s} {a.dtype}')

ei, et = g['edge_index'], g['edge_type']
tr, te = g['train_mask'], g['test_mask']
okE = ei.shape[1] == et.shape[0] == tr.shape[0] == te.shape[0]
print(f'\n=== DONG NHAT DO DAI ===')
print(f'  edge_index[1]={ei.shape[1]} edge_type={et.shape[0]} train={tr.shape[0]} test={te.shape[0]}'
      f'  -> {"PASS" if okE else "FAIL"}')

print(f'\n=== RO RI ===')
print(f'  train&test = {int((tr & te).sum())}  -> {"PASS" if int((tr&te).sum())==0 else "FAIL"}')
print(f'  train={int(tr.sum())} test={int(te.sum())} tổng={int(tr.sum()+te.sum())} / {len(tr)}')

print(f'\n=== CANH THEO LOAI ===')
names = [str(x) for x in g['edge_type_names']] if 'edge_type_names' in g.files else ['0','1','2','3']
for t in range(4):
    m = et == t
    print(f'  type {t} ({names[t] if t < len(names) else "?"}): {int(m.sum()):8d}  '
          f'train={int((m&tr).sum()):8d} test={int((m&te).sum()):8d}')

print(f'\n=== DAI SO ===')
n = int(g['n_nodes']); nU = int(g['n_users']); nJ = int(g['n_jobs'])
nO = int(g['n_occupations']); nS = int(g['n_skills'])
print(f'  n_nodes={n} = {nU}+{nJ}+{nO}+{nS} -> {"PASS" if n==nU+nJ+nO+nS else "FAIL"}')
print(f'  offsets={list(g["offsets"])}')
print(f'  index min/max: {int(ei.min())}/{int(ei.max())} (phai trong [0,{n-1}]) '
      f'-> {"PASS" if int(ei.min())>=0 and int(ei.max())<n else "FAIL"}')
print(f'  cạnh tự trỏ: {int((ei[0]==ei[1]).sum())}')
print(f'  mã nghề dài 7: {all(len(str(x))==7 for x in g["occ_ids"])} (n={nO})')

print(f'\n=== CLIENT ===')
cj = g['client_of_job']; cu = g['client_of_user']
clients = json.load(open(os.path.join(V3, 'clients.json'), encoding='utf-8'))
if isinstance(clients, dict):
    clients = clients.get('clients', clients.get('items', []))
print(f'  clients.json: {len(clients)}')
apps = [int(c.get('n_apps', 0)) for c in clients]
print(f'  n_apps: min={min(apps)} median={sorted(apps)[len(apps)//2]} max={max(apps)}')
print(f'  client <10 app: {sum(1 for a in apps if a < 10)} -> {"PASS" if sum(1 for a in apps if a<10)==0 else "FAIL"}')
print(f'  client_of_job: min={int(cj.min())} max={int(cj.max())} | -1 (khong co client): {int((cj<0).sum())}')
print(f'  client_of_user: min={int(cu.min())} max={int(cu.max())} | -1: {int((cu<0).sum())}')
print(f'  client_id lien tuc: {sorted(int(c["client_id"]) for c in clients) == list(range(len(clients)))}')

print(f'\n=== OCCUPATION COVERAGE ===')
jo = et == 1
print(f'  job-occ cạnh: {int(jo.sum())} | job có cạnh nghề: {len(set(ei[0][jo].tolist()))}')
print(f'  job KHÔNG có nghề: {nJ - len(set(ei[0][jo].tolist()))} ({100.0*(nJ-len(set(ei[0][jo].tolist())))/nJ:.1f}%)')
print(f'  nghề được dùng trong job-occ: {len(set(ei[1][jo].tolist()))}')

print(f'\n=== SKILL LAYER ===')
os_ = et == 2
src = set(ei[0][os_].tolist()); dst = set(ei[1][os_].tolist())
print(f'  occ-skill cạnh: {int(os_.sum())} | nghề có skill: {len(src)}/{nO}')
print(f'  skill được dùng: {len(dst)}/{nS}')
# kiem entropy: co nghe nao du skill khong
from collections import Counter
per_occ = Counter(ei[0][os_].tolist())
cnts = sorted(per_occ.values())
print(f'  skill/nghề: min={cnts[0]} median={cnts[len(cnts)//2]} mean={sum(cnts)/len(cnts):.1f} max={cnts[-1]}')
print(f'  nghề có skill >= median: {sum(1 for c in cnts if c >= cnts[len(cnts)//2])}')
