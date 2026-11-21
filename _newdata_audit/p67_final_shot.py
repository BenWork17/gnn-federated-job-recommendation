# -*- coding: utf-8 -*-
"""Chup anh trang Do thi sau khi sua zoom: 1920 sidebar dong, doi chieu truoc."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8613
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
o.add_argument('--disable-dev-shm-usage')
o.add_argument('--window-size=1920,1200')
d = webdriver.Chrome(options=o)
d.set_window_size(1920, 1200)

def find_graph_frame():
    for _ in range(80):
        frames = d.find_elements('css selector', 'iframe')
        for f in frames:
            try:
                d.switch_to.frame(f)
                ok = d.execute_script("return typeof window.__GRAPH2D__ !== 'undefined'")
                if ok:
                    d.switch_to.default_content()
                    return f
                d.switch_to.default_content()
            except Exception:
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
        time.sleep(0.5)
    return None

try:
    d.get(f'{BASE}/do-thi')
    time.sleep(4)
    for _ in range(5):
        d.execute_script('window.scrollBy(0, 400)')
        time.sleep(0.7)
    d.execute_script('window.scrollTo(0, 0)')
    time.sleep(1.5)

    # dong sidebar
    d.execute_script("""
      const b = document.querySelector('[data-testid="stSidebarCollapseButton"] button, [data-testid="collapsedControl"] button');
      if (b) b.click();
    """)
    time.sleep(1.5)

    f = find_graph_frame()
    if f is None:
        print('KHONG THAY IFRAME DO THI')
    else:
        d.switch_to.frame(f)
        for _ in range(80):
            st = d.execute_script("return window.__GRAPH2D__.status()")
            if not st.get('engineRunning'):
                break
            time.sleep(0.3)
        print(f'  zoom = {st.get("zoom"):.4f}')
        cnt = d.execute_script("return window.__GRAPH2D__.counts()")
        print(f'  counts = {cnt}')
        d.switch_to.default_content()

    # do vi tri iframe
    info = d.execute_script("""
      const fr = document.querySelector('iframe');
      const r = fr ? fr.getBoundingClientRect() : null;
      const cards = document.querySelectorAll('.gx-mini-card');
      return {
        iframeTop: r ? Math.round(r.top) : -1,
        iframeW: r ? Math.round(r.width) : -1,
        iframeH: r ? Math.round(r.height) : -1,
        nCards: cards.length,
        cardW: cards.length ? Math.round(cards[0].getBoundingClientRect().width) : -1,
        pageH: document.documentElement.scrollHeight,
        hasSearchInput: !!document.querySelector('input[type="text"]'),
        nMultiSelect: document.querySelectorAll('[data-testid="stMultiSelect"]').length,
        nRadio: document.querySelectorAll('[data-testid="stRadio"]').length,
        nToggle: document.querySelectorAll('[data-testid="stToggle"]').length,
        txt: document.body.innerText.slice(0, 400)
      };
    """)
    print('\n=== DO TRANG ===')
    for k, v in info.items():
        if k != 'txt':
            print(f'  {k:16s} = {v}')
    print(f'  co "ranh giới dữ liệu": {"ranh giới dữ liệu" in info["txt"]}')
    print(f'  co "Câu hỏi của trang": {"Câu hỏi của trang" in info["txt"]}')

    d.save_screenshot(os.path.join(SHOT, 'graph-final-1920.png'))
    print('\n  anh: ui/screenshots/graph-final-1920.png')
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
