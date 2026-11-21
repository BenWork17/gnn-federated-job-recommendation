# -*- coding: utf-8 -*-
"""Cau hinh client KHA THI cho FL tren bo CareerBuilder.

Van de phat hien tu p26: chia tho theo 189 bang -> cuc lech
(min 1, median 11, max 169.760 app). Khong dung duoc truc tiep.

Script nay thu cac cau hinh "gom nhom" de ra so client can bang hon:
  G1. Top-K bang lam client rieng, phan con lai gop 1 client "Rest"
  G2. Gom bang theo vung Census (4 vung) + top-K rieng
  G3. Nguong toi thieu: chi giu client co >= M app
Va do JSD phan bo "nhom nghe" giua cac client (dung lai regex nhe tren Title).
"""
import os, re, json, collections, math

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"
R = {}

# --- Census regions ---
NORTHEAST = {'CT','ME','MA','NH','RI','VT','NJ','NY','PA'}
MIDWEST = {'IL','IN','MI','OH','WI','IA','KS','MN','MO','NE','ND','SD'}
SOUTH = {'DE','FL','GA','MD','NC','SC','VA','DC','WV','AL','KY','MS','TN',
         'AR','LA','OK','TX'}
WEST = {'AZ','CO','ID','MT','NV','NM','UT','WY','AK','CA','HI','OR','WA'}
REGION = {}
for s in NORTHEAST: REGION[s] = 'Northeast'
for s in MIDWEST: REGION[s] = 'Midwest'
for s in SOUTH: REGION[s] = 'South'
for s in WEST: REGION[s] = 'West'

# --- industry buckets (nhe, chi tren Title) ---
BUCKETS = [
    ('IT/Software', re.compile(r'\b(software|developer|programmer|java|python|database|network|help desk|data (analyst|scientist|engineer))\b', re.I)),
    ('Healthcare', re.compile(r'\b(nurse|nursing|medical|pharmac|therap|physician|dental|clinical|patient)\b', re.I)),
    ('Sales/Retail', re.compile(r'\b(sales|retail|store|cashier|merchandis|account executive)\b', re.I)),
    ('Office/Admin', re.compile(r'\b(administrative|assistant|receptionist|secretary|clerk|bookkeep|accounting|coordinator)\b', re.I)),
    ('Engineering/Industrial', re.compile(r'\b(mechanic|electrician|weld|hvac|cnc|manufactur|machinist|maintenance|technician)\b', re.I)),
    ('Driving/Logistics', re.compile(r'\b(driver|cdl|truck|warehouse|logistic|delivery|dispatch)\b', re.I)),
    ('Management', re.compile(r'\b(manager|director|supervisor|president)\b', re.I)),
    ('Finance', re.compile(r'\b(financial|finance|bank|loan|credit|insurance|underwrit)\b', re.I)),
]

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
        if len(p) != 5:
            continue
        if p[2] != 'Train':
            continue
        uid, jid = int(p[0]), int(p[4])
        train.append((uid, jid))
        job_apps[jid] += 1
need = set(job_apps)
tot = len(train)
print('train apps:', tot, '| users:', len(user_state), flush=True)

job_bucket = {}
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
        if jid not in need:
            continue
        t = p[2]
        hit = 'Other'
        for name, rx in BUCKETS:
            if rx.search(t):
                hit = name
                break
        job_bucket[jid] = hit
print('job bucket done:', len(job_bucket), flush=True)

