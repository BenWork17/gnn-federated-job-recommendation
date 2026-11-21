# -*- coding: utf-8 -*-
"""Kiem chung TO SANG ket qua tim kiem tren do thi.
Do: truoc khi tim -> HL_COUNT=0, moi nut alpha=1.
    go "python"     -> HL_COUNT>0, nut khop alpha=1, nut xa alpha=0.10, lang gieng 0.55.
"""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8630
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


def wait_graph():
    for _ in range(80):
        d.switch_to.default_content()
        for idx in range(len(d.find_elements('css selector', 'iframe'))):
            try:
                d.switch_to.default_content()
                frames = d.find_elements('css selector', 'iframe')
                if idx >= len(frames):
                    continue
                d.switch_to.frame(frames[idx])
                if d.execute_script("return typeof window.__GRAPH2D__ !== 'undefined'"):
                    for _ in range(100):
                        st = d.execute_script("return window.__GRAPH2D__.status()")
                        if not st.get('engineRunning'):
                            return True
                        time.sleep(0.3)
                    return True
            except Exception:
                pass
        time.sleep(0.6)
    d.switch_to.default_content()
    return False


def probe():
    return d.execute_script("""
      const g = window.__GRAPH2D__;
      // tinh lai alpha theo logic trong bundle de doi chieu
      const out = {n: g.nodes.length, hl: null, alphas: {}};
      const counts = {};
      g.nodes.forEach(nd => {
        const a = g.alpha ? g.alpha(nd) : null;
        const key = a === null ? 'null' : String(a);
        counts[key] = (counts[key] || 0) + 1;
      });
      out.alphas = counts;
      if (g.hl == null) {
        try { out.hl = Object.keys(g.HL_SET || {}).length; } catch (e) {}
      }
      return out;
    """)


def type_search(text):
    d.switch_to.default_content()
    ok = d.execute_script("""
      const inp = document.querySelector('input[aria-label*="Tìm" i]') ||
                  document.querySelector('[data-testid="stTextInput"] input');
      if (!inp) return false;
      const setter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype, 'value').set;
      setter.call(inp, arguments[0]);
      inp.dispatchEvent(new Event('input', {bubbles: true}));
      inp.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
      inp.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', keyCode: 13, bubbles: true}));
      inp.dispatchEvent(new Event('change', {bubbles: true}));
      return true;
    """, text)
    return ok


try:
    d.get(f'{BASE}/do-thi')
    time.sleep(5)
    d.execute_script("""
      const m = document.querySelector('[data-testid="stMain"]');
      if (m) m.scrollTop = 0;
    """)
    time.sleep(2)

    ok = wait_graph()
    print(f'do thi 2D san sang: {ok}')
    if not ok:
        sys.exit('khong tai duoc do thi')

    print('\n=== TRUOC KHI TIM ===')
    a0 = probe()
    print(f'  so nut: {a0["n"]}')
    print(f'  phan bo alpha: {a0["alphas"]}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl-00-before.png'))

    print('\n=== GO "python" ===')
    typed = type_search('python')
    print(f'  go duoc: {typed}')
    time.sleep(6)

    ok2 = wait_graph()
    print(f'  do thi render lai: {ok2}')
    a1 = probe()
    print(f'  phan bo alpha: {a1["alphas"]}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl-01-python.png'))

    # dem so nut sang
    n_full = a1['alphas'].get('1', 0)
    n_dim = a1['alphas'].get('0.1', 0) + a1['alphas'].get('0.1', 0)
    n_nb = a1['alphas'].get('0.55', 0)
    print(f'\n  nut SANG (alpha=1)   : {n_full}')
    print(f'  nut LANG GIENG (0.55): {n_nb}')
    print(f'  nut MO (0.1)         : {a1["alphas"].get("0.1", 0)}')
    hl_ok = (n_full > 0 and n_full < a0['n'] * 0.5)
    print(f'  -> TO SANG {"PASS" if hl_ok else "FAIL"}')

    print('\n=== GO "kỹ năng" ===')
    type_search('kỹ năng')
    time.sleep(6)
    wait_graph()
    a2 = probe()
    print(f'  phan bo alpha: {a2["alphas"]}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl-02-kynang.png'))

    print('\n=== XOA TIM KIEM -> tro lai binh thuong ===')
    type_search('')
    time.sleep(6)
    wait_graph()
    a3 = probe()
    print(f'  phan bo alpha: {a3["alphas"]}')
    back_ok = a3['alphas'].get('1', 0) == a3['n']
    print(f'  -> tro ve binh thuong {"PASS" if back_ok else "FAIL"}')

    logs = d.get_log('browser')
    sev = [l for l in logs if l['level'] == 'SEVERE' and '_stcore' not in l['message']]
    print(f'\n  console SEVERE: {len(sev)}')
    for l in sev[:3]:
        print('   ', l['message'][:120])
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
