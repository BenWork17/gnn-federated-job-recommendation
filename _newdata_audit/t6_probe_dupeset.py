import zipfile, io, csv, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
ts = list(csv.reader(io.StringIO(z.read(f("Technology Skills.txt")).decode("utf-8","replace")), delimiter="\t"))
h=ts[0]; ic,ie=h.index("O*NET-SOC Code"), h.index("Example")
full = collections.defaultdict(set); base = collections.defaultdict(set)
for r in ts[1:]:
    if len(r)>max(ic,ie):
        full[r[ic]].add(r[ie]); base[r[ic][:7]].add(r[ie])
print("full codes:", len(full), "| base groups:", len(base))
# For a base group with several full codes, the tuples become identical skill sets
dup = collections.Counter()
for c in full: dup[tuple(sorted(base[c[:7]]))]+=1
identical = sum(v for v in dup.values() if v>1)
print("full codes whose skill-set equals another full code's:", identical)
print("distinct skill-set signatures among 923 full codes:", len(dup))
print("=> neu dung nut Occupation o cap MA DAY DU nhung skill o cap GOC, so tap skill phan biet =", len(dup))
