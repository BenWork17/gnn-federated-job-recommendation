# -*- coding: utf-8 -*-
"""Phân tích nội dung: kỹ năng, ngành, chất lượng text trên sample jobs."""
import os, re, collections, json, statistics

OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"
path = os.path.join(OUT, 'jobs_sample.tsv')

rows = []
with open(path, encoding='utf-8') as fh:
    hdr = fh.readline().rstrip('\n').split('\t')
    for line in fh:
        p = line.rstrip('\n').split('\t')
        if len(p) != 11:
            continue
        rows.append(dict(zip(hdr, p)))
print('sample rows:', len(rows))

TAG = re.compile(r'<[^>]{0,400}>')
ENT = re.compile(r'&[a-zA-Z]{2,8};|&#\d{2,5};')
WS = re.compile(r'\s+')

def detag(t):
    t = TAG.sub(' ', t)
    t = ENT.sub(' ', t)
    return WS.sub(' ', t).strip()

lens_raw, lens_clean, ratio = [], [], []
ent_rows = 0
moji_rows = 0
dbl_esc = 0
for r in rows:
    d = r['Description']
    c = detag(d)
    lens_raw.append(len(d)); lens_clean.append(len(c))
    if len(d):
        ratio.append(len(c)/len(d))
    if ENT.search(d):
        ent_rows += 1
    if '\ufffd' in d or '\\ufffd' in d:
        moji_rows += 1
    if '\\r<' in d or '&lt;p&gt;' in d:
        dbl_esc += 1

def q(a, name):
    a = sorted(a)
    print('%s: median %d p10 %d p90 %d' % (name, a[len(a)//2], a[len(a)//10], a[int(len(a)*.9)]))
q(lens_raw, 'raw desc len'); q(lens_clean, 'clean desc len')
print('mean ratio clean/raw: %.2f' % (sum(ratio)/len(ratio)))
print('rows with HTML entities:', ent_rows, '| with mojibake U+FFFD:', moji_rows,
      '| double-escaped:', dbl_esc)

# --- HTML tags phổ biến
tags = collections.Counter()
for r in rows:
    for m in TAG.findall(r['Description'] + ' ' + r['Requirements']):
        name = re.match(r'</?\s*([a-zA-Z0-9]+)', m)
        if name:
            tags[name.group(1).lower()] += 1
print('top tags:', tags.most_common(20))

# --- Độ trùng lặp nội dung (near-duplicate)
def shingles(t, k=5):
    w = re.findall(r'[a-z0-9]+', t.lower())
    return {' '.join(w[i:i+k]) for i in range(max(0, len(w)-k+1))}
sig = []
for r in rows:
    sh = shingles(detag(r['Description'])[:6000])
    sig.append(sh)
pairs_above = collections.Counter()
dup_pairs = 0
example_pairs = []
n = len(sig)
# so sánh pairwise trên sample 500 cho nhanh
sub = list(range(min(n, 1200)))
import itertools
cnt = 0
for a, b in itertools.combinations(sub, 2):
    A, B = sig[a], sig[b]
    if not A or not B:
        continue
    j = len(A & B) / len(A | B)
    cnt += 1
    if j > 0.8:
        dup_pairs += 1
        if len(example_pairs) < 8:
            example_pairs.append((round(j, 3), rows[a]['Title'][:50], rows[b]['Title'][:50]))
print('\nnear-duplicate pairs (Jaccard>0.8) trong %d cặp: %d (%.2f%%)'
      % (cnt, dup_pairs, 100.0*dup_pairs/max(cnt, 1)))
for e in example_pairs:
    print('   ', e)

# --- Trùng Description y nguyên
desc_norm = collections.Counter()
for r in rows:
    desc_norm[detag(r['Description'])[:4000].lower()] += 1
print('\nDescription trùng y nguyên (exact, sau detag, top-10):')
for d, c in desc_norm.most_common(5):
    print('   %d x  %s' % (c, d[:110]))
print('số description distinct: %d / %d' % (len(desc_norm), len(rows)))

# --- Từ vựng kỹ năng: quét từ điển hẹp
SKILLS = {
 'python': r'\bpython\b', 'java': r'\bjava\b', 'javascript': r'\bjavascript\b',
 'sql': r'\bsql\b', 'c++': r'\bc\+\+', 'c#': r'\bc#', '.net': r'\b\.net\b',
 'excel': r'\bexcel\b', 'sap': r'\bsap\b', 'salesforce': r'\bsalesforce\b',
 'aws': r'\baws\b', 'azure': r'\bazure\b', 'linux': r'\blinux\b',
 'html': r'\bhtml\b', 'css': r'\bcss\b', 'react': r'\breact\b',
 'node': r'\bnode\.?js\b', 'oracle': r'\boracle\b', 'pharmacy': r'\bpharmac',
 'nursing': r'\bnurs(e|ing)\b', 'welding': r'\bweld', 'forklift': r'\bforklift\b',
 'cdl': r'\bcdl\b', 'hvac': r'\bhvac\b', 'cnc': r'\bcnc\b', 'electrician': r'\belectrician\b',
 'quickbooks': r'\bquickbooks\b', 'crm': r'\bcrm\b', 'aws': r'\baws\b',
 'machine learning': r'\bmachine learning\b', 'data analysis': r'\bdata analy',
}
cnt_skill = collections.Counter()
for r in rows:
    text = (r['Description'] + ' ' + r['Requirements']).lower()
    for k, pat in SKILLS.items():
        if re.search(pat, text):
            cnt_skill[k] += 1
print('\nTỉ lệ job (sample) nhắc tới kỹ năng (quét text tự do):')
tot = len(rows)
for k, c in cnt_skill.most_common():
    print('   %-18s %5d  (%.1f%%)' % (k, c, 100.0*c/tot))

# --- Có cột kỹ năng có cấu trúc? Không. Kiểm tra xem có mẫu "Skills:" không
pat_sec = re.compile(r'(skills?|qualifications?|requirements?)\s*:', re.I)
has_sec = sum(1 for r in rows if pat_sec.search(r['Requirements']))
print('\njob có tiêu đề mục "Skills/Qualifications/Requirements:" trong Requirements: %d (%.1f%%)'
      % (has_sec, 100.0*has_sec/tot))

# --- Trùng lặp giữa Description và Requirements
same = sum(1 for r in rows if detag(r['Description']).strip() and
           detag(r['Description']).strip() == detag(r['Requirements']).strip())
print('job có Description == Requirements (sau detag):', same)
print('job có Requirements rỗng/chỉ boilerplate:',
      sum(1 for r in rows if len(detag(r['Requirements'])) < 40))

# --- ví dụ text sạch
print('\n--- 3 ví dụ Description sau khi bóc HTML ---')
for i in (0, 5, 11):
    print('TITLE:', rows[i]['Title'])
    print('CLEAN:', detag(rows[i]['Description'])[:300].replace('\n', ' '))
    print()
