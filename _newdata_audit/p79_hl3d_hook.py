# -*- coding: utf-8 -*-
"""Kiem chung to sang 3D qua hook window.__G3__."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8642
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
          return Array.from(document.querySelectorAll('[data-testid="stRadio"] label')).map(l=>l.innerText.trim()).filter(x=>x);
        """)
        if r and any('3D' in x for x in r):
            return r
        d.execute_script("""
          const m = document.querySelector('[data-testid="stMain"]');
          if (m) m.scrollTop = Math.min(m.scrollTop+300, m.scrollHeight);
        """)
        time.sleep(0.8)
    return []


def click_radio(txt):
    return d.execute_script("""
      const ls = Array.from(document.querySelectorAll('[data-testid="stRadio"] label'));
      const l = ls.find(x => x.innerText.trim() === arguments[0]);
      if (!l) return false;
      (l.querySelector('input')||l).click(); return true;
    """, txt)


def enter_3d():
    d.switch_to.default_content()
    for idx in range(len(d.find_elements('css selector', 'iframe'))):
        d.switch_to.default_content()
        frs = d.find_elements('css selector', 'iframe')
        if idx >= len(frs):
            continue
        try:
            d.switch_to.frame(frs[idx])
            if d.execute_script("return typeof window.__G3__ !== 'undefined'"):
                return True
        except Exception:
            pass
    d.switch_to.default_content()
    return False


def probe():
    return d.execute_script("""
      var g = window.__G3__;
      if (!g) return null;
      return {status: g.status(), colors: g.colors(),
              hlIds: Object.keys(g.hl).slice(0, 5),
              hlCount: g.hlCount};
    """)


def search_via_cdp(text):
    d.switch_to.default_content()
    box = d.execute_script("""
      const inp = document.querySelector('input[aria-label*="Tìm" i]') ||
                  document.querySelector('[data-testid="stTextInput"] input');
      if (!inp) return null;
      const r = inp.getBoundingClientRect(); inp.focus(); return true;
    """)
    if not box:
        return False
    for tp, kw in (('rawKeyDown', dict(windowsVirtualKeyCode=65, modifiers=2, key='a', code='KeyA')),
                   ('keyUp', dict(windowsVirtualKeyCode=65, modifiers=2, key='a', code='KeyA')),
                   ('rawKeyDown', dict(windowsVirtualKeyCode=46, key='Delete', code='Delete')),
                   ('keyUp', dict(windowsVirtualKeyCode=46, key='Delete', code='Delete'))):
        d.execute_cdp_cmd('Input.dispatchKeyEvent', dict(type=tp, **kw))
    time.sleep(0.3)
    for ch in text:
        d.execute_cdp_cmd('Input.insertText', {'text': ch})
        time.sleep(0.04)
    time.sleep(0.5)
    for tp in ('rawKeyDown', 'char', 'keyUp'):
        d.execute_cdp_cmd('Input.dispatchKeyEvent',
                          {'type': tp, 'windowsVirtualKeyCode': 13, 'key': 'Enter',
                           'code': 'Enter', 'text': '\r'})
    return True


try:
    d.get(f'{BASE}/do-thi')
    time.sleep(5)
    print(f'radio: {wait_radio()}')
    click_radio('3D')
    time.sleep(7)
    wait_radio(15)

    ok = False
    for _ in range(15):
        if enter_3d():
            ok = True
            break
        time.sleep(1)
    print(f'vao duoc __G3__: {ok}')
    if not ok:
        sys.exit('khong co hook __G3__')

    print('\n=== TRUOC KHI TIM (3D) ===')
    r0 = probe()
    print(f'  status: {r0["status"]}')
    print(f'  mau: {r0["colors"]}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl3d-00-before.png'))

    print('\n=== GO "python" (3D) ===')
    search_via_cdp('python')
    time.sleep(8)
    enter_3d()
    r1 = probe()
    print(f'  status: {r1["status"]}')
    print(f'  mau: {r1["colors"]}')
    print(f'  hlCount: {r1["hlCount"]} | vd id: {r1["hlIds"]}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl3d-01-python.png'))

    amber = r1['colors'].get('#b8860b', 0)
    hl = r1['hlCount']
    print(f'\n  nut ho phach: {amber} (ky vong = hlCount = {hl})')
    print(f'  -> TO SANG 3D {"PASS" if amber > 0 and amber == hl else "FAIL"}')

    print('\n=== GO "kỹ năng" (3D) ===')
    search_via_cdp('kỹ năng')
    time.sleep(8)
    enter_3d()
    r2 = probe()
    print(f'  hlCount: {r2["hlCount"]} | ho phach: {r2["colors"].get("#b8860b", 0)}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl3d-02-kynang.png'))

    print('\n=== XOA TIM (3D) ===')
    search_via_cdp('')
    time.sleep(8)
    enter_3d()
    r3 = probe()
    print(f'  hlCount: {r3["hlCount"]} | ho phach: {r3["colors"].get("#b8860b", 0)}')
    back = r3['hlCount'] == 0 and r3['colors'].get('#b8860b', 0) == 0
    print(f'  -> reset {"PASS" if back else "FAIL"}')

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
