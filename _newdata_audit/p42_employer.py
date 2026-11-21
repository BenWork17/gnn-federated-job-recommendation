# -*- coding: utf-8 -*-
"""Thu employer tu CareerBuilder: do PHU va CHAT LUONG that, tren TOAN BO jobs.tsv.
Muc tieu: co chia duoc FL theo nha tuyen dung khong, va neu co thi chat den dau.
"""
import csv, os, re, sys, collections

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
JOBS = os.path.join(BASE, "jobs.tsv")

TAG = re.compile(r'<[^>]{0,300}>')
WS = re.compile(r'\s+')
def detag(t):
    return WS.sub(' ', TAG.sub(' ', t)).strip()

# cac chien luoc
SUFFIX = re.compile(r'\b(Inc\.?|LLC|L\.L\.C\.?|Corp\.?|Corporation|Company|Co\.|Ltd\.?|LLP|L\.P\.|Group|Holdings|Enterprises|Associates|Partners|Services|Solutions|Technologies|Systems)\b')
EMAIL = re.compile(r'([a-z0-9][a-z0-9\-]*)\.[a-z]{2,6}$')
LEAD = re.compile(r'^(.{2,60}?)\s+(?:is|are)\s+(?:a|an|the|currently|now|seeking|looking|hiring|proud|one of|committed|dedicated)\b', re.I)
SEEKING = re.compile(r'^(.{2,60}?,?\s*(?:Inc|LLC|Corp|Company|Ltd|Group)\.?)\s+(?:is|has|seeks|seeking)', re.I)
HEADHUNT = {'randstadusa.com','roberthalf.com','volt.com','kellyservices.com','adecco.com','manpower.com',
            'aeronet.com','job.com','monster.com','careerbuilder.com','indeed.com','snagajob.com',
            'hire.com','staffmark.com','aerotek.com','kforce.com','teksystems.com','insightglobal.com'}

def first_line(d):
    t = detag(d)
    if not t:
        return ''
    # cau dau tien
    m = re.split(r'(?<=[.!?])\s', t, maxsplit=1)
    return m[0][:120] if m else t[:120]

n = 0
cov = collections.Counter()
companies = collections.defaultdict(set)   # strategy -> set(company)
head_hits = collections.Counter()
sample_pairs = collections.defaultdict(list)

with open(JOBS, encoding='utf-8', errors='replace', newline='') as f:
    rd = csv.reader(f, delimiter='\t')
    h = next(rd)
    i_desc, i_req, i_title = h.index('Description'), h.index('Requirements'), h.index('Title')
    for row in rd:
        if len(row) < 11:
            continue
        n += 1
        desc = row[i_desc]; req = row[i_req]
        text = desc + ' ' + req
        fl = first_line(desc)

        # S1: hậu tố pháp lý ở câu đầu
        m1 = SUFFIX.search(fl)
        if m1:
            name = fl[:m1.end()].strip()
            cov['S1_hau_to_phap_ly'] += 1
            companies['S1'].add(name.lower())
            if len(sample_pairs['S1']) < 6:
                sample_pairs['S1'].append(name)

        # S2: mẫu "X is a/the ..."
        m2 = LEAD.match(fl)
        if m2 and len(m2.group(1).split()) <= 8:
            name = m2.group(1).strip(' ,.')
            cov['S2_X_is_a'] += 1
            companies['S2'].add(name.lower())
            if len(sample_pairs['S2']) < 6:
                sample_pairs['S2'].append(name)

        # S3: email domain
        em = re.findall(r'[\w\.\-+]+@([\w\-]+)\.([a-z]{2,6})', text[:6000], re.I)
        if em:
            dom = (em[0][0] + '.' + em[0][1]).lower()
            cov['S3_email_domain'] += 1
            companies['S3'].add(dom)
            if len(sample_pairs['S3']) < 6:
                sample_pairs['S3'].append(dom)

        if n % 200000 == 0:
            print(f'  ...{n}', flush=True)

print(f'\n=== TONG: {n} job ===')
for k in ('S1_hau_to_phap_ly', 'S2_X_is_a', 'S3_email_domain'):
    c = cov[k]
    d = len(companies[k.split('_')[0]])
    print(f'{k:22s} phu {c:8d} ({100.0*c/n:5.2f}%)  {d:7d} gia tri phan biet  '
          f'{c/max(d,1):6.1f} job/gia tri')

print('\n--- mau S1 (hau to phap ly) ---')
for s in sample_pairs['S1']: print('   ', s)
print('--- mau S2 (X is a...) ---')
for s in sample_pairs['S2']: print('   ', s)
print('--- mau S3 (email domain) ---')
for s in sample_pairs['S3']: print('   ', s)

# chat luong S1: top gia tri
top1 = sorted(companies['S1'], key=lambda x: -sum(1 for _ in [0]))[:0]
print('\n--- kiem tra S1 co phai cong ty that: dem gia tri xuat hien nhieu lan ---')
freq = collections.Counter()
with open(JOBS, encoding='utf-8', errors='replace', newline='') as f:
    rd = csv.reader(f, delimiter='\t'); h = next(rd)
    i_desc = h.index('Description')
    m = 0
    for row in rd:
        if len(row) < 11: continue
        m += 1
        fl = first_line(row[i_desc])
        mm = SUFFIX.search(fl)
        if mm:
            freq[fl[:mm.end()].strip().lower()] += 1
        if m >= 300000: break
print('  top 12 gia tri S1 (300k job dau):')
for v, c in freq.most_common(12):
    print(f'    {c:6d}  {v[:70]}')
print(f'  gia tri chi xuat hien 1 lan: {sum(1 for x in freq.values() if x == 1)}/{len(freq)}')
