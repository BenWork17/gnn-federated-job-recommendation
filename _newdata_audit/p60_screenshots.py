# -*- coding: utf-8 -*-
"""Chup lai anh TAT CA 6 trang, cho render xong han (wait_for_element)."""
import os, subprocess, sys, time
import urllib.request

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8603
BASE = f'http://127.0.0.1:{PORT}'

PAGES = [
    ('tong-quan', 'tong-quan'),
    ('do-thi', 'do-thi'),
    ('lien-bang', 'lien-bang'),
    ('goi-y', 'goi-y'),
    ('giam-sat-node', 'giam-sat-node'),
    ('ket-luan', 'ket-luan'),
]

env = dict(os.environ)
env['MPLCONFIGDIR'] = os.path.join(ROOT, 'artifacts', '.mplcache')
proc = subprocess.Popen(
    [sys.executable, '-m', 'streamlit', 'run', 'app/streamlit_app.py',
     '--server.headless=true', f'--server.port={PORT}', '--browser.gatherUsageStats=false'],
    cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for i in range(40):
    time.sleep(2)
    try:
        urllib.request.urlopen(BASE, timeout=3)
        print(f'  san sang sau {(i+1)*2}s')
        break
    except Exception:
        pass

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--window-size=1920,1080')
opts.add_argument('--hide-scrollbars')
driver = webdriver.Chrome(options=opts)
driver.set_window_size(1920, 1080)

JS_CLOSE = """
const sel = ['[data-testid="stSidebarCollapseButton"] button',
             '[data-testid="collapsedControl"] button'];
for (const s of sel) { const b = document.querySelector(s); if (b) { b.click(); return true; } }
return false;
"""

try:
    for slug, fname in PAGES:
        driver.get(f'{BASE}/{slug}')
        # doi Streamlit render xong: co .block-container VA co text ben trong
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.block-container')))
        except Exception:
            print(f'  {slug}: khong thay .block-container')
        # DOI NOI DUNG ON DINH: text khong tang trong 4 lan lien tiep (~2s)
        # Streamlit render bat dong bo: chi cho ">200 ky tu" la chup som.
        prev, stable, total_wait = -1, 0, 0.0
        for _ in range(80):
            txt = driver.execute_script("""
              const b = document.querySelector('.block-container');
              return b ? b.innerText.length : 0;
            """)
            if txt == prev and txt > 100:
                stable += 1
                if stable >= 4:
                    break
            else:
                stable = 0
            prev = txt
            time.sleep(0.5)
            total_wait += 0.5
        # dong sidebar
        driver.execute_script(JS_CLOSE)
        time.sleep(1.0)
        # cuon len dau
        driver.execute_script("window.scrollTo(0,0)")
        time.sleep(0.4)

        n = driver.execute_script("""
          const b = document.querySelector('.block-container');
          return b ? b.innerText.length : 0;
        """)
        p = os.path.join(SHOT, f'final-{fname}.png')
        driver.save_screenshot(p)
        print(f'  {slug:16s} text={n:6d} ky tu | {os.path.basename(p)}')

    # chup them trang ket luan voi sidebar MO
    driver.get(f'{BASE}/ket-luan')
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.block-container')))
    for _ in range(30):
        t = driver.execute_script("const b=document.querySelector('.block-container'); return b?b.innerText.length:0;")
        if t and t > 200:
            break
        time.sleep(0.5)
    driver.save_screenshot(os.path.join(SHOT, 'final-ket-luan-sidebar-open.png'))
    print('  ket-luan (sidebar mo) da chup')
finally:
    driver.quit()
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    print('xong')

