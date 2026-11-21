# -*- coding: utf-8 -*-
"""Kiem chung ban sua zoom: zoom luc yen phai >= 0.75 (truoc la 0.5498).
Kiem them: keo node van chay, va sau khi keo thi KHONG tu canh lai."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
PORT = 8612
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
        print(f'server san sang sau {(i+1)*1.5:.0f}s')
        break
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
o = Options()
o.add_argument('--headless=new')
o.add_argument('--no-sandbox')
o.add_argument('--disable-dev-shm-usage')
o.add_argument('--window-size=1920,1080')
d = webdriver.Chrome(options=o)
d.set_window_size(1920, 1080)

def wait_ready():
    """Doi iframe co __GRAPH2D__ va engine dung."""
    for _ in range(80):
        frames = d.find_elements('css selector', 'iframe')
        for f in frames:
            try:
                d.switch_to.frame(f)
                ok = d.execute_script("return typeof window.__GRAPH2D__ !== 'undefined'")
                if ok:
                    for _ in range(60):
                        st = d.execute_script("return window.__GRAPH2D__.status()")
                        if not st.get('engineRunning'):
                            d.switch_to.default_content()
                            return True, st
                        time.sleep(0.3)
                    d.switch_to.default_content()
                    return True, st
                d.switch_to.default_content()
            except Exception:
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
        time.sleep(0.5)
    return False, None

try:
    d.get(f'{BASE}/do-thi')
    time.sleep(4)
    # cuon xuong cho lazy render
    for _ in range(4):
        d.execute_script('window.scrollBy(0, 400)')
        time.sleep(0.8)
    d.execute_script('window.scrollTo(0, 0)')
    time.sleep(1.5)

    ok, st = wait_ready()
    if not ok:
        print('KHONG TIM THAY __GRAPH2D__ trong iframe')
        print('so iframe:', len(d.find_elements('css selector', 'iframe')))
    else:
        print('\n=== STATUS SAU KHI ENGINE DUNG ===')
        for k in ('engineRunning', 'zoom', 'cx', 'cy', 'hover', 'sel', 'panelOpen'):
            print(f'  {k:14s} = {st.get(k)}')
        z = st.get('zoom', 0)
        print(f'\n  ZOOM = {z:.4f}')
        print(f'  Ky vong >= 0.75 (truoc khi sua la 0.5498)')
        print(f'  -> {"PASS" if z >= 0.75 else "FAIL"}')

        # dem node/canh
        n = d.execute_script("""
          const g = window.__GRAPH2D__;
          return {nodes: g.nodes.length, links: g.links.length, counts: g.counts ? g.counts() : null};
        """)
        print(f'\n  so nut: {n["nodes"]} | so canh: {n["links"]}')

        # thu zoomToFit tay
        d.execute_script("window.__GRAPH2D__.graph.zoomToFit(0, 40)")
        time.sleep(0.6)
        st2 = d.execute_script("return window.__GRAPH2D__.status()")
        print(f'  zoomToFit tay -> zoom = {st2.get("zoom"):.4f}')

        d.switch_to.default_content()
        d.save_screenshot(os.path.join(ROOT, 'ui', 'screenshots', 'graph-zoom-fixed.png'))
        print('  anh: ui/screenshots/graph-zoom-fixed.png')
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
