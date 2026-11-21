# -*- coding: utf-8 -*-
"""MUC TIEU: thoả yêu cầu #4 ("mỗi nhà tuyển dụng 1 node") TRÊN CareerBuilder.
Chien luoc: trich employer tu text -> chuan hoa -> gop cum -> do xem co du client de train.

Do:
  1. Phu employer sau khi chuan hoa (gop S1/S2/S3)
  2. So employer co >= N application
  3. % application phu duoc neu giu employer co >= N app
  4. So user trai nhieu employer (de bao cao trung thuc ve cross-silo)
"""
import csv, os, re, sys, collections, unicodedata

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"

TAG = re.compile(r'<[^>]{0,300}>')
WS = re.compile(r'\s+')
MOJI = re.compile(r'[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f]')

def detag(t):
    t = TAG.sub(' ', t or '')
    t = MOJI.sub(' ', t)
    return WS.sub(' ', t).strip()

# --- trích tên công ty ---
LEGAL = (r'(?:Inc|LLC|L\.L\.C|Corp|Corporation|Company|Co|Ltd|Limited|LLP|L\.P|LP|'
         r'Group|Holdings|Enterprises|Associates|Partners|PLC|GmbH|AG|SA|NV|BV)')
RX_LEGAL_END = re.compile(r'^(.{3,70}?)\s+' + LEGAL + r'\.?(?=[\s,;:)\-–—"”]|$)', re.I)
RX_IS_A = re.compile(r'^(.{3,60}?)\s*(?:,\s*)?(?:' + LEGAL + r'\.?\s*)?(?:is|are)\s+'
                     r'(?:a|an|the|one of|currently|now|seeking|looking|hiring|proud|committed|dedicated|'
                     r'national|leading|growing|global|full-service|premier)\b', re.I)
RX_EMAIL = re.compile(r'[\w\.\-+]+@([\w\-]{2,40})\.([a-z]{2,6})\b', re.I)
RX_ABOUT = re.compile(r'(?:about us|company summary|company overview)\s*:?\s*([A-Z][\w&\.\,\'\- ]{3,60})', re.I)

# từ vô nghĩa / nhãn rác
NOISE = {
    'company','group','the company','our company','client','confidential','a company','this company',
    'employer','organization','team','us','we','you','job','position','career','opportunity',
    'inc','llc','corp','ltd','the','a','an','and','of','for','with','is','are','we are',
    'now hiring','immediate opening','full time','part time','no corp','headquarters',
}
HEADHUNT = {
    'randstadusa.com','roberthalf.com','volt.com','kellyservices.com','adecco.com','manpower.com',
    'aerotek.com','kforce.com','teksystems.com','insightglobal.com','staffmark.com','job.com',
    'monster.com','careerbuilder.com','indeed.com','snagajob.com','hire.com','aol.com','yahoo.com',
    'hotmail.com','gmail.com','msn.com',
}
GENERIC_DOMAIN = {'aol.com','yahoo.com','gmail.com','hotmail.com','msn.com','comcast.net','att.net'}

def clean_name(s):
    s = detag(s).strip(' ,.;:-–—"”\'')
    s = re.sub(r'\([^)]{0,40}\)', ' ', s)          # bỏ ngoặc (M/F/D)...
    s = re.sub(r'\s{2,}', ' ', s).strip(' ,.;:-–—')
    low = s.lower()
    if len(low) < 3 or low in NOISE:
        return None
    if re.fullmatch(r'[\d\W]+', s):
        return None
    if len(s.split()) > 10:
        return None
    # phải có ít nhất 1 chữ hoa đầu từ
    if not re.search(r'[A-Z]', s):
        return None
    return s

def employer_from(desc, req):
    """Trả về (tên, nguồn) hoặc (None, None)."""
    d = detag(desc)
    if not d:
        return None, None
    head = d[:700]
    # câu đầu
    first = re.split(r'(?<=[.!?])\s+|\s{2,}', head, maxsplit=1)[0][:200]
    for text, src in ((first, 'S2_cau_dau'), (head, 'S3_dau_mo_ta')):
        m = RX_IS_A.match(text)
        if m:
            n = clean_name(m.group(1))
            if n:
                return n, src
        m = RX_LEGAL_END.match(text)
        if m:
            n = clean_name(m.group(1) + ' ' + m.group(0)[len(m.group(1)):].strip())
            if n:
                return n, src
    m = RX_ABOUT.search(head)
    if m:
        n = clean_name(m.group(1))
        if n:
            return n, 'S4_about_us'
    # email domain
    for dom, tld in RX_EMAIL.findall((desc or '')[:5000] + ' ' + (req or '')[:3000]):
        full = f'{dom}.{tld}'.lower()
        if full in GENERIC_DOMAIN or full in HEADHUNT:
            continue
        return full, 'S5_email'
    return None, None

