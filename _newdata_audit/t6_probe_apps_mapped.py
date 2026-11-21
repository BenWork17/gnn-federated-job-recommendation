import csv, re, sys, unicodedata, zipfile
from collections import defaultdict
csv.field_size_limit(min(sys.maxsize, 2**31-1))
BASE=r"E:\2026\DUT\IOT\Cuoiki\NewData"
ZIP=r"_newdata_audit\t4_verify\db_29_3_text.zip"
GENDER=re.compile(r"\((?:m|f|d|w|m/w/d|m/f/d|m/f|x|gn|all genders)\)",re.I)
REMOTE=re.compile(r"\((?:remote|hybrid|onsite|on-site)\)",re.I)
YEAR=re.compile(r"\b(19|20)\d{2}\b"); NONWORD=re.compile(r"[^a-z0-9+#. ]+"); WS=re.compile(r"\s+")
def norm(s):
    s=unicodedata.normalize("NFKD",s or "").lower(); s=GENDER.sub(" ",s); s=REMOTE.sub(" ",s)
    s=YEAR.sub(" ",s); s=s.replace("&"," and "); s=NONWORD.sub(" ",s); return WS.sub(" ",s).strip()
def loose(s):
    t=re.split(r"[-/|,]",s)[0].split()
    return " ".join(t[:-1] if len(t)>2 else t)
z=zipfile.ZipFile(ZIP)
def zr(n):
    for x in z.namelist():
        if x.endswith("/"+n): return z.read(x).decode("utf-8","replace")
t2s={}
for r in list(csv.reader(zr("Alternate Titles.txt").splitlines(),delimiter="\t"))[1:]:
    if len(r)>3:
        for raw in (r[1],r[2]):
            t=norm(raw)
            if t: t2s.setdefault(t,r[0])
for r in list(csv.reader(zr("Occupation Data.txt").splitlines(),delimiter="\t"))[1:]:
    if len(r)>1:
        t=norm(r[1])
        if t: t2s.setdefault(t,r[0])
t2l={}
for t,s in t2s.items(): t2l.setdefault(loose(t),s)
j2s={}
with open(BASE+r"\jobs.tsv",encoding="utf-8",errors="replace",newline="") as f:
    rd=csv.reader(f,delimiter="\t"); h=next(rd); ij,it_=h.index("JobID"),h.index("Title")
    for row in rd:
        if it_<len(row):
            t=norm(row[it_]); j2s[row[ij]]=t2s.get(t) or t2l.get(loose(t))
tech=defaultdict(set)
for r in list(csv.reader(zr("Technology Skills.txt").splitlines(),delimiter="\t"))[1:]:
    if len(r)>1: tech[r[0][:7]].add(r[1])
tot=mapped=withskill=0
with open(BASE+r"\apps.tsv",encoding="utf-8",newline="") as f:
    rd=csv.reader(f,delimiter="\t"); h=next(rd); iu,ij=h.index("UserID"),h.index("JobID")
    for row in rd:
        tot+=1; s=j2s.get(row[ij])
        if s: mapped+=1
        if s and tech.get(s[:7]): withskill+=1
print("apps total", tot)
print("apps mapped to occupation (no skill filter):", mapped, "=", round(100*mapped/tot,3), "%")
print("apps on occ with >=1 tech skill:", withskill, "=", round(100*withskill/tot,3), "%")
print()
print("=> 641.952 (40,044%) la 'map duoc nghe' KHONG loc skill:", mapped==641952)
print("=> 636.896 (39,729%) la 'co >=1 tech skill':", withskill==636896)
