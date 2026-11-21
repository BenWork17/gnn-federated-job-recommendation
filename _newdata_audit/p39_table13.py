# -*- coding: utf-8 -*-
"""Bảng 13: t5 báo mean 37,93 / max 594 trên 798 nghề; t6 báo mean 35,41 / max 426 trên 923 nghề.
Kiểm xem khác nhau vì lý do gì — lọc theo CareerBuilder, hay đếm theo cột khác?
"""
import zipfile, collections, statistics, csv, os

Z = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t4_verify\db_29_3_text.zip"
zf = zipfile.ZipFile(Z)
raw = zf.read('db_29_3_text/Technology Skills.txt').decode('latin-1')
lines = raw.splitlines()
hdr = lines[0].split('\t')
rows = [l.split('\t') for l in lines[1:] if l.strip()]
print('header:', hdr)
print('rows:', len(rows))

i_soc = hdr.index('O*NET-SOC Code')
i_ex = hdr.index('Example')
i_cc = hdr.index('Commodity Code')

def stats(counter_map, label):
    c = sorted(len(v) for v in counter_map.values())
    print(f'  {label}: nghề={len(counter_map)} min={c[0]} median={c[len(c)//2]} '
          f'mean={statistics.mean(c):.2f} max={c[-1]}')

# A) đếm theo Example (như t6)
m_ex = collections.defaultdict(set)
for r in rows:
    m_ex[r[i_soc]].add(r[i_ex])
print('\nA) đếm Example phân biệt:')
stats(m_ex, 'Example')

# B) đếm theo Commodity Code
m_cc = collections.defaultdict(set)
for r in rows:
    m_cc[r[i_soc]].add(r[i_cc])
print('\nB) đếm Commodity Code phân biệt:')
stats(m_cc, 'CommodityCode')

# C) đếm RAW ROWS (có thể trùng)
m_raw = collections.Counter(r[i_soc] for r in rows)
print('\nC) đếm RAW ROWS (kể cả trùng):')
c = sorted(m_raw.values())
print(f'  nghề={len(c)} min={c[0]} median={c[len(c)//2]} mean={statistics.mean(c):.2f} max={c[-1]}')

# D) lọc theo SOC gốc 6 ký tự (CareerBuilder dùng SOC 6-digit?)
base_soc = {s.split('.')[0] for s in m_ex}
print(f'\nD) số SOC gốc (bỏ hậu tố .xx): {len(base_soc)}')
m_base = collections.defaultdict(set)
for r in rows:
    m_base[r[i_soc].split('.')[0]].add(r[i_ex])
stats(m_base, 'SOC-goc + Example')

print('\n=== KET LUAN ===')
print('Nếu t5 báo 798 nghề / mean 37,93 / max 594:')
print('  - 798 < 923 => PHẢI là lọc bớt, nhưng max TĂNG 426->594 là bất khả nếu cùng cách đếm.')
print('  - Kiểm xem có cách đếm nào ra max ~594 không.')
for label, m in [('Example', m_ex), ('CommodityCode', m_cc), ('SOC-goc', m_base)]:
    c = sorted(len(v) for v in m.values())
    print(f'  {label:15s} max={c[-1]:4d}  nghề={len(c)}')
from collections import Counter
rawc = sorted(m_raw.values())
print(f'  {"RawRows":15s} max={rawc[-1]:4d}  nghề={len(rawc)}')
