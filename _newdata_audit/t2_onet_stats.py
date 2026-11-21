"""t2: do dac O*NET - so nghe, so ky nang, ma tran nghe-ky nang, quan he phan cap."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

B = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_data\onet\db_29_3_text")
OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")


def rows(name):
    p = B / name
    with p.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in r:
            yield row


res = {}

# --- occupations ---
occ = {}
for r in rows("Occupation Data.txt"):
    occ[r["O*NET-SOC Code"].strip()] = r["Title"].strip()
res["n_occupation_rows"] = len(occ)
res["n_occupation_codes_unique"] = len(occ)
res["n_soc_major_groups"] = len({c.split("-")[0] for c in occ})
res["n_soc_minor_groups"] = len({".".join(c.split("-")[0].split(".")[:2]) for c in occ})
# base SOC (6-digit) vs detailed
res["n_base_soc_6digit"] = len({c.split(".")[0] for c in occ})
res["sample_occupations"] = list(occ.items())[:3]

# --- skills (Skills.txt: Element Name = skill) ---
skills = defaultdict(set)   # onetsoc -> set(element name)
elem_ids = {}
scale_ids = Counter()
for r in rows("Skills.txt"):
    code = r["O*NET-SOC Code"].strip()
    en = r["Element Name"].strip()
    skills[code].add(en)
    elem_ids.setdefault(en, r["Element ID"].strip())
    scale_ids[r["Scale ID"].strip()] += 1
res["skills_unique_elements"] = len(elem_ids)
res["skills_rows"] = sum(scale_ids.values())
res["skills_scale_ids"] = dict(scale_ids)
res["skills_occupations_covered"] = len(skills)
res["skills_edges_occ_skill"] = sum(len(v) for v in skills.values())
res["skills_per_occ_mean"] = round(res["skills_edges_occ_skill"] / len(skills), 2)
res["skills_sample_elements"] = list(elem_ids)[:8]
# is there hierarchy in skills? Element ID like 2.A.1.a -> yes, O*NET content model hierarchy
res["skills_element_id_sample"] = {k: elem_ids[k] for k in list(elem_ids)[:6]}

# --- knowledge ---
kn = defaultdict(set)
for r in rows("Knowledge.txt"):
    kn[r["O*NET-SOC Code"].strip()].add(r["Element Name"].strip())
res["knowledge_unique_elements"] = len({e for s in kn.values() for e in s})
res["knowledge_edges"] = sum(len(v) for v in kn.values())

# --- technology skills (job-level explicit skill, near "job corpus with skills") ---
tech = defaultdict(set)
tech_rows = 0
hot = 0
for r in rows("Technology Skills.txt"):
    tech[r["O*NET-SOC Code"].strip()].add(r["Example"].strip())
    tech_rows += 1
    if r.get("Hot Technology", "").strip().upper() == "Y":
        hot += 1
res["techskills_rows"] = tech_rows
res["techskills_unique_examples"] = len({e for s in tech.values() for e in s})
res["techskills_occupations"] = len(tech)
res["techskills_edges"] = sum(len(v) for v in tech.values())
res["techskills_hot_rows"] = hot

# --- tools used ---
tools = defaultdict(set)
for r in rows("Tools Used.txt"):
    tools[r["O*NET-SOC Code"].strip()].add(r["Example"].strip())
res["tools_unique"] = len({e for s in tools.values() for e in s})
res["tools_edges"] = sum(len(v) for v in tools.values())

# --- abilities / work activities ---
for f, k in [("Abilities.txt", "abilities"), ("Work Activities.txt", "work_activities"),
             ("Work Styles.txt", "work_styles"), ("Interests.txt", "interests")]:
    d = defaultdict(set)
    for r in rows(f):
        d[r["O*NET-SOC Code"].strip()].add(r["Element Name"].strip())
    res[f"{k}_unique"] = len({e for s in d.values() for e in s})
    res[f"{k}_edges"] = sum(len(v) for v in d.values())

# --- alternate titles (job-title surface forms: useful for title matching) ---
alt = defaultdict(set)
for r in rows("Alternate Titles.txt"):
    alt[r["O*NET-SOC Code"].strip()].add(r["Alternate Title"].strip())
res["alt_titles_edges"] = sum(len(v) for v in alt.values())
res["alt_titles_occupations"] = len(alt)

# --- tasks ---
tasks = defaultdict(int)
for r in rows("Task Statements.txt"):
    tasks[r["O*NET-SOC Code"].strip()] += 1
res["task_statements"] = sum(tasks.values())

# --- education / etc ---
edu = defaultdict(set)
for r in rows("Education, Training, and Experience.txt"):
    edu[r["O*NET-SOC Code"].strip()].add((r["Element Name"].strip(), r["Category"].strip()))
res["edu_occupations"] = len(edu)

# --- check DWA / IWA reference files for skill hierarchy ---
extra = sorted(p.name for p in B.iterdir())
res["all_files"] = extra

# IWA / DWA if present
for f in ["Intermediate Work Activities.txt", "Detailed Work Activities.txt",
          "Work Context.txt", "Task Categories.txt", "Content Model Reference.txt"]:
    p = B / f
    res[f"exists_{f}"] = p.exists()

OUT.joinpath("t2_onet_stats.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(res, indent=2, ensure_ascii=False))
