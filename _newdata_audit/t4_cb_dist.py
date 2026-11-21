"""t4: do phan bo tuong tac CareerBuilder (apps.tsv) — BO SUNG cho moc da co.

Muc da biet (KHONG do lai, chi doi chieu): 1.603.111 app / 321.235 user / 365.668 job,
mat do 0,001365%. Task t4 can them: median / p90 / max per user va per job,
so user co >=5 tuong tac, % job chi co 1 tuong tac.
"""
import csv
import json
from collections import Counter
from pathlib import Path

P = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData\apps.tsv")


def q(sorted_vals, p):
    if not sorted_vals:
        return None
    k = min(len(sorted_vals) - 1, max(0, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


users = Counter()
jobs = Counter()
n = 0
splits = Counter()
with open(P, encoding="utf-8", newline="") as f:
    rd = csv.reader(f, delimiter="\t")
    header = next(rd)
    print("header:", header)
    iu, ij, isp = header.index("UserID"), header.index("JobID"), header.index("Split")
    for row in rd:
        n += 1
        users[row[iu]] += 1
        jobs[row[ij]] += 1
        splits[row[isp]] += 1

uc = sorted(users.values())
jc = sorted(jobs.values())
res = {
    "file": str(P),
    "rows": n,
    "distinct_users": len(users),
    "distinct_jobs": len(jobs),
    "splits": dict(splits),
    "density_pct_active": round(100.0 * n / (len(users) * len(jobs)), 6),
    "apps_per_user": {
        "min": uc[0], "median": q(uc, 50), "p90": q(uc, 90), "p99": q(uc, 99), "max": uc[-1],
        "mean": round(n / len(users), 4),
        "n_ge5": sum(1 for x in uc if x >= 5),
        "n_ge10": sum(1 for x in uc if x >= 10),
        "pct_ge5": round(100.0 * sum(1 for x in uc if x >= 5) / len(uc), 2),
        "pct_ge10": round(100.0 * sum(1 for x in uc if x >= 10) / len(uc), 2),
        "apps_held_by_users_ge5": sum(x for x in uc if x >= 5),
    },
    "apps_per_job": {
        "min": jc[0], "median": q(jc, 50), "p90": q(jc, 90), "p99": q(jc, 99), "max": jc[-1],
        "mean": round(n / len(jobs), 4),
        "n_eq1": sum(1 for x in jc if x == 1),
        "pct_eq1": round(100.0 * sum(1 for x in jc if x == 1) / len(jc), 2),
        "n_ge5": sum(1 for x in jc if x >= 5),
        "n_ge10": sum(1 for x in jc if x >= 10),
        "pct_ge10": round(100.0 * sum(1 for x in jc if x >= 10) / len(jc), 2),
    },
}
with open(r"_newdata_audit/t4_verify/t4_careerbuilder_dist.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
