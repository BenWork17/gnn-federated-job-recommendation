# -*- coding: utf-8 -*-
"""Do CHINH XAC non-IID cua cach chia theo bang.

Ket qua p27 cho thay JSD tren nhom nghe THO chi ~0.002 (gan IID). Can kiem tra:
  (a) JSD tren TIEU DE CU THE (top-N title) -- granularity min hon
  (b) Tinh "doc quyen item": bao nhieu % app cua client roi vao job chi client do dung
  (c) Jaccard item-set giua cac client
  (d) So sanh: JSD(state) vs JSD(hash) -- hash phai ~0 neu dung chuan
"""
import os, json, collections, math, hashlib

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"
R = {}

user_state = {}
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 15:
            user_state[int(p[0])] = p[4].strip()

train = []
job_apps = collections.Counter()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5 or p[2] != 'Train':
            continue
        uid, jid = int(p[0]), int(p[4])
        train.append((uid, jid))
        job_apps[jid] += 1
need = set(job_apps)
tot = len(train)
print('train apps:', tot, flush=True)

# --- lay Title cho cac job co app ---
job_title = {}
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        try:
            jid = int(p[0])
        except ValueError:
            continue
        if jid in need:
            job_title[jid] = p[2].strip().lower()
print('titles:', len(job_title), flush=True)

def jsd(p, q):
    keys = set(p) | set(q)
    sp, sq = sum(p.values()), sum(q.values())
    if sp == 0 or sq == 0: return 0.0
    d = 0.0
    for k in keys:
        a, b = p.get(k,0)/sp, q.get(k,0)/sq
        m = 0.5*(a+b)
        if a > 0: d += 0.5*a*math.log2(a/m)
        if b > 0: d += 0.5*b*math.log2(b/m)
    return d

def client_dists(client_apps, labeler):
    glob = collections.Counter(); per = {}
    for cid, lst in client_apps.items():
        cc = collections.Counter(labeler(j) for _, j in lst)
        per[cid] = cc; glob.update(cc)
    ds, ws = [], []
    for cc in per.values():
        ds.append(jsd(cc, glob)); ws.append(sum(cc.values()))
    return sum(d*w for d,w in zip(ds,ws)) / sum(ws)

# --- phan vung: state tho (chi client >= 1000 app de do cho on) ---
by_state = collections.defaultdict(list)
for uid, jid in train:
    by_state[user_state.get(uid, '') or '??'].append((uid, jid))
big_states = {k: v for k, v in by_state.items() if len(v) >= 1000}
print('client >=1000 app:', len(big_states), flush=True)

# --- ham label: title cu the + nhom title ---
R['jsd_by_state'] = {
    'on_exact_job_id': round(client_dists(big_states, lambda j: j), 4),
    'on_exact_title': round(client_dists(big_states, lambda j: job_title.get(j, '')), 4),
}

# --- hash baseline, cung n_clients ---
C = len(big_states)
by_hash = collections.defaultdict(list)
for uid, jid in train:
    if uid in user_state:
        by_hash[int(hashlib.md5(str(uid).encode()).hexdigest()[:8], 16) % C].append((uid, jid))
R['jsd_by_hash'] = {
    'n_clients': C,
    'on_exact_job_id': round(client_dists(by_hash, lambda j: j), 4),
    'on_exact_title': round(client_dists(by_hash, lambda j: job_title.get(j, '')), 4),
}
print('\nJSD state:', R['jsd_by_state'], flush=True)
print('JSD hash :', R['jsd_by_hash'], flush=True)

# --- (b) tinh doc quyen item ---
job_states = collections.defaultdict(set)
for uid, jid in train:
    st = user_state.get(uid, '').strip()
    if st: job_states[jid].add(st)

excl = {}; home = []
for st, lst in big_states.items():
    n = 0; ne = 0
    for uid, jid in lst:
        n += 1
        if job_states.get(jid) == {st}:
            ne += 1
    if n: excl[st] = round(100.0*ne/n, 1)
ws = sorted(excl.items(), key=lambda kv: -len(big_states[kv[0]]))
R['pct_apps_on_state_exclusive_jobs'] = {
    'per_state_top10': ws[:10],
    'weighted_mean': round(sum(excl[s]*len(big_states[s]) for s in excl)/sum(len(big_states[s]) for s in excl), 1),
}
print('\n%% app tren job chi 1 bang dung:', R['pct_apps_on_state_exclusive_jobs'], flush=True)

# --- (c) Jaccard item-set giua cac client lon ---
tops = sorted(big_states, key=lambda k: -len(big_states[k]))[:12]
sets = {s: set(j for _, j in big_states[s]) for s in tops}
jac = []
for i, a in enumerate(tops):
    for b in tops[i+1:]:
        inter = len(sets[a] & sets[b]); uni = len(sets[a] | sets[b])
        jac.append((a, b, round(100.0*inter/uni, 1)))
jac.sort(key=lambda x: -x[2])
R['item_jaccard_top12'] = {'pairs_n': len(jac), 'max': jac[0], 'min': jac[-1],
                           'median': jac[len(jac)//2]}
print('\nJaccard item-set:', R['item_jaccard_top12'], flush=True)

json.dump(R, open(os.path.join(OUT, 'nonIID.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('\nsaved nonIID.json')
