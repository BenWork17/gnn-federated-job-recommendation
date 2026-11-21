# -*- coding: utf-8 -*-
"""Streaming profile jobs.tsv (3.4GB) - single pass, low memory."""
import os, sys, collections, json, random, re

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit"
path = os.path.join(BASE, 'jobs.tsv')
TOTAL = 1092096
SAMPLE_RATE = 4000.0 / TOTAL

n = 0
bad = 0
win = collections.Counter()
state = collections.Counter()
country = collections.Counter()
zip_bad = 0
empty_desc = 0
empty_req = 0
has_html = 0
boiler_req = 0
dup_titles = collections.Counter()
jobid_seen = set()
jobid_dup = 0
len_title, len_desc, len_req = [], [], []
start_min, start_max, end_min, end_max = '', '', '9', '0'
samp = []

def stats(arr, name):
    a = sorted(arr); k = len(a)
    print('%s: min %d p25 %d median %d p75 %d p95 %d p99 %d max %d mean %.0f empty %d' % (
        name, a[0], a[k//4], a[k//2], a[3*k//4], a[int(k*.95)], a[int(k*.99)], a[-1],
        sum(a)/k, sum(1 for x in a if x == 0)))

with open(path, 'rb') as fh:
    hdr = fh.readline().decode('utf-8', 'replace').rstrip('\r\n').split('\t')
    print('HEADER:', hdr, flush=True)
    for i, raw in enumerate(fh):
        line = raw.decode('utf-8', 'replace').rstrip('\r\n')
        p = line.split('\t')
        if len(p) != 11:
            bad += 1
            if bad <= 5:
                print('BADLINE nfields=%d :: %s' % (len(p), line[:160]), flush=True)
            continue
        jid, w, title, desc, req, city, st, cou, zip5, sd, ed = p
        n += 1
        win[w] += 1
        state[st] += 1
        country[cou] += 1
        if not re.fullmatch(r'\d{5}', zip5 or ''):
            zip_bad += 1
        if not desc.strip():
            empty_desc += 1
        if not req.strip():
            empty_req += 1
        if '<' in desc:
            has_html += 1
        if 'please refer to the job description' in req.lower():
            boiler_req += 1
        dup_titles[title.strip().lower()] += 1
        try:
            ji = int(jid)
            if ji in jobid_seen:
                jobid_dup += 1
            jobid_seen.add(ji)
        except ValueError:
            pass
        len_title.append(len(title)); len_desc.append(len(desc)); len_req.append(len(req))
        s, e = sd[:10], ed[:10]
        if s < (start_min or '9'): start_min = s
        if s > start_max: start_max = s
        if e < end_min: end_min = e
        if e > end_max: end_max = e
        if random.random() < SAMPLE_RATE:
            samp.append(line)
        if n % 250000 == 0:
            print('  ... %d rows (sample=%d)' % (n, len(samp)), flush=True)

print('\n=== JOBS SUMMARY ===')
print('rows:', n, '| bad lines:', bad)
print('unique JobID:', len(jobid_seen), '| duplicate JobID rows:', jobid_dup)
print('window counts:', dict(sorted(win.items(), key=lambda kv: int(kv[0]))))
print('country:', dict(country.most_common(10)))
print('state top20:', dict(state.most_common(20)))
print('bad zip5:', zip_bad)
print('empty Description:', empty_desc, '| empty Requirements:', empty_req)
print('rows containing HTML tags:', has_html)
print('Requirements boilerplate "please refer":', boiler_req)
print('StartDate range:', start_min, '->', start_max, '| EndDate:', end_min, '->', end_max)
stats(len_title, 'Title len')
stats(len_desc, 'Description len')
stats(len_req, 'Requirements len')

tot_dup = sum(c - 1 for c in dup_titles.values() if c > 1)
print('\nTop duplicated titles:')
for t, c in dup_titles.most_common(10):
    print('  %5d  %s' % (c, t[:90]))
print('rows with duplicated normalized title: %d (%.1f%%)' % (tot_dup, 100.0*tot_dup/max(n,1)))
print('unique normalized titles:', len(dup_titles))

json.dump({'rows': n, 'bad': bad, 'unique_jobid': len(jobid_seen), 'jobid_dup': jobid_dup,
           'window': {k: v for k, v in sorted(win.items(), key=lambda kv: int(kv[0]))},
           'empty_desc': empty_desc, 'empty_req': empty_req, 'has_html': has_html,
           'boiler_req': boiler_req, 'uniq_titles': len(dup_titles), 'dup_title_rows': tot_dup,
           'start_min': start_min, 'start_max': start_max, 'end_min': end_min, 'end_max': end_max,
           'bad_zip': zip_bad, 'countries': dict(country.most_common(10)),
           'states': dict(state.most_common(60))},
          open(os.path.join(OUT, 'jobs_stats.json'), 'w', encoding='utf-8'), indent=1)

with open(os.path.join(OUT, 'jobs_sample.tsv'), 'w', encoding='utf-8', newline='') as out:
    out.write('\t'.join(hdr) + '\n')
    for line in samp:
        out.write(line + '\n')
print('saved %d sample rows' % len(samp))
