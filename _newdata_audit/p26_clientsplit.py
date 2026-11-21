# -*- coding: utf-8 -*-
"""Chia client cho FL khi KHONG co cot employer -- phien ban gon, khong regex nang.

Chi doc:
  - users.tsv  (state cua user)
  - apps.tsv   (uid, jid, split)
  - jobs.tsv   (state cua job)  -> 1 lan quet, KHONG chay regex tren text lon

Bo hoan toan phan "khoi phuc employer tu text" (da do o p6_buckets.py: src 3.73%,
mail 13.07%) vi regex tren 3.4GB gay backtracking.
"""
import os, json, hashlib, collections, math

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"
R = {}

# ---------------- users ----------------
user_state, user_split = {}, {}
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        uid = int(p[0])
        user_state[uid] = p[4].strip()
        user_split[uid] = p[2]
print('users:', len(user_state), flush=True)

# ---------------- apps ----------------
apps = []
job_apps = collections.Counter()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        uid, jid = int(p[0]), int(p[4])
        apps.append((uid, jid, p[2], p[3][:10]))
        job_apps[jid] += 1
print('apps:', len(apps), flush=True)

R['apps_total'] = len(apps)
R['apps_train'] = sum(1 for a in apps if a[2] == 'Train')
R['apps_test'] = R['apps_total'] - R['apps_train']
R['users_total'] = len(user_state)

need = set(job_apps)

# ---------------- jobs: chi lay State + Title (1 lan quet) ----------------
job_state = {}
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    n = 0
    for raw in fh:
        # tach tay: chi can truong 0, 2, 6 -> tranh split toan bo dong dai
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        try:
            jid = int(p[0])
        except ValueError:
            continue
        if jid in need:
            job_state[jid] = p[6].strip()
            n += 1
            if n % 200000 == 0:
                print('  ...jobs matched %d' % n, flush=True)
print('jobs co app:', n, '/', len(need), flush=True)

# ---------------- phan vung ----------------
train = [a for a in apps if a[2] == 'Train']
tot = len(train)

def stats(vals):
    s = sorted(vals)
    return {'min': s[0], 'p25': s[len(s) // 4], 'median': s[len(s) // 2],
            'p75': s[3 * len(s) // 4], 'max': s[-1]}

# --- A. theo STATE cua user ---
clients_A = collections.defaultdict(list)
no_state = 0
for uid, jid, sp, dt in train:
    st = user_state.get(uid, '').strip()
    if not st:
        no_state += 1
        st = '??'
    clients_A[st].append((uid, jid))

sizes = sorted((len(v) for v in clients_A.values()), reverse=True)
R['partition_state'] = {
    'n_clients': len(clients_A),
    'apps_per_client': stats(sizes),
    'top5_share_pct': round(100.0 * sum(sizes[:5]) / tot, 1),
    'clients_ge_10000': sum(1 for s in sizes if s >= 10000),
    'clients_ge_1000': sum(1 for s in sizes if s >= 1000),
    'clients_lt_100': sum(1 for s in sizes if s < 100),
    'apps_missing_user_state': no_state,
}
print('\n=== [A] STATE ===', flush=True)
print('n_clients %d | app/client %s' % (len(clients_A), stats(sizes)), flush=True)
print('top5 share %.1f%%' % R['partition_state']['top5_share_pct'], flush=True)

# --- B. hash(user_id) % C ---
def hash_partition(C):
    ca = collections.defaultdict(list)
    for uid, jid, sp, dt in train:
        h = int(hashlib.md5(str(uid).encode()).hexdigest()[:8], 16) % C
        ca[h].append((uid, jid))
    return ca

hash_res = {}
for C in (12, 50, 100, 1000):
    ca = hash_partition(C)
    hash_res[str(C)] = {'n_clients': C, 'apps_per_client': stats(list(len(v) for v in ca.values()))}
R['partition_hash'] = hash_res
print('\n=== [B] hash(user_id) %% C ===')
for C, v in hash_res.items():
    print('C=%-4s %s' % (C, v['apps_per_client']), flush=True)

# --- C. tinh tap trung noi bang cua user ---
per_user_home = collections.Counter()
per_user_all = collections.Counter()
for uid, jid, sp, dt in train:
    us = user_state.get(uid, '').strip()
    js = job_state.get(jid, '')
    per_user_all[uid] += 1
    if us and js and us == js:
        per_user_home[uid] += 1
frac = sorted((per_user_home[u] / per_user_all[u]) for u in per_user_all)
R['user_home_state_concentration'] = {
    'n_users': len(frac),
    'mean_pct': round(100.0 * sum(frac) / len(frac), 1),
    'median_pct': round(100.0 * frac[len(frac) // 2], 1),
    'pct_users_100': round(100.0 * sum(1 for f in frac if f == 1.0) / len(frac), 1),
    'pct_users_ge_80': round(100.0 * sum(1 for f in frac if f >= 0.8) / len(frac), 1),
    'pct_users_lt_50': round(100.0 * sum(1 for f in frac if f < 0.5) / len(frac), 1),
}
print('\n=== [C] Tap trung noi bang cua user ===')
print(R['user_home_state_concentration'], flush=True)

# --- D. item dung chung giua cac bang (ro ri cheo client) ---
job_states = collections.defaultdict(set)
for uid, jid, sp, dt in train:
    st = user_state.get(uid, '').strip()
    if st:
        job_states[jid].add(st)
shared = {j: s for j, s in job_states.items() if len(s) >= 2}
apps_shared = sum(job_apps[j] for j in shared)
R['item_sharing_across_states'] = {
    'n_jobs_applied': len(job_states),
    'n_jobs_shared_ge2_states': len(shared),
    'pct_jobs_shared': round(100.0 * len(shared) / len(job_states), 1),
    'pct_apps_on_shared_jobs': round(100.0 * apps_shared / tot, 1),
}
print('\n=== [D] Item dung chung giua cac bang ===')
print(R['item_sharing_across_states'], flush=True)

# --- E. user xuat hien o bao nhieu bang ---
R['temporal'] = {}
dates = sorted(set(a[3] for a in train if a[3]))
R['temporal'] = {'min': dates[0], 'max': dates[-1], 'n_distinct_dates': len(dates)}
print('\n=== [E] Thoi gian ===', R['temporal'], flush=True)

# --- F. quy mo ---
user_apps_train = collections.Counter(uid for uid, jid, sp, dt in train)
R['users_train'] = len(user_apps_train)
for k in (1, 3, 5, 10):
    R['users_train_ge%d' % k] = sum(1 for c in user_apps_train.values() if c >= k)
print('\n=== [F] user (train) theo so app ===')
print({k: v for k, v in R.items() if k.startswith('users_train')}, flush=True)

json.dump(R, open(os.path.join(OUT, 'clientsplit.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('\nsaved clientsplit.json')
