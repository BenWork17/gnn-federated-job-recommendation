# -*- coding: utf-8 -*-
"""Kiem chung 3D — cho radio render han roi moi bam."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8621
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
    """Cho radio 2D/3D xuat hien trong DOM."""
    t0 = time.time()
    while time.time() - t0 < max_s:
        r = d.execute_script("""
          const labs = Array.from(document.querySelectorAll('[data-testid="stRadio"] label'));
          return labs.map(l => l.innerText.trim()).filter(x => x);
        """)
        if r and any('3D' in x for x in r):
            return r
        # thu cuon de trigger lazy render
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
      l.querySelector('input') ? l.querySelector('input').click() : l.click();
      return true;
    """, txt)


def graph_kind():
    """Xac dinh iframe dang chua gi: 3D (three.js) hay 2D (force-graph)."""
    d.switch_to.default_content()
    n = len(d.find_elements('css selector', 'iframe'))
    for idx in range(n):
        d.switch_to.default_content()
        frames = d.find_elements('css selector', 'iframe')
        if idx >= len(frames):
            continue
        try:
            d.switch_to.frame(frames[idx])
            r = d.execute_script("""
              return {
                has2D: typeof window.__GRAPH2D__ !== 'undefined',
                has3DObj: typeof window.__GRAPH3D__ !== 'undefined',
                canvases: document.querySelectorAll('canvas').length,
                gChildren: (document.getElementById('g')||{children:[]}).children.length,
                panel: !!document.getElementById('panel'),
                legend: !!document.getElementById('legend'),
                w: (document.querySelector('canvas')||{width:0}).width,
                h: (document.querySelector('canvas')||{height:0}).height,
                bodyLen: document.body.innerText.length
              };
            """)
            if r and r['canvases'] > 0:
                return idx, r
        except Exception:
            pass
    return -1, None


try:
    d.get(f'{BASE}/do-thi')
    time.sleep(5)
    labs = wait_radio()
    print(f'=== RADIO ===\n  lua chon: {labs}')

    if not labs:
        print('  KHONG THAY RADIO — bo qua test 3D')
    else:
        print('\n=== BAM 3D ===')
        ok = click_label('3D')
        print(f'  click: {ok}')
        time.sleep(6)
        wait_radio(15)
        idx, info = graph_kind()
        d.switch_to.default_content()
        print(f'  iframe idx={idx}')
        if info:
            for k, v in info.items():
                print(f'    {k:12s} = {v}')
            is3d = info['gChildren'] > 0 and not info['has2D']
            print(f'  -> {'3D (three.js)' if is3d else '2D (force-graph)'}')
            if is3d:
                d.save_screenshot(os.path.join(SHOT, 'graph-3d-on.png'))
                print('  anh: graph-3d-on.png')

                print('\n=== XOAY THU 3D (CDP drag) ===')
                import json as _j
                try:
                    d.execute_cdp_cmd('Input.dispatchMouseEvent', {
                        'type': 'mousePressed', 'x': 900, 'y': 500,
                        'button': 'left', 'clickCount': 1})
                    for step in range(8):
                        d.execute_cdp_cmd('Input.dispatchMouseEvent', {
                            'type': 'mouseMoved', 'x': 900 + step * 25, 'y': 500 + step * 8,
                            'button': 'left', 'buttons': 1})
                        time.sleep(0.05)
                    d.execute_cdp_cmd('Input.dispatchMouseEvent', {
                        'type': 'mouseReleased', 'x': 1100, 'y': 564, 'button': 'left'})
                    print('  da keo xoay')
                    time.sleep(1)
                    d.save_screenshot(os.path.join(SHOT, 'graph-3d-rotated.png'))
                    print('  anh: graph-3d-rotated.png')
                except Exception as e:
                    print(f'  loi CDP: {e}')

        print('\n=== QUAY LAI 2D ===')
        click_label('2D')
        time.sleep(5)
        idx2, info2 = graph_kind()
        d.switch_to.default_content()
        if info2:
            print(f'  has2D={info2["has2D"]} canvases={info2["canvases"]}')
            if info2['has2D']:
                d.switch_to.default_content()
                frames = d.find_elements('css selector', 'iframe')
                for fr in frames:
                    try:
                        d.switch_to.frame(fr)
                        if d.execute_script("return typeof window.__GRAPH2D__ !== 'undefined'"):
                            st = d.execute_script("return window.__GRAPH2D__.status()")
                            print(f'  zoom 2D = {st.get("zoom"):.4f}')
                            break
                    except Exception:
                        pass
                d.switch_to.default_content()
                d.save_screenshot(os.path.join(SHOT, 'graph-2d-after-3d.png'))
                print('  anh: graph-2d-after-3d.png')

    logs = d.get_log('browser')
    sev = [l for l in logs if l['level'] == 'SEVERE' and '_stcore' not in l['message']]
    print(f'\n  console SEVERE (bo _stcore): {len(sev)}')
    for l in sev[:4]:
        print('   ', l['message'][:130])
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
