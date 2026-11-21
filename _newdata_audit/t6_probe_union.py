import zipfile, io, csv, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
ts = list(csv.reader(io.StringIO(z.read(f("Technology Skills.txt")).decode("utf-8","replace")), delimiter="\t"))
h=ts[0]; ic,ie=h.index("O*NET-SOC Code"), h.index("Example")
base = collections.defaultdict(list)
for r in ts[1:]:
    if len(r)>max(ic,ie): base[r[ic][:7]].append((r[ic], r[ie]))
multi = {k:v for k,v in base.items() if len({c for c,_ in v})>1}
print("base codes with >1 detailed occupation:", len(multi), "of", len(base))
k = list(multi)[0]
detail = collections.defaultdict(set)
for c,e in multi[k]: detail[c].add(e)
print("example base", k, "-> detailed codes:", list(detail))
for c,v in list(detail.items())[:3]: print("   ", c, "tools:", len(v))
union = set().union(*detail.values())
print("   union tools:", len(union), "| sum of individual:", sum(len(v) for v in detail.values()))
print("   => union > each individual:", len(union) > max(len(v) for v in detail.values()))
