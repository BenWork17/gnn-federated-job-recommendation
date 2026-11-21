# -*- coding: utf-8 -*-
"""Do dien tich trong that su bang Selenium tren ca 6 trang x 3 kich thuoc x 2 trang thai sidebar."""
import json, os, subprocess, sys, time
import urllib.request

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8601
BASE = f'http://127.0.0.1:{PORT}'

PAGES = [
    ('tong-quan', 'Tổng quan'),
    ('do-thi', 'Đồ thị việc làm'),
    ('lien-bang', 'FL simulation'),
    ('goi-y', 'Gợi ý'),
    ('giam-sat-node', 'Giám sát node'),
    ('ket-luan', 'Kết luận'),
]
SIZES = [(1366, 768), (1600, 900), (1920, 1080)]

print('=== KHOI DONG STREAMLIT ===')
env = dict(os.environ)
env['MPLCONFIGDIR'] = os.path.join(ROOT, 'artifacts', '.mplcache')
proc = subprocess.Popen(
    [sys.executable, '-m', 'streamlit', 'run', 'app/streamlit_app.py',
     '--server.headless=true', f'--server.port={PORT}',
     '--browser.gatherUsageStats=false'],
    cwd=ROOT, env=env,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

ok = False
for i in range(40):
    time.sleep(2)
    try:
        urllib.request.urlopen(BASE, timeout=3)
        print(f'  san sang sau {(i+1)*2}s')
        ok = True
        break
    except Exception:
        pass
if not ok:
    proc.terminate()
    sys.exit('Streamlit khong khoi dong duoc')

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
driver = webdriver.Chrome(options=opts)

JS_MEASURE = """
const bc = document.querySelector('.block-container');
if (!bc) return null;
const r = bc.getBoundingClientRect();
return {
  blockWidth: Math.round(r.width),
  viewport: window.innerWidth,
  leftGap: Math.round(r.left),
  rightGap: Math.round(window.innerWidth - r.right),
  scrollHeight: document.body.scrollHeight,
  overflow: document.documentElement.scrollWidth > window.innerWidth + 1
};
"""

rows = []
try:
    for slug, name in PAGES:
        for (w, h) in SIZES:
            driver.set_window_size(w, h)
            for sb in ('open', 'closed'):
                try:
                    driver.get(f'{BASE}/{slug}')
                    time.sleep(3.2)
                    if sb == 'closed':
                        # bam nut collapse sidebar
                        driver.execute_script("""
                          const btns = Array.from(document.querySelectorAll(
                            '[data-testid="stSidebarCollapseButton"] button, [data-testid="collapsedControl"] button, button[kind="header"]'));
                          if (btns.length) btns[0].click();
                        """)
                        time.sleep(1.2)
                    m = driver.execute_script(JS_MEASURE)
                    if m is None:
                        rows.append(dict(page=name, w=w, sb=sb, err='no .block-container'))
                        continue
                    errs = [l for l in driver.get_log('browser') if l['level'] == 'SEVERE']
                    m.update(page=name, w=w, sb=sb, console=len(errs))
                    rows.append(m)
                    gap = m['leftGap'] + m['rightGap']
                    print(f"  {name:18s} {w:4d}px sb={sb:6s} | block={m['blockWidth']:4d} "
                          f"left={m['leftGap']:3d} right={m['rightGap']:3d} gap={gap:4d} "
                          f"h={m['scrollHeight']:5d} overflow={m['overflow']} err={len(errs)}")
                    if sb == 'closed' and w == 1920:
                        os.makedirs(SHOT, exist_ok=True)
                        driver.save_screenshot(os.path.join(SHOT, f'layout-{slug}.png'))
                except Exception as e:
                    rows.append(dict(page=name, w=w, sb=sb, err=str(e)[:80]))
                    print(f'  {name} {w} {sb} FAIL: {str(e)[:80]}')
finally:
    driver.quit()
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

print('\n=== TONG KET ===')
ok_rows = [r for r in rows if 'blockWidth' in r]
if ok_rows:
    c1920 = [r for r in ok_rows if r['w'] == 1920 and r['sb'] == 'closed']
    if c1920:
        avg_gap = sum(r['leftGap'] + r['rightGap'] for r in c1920) / len(c1920)
        print(f'  1920px sidebar DONG: gap trung binh = {avg_gap:.0f}px (muc tieu <=120)')
        print(f'    -> {"PASS" if avg_gap <= 120 else "FAIL"}')
    ov = [r for r in ok_rows if r.get('overflow')]
    print(f'  tran ngang: {len(ov)}/{len(ok_rows)} -> {"PASS" if not ov else "FAIL"}')
    ce = sum(r.get('console', 0) for r in ok_rows)
    print(f'  console errors: {ce} -> {"PASS" if ce == 0 else "FAIL"}')

json.dump(rows, open(os.path.join(ROOT, '_newdata_audit', 'layout_measure.json'), 'w',
                     encoding='utf-8'), indent=1, ensure_ascii=False)
print('  da luu _newdata_audit/layout_measure.json')
