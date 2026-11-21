# -*- coding: utf-8 -*-
"""Kiem chung to sang trong 3D: go tim kiem -> nut khop doi mau ho phach."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8640
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
          return Array.from(document.querySelectorAll('[data-testid="stRadio"] label')).map(l => l.innerText.trim()).filter(x=>x);
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
      const i = l.querySelector('input'); (i||l).click(); return true;
    """, txt)


def enter_3d_frame():
    d.switch_to.default_content()
    for idx in range(len(d.find_elements('css selector', 'iframe'))):
        d.switch_to.default_content()
        frs = d.find_elements('css selector', 'iframe')
        if idx >= len(frs):
            continue
        try:
            d.switch_to.frame(frs[idx])
            r = d.execute_script("""
              var g = document.getElementById('g');
              return {has3d: !!(window.__G3__ || (g && g.children.length)),
                      canvases: document.querySelectorAll('canvas').length};
            """)
            if r and r['canvases'] > 0:
                return True
        except Exception:
            pass
    d.switch_to.default_content()
    return False


def probe_3d_colors():
    """Dem so nut mau ho phach (#b8860b) trong 3D."""
    return d.execute_script("""
      // 3d-force-graph khong expose nodes de dem mau de dang, nen doc tu
      // chinh data da nhung trong trang neu co.
      var out = {hl: null, total: null, colorFnHasHl: null};
      try {
        // HL la bien trong closure -> khong doc duoc. Thay vao do dem pixel
        // mau ho phach tren canvas la cach duy nhat khach quan.
        var cv = document.querySelector('canvas');
        if (!cv) return out;
        var tmp = document.createElement('canvas');
        tmp.width = cv.width; tmp.height = cv.height;
        var ctx = tmp.getContext('2d');
        ctx.drawImage(cv, 0, 0);
        var img = ctx.getImageData(0, 0, tmp.width, tmp.height).data;
        var n = 0;
        for (var i = 0; i < img.length; i += 4) {
          var r = img[i], g = img[i+1], b = img[i+2];
          // #b8860b = rgb(184,134,11) — cho phep sai so
          if (Math.abs(r-184)<26 && Math.abs(g-134)<26 && Math.abs(b-11)<34) n++;
        }
        out.hl = n;
        out.total = tmp.width * tmp.height;
      } catch (e) { out.err = String(e).slice(0,80); }
      return out;
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
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {'type':'rawKeyDown','windowsVirtualKeyCode':65,'modifiers':2,'key':'a','code':'KeyA'})
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {'type':'keyUp','windowsVirtualKeyCode':65,'modifiers':2,'key':'a','code':'KeyA'})
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {'type':'rawKeyDown','windowsVirtualKeyCode':46,'key':'Delete','code':'Delete'})
    d.execute_cdp_cmd('Input.dispatchKeyEvent', {'type':'keyUp','windowsVirtualKeyCode':46,'key':'Delete','code':'Delete'})
    time.sleep(0.3)
    for ch in text:
        d.execute_cdp_cmd('Input.insertText', {'text': ch})
        time.sleep(0.04)
    time.sleep(0.5)
    for tp in ('rawKeyDown','char','keyUp'):
        d.execute_cdp_cmd('Input.dispatchKeyEvent', {'type':tp,'windowsVirtualKeyCode':13,'key':'Enter','code':'Enter','text':'\r'})
    return True


try:
    d.get(f'{BASE}/do-thi')
    time.sleep(5)
    labs = wait_radio()
    print(f'radio: {labs}')

    print('\n=== CHUYEN 3D ===')
    click_radio('3D')
    time.sleep(7)
    wait_radio(15)
    ok = enter_3d_frame()
    print(f'  vao duoc iframe 3D: {ok}')
    if not ok:
        sys.exit('khong vao duoc 3D')

    time.sleep(2)
    print('\n=== TRUOC KHI TIM (3D) ===')
    c0 = probe_3d_colors()
    print(f'  pixel mau ho phach: {c0.get("hl")} / {c0.get("total")}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl3d-00-before.png'))

    print('\n=== GO "python" (3D) ===')
    search_via_cdp('python')
    time.sleep(8)
    ok2 = enter_3d_frame()
    print(f'  render lai: {ok2}')
    time.sleep(2)
    c1 = probe_3d_colors()
    print(f'  pixel mau ho phach: {c1.get("hl")} / {c1.get("total")}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl3d-01-python.png'))

    b = c0.get('hl') or 0
    a = c1.get('hl') or 0
    print(f'  tang: {a} - {b} = {a-b}')
    print(f'  -> TO SANG 3D {"PASS" if a > b * 1.5 and a > 200 else "FAIL"}')

    print('\n=== GO "kỹ năng" (3D) ===')
    search_via_cdp('kỹ năng')
    time.sleep(8)
    enter_3d_frame()
    time.sleep(2)
    c2 = probe_3d_colors()
    print(f'  pixel: {c2.get("hl")}')
    d.switch_to.default_content()
    d.save_screenshot(os.path.join(SHOT, 'hl3d-02-kynang.png'))

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
