import zipfile, io, csv, statistics, collections
import numpy as np
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
ts = list(csv.DictReader(io.StringIO(z.read(f("Technology Skills.txt")).decode("utf-8","replace")), delimiter="\t"))
base = collections.defaultdict(set)
for r in ts: base[r["O*NET-SOC Code"].split(".")[0]].add(r["Example"])
c = sorted(len(v) for v in base.values())
print("n =", len(c))
print("statistics.median      =", statistics.median(c))
print("numpy.median           =", np.median(c))
print("numpy.percentile(50)   =", np.percentile(c, 50))
print("middle two values      =", c[len(c)//2-1], c[len(c)//2])
print("lower middle           =", c[(len(c)-1)//2])
print("mean                   =", round(statistics.mean(c),2))
print("max                    =", c[-1])
