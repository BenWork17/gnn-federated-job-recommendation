# -*- coding: utf-8 -*-
"""YEU CAU 4 cua de bai: "Chia cac nha tuyen dung khac nhau, moi nha 1 node".
Kiem: MEDAJob co du du lieu de chia theo employer khong?
Va: chia theo employer co vi pham gia dinh FL (moi client giu user rieng) khong?
"""
import csv, os, collections, statistics

L = r"E:\2026\DUT\DSS\SauGK\Lab03"
def rd(f):
    with open(os.path.join(L, f), encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))

jobs = rd('job.csv'); rats = rd('ratings.csv'); profs = rd('user_profiles.csv')

job_emp = {j['id']: j.get('employer_id', '') for j in jobs}
print(f'tin={len(jobs)} | employer_id phan biet={len(set(job_emp.values()))}')
emp_jobs = collections.Counter(job_emp.values())
c = sorted(emp_jobs.values())
print(f'tin/employer: min={c[0]} median={c[len(c)//2]} mean={statistics.mean(c):.2f} max={c[-1]}')
print(f'employer co >=5 tin: {sum(1 for x in c if x>=5)} | >=10: {sum(1 for x in c if x>=10)}')

# rating theo employer
emp_rat = collections.Counter(job_emp[r['job_id']] for r in rats if r['job_id'] in job_emp)
d = sorted(emp_rat.values())
print(f'\nRATING theo employer: tong {len(rats)} rating tren {len(emp_rat)} employer co rating')
print(f'rating/employer: min={d[0]} median={d[len(d)//2]} mean={statistics.mean(d):.2f} max={d[-1]}')
for k in (1, 2, 3, 5, 10, 20):
    n = sum(1 for x in d if x >= k)
    print(f'  employer co >= {k:2d} rating: {n:4d}  ({100.0*n/len(emp_rat):5.1f}%)')

print(f'\nemployer co 0 rating (khong huan luyen duoc): '
      f'{len(set(job_emp.values())) - len(emp_rat)}/{len(set(job_emp.values()))}')

# VI PHAM GIA DINH FL: user co rating trai nhieu employer
user_emps = collections.defaultdict(set)
for r in rats:
    e = job_emp.get(r['job_id'])
    if e:
        user_emps[r['user_id']].add(e)
n_user = len(user_emps)
multi = sum(1 for v in user_emps.values() if len(v) > 1)
print(f'\n=== GIA DINH FL: moi client giu USER RIENG? ===')
print(f'user co rating: {n_user} | trong do rating trai >1 employer: {multi} '
      f'({100.0*multi/max(n_user,1):.1f}%)')
cnt = sorted(len(v) for v in user_emps.values())
print(f'so employer/user: min={cnt[0]} median={cnt[len(cnt)//2]} max={cnt[-1]}')
print('=> Neu client = employer, du lieu cua MOT user bi cat sang NHIEU client')
print('   -> vi pham gia dinh "moi client giu du lieu rieng, khong chia se user".')

# So sanh: neu chia theo nhom employer (gop lai)
print('\n=== Neu GOP employer thanh K cum (chia de) ===')
for K in (5, 8, 12):
    buckets = collections.defaultdict(list)
    for e in set(job_emp.values()):
        buckets[hash(e) % K].append(e)
    sizes = [sum(emp_rat.get(e, 0) for e in es) for es in buckets.values()]
    sizes.sort()
    print(f'  K={K:2d}: rating/client min={sizes[0]} median={sizes[len(sizes)//2]} '
          f'max={sizes[-1]} | client co <10 rating: {sum(1 for s in sizes if s < 10)}/{K}')