def stats(vals):
    s = sorted(vals)
    return {'min': s[0], 'p25': s[len(s)//4], 'median': s[len(s)//2],
            'p75': s[3*len(s)//4], 'max': s[-1]}

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

def client_cat_dists(client_apps):
    """JSD trung binh theo trong so app: phan bo nhom nghe cua client vs toan cuc."""
    glob = collections.Counter()
    per = {}
    for cid, lst in client_apps.items():
        cc = collections.Counter(job_bucket.get(j, 'Other') for _, j in lst)
        per[cid] = cc
        glob.update(cc)
    ds, ws = [], []
    for cc in per.values():
        ds.append(jsd(cc, glob)); ws.append(sum(cc.values()))
    return sum(d*w for d,w in zip(ds,ws)) / sum(ws)

# ---- G0: tho theo state (baseline da biet) ----
by_state = collections.defaultdict(list)
for uid, jid in train:
    by_state[user_state.get(uid, '') or '??'].append((uid, jid))
s0 = sorted((len(v) for v in by_state.values()), reverse=True)
R['G0_raw_state'] = {'n_clients': len(by_state), 'apps': stats(s0),
                     'top5_share_pct': round(100.0*sum(s0[:5])/tot,1),
                     'clients_lt_1000': sum(1 for x in s0 if x < 1000),
                     'clients_lt_100': sum(1 for x in s0 if x < 100)}
print('\n[G0] state tho:', R['G0_raw_state'], flush=True)

# ---- G1: top-K state + Rest ----
G1 = {}
for K in (4, 6, 8, 10, 12, 16, 20):
    order = [s for s, _ in collections.Counter(
        (user_state.get(u,'') or '??') for u, j in train).most_common()]
    keep = set(order[:K])
    ca = collections.defaultdict(list)
    for uid, jid in train:
        st = user_state.get(uid, '') or '??'
        ca[st if st in keep else 'REST'].append((uid, jid))
    sz = sorted((len(v) for v in ca.values()), reverse=True)
    G1[str(K)] = {'n_clients': len(ca), 'apps': stats(sz),
                  'top1_share_pct': round(100.0*sz[0]/tot,1),
                  'jsd': round(client_cat_dists(ca), 4)}
R['G1_topK_state_plus_rest'] = G1
print('\n[G1] top-K state + Rest')
for K, v in G1.items():
    print('  K=%-3s n=%-3d %s top1=%.1f%% JSD=%.4f'
          % (K, v['n_clients'], v['apps'], v['top1_share_pct'], v['jsd']), flush=True)

# ---- G2: 4 vung Census ----
ca = collections.defaultdict(list)
for uid, jid in train:
    st = user_state.get(uid, '') or '??'
    ca[REGION.get(st, 'Other/NonUS')].append((uid, jid))
sz = sorted((len(v) for v in ca.values()), reverse=True)
R['G2_census_region'] = {'n_clients': len(ca), 'apps': stats(sz),
                         'top1_share_pct': round(100.0*sz[0]/tot,1),
                         'jsd': round(client_cat_dists(ca), 4),
                         'sizes': {k: len(v) for k, v in
                                   sorted(ca.items(), key=lambda kv: -len(kv[1]))}}
print('\n[G2] 4 vung Census:', R['G2_census_region'], flush=True)

# ---- G3: vung + top-K state rieng (mo rong) ----
G3 = {}
for K in (8, 12, 16):
    order = [s for s, _ in collections.Counter(
        (user_state.get(u,'') or '??') for u, j in train).most_common()]
    keep = set(order[:K])
    ca = collections.defaultdict(list)
    for uid, jid in train:
        st = user_state.get(uid, '') or '??'
        key = st if st in keep else REGION.get(st, 'Other/NonUS')
        ca[key].append((uid, jid))
    sz = sorted((len(v) for v in ca.values()), reverse=True)
    G3[str(K)] = {'n_clients': len(ca), 'apps': stats(sz),
                  'top1_share_pct': round(100.0*sz[0]/tot,1),
                  'jsd': round(client_cat_dists(ca), 4)}
R['G3_region_plus_topK'] = G3
print('\n[G3] Vung + top-K state rieng')
for K, v in G3.items():
    print('  K=%-3s n=%-3d %s top1=%.1f%% JSD=%.4f'
          % (K, v['n_clients'], v['apps'], v['top1_share_pct'], v['jsd']), flush=True)

json.dump(R, open(os.path.join(OUT, 'client_configs.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('\nsaved client_configs.json')
