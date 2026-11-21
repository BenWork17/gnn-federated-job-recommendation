"""t2: tim mirror cua asaniczka 1.3M LinkedIn (cot job_skills) + do lai datastax."""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def get(u, timeout=90):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


print("== HF search: '1.3m', 'job_skills', 'asaniczka' ==")
for q in ["1.3m linkedin", "job_skills", "asaniczka", "linkedin skills 2024"]:
    try:
        j = get(f"https://huggingface.co/api/datasets?search={urllib.parse.quote(q)}&limit=25")
        print(f"-- {q!r}: {len(j)}")
        for d in j[:25]:
            print("    ", d.get("id"))
    except Exception as e:
        print(q, "ERR", e)

print()
print("== retry datastax rows ==")
for off in [0, 5000, 50000]:
    try:
        u = (f"https://datasets-server.huggingface.co/rows?dataset=datastax%2Flinkedin_job_listings"
             f"&config=default&split=train&offset={off}&length=100")
        d = get(u)
        rows = d["rows"]
        cols = ["job_id", "company_id", "skills_desc", "formatted_experience_level"]
        for c in cols:
            if c in rows[0]["row"]:
                vals = [r["row"].get(c) for r in rows]
                nn = [v for v in vals if v not in (None, "", "nan")]
                print(f"  off={off} {c}: {100*len(nn)/len(vals):.1f}% filled")
    except Exception as e:
        print("  off", off, "ERR", type(e).__name__, e)
