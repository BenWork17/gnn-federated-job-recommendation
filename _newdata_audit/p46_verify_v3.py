# -*- coding: utf-8 -*-
"""KIEM TRA CHAT LUONG CLIENT trong artifacts/v3.
Van de: top20 employer toan staffing agency (randstad, spherion, volt...).
Do: ty le headhunt trong client, va anh huong len yeu cau #4 "chia nha tuyen dung".
"""
import json, re, os, collections
import numpy as np

V3 = r"E:\2026\DUT\DSS\SauGK\CuoiKi\artifacts\v3"

# ---- 1. graph.npz ----
g = np.load(os.path.join(V3, 'graph.npz'), allow_pickle=True)
print('=== graph.npz ===')
for k in g.files:
    a = g[k]
    print(f'  {k:22s} shape={str(a.shape):14s} dtype={a.dtype}')

meta = json.load(open(os.path.join(V3, 'meta.json'), encoding='utf-8'))
clients = json.load(open(os.path.join(V3, 'clients.json'), encoding='utf-8'))
if isinstance(clients, dict):
    print('\nclients.json la dict, keys:', list(clients.keys())[:8])
    clients = clients.get('clients', clients.get('items', []))
print(f'\n=== clients.json: {len(clients)} client ===')
print('mau:', json.dumps(clients[0], ensure_ascii=False)[:300] if clients else 'rong')

# ---- 2. phan loai headhunt ----
HEADHUNT_PAT = re.compile(
    r'(staff(ing)?|recruit|personnel|employment|talent|hire|placement|'
    r'randstad|spherion|volt|adecco|kelly|manpower|aerotek|kforce|teksystems|'
    r'insightglobal|staffmark|express ?(pros|employment)|select-?staffing|'
    r'allmedstaffing|ultimatestaffing|elitestaffing|webhrdept|selfopportunity|'
    r'careerlister|lcca|elitemed|mergis|officeteam|mriweb|mdi\b|workway|'
    r'collabera|superior technical|axisincorporated|ffres|printplace)', re.I)

real = head = unknown = 0
head_apps = real_apps = 0
examples_head, examples_real = [], []
for c in clients:
    name = str(c.get('name', c.get('employer_name', '')))
    n = int(c.get('n_apps', 0))
    if HEADHUNT_PAT.search(name):
        head += 1; head_apps += n
        if len(examples_head) < 15: examples_head.append((n, name))
    elif re.search(r'\.(com|org|net|edu|gov|us)\b', name) and not re.search(r'[a-z]{4,}', name.split('.')[0]):
        unknown += 1; real_apps += n
    else:
        real += 1; real_apps += n
        if len(examples_real) < 15: examples_real.append((n, name))

tot = head + real + unknown
tot_apps = head_apps + real_apps
print(f'\n=== PHAN LOAI {tot} CLIENT ===')
print(f'  HEADHUNT/staffing : {head:6d} ({100.0*head/tot:5.1f}%)  {head_apps:8d} app ({100.0*head_apps/max(tot_apps,1):5.1f}%)')
print(f'  CONG TY THAT      : {real:6d} ({100.0*real/tot:5.1f}%)  {real_apps:8d} app ({100.0*real_apps/max(tot_apps,1):5.1f}%)')
print(f'  DOMAIN/kho xac dinh: {unknown:5d} ({100.0*unknown/tot:5.1f}%)')

print('\n--- vi du HEADHUNT ---')
for n, e in examples_head[:12]: print(f'   {n:6d}  {e[:60]}')
print('\n--- vi du CONG TY THAT ---')
for n, e in examples_real[:12]: print(f'   {n:6d}  {e[:60]}')

# ---- 3. client lon nhat ----
print('\n=== 25 CLIENT LON NHAT ===')
for c in clients[:25]:
    name = str(c.get('name', c.get('employer_name', '')))
    flag = 'HEADHUNT' if HEADHUNT_PAT.search(name) else '   that '
    print(f"   {flag}  {int(c.get('n_apps',0)):5d} app  {name[:55]}")

# ---- 4. kiem tra ro ri train/test ----
print('\n=== KIEM TRA RO RI ===')
em = g['edge_index']; et = g['edge_type']
tr = g['train_mask']; te = g['test_mask']
print(f'edge_index shape={em.shape} | edge_type shape={et.shape}')
print(f'train_mask shape={tr.shape} sum={int(tr.sum())} | test_mask shape={te.shape} sum={int(te.sum())}')
if tr.shape == te.shape:
    overlap = int((tr & te).sum())
    print(f'GIAO train & test: {overlap}  {"OK" if overlap==0 else "!!! RO RI !!!"}')
uj = (et == 0)
print(f'canh user-job: {int(uj.sum())} (co huong, = 2x vo huong)')
print(f'  trong do train: {int((tr & uj).sum())} | test: {int((te & uj).sum())}')
