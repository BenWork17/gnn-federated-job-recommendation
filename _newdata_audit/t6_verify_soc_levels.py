# -*- coding: utf-8 -*-
"""t6 — giai thich chenh lech so nghe giua hai lan do: CAP GOM MA SOC.

t6 bao 923 nghe / mean 35,41 / max 426 (ma DAY DU, co hau to .xx)
t5 bao 798 nghe / mean 37,93 / max 594 (ma GOC 6 ky tu, cat [:7])

Script nay chung minh co che: cat [:7] GOP nhieu nghe chi tiet vao mot nghe goc,
nen so nghe GIAM va so cong cu trung binh/toi da TANG (union lon hon).

Chay: python _newdata_audit\\t6_verify_soc_levels.py
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


def load(z, name):
    return list(csv.DictReader(
        io.StringIO(z.read(find(z, name)).decode("utf-8", "replace")), delimiter="\t"))


def stats(d):
    c = sorted(len(v) for v in d.values())
    return {"n": len(d), "min": c[0], "median": statistics.median(c),
            "mean": round(statistics.mean(c), 2), "max": c[-1]}


def main():
    os.makedirs(OUT, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    res = {}

    # ---- 1. moi ma O*NET co hau to .xx khong ----
    suf = {}
    for name in ["Occupation Data.txt", "Alternate Titles.txt",
                 "Skills.txt", "Technology Skills.txt"]:
        codes = {r["O*NET-SOC Code"] for r in load(z, name)}
        withsuf = {c for c in codes if "." in c}
        suf[name] = {"codes": len(codes), "with_suffix": len(withsuf),
                     "base_only": len(codes) - len(withsuf)}
    res["suffix_presence"] = suf

    # ---- 2. hai cap gop cho Technology Skills ----
    ts = load(z, "Technology Skills.txt")
    full, base = collections.defaultdict(set), collections.defaultdict(set)
    for r in ts:
        full[r["O*NET-SOC Code"]].add(r["Example"])
        base[r["O*NET-SOC Code"][:7]].add(r["Example"])
    res["technology_skills"] = {"by_full_code": stats(full), "by_base_code": stats(base)}

    # ---- 3. hai cap gop cho Skills.txt ----
    sk = load(z, "Skills.txt")
    fsk, bsk = collections.defaultdict(set), collections.defaultdict(set)
    for r in sk:
        fsk[r["O*NET-SOC Code"]].add(r["Element ID"])
        bsk[r["O*NET-SOC Code"][:7]].add(r["Element ID"])
    res["skills"] = {"by_full_code": stats(fsk), "by_base_code": stats(bsk)}
    res["skills"]["by_full_code"]["occupations_with_all_35"] = sum(
        1 for v in fsk.values() if len(v) == 35)
    res["skills"]["by_base_code"]["occupations_with_all_35"] = sum(
        1 for v in bsk.values() if len(v) == 35)

    # ---- 4. co che: gop lam giam so nhom, tang union ----
    multi = {k: v for k, v in base.items() if len({x["O*NET-SOC Code"] for x in ts})}
    grp = collections.defaultdict(set)
    for r in ts:
        grp[r["O*NET-SOC Code"][:7]].add(r["O*NET-SOC Code"])
    multi = {k: v for k, v in grp.items() if len(v) > 1}
    absorbed = sum(len(v) - 1 for v in multi.values())
    res["mechanism"] = {
        "base_groups": len(grp),
        "groups_with_more_than_one_detailed_code": len(multi),
        "pct_groups_multi": round(100.0 * len(multi) / len(grp), 2),
        "detailed_codes_absorbed": absorbed,
        "check_923_minus_absorbed": len(full) - absorbed,
    }

    # ví dụ cụ thể, kiểm chứng được
    ex = {}
    for k in list(multi)[:1]:
        per = collections.defaultdict(set)
        for r in ts:
            if r["O*NET-SOC Code"][:7] == k:
                per[r["O*NET-SOC Code"]].add(r["Example"])
        union = set().union(*per.values())
        ex = {"base_code": k,
              "detailed_codes": {c: len(v) for c, v in per.items()},
              "union": len(union)}
    res["example"] = ex

    # ---- 5. neu TRON hai cap (nut = ma day du, canh skill = ma goc) ----
    # Doi chieu: 923 nut hien thi tap skill lay tu nhom goc -> bao nhieu nut trung tap?
    sig = collections.Counter()
    for c in full:
        sig[tuple(sorted(base[c[:7]]))] += 1
    res["mixed_level_effect"] = {
        "n_nodes_full_code": len(full),
        "distinct_skill_sets_after_base_lookup": len(sig),
        "nodes_sharing_identical_skill_set_with_another": sum(
            v for v in sig.values() if v > 1),
        "note": "nut Occupation o cap ma day du nhung tra skill o cap ma goc "
                "=> 203 nut chia se y nguyen tap skill voi nut khac",
    }

    # doi chieu: neu dung NHAT QUAN cap ma day du thi tap skill phan biet = 923
    sig_full = collections.Counter()
    for c in full:
        sig_full[tuple(sorted(full[c]))] += 1
    res["consistent_full_level"] = {
        "n_nodes": len(full),
        "distinct_skill_sets": len(sig_full),
        "nodes_sharing_identical_skill_set": sum(v for v in sig_full.values() if v > 1),
    }

    with open(os.path.join(OUT, "t6_soc_levels.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
