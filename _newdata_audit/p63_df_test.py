# -*- coding: utf-8 -*-
"""Thu nghiem doc lap: pandera Styler co render duoc trong trinh duyet khong?
Dung 1 app toi gian, khong lien quan den trang that."""
import os, subprocess, sys, time
import urllib.request

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
TMP = os.path.join(ROOT, '_newdata_audit', '_df_test')
os.makedirs(TMP, exist_ok=True)
APP = os.path.join(TMP, 'app_df.py')

open(APP, 'w', encoding='utf-8').write('''
import pandas as pd
import streamlit as st

st.title("Test dataframe")

rows = [
    {"yeu cau": "A", "cach do": "x", "thuc do": "1", "ket luan": "Dat"},
    {"yeu cau": "B", "cach do": "y", "thuc do": "2", "ket luan": "Chua"},
    {"yeu cau": "C", "cach do": "z", "thuc do": "3", "ket luan": "Dat"},
]
tbl = pd.DataFrame(rows)

def _to_mau(row):
    mau = ("color:#1e8449;font-weight:700" if row["ket luan"] == "Dat"
           else "color:#a93226;font-weight:700")
    return ["" if c != "ket luan" else mau for c in row.index]

st.subheader("1. Styler + use_container_width (cach hien tai)")
st.dataframe(tbl.style.apply(_to_mau, axis=1), use_container_width=True, hide_index=True)

st.subheader("2. Styler + width=stretch (cach moi)")
st.dataframe(tbl.style.apply(_to_mau, axis=1), width="stretch", hide_index=True)

st.subheader("3. DataFrame thuong + width=stretch")
st.dataframe(tbl, width="stretch", hide_index=True)

st.subheader("4. st.table")
st.table(tbl)
''')

PORT = 8606
env = dict(os.environ)
env['MPLCONFIGDIR'] = os.path.join(ROOT, 'artifacts', '.mplcache')
p = subprocess.Popen(
    [sys.executable, '-m', 'streamlit', 'run', APP, '--server.headless=true',
     f'--server.port={PORT}', '--browser.gatherUsageStats=false'],
    cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for i in range(40):
    time.sleep(1.5)
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{PORT}', timeout=3)
        break
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
o = Options()
o.add_argument('--headless=new')
o.add_argument('--no-sandbox')
o.add_argument('--window-size=1400,1200')
d = webdriver.Chrome(options=o)
try:
    d.get(f'http://127.0.0.1:{PORT}')
    for _ in range(40):
        n = d.execute_script("const b=document.querySelector('.block-container'); return b?b.innerText.length:0;")
        if n and n > 100:
            break
        time.sleep(0.4)
    time.sleep(2)
    info = d.execute_script("""
      return {
        dataframes: document.querySelectorAll('[data-testid="stDataFrame"]').length,
        tables: document.querySelectorAll('table').length,
        textLen: document.querySelector('.block-container').innerText.length
      };
    """)
    print('=== KET QUA ===')
    print(f'  stDataFrame elements: {info["dataframes"]} (ky vong 3)')
    print(f'  <table> elements    : {info["tables"]} (ky vong 1 tu st.table)')
    print(f'  do dai text         : {info["textLen"]}')
    d.save_screenshot(os.path.join(ROOT, '_newdata_audit', '_df_test', 'df.png'))
    print('  anh: _newdata_audit/_df_test/df.png')
finally:
    d.quit()
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
