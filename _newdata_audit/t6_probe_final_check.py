import zipfile, io, csv, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
ts = list(csv.reader(io.StringIO(z.read(f("Technology Skills.txt")).decode("utf-8","replace")), delimiter="\t"))
h=ts[0]; ic,ie=h.index("O*NET-SOC Code"), h.index("Example")
base = collections.defaultdict(set)
for r in ts[1:]:
    if len(r)>max(ic,ie): base[r[ic][:7]].add(r[ic])
multi = {k:v for k,v in base.items() if len(v)>1}
print("base groups total:", len(base))
print("base groups containing >1 detailed code:", len(multi), "=", round(100*len(multi)/len(base),2), "%")
print("extra detailed codes absorbed:", sum(len(v)-1 for v in multi.values()))
print("923 - (extra) =", 923 - sum(len(v)-1 for v in multi.values()))
# does CareerBuilder have any SOC column at all?
import csv as c2
with open(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv", encoding="utf-8", newline="") as fh:
    hdr = next(c2.reader(fh, delimiter="\t"))
print("CareerBuilder jobs.tsv columns:", hdr)
print("any SOC/occupation column:", [x for x in hdr if "soc" in x.lower() or "occup" in x.lower()] or "NONE")
