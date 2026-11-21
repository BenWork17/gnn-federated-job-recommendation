# Chung minh co che dem trung: 2 ma day du cung nhom goc -> tra 1 lan nhung cong 2 lan
import zipfile, io, csv, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
ts = list(csv.reader(io.StringIO(z.read(f("Technology Skills.txt")).decode("utf-8","replace")), delimiter="\t"))
h=ts[0]; ic,ie=h.index("O*NET-SOC Code"), h.index("Example")
base = collections.defaultdict(set)
for r in ts[1:]:
    if len(r)>max(ic,ie): base[r[ic][:7]].add(r[ie])
# gia lap p1_socs = 2 ma day du cung nhom 11-1011
p1_socs = ["11-1011.00", "11-1011.03"]
mixed = sum(len(base.get(s[:7], ())) for s in p1_socs)   # kieu t5
correct = sum(len(base.get(s, ())) for s in {s[:7] for s in p1_socs})  # kieu dung
print("p1_socs (ma day du):", p1_socs)
print("t5 mixed  ->", mixed, "(dem 2 lan cung 1 nhom)")
print("dung goc  ->", correct)
print("phong dai:", round(100*(mixed-correct)/correct,1), "%")
