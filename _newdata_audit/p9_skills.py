# -*- coding: utf-8 -*-
"""Đo khả thi trích xuất KỸ NĂNG từ text tự do (dữ liệu mới không có cột skill)."""
import os, re, collections, json, random, statistics

OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"
path = os.path.join(OUT, 'jobs_sample.tsv')

# Từ điển kỹ năng thử nghiệm: IT + y tế + công nghiệp + văn phòng
LEX = {
 'python': r'\bpython\b', 'java': r'\bjava\b(?!script)', 'javascript': r'\bjavascript\b',
 'sql': r'\bsql\b', 'c#': r'\bc#', 'c++': r'\bc\+\+', '.net': r'\.net\b',
 'excel': r'\bms\s?excel\b|\bexcel\b', 'sap': r'\bsap\b', 'salesforce': r'\bsalesforce\b',
 'aws': r'\baws\b', 'azure': r'\bazure\b', 'linux': r'\blinux\b',
 'html': r'\bhtml\b', 'css': r'\bcss\b', 'react': r'\breact(js|\.js)?\b',
 'node.js': r'\bnode\.?js\b', 'oracle': r'\boracle\b', 'quickbooks': r'\bquickbooks\b',
 'crm': r'\bcrm\b', 'erp': r'\berp\b', 'sharepoint': r'\bsharepoint\b',
 'photoshop': r'\bphotoshop\b', 'autocad': r'\bautocad\b', 'solidworks': r'\bsolidworks\b',
 'nursing': r'\bnurs(e|ing)\b', 'phlebotomy': r'\bphlebotom', 'cpr': r'\bcpr\b',
 'bls': r'\bbls\b', 'emt': r'\bemt\b', 'ehr': r'\behr\b|\bemr\b',
 'welding': r'\bweld', 'hvac': r'\bhvac\b', 'cnc': r'\bcnc\b', 'forklift': r'\bforklift\b',
 'cdl': r'\bcdl\b', 'electrician': r'\belectrician\b', 'plumbing': r'\bplumb',
 'osha': r'\bosha\b', 'lean': r'\blean\b', 'six sigma': r'\bsix sigma\b',
 'bilingual': r'\bbilingual\b', 'spanish': r'\bspanish\b',
 'customer service': r'\bcustomer service\b', 'bookkeeping': r'\bbookkeep',
 'accounts payable': r'\baccounts payable\b', 'accounts receivable': r'\baccounts receivable\b',
 'payroll': r'\bpayroll\b', 'adp': r'\badp\b', 'medical billing': r'\bmedical billing\b',
 'icd': r'\bicd[- ]?(9|10)\b', 'cpt': r'\bcpt\b', 'hipaa': r'\bhipaa\b',
 'machine learning': r'\bmachine learning\b', 'data analysis': r'\bdata analy',
 'project management': r'\bproject management\b', 'pmp': r'\bpmp\b',
 'agile': r'\bagile\b', 'scrum': r'\bscrum\b', 'jira': r'\bjira\b',
 'wms': r'\bwms\b', 'tms': r'\btms\b', 'gis': r'\bgis\b', 'arcgis': r'\barcgis\b',
}
RX = {k: re.compile(v, re.I) for k, v in LEX.items()}
TAG = re.compile(r'<[^>]{0,400}>')
ENT = re.compile(r'&[a-zA-Z]{2,8};|&#\d{2,5};')
WS = re.compile(r'\s+')
def detag(t):
    return WS.sub(' ', ENT.sub(' ', TAG.sub(' ', t))).strip()

rows = []
with open(path, encoding='utf-8') as fh:
    hdr = fh.readline().rstrip('\n').split('\t')
    for line in fh:
        p = line.rstrip('\n').split('\t')
        if len(p) == 11:
            rows.append(dict(zip(hdr, p)))

nskills = []
vocab = collections.Counter()
n = 0
for r in rows:
    text = detag(r['Description']) + ' ' + detag(r['Requirements'])
    found = [k for k, rx in RX.items() if rx.search(text)]
    nskills.append(len(found))
    for f in found:
        vocab[f] += 1
    n += 1

nskills.sort()
print('jobs trong sample:', n)
print('số kỹ năng/job: mean %.1f median %d p90 %d max %d' % (
    sum(nskills)/n, nskills[n//2], nskills[int(n*.9)], nskills[-1]))
print('job có >=1 kỹ năng: %d (%.1f%%)' % (sum(1 for x in nskills if x > 0),
      100.0*sum(1 for x in nskills if x > 0)/n))
print('job có >=3 kỹ năng: %d (%.1f%%)' % (sum(1 for x in nskills if x >= 3),
      100.0*sum(1 for x in nskills if x >= 3)/n))
print('job có 0 kỹ năng: %d (%.1f%%)' % (sum(1 for x in nskills if x == 0),
      100.0*sum(1 for x in nskills if x == 0)/n))
print('kích thước từ vựng khớp:', len(vocab))
print('top kỹ năng:', vocab.most_common(20))
