import csv, os, collections
base = r"E:\2026\DUT\IOT\Cuoiki\NewData"
p = os.path.join(base, "jobs.tsv")
with open(p, encoding='utf-8', errors='replace', newline='') as fh:
    r = csv.reader(fh, delimiter='\t')
    hdr = next(r)
    print('HEADER', len(hdr), hdr)
    for i, row in enumerate(r):
        if i >= 3:
            break
        print('--- row', i, 'nfields=', len(row))
        for h, v in zip(hdr, row):
            print(f'   {h!r}: {v[:160]!r}')
