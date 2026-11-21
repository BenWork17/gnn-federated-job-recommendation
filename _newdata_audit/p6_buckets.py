# -*- coding: utf-8 -*-
"""Đặc điểm split, phân bố ngành nghề, khả năng khôi phục employer."""
import os, re, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

# ---------- 1. Đặc điểm user theo split ----------
user_split = {}
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 15:
            continue
        user_split[int(p[0])] = p[2]

apps_by_user = collections.Counter()
user_split_app = {}
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        uid = int(p[0])
        apps_by_user[uid] += 1
        user_split_app[uid] = p[2]

print('=== Phân bố số app theo split (user-level) ===')
for sp in ('Train', 'Test'):
    c = sorted(apps_by_user[u] for u in apps_by_user if user_split_app[u] == sp)
    print('%s: n_users=%d  mean=%.2f median=%d p90=%d p99=%d max=%d' % (
        sp, len(c), sum(c)/len(c), c[len(c)//2], c[int(len(c)*.9)], c[int(len(c)*.99)], c[-1]))
print('users trong users.tsv không có app nào:',
      sum(1 for u in user_split if u not in apps_by_user))

# ---------- 2. Ngành nghề theo title ----------
BUCKETS = [
    ('IT/Software', r'\b(software|developer|programmer|java|python|\.net|web|database|'
                    r'systems? engineer|network|cisco|it support|help desk|qa|'
                    r'data (analyst|scientist|engineer)|analyst programmer)\b'),
    ('Healthcare', r'\b(nurse|nursing|rn|lpn|medical|pharmac|therap|physician|'
                   r'dental|hygien|patient|clinical|cna|home health)\b'),
    ('Sales/Retail', r'\b(sales|retail|store|merchandis|cashier|account executive|'
                     r'business development|broker|agent)\b'),
    ('Office/Admin', r'\b(administrative|assistant|receptionist|secretary|clerk|'
                     r'bookkeep|accounting|office|data entry|coordinator)\b'),
    ('Engineering/Industrial', r'\b(engineer|mechanic|electrician|weld|hvac|cnc|'
                               r'manufactur|machin|maintenance|technician)\b'),
    ('Driving/Logistics', r'\b(driver|cdl|truck|warehouse|logistic|delivery|dispatch)\b'),
    ('Management', r'\b(manager|director|supervisor|management|vp|president)\b'),
    ('Education', r'\b(teacher|tutor|instructor|professor|education|childcare)\b'),
    ('Food/Hospitality', r'\b(cook|chef|server|waiter|waitress|bartender|hospitality|hotel)\b'),
    ('Finance', r'\b(financial|finance|bank|loan|credit|insurance|underwrit|tax)\b'),
    ('Legal/Social', r'\b(attorney|legal|paralegal|social work|counselor|case manager)\b'),
]
BUCKETS = [(n, re.compile(p, re.I)) for n, p in BUCKETS]

title_bucket = collections.Counter()
job_bucket = {}
n = 0
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        t = p[2]
        hit = 'Other'
        for name, rx in BUCKETS:
            if rx.search(t):
                hit = name
                break
        title_bucket[hit] += 1
        job_bucket[p[0]] = hit
print('\n=== Phân bố job theo nhóm title (toàn bộ %d job) ===' % n)
for k, v in title_bucket.most_common():
    print('  %-26s %8d  %5.1f%%' % (k, v, 100.0*v/n))

# app theo bucket
app_bucket = collections.Counter()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        app_bucket[job_bucket.get(p[4], 'Other')] += 1
tot = sum(app_bucket.values())
print('\n=== Phân bố APPLICATION theo nhóm job ===')
for k, v in app_bucket.most_common():
    print('  %-26s %8d  %5.1f%%' % (k, v, 100.0*v/tot))

# ---------- 3. Khả năng khôi phục employer ----------
pat_src = re.compile(r'Source\s*[-\u2013\u2014]\s*([^\r\n]{3,60})', re.I)
pat_mail = re.compile(r'[\w\.\-]+@[\w\.\-]+\.\w{2,}')
pat_company = re.compile(r'\b(Inc\b|LLC|L\.L\.C|Corp\b|Corporation|Company\b|Ltd\b|LLP\b|LP\b)')
n = has_src = has_mail = has_co = 0
src_names = collections.Counter()
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for i, raw in enumerate(fh):
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        d = p[3] + ' ' + p[4]
        m = pat_src.search(d)
        if m:
            has_src += 1
            src_names[m.group(1).strip().lower()[:40]] += 1
        if pat_mail.search(d):
            has_mail += 1
        if pat_company.search(d[:1000]):
            has_co += 1
        if n >= 300000:
            break
print('\n=== Khôi phục employer từ text (%d job đầu) ===' % n)
print('mẫu "Source - X": %d (%.1f%%) | có email: %d (%.1f%%) | có hậu tố công ty: %d (%.1f%%)'
      % (has_src, 100.0*has_src/n, has_mail, 100.0*has_mail/n, has_co, 100.0*has_co/n))
print('top "Source":', src_names.most_common(8))

json.dump({'title_buckets': dict(title_bucket), 'app_buckets': dict(app_bucket),
           'src_pct': round(100.0*has_src/n, 2), 'mail_pct': round(100.0*has_mail/n, 2)},
          open(os.path.join(OUT, 'buckets.json'), 'w'), indent=1)
