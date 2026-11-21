"""t5 supplement: clean test set (no u->occ->j detour) + client silo viability.

Outputs:
  _newdata_audit/v3_verify/test_clean_index.npz  is_clean bool[37957] (order = test edges as
                                                 they appear in edge_index) + edge_pos int64
  _newdata_audit/v3_verify/t5_supplement.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi")
ART = ROOT / "artifacts" / "v3"
OUT = ROOT / "_newdata_audit" / "v3_verify"
OUT.mkdir(parents=True, exist_ok=True)

z = np.load(ART / "graph.npz", allow_pickle=True)
src, dst, et = z["edge_index"][0], z["edge_index"][1], z["edge_type"]
te, tr = z["test_mask"], z["train_mask"]
n_users, n_jobs = int(z["n_users"]), int(z["n_jobs"])
n_occ = int(z["n_occupations"])
off = z["offsets"].tolist()
occ_start = off[2]
cou, coj = z["client_of_user"], z["client_of_job"]
users_ids = z["user_ids"]
jobs_ids = z["job_ids"]
uj = et == 0
test_uj = np.where(te & uj)[0]

# ---- detour u-occ-j: user's occupation set (u-occ edges) ∩ job's occupation (job-occ edge)
uo = et == 3
jo = et == 1
user_occ: dict[int, set] = {}
for u, o in zip(src[uo].tolist(), dst[uo].tolist()):
    user_occ.setdefault(int(u), set()).add(int(o))
job_occ = {int(j): int(o) for j, o in zip(src[jo].tolist(), dst[jo].tolist())}

detour = np.zeros(len(test_uj), dtype=bool)
for k, e in enumerate(test_uj.tolist()):
    u, j = int(src[e]), int(dst[e])
    o = job_occ.get(j)
    if o is not None and o in user_occ.get(u, ()):
        detour[k] = True
is_clean = ~detour

# eligible set: users with >= min_apps_for_test (5) applications — the population the
# official split actually samples from
_deg = np.bincount(src[uj].astype(np.int64), minlength=int(z["n_nodes"])) + \
       np.bincount(dst[uj].astype(np.int64), minlength=int(z["n_nodes"]))
elig = _deg[:n_users] >= 5
elig_edges = int(elig[src[uj]].sum())

# ---- user-level classification (users are ALWAYS the src of user-job edges)
clean_users = set(src[test_uj[is_clean]].tolist())
all_test_users = set(src[test_uj].tolist())
leaky_users = all_test_users - clean_users
clean_jobs = set((dst[test_uj[is_clean]] - n_users).tolist())
all_test_jobs = set((dst[test_uj] - n_users).tolist())
leaky_jobs = all_test_jobs - clean_jobs

# per-user: does the user have ANY clean test edge left?
user_clean_edges = {}
for k, e in enumerate(test_uj.tolist()):
    u = int(src[e])
    user_clean_edges.setdefault(u, [0, 0])
    user_clean_edges[u][0 if is_clean[k] else 1] += 1
users_all_edges_dirty = sum(1 for v in user_clean_edges.values() if v[0] == 0)

# =============================== client silo ===============================
clients = json.loads((ART / "clients.json").read_text(encoding="utf-8"))
n_clients = len(clients)

# jobs per client straight from graph
jobs_per_client = np.bincount(coj.astype(np.int64), minlength=n_clients)
# users per client straight from user-job edges (a user "belongs" to a client it applied to)
u_arr = src[uj].astype(np.int64)
c_arr = coj[(dst[uj] - n_users)].astype(np.int64)
pair = np.unique(u_arr * n_clients + c_arr)
users_per_client = np.bincount(pair % n_clients, minlength=n_clients)
train_u = src[tr & uj].astype(np.int64)
train_c = coj[(dst[tr & uj] - n_users)].astype(np.int64)
train_edges_per_client = np.bincount(train_c, minlength=n_clients)
test_edges_per_client = np.bincount(c_arr, minlength=n_clients) - train_edges_per_client
# clean test edges per client (drop detour edges)
clean_pos = test_uj[is_clean]
clean_c = coj[(dst[clean_pos] - n_users)].astype(np.int64)
clean_test_per_client = np.bincount(clean_c, minlength=n_clients)

zero_jobs = np.where(jobs_per_client == 0)[0]
zero_users = np.where(users_per_client == 0)[0]
zero_train = np.where(train_edges_per_client == 0)[0]

rep = {
    "task": "t5 supplement",
    "clean_test": {
        "n_test_user_job_edges": int(len(test_uj)),
        "n_detour_edges_removed": int(detour.sum()),
        "n_clean_edges": int(is_clean.sum()),
        "pct_clean": round(100 * float(is_clean.mean()), 2),
        "n_users_all_test_edges": len(all_test_users),
        "n_users_remaining_clean": len(clean_users),
        "n_users_losing_all_test_edges": len(leaky_users),
        "n_jobs_all_test_edges": len(all_test_jobs),
        "n_jobs_remaining_clean": len(clean_jobs),
        "n_jobs_losing_all_test_edges": len(leaky_jobs),
        "n_users_with_only_dirty_test_edges": users_all_edges_dirty,
        "n_clean_test_edges_on_clean_users": int(
            sum(1 for k, e in enumerate(test_uj.tolist())
                if is_clean[k] and int(src[e]) in clean_users)),
        "pct_clean_of_all_user_job_edges": round(100 * int(is_clean.sum()) / int(uj.sum()), 3),
        "pct_all_test_of_all_user_job_edges": round(100 * len(test_uj) / int(uj.sum()), 3),
        "pct_clean_of_eligible_user_job_edges": round(100 * int(is_clean.sum()) / elig_edges, 3),
        "pct_all_test_of_eligible_user_job_edges": round(100 * len(test_uj) / elig_edges, 3),
        "n_eligible_users_min_apps_5": int(elig.sum()),
        "n_eligible_user_job_edges": elig_edges,
        "mask_order": "true order of test edges as they appear in edge_index "
                      "(edge_pos = np.where(test_mask & edge_type==0)[0])",
        "npz_arrays": {
            "is_clean": "bool[37957] - True = cạnh test KHÔNG có đường vòng u-occ-j",
            "detour_flag": "bool[37957] - đảo của is_clean, để đọc trực tiếp",
            "edge_pos": "int64[37957] - vị trí cột trong edge_index",
            "user": "int64[37957] - chỉ số nút user (0..171806)",
            "job": "int64[37957] - chỉ số job trong khối job (0..84844), +171807 để ra node idx",
        },
    },
    "clients": {
        "n_clients": n_clients,
        "n_clients_zero_jobs": int(len(zero_jobs)),
        "n_clients_zero_users": int(len(zero_users)),
        "n_clients_zero_train_edges": int(len(zero_train)),
        "n_clients_zero_test_edges": int((test_edges_per_client == 0).sum()),
        "n_clients_zero_clean_test_edges": int((clean_test_per_client == 0).sum()),
        "jobs_per_client": {"min": int(jobs_per_client.min()), "p25": int(np.percentile(jobs_per_client, 25)),
                            "median": float(np.median(jobs_per_client)), "p75": int(np.percentile(jobs_per_client, 75)),
                            "max": int(jobs_per_client.max()), "mean": round(float(jobs_per_client.mean()), 2),
                            "sum": int(jobs_per_client.sum())},
        "users_per_client": {"min": int(users_per_client.min()), "p25": int(np.percentile(users_per_client, 25)),
                             "median": float(np.median(users_per_client)), "p75": int(np.percentile(users_per_client, 75)),
                             "max": int(users_per_client.max()), "mean": round(float(users_per_client.mean()), 2)},
        "train_edges_per_client": {"min": int(train_edges_per_client.min()),
                                   "p25": int(np.percentile(train_edges_per_client, 25)),
                                   "median": float(np.median(train_edges_per_client)),
                                   "p75": int(np.percentile(train_edges_per_client, 75)),
                                   "max": int(train_edges_per_client.max())},
        "n_clients_with_train_edges_ge_1": int((train_edges_per_client >= 1).sum()),
        "n_clients_with_train_edges_ge_10": int((train_edges_per_client >= 10).sum()),
        "n_clients_with_fewer_than_2_train_edges": int((train_edges_per_client < 2).sum()),
        "clients_with_zero_train_examples": [int(clients[i]["client_id"]) for i in zero_train[:20]],
        "n_clients_with_zero_users_and_zero_jobs": int(((jobs_per_client == 0) & (users_per_client == 0)).sum()),
        "n_clients_single_job": int((jobs_per_client == 1).sum()),
        "n_clients_max_3_jobs": int((jobs_per_client <= 3).sum()),
        "n_clients_fewer_than_10_users": int((users_per_client < 10).sum()),
        "cross_check_vs_clients_json": {
            "jobs_mismatches": int((jobs_per_client != np.array([c["n_jobs"] for c in clients])).sum()),
            "users_mismatches": int((users_per_client != np.array([c["n_users"] for c in clients])).sum()),
        },
    },
}
(OUT / "test_clean_index.npz").write_bytes(b"")
np.savez_compressed(
    OUT / "test_clean_index.npz",
    is_clean=is_clean.astype(bool),
    edge_pos=test_uj.astype(np.int64),
    detour_flag=detour.astype(bool),
    user=src[test_uj].astype(np.int64),
    job=(dst[test_uj] - n_users).astype(np.int64),
)
(OUT / "t5_supplement.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(rep, ensure_ascii=False, indent=2))
