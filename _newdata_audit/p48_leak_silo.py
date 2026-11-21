# -*- coding: utf-8 -*-
"""KIEM CHUNG 3 WARN cua verifier + kiem tra silo that su.
Tap trung: (1) ro ri duong vong u-occ-j; (2) client co job de train khong;
(3) neu gan canh theo client_of_job thi moi client co bao nhieu canh train.
"""
import json, os
import numpy as np
from collections import Counter, defaultdict

V3 = r"E:\2026\DUT\DSS\SauGK\CuoiKi\artifacts\v3"
g = np.load(os.path.join(V3, 'graph.npz'), allow_pickle=True)
ei, et = g['edge_index'], g['edge_type']
tr, te = g['train_mask'], g['test_mask']
cj, cu = g['client_of_job'], g['client_of_user']
nU = int(g['n_users']); nJ = int(g['n_jobs'])
off_user, off_job = 0, nU
off_occ = nU + nJ

print('=== 1. RO RI DUONG VONG u-occ-j ===')
# canh train user-job
uj = et == 0
train_uj = uj & tr
test_uj = uj & te
print(f'canh user-job: train={int(train_uj.sum())} test={int(test_uj.sum())}')

# job -> tap occ (tu canh job-occ trong train)
jo = (et == 1) & tr
job2occ = defaultdict(set)
for s, d in zip(ei[0][jo].tolist(), ei[1][jo].tolist()):
    j = s - off_job
    o = d - off_occ
    if 0 <= j < nJ:
        job2occ[j].add(o)
print(f'job co canh nghề (train): {len(job2occ)}')

# user -> tap occ qua canh user-occ train
uo = (et == 3) & tr
user2occ = defaultdict(set)
for s, d in zip(ei[0][uo].tolist(), ei[1][uo].tolist()):
    u = s - off_user
    o = d - off_occ
    if 0 <= u < nU:
        user2occ[u].add(o)
print(f'user co canh nghề (train): {len(user2occ)}')

# test edge (u,j): co duong vong neu user2occ[u] giao job2occ[j] khac rong
ts_u = ei[0][test_uj].tolist()
ts_j = (ei[1][test_uj] - off_job).tolist()
leak = 0
for u, j in zip(ts_u, ts_j):
    ou = user2occ.get(u)
    oj = job2occ.get(j)
    if ou and oj and (ou & oj):
        leak += 1
n_test = len(ts_u)
print(f'canh test co duong vong: {leak}/{n_test} = {100.0*leak/n_test:.2f}%')
print(f'canh test SACH: {n_test-leak}')

# luu mask cho t4
clean = np.ones(n_test, dtype=bool)
k = 0
for i, (u, j) in enumerate(zip(ts_u, ts_j)):
    ou = user2occ.get(u); oj = job2occ.get(j)
    if ou and oj and (ou & oj):
        clean[i] = False
os.makedirs(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\v3_verify", exist_ok=True)
np.savez_compressed(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\v3_verify\test_clean_index.npz",
                    clean=clean, test_user=ei[0][test_uj], test_job=ei[1][test_uj])
print(f'da luu test_clean_index.npz ({int(clean.sum())} sach / {n_test})')

print('\n=== 2. CLIENT CO JOB DE TRAIN KHONG ===')
nC = int(cj.max()) + 1
job_per_client = Counter(cj.tolist())
print(f'client: {nC} | client co >=1 job: {len(job_per_client)}')
cnt = sorted(job_per_client.values())
print(f'job/client: min={cnt[0]} median={cnt[len(cnt)//2]} max={cnt[-1]}')

# canh train user-job theo client CUA JOB
uj_train_j = (ei[1][train_uj] - off_job)
edge_per_client = Counter(cj[uj_train_j].tolist())
cnt2 = sorted(edge_per_client.values())
print(f'client co >=1 canh train: {len(edge_per_client)}/{nC}')
print(f'canh train/client: min={cnt2[0]} median={cnt2[len(cnt2)//2]} mean={sum(cnt2)/len(cnt2):.1f} max={cnt2[-1]}')
for thr in (1, 10, 50, 100):
    print(f'  client >= {thr:4d} canh train: {sum(1 for x in cnt2 if x>=thr):5d}')

# client rong
empty = nC - len(edge_per_client)
print(f'client KHONG co canh train nao: {empty}')

print('\n=== 3. GAN CANH DUNG CACH ===')
print(f'43,15% khop neu dung client_of_user — do la SAI (nhan argmax, khong phai membership)')
match = sum(1 for u, j in zip(ts_u, ts_j) if cu[u] == cj[j])
print(f'canh test co client_of_user == client_of_job: {match}/{n_test} = {100.0*match/n_test:.2f}%')
print('=> Phai gan canh vao client_of_job[j].')

print('\n=== 4. TY LE TEST ===')
print(f'toan bo canh user-job: {int(uj.sum())} | test: {int(test_uj.sum())} = {100.0*int(test_uj.sum())/int(uj.sum()):.2f}%')
print(f'meta ghi test_ratio 0.2 nhung min_apps_for_test=5 -> chi user >=5 app moi co test')
