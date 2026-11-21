# -*- coding: utf-8 -*-
"""Kiem chung to sang 3D bang cach DOC TRUC TIEP tu graph object.
3d-force-graph co `graphData()` va node objects mang `.color` sau khi
nodeColor accessor chay. Do truc tiep thay vi doc pixel WebGL (khong doc duoc).
"""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8641
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
            if d.execute_script("return document.querySelectorAll('canvas').length > 0"):
                return True
        except Exception:
            pass
    d.switch_to.default_content()
    return False


def probe_nodes():
    """Tim graph object trong scope, dem node theo mau."""
    return d.execute_script("""
      // 3d-force-graph gan instance vao element? Thu nhieu cach.
      var res = {found:false};
      // Cach 1: window co bien graph?
      var cands = ['__GRAPH3D__','graph','Graph','G'];
      for (var i=0;i<cands.length;i++) {
        var g = window[cands[i]];
        if (g && typeof g.graphData === 'function') {
          var data = g.graphData();
          var counts = {};
          (data.nodes||[]).forEach(function(n){
            var c = (n && n.color) ? n.color : 'none';
            counts[c] = (counts[c]||0)+1;
          });
          res.found = true; res.via = cands[i];
          res.n = (data.nodes||[]).length;
          res.colors = counts;
          return res;
        }
      }
      // Cach 2: tim qua canvas -> khong co ref. Thu doc tu DOM custom prop.
      res.canvas = document.querySelectorAll('canvas').length;
      res.keys = Object.keys(window).filter(function(k){
        return /graph|force|g3|three/i.test(k);
      }).slice(0,10);
      return res;
    """)


def search_via_cdp(text):
    d.switch_to.default_content()
    box = d.execute_script("""
      const inp = document.querySelector('input[aria-label*="Tìm" i]') ||
                  document.querySelector('[data-testid="stTextInput"] input');
      if (!inp) return null;
      const r = inp.getBoundingClientRect(); inp.focus();
      return {x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2)};
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
    wait_radio()
    click_radio('3D')
    time.sleep(7)
    wait_radio(15)
    if not enter_3d():
        sys.exit('khong vao duoc 3D')

    print('=== TIM GRAPH OBJECT ===')
    r0 = probe_nodes()
    print(f'  {r0}')
    d.switch_to.default_content()

    if r0.get('found'):
        print('\n=== TRUOC TIM ===')
        print(f'  node: {r0["n"]} | mau: {r0["colors"]}')
        d.save_screenshot(os.path.join(SHOT, 'hl3d-00-before.png'))

        search_via_cdp('python')
        time.sleep(8)
        enter_3d()
        r1 = probe_nodes()
        print('\n=== SAU KHI GO "python" ===')
        print(f'  node: {r1.get("n")} | mau: {r1.get("colors")}')
        d.switch_to.default_content()
        d.save_screenshot(os.path.join(SHOT, 'hl3d-01-python.png'))
        amber = r1.get('colors', {}).get('#b8860b', 0)
        print(f'  -> so nut ho phach: {amber} {"PASS" if amber > 0 else "FAIL"}')
    else:
        print('  KHONG TIM THAY graph object — thu cach khac')
        # fallback: chup anh de xem bang mat
        d.switch_to.default_content()
        d.save_screenshot(os.path.join(SHOT, 'hl3d-probe.png'))
        print('  da chup anh: hl3d-probe.png')

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
