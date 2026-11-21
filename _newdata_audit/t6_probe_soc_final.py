import zipfile, io, csv, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
def load(n):
    return list(csv.DictReader(io.StringIO(z.read(f(n)).decode("utf-8","replace")), delimiter="\t"))
# 1. Moi ma O*NET deu co hau to .xx?
for name in ["Occupation Data.txt","Alternate Titles.txt","Skills.txt","Technology Skills.txt"]:
    d = load(name)
    codes = {r["O*NET-SOC Code"] for r in d}
    suf = {c for c in codes if "." in c}
    print("%-24s codes=%-5d with_suffix=%-5d base_only=%d" % (name, len(codes), len(suf), len(codes)-len(suf)))
# 2. So ma goc SOC neu gop
print()
alt = load("Alternate Titles.txt")
print("Alternate Titles: base SOC groups =", len({r["O*NET-SOC Code"][:7] for r in alt}))
# 3. Kiem tra hau to .00 la chinh, cac .xx khac la nghề chi tiet
suffix = collections.Counter(r["O*NET-SOC Code"].split(".")[1] for r in load("Occupation Data.txt"))
print("suffix distribution (top6):", suffix.most_common(6))
print("so ma chi co .00:", suffix[".00"] if ".00" in suffix else suffix["00"])
