# -*- coding: utf-8 -*-
"""t6 — kiem chung doc lap lop Skill cua O*NET 29.3 (Skills.txt vs Technology Skills.txt).

Muc dich: xac nhan phat hien cua t5 rang Skills.txt (35 element) VO DUNG lam node Skill,
va Technology Skills.txt thi DUNG DUOC. Chay lai:
    python _newdata_audit\\t6_verify_onet_skills.py
"""
import zipfile, io, csv, statistics, collections, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP = os.path.join(ROOT, "_newdata_audit", "t4_verify", "db_29_3_text.zip")
OUT = os.path.join(ROOT, "_newdata_audit", "t6_verify")


def find(z, name):
    for n in z.namelist():
        if n.replace("\\", "/").endswith("/" + name):
            return n
    raise FileNotFoundError(name)


def main():
    os.makedirs(OUT, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    res = {"zip_bytes": os.path.getsize(ZIP), "n_entries": len(z.namelist())}

    # ---------- 1. Skills.txt: 35 element ----------
    raw = z.read(find(z, "Skills.txt")).decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(raw), delimiter="\t"))
    occ = collections.defaultdict(set)
    for r in rows:
        occ[r["O*NET-SOC Code"]].add(r["Element ID"])
    cnt = sorted(len(v) for v in occ.values())
    elem_occ = collections.Counter()
    for v in occ.values():
        for e in v:
            elem_occ[e] += 1
    res["skills_txt"] = {
        "rows": len(rows),
        "occupations": len(occ),
        "distinct_elements": len(elem_occ),
        "skills_per_occ_min": cnt[0],
        "skills_per_occ_median": statistics.median(cnt),
        "skills_per_occ_max": cnt[-1],
        "occupations_with_all_elements": sum(1 for v in cnt if v == len(elem_occ)),
        "occupation_share_of_rarest_element_pct": round(
            100.0 * min(elem_occ.values()) / len(occ), 2),
    }

    # ---------- 2. Technology Skills.txt ----------
    raw2 = z.read(find(z, "Technology Skills.txt")).decode("utf-8", "replace")
    rows2 = list(csv.DictReader(io.StringIO(raw2), delimiter="\t"))
    occ2 = collections.defaultdict(set)
    for r in rows2:
        occ2[r["O*NET-SOC Code"]].add(r["Example"])
    c2 = sorted(len(v) for v in occ2.values())
    tool_occ = collections.Counter()
    for v in occ2.values():
        for t in v:
            tool_occ[t] += 1
    n_occ2 = len(occ2)
    n_tools = len(tool_occ)
    top = tool_occ.most_common(3)
    res["technology_skills_txt"] = {
        "rows": len(rows2),
        "occupations": n_occ2,
        "distinct_tools": n_tools,
        "tools_per_occ_min": c2[0],
        "tools_per_occ_median": statistics.median(c2),
        "tools_per_occ_mean": round(statistics.mean(c2), 2),
        "tools_per_occ_max": c2[-1],
        "occupations_with_all_tools": sum(1 for v in c2 if v == n_tools),
        "tools_covering_le_5pct_of_occ": sum(
            1 for t, k in tool_occ.items() if 100.0 * k / n_occ2 <= 5.0),
        "top3": [{"tool": t, "n_occ": k} for t, k in top],
    }

    with open(os.path.join(OUT, "t6_onet_skill_layers.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
