"""t4: do Djinni (2 repo HF, MIT) — ban NHANH, chi doc cot can thiet.

Toi uu: doc theo batch, chi lay cac cot can, dung pyarrow.compute de tinh fill rate
thay vi vong lap Python tung o.

Do:
  jobs repo    : rows, Company Name fill + distinct, Primary Keyword distinct,
                 Published range, va % tin co >=1 ky nang trong Long Description
                 (gazetteer O*NET strict nhu ban CareerBuilder -> so sanh duoc)
  profiles repo: rows, CV fill, Experience Years fill, Primary Keyword distinct
"""
import csv
import json
import re
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit/t4_verify")
ZIP = OUT / "db_29_3_text.zip"

REPOS = {
    "jobs": ("lang-uk/recruitment-dataset-job-descriptions-english",
             "data/train-00000-of-00001.parquet", "Long Description"),
    "profiles": ("lang-uk/recruitment-dataset-candidate-profiles-english",
                 "data/train-00000-of-00001.parquet", "CV"),
}


def download(repo, path, dest):
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest.stat().st_size
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{path}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=900) as r, open(dest, "wb") as f:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            f.write(c)
    return dest.stat().st_size


# --- gazetteer strict (giong t4_cb_skills_onet_strict.py) ---
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
    if len(toks) == 1 and toks[0].lower() not in SINGLE_OK:
        continue
    if len(toks) > 1 and any(t.lower() in COMMON_EN for t in toks):
        continue
    gaz.append(e)
pat = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(g) for g in sorted(gaz, key=len, reverse=True)) + r")(?![A-Za-z0-9])", re.I)
print("gazetteer strict:", len(gaz))


def pct(a, b):
    return round(100.0 * a / b, 2) if b else None


res = {}
for kind, (repo, path, textcol) in REPOS.items():
    dest = OUT / f"{kind}.parquet"
    size = download(repo, path, dest)
    pf = pq.ParquetFile(dest)
    cols = pf.schema_arrow.names
    total = pf.metadata.num_rows
    print(f"{kind}: {size} B, rows={total}, cols={cols}")

    fill = {}
    distinct = {}
    for c in cols:
        col = pf.read(columns=[c])[c]
        n_rows_c = len(col)
        n_null = pc.sum(pc.cast(pc.is_null(col), "int64")).as_py() or 0
        if str(col.type) in ("string", "large_string"):
            n_empty = pc.sum(pc.cast(pc.equal(pc.fill_null(col, pa.scalar("")), ""), "int64")).as_py() or 0
            n_nonempty = n_rows_c - n_empty
        else:
            n_nonempty = n_rows_c - n_null
        fill[c] = int(n_nonempty)
        distinct[c] = len(pc.unique(col).to_pylist())
    print(kind, "fill:", {k: fill[k] for k in cols})
    print(kind, "distinct:", distinct)

    # quet van ban de dem % co >=1 ky nang (streaming theo batch, chi 1 cot)
    n_scanned = 0
    n_ge1 = 0
    per_doc = []
    matched = Counter()
    for batch in pf.iter_batches(batch_size=20000, columns=[textcol]):
        for t in batch.column(0).to_pylist():
            n_scanned += 1
            if not isinstance(t, str) or not t:
                per_doc.append(0)
                continue
            found = {m.group(1).lower() for m in pat.finditer(t)}
            per_doc.append(len(found))
            if found:
                n_ge1 += 1
                for g in found:
                    matched[g] += 1
        print(f"  {kind} scanned {n_scanned}/{total}", flush=True)

    per_doc.sort()

    def q(p):
        k = min(len(per_doc) - 1, max(0, int(round(p / 100.0 * (len(per_doc) - 1)))))
        return per_doc[k]

    dates = None
    if "Published" in cols:
        pv = pf.read(columns=["Published"])["Published"].to_pylist()
        ds = sorted(x for x in pv if isinstance(x, str) and x.strip())
        dates = (ds[0], ds[-1], len(ds)) if ds else None

    res[kind] = {
        "repo": repo,
        "parquet_bytes": size,
        "rows": total,
        "columns": cols,
        "fill_pct": {c: pct(fill[c], total) for c in cols},
        "distinct": distinct,
        "text_column": textcol,
        "pct_with_ge1_skill_strict": pct(n_ge1, n_scanned),
        "skills_per_doc_mean": round(sum(per_doc) / len(per_doc), 3),
        "skills_per_doc_median": q(50),
        "skills_per_doc_p90": q(90),
        "skills_per_doc_max": per_doc[-1],
        "pct_zero_skill": pct(sum(1 for x in per_doc if x == 0), len(per_doc)),
        "top15_matched": matched.most_common(15),
        "published_range": dates,
        "users_total": total if kind == "profiles" else None,
        "jobs_total": total if kind == "jobs" else None,
        "interactions_total": 0,
    }
    del pf

with open(OUT / "t4_djinni.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:6000])
