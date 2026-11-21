import zipfile, io, csv, statistics, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
sk = list(csv.DictReader(io.StringIO(z.read(f("Skills.txt")).decode("utf-8","replace")), delimiter="\t"))
oc = list(csv.DictReader(io.StringIO(z.read(f("Occupation Data.txt")).decode("utf-8","replace")), delimiter="\t"))
print("occupation data rows", len(oc), "codes", len({r["O*NET-SOC Code"] for r in oc}))
print("Skills.txt codes", len({r["O*NET-SOC Code"] for r in sk}))
print("Skills scale IDs", collections.Counter(r["Scale ID"] for r in sk))
print("Skills rows per scale", collections.Counter(r["Scale ID"] for r in sk).most_common())
codes_oc = {r["O*NET-SOC Code"] for r in oc}
codes_sk = {r["O*NET-SOC Code"] for r in sk}
print("skills codes ∩ occupation data codes:", len(codes_sk & codes_oc))
# with IM only
im = [r for r in sk if r["Scale ID"]=="IM"]
print("IM rows", len(im), "IM codes", len({r["O*NET-SOC Code"] for r in im}))
ts = list(csv.DictReader(io.StringIO(z.read(f("Technology Skills.txt")).decode("utf-8","replace")), delimiter="\t"))
codes_ts = {r["O*NET-SOC Code"] for r in ts}
print("tech codes", len(codes_ts), "∩ occ data:", len(codes_ts & codes_oc))
