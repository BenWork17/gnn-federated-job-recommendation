# -*- coding: utf-8 -*-
"""Kiem tra gia thuyet: Streamlit lazy-render, chi ve phan trong viewport.
Mo trang, CUON XUONG tung doan, dem text sau moi lan cuon."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
PORT = 8607
BASE = f'http://127.0.0.1:{PORT}'

env = dict(os.environ)
env['MPLCONFIGDIR'] = os.path.join(ROOT, 'artifacts', '.mplcache')
p = subprocess.Popen(
    [sys.executable, '-m', 'streamlit', 'run', 'app/streamlit_app.py',
     '--server.headless=true', f'--server.port={PORT}', '--browser.gatherUsageStats=false'],
    cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for i in range(40):
    time.sleep(1.5)
    try:
        urllib.request.urlopen(BASE, timeout=3)
        break
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
o = Options()
o.add_argument('--headless=new')
o.add_argument('--no-sandbox')
o.add_argument('--window-size=1920,1080')
d = webdriver.Chrome(options=o)
d.set_window_size(1920, 1080)

def measure():
    return d.execute_script("""
      const b = document.querySelector('.block-container');
      return {
        text: b ? b.innerText.length : -1,
        docH: document.documentElement.scrollHeight,
        tables: document.querySelectorAll('[data-testid="stDataFrame"]').length,
        subs: Array.from(document.querySelectorAll('h2,h3')).map(h=>h.innerText.slice(0,25))
      };
    """)

try:
    for slug in ('ket-luan', 'goi-y', 'giam-sat-node'):
        print(f'\n===== {slug} =====')
        d.get(f'{BASE}/{slug}')
        time.sleep(3)
        m = measure()
        print(f'  luc dau : text={m["text"]:5d} docH={m["docH"]:5d} df={m["tables"]} subs={len(m["subs"])}')

        # cuon xuong tung 800px, do lai
        for step in range(1, 8):
            d.execute_script(f'window.scrollTo(0, {step * 800});')
            time.sleep(1.2)
            m = measure()
            print(f'  cuon {step*800:5d}: text={m["text"]:5d} docH={m["docH"]:5d} df={m["tables"]} subs={len(m["subs"])}')

        # cuon lai len dau, chup full page
        d.execute_script('window.scrollTo(0, 0);')
        time.sleep(1.0)
        m = measure()
        print(f'  cuoi cung: text={m["text"]:5d} docH={m["docH"]:5d} df={m["tables"]}')
        print(f'  subheaders: {m["subs"]}')
        # chup TOAN TRANG (ca phan ngoai viewport)
        h = max(m['docH'], 1200)
        d.set_window_size(1920, h)
        time.sleep(1.5)
        d.save_screenshot(os.path.join(ROOT, 'ui', 'screenshots', f'full-{slug}.png'))
        print(f'  da chup toan trang (cao {h})')
        d.set_window_size(1920, 1080)
        time.sleep(0.5)
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
