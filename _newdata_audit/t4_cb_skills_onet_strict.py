"""t4: % tin CareerBuilder co >=1 KY NANG trich duoc — ban CHAT (tranh duong tinh gia).

Van de cua ban truoc: gazetteer O*NET Technology Skills co nhieu muc 1-token
("r", "c", "go", "act", "analyze", "reduce", "chef", "route") -> khop nham hang tram
nghin tin (chu "r" xuat hien o moi noi). Do la DUONG TINH GIA.

Sua:
  - Chi giu cum >=2 token, HOAC 1-token nhung la ten rieng cong nghe ro rang
    (python, java, javascript, linux, unix, ajax, vmware, excel, oracle, sap,
    autocad, solidworks, matlab, kubernetes, docker, hadoop, spark, kafka, salesforce)
    va KHONG nam trong danh sach tu tieng Anh thong thuong.
  - Khop theo bien gioi tu (regex \\b...\\b) tren text da bo HTML.
  - Lay mau PHAN TANG theo toan file (moi dong thu 12) de khong chi doc dau file.

Ket qua: % tin co >=1 ky nang (can duoi, chi phu ky nang cong nghe).
"""
import csv
import html
import json
import re
import statistics
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

OUT = Path(r"_newdata_audit/t4_verify")
ZIP = OUT / "db_29_3_text.zip"
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
STRIDE = 12

if not ZIP.exists():
    req = urllib.request.Request("https://www.onetcenter.org/dl_files/database/db_29_3_text.zip",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(ZIP, "wb") as f:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            f.write(c)

with zipfile.ZipFile(ZIP) as z:
    name = [n for n in z.namelist() if n.endswith("Technology Skills.txt")][0]
    raw = z.read(name).decode("utf-8", "replace")
rows = list(csv.reader(raw.splitlines(), delimiter="\t"))
h = rows[0]
iex = h.index("Example")
examples = sorted({r[iex].strip() for r in rows[1:] if len(r) > iex and r[iex].strip()})

WORD = re.compile(r"[A-Za-z0-9+#._\-]+")
COMMON_EN = set("""a an the and or of for with to in on at by from as is are be been being this that
these those it its all any both each few more most other some such no nor not only own same so than
too very can will just should now who whom which what when where why how i you he she we they them
his her their our your my me us do does did doing have has had having would could may might must
shall about above across after again against among around before below between during into through
under until up down out off over then once here there also within without per via using use used
users user work working works""".split())
SINGLE_OK = {
    "python", "java", "javascript", "typescript", "linux", "unix", "ajax", "vmware", "excel",
    "oracle", "sap", "autocad", "solidworks", "matlab", "kubernetes", "docker", "hadoop",
    "spark", "kafka", "salesforce", "quickbooks", "sharepoint", "photoshop", "peoplesoft",
    "sas", "stata", "spss", "perl", "php", "ruby", "scala", "kotlin", "swift", "drupal",
    "wordpress", "jquery", "angular", "reactjs", "nodejs", "tensorflow", "pytorch", "keras",
    "git", "jenkins", "ansible", "puppet", "chef", "terraform", "nginx", "apache", "tomcat",
    "mysql", "postgresql", "mongodb", "redis", "hive", "pig", "cognos", "tableau", "hyperion",
    "peachtree", "sagem", "meditech", "epic", "cerner", "citrix", "activedirectory",
}
gaz = []
for e in examples:
    toks = WORD.findall(e)
    if not (1 <= len(toks) <= 4):
        continue
    if len(toks) == 1:
        if toks[0].lower() not in SINGLE_OK:
            continue
    else:
        if any(t.lower() in COMMON_EN for t in toks):
            continue
    gaz.append(e)
# bien gioi tu, khong phan biet hoa thuong
pat = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(g) for g in sorted(gaz, key=len, reverse=True)) + r")(?![A-Za-z0-9])", re.I)
print("gazetteer strict:", len(gaz), "-> regex groups:", pat.groups)

TAG = re.compile(r"<[^>]{0,400}>")
ENT = re.compile(r"&[a-zA-Z]{2,8};|&#\d{2,5};")

n = 0
considered = 0
n_ge1 = 0
per_doc = []
matched = Counter()
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    hh = next(rd)
    idesc, ireq = hh.index("Description"), hh.index("Requirements")
    for i, row in enumerate(rd):
        n += 1
        if i % STRIDE:
            continue
        considered += 1
        if len(row) <= max(idesc, ireq):
            per_doc.append(0)
            continue
        text = html.unescape(ENT.sub(" ", TAG.sub(" ", row[idesc] + " " + row[ireq])))
        found = {m.group(1).lower() for m in pat.finditer(text)}
        per_doc.append(len(found))
        if found:
            n_ge1 += 1
            for g in found:
                matched[g] += 1
        if considered % 20000 == 0:
            print("...", considered, "ge1:", n_ge1, flush=True)

per_doc.sort()


def q(v, p):
    k = min(len(v) - 1, max(0, int(round(p / 100.0 * (len(v) - 1)))))
    return v[k]


res = {
    "jobs_file": str(JOBS),
    "rows_total_in_file": n,
    "sampling": f"systematic stride {STRIDE} over the whole file (rows 0,{STRIDE},{2*STRIDE},...)",
    "sample_considered": considered,
    "gazetteer": {
        "source": "O*NET 29.3 Technology Skills.txt (CC BY 4.0)",
        "raw_examples": len(examples),
        "strict_phrases": len(gaz),
        "rules": ">=2 tokens, no common-English token; 1 token only if in SINGLE_OK allowlist",
    },
    "jobs_with_ge1_skill": n_ge1,
    "pct_ge1": round(100.0 * n_ge1 / considered, 2),
    "pct_zero": round(100.0 * (considered - n_ge1) / considered, 2),
    "skills_per_job_mean": round(statistics.fmean(per_doc), 3),
    "skills_per_job_median": q(per_doc, 50),
    "skills_per_job_p90": q(per_doc, 90),
    "skills_per_job_max": per_doc[-1],
    "top25_matched": matched.most_common(25),
    "caveat": ("chi phu ky nang CONG NGHE/phan mem (O*NET Technology Skills); ky nang mem, "
               "chung chi, tay nghe KHONG duoc phu -> van la CAN DUOI. "
               "Ban truoc dung khop 1-token loose da bi nhieu (chu 'r' khop 267k tin) -> da sua."),
}
with open(OUT / "t4_cb_skills_onet_strict.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k != "top25_matched"}, indent=1, ensure_ascii=False))
print("top:", matched.most_common(15))
