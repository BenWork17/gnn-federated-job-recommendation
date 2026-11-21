# -*- coding: utf-8 -*-
"""Test search dung selector #q (type=search). Do them bbox de tim cach lap day chieu ngang."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
PORT = 8616
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


def enter_graph():
    d.switch_to.default_content()
    n = len(d.find_elements('css selector', 'iframe'))
    for idx in range(n):
        try:
            d.switch_to.default_content()
            frames = d.find_elements('css selector', 'iframe')
            if idx >= len(frames):
                continue
            d.switch_to.frame(frames[idx])
            if d.execute_script("return typeof window.__GRAPH2D__ !== 'undefined'"):
                return True
        except Exception:
            continue
    d.switch_to.default_content()
    return False


try:
    d.get(f'{BASE}/do-thi')
    time.sleep(4)
    for _ in range(5):
        d.execute_script('window.scrollBy(0, 400)')
        time.sleep(0.6)
    d.execute_script('window.scrollTo(0, 0)')
    time.sleep(1.5)
    d.execute_script("""
      const b = document.querySelector('[data-testid="stSidebarCollapseButton"] button, [data-testid="collapsedControl"] button');
      if (b) b.click();
    """)
    time.sleep(1.5)

    for _ in range(20):
        if enter_graph():
            for _ in range(80):
                st = d.execute_script("return window.__GRAPH2D__.status()")
                if not st.get('engineRunning'):
                    break
                time.sleep(0.3)
            break
        time.sleep(0.8)

    print('=== TEST TIM KIEM voi #q ===')
    has_q = d.execute_script("return !!document.getElementById('q')")
    print(f'  co #q: {has_q}')

    for term in ('python', 'kỹ năng', 'data'):
        r = d.execute_script("""
          const q = document.getElementById('q');
          if (!q) return {err:'no #q'};
          q.value = arguments[0];
          q.dispatchEvent(new Event('input', {bubbles:true}));
          return {val: q.value};
        """, term)
        time.sleep(0.9)
        rr = d.execute_script("""
          const hits = document.querySelectorAll('.s-hit');
          const cnt = document.getElementById('cnt');
          return {n: hits.length,
                  first: hits.length ? hits[0].innerText.replace(/\\n/g,' ') : null,
                  cnt: cnt ? cnt.textContent : null,
                  resHidden: document.getElementById('res') ? document.getElementById('res').hidden : null};
        """)
        print(f'  "{term}": {rr["n"]} ket qua | cnt="{rr["cnt"]}" | first={rr["first"]}')

    # reset
    d.execute_script("""
      const q = document.getElementById('q');
      if (q) { q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); }
    """)
    time.sleep(0.5)

    print('\n=== DO BBOX / TIM CACH LAP DAY ===')
    m = d.execute_script("""
      const g = window.__GRAPH2D__;
      const G = g.graph;
      const cv = document.querySelector('canvas');
      let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
      g.nodes.forEach(n => { if(!isFinite(n.x)||!isFinite(n.y)) return;
        x0=Math.min(x0,n.x); x1=Math.max(x1,n.x); y0=Math.min(y0,n.y); y1=Math.max(y1,n.y); });
      return {gw: +(x1-x0).toFixed(1), gh: +(y1-y0).toFixed(1),
              cw: cv.clientWidth, ch: cv.clientHeight, zoom:+G.zoom().toFixed(4)};
    """)
    print(f'  noi dung: {m["gw"]} x {m["gh"]}  | canvas: {m["cw"]} x {m["ch"]} | zoom {m["zoom"]}')
    fill_x = m['gw'] * m['zoom'] / m['cw']
    fill_y = m['gh'] * m['zoom'] / m['ch']
    print(f'  lap day chieu NGANG = {fill_x*100:.1f}%')
    print(f'  lap day chieu DOC   = {fill_y*100:.1f}%')
    print(f'  => Bi gioi han boi: {"CHIEU DOC (canvas rong, noi dung hep)" if fill_y > fill_x else "CHIEU NGANG"}')

    # thu zoom them de lap ngang
    print('\n  Thu zoom 1.6x de xem co lap ngang khong:')
    d.execute_script("window.__GRAPH2D__.graph.zoom(1.6, 400)")
    time.sleep(0.9)
    m2 = d.execute_script("""
      const g = window.__GRAPH2D__; const cv = document.querySelector('canvas');
      return {zoom:+g.graph.zoom().toFixed(4), cw:cv.clientWidth, ch:cv.clientHeight};
    """)
    print(f'    zoom = {m2["zoom"]} -> noi dung lap {(m["gw"]*m2["zoom"]/m2["cw"])*100:.0f}% ngang, {(m["gh"]*m2["zoom"]/m2["ch"])*100:.0f}% doc')

finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
