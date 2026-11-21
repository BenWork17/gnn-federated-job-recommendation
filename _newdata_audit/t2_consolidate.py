# -*- coding: utf-8 -*-
"""t2: tong hop TOAN BO so do da kiem chung vao 1 file evidence duy nhat."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")


def rd(n, default=None):
    p = A / n
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


onet = rd("t2_onet_stats.json", {})
esco_mat = rd("t2_esco_matrix.json", {})
esco_sk = rd("t2_esco_skill_detail.json", {})
esco_cov = rd("t2_esco_coverage.json", {})
jobhop = rd("t2_c_stats.json", {})
rav = rd("t2_ravindra_fill.json", {})
arb = rd("t2_arbeitnow.json", {})
kcols = rd("t2_kaggle_columns.json", {})
src = rd("t2_sources_probe.json", {})

ev = {
    "measured_at": "2026-11-08 (Asia/Saigon)",
    "machine": {"drive": "E:", "note": "Python urllib works; PowerShell Invoke-WebRequest and curl.exe schannel are broken on this host"},
    "A_taxonomy": {
        "ESCO": {
            "version": "v1.2.1 (release 6.2.0, last update 2025-12-10)",
            "n_occupations_api_total": 2942,
            "n_skills_api_total": 13485,
            "n_languages": 28,
            "languages": "bg,es,cs,da,de,et,el,en,fr,ga,hr,it,lv,lt,hu,mt,nl,pl,pt,ro,sk,sl,fi,sv,is,no,ar,uk",
            "vietnamese_available": False,
            "vietnamese_evidence": "GET /resource/occupation?...&language=vi returned 28 preferredLabels, 'vi' not in preferredLabel nor alternativeLabel; same 28 with language=en/fr/de",
            "skill_hierarchy": {
                "broaderHierarchyConcept_present_pct": 100.0,
                "broaderSkill_pct": round(100 * 38 / 60, 1),
                "narrowerSkill_pct": round(100 * 10 / 60, 1),
                "sample_n": 60,
            },
            "skill_types_on_60_sample": esco_sk.get("skillType_distribution"),
            "skill_reuse_levels_on_60_sample": esco_sk.get("reuseLevel_distribution"),
            "skill_to_occupation_matrix": {
                "essential_skills_per_occupation": esco_mat.get("essential_skill_per_occ"),
                "optional_skills_per_occupation": esco_mat.get("optional_skill_per_occ"),
                "mean_edges_per_occupation": esco_mat.get("mean_edges_per_occ"),
                "estimated_total_edges": esco_mat.get("est_total_occ_skill_edges_for_2942"),
                "sample_n_occupations": esco_mat.get("n_sampled"),
            },
            "skill_coverage": esco_cov,
            "hierarchy_examples": esco_sk.get("hierarchy_examples"),
            "license": "Commission Decision 2011/833/EU - free download/reuse for any purpose, attribution statement mandatory",
            "license_quote": "In accordance with the Commission Decision of 12 December 2011 on the reuse of Commission documents (2011/833/EU), the ESCO classification can be downloaded, used, reproduced and reused for any purpose and by any interested party free of charge.",
            "offline": "CSV/ODS/RDF/TTL/XML/JSON-LD + downloadable Local API. Download form requires accepting privacy statement + entering an email to receive the link (no account).",
            "download_package_19_files": ["occupations", "skills", "skillGroups", "skillsHierarchy",
                                          "occupationSkillRelations", "skillSkillRelations",
                                          "broaderRelationsOccPillar", "broaderRelationsSkillPillar",
                                          "ISCOGroups", "digitalSkillsCollection", "greenSkillsCollection",
                                          "digCompSkillsCollection", "languageSkillsCollection",
                                          "transversalSkillsCollection", "researchSkillsCollection",
                                          "researchOccupationsCollection", "greenShareOcc",
                                          "conceptSchemes", "dictionary"],
            "isco_mapping": "each occupation maps to exactly one ISCO-08 code (e.g. calculation engineer = 2149.2.1)",
        },
        "ONET": {
            "version": "O*NET 29.3 text database (db_29_3_text.zip)",
            "zip_bytes": 13301357,
            "n_files_in_zip": 42,
            "n_occupations": onet.get("n_occupation_rows"),
            "n_base_soc_6digit": onet.get("n_base_soc_6digit"),
            "n_major_groups": onet.get("n_soc_major_groups"),
            "skills": {
                "unique_elements": onet.get("skills_unique_elements"),
                "basic_2A": 10,
                "cross_functional_2B": 25,
                "occupation_skill_edges": onet.get("skills_edges_occ_skill"),
                "occupations_covered": onet.get("skills_occupations_covered"),
                "mean_per_occupation": onet.get("skills_per_occ_mean"),
                "scale_ids": onet.get("skills_scale_ids"),
            },
            "knowledge": {"unique": onet.get("knowledge_unique_elements"), "edges": onet.get("knowledge_edges")},
            "technology_skills": {"unique_software": onet.get("techskills_unique_examples"),
                                  "edges": onet.get("techskills_edges"),
                                  "occupations": onet.get("techskills_occupations"),
                                  "hot_technology_rows": onet.get("techskills_hot_rows")},
            "tools_used": {"unique": onet.get("tools_unique"), "edges": onet.get("tools_edges")},
            "abilities_unique": onet.get("abilities_unique"),
            "work_activities_unique": onet.get("work_activities_unique"),
            "work_styles_unique": onet.get("work_styles_unique"),
            "alternate_titles_edges": onet.get("alt_titles_edges"),
            "task_statements": onet.get("task_statements"),
            "hierarchy": "Element ID is hierarchical (2.A.1.a). Content Model Reference + IWA Reference (332) + DWA Reference (2087)",
            "license": "CC BY 4.0 (O*NET 29.3 / 31.0 Database Content License) - attribution + trademark rules",
            "offline": "full text DB, no registration (optional developer registration)",
            "esco_crosswalk": "official ESCO-O*NET mapping table published on both portals",
        },
        "Lightcast": {"status": "not open", "evidence": "GitHub search 'lightcast open skills' / 'lightcast-io' found no skills dataset repo; API is contractual"},
        "LinkedIn_taxonomy": {"status": "not public", "evidence": "linkedin talent API reference pages 404; taxonomy only via Talent Solutions partner access"},
    },
    "B_job_corpus": {
        "kaggle_asaniczka_1_3m_linkedin": {
            "totalBytes": src.get("asaniczka_linkedin", {}).get("totalBytes"),
            "license": src.get("asaniczka_linkedin", {}).get("license"),
            "lastUpdated": src.get("asaniczka_linkedin", {}).get("lastUpdated"),
            "files": ["linkedin_job_postings.csv", "job_skills.csv"],
            "rows": {"linkedin_job_postings.csv": 1348454, "job_skills.csv": 1296381},
            "columns_job_skills": ["job_link", "job_skills"],
            "columns_job_postings": [f[0] for f in (kcols.get("linkedin_job_postings.csv", {}).get("fields") or [])],
            "field_descriptions": kcols.get("linkedin_job_postings.csv", {}).get("fields"),
            "got_summary_true_pct": 96,
            "n_unique_companies": 584544,
            "skills_origin": "NER over the job summary, free text, '.split(\", \")' to list - NOT taxonomy-coded",
            "noise_observed": "some rows contain 'I'm unable to extract the requested data...'; benefits leak into skills (Health Insurance, Dental Insurance, Vision Insurance)",
            "download_blocked": "6.19 GB > 500 MB cap; Kaggle API download endpoint returns 404 without an authenticated session, so only the data card was read",
        },
        "kaggle_ravindrasinghana_job_description": {
            "totalBytes": src.get("ravindra_jd", {}).get("totalBytes"),
            "license": src.get("ravindra_jd", {}).get("license"),
            "lastUpdated": src.get("ravindra_jd", {}).get("lastUpdated"),
            "n_rows": 1615940,
            "n_columns": 23,
            "columns": ["Job Id", "Experience", "Qualifications", "Salary Range", "location", "Country",
                        "latitude", "longitude", "Work Type", "Company Size", "Job Posting Date",
                        "Preference", "Contact Person", "Contact", "Job Title", "Role", "Job Portal",
                        "Job Description", "Benefits", "skills", "Responsibilities", "Company", "Company Profile"],
            "skills_fill_pct": 100.0,
            "verdict": "SYNTHETIC - do not use as real market data",
            "synthetic_evidence": {
                "company_size_unique_in_5551_rows": 5412,
                "qualifications_unique": 10,
                "job_portal_values": 4,
                "preference_values": ["Male", "Both", "Female"],
                "implausible_company_country": ["BT Group -> Gibraltar", "Truist Financial -> Maldives", "Prudential Financial -> San Marino", "UltraTech Cement -> Madagascar"],
                "salary_range_absurd": "181794758338.00 - 62170523408759.90",
                "job_description": "boilerplate template per Role",
            },
            "employer_id": "none (Company name string only, and synthetic)",
        },
        "adzuna": {
            "auth": "requires app_id + app_key (registration)",
            "no_key_status": 400,
            "fields": ["id", "title", "description", "created", "redirect_url", "company.display_name",
                       "category.label", "category.tag", "location.area[]", "location.display_name",
                       "salary_min", "salary_max", "salary_is_predicted", "contract_type", "contract_time",
                       "latitude", "longitude"],
            "skills_column": False,
            "employer_stable_id": False,
            "user_interactions": False,
            "results_per_page": 20,
            "tos": "adzuna.com/terms returned HTTP 403 to this host - licence terms not verified, must be read manually before use",
        },
        "usajobs": {
            "auth": "requires API key + registered email (401 without)",
            "fields": ["MatchedObjectId", "MatchedObjectDescriptor.PositionID", "PositionTitle",
                       "PositionURI", "OrganizationName", "DepartmentName", "JobCategory[].Name/Code",
                       "QualificationSummary", "PositionRemuneration", "PositionLocation",
                       "UserArea.Details.OfferingType"],
            "job_category_as_industry": True,
            "skills_column": False,
            "qualification_summary_is_free_text": True,
            "user_interactions": False,
            "license": "US federal job announcements are public domain, but the API has ToS + rate limiting",
        },
        "arbeitnow": {
            "auth": "none, no key, no registration",
            "schema_fields": ["slug", "company_name", "title", "description", "remote", "url", "tags",
                              "job_types", "location", "created_at"],
            "measured_one_sweep": {"pages": arb.get("pages"), "items": arb.get("n_items")},
            "rate_limit": "HTTP 429 from page 16 onward",
            "fill_pct": {k: (arb.get(k) or {}).get("fill_pct") for k in
                         ["slug", "company_name", "title", "description", "remote", "url", "tags", "location", "created_at"]},
            "distinct_tags": arb.get("distinct_tags"),
            "top_tags": arb.get("top_tags"),
            "distinct_companies": arb.get("distinct_companies"),
            "tags_are_skills": False,
            "market": "Germany",
            "user_interactions": False,
        },
    },
    "C_profile": {
        "jobhop_v2": {
            "hf_id": "aida-ugent/JobHop",
            "license": "cc-by-4.0",
            "languages": ["nl", "fr", "en"],
            "total_download_bytes": 11572872,
            "train_parquet_bytes": 9213302,
            "work_experience_entries": {"train": 1594827, "validation": 199587, "test": 198877,
                                        "total": 1993291},
            "released_trajectories": 355315,
            "actual_columns_v2_parquet": jobhop.get("jobhop", {}).get("columns"),
            "doc_vs_data_mismatch": "README documents person_id/esco_code/education_level for v2, but the shipped parquet columns are resume_id/matched_code/university_level (v1 naming)",
            "n_unique_resume_id_train": jobhop.get("jobhop", {}).get("n_unique_resume_id"),
            "n_unique_matched_code": jobhop.get("jobhop", {}).get("n_unique_matched_code"),
            "matched_code_null_frac": jobhop.get("jobhop", {}).get("matched_code_null_frac"),
            "education_level_counts_train": jobhop.get("jobhop", {}).get("university_level_counts"),
            "has_skills_per_person": False,
            "skills_disclaimer_quote": "it also extracts standardized job titles, free-text descriptions, company and institution names, technical skills, languages, certificates, contract type, and work-schedule type. Those fields are used internally to produce the ESCO codes and education levels; the public release contains only the structured fields listed in the table above.",
            "has_job_postings": False,
            "has_interactions": False,
            "has_employer": False,
            "registration": "none",
        },
        "resume_job_description_fit": {
            "hf_id": "cnamuangtoun/resume-job-description-fit",
            "license": "NONE DECLARED (cardData null, no license tag)",
            "train_rows": 6241,
            "test_rows": 1759,
            "total_rows": 8000,
            "download_bytes": 68616017,
            "columns": ["resume_text", "job_description_text", "label"],
            "label_counts_train": {"No Fit": 3143, "Potential Fit": 1556, "Good Fit": 1542},
            "label_counts_test": {"No Fit": 857, "Good Fit": 458, "Potential Fit": 444},
            "skills_column": False,
            "employer_id": False,
            "rating": False,
            "interaction_type": "explicit fit label, not a click/apply event",
            "measured_locally": True,
        },
    },
}

out = A / "T2_EVIDENCE.json"
out.write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8")
print("written", out, out.stat().st_size, "bytes")
print(json.dumps(ev["A_taxonomy"]["ONET"]["skills"], ensure_ascii=False))
print(json.dumps(ev["A_taxonomy"]["ESCO"]["skill_to_occupation_matrix"], ensure_ascii=False))
