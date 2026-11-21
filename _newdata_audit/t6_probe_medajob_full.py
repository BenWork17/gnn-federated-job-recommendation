# -*- coding: utf-8 -*-
"""t6 — do doc lap nguon goc MEDAJob (Lab03) va artifacts da lam sach.

Muc dich: xac dinh CHINH XAC cai gi trong MEDAJob la tong hop va cai gi la that.
Chay: python _newdata_audit\\t6_probe_medajob_full.py
"""
import csv, re, json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = r"E:\2026\DUT\DSS\SauGK\Lab03"
OUT = os.path.join(ROOT, "_newdata_audit", "t6_verify")
TECH = re.compile(r"^Tech Company \d+$")


def rows(p):
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pct(a, b):
    return round(100.0 * a / b, 2)


def main():
    os.makedirs(OUT, exist_ok=True)
    J = rows(os.path.join(RAW, "job.csv"))
    U = rows(os.path.join(RAW, "users.csv"))
    P = rows(os.path.join(RAW, "user_profiles.csv"))
    R = rows(os.path.join(RAW, "ratings.csv"))
    CJ = rows(os.path.join(ROOT, "artifacts", "medajob", "jobs.csv"))
    CU = rows(os.path.join(ROOT, "artifacts", "medajob", "users.csv"))
    n = len(J)
    res = {"raw": {"jobs": n, "users": len(U), "profiles": len(P), "ratings": len(R)},
           "clean": {"jobs": len(CJ), "users": len(CU)}}

    # ---- A. dau hieu sinh tu dong trong job corpus ----
    tech = [r for r in J if TECH.match((r["company_name"] or "").strip())]
    ex = [r for r in J if "example.com" in ((r.get("hr_contact") or "")
                                            + (r.get("company_website") or "")
                                            + (r.get("link") or ""))]
    tksys = [r for r in J if "tkrecsys" in (r.get("link") or "")]
    numtitle = [r for r in J if re.search(r"\s\d{2}$", (r.get("job_title") or "").strip())]
    synth_idx = set()
    for i, r in enumerate(J):
        if (TECH.match((r["company_name"] or "").strip())
                or "example.com" in ((r.get("hr_contact") or "")
                                     + (r.get("company_website") or "")
                                     + (r.get("link") or ""))
                or re.search(r"\s\d{2}$", (r.get("job_title") or "").strip())):
            synth_idx.add(i)
    # tên công ty thật (có dấu tiếng Việt)
    vn = [r for r in J if re.search(r"[àáảãạăâđêôơư]", (r.get("company_name") or ""), re.I)]
    res["job_markers"] = {
        "rows": n,
        "tech_company_n_rows": len(tech),
        "tech_company_n_pct": pct(len(tech), n),
        "tech_company_n_distinct_names": len({r["company_name"].strip() for r in tech}),
        "example_com_rows": len(ex),
        "example_com_pct": pct(len(ex), n),
        "tkrecsys_rows": len(tksys),
        "title_ends_2digits": len(numtitle),
        "distinct_company_name_all": len({r["company_name"] for r in J}),
        "vietnamese_diacritic_rows": len(vn),
        "vietnamese_diacritic_pct": pct(len(vn), n),
        "vietnamese_distinct_companies": len({r["company_name"] for r in vn}),
        "rows_with_any_synthetic_marker": len(synth_idx),
        "rows_with_any_synthetic_marker_pct": pct(len(synth_idx), n),
        "rows_real_looking": n - len(synth_idx),
        "rows_real_looking_pct": pct(n - len(synth_idx), n),
    }

    # ---- B. chat luong mo ta ----
    empty = sum(1 for r in J if not (r.get("job_description") or "").strip())
    same = sum(1 for r in J if (r.get("job_description") or "").strip().lower()
               == (r.get("job_title") or "").strip().lower())
    longd = sum(1 for r in J if len((r.get("job_description") or "").strip()) > 80)
    res["description"] = {
        "empty": empty, "empty_pct": pct(empty, n),
        "same_as_title": same, "same_as_title_pct": pct(same, n),
        "length_gt_80": longd, "length_gt_80_pct": pct(longd, n),
        "distinct": len({(r.get("job_description") or "") for r in J}),
    }

    # ---- C. NGUON GOC TANG TUONG TAC (quan trong nhat) ----
    uix = {u["id"]: u for u in U}
    ru = [r["user_id"] for r in R]
    uru = set(ru)
    roles = collections.Counter(uix[x]["role"] for x in uru if x in uix)
    doms = collections.Counter((uix[x]["email"] or "").split("@")[-1] for x in uru if x in uix)
    rv = collections.Counter(r["rating"] for r in R)
    per_user = collections.Counter(ru)
    res["interaction_layer"] = {
        "rating_rows": len(R),
        "distinct_jobs_rated": len({r["job_id"] for r in R}),
        "distinct_users_in_ratings": len(uru),
        "rating_distribution": {k: v for k, v in sorted(rv.items())},
        "comments_nonempty": sum(1 for r in R if (r.get("comment") or "").strip()),
        "user_roles": dict(roles),
        "user_email_domains": dict(doms),
        "ratings_per_user_min": min(per_user.values()),
        "ratings_per_user_max": max(per_user.values()),
        "student_account_usernames_sample": [uix[x]["username"] for x in list(uru)[:5] if x in uix],
    }

    # ---- D. tang ho so ----
    res["profile_layer"] = {
        "rows": len(P),
        "distinct_title": len({r["title"] for r in P}),
        "cv_url_empty": sum(1 for r in P if not (r.get("cv_url") or "").strip()),
        "cv_url_empty_pct": pct(sum(1 for r in P if not (r.get("cv_url") or "").strip()), len(P)),
        "profile_vector_filled": sum(1 for r in P if (r.get("profile_vector") or "").strip()),
        "user_summary_empty": sum(1 for r in P if not (r.get("user_summary") or "").strip()),
        "user_summary_empty_pct": pct(sum(1 for r in P if not (r.get("user_summary") or "").strip()), len(P)),
        "profiles_by_role": dict(collections.Counter(
            uix[r["user_id"]]["role"] for r in P if r["user_id"] in uix)),
        "profiles_by_role_pct": {k: pct(v, len(P)) for k, v in collections.Counter(
            uix[r["user_id"]]["role"] for r in P if r["user_id"] in uix).items()},
    }

    # ---- D2. do phu tuong tac tren artifacts da lam sach ----
    import numpy as np
    g = np.load(os.path.join(ROOT, "artifacts", "medajob", "graph.npz"), allow_pickle=True)
    Rm = g["R"]
    users_with = int((Rm > 0).any(axis=1).sum())
    res["clean_interaction_coverage"] = {
        "users": int(Rm.shape[0]), "jobs": int(Rm.shape[1]),
        "nnz": int((Rm > 0).sum()),
        "users_with_ge1_interaction": users_with,
        "users_with_ge1_interaction_pct": pct(users_with, Rm.shape[0]),
        "users_zero_interaction": int(Rm.shape[0]) - users_with,
        "users_zero_interaction_pct": pct(int(Rm.shape[0]) - users_with, Rm.shape[0]),
        "test_users": int((g["test"] > 0).any(axis=1).sum()),
    }

    # ---- D3. do lech rating ----
    c = collections.Counter(int(r["rating"]) for r in R)
    res["rating_skew"] = {
        "ge4": c[4] + c[5], "ge4_pct": pct(c[4] + c[5], len(R)),
        "eq3": c[3], "eq3_pct": pct(c[3], len(R)),
        "le2": c[1] + c[2], "le2_pct": pct(c[1] + c[2], len(R)),
        "jobs_rated": len({r["job_id"] for r in R}),
        "jobs_total": len(J),
        "jobs_rated_pct": pct(len({r["job_id"] for r in R}), len(J)),
        "jobs_never_rated": len(J) - len({r["job_id"] for r in R}),
        "jobs_never_rated_pct": pct(len(J) - len({r["job_id"] for r in R}), len(J)),
    }

    # ---- E. artifacts da lam sach ----
    techc = [r for r in CJ if TECH.match((r["company_name"] or "").strip())]
    res["clean_artifacts"] = {
        "jobs": len(CJ), "distinct_company_name": len({r["company_name"] for r in CJ}),
        "tech_company_n_rows": len(techc),
        "tech_company_n_distinct": len({r["company_name"] for r in techc}),
        "skills_fill_pct": pct(sum(1 for r in CJ if (r.get("skills") or "").strip()), len(CJ)),
    }

    with open(os.path.join(OUT, "t6_medajob_provenance.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
