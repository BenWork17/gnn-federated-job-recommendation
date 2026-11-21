# -*- coding: utf-8 -*-
"""t6 — SUA LOI TRON CAP SOC trong t5_graph_design.py / t5_esco_graph2.py.

LOI: nut Occupation dung ma DAY DU (11-1011.00) nhung canh skill tra bang ma GOC [:7].
     Khi cong don `sum(len(tech.get(s[:7]))) for s in p1_socs` qua nhieu ma day du
     cung mot nhom goc => DEM TRUNG, so canh bi phong dai.

Script nay tinh LAI ca hai cap MOT CACH NHAT QUAN, cho CA HAI dinh nghia P1
(goc theo Skills.txt va goc theo Technology Skills), de so sanh ro rang.

Chay: python _newdata_audit\\t6_fix_soc_levels.py
"""
import csv, json, os, re, sys, unicodedata, zipfile
from collections import defaultdict

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_newdata_audit", "t6_verify")
BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
ZIP = os.path.join(ROOT, "_newdata_audit", "t4_verify", "db_29_3_text.zip")

GENDER = re.compile(r"\((?:m|f|d|w|m/w/d|m/f/d|m/f|x|gn|all genders)\)", re.I)
REMOTE = re.compile(r"\((?:remote|hybrid|onsite|on-site)\)", re.I)
YEAR = re.compile(r"\b(19|20)\d{2}\b")
NONWORD = re.compile(r"[^a-z0-9+#. ]+")
WS = re.compile(r"\s+")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = GENDER.sub(" ", s)
    s = REMOTE.sub(" ", s)
    s = YEAR.sub(" ", s)
    s = s.replace("&", " and ")
    s = NONWORD.sub(" ", s)
    return WS.sub(" ", s).strip()


def loose(s):
    t = re.split(r"[-/|,]", s)[0].split()
    if len(t) > 2:
        t = t[:-1]
    return " ".join(t)


def zread(z, name):
    for n in z.namelist():
        if n.replace("\\", "/").endswith("/" + name):
            return z.read(n).decode("utf-8", "replace")
    raise FileNotFoundError(name)


def main():
    os.makedirs(OUT, exist_ok=True)
    z = zipfile.ZipFile(ZIP)

    # ---------- 1. title -> ma nghe DAY DU ----------
    title2soc = {}
    for line in list(csv.reader(zread(z, "Alternate Titles.txt").splitlines(), delimiter="\t"))[1:]:
        if len(line) > 3:
            for raw in (line[1], line[2]):
                t = norm(raw)
                if t:
                    title2soc.setdefault(t, line[0])
    for line in list(csv.reader(zread(z, "Occupation Data.txt").splitlines(), delimiter="\t"))[1:]:
        if len(line) > 1:
            t = norm(line[1])
            if t:
                title2soc.setdefault(t, line[0])
    title2soc_loose = {}
    for t, s in title2soc.items():
        title2soc_loose.setdefault(loose(t), s)

    # ---------- 2. hai lop skill, moi lop o CA HAI cap ----------
    # skills_per[level][code] = set(element)
    skills_per = {"full": defaultdict(set), "base": defaultdict(set)}
    tech_per = {"full": defaultdict(set), "base": defaultdict(set)}
    for line in list(csv.reader(zread(z, "Skills.txt").splitlines(), delimiter="\t"))[1:]:
        if len(line) > 2:
            for lv in ("full", "base"):
                skills_per[lv][line[0] if lv == "full" else line[0][:7]].add(line[2])
    for line in list(csv.reader(zread(z, "Technology Skills.txt").splitlines(), delimiter="\t"))[1:]:
        if len(line) > 1:
            for lv in ("full", "base"):
                tech_per[lv][line[0] if lv == "full" else line[0][:7]].add(line[1])

    # ---------- 3. job -> ma nghe ----------
    job2soc = {}
    with open(os.path.join(BASE, "jobs.tsv"), encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        h = next(rd)
        ij, it_ = h.index("JobID"), h.index("Title")
        for row in rd:
            if it_ < len(row):
                t = norm(row[it_])
                job2soc[row[ij]] = title2soc.get(t) or title2soc_loose.get(loose(t))

    # ---------- 4. doc apps mot lan, giu lai ----------
    apps = []
    with open(os.path.join(BASE, "apps.tsv"), encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        h = next(rd)
        iu, ij = h.index("UserID"), h.index("JobID")
        for row in rd:
            apps.append((row[iu], row[ij]))
    print("apps rows:", len(apps))

    # ---------- 5. hai dinh nghia P1 x 2 cap, TAT CA NHAT QUAN ----------
    result = {}
    # P1_skills: job co ma nghe VA nghe do co >=1 trong 35 element (giong t5_graph_design)
    # P1_tech  : job co ma nghe VA nghe do co >=1 technology skill (giong t5_esco_graph2)
    for p1name, table in (("P1_skills35", skills_per), ("P1_technologies", tech_per)):
        for lv in ("full", "base"):
            key = lambda s: s if lv == "full" else s[:7]
            tbl = table[lv]
            pairs = []
            for u, j in apps:
                soc = job2soc.get(j)
                if soc and tbl.get(key(soc)):
                    pairs.append((u, j, key(soc)))
            us = {u for u, _, _ in pairs}
            js = {j for _, j, _ in pairs}
            socs = {s for _, _, s in pairs}
            # NHAT QUAN: cong tren tap ma DA GOM, khong cong don qua ma chi tiet
            jse = sum(len(tbl[s]) for s in socs)
            skills_union = set()
            for s in socs:
                skills_union |= tbl[s]
            result[f"{p1name}__{lv}"] = {
                "edges_user_job": len(pairs),
                "nodes_user": len(us),
                "nodes_job": len(js),
                "nodes_occupation": len(socs),
                "edges_job_skill": jse,
                "distinct_skill_nodes": len(skills_union),
                "skills_per_job_mean": round(jse / len(socs), 2) if socs else None,
                "jobs_per_occupation": round(len(js) / len(socs), 1) if socs else None,
            }
            print(p1name, lv, result[f"{p1name}__{lv}"])

    # ---------- 6. tai hien dung con so SAI cua t5 (de doi chieu) ----------
    # t5 cong don `sum(len(t.get(s[:7]))) for s in p1_socs` voi p1_socs la ma DAY DU
    for p1name, table in (("P1_skills35", skills_per), ("P1_technologies", tech_per)):
        tbl = table["base"]
        pairs = []
        for u, j in apps:
            soc = job2soc.get(j)
            if soc and tbl.get(soc[:7]):
                pairs.append((u, j, soc))
        socs_full = {s for _, _, s in pairs}
        buggy = sum(len(tbl[s[:7]]) for s in socs_full)
        correct = sum(len(tbl[s]) for s in {s[:7] for s in socs_full})
        result[f"BUG_{p1name}"] = {
            "nodes_occupation_full_code": len(socs_full),
            "nodes_occupation_base_code": len({s[:7] for s in socs_full}),
            "edges_job_skill_t5_mixed": buggy,
            "edges_job_skill_correct_base": correct,
            "inflation_pct": round(100.0 * (buggy - correct) / correct, 1) if correct else None,
        }
        print("BUG", p1name, result[f"BUG_{p1name}"])

    with open(os.path.join(OUT, "t6_soc_fixed.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("\nwrote", os.path.join(OUT, "t6_soc_fixed.json"))


if __name__ == "__main__":
    main()
