# -*- coding: utf-8 -*-
"""Kiem chung to sang — dung CDP de go chu vao st.text_input that.
Streamlit text_input chi apply khi blur/Enter; phai dung Input.insertText
hoac rawKeyDown kem text."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8631
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
    """Tra ve so nut theo tung muc alpha."""
    return d.execute_script("""
      const g = window.__GRAPH2D__;
      const counts = {};
      g.nodes.forEach(nd => {
        const a = g.alpha(nd);
        const key = String(a);
        counts[key] = (counts[key] || 0) + 1;
      });
      return {n: g.nodes.length, alphas: counts};
    """)


def search_via_cdp(text):
    """Go vao o tim kiem bang CDP (tin cay hon JS dispatch)."""
    d.switch_to.default_content()
    # tim input
    box = d.execute_script("""
      const inp = document.querySelector('input[aria-label*="Tìm" i]') ||
                  document.querySelector('[data-testid="stTextInput"] input');
      if (!inp) return null;
      const r = inp.getBoundingClientRect();
      inp.focus();
      return {x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)};
    """)
    if not box:
        return False
    # xoa noi dung cu: Ctrl+A roi Delete (Ctrl+A CHI BOI DEN, khong xoa)
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {
        'type': 'rawKeyDown', 'windowsVirtualKeyCode': 65, 'modifiers': 2,
        'key': 'a', 'code': 'KeyA'})
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {
        'type': 'keyUp', 'windowsVirtualKeyCode': 65, 'modifiers': 2,
        'key': 'a', 'code': 'KeyA'})
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {
        'type': 'rawKeyDown', 'windowsVirtualKeyCode': 46, 'key': 'Delete',
        'code': 'Delete'})
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {
        'type': 'keyUp', 'windowsVirtualKeyCode': 46, 'key': 'Delete',
        'code': 'Delete'})
    time.sleep(0.3)
    # go tung ky tu
    for ch in text:
        d.execute_cdp_cmd('Input.insertText', {'text': ch})
        time.sleep(0.04)
    time.sleep(0.6)
    # Enter de apply
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {
        'type': 'rawKeyDown', 'windowsVirtualKeyCode': 13, 'key': 'Enter',
        'code': 'Enter', 'text': '\r', 'unmodifiedText': '\r'})
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {
        'type': 'char', 'text': '\r', 'key': 'Enter'})
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {
        'type': 'keyUp', 'windowsVirtualKeyCode': 13, 'key': 'Enter',
        'code': 'Enter'})
    return True


try:
    d.get(f'{BASE}/do-thi')
    time.sleep(5)
    d.execute_script("""
      const m = document.querySelector('[data-testid="stMain"]');
      if (m) m.scrollTop = 0;
    """)
    time.sleep(2)

    if not wait_graph():
        sys.exit('khong tai duoc do thi')

    print('=== TRUOC KHI TIM ===')
    a0 = probe()
    print(f'  so nut: {a0["n"]} | alpha: {a0["alphas"]}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl-00-before.png'))

    print('\n=== GO "python" bang CDP ===')
    search_via_cdp('python')
    time.sleep(7)
    ok = wait_graph()
    print(f'  do thi render lai: {ok}')
    a1 = probe()
    print(f'  alpha: {a1["alphas"]}')
    n_lit = a1['alphas'].get('1', 0)
    n_nb = a1['alphas'].get('0.55', 0)
    n_dim = a1['alphas'].get('0.1', 0)
    print(f'  SANG={n_lit} | LANG GIENG={n_nb} | MO={n_dim}')
    hl_ok = n_lit < a0['n'] and (n_nb > 0 or n_dim > 0)
    print(f'  -> TO SANG {"PASS" if hl_ok else "FAIL"}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl-01-python.png'))

    print('\n=== GO "kỹ năng" ===')
    search_via_cdp('kỹ năng')
    time.sleep(7)
    wait_graph()
    a2 = probe()
    print(f'  alpha: {a2["alphas"]}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl-02-kynang.png'))

    print('\n=== XOA TIM KIEM ===')
    search_via_cdp('')
    time.sleep(7)
    wait_graph()
    a3 = probe()
    print(f'  alpha: {a3["alphas"]}')
    back = a3['alphas'].get('1', 0) == a3['n']
    print(f'  -> tro ve binh thuong {"PASS" if back else "FAIL"}')

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
