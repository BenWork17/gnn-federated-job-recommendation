# -*- coding: utf-8 -*-
"""KIEM CHUNG DOC LAP notebook t4: kiem tra tinh + kiem tra so lieu.
Khong tin bao cao cua agent, tu doc file.
"""
import json, os, re, ast

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
NB = os.path.join(ROOT, 'notebooks', '01_gnn_fl.ipynb')
PY = os.path.join(ROOT, 'notebooks', '01_gnn_fl_source.py')

print('=== 1. FILE TON TAI ===')
for p in (NB, PY):
    print(f'  {os.path.basename(p):26s} {os.path.getsize(p):8d} B  {"OK" if os.path.exists(p) else "MISSING"}')

print('\n=== 2. NOTEBOOK HOP LE JSON ===')
nb = json.load(open(NB, encoding='utf-8'))
cells = nb['cells']
code_cells = [c for c in cells if c['cell_type'] == 'code']
md_cells = [c for c in cells if c['cell_type'] == 'markdown']
print(f'  nbformat={nb.get("nbformat")} | tong {len(cells)} cell | code {len(code_cells)} | md {len(md_cells)}')

print('\n=== 3. PARSE MOI CELL ===')
fail = 0
for i, c in enumerate(code_cells):
    src = ''.join(c['source'])
    cleaned = '\n'.join('' if ln.strip().startswith(('!', '%')) else ln
                        for ln in src.splitlines())
    try:
        compile(cleaned, f'<cell{i}>', 'exec')
    except SyntaxError as e:
        fail += 1
        print(f'  CELL {i} SYNTAX ERROR: {e}')
print(f'  {"PASS" if fail == 0 else f"FAIL {fail}"} — {len(code_cells)} code cell parse OK')

print('\n=== 4. DUONG DAN LOCAL ===')
bad = []
for i, c in enumerate(code_cells):
    src = ''.join(c['source'])
    for m in re.finditer(r'E:[\\/]+2026|C:[\\/]+Users|E:[\\/]+DUT', src):
        bad.append((i, m.group(0)))
print(f'  {"PASS - khong co" if not bad else bad[:8]}')
# kiem ca trong .py
py_txt = open(PY, encoding='utf-8').read()
badpy = re.findall(r'E:[\\/]+2026|C:[\\/]+Users|E:[\\/]+DUT', py_txt)
print(f'  file .py: {"PASS" if not badpy else badpy[:5]}')

print('\n=== 5. CELL DAU TIEN CO DO MOI TRUONG ===')
first = ''.join(code_cells[0]['source'])
print(f'  "find_artifacts" co: {"find_artifacts" in first}')
print(f'  "/kaggle/input" co : {"/kaggle/input" in first}')
print(f'  "glob" co          : {"glob" in first}')
print(f'  "OUT" co           : {"OUT" in first}')

print('\n=== 6. KEY graph.npz — so voi du lieu that ===')
import numpy as np
g = np.load(os.path.join(ROOT, 'artifacts', 'v3', 'graph.npz'), allow_pickle=True)
real_keys = set(g.keys())
print(f'  key that ({len(real_keys)}): {sorted(real_keys)}')
used = set(re.findall(r"g\[['\"]([a-z_0-9]+)['\"]\]", py_txt))
used |= set(re.findall(r"data\[['\"]([a-z_0-9]+)['\"]\]", py_txt))
bogus = used - real_keys
print(f'  key notebook dung ({len(used)}): {sorted(used)}')
print(f'  key KHONG TON TAI: {"KHONG CO (PASS)" if not bogus else bogus}')

print('\n=== 7. HANG SO — so voi du lieu that ===')
checks = {
    '764364': (g['edge_index'].shape[1] == 764364),
    '264995': (int(g['n_nodes']) == 264995),
    '171807': (int(g['n_users']) == 171807),
    '84845':  (int(g['n_jobs']) == 84845),
    '583':    (int(g['n_occupations']) == 583),
    '7760':   (int(g['n_skills']) == 7760),
    '37957':  (int((g['edge_type'] == 0).sum() and g['test_mask'].sum()) == 37957),
}
for k, v in checks.items():
    print(f'  {k:8s} trong notebook={k in py_txt:5} | dung trong du lieu={v}')
et = g['edge_type']
for t, exp in enumerate([436893, 26678, 25866, 274927]):
    got = int((et == t).sum())
    print(f'  edge_type {t}: {got} (ky vong {exp}) {"OK" if got==exp else "LECH"}')

print('\n=== 8. FALLBACK test_clean_index ===')
print(f'  co fallback: {"test_clean_index" in py_txt}')
print(f'  tu tinh 880: {"880" in py_txt}')

print('\n=== 9. SCALE + DEVICE ===')
for kw in ('SCALE', 'tiny', 'small', 'full', 'cuda', 'torch_geometric', 'multiprocessing'):
    print(f'  {kw:18s} xuat hien: {kw in py_txt}')
