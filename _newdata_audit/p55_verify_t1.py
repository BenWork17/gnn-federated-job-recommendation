# -*- coding: utf-8 -*-
"""Kiem chung 4 khoi giai thich cua t1 trong ban inline va trong ui/ goc."""
import os, re

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
FILES = {
    'ui goc': os.path.join(ROOT, 'ui', 'index.html'),
    'app.js': os.path.join(ROOT, 'ui', 'assets', 'app.js'),
    'inline': os.path.join(ROOT, 'ui', '_inline', 'index_inline.html'),
}

texts = {k: open(p, encoding='utf-8').read() for k, p in FILES.items() if os.path.exists(p)}
print('=== KICH THUOC ===')
for k, p in FILES.items():
    if os.path.exists(p):
        print(f'  {k:10s} {os.path.getsize(p):>10,} B')

# 4 khoi phai co (tim trong ca 2 ban)
CHECKS = {
    '1. Panel mot node la gi': ['Một node là gì', 'application', 'ứng viên'],
    '2. So do 5 buoc':          ['BƯỚC 1', 'BƯỚC 5', 'FedAvg'],
    '3. O lai / Truyen di':     ['Ở LẠI', 'TRUYỀN ĐI', 'dữ liệu thô'],
    '4. Trace node':            ['idle', 'training', 'uploading', 'waiting'],
    'Canh bao mo phong':        ['mô phỏng', 'LightGCN 0,7151'],
    'Moi truong 1 may':         ['MỘT tiến trình', 'Không phải 9.116 máy'],
    'So client that':           ['9.116'],
}

for label, kws in CHECKS.items():
    print(f'\n--- {label} ---')
    for k, t in texts.items():
        hits = [kw for kw in kws if kw in t]
        miss = [kw for kw in kws if kw not in t]
        status = 'PASS' if not miss else f'thieu {miss}'
        print(f'  {k:10s} {len(hits)}/{len(kws)} -> {status}')

# kiem tra so cu con sot khong
print('\n=== SO CU CON SOT (14740 / 389708 / 1092096 trong ngu canh demo) ===')
for k, t in texts.items():
    for bad in ('14740', '14.740'):
        c = t.count(bad)
        if c:
            print(f'  {k}: "{bad}" x{c}')
    if '14740' not in t and '14.740' not in t:
        print(f'  {k}: SACH')

# byte dung dai
print('\n=== BYTE DUNG DAI (12800-15872 / 94208-97900) ===')
for k, t in texts.items():
    ok_up = bool(re.search(r'1[2-5][.,]?\d*\s*KB', t))
    print(f'  {k}: co "12-15 KB" -> {ok_up}')

# id phan tu cu con nguyen
print('\n=== ID PHAN TU CU ===')
ids = ['healthBadge','nodeGrid','clientBody','startBtn','stopBtn','runBadge',
       'log','chartRecall','chartLatency','detailBox','nClients','rounds',
       'algorithm','localEpochs']
t = texts.get('ui goc', '')
missing = [i for i in ids if f'id="{i}"' not in t]
print(f'  {len(ids)-len(missing)}/{len(ids)} id con nguyen')
if missing:
    print('  THIEU:', missing)
