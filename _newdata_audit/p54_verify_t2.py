# -*- coding: utf-8 -*-
"""Kiem chung doc lap t2: inline hoa + dang ky Streamlit."""
import os, re, json, hashlib

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
INLINE = os.path.join(ROOT, 'ui', '_inline', 'index_inline.html')
STAPP = os.path.join(ROOT, 'app', 'streamlit_app.py')
VIEW = os.path.join(ROOT, 'app', 'views', 'giam_sat_node.py')
BUILD = os.path.join(ROOT, 'tools', 'build_ui_inline.py')

print('=== FILE ===')
for p in (BUILD, VIEW, INLINE):
    ok = os.path.exists(p)
    sz = os.path.getsize(p) if ok else 0
    print(f'  {os.path.basename(p):28s} {"OK" if ok else "MISSING":8s} {sz:>10,} B')

if not os.path.exists(INLINE):
    raise SystemExit('khong co file inline')

h = open(INLINE, encoding='utf-8').read()
print(f'\n=== INLINE ({len(h):,} ky tu) ===')
checks = {
    'con href="assets/app.css"': bool(re.search(r'href=["\']assets/app\.css', h)),
    'con src="assets/app.js"':   bool(re.search(r'src=["\']assets/app\.js', h)),
    'con src="vendor/chart':     bool(re.search(r'src=["\']vendor/chart', h)),
    'co <style>':                '<style' in h,
    'co Chart.js nhung':         'Chart' in h,
    'co app.js nhung':           'API_BASE' in h,
    'co font base64':            'base64' in h,
}
for k, v in checks.items():
    # 3 dong dau mong muon = False (khong con duong dan tuong doi)
    expect = False if k.startswith('con ') else True
    flag = 'PASS' if v == expect else 'FAIL'
    print(f'  {k:32s} {str(v):6s} (ky vong {expect}) -> {flag}')

s_open = len(re.findall(r'<script', h))
s_close = len(re.findall(r'</script>', h))
print(f'  the <script>={s_open} | </script>={s_close} -> {"PASS" if s_open == s_close else "FAIL"}')

st = len(re.findall(r'<style', h)); stc = len(re.findall(r'</style>', h))
print(f'  the <style>={st} | </style>={stc} -> {"PASS" if st == stc else "FAIL"}')

print('\n=== DANG KY STREAMLIT ===')
app = open(STAPP, encoding='utf-8').read()
print('  import giam_sat_node :', 'giam_sat_node' in app)
print('  url_path giam-sat-node:', 'giam-sat-node' in app)
print('  title Giám sát node   :', 'Giám sát node' in app)
# thu tu
order = re.findall(r'title="([^"]+)"', app)
print('  thu tu PAGES:', order)

print('\n=== VIEW giam_sat_node.py ===')
v = open(VIEW, encoding='utf-8').read()
print(f'  {len(v.splitlines())} dong')
for kw in ('components.html', '/health', 'uvicorn api.main:app', 'DEMO MODE', 'height=1400'):
    print(f'  co "{kw}":', kw in v)

print('\n=== SO SANH md5 inline voi ui/ hien tai ===')
cur = os.path.join(ROOT, 'ui', 'index.html')
def digest(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16] if os.path.exists(path) else None
print('  ui/index.html md5      :', digest(cur))
print('  (inline sinh tu ban nao khong kiem duoc truc tiep, can chay --check)')
