"""t4: do % tin CareerBuilder trich duoc >=1 ky nang tu Description+Requirements.

Toan bo 1.092.096 tin trong jobs.tsv (3,4 GB), mot luot quet streaming bang csv.reader
(delimiter tab). Dung MOT regex hop nhat de nhanh.

Tu dien = 60 term pho bien (IT + y te + cong nghiep + van phong), cung lexicon voi
p9_skills.py de so sanh duoc. Day la CAN DUOI (lexicon nho), khong phai ESCO day du
-> bao cao ro day la uoc luong duoi.
"""
import csv
import json
import re
import statistics
from collections import Counter
from pathlib import Path

P = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\jobs.tsv")

LEX = {
    'python': r'\bpython\b', 'java': r'\bjava\b(?!script)', 'javascript': r'\bjavascript\b',
    'sql': r'\bsql\b', 'c#': r'\bc#', 'c++': r'\bc\+\+', '.net': r'\.net\b',
    'excel': r'\bms\s?excel\b|\bexcel\b', 'sap': r'\bsap\b', 'salesforce': r'\bsalesforce\b',
    'aws': r'\baws\b', 'azure': r'\bazure\b', 'linux': r'\blinux\b',
    'html': r'\bhtml\b', 'css': r'\bcss\b', 'react': r'\breact(js|\.js)?\b',
    'node.js': r'\bnode\.?js\b', 'oracle': r'\boracle\b', 'quickbooks': r'\bquickbooks\b',
    'crm': r'\bcrm\b', 'erp': r'\berp\b', 'sharepoint': r'\bsharepoint\b',
    'photoshop': r'\bphotoshop\b', 'autocad': r'\bautocad\b', 'solidworks': r'\bsolidworks\b',
    'nursing': r'\bnurs(e|ing)\b', 'phlebotomy': r'\bphlebotom', 'cpr': r'\bcpr\b',
    'bls': r'\bbls\b', 'emt': r'\bemt\b', 'ehr': r'\behr\b|\bemr\b',
    'welding': r'\bweld', 'hvac': r'\bhvac\b', 'cnc': r'\bcnc\b', 'forklift': r'\bforklift\b',
    'cdl': r'\bcdl\b', 'electrician': r'\belectrician\b', 'plumbing': r'\bplumb',
    'osha': r'\bosha\b', 'lean': r'\blean\b', 'six sigma': r'\bsix sigma\b',
    'bilingual': r'\bbilingual\b', 'spanish': r'\bspanish\b',
    'customer service': r'\bcustomer service\b', 'bookkeeping': r'\bbookkeep',
    'accounts payable': r'\baccounts payable\b', 'accounts receivable': r'\baccounts receivable\b',
    'payroll': r'\bpayroll\b', 'adp': r'\badp\b', 'medical billing': r'\bmedical billing\b',
    'icd': r'\bicd[- ]?(9|10)\b', 'cpt': r'\bcpt\b', 'hipaa': r'\bhipaa\b',
    'machine learning': r'\bmachine learning\b', 'data analysis': r'\bdata analy',
    'project management': r'\bproject management\b', 'pmp': r'\bpmp\b',
    'agile': r'\bagile\b', 'scrum': r'\bscrum\b', 'jira': r'\bjira\b',
    'wms': r'\bwms\b', 'tms': r'\btms\b', 'gis': r'\bgis\b', 'arcgis': r'\barcgis\b',
}
names = list(LEX)
COMBINED = re.compile("|".join(f"(?P<g{i}>{rx})" for i, rx in enumerate(LEX.values())), re.I)
TAG = re.compile(r"<[^>]{0,400}>")
ENT = re.compile(r"&[a-zA-Z]{2,8};|&#\d{2,5};")
WS = re.compile(r"\s+")

n = 0
n_ge1 = n_ge3 = n_ge5 = 0
dist = Counter()
vocab = Counter()
with open(P, encoding="utf-8", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    header = next(rd)
    print("header:", header)
    it, idesc, ireq = header.index("Title"), header.index("Description"), header.index("Requirements")
    for row in rd:
        n += 1
        if len(row) <= max(idesc, ireq):
            continue
        text = WS.sub(" ", ENT.sub(" ", TAG.sub(" ", row[idesc] + " " + row[ireq])))
        found = set()
        for m in COMBINED.finditer(text):
            found.add(m.lastgroup)
        k = len(found)
        dist[k] += 1
        if k >= 1:
            n_ge1 += 1
        if k >= 3:
            n_ge3 += 1
        if k >= 5:
            n_ge5 += 1
        for g in found:
            vocab[g] += 1
        if n % 200000 == 0:
            print("...", n, flush=True)


def pct(a, b):
    return round(100.0 * a / b, 2) if b else None


res = {
    "file": str(P),
    "jobs_total": n,
    "lexicon_terms": len(LEX),
    "jobs_with_ge1_skill": n_ge1,
    "pct_ge1": pct(n_ge1, n),
    "jobs_with_ge3_skill": n_ge3,
    "pct_ge3": pct(n_ge3, n),
    "jobs_with_ge5_skill": n_ge5,
    "pct_ge5": pct(n_ge5, n),
    "skills_per_job_mean": round(sum(k * v for k, v in dist.items()) / n, 3),
    "dist_fn": {str(k): v for k, v in sorted(dist.items())},
    "top20_terms": vocab.most_common(20),
    "caveat": "lexicon 60 term, khong phai ESCO day du -> day la CAN DUOI",
}
with open(r"_newdata_audit/t4_verify/t4_cb_skills.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
