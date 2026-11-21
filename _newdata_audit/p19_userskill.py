# -*- coding: utf-8 -*-
"""Kiểm tra đường đi khả thi để dựng cạnh user-skill (bộ mới KHÔNG có cột kỹ năng của user)."""
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
 'six sigma': r'\bsix sigma\b', 'iso 9001': r'\biso\s?9001\b',
}
RX = {k: re.compile(v, re.I) for k, v in LEX.items()}
TAG = re.compile(r'<[^>]{0,300}>')
WS = re.compile(r'\s+')
def detag(t):
    return WS.sub(' ', TAG.sub(' ', t)).strip()

# 1) Job -> skills từ text
job_skills = {}
n = 0
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        n += 1
        text = detag(p[3]) + ' ' + detag(p[4])
        found = [k for k, rx in RX.items() if rx.search(text)]
        if found:
            job_skills[p[0]] = found
print('job có >=1 skill (lexicon 52): %d / %d (%.1f%%)'
      % (len(job_skills), n, 100.0*len(job_skills)/n))
edges = sum(len(v) for v in job_skills.values())
print('tổng cạnh job-skill:', edges, '| trung bình %.2f/job có skill' % (edges/len(job_skills)))
sk = collections.Counter(s for v in job_skills.values() for s in v)
print('số kỹ năng phân biệt:', len(sk))
print('top:', sk.most_common(12))

# 2) User -> skills qua lịch sử nghề nghiệp: title history -> title job -> skills
title_skills = {}
for jid, s in job_skills.items():
    pass
# Xây title -> tập skill
tmap = collections.defaultdict(collections.Counter)
with open(os.path.join(BASE, 'jobs.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 11:
            continue
        t = p[2].strip().lower()
        if p[0] in job_skills:
            for s in job_skills[p[0]]:
                tmap[t][s] += 1
print('\nsố title (job) có skill:', len(tmap))

user_hist = collections.defaultdict(list)
with open(os.path.join(BASE, 'user_history.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        user_hist[p[0]].append(p[4].strip().lower())

hit_users = 0
covered = 0
tot_u = 0
for u, titles in user_hist.items():
    tot_u += 1
    s = set()
    for t in titles:
        if t in tmap:
            s.update(x for x, c in tmap[t].most_common(5))
    if s:
        hit_users += 1
        covered += len(s)
print('user có history:', tot_u)
print('user suy được >=1 skill qua title history: %d (%.1f%%)'
      % (hit_users, 100.0*hit_users/tot_u))
print('số skill trung bình/user suy được: %.2f' % (covered/max(hit_users, 1)))
print('\n=> CẢNH BÁO: đây là suy diễn 2 bước (title history -> title job -> skill từ text),')
print('   sai số chồng sai số. Bộ cũ có cột user_skills tường minh.')
