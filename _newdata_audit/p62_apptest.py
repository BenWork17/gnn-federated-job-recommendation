# -*- coding: utf-8 -*-
"""Dung AppTest render ket_luan, liet ke TAT CA element theo thu tu."""
import os, sys

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
os.environ['DSH_VIEW'] = 'ket_luan'
os.environ.setdefault('MPLCONFIGDIR', os.path.join(ROOT, 'artifacts', '.mplcache'))
sys.path.insert(0, ROOT)

from streamlit.testing.v1 import AppTest

at = AppTest.from_file(os.path.join(ROOT, 'tests', '_view_runner.py'), default_timeout=180)
at.run()

print('=== EXCEPTION ===')
print(' ', [str(e.value)[:300] for e in at.exception])

print('\n=== DEM ELEMENT ===')
print(f'  markdown   : {len(at.markdown)}')
print(f'  dataframe  : {len(at.dataframe)}')
print(f'  subheader  : {len(at.subheader)}')
print(f'  info       : {len(at.info)}')
print(f'  warning    : {len(at.warning)}')
print(f'  caption    : {len(at.caption)}')
print(f'  expander   : {len(at.expander)}')
print(f'  columns    : {len(at.columns)}')

print('\n=== SUBHEADER THEO THU TU ===')
for i, s in enumerate(at.subheader):
    print(f'  [{i}] {str(s.value)[:70]}')

print('\n=== DATAFRAME ===')
for i, d in enumerate(at.dataframe):
    v = getattr(d, 'value', None)
    try:
        print(f'  [{i}] type={type(v).__name__} shape={getattr(v, "shape", "?")}')
    except Exception as e:
        print(f'  [{i}] khong doc duoc: {e}')

print('\n=== EXPANDER ===')
for i, e in enumerate(at.expander):
    print(f'  [{i}] label={getattr(e, "label", "?")}')

print('\n=== CAC MARKDOWN SAU CUNG (10 cai cuoi) ===')
for m in at.markdown[-10:]:
    t = str(m.value).replace('\n', ' ')
    print(f'  - {t[:90]}')

print('\n=== ELEMENT TREE (theo thu tu xuat hien) ===')
try:
    def walk(node, depth=0):
        name = getattr(node, 'type', type(node).__name__)
        val = getattr(node, 'value', '')
        s = str(val).replace('\n', ' ')[:55]
        print('  ' + '  ' * depth + f'{name}: {s}')
    for el in at.main[:60]:
        walk(el)
except Exception as e:
    print('  khong walk duoc:', e)
