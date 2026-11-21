# -*- coding: utf-8 -*-
"""KIỂM CHỨNG ĐỘC LẬP: MEDAJob có phải dữ liệu tổng hợp hoàn toàn như tôi đã nói?
doc-writer phản biện. Phải kiểm file thô, không suy đoán.
"""
import csv, os, collections, statistics

L = r"E:\2026\DUT\DSS\SauGK\Lab03"
def rd(f):
    with open(os.path.join(L, f), encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))

jobs = rd('job.csv')
users = rd('users.csv')
profs = rd('user_profiles.csv')
rats = rd('ratings.csv')
print(f'job={len(jobs)} users={len(users)} profiles={len(profs)} ratings={len(rats)}')

print('\n=== 1. TEN CONG TY ===')
comp = collections.Counter(j['company_name'] for j in jobs)
print('distinct company_name:', len(comp))
print('top 15:', comp.most_common(15))
generic = [c for c in comp if c.lower().startswith('tech company')]
print('dạng "Tech Company N":', len(generic), 'tên |', sum(comp[c] for c in generic), 'tin')
ratio = 100.0 * sum(comp[c] for c in generic) / len(jobs)
print(f'=> {ratio:.2f}% tin thuộc dạng tổng hợp')

print('\n=== 2. LINK / EMAIL ===')
links = [j.get('link', '') for j in jobs]
ex = sum(1 for l in links if 'example.com' in l)
print(f'link chứa example.com: {ex}/{len(links)} = {100.0*ex/len(links):.2f}%')
hrs = [j.get('hr_contact', '') for j in jobs]
hr_ex = sum(1 for h in hrs if '@example.com' in h)
print(f'hr_contact @example.com: {hr_ex}/{len(hrs)} = {100.0*hr_ex/len(hrs):.2f}%')
webs = [j.get('company_website', '') for j in jobs]
ws_ex = sum(1 for w in webs if 'example.com' in w)
print(f'company_website example.com: {ws_ex}/{len(webs)} = {100.0*ws_ex/len(webs):.2f}%')

print('\n=== 3. CATEGORICAL CO SACH KHONG ===')
for c in ('job_type', 'experience_level', 'job_location', 'job_country'):
    vals = collections.Counter(j.get(c, '') for j in jobs)
    print(f'  {c}: {len(vals)} giá trị -> {list(vals.items())[:6]}')

print('\n=== 4. RATING PHAN BO ===')
r = collections.Counter(x['rating'] for x in rats)
print('  rating:', dict(sorted(r.items())))
print('  comment rỗng:', sum(1 for x in rats if not x.get('comment', '').strip()), '/', len(rats))

print('\n=== 5. NGUOI DANH GIA ===')
uids = {u['id']: u for u in users}
raters = collections.Counter(x['user_id'] for x in rats)
print('  số tài khoản đã rating:', len(raters))
roles = collections.Counter(uids.get(uid, {}).get('role', '?') for uid in raters)
print('  role:', dict(roles))
names = [uids.get(uid, {}).get('username', '?') for uid in raters]
print('  username mẫu:', names[:10])
sv = sum(1 for n in names if n.startswith('sv'))
print(f'  username dạng sv+ số: {sv}/{len(names)}')
mails = [uids.get(uid, {}).get('email', '') for uid in raters]
dut = sum(1 for m in mails if '@dut' in m)
print(f'  email @dut: {dut}/{len(mails)}')
print('  email mẫu:', mails[:6])

print('\n=== 6. PHU TIN ===')
rated = {x['job_id'] for x in rats}
print(f'  job KHÔNG có rating: {len(jobs)-len(rated)}/{len(jobs)} = {100.0*(len(jobs)-len(rated))/len(jobs):.2f}%')
print(f'  user KHÔNG rating: {len(users)-len(raters)}/{len(users)} = {100.0*(len(users)-len(raters))/len(users):.2f}%')

print('\n=== 7. HO SO ===')
prole = collections.Counter(uids.get(p['user_id'], {}).get('role', '?') for p in profs)
print('  role của người có profile:', dict(prole))
print('  cv_url rỗng:', sum(1 for p in profs if not p.get('cv_url', '').strip()), '/', len(profs))
print('  profile_vector rỗng:', sum(1 for p in profs if not p.get('profile_vector', '').strip()), '/', len(profs))

print('\n=== KET LUAN ===')
print('Số liệu trên tự nói. Không suy diễn thêm.')
