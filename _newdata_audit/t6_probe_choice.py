import json
d = json.load(open(r"_newdata_audit\t6_verify\t6_canonical.json", encoding="utf-8"))
c = d["combos"]
print("=== NEU CHON CAP GOC + LOC BANG TECHNOLOGY (lop skill ma tai lieu khuyen nghi) ===")
x = c["P1_by_technology__base"]
for k in ("edges_user_job","nodes_user","nodes_job","nodes_occupation","nodes_skill_tech",
          "edges_job_skill_tech","edges_user_occupation","users_with_tech","pct_users_with_tech",
          "density_pct","jobs_per_occupation","tech_per_job_mean","pct_tech_vocab"):
    print("  %-24s %s" % (k, x[k]))
print()
print("=== NEU CHON CAP GOC + LOC BANG SKILLS35 (cot A cua captain) ===")
y = c["P1_by_skills35__base"]
for k in ("edges_user_job","nodes_user","nodes_job","nodes_occupation",
          "edges_job_skill_35","edges_user_occupation","users_with_skill35","pct_users_with_skill35"):
    print("  %-24s %s" % (k, y[k]))
print()
print("=== % job co >=1 ky nang (mau so 129.120) ===")
print(json.dumps(d["jobs_with_skill"], ensure_ascii=False, indent=1))