# ---------- 1. trích employer cho toàn bộ job ----------
job_emp = {}
src_count = collections.Counter()
n = 0
with open(os.path.join(BASE, 'jobs.tsv'), encoding='utf-8', errors='replace', newline='') as f:
    rd = csv.reader(f, delimiter='\t')
    h = next(rd)
    ij, idesc, ireq = h.index('JobID'), h.index('Description'), h.index('Requirements')
    for row in rd:
        if len(row) < 11:
            continue
        n += 1
        e, s = employer_from(row[idesc], row[ireq])
        if e:
            job_emp[row[ij]] = e
            src_count[s] += 1
        if n % 250000 == 0:
            print(f'  ...{n}  (co employer: {len(job_emp)})', flush=True)

print(f'\n=== PHU EMPLOYER ===')
print(f'tong job: {n} | co employer: {len(job_emp)} ({100.0*len(job_emp)/n:.2f}%)')
print('nguon:', dict(src_count))

# ---------- 2. join sang application ----------
emp_apps = collections.Counter()
user_emps = collections.defaultdict(set)
emp_users = collections.defaultdict(set)
napp = 0
with open(os.path.join(BASE, 'apps.tsv'), encoding='utf-8', newline='') as f:
    rd = csv.reader(f, delimiter='\t')
    h = next(rd)
    iu, ij = h.index('UserID'), h.index('JobID')
    for row in rd:
        if len(row) < 5:
            continue
        napp += 1
        e = job_emp.get(row[ij])
        if not e:
            continue
        e = e.lower()
        emp_apps[e] += 1
        user_emps[row[iu]].add(e)
        emp_users[e].add(row[iu])

print(f'\n=== APPLICATION CO EMPLOYER ===')
cov = sum(emp_apps.values())
print(f'tong app: {napp} | app co employer: {cov} ({100.0*cov/napp:.2f}%)')
print(f'employer phan biet: {len(emp_apps)}')

# ---------- 3. bao nhieu client dung duoc ----------
print(f'\n=== CHIA THEO EMPLOYER: BAO NHIEU CLIENT DU HOC? ===')
print(f'{"ngưỡng":>10} | {"#client":>8} | {"app phủ":>10} | {"%app":>7} | {"user phủ":>10}')
for thr in (1, 5, 10, 20, 50, 100):
    kept = {e for e, c in emp_apps.items() if c >= thr}
    apps = sum(emp_apps[e] for e in kept)
    us = set()
    for e in kept:
        us |= emp_users[e]
    print(f'{thr:>10} | {len(kept):>8} | {apps:>10} | {100.0*apps/napp:>6.2f}% | {len(us):>10}')

# ---------- 4. cross-silo overlap (báo cáo trung thực) ----------
cnt = sorted(len(v) for v in user_emps.values())
if cnt:
    print(f'\n=== CROSS-SILO: user trai bao nhieu employer ===')
    print(f'user co employer: {len(user_emps)}')
    print(f'employer/user: min={cnt[0]} median={cnt[len(cnt)//2]} mean={sum(cnt)/len(cnt):.2f} max={cnt[-1]}')
    multi = sum(1 for x in cnt if x > 1)
    print(f'user trai >1 employer: {multi} ({100.0*multi/len(cnt):.1f}%)')
    print('=> cross-silo HOP LE: moi employer so huu "user X da ung tuyen vao tin CUA TOI".')
    print('   Day la kich ban that cua san tuyen dung, khong phai vi pham FL.')

# ---------- 5. gop cum employer -> K client ----------
print(f'\n=== GOP EMPLOYER THANH K CLIENT (moi client = 1 node) ===')
import hashlib
for K in (5, 8, 12, 21):
    buck = collections.defaultdict(lambda: [0, set()])
    for e, c in emp_apps.items():
        k = hashlib.md5(e.encode()).digest()[0] % K
        buck[k][0] += c
        buck[k][1] |= emp_users[e]
    sizes = sorted(v[0] for v in buck.values())
    print(f'  K={K:2d}: app/client min={sizes[0]:6d} median={sizes[len(sizes)//2]:6d} '
          f'max={sizes[-1]:6d} | client <10 app: {sum(1 for s in sizes if s<10)}/{K}')

import json
json.dump({'n_jobs': n, 'n_job_with_employer': len(job_emp),
           'n_apps': napp, 'n_app_with_employer': cov,
           'n_employers': len(emp_apps),
           'clients_thr': {str(t): len({e for e,c in emp_apps.items() if c>=t}) for t in (1,5,10,20,50,100)}},
          open(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t_employer_coverage.json", 'w'), indent=1)
