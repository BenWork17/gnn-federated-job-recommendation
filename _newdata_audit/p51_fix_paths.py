# -*- coding: utf-8 -*-
"""Sua danh sach duong dan trong notebook (.ipynb) va source (.py)
de ho tro CA HAI dang Kaggle:
  - /kaggle/input/<dataset-slug>                 (dang cu)
  - /kaggle/input/datasets/<username>/<slug>     (dang moi)
Va ca truong hop zip co folder con.
"""
import json, re, os

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
NB = os.path.join(ROOT, 'notebooks', '01_gnn_fl.ipynb')
PY = os.path.join(ROOT, 'notebooks', '01_gnn_fl_source.py')

NEW_CANDS = '''    cands = [
        os.environ.get("DSS_ARTIFACT_DIR", ""),
        # --- Kaggle: dạng MỚI (datasets/<user>/<slug>) ---
        "/kaggle/input/datasets/baohoanhao/dss-gnn-fl-v3",
        "/kaggle/input/datasets/baohoanhao/dss-gnn-fl-v3/v3",
        "/kaggle/input/datasets/baohoanhao/dss-gnn-fl-v3/artifacts/v3",
        # --- Kaggle: dạng CŨ (<slug>) ---
        "/kaggle/input/dss-gnn-fl-v3/v3",
        "/kaggle/input/dss-gnn-fl-v3",
        "/kaggle/input/dss-gnn-fl-v3/artifacts/v3",
        # --- local ---
        here,
        os.path.join(here, "artifacts", "v3"),
        os.path.dirname(here),
        os.path.join(os.path.dirname(here), "artifacts", "v3"),
        # --- Colab ---
        "/content/GNN-FL-JobRec/artifacts/v3",
        "/content/artifacts/v3",
        "/content/drive/MyDrive/dss-gnn-fl-v3/artifacts/v3",
        "/content/drive/MyDrive/dss-gnn-fl-v3",
    ]'''

OLD_PAT = re.compile(
    r"    cands = \[\n"
    r"        os\.environ\.get\(\"DSS_ARTIFACT_DIR\", \"\"\),.*?\n    \]",
    re.S)

def patch_text(txt, label):
    if not OLD_PAT.search(txt):
        print(f'  [{label}] KHONG TIM THAY mau cands — bo qua')
        return txt, False
    txt2 = OLD_PAT.sub(NEW_CANDS, txt, count=1)
    return txt2, True

# ---- 1. sua file .py ----
py = open(PY, encoding='utf-8').read()
py2, ok1 = patch_text(py, 'source.py')
if ok1:
    open(PY, 'w', encoding='utf-8').write(py2)
print(f'source.py: {"PATCHED" if ok1 else "KHONG DOI"}')

# ---- 2. sua file .ipynb ----
nb = json.load(open(NB, encoding='utf-8'))
patched = 0
for i, c in enumerate(nb['cells']):
    if c['cell_type'] != 'code':
        continue
    src = ''.join(c['source'])
    if 'cands = [' in src and 'DSS_ARTIFACT_DIR' in src:
        new_src, ok = patch_text(src, f'cell{i}')
        if ok:
            # giu dang list-of-lines nhu ipynb chuan
            nb['cells'][i]['source'] = new_src.splitlines(keepends=True)
            patched += 1
            print(f'  cell {i}: PATCHED')
if patched:
    json.dump(nb, open(NB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'ipynb: {patched} cell da sua')

# ---- 3. kiem tra lai ----
print('\n=== KIEM TRA ===')
nb2 = json.load(open(NB, encoding='utf-8'))
for i, c in enumerate(nb2['cells']):
    if c['cell_type'] != 'code':
        continue
    src = ''.join(c['source'])
    if 'datasets/baohoanhao' in src:
        print(f'  cell {i}: co duong dan moi OK')
py3 = open(PY, encoding='utf-8').read()
print(f'  source.py co "datasets/baohoanhao": {"datasets/baohoanhao" in py3}')
print(f'  source.py con glob: {"glob.glob" in py3}')
