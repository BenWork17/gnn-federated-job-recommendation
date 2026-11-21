# -*- coding: utf-8 -*-
"""Kiem tra 5 trang sau khi cac agent sua (2 agent chet giua chung)."""
import ast, os, re

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
PAGES = ['tong_quan', 'do_thi_viec_lam', 'fl_sim', 'goi_y', 'ket_luan']

print('=== TRANG THAI 5 TRANG ===')
for p in PAGES:
    f = os.path.join(ROOT, 'app', 'views', p + '.py')
    src = open(f, encoding='utf-8').read()
    lines = len(src.splitlines())
    ok = True
    try:
        ast.parse(src)
    except SyntaxError as e:
        ok = False
        print(f'  {p}: SYNTAX ERROR {e}')
        continue
    counts = {
        'grid': len(re.findall(r'theme\.grid', src)),
        'columns': len(re.findall(r'st\.columns\(', src)),
        'expander': len(re.findall(r'st\.expander\(', src)),
        'divider': len(re.findall(r'st\.divider\(', src)),
        'dataframe': len(re.findall(r'st\.dataframe\(', src)),
        'ucw': len(re.findall(r'use_container_width', src)),
        'metric_row': len(re.findall(r'metric_row\(', src)),
    }
    has_comment = bool(re.search(r'BỐ CỤC|Trước:|Nay:', src))
    print(f'  {p:18s} {lines:4d} dong  ' +
          '  '.join(f'{k}={v}' for k, v in counts.items()) +
          f'  comment_bocuc={"CO" if has_comment else "KHONG"}')

print('\n=== NOI DUNG KHAN CON NGUYEN? (mau so lieu) ===')
CHECKS = {
    'tong_quan': ['recall@20', 'fedavg', 'local_only'],
    'fl_sim': ['autoplay', 'selectbox', 'slider'],
    'goi_y': ['use_container_width', 'st.tabs'],
    'ket_luan': ['DP-SGD', 'secure aggregation', 'tổng hợp'],
    'do_thi_viec_lam': ['build_graph_view', 'show_private'],
}
for p, kws in CHECKS.items():
    f = os.path.join(ROOT, 'app', 'views', p + '.py')
    src = open(f, encoding='utf-8').read()
    miss = [k for k in kws if k not in src]
    print(f'  {p:18s} {len(kws)-len(miss)}/{len(kws)}' +
          (f'  THIEU {miss}' if miss else '  PASS'))

print('\n=== THEME.PY CO GRID() KHONG ===')
t = open(os.path.join(ROOT, 'app', 'components', 'theme.py'), encoding='utf-8').read()
print('  def grid:', 'def grid' in t)
print('  st-key-lx-grid:', 'st-key-lx-grid' in t)
print('  max-width 100%:', 'max-width: 100%' in t)
print('  con 1250px:', '1250px' in t)
print('  aria-expanded cho sidebar:', 'aria-expanded="true"' in t)
