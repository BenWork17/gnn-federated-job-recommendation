# -*- coding: utf-8 -*-
"""Pseudo-employer từ block Description + địa lý + khả năng lọc trùng."""
import os, re, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"
TAG = re.compile(r'<[^>]{0,300}>')
WS = re.compile(r'\s+')

block = {}
sample_title = {}
city_state = collections.Counter()
n = 0
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        d = WS.sub(' ', TAG.sub(' ', p[3])).strip()[:400].lower()
        block[p[0]] = d
        sample_title.setdefault(d, (p[2], p[5], p[6]))
        city_state[(p[5], p[6])] += 1
print('jobs:', n, '| distinct city,state:', len(city_state))
print('top city,state:', city_state.most_common(8))

size = collections.Counter(block.values())
print('\n=== Block Description (proxy cho "cùng một nhà tuyển dụng/chiến dịch") ===')
print('distinct block:', len(size))
big = sum(c for c in size.values() if c >= 5)
print('job nằm trong block >=5 bản sao: %d (%.1f%%)' % (big, 100.0*big/n))
print('job nằm trong block >=50 bản sao: %d (%.1f%%)'
      % (sum(c for c in size.values() if c >= 50), 100.0*sum(c for c in size.values() if c >= 50)/n))
print('job độc nhất (block size 1): %d (%.1f%%)'
      % (size and sum(1 for v in size.values() if v == 1),
         100.0*sum(1 for v in size.values() if v == 1)/n))
print('block lớn nhất:', size.most_common(1)[0][1])

# Ứng dụng rơi vào job trong block lớn
job_block_size = {int(j): size[d] for j, d in block.items()}
apps_block = collections.Counter()
tot = 0
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        tot += 1
        b = job_block_size.get(int(p[4]), 1)
        apps_block['>=50' if b >= 50 else ('5-49' if b >= 5 else ('2-4' if b >= 2 else '1'))] += 1
print('\nPhân bố APPLICATION theo kích thước block:')
for k in ('1', '2-4', '5-49', '>=50'):
    print('   %-6s %8d (%.1f%%)' % (k, apps_block.get(k, 0), 100.0*apps_block.get(k, 0)/tot))

json.dump({'distinct_blocks': len(size), 'jobs_in_block50': sum(c for c in size.values() if c >= 50),
           'distinct_city_state': len(city_state)},
          open(os.path.join(OUT, 'blocksum.json'), 'w'))
