# -*- coding: utf-8 -*-
"""t6 — SO CHUAN CUOI CUNG cho Bang 6, voi NHAN CHINH XAC.

Phat hien khi sua: con so "47.567 canh Job-Skill" trong tai lieu cu thuc chat la
canh OCCUPATION-Skill (tong qua cac nghe), KHONG phai Job-Skill.
Script nay tach ro tung loai canh.

Cau hinh chon: CAP GOC [:7] + lop skill = O*NET Technology Skills
(vi tai lieu khuyen nghi Technology la lop skill dung, va P1 duoc loc
 "job co nghe ma nghe co >=1 technology skill").

Chay: python _newdata_audit\\t6_bang6.py
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

    # lop skill: Technology, cap ma GOC
    tech = defaultdict(set)
    tech_full = defaultdict(set)
    for r in list(csv.reader(zread(z, "Technology Skills.txt").splitlines(), delimiter="\t"))[1:]:
        if len(r) > 1:
            tech[r[0][:7]].add(r[1]); tech_full[r[0]].add(r[1])

    job2soc = {}
    with open(os.path.join(BASE, "jobs.tsv"), encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd)
        ij, it_ = h.index("JobID"), h.index("Title")
        for row in rd:
            if it_ < len(row):
                t = norm(row[it_])
                job2soc[row[ij]] = t2s.get(t) or t2s_loose.get(loose(t))

    apps = []
    with open(os.path.join(BASE, "apps.tsv"), encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t"); h = next(rd)
        iu, ij = h.index("UserID"), h.index("JobID")
        for row in rd:
            apps.append((row[iu], row[ij]))

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
                hm += 1; s.add(x[:7])
        if s:
            u2s[u] = s

    # ---- P1: job co nghe VA nghe co >=1 tech skill (cap GOC) ----
    pairs = []
    for u, j in apps:
        s = job2soc.get(j)
        if s and tech.get(s[:7]):
            pairs.append((u, j, s[:7]))
    us = {x[0] for x in pairs}
    js = {x[1] for x in pairs}
    socs = {x[2] for x in pairs}

    job_occ = len(js)                      # moi job map duoc dung 1 nghe
    occ_skill = sum(len(tech[s]) for s in socs)          # Occupation-Skill
    job_skill = sum(len(tech[job2soc[j][:7]]) for j in js)  # Job-Skill neu noi truc tiep

    u_occ = sum(len(u2s[u]) for u in us if u in u2s)
    u_skill = 0; u_with = 0
    for u in us:
        if u in u2s:
            st = set()
            for s in u2s[u]:
                st |= tech[s]
            if st:
                u_with += 1; u_skill += len(st)

    res = {
        "config": "cap ma GOC [:7] + O*NET Technology Skills",
        "nodes": {"user": len(us), "job": len(js), "occupation": len(socs),
                  "skill_tech": len(set().union(*[tech[s] for s in socs]))},
        "edges": {
            "user_job": len(pairs),
            "job_occupation": job_occ,
            "occupation_skill": occ_skill,
            "user_occupation": u_occ,
            "user_skill": u_skill,
            "job_skill_nếu_nối_trực_tiếp": job_skill,
        },
        "derived": {
            "density_pct": round(100.0 * len(pairs) / (len(us) * len(js)), 6),
            "pct_apps_mapped": round(100.0 * len(pairs) / len(apps), 3),
            "tech_per_occupation_mean": round(occ_skill / len(socs), 2),
            "tech_per_job_mean": round(job_skill / len(js), 2),
            "jobs_per_occupation": round(len(js) / len(socs), 1),
            "users_with_skill": u_with,
            "pct_users_with_skill": round(100.0 * u_with / len(us), 2),
            "pct_tech_vocab": round(100.0 * len(set().union(*[tech[s] for s in socs])) / 8775, 2),
            "all_p1_jobs_have_skill": job_occ == len(js),
        },
        "history": {"rows": n_hist, "users": len(hist), "titles_total": ht,
                    "titles_mapped": hm, "pct_mapped": round(100.0 * hm / ht, 2),
                    "users_with_occupation": len(u2s),
                    "pct_all_users_with_skill": round(
                        100.0 * sum(1 for v in u2s.values() if any(tech[s] for s in v)) / len(hist), 2)},
        "jobs_mapped_total": len({j for u, j in apps if job2soc.get(j)}),
    }
    res["derived"]["pct_jobs_mapped_with_tech_skill"] = round(
        100.0 * len(js) / res["jobs_mapped_total"], 2)

    with open(os.path.join(OUT, "t6_bang6.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
