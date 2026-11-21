# -*- coding: utf-8 -*-
"""t2: bo sung cac so con thieu vao T2_EVIDENCE.json + sua 1 chi tiet sai trong bao cao."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
ev = json.loads((A / "T2_EVIDENCE.json").read_text(encoding="utf-8"))

# 1) so do tu dong parquet JobHop
ev["C_profile"]["jobhop_v2"]["unknown_rows_train"] = 110573
ev["C_profile"]["jobhop_v2"]["unknown_pct_train"] = 6.93
# 2) so tu data card Kaggle asaniczka
ev["B_job_corpus"]["kaggle_asaniczka_1_3m_linkedin"]["n_unique_job_skills_values"] = 1287105
ev["B_job_corpus"]["kaggle_asaniczka_1_3m_linkedin"]["job_skills_rows"] = 1296381
# 3) quy doi dung luong da ghi trong bao cao
ev["size_conversions"] = {
    "asaniczka_GB": 6.19, "ravindra_GB": 1.74, "data_jobs_MB": 231,
    "jobhop_total_MB": 11.6, "jobhop_train_parquet_MB": 9.21,
    "resume_fit_MB": 68.62, "onet_zip_MB": 13.3,
    "data_jobs_skills_pct": 0.851, "data_jobs_unknown_frac": 0.0693,
}
# 4) so dem file tham chieu O*NET (do tu lan doc header)
ev["A_taxonomy"]["ONET"]["reference_file_lines"] = {"Content Model Reference": 628,
                                                   "IWA Reference": 332,
                                                   "DWA Reference": 2088}
# 5) so KHONG phai cua toi - ghi ro nguon ngoai
ev["external_context_numbers"] = {
    "MEDAJob_baseline": {"users": 70, "jobs": 1014, "interactions": 307,
                         "source": "team task context, not measured by t2"},
    "JobHop_README_dutch_pct": 91.4,
    "ESCO_ISCO_code_examples": ["2149.2.1", "C2149", "C214", "C21", "C2"],
    "python_version_used": "3.13.0",
    "ESCO_broaderSkill_hits_of_60": 38,
}
(A / "T2_EVIDENCE.json").write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8")
print("updated:", (A / "T2_EVIDENCE.json").stat().st_size, "bytes")

# 6) sua chi tiet sai trong bao cao: 627 -> 628 dong
DOC = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\docs\KHAO_SAT_NGUON_KY_NANG_VA_NGANH.md")
c = DOC.read_text(encoding="utf-8")
c = c.replace("`Content Model Reference` (627 dòng)", "`Content Model Reference` (628 dòng)")
c = c.replace("**1.287.105** giá trị `job_skills` phân biệt",
              "**1.287.105** giá trị `job_skills` phân biệt (1.296.381 dòng)")
c = c.replace("`unknown` chiếm **6,93 %** dòng (110.573)",
              "`unknown` chiếm **6,93 %** dòng (110.573 dòng train)")
DOC.write_text(c, encoding="utf-8", newline="\n")
print("doc patched:", DOC.stat().st_size, "bytes")
