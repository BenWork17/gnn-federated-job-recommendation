# -*- coding: utf-8 -*-
"""KIEM CHUNG t4 bang Selenium: WebSocket trong iframe (srcdoc) co hoat dong khong.
Day la diem rui ro duy nhat con lai cua phuong an 1a.
"""
import json, os, sys, time
import urllib.request

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
INLINE = os.path.join(ROOT, 'ui', '_inline', 'index_inline.html')
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
API = 'http://127.0.0.1:8000'

print('=== 0. BACKEND ===')
try:
    h = json.loads(urllib.request.urlopen(API + '/health', timeout=5).read())
    print('  /health:', h)
    c = json.loads(urllib.request.urlopen(API + '/api/clients?limit=2', timeout=15).read())
    print('  /api/clients total:', c.get('total'), '| source:', c.get('data_source'))
    ok_backend = h.get('status') == 'ok'
except Exception as e:
    print('  BACKEND KHONG SONG:', type(e).__name__, str(e)[:120])
    ok_backend = False

if not ok_backend:
    sys.exit('Backend phai chay truoc. Dung: python -m uvicorn api.main:app --port 8000')

print('\n=== 1. KHOI DONG CHROME ===')
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--window-size=1600,2400')
opts.add_argument('--allow-file-access-from-files')
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = None
for cand in [r'E:\2026\DUT\DSS\SauGK\CuoiKi\chromedriver\chromedriver.exe']:
    if os.path.exists(cand):
        print('  dung chromedriver:', cand)
        try:
            driver = webdriver.Chrome(service=Service(cand), options=opts)
        except Exception as e:
            print('  FAIL:', str(e)[:150])
        break
if driver is None:
    try:
        driver = webdriver.Chrome(options=opts)
        print('  dung chromedriver mac dinh (Selenium Manager)')
    except Exception as e:
        sys.exit('Khong khoi dong duoc Chrome: ' + str(e)[:200])

print('  OK, browser:', driver.name, driver.capabilities.get('browserVersion'))

try:
    print('\n=== 2. MO FILE INLINE TRUC TIEP (mo phong iframe srcdoc) ===')
    driver.get('file:///' + INLINE.replace('\\', '/'))
    time.sleep(4)

    # kiem CSS da load
    bg = driver.execute_script("return getComputedStyle(document.body).backgroundColor;")
    print('  body background:', bg, '->', 'PASS' if bg != 'rgba(0, 0, 0, 0)' else 'FAIL (CSS chua load)')

    # kiem 4 panel giai thich
    txt = driver.find_element(By.TAG_NAME, 'body').text
    for label, kw in [('Panel mot node', 'Một node là gì'),
                      ('So do 5 buoc', 'BƯỚC 5'),
                      ('O lai/Truyen di', 'TRUYỀN ĐI'),
                      ('Moi truong 1 may', 'MỘT tiến trình'),
                      ('Canh bao mo phong', 'LightGCN 0,7151')]:
        print(f'  {label:20s}: {"PASS" if kw in txt else "FAIL"}')

    # kiem ket noi backend
    badge = driver.execute_script("return document.getElementById('healthBadge')?.textContent || '';")
    print('  healthBadge:', repr(badge.strip()[:60]))

    print('\n=== 3. BAM START TRAINING ===')
    driver.execute_script("document.getElementById('startBtn').click();")
    time.sleep(3)

    # doi WS tick
    got_tick = False
    for i in range(15):
        time.sleep(2)
        log = driver.execute_script("return document.getElementById('log')?.innerText || '';")
        n_lines = len([l for l in log.splitlines() if l.strip()])
        run_badge = driver.execute_script("return document.getElementById('runBadge')?.textContent || '';")
        print(f'  t={2*(i+1):2d}s log={n_lines:3d} dong | runBadge={run_badge.strip()[:40]}')
        if n_lines >= 5:
            got_tick = True
            break

    print('  WS tick nhan duoc:', 'PASS' if got_tick else 'FAIL')

    # kiem node grid
    n_nodes = driver.execute_script("return document.querySelectorAll('#nodeGrid .nc-node, #nodeGrid > *').length;")
    print('  so o node:', n_nodes)

    # kiem bieu do co ve
    canvas = driver.execute_script(
        "return Array.from(document.querySelectorAll('canvas')).map(c=>c.width+'x'+c.height);")
    print('  canvas:', canvas)

    # kiem trace node (bam o dau)
    driver.execute_script("""
      const g = document.getElementById('nodeGrid');
      if (g && g.children.length) g.children[0].click();
    """)
    time.sleep(2)
    detail = driver.execute_script("return document.getElementById('detailBox')?.innerText || '';")
    print('  trace panel mo:', 'PASS' if len(detail) > 30 else 'FAIL')
    if detail:
        print('    trace (200 ky tu dau):', detail[:200].replace('\n', ' | '))

    # chup anh
    os.makedirs(SHOT, exist_ok=True)
    p = os.path.join(SHOT, 't4-verify-inline.png')
    driver.save_screenshot(p)
    print('  anh:', p)

    print('\n=== 4. CONSOLE ERRORS ===')
    logs = driver.get_log('browser')
    errs = [l for l in logs if l['level'] == 'SEVERE']
    print(f'  tong log: {len(logs)} | SEVERE: {len(errs)}')
    for e in errs[:6]:
        print('   ', e['message'][:150])
    print('  ->', 'PASS (khong loi)' if not errs else f'CO {len(errs)} LOI')

finally:
    driver.quit()
    print('\n=== DONG BROWSER ===')
