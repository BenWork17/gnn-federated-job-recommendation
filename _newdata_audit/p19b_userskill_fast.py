# -*- coding: utf-8 -*-
"""Bản nhanh: user-skill chỉ có thể suy qua title history (dùng sample 1% cho job->skill)."""
import os, re, collections, json, random

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

LEX = {
 'python': r'\bpython\b', 'java': r'\bjava\b(?!script)', 'javascript': r'\bjavascript\b',
 'sql': r'\bsql\b', 'c#': r'\bc#', 'c++': r'\bc\+\+', '.net': r'\.net\b',
 'excel': r'\bexcel\b', 'sap': r'\bsap\b', 'salesforce': r'\bsalesforce\b',
 'aws': r'\baws\b', 'azure': r'\bazure\b', 'linux': r'\blinux\b', 'html': r'\bhtml\b',
 'css': r'\bcss\b', 'react': r'\breact(js|\.js)?\b', 'oracle': r'\boracle\b',
 'quickbooks': r'\bquickbooks\b', 'crm': r'\bcrm\b', 'erp': r'\berp\b',
 'nursing': r'\bnurs(e|ing)\b', 'cpr': r'\bcpr\b', 'bls': r'\bbls\b', 'ehr': r'\behr\b',
 'welding': r'\bweld', 'hvac': r'\bhvac\b', 'cnc': r'\bcnc\b', 'forklift': r'\bforklift\b',
 'cdl': r'\bcdl\b', 'electrician': r'\belectrician\b', 'osha': r'\bosha\b',
 'customer service': r'\bcustomer service\b', 'bookkeeping': r'\bbookkeep',
 'accounts payable': r'\baccounts payable\b', 'accounts receivable': r'\baccounts receivable\b',
 'payroll': r'\bpayroll\b', 'medical billing': r'\bmedical billing\b', 'hipaa': r'\bhipaa\b',
 'project management': r'\bproject management\b', 'agile': r'\bagile\b',
 'bilingual': r'\bbilingual\b', 'supervisory': r'\bsupervis',
 'office management': r'\boffice manag', 'data entry': r'\bdata entry\b',
 'scheduling': r'\bschedul', 'inventory': r'\binventor', 'logistics': r'\blogistic',
 'quality assurance': r'\bquality assurance\b', 'lean': r'\blean\b',
 'six sigma': r'\bsix sigma\b',
}
RX = {k: re.compile(v, re.I) for k, v in LEX.items()}
TAG = re.compile(r'<[^>]{0,300}>')
WS = re.compile(r'\s+')
def detag(t):
    return WS.sub(' ', TAG.sub(' ', t)).strip()

# Job -> skill + title -> skill trên 5% mẫu (đủ để đánh giá độ phủ)
title_sk = collections.defaultdict(collections.Counter)
n = kept = 0
random.seed(3)
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        if random.random() > 0.05:
            continue
        kept += 1
        text = detag(p[3]) + ' ' + detag(p[4])
        found = [k for k, rx in RX.items() if rx.search(text)]
        if found:
            t = p[2].strip().lower()
            for s in found:
                title_sk[t][s] += 1
print('job quét: %d | có >=1 skill trong lexicon: %d (%.1f%%)'
      % (kept, sum(1 for c in title_sk.values() if c), 100.0*len(title_sk)/kept))
print('distinct title có skill:', len(title_sk))

# user history -> skill
user_hist = collections.defaultdict(list)
with open(os.path.join(BASE, 'user_history.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        user_hist[p[0]].append(p[4].strip().lower())

tot = hit = 0
sk_per_user = []
for u, titles in user_hist.items():
    tot += 1
    s = set()
    for t in titles:
        if t in title_sk:
            s.update(x for x, c in title_sk[t].most_common(5))
    if s:
        hit += 1
        sk_per_user.append(len(s))
sk_per_user.sort()
print('\nuser có history: %d | suy được >=1 skill (qua title): %d (%.1f%%)'
      % (tot, hit, 100.0*hit/tot))
if sk_per_user:
    print('skill/user: median %d p90 %d max %d'
          % (sk_per_user[len(sk_per_user)//2], sk_per_user[int(len(sk_per_user)*.9)], sk_per_user[-1]))
print('\nKẾT LUẬN: user-skill là suy diễn 2 bước, không có nguồn tường minh.')
