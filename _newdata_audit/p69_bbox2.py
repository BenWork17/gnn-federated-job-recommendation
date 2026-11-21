# -*- coding: utf-8 -*-
"""Do bbox + test tuong tac. Sua loi stale iframe: tim lai element moi lan."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8615
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
    """Vao iframe co __GRAPH2D__. Tra True neu thanh cong."""
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


def wait_stop(max_s=30):
    t0 = time.time()
    while time.time() - t0 < max_s:
        try:
            st = d.execute_script("return window.__GRAPH2D__.status()")
        except Exception:
            return None
        if not st.get('engineRunning'):
            return st
        time.sleep(0.3)
    return None


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

    ok = False
    for _ in range(20):
        if enter_graph():
            st = wait_stop()
            if st:
                ok = True
                break
        time.sleep(0.8)
    if not ok:
        sys.exit('khong vao duoc iframe do thi')

    print('=== STATUS ===')
    print(f'  zoom = {st.get("zoom"):.4f}')

    bb = d.execute_script("""
      const G = window.__GRAPH2D__.graph;
      const ns = window.__GRAPH2D__.nodes;
      let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
      ns.forEach(n => { if (!isFinite(n.x)||!isFinite(n.y)) return;
        x0=Math.min(x0,n.x); x1=Math.max(x1,n.x);
        y0=Math.min(y0,n.y); y1=Math.max(y1,n.y); });
      const el = document.querySelector('canvas');
      return {graphW: Math.round(x1-x0), graphH: Math.round(y1-y0),
              canvasW: el?el.clientWidth:-1, canvasH: el?el.clientHeight:-1,
              zoom: +G.zoom().toFixed(4), ratio: +((x1-x0)/Math.max(1,y1-y0)).toFixed(3)};
    """)
    print('\n=== BBOX ===')
    for k, v in bb.items():
        print(f'  {k:10s} = {v}')
    print(f'\n  graphW/canvasW = {bb["graphW"]/bb["canvasW"]:.2f}')
    print(f'  graphH/canvasH = {bb["graphH"]/bb["canvasH"]:.2f}')
    print(f'  ti le rong/cao noi dung = {bb["ratio"]}')
    print(f'  ti le rong/cao canvas   = {bb["canvasW"]/bb["canvasH"]:.2f}')

    print('\n=== TIM KIEM ===')
    sr = d.execute_script("""
      const hits0 = document.querySelectorAll('.s-hit').length;
      const inp = document.querySelector('input[type=text], input:not([type])');
      let typed = null;
      if (inp) { inp.value='python'; inp.dispatchEvent(new Event('input',{bubbles:true})); typed='ok'; }
      return {before: hits0, typed};
    """)
    time.sleep(1.2)
    sr2 = d.execute_script("""
      const hits = document.querySelectorAll('.s-hit');
      return {n: hits.length, first: hits.length ? hits[0].innerText.replace(/\\n/g,' | ').slice(0,80) : null};
    """)
    print(f'  truoc: {sr["before"]} | go: {sr["typed"]} | sau: {sr2["n"]} ket qua')
    if sr2['first']:
        print(f'  ket qua dau: {sr2["first"]}')

    print('\n=== CLICK NODE ===')
    sel = d.execute_script("""
      const g = window.__GRAPH2D__;
      let best = null, bd = -1;
      g.nodes.forEach(n => { const dg = n.degree||n.__deg||0; if (dg > bd) { bd=dg; best=n; } });
      if (!best) return null;
      if (g.select) g.select(best.id);
      return {id: best.id, label: best.label, kind: best.kind, degree: bd};
    """)
    print(f'  chon: {sel}')
    time.sleep(1.0)
    st2 = d.execute_script("return window.__GRAPH2D__.status()")
    print(f'  panelOpen={st2.get("panelOpen")} sel={st2.get("sel")}')
    ptxt = d.execute_script("""
      const ps = Array.from(document.querySelectorAll('div')).filter(e => !e.hidden && /Bậc|degree|Láng giềng/i.test(e.innerText||''));
      return ps.length ? ps[0].innerText.replace(/\\n/g,' | ').slice(0,200) : null;
    """)
    print(f'  noi dung panel: {ptxt}')

    print('\n=== HOVER ===')
    hv = d.execute_script("""
      const g = window.__GRAPH2D__;
      if (g.setHover && g.nodes.length > 3) { g.setHover(g.nodes[3].id); }
      return g.status().hover;
    """)
    time.sleep(0.6)
    hv2 = d.execute_script("return window.__GRAPH2D__.status().hover")
    print(f'  hover dat: {hv} | doc lai: {hv2}')

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
