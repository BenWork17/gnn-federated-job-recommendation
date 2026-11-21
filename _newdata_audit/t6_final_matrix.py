# -*- coding: utf-8 -*-
"""t6 — BANG SO CHUAN cho moi to hop (dinh nghia P1 x lop skill x cap ma SOC).

Muc dich: chot MOT bang so duy nhat, tat ca deu NHAT QUAN mot cap ma.
Dong thoi tai hien con so SAI cua t5 de doi chieu.

Boi canh: t5 co HAI script voi HAI dinh nghia P1 khac nhau:
  - t5_graph_design.py : P1 = job co ma nghe VA nghe co >=1 trong 35 Skills.txt
  - t5_esco_graph2.py  : P1 = job co ma nghe VA nghe co >=1 Technology Skill
Ca hai deu mac loi tron cap khi cong don canh skill.

Chay: python _newdata_audit\\t6_final_matrix.py
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

    title2soc = {}
    for r in list(csv.reader(zread(z, "Alternate Titles.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 3:
            for raw in (r[1], r[2]):
                t = norm(raw)
                if t:
                    title2soc.setdefault(t, r[0])
    for r in list(csv.reader(zread(z, "Occupation Data.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 1:
            t = norm(r[1])
            if t:
                title2soc.setdefault(t, r[0])
    t2s_loose = {}
    for t, s in title2soc.items():
        t2s_loose.setdefault(loose(t), s)

    skills = {"full": defaultdict(set), "base": defaultdict(set)}
    tech = {"full": defaultdict(set), "base": defaultdict(set)}
    for r in list(csv.reader(zread(z, "Skills.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 2:
            skills["full"][r[0]].add(r[2]); skills["base"][r[0][:7]].add(r[2])
    for r in list(csv.reader(zread(z, "Technology Skills.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 1:
            tech["full"][r[0]].add(r[1]); tech["base"][r[0][:7]].add(r[1])

    job2soc = {}
    with open(os.path.join(BASE, "jobs.tsv"), encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd)
        ij, it_ = h.index("JobID"), h.index("Title")
        for row in rd:
            if it_ < len(row):
                t = norm(row[it_])
                job2soc[row[ij]] = title2soc.get(t) or t2s_loose.get(loose(t))

    apps = []
    with open(os.path.join(BASE, "apps.tsv"), encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd)
        iu, ij = h.index("UserID"), h.index("JobID")
        for row in rd:
            apps.append((row[iu], row[ij]))
    print("apps:", len(apps))

    # user_history -> soc
    hist = defaultdict(list)
    with open(os.path.join(BASE, "user_history.tsv"), encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd)
        iu, ijt = h.index("UserID"), h.index("JobTitle")
        n_hist = 0
        for row in rd:
            n_hist += 1
            if len(row) > max(iu, ijt):
                hist[row[iu]].append(row[ijt])
    user2socs = {}
    hist_total = 0; hist_mapped = 0
    for u, titles in hist.items():
        socs = set()
        for raw in titles:
            hist_total += 1
            s = title2soc.get(norm(raw)) or t2s_loose.get(loose(norm(raw)))
            if s:
                hist_mapped += 1; socs.add(s)
        if socs:
            user2socs[u] = socs

    res = {"apps_rows": len(apps), "jobs_rows_mapped": len(job2soc),
           "user_history_rows": n_hist, "history_total": hist_total,
           "history_mapped": hist_mapped,
           "pct_history_mapped": round(100.0 * hist_mapped / hist_total, 2),
           "combos": {}}

    # 4 to hop: (dinh nghia P1) x (cap ma) — MOI THU deu dung cung mot cap
    for p1name in ("P1_by_skills35", "P1_by_technology"):
        filt = skills if p1name == "P1_by_skills35" else tech
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
            # canh skill cho CA HAI lop, cung cap ma
            s_edges = sum(len(skills[lv][s]) for s in socs)
            t_edges = sum(len(tech[lv][s]) for s in socs)
            s_nodes = set(); t_nodes = set()
            for s in socs:
                s_nodes |= skills[lv][s]; t_nodes |= tech[lv][s]
            # phia user, cung cap ma
            u_socs = {u: {key(s) for s in v} for u, v in user2socs.items()}
            u_soc_edges = sum(len(u_socs[u]) for u in us if u in u_socs)
            u_skill_edges = 0; u_with_skill = 0
            for u in us:
                if u in u_socs:
                    st = set()
                    for s in u_socs[u]:
                        st |= tech[lv][s]
                    if st:
                        u_with_skill += 1
                        u_skill_edges += len(st)
            res["combos"][f"{p1name}__{lv}"] = {
                "edges_user_job": len(pairs), "nodes_user": len(us),
                "nodes_job": len(js), "nodes_occupation": len(socs),
                "nodes_skill_35": len(s_nodes), "nodes_skill_tech": len(t_nodes),
                "edges_job_skill_35_mixed_OFF": s_edges,
                "edges_job_skill_tech_mixed_OFF": t_edges,
                "edges_user_occupation": u_soc_edges,
                "edges_user_skill": u_skill_edges,
                "p1_users_with_skill": u_with_skill,
                "pct_p1_users_with_skill": round(100.0 * u_with_skill / len(us), 2) if us else None,
                "jobs_per_occupation": round(len(js) / len(socs), 1) if socs else None,
                "skills_per_job_mean": round(s_edges / len(socs), 2) if socs else None,
            }
            print(p1name, lv, res["combos"][f"{p1name}__{lv}"])

    # tai hien loi t5: nut = ma DAY DU, tra skill = ma GOC
    res["t5_bug_repro"] = {}
    for p1name in ("P1_by_skills35", "P1_by_technology"):
        filt = skills if p1name == "P1_by_skills35" else tech
        ftbl = filt["base"]
        pairs = []
        for u, j in apps:
            s = job2soc.get(j)
            if s and ftbl.get(s[:7]):
                pairs.append((u, j, s))
        socs_full = {x[2] for x in pairs}
        buggy_s = sum(len(skills["base"][s[:7]]) for s in socs_full)
        buggy_t = sum(len(tech["base"][s[:7]]) for s in socs_full)
        corr_s = sum(len(skills["base"][s]) for s in {x[:7] for x in socs_full})
        corr_t = sum(len(tech["base"][s]) for s in {x[:7] for x in socs_full})
        res["t5_bug_repro"][p1name] = {
            "nodes_occupation_full": len(socs_full),
            "nodes_occupation_base": len({x[:7] for x in socs_full}),
            "job_skill35_t5_mixed": buggy_s, "job_skill35_correct": corr_s,
            "job_tech_t5_mixed": buggy_t, "job_tech_correct": corr_t,
            "tech_inflation_pct": round(100.0 * (buggy_t - corr_t) / corr_t, 1) if corr_t else None,
        }
        print("BUG", p1name, res["t5_bug_repro"][p1name])

    with open(os.path.join(OUT, "t6_final_matrix.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("\nwrote t6_final_matrix.json")


if __name__ == "__main__":
    main()
