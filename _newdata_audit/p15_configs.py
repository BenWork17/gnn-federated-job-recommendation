# -*- coding: utf-8 -*-
"""Ước lượng cấu hình thực nghiệm khả thi + chi phí truyền thông FL trên dữ liệu mới."""
import os, collections, json

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"

user_apps = collections.Counter()
job_apps = collections.Counter()
edges = []
with open(os.path.join(BASE, 'apps.tsv'), 'rb') as fh:
    fh.readline()
    for raw in fh:
        p = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
        if len(p) != 5:
            continue
        u, j = int(p[0]), int(p[4])
        user_apps[u] += 1
        job_apps[j] += 1
        edges.append((u, j))

print('=== Cấu hình thực nghiệm khả thi (app nằm trong giao user x job) ===')
print('%-28s %8s %8s %9s %10s %10s' % ('điều kiện', 'users', 'jobs', 'apps', 'density%', 'app/user'))
configs = [(1, 1), (5, 5), (10, 10), (20, 10), (20, 20), (50, 20), (30, 5)]
for umin, jmin in configs:
    U = {u for u, c in user_apps.items() if c >= umin}
    J = {j for j, c in job_apps.items() if c >= jmin}
    n = sum(1 for u, j in edges if u in U and j in J)
    dens = 100.0*n/(len(U)*len(J)) if U and J else 0
    print('%-28s %8d %8d %9d %10.4f %10.1f'
          % ('user>=%d, job>=%d' % (umin, jmin), len(U), len(J), n, dens, n/max(len(U), 1)))

# Trọng số phổ biến: nghịch đảo tần suất
print('\n=== Độ lệch phổ biến của item (trong tập user>=10 & job>=10) ===')
U = {u for u, c in user_apps.items() if c >= 10}
J = {j for j, c in job_apps.items() if c >= 10}
c = sorted([job_apps[j] for j in J])
print('item popularity: min %d median %d p90 %d p99 %d max %d'
      % (c[0], c[len(c)//2], c[int(len(c)*.9)], c[int(len(c)*.99)], c[-1]))

# ---- Chi phí truyền thông FL
print('\n=== Ước lượng băng thông FL (dim=32, float32) ===')
for name, nU, nJ, nEdges in [
        ('toàn bộ', 321235, 365668, 1603111),
        ('user>=10 & job>=10', 36387, 37538, 495684),
        ('user>=20 & job>=20', None, None, None)]:
    if nU is None:
        continue
    n_nodes = nU + nJ + 2000 + 20  # + skill + industry (giả định tối thiểu)
    payload = n_nodes * 32 * 4
    raw = nEdges * (8 + 8 + 4)  # user_id, job_id, timestamp int64/int64/int32
    rounds = 20
    print('%-22s nodes=%8d | payload/vòng=%9.1f MB | %d vòng=%8.1f MB | raw=%9.2f MB | tỉ lệ=%.1fx'
          % (name, n_nodes, payload/1e6, rounds, rounds*payload/1e6, raw/1e6,
             (rounds*payload)/raw))
    be = rounds*payload/(12.0)
    print('%-22s điểm hoà vốn: %s tương tác' % ('', format(int(be), ',')))
