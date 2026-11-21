# -*- coding: utf-8 -*-
"""Kiem chung loi 5c: 4 the so lieu phai nam BEN PHAI do thi ca khi sidebar MO.
Thu 3 be ngang: 1920, 1440, 1024."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8617
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

try:
    for (w, h) in [(1920, 1200), (1440, 1000), (1024, 900)]:
        d.set_window_size(w, h)
        d.get(f'{BASE}/do-thi')
        time.sleep(3.5)
        # Streamlit cuon trong stMain, khong phai window
        d.execute_script("""
          const m = document.querySelector('[data-testid="stMain"]');
          if (m) m.scrollTop = 0;
        """)
        time.sleep(1.0)
        # doi noi dung on dinh
        prev = -1
        for _ in range(30):
            n = d.execute_script("""
              const b = document.querySelector('.block-container');
              return b ? b.innerText.length : 0;
            """)
            if n == prev and n > 300:
                break
            prev = n
            time.sleep(0.4)

        m = d.execute_script("""
          const cards = document.querySelectorAll('.gx-mini-card');
          const fr = document.querySelector('iframe');
          const sb = document.querySelector('[data-testid="stSidebar"]');
          const c0 = cards.length ? cards[0].getBoundingClientRect() : null;
          const frr = fr ? fr.getBoundingClientRect() : null;
          const sbw = sb ? Math.round(sb.getBoundingClientRect().width) : -1;
          // tim cot phai: cha cua card dau tien
          let colR = null;
          if (c0) {
            let e = cards[0];
            while (e && e.parentElement) {
              const r = e.parentElement.getBoundingClientRect();
              if (r.width < 420) { colR = r; }
              if (r.width > 600) break;
              e = e.parentElement;
            }
          }
          return {
            nCards: cards.length,
            cardW: c0 ? Math.round(c0.width) : -1,
            cardLeft: c0 ? Math.round(c0.left) : -1,
            cardTop: c0 ? Math.round(c0.top) : -1,
            frameLeft: frr ? Math.round(frr.left) : -1,
            frameRight: frr ? Math.round(frr.right) : -1,
            frameW: frr ? Math.round(frr.width) : -1,
            frameTop: frr ? Math.round(frr.top) : -1,
            sidebarW: sbw,
            blockW: Math.round((document.querySelector('.block-container')||{getBoundingClientRect:()=>({width:-1})}).getBoundingClientRect().width),
            wrap: document.querySelector('[data-testid="stHorizontalBlock"]') ?
                  getComputedStyle(document.querySelector('[data-testid="stHorizontalBlock"]')).flexWrap : null
          };
        """)
        sb_state = 'MO' if m['sidebarW'] > 100 else 'DONG'
        beside = m['cardLeft'] > m['frameRight'] and abs(m['cardTop'] - m['frameTop']) < 100
        print(f'\n=== {w}x{h} | sidebar {sb_state} (rộng {m["sidebarW"]}px) ===')
        print(f'  blockW={m["blockW"]} | iframe: left={m["frameLeft"]} right={m["frameRight"]} w={m["frameW"]} top={m["frameTop"]}')
        print(f'  thẻ: {m["nCards"]} cái | left={m["cardLeft"]} top={m["cardTop"]} w={m["cardW"]}')
        print(f'  flex-wrap = {m["wrap"]}')
        print(f'  thẻ NẰM BÊN PHẢI đồ thị: {"PASS" if beside else "FAIL"}')
        if beside:
            d.save_screenshot(os.path.join(SHOT, f'gx-fixed-{w}.png'))
            print(f'  anh: gx-fixed-{w}.png')
        else:
            print(f'  -> thẻ Ở DƯỚI (cardTop {m["cardTop"]} > frameTop {m["frameTop"]})')
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
