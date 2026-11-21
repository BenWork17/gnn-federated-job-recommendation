# -*- coding: utf-8 -*-
"""Kiem chung vong tron 2D -> 3D -> 2D. Zoom 2D sau khi quay lai phai >= 0.75."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8622
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
o.add_argument('--use-gl=swiftshader')
o.add_argument('--enable-unsafe-swiftshader')
d = webdriver.Chrome(options=o)
d.set_window_size(1920, 1200)


def wait_radio(max_s=60):
    t0 = time.time()
    while time.time() - t0 < max_s:
        r = d.execute_script("""
          const labs = Array.from(document.querySelectorAll('[data-testid="stRadio"] label'));
          return labs.map(l => l.innerText.trim()).filter(x => x);
        """)
        if r and any('3D' in x for x in r):
            return r
        d.execute_script("""
          const m = document.querySelector('[data-testid="stMain"]');
          if (m) m.scrollTop = Math.min(m.scrollTop + 300, m.scrollHeight);
        """)
        time.sleep(0.8)
    return []


def click_label(txt):
    return d.execute_script("""
      const labels = Array.from(document.querySelectorAll('[data-testid="stRadio"] label'));
      const l = labels.find(x => x.innerText.trim() === arguments[0]);
      if (!l) return false;
      const inp = l.querySelector('input');
      if (inp) inp.click(); else l.click();
      return true;
    """, txt)


def get_2d_status(wait_engine=True):
    d.switch_to.default_content()
    n = len(d.find_elements('css selector', 'iframe'))
    for idx in range(n):
        d.switch_to.default_content()
        frames = d.find_elements('css selector', 'iframe')
        if idx >= len(frames):
            continue
        try:
            d.switch_to.frame(frames[idx])
            if d.execute_script("return typeof window.__GRAPH2D__ !== 'undefined'"):
                if wait_engine:
                    for _ in range(120):
                        st = d.execute_script("return window.__GRAPH2D__.status()")
                        if not st.get('engineRunning'):
                            time.sleep(0.8)   # doi setTimeout 420ms chay
                            st = d.execute_script("return window.__GRAPH2D__.status()")
                            d.switch_to.default_content()
                            return st
                        time.sleep(0.3)
                st = d.execute_script("return window.__GRAPH2D__.status()")
                d.switch_to.default_content()
                return st
        except Exception:
            pass
    d.switch_to.default_content()
    return None


try:
    d.get(f'{BASE}/do-thi')
    time.sleep(5)
    labs = wait_radio()
    print(f'radio: {labs}')

    print('\n=== BUOC 1: 2D lan dau ===')
    st0 = get_2d_status()
    print(f'  zoom = {st0.get("zoom"):.4f}  -> {"PASS" if st0.get("zoom", 0) >= 0.75 else "FAIL"}')

    print('\n=== BUOC 2: chuyen 3D ===')
    click_label('3D')
    time.sleep(6)
    wait_radio(15)
    canv3d = d.execute_script("""
      const fr = document.querySelector('iframe');
      return fr ? 1 : 0;
    """)
    print(f'  iframe 3D: {canv3d}')
    d.save_screenshot(os.path.join(SHOT, 'cycle-3d.png'))

    print('\n=== BUOC 3: quay lai 2D ===')
    click_label('2D')
    time.sleep(6)
    st2 = get_2d_status()
    print(f'  zoom = {st2.get("zoom"):.4f}  -> {"PASS" if st2.get("zoom", 0) >= 0.75 else "FAIL"}')
    d.save_screenshot(os.path.join(SHOT, 'cycle-2d-back.png'))

    print('\n=== BUOC 4: chuyen 3D lan 2 ===')
    click_label('3D')
    time.sleep(5)
    print('  da chuyen')
    print('\n=== BUOC 5: quay lai 2D lan 2 ===')
    click_label('2D')
    time.sleep(6)
    st3 = get_2d_status()
    print(f'  zoom = {st3.get("zoom"):.4f}  -> {"PASS" if st3.get("zoom", 0) >= 0.75 else "FAIL"}')

    logs = d.get_log('browser')
    sev = [l for l in logs if l['level'] == 'SEVERE' and '_stcore' not in l['message']]
    print(f'\n  console SEVERE: {len(sev)}')
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
