# -*- coding: utf-8 -*-
"""Kiểm Technology Skills.txt — phương án thay thế của t5 có thật sự phân biệt không?"""
import zipfile, collections, statistics, re

Z = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t4_verify\db_29_3_text.zip"
zf = zipfile.ZipFile(Z)

for fn in ['db_29_3_text/Technology Skills.txt',
           'db_29_3_text/Skills to Work Activities.txt',
           'db_29_3_text/Skills to Work Context.txt']:
    raw = zf.read(fn).decode('latin-1')
    lines = raw.splitlines()
    hdr = lines[0].split('\t')
    rows = [l.split('\t') for l in lines[1:] if l.strip()]
    print('=' * 92)
    print(fn)
    print('  header:', hdr[:8])
    print('  số dòng:', len(rows))
    # tìm cột
    def col(*names):
        for n in names:
            if n in hdr:
                return hdr.index(n)
        return None
    i_soc = col('O*NET-SOC Code')
    if i_soc is None:
        continue
    occs = {r[i_soc] for r in rows}
    print('  số nghề:', len(occs))
    # cột thực thể (skill/software/activity)
    cand = [i for i, h in enumerate(hdr) if h in
            ('Example', 'Element Name', 'Work Context', 'Work Activity', 'Technology Skills')]
    if cand:
        i = cand[0]
        ents = {r[i] for r in rows}
        print(f'  cột thực thể: {hdr[i]!r} | số giá trị phân biệt: {len(ents)}')
        m = collections.defaultdict(set)
        for r in rows:
            m[r[i_soc]].add(r[i])
        c = sorted(len(v) for v in m.values())
        print(f'  thực thể/nghề: min {c[0]} median {c[len(c)//2]} mean {statistics.mean(c):.1f} max {c[-1]}')
        # entropy khác biệt
        full = len(ents)
        print(f'  nghề có ĐỦ tất cả {full} thực thể: {sum(1 for v in m.values() if len(v) == full)} / {len(m)}')
        freq = collections.Counter()
        for v in m.values():
            for e in v:
                freq[e] += 1
        n_occ = len(m)
        print('  thực thể xuất hiện ở >=99% nghề:', sum(1 for e, c2 in freq.items() if c2 >= 0.99 * n_occ))
        print('  thực thể xuất hiện ở <=5% nghề :', sum(1 for e, c2 in freq.items() if c2 <= 0.05 * n_occ))
        print('  top 5 phổ biến:', freq.most_common(5))
