import zipfile, io, csv, statistics, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
def load(n):
    return list(csv.DictReader(io.StringIO(z.read(f(n)).decode("utf-8","replace")), delimiter="\t"))

ts = load("Technology Skills.txt")
print("=== Technology Skills.txt ===")
print("full codes:", len({r["O*NET-SOC Code"] for r in ts}))
# group by full code
full = collections.defaultdict(set)
for r in ts: full[r["O*NET-SOC Code"]].add(r["Example"])
c = sorted(len(v) for v in full.values())
print("FULL: n=%d min=%d median=%s mean=%.2f max=%d" % (len(full), c[0], statistics.median(c), statistics.mean(c), c[-1]))
# group by base 6-char SOC
base = collections.defaultdict(set)
for r in ts: base[r["O*NET-SOC Code"].split(".")[0]].add(r["Example"])
c2 = sorted(len(v) for v in base.values())
print("BASE: n=%d min=%d median=%s mean=%.2f max=%d" % (len(base), c2[0], statistics.median(c2), statistics.mean(c2), c2[-1]))

sk = load("Skills.txt")
print()
print("=== Skills.txt ===")
fullsk = collections.defaultdict(set)
for r in sk: fullsk[r["O*NET-SOC Code"]].add(r["Element ID"])
basesk = collections.defaultdict(set)
for r in sk: basesk[r["O*NET-SOC Code"].split(".")[0]].add(r["Element ID"])
print("FULL codes:", len(fullsk), "| BASE codes:", len(basesk))
cf = sorted(len(v) for v in fullsk.values())
cb = sorted(len(v) for v in basesk.values())
print("FULL: min=%d max=%d | all35=%d/%d" % (cf[0], cf[-1], sum(1 for v in cf if v==35), len(cf)))
print("BASE: min=%d max=%d | all35=%d/%d" % (cb[0], cb[-1], sum(1 for v in cb if v==35), len(cb)))
