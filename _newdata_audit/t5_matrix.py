"""t5: tong hop BANG QUYET DINH — doc lai TAT CA so tu file JSON, khong go tay.

Muc dich: bao dam moi con so trong bao cao deu truy nguoc duoc ve 1 file bang chung.
Sinh ra t5_matrix.json + in bang so sanh.
"""
import json
from pathlib import Path

T4 = Path(r"_newdata_audit/t4_verify")
T5 = Path(r"_newdata_audit/t5_verify")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


g = load(T5 / "t5_graph_design.json")
g2 = load(T5 / "t5_esco_and_graph2.json")
disc = load(T5 / "t5_skill_discriminative.json")
syn = load(T5 / "t5_synthetic_check.json")
t4pipe = load(T4 / "t4_pipeline_option1.json")
t4join = load(T4 / "t4_join_rates.json")
t4sem = load(T4 / "t4_join_semantic.json")
t4emp = load(T4 / "t4_employer_ambiguity.json")
t4onet = load(T4 / "t4_onet_occupation_coverage.json")
t4cb = load(T4 / "t4_careerbuilder_dist.json")
t4lb = load(T4 / "t4_lukebarousse.json")
timing = load(T5 / "t5_olx_and_timing.json")

m = {}

# ---------- CareerBuilder ----------
cb = t4cb
m["careerbuilder"] = {
    "users": cb["distinct_users"],
    "jobs": cb["distinct_jobs"],
    "interactions": cb["rows"],
    "density_pct": cb["density_pct_active"],
    "apps_per_user_median": cb["apps_per_user"]["median"],
    "apps_per_user_p90": cb["apps_per_user"]["p90"],
    "apps_per_user_max": cb["apps_per_user"]["max"],
    "users_ge5": cb["apps_per_user"]["n_ge5"],
    "users_ge5_pct": cb["apps_per_user"]["pct_ge5"],
    "jobs_single_app_pct": cb["apps_per_job"]["pct_eq1"],
    "license": "CAM — chi dung trong cuoc thi, phai huy du lieu sau khi ket thuc",
}

# ---------- P1 pipeline ----------
p1 = t4pipe["pipeline_option1"]["P1"]
m["P1_geography_clients"] = {
    "interactions": p1["interactions"],
    "users": p1["users"],
    "jobs": p1["jobs"],
    "density_pct": p1["density_pct"],
    "jobs_with_ge1_skill": p1["jobs_with_ge1_skill"],
    "pct_jobs_with_skill": p1["pct_jobs_with_skill"],
    "clients": p1["clients"],
    "client_min": p1["client_min"],
    "client_median": p1["client_median"],
    "client_max": p1["client_max"],
    "max_min_ratio": round(p1["client_max"] / p1["client_min"], 2),
}

# ---------- O*NET occupation-level ----------
m["onet_occupation_level"] = {
    "pct_jobs_mapped": t4onet["pct_jobs_mapped"],
    "pct_apps_mapped": t4onet["pct_apps_mapped"],
    "pct_apps_with_onet_skill": t4onet["pct_apps_with_onet_skill"],
    "pct_apps_with_onet_tech": t4onet["pct_apps_with_onet_tech"],
}

# ---------- join rates ----------
m["join_data_jobs"] = {
    "exact_pct_apps": t4join["join_levels"]["dj_exact"]["pct_apps"],
    "loose_pct_apps": t4join["join_levels"]["dj_loose"]["pct_apps"],
    "short_pct_apps": t4join["join_levels"]["dj_short"]["pct_apps"],
    "any_pct_apps": t4join["cumulative"]["data_jobs_any"]["pct_apps"],
    "semantically_valid_pct_apps": t4sem["data_jobs_join"]["pct"],
    "nonsense_share_of_matches_pct": t4sem["data_jobs_join"]["share_of_matches_that_are_nondata_pct"],
}
m["join_arshkon"] = {
    "exact_pct_apps": t4join["join_levels"]["ar_exact"]["pct_apps"],
    "any_pct_apps": t4join["cumulative"]["arshkon_any"]["pct_apps"],
    "employer_unique_pct": t4emp["employer_attribution"]["pct_unique"],
    "employer_multi_pct": t4emp["employer_attribution"]["pct_multi"],
    "employer_unmatched_pct": t4emp["employer_attribution"]["pct_unmatched"],
    "median_companies_per_title": t4emp["employer_attribution"]["median_companies_per_multi_title"],
    "max_companies_per_title": t4emp["employer_attribution"]["max_companies_per_title"],
    "skills_desc_fill_pct": t4emp["arshkon_skills_desc_fill_pct"],
}

