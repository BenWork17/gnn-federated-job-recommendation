# Chứng minh cơ chế: [:7] vs mã đầy đủ
import zipfile, io, csv, statistics, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
ts = list(csv.reader(io.StringIO(z.read(f("Technology Skills.txt")).decode("utf-8","replace")), delimiter="\t"))
h = ts[0]; ic, ie = h.index("O*NET-SOC Code"), h.index("Example")
full = collections.defaultdict(set); trunc = collections.defaultdict(set)
for r in ts[1:]:
    if len(r) > max(ic, ie):
        full[r[ic]].add(r[ie]); trunc[r[ic][:7]].add(r[ie])
print("sample codes:", list({r[ic] for r in ts[1:10]}))
print("[:7] of them:", [r[ic][:7] for r in list(ts[1:10])])
for name, d in (("FULL", full), ("TRUNC[:7]", trunc)):
    c = sorted(len(v) for v in d.values())
    print("%-10s n=%d min=%d median=%s mean=%.2f max=%d" % (name, len(d), c[0], statistics.median(c), statistics.mean(c), c[-1]))
