# -*- coding: utf-8 -*-
"""Doc va phan tich notebook_metrics.json tai ve tu Kaggle."""
import json, os

R = r"E:\2026\DUT\DSS\SauGK\CuoiKi\results_v3"
M = json.load(open(os.path.join(R, 'notebook_metrics.json'), encoding='utf-8'))

print('=== KEY TOP-LEVEL ===')
for k in M:
    v = M[k]
    t = type(v).__name__
    sz = f'({len(v)})' if isinstance(v, (list, dict)) else ''
    print(f'  {k:28s} {t}{sz}')

def show(label, v, depth=0):
    pad = '  ' * depth
    if isinstance(v, dict):
        print(f'{pad}{label}:')
        for k2, v2 in v.items():
            if isinstance(v2, (dict, list)):
                show(k2, v2, depth + 1)
            else:
                print(f'{pad}  {k2:24s} = {v2}')
    elif isinstance(v, list):
        print(f'{pad}{label}: [{len(v)} muc]')
        for it in v[:6]:
            if isinstance(it, dict):
                print(f'{pad}  - ' + ' | '.join(f'{k3}={v3}' for k3, v3 in list(it.items())[:7]))
            else:
                print(f'{pad}  - {it}')
        if len(v) > 6:
            print(f'{pad}  ... ({len(v)-6} muc nua)')
    else:
        print(f'{pad}{label} = {v}')

for k in M:
    print()
    print('=' * 90)
    show(k, M[k])
