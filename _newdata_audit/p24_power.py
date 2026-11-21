# -*- coding: utf-8 -*-
"""Lượng hoá: bộ MEDAJob nhỏ đến mức nào, và cái nhỏ đó phá vỡ kết luận gì."""
import json, os, math
import numpy as np

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
reco = json.load(open(os.path.join(ROOT, 'results', 'reco_main.json'), encoding='utf-8'))
S = reco['systems']
print('các hệ có trong results:', list(S.keys()))

def per_user(name, metric='recall'):
    d = S[name].get('per_user')
    if not d:
        return None
    return np.array(d[metric]['20'], dtype=float)

names = [n for n in S if per_user(n) is not None]
print('số hệ có per_user:', len(names))

base = None
for n in names:
    a = per_user(n)
    if base is None or len(a) > len(base):
        base_name, base = n, a
print('\nuser được đánh giá (n):', len(base), '— hệ', base_name)

boot_rng = np.random.default_rng(42)
def boot_mean_ci(x, n_boot=5000):
    m = np.array([boot_rng.choice(x, len(x), replace=True).mean() for _ in range(n_boot)])
    return np.percentile(m, 2.5), np.percentile(m, 97.5)

print('\n%-28s %8s %8s %22s' % ('hệ', 'mean', 'std', 'CI 95% (bootstrap)'))
for n in names:
    a = per_user(n)
    lo, hi = boot_mean_ci(a)
    print('%-28s %8.4f %8.4f   [%.4f, %.4f]  rộng %.4f'
          % (n, a.mean(), a.std(ddof=1), lo, hi, hi - lo))

# So sánh cặp: cùng user
print('\n=== So sánh CẶP trên cùng tập user ===')
def paired(a_name, b_name, n_boot=5000):
    a, b = per_user(a_name), per_user(b_name)
    if a is None or b is None or len(a) != len(b):
        print('  %s vs %s: không so cặp được (n lệch)' % (a_name, b_name))
        return
    d = a - b
    m = np.array([boot_rng.choice(d, len(d), replace=True).mean() for _ in range(n_boot)])
    lo, hi = np.percentile(m, 2.5), np.percentile(m, 97.5)
    se = d.std(ddof=1) / math.sqrt(len(d))
    # n cần để phát hiện hiệu ứng quan sát với power 80%, alpha .05 (xấp xỉ chuẩn)
    eff = d.mean()
    if se > 0 and eff != 0:
        n_need = int(math.ceil(((1.96 + 0.84) * d.std(ddof=1) / abs(eff)) ** 2))
    else:
        n_need = None
    sig = 'CÓ' if (lo > 0 or hi < 0) else 'KHÔNG'
    print('  %-18s vs %-18s diff=%+.4f  CI[%+.4f, %+.4f]  %s ý nghĩa | n cần cho power 80%%: %s'
          % (a_name, b_name, d.mean(), lo, hi, sig, f'{n_need:,}' if n_need else '∞'))

pairs = [('fedavg', 'local_only'), ('fedavg', 'centralized'), ('fedavg', 'item_knn'),
         ('fedavg', 'popularity'), ('centralized', 'item_knn'), ('fedprox', 'fedavg')]
for a, b in pairs:
    if a in S and b in S:
        paired(a, b)

# Đảo lại để so đúng chiều
print('\n=== Theo chiều "tốt hơn - kém hơn" ===')
for a, b in pairs:
    if a in S and b in S:
        paired(b, a)
