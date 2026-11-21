# -*- coding: utf-8 -*-
"""KIá»‚M CHá»¨NG Äá»˜C Láº¬P tuyÃªn bá»‘ cá»§a t5: O*NET Skills.txt gÃ¡n Ä‘á»§ 35 ká»¹ nÄƒng cho 100% nghá»?
Náº¿u Ä‘Ãºng -> lá»›p Skill vÃ´ dá»¥ng (entropy=0). Náº¿u sai -> t5 sai vÃ  pháº£i sá»­a.
"""
import zipfile, collections, os, statistics

Z = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t4_verify\db_29_3_text.zip"
zf = zipfile.ZipFile(Z)
names = zf.namelist()
print('sá»‘ file trong zip:', len(names))
print('cÃ¡c file cÃ³ "Skills":', [n for n in names if 'Skills' in n][:10])

raw = zf.read('db_29_3_text/Skills.txt').decode('latin-1')
lines = raw.splitlines()
hdr = lines[0].split('\t')
print('\nSkills.txt header:', hdr[:8])
rows = [l.split('\t') for l in lines[1:] if l.strip()]
print('sá»‘ dÃ²ng:', len(rows))

i_soc, i_elem, i_name, i_scale = (hdr.index('O*NET-SOC Code'), hdr.index('Element ID'),
                                  hdr.index('Element Name'), hdr.index('Scale ID'))
occs = {r[i_soc] for r in rows}
elems = {(r[i_elem], r[i_name]) for r in rows}
scales = collections.Counter(r[i_scale] for r in rows)
print('sá»‘ nghá» (SOC code):', len(occs))
print('sá»‘ (Element ID, Name) phÃ¢n biá»‡t:', len(elems))
print('Scale ID:', dict(scales))

# Chá»‰ láº¥y scale IM (Importance) Ä‘á»ƒ Ä‘áº¿m
im = [r for r in rows if r[i_scale] == 'IM']
occ_to_elems = collections.defaultdict(set)
for r in im:
    occ_to_elems[r[i_soc]].add(r[i_elem])
counts = [len(v) for v in occ_to_elems.values()]
print('\n--- Vá»šI SCALE IM (Importance) ---')
print('sá»‘ nghá» cÃ³ IM:', len(occ_to_elems))
print('sá»‘ element phÃ¢n biá»‡t:', len({e for v in occ_to_elems.values() for e in v}))
counts.sort()
print('element/nghá»: min %d median %d mean %.1f max %d' %
      (counts[0], counts[len(counts)//2], statistics.mean(counts), counts[-1]))
full = [o for o, v in occ_to_elems.items() if len(v) == len({e for vv in occ_to_elems.values() for e in vv})]
print('sá»‘ nghá» cÃ³ Äá»¦ táº¥t cáº£ element: %d / %d' % (len(full), len(occ_to_elems)))

# entropy cá»§a phÃ¢n bá»‘ "nghá» nÃ o cÃ³ ká»¹ nÄƒng nÃ o"
import math
all_e = {e for v in occ_to_elems.values() for e in v}
print('\n--- TEST ENTROPY ---')
freq = collections.Counter()
for o, v in occ_to_elems.items():
    for e in v:
        freq[e] += 1
print('sá»‘ ká»¹ nÄƒng xuáº¥t hiá»‡n á»Ÿ >=99% nghá»:',
      sum(1 for e, c in freq.items() if c >= 0.99 * len(occ_to_elems)))
print('sá»‘ ká»¹ nÄƒng xuáº¥t hiá»‡n á»Ÿ <=50% nghá»:',
      sum(1 for e, c in freq.items() if c <= 0.50 * len(occ_to_elems)))
print('tá»•ng element:', len(all_e))
print('\nTuyÃªn bá»‘ cá»§a t5: "gÃ¡n Ä‘á»§ 35/35 cho 763/763 nghá» = 100%"')
print('Sá»‘ element thá»±c táº¿:', len(all_e), '| sá»‘ nghá»:', len(occ_to_elems))
print('=> Náº¾U element thá»±c táº¿ > 35, tuyÃªn bá»‘ "35" cá»§a t5 lÃ  SAI.')

