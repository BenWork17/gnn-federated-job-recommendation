"""t4: gazetteer khop NHANH bang n-gram hash (thay regex 6110 alternatives).

Y tuong: token hoa van ban thanh chu thuong; sinh n-gram 1..4 tu; tim trong dict
  key = tuple token -> ten ky nang chuan.
Do phuc tap O(so token * 4), khong phu thuoc so luong mau.

Dung cho ca CareerBuilder va Djinni -> so sanh duoc cung mot thuoc do.
"""
import csv
import json
import re
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

OUT = Path(r"_newdata_audit/t4_verify")
ZIP = OUT / "db_29_3_text.zip"
JOBS = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")
CB_SAMPLE = OUT / "cb_skill_sample.tsv"

WORD = re.compile(r"[a-z0-9+#.]+")
COMMON_EN = set("""a an the and or of for with to in on at by from as is are be been being this that
these those it its all any both each few more most other some such no nor not only own same so than
too very can will just should now who whom which what when where why how i you he she we they them
his her their our your my me us do does did doing have has had having would could may might must
shall about above across after again against among around before below between during into through
under until up down out off over then once here there also within without per via using use used
users user work working works field fields report reports system systems software programs""".split())
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


def build_gazetteer():
    with zipfile.ZipFile(ZIP) as z:
        raw = z.read([n for n in z.namelist() if n.endswith("Technology Skills.txt")][0]).decode(
            "utf-8", "replace")
    rows = list(csv.reader(raw.splitlines(), delimiter="\t"))
    iex = rows[0].index("Example")
    examples = sorted({r[iex].strip() for r in rows[1:] if len(r) > iex and r[iex].strip()})
    g = {}
    for e in examples:
        toks = tuple(WORD.findall(e.lower()))
        if not (1 <= len(toks) <= 4):
            continue
        if len(toks) == 1 and toks[0] not in SINGLE_OK:
            continue
        if len(toks) > 1 and any(t in COMMON_EN for t in toks):
            continue
        g.setdefault(toks, e)
    return g, len(examples)


GAZ, n_examples = build_gazetteer()
maxlen = max(len(k) for k in GAZ)
print("gazetteer phrases:", len(GAZ), "from", n_examples, "examples; max tokens", maxlen)

TAG = re.compile(r"<[^>]{0,400}>")


def find_skills(text):
    toks = WORD.findall(TAG.sub(" ", text).lower())
    found = set()
    L = len(toks)
    for i in range(L):
        for k in range(1, maxlen + 1):
            if i + k <= L:
                hit = GAZ.get(tuple(toks[i:i + k]))
                if hit:
                    found.add(hit)
    return found


def measure_cb():
    n = 0
    n_ge1 = 0
    per_doc = []
    matched = Counter()
    STRIDE = 25
    with open(JOBS, encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        h = next(rd)
        idesc, ireq = h.index("Description"), h.index("Requirements")
        for i, row in enumerate(rd):
            n += 1
            if i % STRIDE:
                continue
            if len(row) <= max(idesc, ireq):
                per_doc.append(0)
                continue
            skills = find_skills(row[idesc] + " " + row[ireq])
            per_doc.append(len(skills))
            if skills:
                n_ge1 += 1
                for s in skills:
                    matched[s] += 1
            if len(per_doc) % 5000 == 0:
                print("  cb", len(per_doc), "ge1", n_ge1, flush=True)
    per_doc.sort()

    def q(p):
        k = min(len(per_doc) - 1, max(0, int(round(p / 100.0 * (len(per_doc) - 1)))))
        return per_doc[k]

    return {
        "rows_total": n,
        "stride": STRIDE,
        "sample_considered": len(per_doc),
        "jobs_with_ge1_skill": n_ge1,
        "pct_ge1": round(100.0 * n_ge1 / len(per_doc), 2),
        "pct_zero": round(100.0 * (len(per_doc) - n_ge1) / len(per_doc), 2),
        "skills_per_job_mean": round(sum(per_doc) / len(per_doc), 3),
        "median": q(50), "p90": q(90), "max": per_doc[-1],
        "top20": matched.most_common(20),
    }


res = {
    "gazetteer": {"source": "O*NET 29.3 Technology Skills.txt (CC BY 4.0)",
                  "raw_examples": n_examples, "strict_phrases": len(GAZ),
                  "rules": "1..4 tokens; 1-token chi khi nam trong allowlist cong nghe; "
                           "bo cum chua tu tieng Anh thong dung"},
    "careerbuilder": measure_cb(),
    "caveat": ("chi phu ky nang CONG NGHE/phan mem; khong phu ky nang mem, chung chi, tay nghe "
               "-> la CAN DUOI cua 'tin co >=1 ky nang'"),
}
with open(OUT / "t4_cb_skills_strict.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k != "careerbuilder"}, indent=1, ensure_ascii=False))
print(json.dumps(res["careerbuilder"], indent=1, ensure_ascii=False))
