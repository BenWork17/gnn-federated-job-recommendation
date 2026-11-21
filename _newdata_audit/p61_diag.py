# -*- coding: utf-8 -*-
"""Chan doan: tai sao trang ket_luan chi render 412 ky tu, bang dataframe khong hien?
Chay Streamlit, bat stderr de thay exception, va do innerText tung phan.
"""
import json, os, subprocess, sys, time
import urllib.request

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
PORT = 8605
BASE = f'http://127.0.0.1:{PORT}'
LOG = os.path.join(ROOT, '_newdata_audit', 'st_err.log')

env = dict(os.environ)
env['MPLCONFIGDIR'] = os.path.join(ROOT, 'artifacts', '.mplcache')
logf = open(LOG, 'w', encoding='utf-8')
proc = subprocess.Popen(
    [sys.executable, '-m', 'streamlit', 'run', 'app/streamlit_app.py',
     '--server.headless=true', f'--server.port={PORT}',
     '--logger.level=debug', '--browser.gatherUsageStats=false'],
    cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT)

for i in range(40):
    time.sleep(2)
    try:
        urllib.request.urlopen(BASE, timeout=3)
        break
    except Exception:
        pass

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--window-size=1920,1400')
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
d = webdriver.Chrome(options=opts)
d.set_window_size(1920, 1400)

try:
    d.get(f'{BASE}/ket-luan')
    for _ in range(50):
        n = d.execute_script(
            "const b=document.querySelector('.block-container'); return b?b.innerText.length:0;")
        if n and n > 200:
            break
        time.sleep(0.4)
    time.sleep(2)

    info = d.execute_script("""
      const b = document.querySelector('.block-container');
      const main = document.querySelector('[data-testid="stMain"]') || document.querySelector('section.main');
      return {
        blockText: b ? b.innerText.length : -1,
        blockH: b ? Math.round(b.getBoundingClientRect().height) : -1,
        mainScrollH: main ? main.scrollHeight : -1,
        mainClientH: main ? main.clientHeight : -1,
        docScrollH: document.documentElement.scrollHeight,
        tables: document.querySelectorAll('[data-testid="stDataFrame"]').length,
        exceptions: document.querySelectorAll('[data-testid="stException"]').length,
        alerts: document.querySelectorAll('[data-testid="stAlert"]').length,
        headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(h=>h.innerText.slice(0,40)),
      };
    """)
    print('=== KET QUA DO ===')
    for k, v in info.items():
        print(f'  {k}: {v}')

    txt = d.execute_script("const b=document.querySelector('.block-container'); return b?b.innerText:'';")
    print('\n=== 500 KY TU DAU ===')
    print(txt[:500].replace('\n', ' | '))
    print('\n=== 500 KY TU CUOI ===')
    print(txt[-500:].replace('\n', ' | '))

    # tim element bao loi
    errs = d.execute_script("""
      const out = [];
      document.querySelectorAll('[data-testid="stException"], [data-testid="stAlert"]').forEach(e => {
        out.push(e.innerText.slice(0, 300));
      });
      return out;
    """)
    print('\n=== ALERT / EXCEPTION TREN TRANG ===')
    for e in errs:
        print('  -', e.replace('\n', ' | ')[:280])

    logs = d.get_log('browser')
    sev = [l for l in logs if l['level'] == 'SEVERE']
    print(f'\n=== CONSOLE SEVERE: {len(sev)} ===')
    for l in sev[:5]:
        print('  ', l['message'][:200])

    d.save_screenshot(os.path.join(ROOT, 'ui', 'screenshots', 'diag-ket-luan-full.png'))
finally:
    d.quit()
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    logf.close()

print('\n=== stderr CUA STREAMLIT: dong co loi ===')
try:
    txt = open(LOG, encoding='utf-8', errors='replace').read()
    keys = [l for l in txt.splitlines()
            if any(k in l for k in ('Error', 'Traceback', 'Exception', 'raise ', 'File "'))]
    if not keys:
        print('  khong co loi nao')
    for l in keys[-30:]:
        print('  ', l[:180])
except Exception as e:
    print('  khong doc duoc log:', e)