# ---------- skill discrimination (PHAT HIEN cua t5) ----------
m["skill_discrimination"] = {
    "onet_skills_per_occupation_min": disc["onet_skills_discriminative"]["skills_per_occupation"]["min"],
    "onet_skills_per_occupation_max": disc["onet_skills_discriminative"]["skills_per_occupation"]["max"],
    "onet_pct_occupations_with_all_35": disc["onet_skills_discriminative"]["pct_occupations_with_all_skills"],
    "onet_verdict": disc["onet_skills_discriminative"]["verdict"],
    "onet_tech_per_occupation_mean": disc["onet_tech_discriminative"]["tech_per_occupation"]["mean"],
    "onet_tech_distinct": disc["onet_tech_discriminative"]["n_distinct_tech"],
    "esco_essential_mean": g2["esco"]["detail"]["essential_mean"],
    "esco_optional_mean": g2["esco"]["detail"]["optional_mean"],
    "esco_edges_per_occupation": g2["esco"]["detail"]["edges_per_occ_mean"],
    "esco_essential_min": g2["esco"]["detail"]["essential_min"],
    "esco_essential_max": g2["esco"]["detail"]["essential_max"],
    "esco_n_sampled": g2["esco"]["detail"]["n"],
}

# ---------- graph with tech skills ----------
m["graph_final"] = g2["graph_with_technology_skills"]

# ---------- user-side ----------
m["user_side"] = g["user_side_skills"]

# ---------- data_jobs ----------
m["data_jobs"] = {
    "rows": t4lb["rows_total"],
    "users": t4lb["users_total"],
    "interactions": t4lb["interactions_total"],
    "job_skills_fill_pct": t4lb["skills"]["job_skills_fill_pct"],
    "distinct_skills": t4lb["skills"]["distinct_skills"],
    "companies": t4lb["company_name_distinct"],
    "jobs_per_company_median": t4lb["jobs_per_company"]["median"],
    "jobs_per_company_p90": t4lb["jobs_per_company"]["p90"],
    "license": "Apache-2.0 (SACH)",
}

# ---------- synthetic ----------
m["synthetic_group"] = {
    "n_repos": len(syn["repos"]),
    "all_tables_byte_identical": all(v["all_identical"] for v in syn["identical_files"].values()),
    "tables_checked": list(syn["identical_files"]),
    "row_counts": syn["row_counts"][list(syn["row_counts"])[0]],
    "score_min": syn.get("score_stats", {}).get("min"),
    "score_max": syn.get("score_stats", {}).get("max"),
    "score_distinct": syn.get("score_stats", {}).get("distinct"),
    "license": "cc-by-nc-4.0",
    "verdict": "LOAI — du lieu tong hop",
}

# ---------- timing ----------
m["cost"] = {
    "apps_tsv_sec": timing["timings"]["apps_tsv_full_sec"],
    "jobs_tsv_full_sec": timing["timings"]["jobs_tsv_estimated_full_sec"],
    "jobs_tsv_full_min": timing["timings"]["jobs_tsv_estimated_full_min"],
}

with open(T5 / "t5_matrix.json", "w", encoding="utf-8") as f:
    json.dump(m, f, indent=1, ensure_ascii=False)

print(json.dumps(m, indent=1, ensure_ascii=False))
