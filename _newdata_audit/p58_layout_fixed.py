# -*- coding: utf-8 -*-
"""Do lai, SUA LOI: trang thai sidebar bi luu giua cac trang (localStorage/session).
Moi lan do phai FORCE dung trang thai, va kiem tra lai sau khi click."""
import json, os, subprocess, sys, time
import urllib.request

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
SHOT = os.path.join(ROOT, 'ui', 'screenshots')
PORT = 8602
BASE = f'http://127.0.0.1:{PORT}'

PAGES = [
    ('tong-quan', 'Tong quan'),
    ('do-thi', 'Do thi'),
    ('lien-bang', 'FL sim'),
    ('goi-y', 'Goi y'),
    ('giam-sat-node', 'Giam sat'),
    ('ket-luan', 'Ket luan'),
]
SIZES = [(1366, 768), (1600, 900), (1920, 1080)]

env = dict(os.environ)
env['MPLCONFIGDIR'] = os.path.join(ROOT, 'artifacts', '.mplcache')
proc = subprocess.Popen(
    [sys.executable, '-m', 'streamlit', 'run', 'app/streamlit_app.py',
     '--server.headless=true', f'--server.port={PORT}', '--browser.gatherUsageStats=false'],
    cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for i in range(40):
    time.sleep(2)
    try:
        urllib.request.urlopen(BASE, timeout=3)
        print(f'streamlit san sang sau {(i+1)*2}s')
        break
    except Exception:
        pass

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
driver = webdriver.Chrome(options=opts)

# do + tra ve trang thai sidebar thuc te
JS = """
const sb = document.querySelector('[data-testid="stSidebar"]');
const bc = document.querySelector('.block-container') || document.querySelector('[data-testid="stMainBlockContainer"]');
if (!bc) return null;
const r = bc.getBoundingClientRect();
const sbw = sb ? Math.round(sb.getBoundingClientRect().width) : -1;
return {
  sidebarWidth: sbw,
  sidebarOpen: sbw > 100,
  blockWidth: Math.round(r.width),
  viewport: window.innerWidth,
  leftGap: Math.round(r.left),
  rightGap: Math.round(window.innerWidth - r.right),
  scrollHeight: document.documentElement.scrollHeight,
  overflow: document.documentElement.scrollWidth > window.innerWidth + 1
};
"""

JS_CLICK_COLLAPSE = """
const sel = [
  '[data-testid="stSidebarCollapseButton"] button',
  '[data-testid="stSidebarCollapsedControl"] button',
  '[data-testid="collapsedControl"] button',
  'button[aria-label*="sidebar" i]',
  'button[aria-label*="Close" i]',
];
for (const s of sel) { const b = document.querySelector(s); if (b) { b.click(); return s; } }
return null;
"""

rows = []
try:
    for slug, name in PAGES:
        for (w, h) in SIZES:
            driver.set_window_size(w, h)
            for want in ('open', 'closed'):
                driver.get(f'{BASE}/{slug}')
                time.sleep(3.0)
                # FORCE trang thai: neu can dong ma dang mo -> click; neu can mo ma dang dong -> click
                for _ in range(3):
                    st0 = driver.execute_script(JS)
                    if st0 is None:
                        break
                    if want == 'closed' and st0['sidebarOpen']:
                        driver.execute_script(JS_CLICK_COLLAPSE)
                        time.sleep(0.9)
                    elif want == 'open' and not st0['sidebarOpen']:
                        # nut mo sidebar khi da dong
                        driver.execute_script("""
                          const b = document.querySelector('[data-testid="stSidebarCollapsedControl"] button, [data-testid="collapsedControl"] button, button[aria-label*="Open" i]');
                          if (b) b.click();
                        """)
                        time.sleep(0.9)
                    else:
                        break
                m = driver.execute_script(JS)
                if m is None:
                    continue
                actual = 'open' if m['sidebarOpen'] else 'closed'
                errs = [l for l in driver.get_log('browser') if l['level'] == 'SEVERE']
                m.update(page=name, w=w, want=want, actual=actual, console=len(errs),
                         errSample=[e['message'][:90] for e in errs[:2]])
                rows.append(m)
                flag = '' if actual == want else '  <-- SAI TRANG THAI'
                print(f"  {name:10s} {w:4d} want={want:6s} actual={actual:6s} "
                      f"sbw={m['sidebarWidth']:3d} block={m['blockWidth']:4d} "
                      f"L={m['leftGap']:3d} R={m['rightGap']:3d} "
                      f"H={m['scrollHeight']:5d} ovf={m['overflow']} err={len(errs)}{flag}")
                if want == 'closed' and actual == 'closed' and w == 1920:
                    os.makedirs(SHOT, exist_ok=True)
                    driver.save_screenshot(os.path.join(SHOT, f'layout-{slug}.png'))
finally:
    driver.quit()
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

print('\n=== TONG KET (chi dong dung trang thai) ===')
good = [r for r in rows if r['actual'] == r['want']]
print(f'  do duoc dung trang thai: {len(good)}/{len(rows)}')
c = [r for r in good if r['w'] == 1920 and r['want'] == 'closed']
if c:
    gaps = [r['leftGap'] + r['rightGap'] for r in c]
    print(f'  1920 closed: gap tung trang = {gaps}')
    print(f'  trung binh = {sum(gaps)/len(gaps):.0f}px (muc tieu <=120) -> '
          f'{"PASS" if sum(gaps)/len(gaps) <= 120 else "FAIL"}')
o = [r for r in good if r['w'] == 1920 and r['want'] == 'open']
if o:
    bw = [r['blockWidth'] for r in o]
    print(f'  1920 open: blockWidth = {bw} (muc tieu >=1450) -> '
          f'{"PASS" if min(bw) >= 1450 else "FAIL"}')
ov = [r for r in good if r['overflow']]
print(f'  tran ngang: {len(ov)}/{len(good)} -> {"PASS" if not ov else "FAIL"}')
ce = sum(r['console'] for r in good)
print(f'  console errors tong: {ce}')
samples = {}
for r in good:
    for s in r.get('errSample') or []:
        samples[s] = samples.get(s, 0) + 1
for s, n in sorted(samples.items(), key=lambda kv: -kv[1])[:6]:
    print(f'    x{n}: {s}')

json.dump(rows, open(os.path.join(ROOT, '_newdata_audit', 'layout_fixed.json'), 'w',
                     encoding='utf-8'), indent=1, ensure_ascii=False)
print('  luu _newdata_audit/layout_fixed.json')
