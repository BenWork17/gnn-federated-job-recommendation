# -*- coding: utf-8 -*-
"""Bao nhiêu dữ liệu là ĐỦ? Đo trực tiếp trên kết quả hiện có."""
import json, os, math
import numpy as np

ROOT = r"E:\2026\DUT\DSS\SauGK\CuoiKi"
reco = json.load(open(os.path.join(ROOT, 'results', 'reco_main.json'), encoding='utf-8'))
meta = json.load(open(os.path.join(ROOT, 'artifacts', 'medajob', 'meta.json'), encoding='utf-8'))
S = reco['systems']

print('=== QUY MÔ BỘ MEDAJob ===')
c = meta['clean']
print('user: %d | job: %d | tương tác: %d (train %d / test %d)'
      % (c['users'], c['jobs'], c['ratings'], c['train'], c['test']))
print('user có mặt trong test: %d (%.0f%% của %d user)'
      % (c['users_in_test'], 100.0 * c['users_in_test'] / c['users'], c['users']))
print('mật độ ma trận: %.4f%%  (tức 99,57%% ô trống)' % meta['sparsity_pct'])

# Tham số vs dữ liệu
n_params = 54304
n_edges = c['train']
print('\n=== Tỉ lệ THAM SỐ / DỮ LIỆU ===')
print('tham số mô hình: %s' % format(n_params, ','))
print('tương tác huấn luyện: %s' % format(n_edges, ','))
print('=> %.0f tham số cho MỖI tương tác' % (n_params / n_edges))
print('(quy tắc kinh nghiệm: cần >=10 mẫu/tham số. Đây là %.1f lần THIẾU)'
      % (10 * n_params / n_edges))

# Bootstrap cho tuyên bố trung tâm: "lấy lại 92,9% khoảng cách"
rng = np.random.default_rng(7)
def pu(name):
    return np.array(S[name]['per_user']['recall']['20'], dtype=float)
fed, loc, cen = pu('fedavg'), pu('local_only'), pu('centralized')
gap = cen.mean() - loc.mean()
ratios, gaps = [], []
for _ in range(20000):
    i = rng.integers(0, len(fed), len(fed))
    r = (fed[i].mean() - loc[i].mean()) / (cen[i].mean() - loc[i].mean())
    ratios.append(r)
    gaps.append(cen[i].mean() - loc[i].mean())
ratios = np.array(ratios)
ok = ratios[np.isfinite(ratios)]
print('\n=== TUYÊN BỐ TRUNG TÂM: "lấy lại 92,9%% khoảng cách" ===')
print('điểm ước lượng: %.1f%%' % (100 * (fed.mean() - loc.mean()) / gap))
print('bootstrap 95%%: [%.0f%%, %.0f%%]' % (100 * np.percentile(ok, 2.5),
                                             100 * np.percentile(ok, 97.5)))
print('tỉ lệ lần tỉ số <0 (FL tệ hơn cục bộ): %.1f%%' % (100 * (ratios < 0).mean()))
print('tỉ lệ lần tỉ số >1 (FL vượt cả tập trung): %.1f%%' % (100 * (ratios > 1).mean()))

# Số item "liên quan" mỗi user trong test -> mẫu số của Recall
print('\n=== MẪU SỐ THẬT của Recall@20 ===')
print('mỗi user test có trung bình %.2f tin "liên quan" (rating>=4)'
      % (c['test'] / c['users_in_test']))
print('=> Recall@20 chỉ có thể nhận các giá trị rời rạc: 0, 1/4, 1/3, 1/2, 1, ...')
print('   với ~3,6 tin/user, mỗi lần "hit" thêm làm R@20 nhảy ~0,28 trên một user')

# Nếu n = 16 -> muốn hẹp CI xuống bao nhiêu cần bao nhiêu user?
sd = fed.std(ddof=1)
print('\n=== CẦN BAO NHIÊU USER ĐỂ SO CẶP fedavg vs local_only ===')
d = fed - loc
eff, sdd = d.mean(), d.std(ddof=1)
for target in (0.05, 0.03, 0.02):
    n = ((1.96 + 0.84) * sdd / target) ** 2
    print('  muốn phát hiện hiệu ứng %.2f (power 80%%, alpha 5%%): cần %s user'
          % (target, format(int(math.ceil(n)), ',')))
print('  hiện có: 16 user')

# So sánh trực tiếp với bộ mới
print('\n=== SO VỚI BỘ MỚI ===')
new_users, new_jobs, new_apps = 321235, 365668, 1603111
print('%-22s %10s %10s %12s %10s' % ('', 'users', 'jobs', 'interactions', 'density'))
print('%-22s %10s %10s %12s %10s' % ('MEDAJob', '70', '1.014', '307', '0,4325%'))
print('%-22s %10d %10d %12d %10s' % ('Bộ mới', new_users, new_jobs, new_apps, '0,0014%'))
print('hệ số: user x%.0f | job x%.0f | tương tác x%.0f'
      % (new_users/70, new_jobs/1014, new_apps/307))
