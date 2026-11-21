# -*- coding: utf-8 -*-
"""t6 — SO CHUAN sau khi sua loi tron cap SOC. Mot lan chay, du moi so cho bao cao.

Boi canh: t5 co HAI script, HAI dinh nghia P1 khac nhau, va CA HAI deu mac loi tron cap:
  t5_graph_design.py : P1 = job co nghe VA nghe co >=1 trong 35 Skills.txt
  t5_esco_graph2.py  : P1 = job co nghe VA nghe co >=1 Technology Skill   <- thiet ke khuyen nghi

Loi: nut Occupation giu ma DAY DU (11-1011.00) nhung canh skill tra bang ma GOC [:7],
nen khi cong don qua nhieu ma day du cung nhom goc thi DEM TRUNG.

Script nay xuat CA HAI dinh nghia P1 x CA HAI cap ma, tat ca NHAT QUAN.
Chay: python _newdata_audit\\t6_canonical.py
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
    s = GENDER.sub(" ", s); s = REMOTE.sub(" ", s); s = YEAR.sub(" ", s)
    s = s.replace("&", " and "); s = NONWORD.sub(" ", s)
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

    # 1. title -> ma nghe DAY DU
    t2s = {}
    for r in list(csv.reader(zread(z, "Alternate Titles.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 3:
            for raw in (r[1], r[2]):
                t = norm(raw)
                if t:
                    t2s.setdefault(t, r[0])
    for r in list(csv.reader(zread(z, "Occupation Data.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 1:
            t = norm(r[1])
            if t:
                t2s.setdefault(t, r[0])
    t2s_loose = {}
    for t, s in t2s.items():
        t2s_loose.setdefault(loose(t), s)

    # 2. hai lop skill, hai cap
    skills = {"full": defaultdict(set), "base": defaultdict(set)}
    tech = {"full": defaultdict(set), "base": defaultdict(set)}
    for r in list(csv.reader(zread(z, "Skills.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 2:
            skills["full"][r[0]].add(r[2]); skills["base"][r[0][:7]].add(r[2])
    for r in list(csv.reader(zread(z, "Technology Skills.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 1:
            tech["full"][r[0]].add(r[1]); tech["base"][r[0][:7]].add(r[1])

    # 3. job -> soc (ma day du)
    job2soc = {}
    with open(os.path.join(BASE, "jobs.tsv"), encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd)
        ij, it_ = h.index("JobID"), h.index("Title")
        for row in rd:
            if it_ < len(row):
                t = norm(row[it_])
                job2soc[row[ij]] = t2s.get(t) or t2s_loose.get(loose(t))

    # 4. apps
    apps = []
    with open(os.path.join(BASE, "apps.tsv"), encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd)
        iu, ij = h.index("UserID"), h.index("JobID")
        for row in rd:
            apps.append((row[iu], row[ij]))

    # 5. user_history
    hist = defaultdict(list)
    with open(os.path.join(BASE, "user_history.tsv"), encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd)
        iu, ijt = h.index("UserID"), h.index("JobTitle")
        n_hist = 0
        for row in rd:
            n_hist += 1
            if len(row) > max(iu, ijt):
                hist[row[iu]].append(row[ijt])
    u2s = {}
    ht = hm = 0
    for u, titles in hist.items():
        s = set()
        for raw in titles:
            ht += 1
            x = t2s.get(norm(raw)) or t2s_loose.get(loose(norm(raw)))
            if x:
                hm += 1; s.add(x)
        if s:
            u2s[u] = s

    res = {
        "apps_rows": len(apps), "jobs_rows": len(job2soc),
        "jobs_mapped_with_app": len({j for u, j in apps if job2soc.get(j)}),
        "user_history_rows": n_hist, "history_total": ht, "history_mapped": hm,
        "pct_history_mapped": round(100.0 * hm / ht, 2),
        "occupations_full": len({s for s in job2soc.values() if s}),
        "occupations_base": len({s[:7] for s in job2soc.values() if s}),
        "combos": {},
    }

    for p1name, filt in (("P1_by_skills35", skills), ("P1_by_technology", tech)):
        for lv in ("full", "base"):
            key = (lambda s: s) if lv == "full" else (lambda s: s[:7])
            ftbl = filt[lv]
            pairs = []
            for u, j in apps:
                s = job2soc.get(j)
                if s and ftbl.get(key(s)):
                    pairs.append((u, j, key(s)))
            us = {x[0] for x in pairs}; js = {x[1] for x in pairs}
            socs = {x[2] for x in pairs}
            # SUA: MOI lop skill tinh tu bang CUA NO, khong lay filt cua P1
            # (ban truoc lay nham: P1_by_technology thi "job_skill_35" bi tinh bang tech)
            jse = sum(len(skills[lv][s]) for s in socs)
            te = sum(len(tech[lv][s]) for s in socs)
            sn = set(); tn = set()
            for s in socs:
                sn |= skills[lv][s]; tn |= tech[lv][s]
            # user side, cung cap
            uu = {u: {key(x) for x in v} for u, v in u2s.items()}
            u_occ = sum(len(uu[u]) for u in us if u in uu)
            u_with35 = u_withtech = 0
            u_sk35 = u_sktech = 0
            for u in us:
                if u in uu:
                    a = set(); b = set()
                    for s in uu[u]:
                        a |= skills[lv][s]; b |= tech[lv][s]
                    if a:
                        u_with35 += 1; u_sk35 += len(a)
                    if b:
                        u_withtech += 1; u_sktech += len(b)
            res["combos"][f"{p1name}__{lv}"] = {
                "edges_user_job": len(pairs),
                "pct_apps_mapped": round(100.0 * len(pairs) / len(apps), 3),
                "nodes_user": len(us), "nodes_job": len(js), "nodes_occupation": len(socs),
                "nodes_skill_35": len(sn), "nodes_skill_tech": len(tn),
                "edges_job_skill_35": jse, "edges_job_skill_tech": te,
                "edges_user_occupation": u_occ,
                "edges_user_skill_35": u_sk35, "edges_user_skill_tech": u_sktech,
                "users_with_skill35": u_with35,
                "pct_users_with_skill35": round(100.0 * u_with35 / len(us), 2) if us else None,
                "users_with_tech": u_withtech,
                "pct_users_with_tech": round(100.0 * u_withtech / len(us), 2) if us else None,
                "density_pct": round(100.0 * len(pairs) / (len(us) * len(js)), 6),
                "jobs_per_occupation": round(len(js) / len(socs), 1) if socs else None,
                "skills35_per_job_mean": round(jse / len(socs), 2) if socs else None,
                "tech_per_job_mean": round(te / len(socs), 2) if socs else None,
                "pct_tech_vocab": round(100.0 * len(tn) / 8775, 2),
            }
            print(p1name, lv, res["combos"][f"{p1name}__{lv}"])

    # 6. tai hien con so SAI cua t5 (de doi chieu, ghi vao bao cao)
    res["t5_bug"] = {}
    for p1name, filt in (("P1_by_skills35", skills), ("P1_by_technology", tech)):
        ftbl = filt["base"]
        pairs = []
        for u, j in apps:
            s = job2soc.get(j)
            if s and ftbl.get(s[:7]):
                pairs.append((u, j, s))
        sfull = {x[2] for x in pairs}
        sbase = {x[:7] for x in sfull}
        res["t5_bug"][p1name] = {
            "nodes_occupation_full_t5": len(sfull),
            "nodes_occupation_base_correct": len(sbase),
            "edges_job_skill35_t5_mixed": sum(len(skills["base"][s[:7]]) for s in sfull),
            "edges_job_skill35_correct": sum(len(skills["base"][s]) for s in sbase),
            "edges_job_tech_t5_mixed": sum(len(tech["base"][s[:7]]) for s in sfull),
            "edges_job_tech_correct": sum(len(tech["base"][s]) for s in sbase),
        }
        b = res["t5_bug"][p1name]
        b["tech_inflation_pct"] = round(
            100.0 * (b["edges_job_tech_t5_mixed"] - b["edges_job_tech_correct"])
            / b["edges_job_tech_correct"], 1)
        print("BUG", p1name, b)

    # 7. job co skill / tong job map duoc (cho bao cao)
    jm = {j for u, j in apps if job2soc.get(j)}
    res["jobs_with_skill"] = {}
    for lv in ("full", "base"):
        key = (lambda s: s) if lv == "full" else (lambda s: s[:7])
        with_t = sum(1 for j in jm if tech[lv].get(key(job2soc[j])))
        with_s = sum(1 for j in jm if skills[lv].get(key(job2soc[j])))
        res["jobs_with_skill"][lv] = {
            "jobs_mapped": len(jm),
            "jobs_with_tech_skill": with_t,
            "pct_jobs_with_tech": round(100.0 * with_t / len(jm), 2),
            "jobs_with_skill35": with_s,
            "pct_jobs_with_skill35": round(100.0 * with_s / len(jm), 2),
        }
        print("jobs", lv, res["jobs_with_skill"][lv])

    with open(os.path.join(OUT, "t6_canonical.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("\nwrote t6_canonical.json")


if __name__ == "__main__":
    main()
