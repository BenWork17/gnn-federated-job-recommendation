import csv, os, sys
base = r"E:\2026\DUT\IOT\Cuoiki\NewData"
for f in ["apps.tsv", "users.tsv", "user_history.tsv"]:
    p = os.path.join(base, f)
    with open(p, encoding='utf-8', errors='replace', newline='') as fh:
        r = csv.reader(fh, delimiter='\t')
        hdr = next(r)
        cnt = {}
        for i, row in enumerate(r):
            if i >= 500: break
            cnt[len(row)] = cnt.get(len(row), 0) + 1
        print(f, '| ncols=', len(hdr), '| field-counts(first500)=', cnt)
    with open(p, encoding='utf-8', errors='replace') as fh:
        print('  header:', fh.readline().rstrip('\n'))
        for _ in range(2):
            print('  row   :', fh.readline().rstrip('\n')[:300])
    print()
