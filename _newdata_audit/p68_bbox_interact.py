# -*- coding: utf-8 -*-
"""Do bbox that cua do thi + test tuong tac (search, click node).
Chan doan vi sao do thi khong lap day chieu ngang."""
import json, os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8614
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

    f = None
    for _ in range(80):
        for fr in d.find_elements('css selector', 'iframe'):
            try:
                d.switch_to.frame(fr)
                if d.execute_script("return typeof window.__GRAPH2D__ !== 'undefined'"):
                    f = fr
                    break
                d.switch_to.default_content()
            except Exception:
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
        if f:
            break
        time.sleep(0.5)
    if not f:
        sys.exit('khong thay iframe')

    d.switch_to.frame(f)
    for _ in range(80):
        st = d.execute_script("return window.__GRAPH2D__.status()")
        if not st.get('engineRunning'):
            break
        time.sleep(0.3)

    print('=== BBOX THAT CUA DO THI ===')
    bb = d.execute_script("""
      const G = window.__GRAPH2D__.graph;
      const ns = window.__GRAPH2D__.nodes;
      let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
      ns.forEach(n => { if (!isFinite(n.x)||!isFinite(n.y)) return;
        x0=Math.min(x0,n.x); x1=Math.max(x1,n.x);
        y0=Math.min(y0,n.y); y1=Math.max(y1,n.y); });
      const el = document.querySelector('canvas');
      return {
        nodeX0: Math.round(x0), nodeX1: Math.round(x1),
        nodeY0: Math.round(y0), nodeY1: Math.round(y1),
        graphW: Math.round(x1-x0), graphH: Math.round(y1-y0),
        canvasW: el ? el.clientWidth : -1, canvasH: el ? el.clientHeight : -1,
        zoom: G.zoom(),
        center: G.centerAt(),
        ratio: +((x1-x0)/(y1-y0)).toFixed(3)
      };
    """)
    for k, v in bb.items():
        print(f'  {k:10s} = {v}')

    print('\n=> Neu graphW/canvasW << graphH/canvasH thi do thi bi gioi han boi CHIEU CAO:')
    print(f'   graphW/canvasW = {bb["graphW"]/bb["canvasW"]:.2f}  (zoom x)')
    print(f'   graphH/canvasH = {bb["graphH"]/bb["canvasH"]:.2f}  (zoom x)')

    print('\n=== TEST TIM KIEM ===')
    d.execute_script("""
      const q = document.getElementById('q') || document.querySelector('input[type=text],input:not([type])');
      if (q) { q.value = 'python'; q.dispatchEvent(new Event('input', {bubbles:true})); }
    """)
    time.sleep(1.2)
    res = d.execute_script("""
      const r = document.getElementById('results') || document.querySelector('.s-hit')?.parentElement;
      const hits = document.querySelectorAll('.s-hit');
      return {nHits: hits.length, first: hits.length ? hits[0].innerText.slice(0,60) : null,
              resHidden: r ? r.hidden : null};
    """)
    print(f'  so ket qua: {res.get("nHits")} | dau tien: {res.get("first")} | an: {res.get("resHidden")}')

    print('\n=== TEST CLICK NODE (mo panel) ===')
    clicked = d.execute_script("""
      const g = window.__GRAPH2D__;
      if (!g.nodes.length) return null;
      // chon node co degree lon nhat
      let best = g.nodes[0];
      g.nodes.forEach(n => { const dg = (n.__deg||0); if (dg > (best.__deg||0)) best = n; });
      const pos = g.screenPos ? g.screenPos(best.id) : null;
      if (!pos) return {err:'no screenPos'};
      if (g.select) g.select(best.id);
      return {id: best.id, label: best.label, kind: best.kind, pos: pos};
    """)
    print(f'  node chon: {clicked}')
    time.sleep(1.0)
    st2 = d.execute_script("return window.__GRAPH2D__.status()")
    print(f'  panelOpen = {st2.get("panelOpen")} | sel = {st2.get("sel")}')
    panel = d.execute_script("""
      const p = document.getElementById('panel') || document.querySelector('.panel,.detail');
      return p ? {visible: !p.hidden, text: p.innerText.slice(0,120)} : null;
    """)
    print(f'  panel: {panel}')

    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'graph-diag.png'))
    print('\n  anh: ui/screenshots/graph-diag.png')
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
