import os, re, collections, json
BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
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
train=[]; job_apps=collections.Counter()
with open(os.path.join(BASE,'apps.tsv'),'rb') as fh:
    fh.readline()
    for raw in fh:
        p=raw.decode('utf-8','replace').rstrip('\r\n').split('\t')
        if len(p)!=5 or p[2]!='Train': continue
        train.append((int(p[0]),int(p[4]))); job_apps[int(p[4])]+=1
need=set(job_apps)
jb={}
with open(os.path.join(BASE,'jobs.tsv'),'rb') as fh:
    fh.readline()
    for raw in fh:
        p=raw.decode('utf-8','replace').rstrip('\r\n').split('\t')
        if len(p)!=11: continue
        try: jid=int(p[0])
        except ValueError: continue
        if jid not in need: continue
        hit='Other'
        for name,rx in BUCKETS:
            if rx.search(p[2]): hit=name; break
        jb[jid]=hit
ub=collections.defaultdict(set)
for u,j in train: ub[u].add(jb.get(j,'Other'))
n=len(ub); multi=sum(1 for s in ub.values() if len(s)>1)
mean=sum(len(s) for s in ub.values())/n
print('users:',n)
print('mean bucket-clients per user: %.2f' % mean)
print('users in EXACTLY 1 bucket-client: %d (%.1f%%)' % (n-multi, 100.0*(n-multi)/n))
print('users in >=2 bucket-clients: %d (%.1f%%)' % (multi, 100.0*multi/n))
