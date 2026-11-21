# -*- coding: utf-8 -*-
"""Lượt cuối: trùng lặp job, nguồn đăng (newspaper), phân bố user theo bang, khối lượng app theo ngày."""
import os, re, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"
TAG = re.compile(r'<[^>]{0,300}>')
WS = re.compile(r'\s+')
def detag(t):
    return WS.sub(' ', TAG.sub(' ', t)).strip()

# ---- 1. trùng lặp job: (title, desc, city, state)
dupkey = collections.Counter()
n = 0
src_hits = collections.Counter()
NEWS = ["star telegram", "miami herald", "newsday", "arizona republic", "sun-sentinel",
        "charlotte observer", "wichita eagle", "chicago tribune", "baltimore sun",
        "denver post", "seattle times", "atlanta journal", "dallas morning news",
        "houston chronicle", "san jose mercury", "orlando sentinel", "tampa tribune",
        "pittsburgh post", "philadelphia inquirer", "detroit free press",
        "indianapolis star", "kansas city star", "sacramento bee", "fort worth",
        "careerbuilder", "monster", "indeed", "employment", "job"]
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        key = (p[2].strip().lower(), detag(p[3])[:300].lower(), p[5], p[6])
        dupkey[key] += 1
        low = detag(p[3]).lower()
        for nw in NEWS:
            if nw in low:
                src_hits[nw] += 1
                break
print('jobs:', n)
print('(title, desc-300, city, state) distinct:', len(dupkey))
print('job trùng lặp (không phải bản đầu): %d (%.1f%%)'
      % (n - len(dupkey), 100.0*(n-len(dupkey))/n))
sizes = collections.Counter(dupkey.values())
print('nhóm trùng kích thước >=10:', sum(1 for k, v in sizes.items() if k >= 10),
      '| job nằm trong nhóm >=10:', sum(k*v for k, v in sizes.items() if k >= 10))

# ---- 2. nguồn đăng
print('\n=== Tên báo/nguồn xuất hiện trong Description ===')
for k, v in src_hits.most_common(20):
    print('   %-24s %7d (%.1f%%)' % (k, v, 100.0*v/n))
print('job không khớp nguồn nào:', n - sum(src_hits.values()),
      '(%.1f%%)' % (100.0*(n-sum(src_hits.values()))/n))

# ---- 3. user theo bang + app theo ngày
uc = collections.Counter()
with open(os.path.join(BASE, 'users.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 15:
            uc[p[4]] += 1
print('\n=== Users theo State (top 12 / %d bang) ===' % len(uc))
for k, v in uc.most_common(12):
    print('   %-3s %6d (%.1f%%)' % (k, v, 100.0*v/389708))

daily = collections.Counter()
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) == 5:
            daily[p[3][:10]] += 1
d = sorted(daily.items())
print('\n=== Ứng tuyển theo ngày (87 ngày) ===')
print('ngày đầu:', d[0], '| ngày cuối:', d[-1])
print('cao nhất:', max(d, key=lambda kv: kv[1]), '| thấp nhất:', min(d, key=lambda kv: kv[1]))
print('5 ngày đông nhất:', sorted(d, key=lambda kv: -kv[1])[:5])
vals = [v for _, v in d]
print('median/ngày: %d | mean: %.0f' % (sorted(vals)[len(vals)//2], sum(vals)/len(vals)))
