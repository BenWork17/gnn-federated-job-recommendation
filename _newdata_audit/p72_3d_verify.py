# -*- coding: utf-8 -*-
"""Kiem chung 3D da khoi phuc: bam radio 3D, kiem canvas 3D + tuong tac xoay."""
import json, os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8620
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


def wait_text_stable(min_len=300, tries=40):
    prev = -1
    for _ in range(tries):
        n = d.execute_script("""
          const b = document.querySelector('.block-container');
          return b ? b.innerText.length : 0;
        """)
        if n == prev and n > min_len:
            return n
        prev = n
        time.sleep(0.4)
    return prev


try:
    d.get(f'{BASE}/do-thi')
    time.sleep(4)
    d.execute_script("""
      const m = document.querySelector('[data-testid="stMain"]');
      if (m) m.scrollTop = 0;
    """)
    wait_text_stable()

    print('=== KIEM TRA RADIO 2D/3D ===')
    radios = d.execute_script("""
      const labels = Array.from(document.querySelectorAll('[data-testid="stRadio"] label'));
      return labels.map(l => l.innerText.trim());
    """)
    print(f'  lua chon radio: {radios}')

    n_before = d.execute_script("return document.querySelectorAll('iframe').length")
    print(f'  so iframe truoc: {n_before}')

    # bam 3D
    clicked = d.execute_script("""
      const labels = Array.from(document.querySelectorAll('[data-testid="stRadio"] label'));
      const l = labels.find(x => x.innerText.trim() === '3D');
      if (!l) return false;
      l.click();
      return true;
    """)
    print(f'  bam 3D: {clicked}')
    time.sleep(5)
    wait_text_stable()

    n_after = d.execute_script("return document.querySelectorAll('iframe').length")
    print(f'  so iframe sau: {n_after}')

    # kiem trong iframe co three.js canvas khong
    info = None
    for idx in range(n_after):
        d.switch_to.default_content()
        frames = d.find_elements('css selector', 'iframe')
        if idx >= len(frames):
            break
        try:
            d.switch_to.frame(frames[idx])
            r = d.execute_script("""
              const cv = document.querySelectorAll('canvas');
              return {
                canvases: cv.length,
                hasTHREE: typeof window.THREE !== 'undefined',
                has3DGraph: !!(window.__GRAPH3D__ || document.getElementById('g')),
                gChildren: document.getElementById('g') ? document.getElementById('g').children.length : -1,
                bodyLen: document.body.innerText.length
              };
            """)
            if r and (r['canvases'] > 0 or r['gChildren'] > 0):
                info = r
                print(f'\n=== IFRAME {idx} ===')
                for k, v in r.items():
                    print(f'  {k:14s} = {v}')
                break
        except Exception as e:
            pass
    d.switch_to.default_content()

    if info is None:
        print('  KHONG TIM THAY CANVAS 3D trong iframe nao')
    else:
        # chup anh
        d.save_screenshot(os.path.join(SHOT, 'graph-3d-restored.png'))
        print('  anh: ui/screenshots/graph-3d-restored.png')

    # bam lai 2D
    d.execute_script("""
      const labels = Array.from(document.querySelectorAll('[data-testid="stRadio"] label'));
      const l = labels.find(x => x.innerText.trim() === '2D');
      if (l) l.click();
    """)
    time.sleep(4)
    back2d = d.execute_script("""
      const labels = Array.from(document.querySelectorAll('[data-testid="stRadio"] label'));
      const checked = labels.filter(l => l.querySelector('input') && l.querySelector('input').checked);
      return checked.map(l => l.innerText.trim());
    """)
    print(f'\n  bam lai 2D -> radio dang chon: {back2d}')

    # kiem 2D van co __GRAPH2D__
    ok2d = False
    for idx in range(len(d.find_elements('css selector', 'iframe'))):
        d.switch_to.default_content()
        frames = d.find_elements('css selector', 'iframe')
        if idx >= len(frames):
            break
        try:
            d.switch_to.frame(frames[idx])
            if d.execute_script("return typeof window.__GRAPH2D__ !== 'undefined'"):
                st = d.execute_script("return window.__GRAPH2D__.status()")
                print(f'  2D: zoom={st.get("zoom"):.4f} engineRunning={st.get("engineRunning")}')
                ok2d = True
                break
        except Exception:
            pass
    d.switch_to.default_content()
    print(f'  2D hoat dong lai: {"PASS" if ok2d else "FAIL"}')

    logs = d.get_log('browser')
    sev = [l for l in logs if l['level'] == 'SEVERE']
    print(f'\n  console SEVERE: {len(sev)}')
    for l in sev[:4]:
        print('   ', l['message'][:120])
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
