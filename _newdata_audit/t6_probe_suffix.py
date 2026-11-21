import zipfile, io, csv, collections
z = zipfile.ZipFile(r"_newdata_audit\t4_verify\db_29_3_text.zip")
def f(n):
    for x in z.namelist():
        if x.endswith("/"+n): return x
def load(n):
    return list(csv.DictReader(io.StringIO(z.read(f(n)).decode("utf-8","replace")), delimiter="\t"))
at = load("Alternate Titles.txt")
print("Alternate Titles cols:", list(at[0].keys()), "rows", len(at))
codes = {r["O*NET-SOC Code"] for r in at}
withsuf = {c for c in codes if "." in c}
print("distinct codes:", len(codes), "| with .xx suffix:", len(withsuf), "| base-only:", len(codes)-len(withsuf))
print("sample:", sorted(list(codes))[:5])
od = load("Occupation Data.txt")
print("Occupation Data codes:", len({r["O*NET-SOC Code"] for r in od}), "| sample:", sorted({r["O*NET-SOC Code"] for r in od})[:5])
