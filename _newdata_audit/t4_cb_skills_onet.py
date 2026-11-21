"""t4: do % tin CareerBuilder co >=1 KY NANG trich duoc, dung gazetteer THAT (O*NET Technology Skills).

Vi sao can ban do nay: ban 60-term (p9) la lexicon tu che -> khong bao quat.
O*NET 29.3 'Technology Skills.txt' co ~8.775 ten phan mem/cong nghe (CC BY 4.0),
download duoc khong can dang ky -> gazetteer tai lap duoc, lon hon nhieu.

Phuong phap:
  - tai db_29_3_text.zip (13 MB), doc 'Technology Skills.txt'
  - chuan hoa ten -> set n-gram (1..4 tu)
  - quet jobs.tsv (tab) theo TUNG DONG, tach text Description+Requirements,
    bo HTML, token hoa chu thuong, sinh n-gram 1..4 tu, tra set
  - dem % tin co >=1 khop; so ky nang/tin
Luu y: day van la CAN DUOI (chi phu ky nang CONG NGHE, khong phu ky nang mem).
"""
import csv
import io
import json
import re
import statistics
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit/t4_verify")
OUT.mkdir(parents=True, exist_ok=True)
ZIP = OUT / "db_29_3_text.zip"
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
SAMPLE_N = 300000

if not ZIP.exists() or ZIP.stat().st_size < 1_000_000:
    req = urllib.request.Request("https://www.onetcenter.org/dl_files/database/db_29_3_text.zip",
                                 headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r, open(ZIP, "wb") as f:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            f.write(c)
print("onet zip bytes:", ZIP.stat().st_size)

with zipfile.ZipFile(ZIP) as z:
    names = [n for n in z.namelist() if n.endswith("Technology Skills.txt")]
    print("tech file:", names)
    raw = z.read(names[0]).decode("utf-8", "replace")

rows = list(csv.reader(io.StringIO(raw), delimiter="\t"))
header = rows[0]
print("header:", header)
i_ex = header.index("Example")
i_hot = header.index("Hot Technology") if "Hot Technology" in header else None
examples = [r[i_ex] for r in rows[1:] if len(r) > i_ex and r[i_ex].strip()]

WORD = re.compile(r"[a-z0-9+#._]+")


def norm_tokens(s):
    return tuple(WORD.findall(s.lower().replace("'", "")))


gaz = Counter()
for e in examples:
    t = norm_tokens(e)
    if 1 <= len(t) <= 4:
        gaz[t] += 1
print("gazetteer phrases:", len(gaz), "distinct raw examples:", len(set(examples)))

TAG = re.compile(r"<[^>]{0,400}>")
ENT = re.compile(r"&[a-zA-Z]{2,8};|&#\d{2,5};")

n = 0
n_ge1 = 0
per_doc = []
matched_terms = Counter()
with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    h = next(rd)
    idesc, ireq = h.index("Description"), h.index("Requirements")
    for row in rd:
        if n >= SAMPLE_N:
            break
        n += 1
        if len(row) <= max(idesc, ireq):
            per_doc.append(0)
            continue
        text = ENT.sub(" ", TAG.sub(" ", row[idesc] + " " + row[ireq]))
        toks = WORD.findall(text.lower())
        found = set()
        L = len(toks)
        for i in range(L):
            for k in (1, 2, 3, 4):
                if i + k <= L:
                    g = tuple(toks[i:i + k])
                    if g in gaz:
                        found.add(g)
        per_doc.append(len(found))
        if found:
            n_ge1 += 1
            for g in found:
                matched_terms[g] += 1
        if n % 50000 == 0:
            print("...", n, "ge1:", n_ge1, flush=True)

per_doc.sort()


def q(v, p):
    k = min(len(v) - 1, max(0, int(round(p / 100.0 * (len(v) - 1)))))
    return v[k]


res = {
    "jobs_file": str(JOBS),
    "sample_rows": n,
    "sampling": f"first {SAMPLE_N} rows of jobs.tsv (streaming), not random",
    "gazetteer": {
        "source": "O*NET 29.3 Technology Skills.txt (CC BY 4.0)",
        "zip_bytes": ZIP.stat().st_size,
        "n_examples": len(examples),
        "n_phrases_1to4_tokens": len(gaz),
    },
    "jobs_with_ge1_skill": n_ge1,
    "pct_ge1": round(100.0 * n_ge1 / n, 2),
    "pct_zero": round(100.0 * (n - n_ge1) / n, 2),
    "skills_per_job_mean": round(statistics.fmean(per_doc), 3),
    "skills_per_job_median": q(per_doc, 50),
    "skills_per_job_p90": q(per_doc, 90),
    "skills_per_job_max": per_doc[-1],
    "top20_matched": [[" ".join(k), v] for k, v in matched_terms.most_common(20)],
    "caveat": "chi phu ky nang CONG NGHE (software/tools); ky nang mem/certificate KHONG duoc phu -> can duoi",
}
with open(OUT / "t4_cb_skills_onet.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:2500])
