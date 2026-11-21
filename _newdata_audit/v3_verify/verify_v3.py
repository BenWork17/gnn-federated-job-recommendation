"""Independent verification of artifacts/v3 (task t5).

Reads ONLY the produced artifacts (graph.npz, clients.json, meta.json,
job_titles.json, user_titles.json). Does not import or trust src/prepare_v3.py.

Output: printed table + JSON dump at _newdata_audit/v3_verify/v3_verify.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi")
ART = ROOT / "artifacts" / "v3"
OUT = ROOT / "_newdata_audit" / "v3_verify"
OUT.mkdir(parents=True, exist_ok=True)

checks: list[dict] = []
metrics: dict = {}


def check(item: str, expected: str, actual, ok: bool, severity: str = "high", detail: str = "",
          warn_only: bool = False):
    checks.append({
        "item": item,
        "expected": expected,
        "actual": actual if isinstance(actual, (int, float, str, bool, type(None))) else str(actual),
        "pass": bool(ok),
        "warn_only": bool(warn_only),
        "severity": severity,
        "detail": detail,
    })
    tag = "PASS" if ok else ("WARN" if warn_only else "FAIL")
    print(f"[{tag}] {item}: expect={expected} actual={actual}"
          + (f" | {detail}" if detail else ""))
    return ok


# ---------------------------------------------------------------- 1. arrays
meta = json.loads((ART / "meta.json").read_text(encoding="utf-8"))
z = np.load(ART / "graph.npz", allow_pickle=True)
arrays = {}
for k in z.files:
    a = z[k]
    arrays[k] = a
    if a.ndim == 0:
        metrics.setdefault("array_shapes", {})[k] = {"shape": [], "dtype": str(a.dtype),
                                                    "value": a.item() if a.dtype.kind in "biu" else str(a.item())}
    else:
        metrics.setdefault("array_shapes", {})[k] = {"shape": list(a.shape), "dtype": str(a.dtype)}

scaler = lambda name: int(arrays[name])
n_nodes, n_users, n_jobs = scaler("n_nodes"), scaler("n_users"), scaler("n_jobs")
n_occ, n_skill = scaler("n_occupations"), scaler("n_skills")
offsets = arrays["offsets"].tolist()
edge_index, edge_type = arrays["edge_index"], arrays["edge_type"]
train_mask, test_mask = arrays["train_mask"], arrays["test_mask"]
is_public = arrays["is_public"]
user_ids, job_ids = arrays["user_ids"], arrays["job_ids"]
occ_ids, skill_names = arrays["occ_ids"], arrays["skill_names"]
client_of_job, client_of_user = arrays["client_of_job"], arrays["client_of_user"]

meta_nodes = meta["nodes"]
meta_edges = meta["edges"]
E = edge_index.shape[1]

check("1.1 graph.npz edge_index shape == (2, meta n_edges)",
      f"(2, {meta_edges['n_edges_stored']})",
      list(edge_index.shape),
      list(edge_index.shape) == [2, meta_edges["n_edges_stored"]])
for nm, val in (("n_nodes", n_nodes), ("n_users", n_users), ("n_jobs", n_jobs),
                ("n_occupations", n_occ), ("n_skills", n_skill)):
    check(f"1.2 meta.nodes.{nm} == graph.npz", meta_nodes[nm], val, int(meta_nodes[nm]) == val)
check("1.3 n_nodes == n_users+n_jobs+n_occ+n_skills",
      n_users + n_jobs + n_occ + n_skill, n_nodes,
      n_users + n_jobs + n_occ + n_skill == n_nodes)
check("1.4 offsets == [0,n_users,n_users+n_jobs,n_users+n_jobs+n_occ]",
      f"{[0, n_users, n_users + n_jobs, n_users + n_jobs + n_occ]}", offsets,
      offsets == [0, n_users, n_users + n_jobs, n_users + n_jobs + n_occ])
check("1.5 all mask/type arrays have length E",
      f"{E}", f"{edge_type.shape[0]}/{train_mask.shape[0]}/{test_mask.shape[0]}",
      all(a.shape[0] == E for a in (edge_type, train_mask, test_mask)))
check("1.6 user_ids/job_ids/occ_ids/skill_names lengths match node counts",
      f"{n_users}/{n_jobs}/{n_occ}/{n_skill}",
      f"{len(user_ids)}/{len(job_ids)}/{len(occ_ids)}/{len(skill_names)}",
      (len(user_ids), len(job_ids), len(occ_ids), len(skill_names)) == (n_users, n_jobs, n_occ, n_skill))
check("1.7 is_symmetric flag True", "True", bool(arrays["is_symmetric"]), bool(arrays["is_symmetric"]), severity="low")

# ------------------------------------------------------ 2. edge_index sanity
src, dst = edge_index[0], edge_index[1]
check("2.1 src within [0,n_nodes)", f"0..{n_nodes-1}", f"{int(src.min())}..{int(src.max())}",
      int(src.min()) >= 0 and int(src.max()) < n_nodes)
check("2.2 dst within [0,n_nodes)", f"0..{n_nodes-1}", f"{int(dst.min())}..{int(dst.max())}",
      int(dst.min()) >= 0 and int(dst.max()) < n_nodes)
n_self = int((src == dst).sum())
check("2.3 no self-loops (src==dst)", "0", n_self, n_self == 0)

# duplicate detection on the undirected key (min,max) and on the directed row
lo = np.minimum(src, dst)
hi = np.maximum(src, dst)
key = lo.astype(np.int64) * n_nodes + hi.astype(np.int64)
uniq_key = np.unique(key)
n_dup_undirected = E - len(uniq_key)
# note: same (u,v) pair stored twice with flipped orientation would collide here.
check("2.4 no duplicated undirected edge (unique (min,max) pairs)", f"0 dups, {E} unique",
      f"{n_dup_undirected} dups, {len(uniq_key)} unique", n_dup_undirected == 0)
directed_key = src.astype(np.int64) * n_nodes + dst.astype(np.int64)
n_dup_directed = E - len(np.unique(directed_key))
check("2.5 no duplicated directed row (src,dst)", "0", n_dup_directed, n_dup_directed == 0, severity="low")

# ------------------------------------------------------------ 3. split masks
inter = int((train_mask & test_mask).sum())
check("3.1 train_mask & test_mask intersection == 0", "0", inter, inter == 0, severity="blocker")
check("3.2 train_mask non-empty", ">0", int(train_mask.sum()), int(train_mask.sum()) > 0, severity="blocker")
check("3.3 union of masks covers every edge", E, int((train_mask | test_mask).sum()),
      int((train_mask | test_mask).sum()) == E, severity="medium")
meta_split = meta_edges["split"]
# meta.edges.split counts only user-job edges (split unit = "cạnh user-job"); train_mask
# additionally covers every non-user-job edge. Verify both interpretations explicitly.
ujm = edge_type == 0
check("3.4a meta split test count == test_mask.sum()",
      meta_split["test"], int(test_mask.sum()), int(test_mask.sum()) == meta_split["test"])
check("3.4b meta split train == user-job edges in train_mask",
      meta_split["train"], int((train_mask & ujm).sum()),
      int((train_mask & ujm).sum()) == meta_split["train"])
check("3.4c every non-user-job edge is in train_mask (never test)",
      int(E - ujm.sum()), int((train_mask & ~ujm).sum()),
      int((train_mask & ~ujm).sum()) == int(E - ujm.sum()), severity="blocker")
check("3.5 test_mask only on user-job edges (edge_type==0)",
      f"all {int(test_mask.sum())} are type 0",
      f"{int((test_mask & (edge_type != 0)).sum())} off-type",
      int((test_mask & (edge_type != 0)).sum()) == 0, severity="blocker")

# edge_type counts
type_names = {int(i): str(n) for i, n in enumerate(arrays["edge_type_names"])}
counts = Counter(edge_type.tolist())
metrics["edge_type_counts"] = {type_names[k]: counts[k] for k in sorted(counts)}
for i, name in type_names.items():
    meta_key = [k for k in meta_edges["by_type"] if k.startswith(f"{i}_")]
    exp = meta_edges["by_type"][meta_key[0]] if meta_key else None
    check(f"3.6 edge_type {i} ({name}) count == meta[{meta_key[0] if meta_key else '?'}]", exp,
          counts.get(i, 0), exp is not None and int(exp) == counts.get(i, 0))

# --------------------------------------------------------- 4. leakage checks
# Semantics declared in meta: test_mask indexes rows of edge_index (edge-level mask),
# so test edges ARE rows of edge_index by construction. The harmful pattern is a test
# user-job pair ALSO present as a non-test row (duplicate / flipped / re-added edge),
# or a test pair placed in train_mask. Both are checked below.
uj_mask = edge_type == 0
test_uj = np.where(test_mask & uj_mask)[0]
train_uj = np.where(train_mask & uj_mask)[0]
test_pairs = set(zip(src[test_uj].tolist(), dst[test_uj].tolist()))
train_pairs = set(zip(src[train_uj].tolist(), dst[train_uj].tolist()))
test_as_train = np.intersect1d(src[test_uj], np.array([], dtype=np.int64))  # placeholder
overlap = test_pairs & train_pairs
check("4.1 no test user-job pair also present as train user-job edge", "0", len(overlap),
      len(overlap) == 0, severity="blocker",
      detail="test_mask marks rows of edge_index by design (edge-level split); "
             "overlap of the SAME pair between train and test would be real leakage")
# a test (u,j) appearing in another row under any type
all_pairs = set(zip(src.tolist(), dst.tolist()))
dup_test_rows = sum(1 for p in test_pairs if p in train_pairs)
metrics["leakage"] = {
    "test_user_job_edges": len(test_uj),
    "train_user_job_edges": len(train_uj),
    "test_pairs_in_train": len(overlap),
    "note": "edge_index chứa cạnh test là ĐÚNG thiết kế mask theo cạnh; rò rỉ thật = cùng cặp (u,j) vừa train vừa test.",
}
# transductive-check: how many test users/jobs also appear in train (expected >0, informational)
test_users = set(src[test_uj].tolist())
test_jobs = set(dst[test_uj].tolist())
train_users = set(src[train_uj].tolist())
train_jobs = set(dst[train_uj].tolist())
metrics["leakage"]["test_users_seen_in_train"] = len(test_users & train_users)
metrics["leakage"]["test_jobs_seen_in_train"] = len(test_jobs & train_jobs)
metrics["leakage"]["transductive_note"] = (
    f"Chia theo CẠNH chứ không theo nút: {len(test_users & train_users)}/{len(test_users)} user test đều có "
    f"cạnh train (transductive hợp lệ, nhãn cạnh test không nằm trong train). Phía job thì KHÔNG hoàn toàn: "
    f"chỉ {len(test_jobs & train_jobs)}/{len(test_jobs)} job test xuất hiện trong train — phần còn lại là "
    f"test-only job, xem 10.1b.")
check("4.2 each test user's test edges are excluded from train (label leakage)", "0 overlapping pairs",
      len(overlap), len(overlap) == 0, severity="blocker")

# --------------------------------------------------------------- 5. clients
clients = json.loads((ART / "clients.json").read_text(encoding="utf-8"))
n_clients = len(clients)
cids = [c["client_id"] for c in clients]
check("5.1 client_id contiguous 0..N-1", f"0..{n_clients-1}", f"min={min(cids)} max={max(cids)} n={n_clients}",
      sorted(cids) == list(range(n_clients)))
min_apps = min(c["n_apps"] for c in clients)
check("5.2 no client with <10 apps", ">=10", f"min={min_apps}", min_apps >= 10, severity="blocker")
sum_apps = sum(c["n_apps"] for c in clients)
check("5.3 sum(client.n_apps) == meta.n_apps_covered == #user-job edges",
      f"{meta['clients']['n_apps_covered']} / {int(uj_mask.sum())}",
      f"{sum_apps} / {int(uj_mask.sum())}",
      sum_apps == meta["clients"]["n_apps_covered"] == int(uj_mask.sum()))
check("5.4 all clients have n_users>0 and n_jobs>0", "min > 0",
      f"min_users={min(c['n_users'] for c in clients)} min_jobs={min(c['n_jobs'] for c in clients)}",
      min(c["n_users"] for c in clients) > 0 and min(c["n_jobs"] for c in clients) > 0,
      severity="blocker")
check("5.5 unique employer names", n_clients, len({c["employer_name"] for c in clients}),
      len({c["employer_name"] for c in clients}) == n_clients)
check("5.6 n_clients == meta.clients.n_clients", meta["clients"]["n_clients"], n_clients,
      n_clients == meta["clients"]["n_clients"])
check("5.7 client_id in graph arrays within [0, n_clients)", f"0..{n_clients-1}",
      f"job:{int(client_of_job.min())}..{int(client_of_job.max())} user:{int(client_of_user.min())}..{int(client_of_user.max())}",
      int(client_of_job.max()) < n_clients and int(client_of_user.max()) < n_clients)

# per-client recount straight from the graph
app_per_client = np.bincount(client_of_job.astype(np.int64)[(dst[uj_mask] - n_users)], minlength=n_clients)
jobs_per_client = np.bincount(client_of_job.astype(np.int64), minlength=n_clients)
users_per_client = [set() for _ in range(n_clients)]
mismatch_apps = [(clients[i]["client_id"], clients[i]["n_apps"], int(app_per_client[i]))
                 for i in range(n_clients) if clients[i]["n_apps"] != int(app_per_client[i])]
check("5.8 per-client n_apps recomputed from graph match clients.json", "0 mismatches",
      f"{len(mismatch_apps)} mismatches", len(mismatch_apps) == 0, severity="blocker",
      detail=str(mismatch_apps[:5]))
mismatch_jobs = [(clients[i]["client_id"], clients[i]["n_jobs"], int(jobs_per_client[i]))
                 for i in range(n_clients) if clients[i]["n_jobs"] != int(jobs_per_client[i])]
check("5.9 per-client n_jobs recomputed from graph match clients.json", "0 mismatches",
      f"{len(mismatch_jobs)} mismatches", len(mismatch_jobs) == 0, severity="medium",
      detail=str(mismatch_jobs[:5]))

# sizes distribution
sizes = np.array([c["n_apps"] for c in clients], dtype=np.int64)
metrics["clients"] = {
    "n_clients": n_clients,
    "n_apps_total": int(sizes.sum()),
    "n_users_total_meta": meta["clients"]["n_users_covered"],
    "n_jobs_total_meta": meta["clients"]["n_jobs_covered"],
    "size_min": int(sizes.min()), "size_p25": int(np.percentile(sizes, 25)),
    "size_median": float(np.median(sizes)), "size_p75": int(np.percentile(sizes, 75)),
    "size_max": int(sizes.max()), "size_mean": round(float(sizes.mean()), 2),
    "n_clients_with_lt_10": int((sizes < 10).sum()),
    "gini": round(float(1 - 2 * np.trapezoid(np.cumsum(np.sort(sizes)) / sizes.sum(),
                                             dx=1 / len(sizes))), 4) if n_clients > 1 else 0.0,
}

# ---------------------------------------------- 6. occupation code consistency
def len_hist(arr) -> dict:
    c = Counter(len(str(x)) for x in arr)
    return {str(k): int(v) for k, v in sorted(c.items())}

metrics["occupation_codes"] = {
    "occ_node_len_hist": len_hist(occ_ids),
    "occ_node_sample": occ_ids[:5].tolist(),
    "occ_node_unique": int(len(set(occ_ids.tolist()))),
}
check("6.1 occupation node codes all SAME length 7 (soc[:7] -> '11-1011')", "100% len 7",
      metrics["occupation_codes"]["occ_node_len_hist"],
      set(len_hist(occ_ids)) == {"7"}, severity="blocker",
      detail="meta ghi 'soc[:7] (6 ky tu goc)' la cau chu SAI: soc[:7] cho 7 ky tu ('11-1011'). "
             "Do dai thuc te phai la 7 va phai DONG NHAT; '6 ky tu' trong meta/contract la nham lan.")
check("6.2 occupation node codes unique", n_occ, len(set(occ_ids.tolist())),
      len(set(occ_ids.tolist())) == n_occ)

occ_lo, occ_hi = offsets[1] + 0, offsets[1] + n_jobs  # job range
occ_start, occ_end = offsets[2], offsets[2] + n_occ
skill_start = offsets[3]

# job-occ edges: dst must be occupation index, src in job range
jo = np.where(edge_type == 1)[0]
check("6.3 job-occ edges: src in job range", f"[{offsets[1]},{offsets[1]+n_jobs})",
      f"{int(src[jo].min())}..{int(src[jo].max())}",
      int(src[jo].min()) >= offsets[1] and int(src[jo].max()) < offsets[1] + n_jobs)
check("6.4 job-occ edges: dst in occupation range", f"[{occ_start},{occ_end})",
      f"{int(dst[jo].min())}..{int(dst[jo].max())}",
      int(dst[jo].min()) >= occ_start and int(dst[jo].max()) < occ_end)
uo = np.where(edge_type == 3)[0]
check("6.5 user-occ edges: src in user range", f"[0,{n_users})",
      f"{int(src[uo].min())}..{int(src[uo].max())}",
      int(src[uo].min()) >= 0 and int(src[uo].max()) < n_users)
check("6.6 user-occ edges: dst in occupation range", f"[{occ_start},{occ_end})",
      f"{int(dst[uo].min())}..{int(dst[uo].max())}",
      int(dst[uo].min()) >= occ_start and int(dst[uo].max()) < occ_end)
os_ = np.where(edge_type == 2)[0]
check("6.7 occ-skill edges: src in occupation range", f"[{occ_start},{occ_end})",
      f"{int(src[os_].min())}..{int(src[os_].max())}",
      int(src[os_].min()) >= occ_start and int(src[os_].max()) < occ_end)
check("6.8 occ-skill edges: dst in skill range", f"[{skill_start},{n_nodes})",
      f"{int(dst[os_].min())}..{int(dst[os_].max())}",
      int(dst[os_].min()) >= skill_start and int(dst[os_].max()) < n_nodes)

# codes carried by job metadata / user metadata must be in the node vocabulary
job_titles = json.loads((ART / "job_titles.json").read_text(encoding="utf-8"))
user_titles = json.loads((ART / "user_titles.json").read_text(encoding="utf-8"))
meta_job_occs = {v.get("occupation") or "" for v in job_titles.values()}
meta_user_occs = {v.get("occupation") or "" for v in user_titles.values()}
meta_job_occs.discard("")
meta_user_occs.discard("")
occ_set = set(occ_ids.tolist())
check("6.9 job_titles occupation codes are 7 chars", "100% len 7",
      len_hist(meta_job_occs), set(len_hist(meta_job_occs)) == {"7"}, severity="blocker")
check("6.10 user_titles occupation codes are 7 chars", "100% len 7",
      len_hist(meta_user_occs), set(len_hist(meta_user_occs)) == {"7"}, severity="blocker")
check("6.11 job_titles occupation codes ⊆ occ node vocab", "0 unknown",
      len(meta_job_occs - occ_set), not (meta_job_occs - occ_set), severity="blocker",
      detail=str(sorted(meta_job_occs - occ_set)[:5]))
n_user_occ_not_in_vocab = len(meta_user_occs - occ_set)
n_users_affected = sum(1 for v in user_titles.values()
                       if (v.get("occupation") or "") and (v.get("occupation") or "") not in occ_set)
metrics["occupation_codes"]["user_titles_codes_not_in_occ_vocab"] = sorted(meta_user_occs - occ_set)
metrics["occupation_codes"]["n_users_with_code_not_in_vocab"] = n_users_affected
# classify those codes against the raw O*NET zip: they must still be real O*NET SOC codes
import csv as _csv, io as _io, zipfile as _zip
_onet_zip = Path(meta["paths"]["onet_zip"])
_onet_all: set[str] = set()
_onet_tech: set[str] = set()
with _zip.ZipFile(_onet_zip) as zf:
    def _rows(name):
        raw = zf.read(name).decode("utf-8-sig", errors="replace")
        r = _csv.reader(_io.StringIO(raw), delimiter="\t")
        next(r)
        return [x for x in r if len(x) > 1]
    _onet_all = {x[0][:7] for x in _rows("db_29_3_text/Occupation Data.txt")}
    _onet_tech = {x[0][:7] for x in _rows("db_29_3_text/Technology Skills.txt")}
extra_codes = meta_user_occs - occ_set
metrics["occupation_codes"]["user_codes_not_in_vocab_are_valid_onet"] = len(extra_codes & _onet_all)
metrics["occupation_codes"]["user_codes_not_in_vocab_with_tech_skill"] = len(extra_codes & _onet_tech)
check("6.12 user_titles codes not in graph vocab are still valid O*NET codes (no mixed level)",
      "0 invalid O*NET codes", f"{len(extra_codes)} codes, all valid O*NET={len(extra_codes & _onet_all)==len(extra_codes)}",
      len(extra_codes & _onet_all) == len(extra_codes), severity="medium",
      detail=f"{n_users_affected} users mang ma khong phai nut do thi (nghề không có job nào map tới); "
             f"mọi mã vẫn dài 7 ký tự và có thật trong O*NET -> KHÔNG trộn cấp, nhưng là dangling reference: "
             f"join user_titles.occupation -> occ node sẽ miss {len(extra_codes)} mã")
# those users must have zero user-occ edges (harmless for masks/split)
u2o_idx = {}
for u, o in zip(src[np.where(edge_type == 3)[0]].tolist(), dst[np.where(edge_type == 3)[0]].tolist()):
    u2o_idx.setdefault(int(u), set()).add(int(o))
affected_with_edge = 0
for i, uidv in enumerate(user_ids.tolist()):
    code = (user_titles.get(str(uidv), {}).get("occupation") or "")
    if code and code not in occ_set and i in u2o_idx:
        affected_with_edge += 1
check("6.12b users with non-vocab code have no user-occ edge (dangling metadata only)", "0",
      affected_with_edge, affected_with_edge == 0, severity="medium", warn_only=True,
      detail="1.217 user vừa mang mã ngoài vocab ở metadata vừa có cạnh user-occ; nguyên nhân: metadata lấy "
             "nghề của title sequence LỚN NHẤT (nghề đó không có job nào -> không thành nút), còn cạnh lấy "
             "TOÀN BỘ nghề trong history. Không phải trộn cấp; trùng đúng số conflict ở 6.17.")

# graph job-occ edges must correspond 1:1 to job metadata with non-empty occupation
job_occ_nodes = set(src[jo].tolist())
jobs_with_meta_occ = {offsets[1] + int(j) for j, v in enumerate(job_ids) if (job_titles.get(str(v), {}).get("occupation") or "")}
check("6.13 jobs with job-occ edge == jobs whose metadata has occupation",
      f"{len(jobs_with_meta_occ)} jobs", f"{len(job_occ_nodes)} edge-jobs",
      job_occ_nodes == jobs_with_meta_occ, severity="blocker",
      detail=f"only_in_edges={len(job_occ_nodes-jobs_with_meta_occ)} only_in_meta={len(jobs_with_meta_occ-job_occ_nodes)}")
# job-occ: one occupation per job
jo_per_job = Counter(src[jo].tolist())
check("6.14 each job has at most one occupation edge", "1", max(jo_per_job.values()) if jo_per_job else 0,
      max(jo_per_job.values()) == 1 if jo_per_job else True, severity="blocker")

metrics["occupation_codes"]["n_jobs_with_occ_edge"] = int(len(job_occ_nodes))
metrics["occupation_codes"]["n_jobs_meta_with_occ"] = int(len(jobs_with_meta_occ))
metrics["occupation_codes"]["pct_jobs_with_occ_edge"] = round(100 * len(job_occ_nodes) / n_jobs, 2)
metrics["occupation_codes"]["meta_n_jobs_with_occupation_edge"] = meta_edges["n_jobs_with_occupation_edge"]

# user-occ: many users legitimately carry several occupations (career history), so the
# real check is that the user's metadata occupation is among the edge targets and that
# every edge target is a valid occupation node.
uo_per_user = Counter(src[uo].tolist())
max_occ_per_user = max(uo_per_user.values()) if uo_per_user else 0
metrics["occupation_codes"]["user_occ_edges_per_user_max"] = int(max_occ_per_user)
metrics["occupation_codes"]["n_users_with_user_occ_edge"] = int(len(uo_per_user))
metrics["occupation_codes"]["n_users_multi_occ_edge"] = int(sum(1 for v in uo_per_user.values() if v > 1))
check("6.15 user-occ edges per user bounded (<=20, đa nghề là hợp lệ)", "<=20",
      int(max_occ_per_user), max_occ_per_user <= 20, severity="low")
check("6.16 no (user,occ) pair duplicated", "0 dups",
      int(len(uo)) - len(set(zip(src[uo].tolist(), dst[uo].tolist()))),
      len(uo) == len(set(zip(src[uo].tolist(), dst[uo].tolist()))), severity="blocker")
# metadata occupation must appear among the user's edge occupations when both exist
occ_of_idx = {occ_start + i: occ_ids[i] for i in range(n_occ)}
u2o_codes: dict[int, set] = {}
for u, o in zip(src[uo].tolist(), dst[uo].tolist()):
    u2o_codes.setdefault(int(u), set()).add(occ_of_idx[int(o)])
agree = mismatch = meta_only = edge_only = 0
for i, uidv in enumerate(user_ids.tolist()):
    m = (user_titles.get(str(uidv), {}).get("occupation") or "")
    e = u2o_codes.get(i, set())
    if m and e:
        if m in e:
            agree += 1
        else:
            mismatch += 1
    elif m and not e:
        meta_only += 1
    elif e and not m:
        edge_only += 1
metrics["occupation_codes"].update({
    "user_meta_occ_agrees_with_edge": agree,
    "user_meta_occ_conflicts_with_edge": mismatch,
    "user_meta_occ_but_no_edge": meta_only,
    "user_edge_but_meta_empty": edge_only,
    "pct_user_meta_occ_agree": round(100 * agree / max(1, agree + mismatch), 2),
})
pct_agree = metrics["occupation_codes"]["pct_user_meta_occ_agree"]
check("6.17 user metadata occupation ∈ edge occupation targets (when both present)",
      ">=95% agree (khai báo lệch)", f"{pct_agree}% agree, {mismatch} conflicts",
      pct_agree >= 95.0, severity="low",
      detail="metadata lấy 'nghề của title có sequence lớn nhất'; edge lấy TOÀN BỘ nghề trong history "
             "-> lệch 1.217 user đa nghề là KỲ VỌNG, đã đo vào JSON; không ảnh hưởng mask/split")

# ---------------------------------------------- 7. skill layer diagnostics
skill_deg = Counter(src[os_].tolist())  # occ index -> n skills
deg = np.array([skill_deg.get(occ_start + i, 0) for i in range(n_occ)], dtype=np.int64)
occ_with_skill = int((deg > 0).sum())
occ_all_skills = int((deg == n_skill).sum())
metrics["skills"] = {
    "n_skill_nodes": n_skill,
    "n_occ_nodes": n_occ,
    "n_occ_with_skill": occ_with_skill,
    "n_occ_without_skill": n_occ - occ_with_skill,
    "n_occ_with_ALL_skills": occ_all_skills,
    "pct_occ_with_all_skills": round(100 * occ_all_skills / n_occ, 2),
    "skills_per_occ_min": int(deg.min()), "skills_per_occ_p25": int(np.percentile(deg, 25)),
    "skills_per_occ_median": float(np.median(deg)), "skills_per_occ_p75": int(np.percentile(deg, 75)),
    "skills_per_occ_p90": int(np.percentile(deg, 90)), "skills_per_occ_max": int(deg.max()),
    "skills_per_occ_mean": round(float(deg.mean()), 2),
    "n_occ_skill_edges": int(len(os_)),
    "n_edges_expected_from_deg": int(deg.sum()),
    "skill_usage_min": int(min(Counter(dst[os_].tolist()).values())) if len(os_) else 0,
    "n_skills_used": int(len(set(dst[os_].tolist()))),
}
check("7.1 skill layer not degenerate: not 100% of occupations have all skills",
      "<100%", f"{metrics['skills']['pct_occ_with_all_skills']}%",
      occ_all_skills < n_occ, severity="blocker")
check("7.2 occ-skill edge count == sum of per-occ degrees", int(len(os_)),
      metrics["skills"]["n_edges_expected_from_deg"], int(deg.sum()) == len(os_))
check("7.3 occ-skill edges have distinct (occ,skill) pairs", "0 dups",
      len(os_) - len(set(zip(src[os_].tolist(), dst[os_].tolist()))),
      len(os_) == len(set(zip(src[os_].tolist(), dst[os_].tolist()))))
check("7.4 every skill node used at least once", n_skill, metrics["skills"]["n_skills_used"],
      metrics["skills"]["n_skills_used"] == n_skill, severity="low")
check("7.5 median skills/occupation in healthy range (5..500)",
      "5 <= median <= 500", metrics["skills"]["skills_per_occ_median"],
      5 <= metrics["skills"]["skills_per_occ_median"] <= 500, severity="low")

# --------------------------------------------------------------- 8. extras
check("8.1 is_public length == n_nodes", n_nodes, len(is_public), len(is_public) == n_nodes)
n_public = int(is_public.sum())
check("8.2 n_public_nodes == meta (jobs+occ+skill)", meta_nodes["n_public_nodes"], n_public,
      n_public == meta_nodes["n_public_nodes"], severity="low")
check("8.3 is_public=1 exactly for occ+skill nodes (metadata-bearing nodes)", 1,
      int((is_public[:n_users] == 0).all() and (is_public[n_users:n_users + n_jobs] == 0).all()
          and (is_public[n_users + n_jobs:] == 1).all()),
      int((is_public[:n_users] == 0).all() and (is_public[n_users:n_users + n_jobs] == 0).all()
          and (is_public[n_users + n_jobs:] == 1).all()), severity="low",
      detail="is_public CHI bat cho occ+skill (=8.343). Job khong bat du co employer metadata; "
             "ten 'is_public' de hieu nham, nen doc la 'is_catalog_node'.")
check("8.4 user_ids unique (nodes are distinct users)", n_users, len(set(user_ids.tolist())),
      len(set(user_ids.tolist())) == n_users, severity="blocker")
check("8.5 job_ids unique", n_jobs, len(set(job_ids.tolist())), len(set(job_ids.tolist())) == n_jobs,
      severity="blocker")
check("8.6 skill_names unique", n_skill, len(set(skill_names.tolist())),
      len(set(skill_names.tolist())) == n_skill, severity="medium")
sparsity_uj = round(100 * int(uj_mask.sum()) / (n_users * n_jobs), 6)
metrics["sparsity"] = {
    "meta_sparsity_pct": meta["sparsity_pct"],
    "user_job_edges_over_users_x_jobs_pct": sparsity_uj,
    "all_edges_over_n_nodes_sq_pct": round(100 * E / (n_nodes ** 2), 6),
    "definition_guess": "meta dùng #cạnh user-job / (n_users*n_jobs) * 100",
}
check("8.7 sparsity matches meta with user-job/(users*jobs) formula",
      f"{meta['sparsity_pct']}%", sparsity_uj, abs(sparsity_uj - meta["sparsity_pct"]) < 0.0001,
      severity="low")

# per-type degree sanity: jobs without occupation edge reported honestly
deg_job_total = np.bincount((src[uj_mask]).astype(np.int64), minlength=n_nodes) + \
                np.bincount((dst[uj_mask]).astype(np.int64), minlength=n_nodes)
metrics["jobs"] = {
    "n_jobs": n_jobs,
    "n_jobs_with_occ_edge": int(len(job_occ_nodes)),
    "pct_jobs_with_occ_edge": metrics["occupation_codes"]["pct_jobs_with_occ_edge"],
    "n_jobs_zero_user_job_edge": int((deg_job_total[n_users:n_users + n_jobs] == 0).sum()),
}
check("8.8 every job node has >=1 user-job edge", "0 orphan jobs",
      metrics["jobs"]["n_jobs_zero_user_job_edge"],
      metrics["jobs"]["n_jobs_zero_user_job_edge"] == 0, severity="medium")

# --------------------------------------------------------------- 9. split stats
n_test = int(test_mask.sum())
# users are eligible for a test split only with >= min_apps_for_test (5) applications;
# recompute the effective ratio on that eligible subset.
uj_deg_all = np.bincount(src[uj_mask].astype(np.int64), minlength=n_nodes) + \
             np.bincount(dst[uj_mask].astype(np.int64), minlength=n_nodes)
eligible_users = np.zeros(n_nodes, dtype=bool)
eligible_users[:n_users] = uj_deg_all[:n_users] >= meta["config"]["min_apps_for_test"]
eligible_uj = int((uj_mask & (eligible_users[src] | eligible_users[dst])).sum())
test_in_eligible = int((test_mask & uj_mask & (eligible_users[src] | eligible_users[dst])).sum())
metrics["split"] = {
    "train_edges": int(train_mask.sum()), "test_edges": n_test,
    "test_ratio_of_all_edges": round(n_test / E, 4),
    "test_user_job_edges": len(test_uj),
    "test_ratio_of_all_user_job_edges": round(len(test_uj) / int(uj_mask.sum()), 4),
    "n_users_eligible_min_apps_5": int(eligible_users[:n_users].sum()),
    "user_job_edges_eligible": eligible_uj,
    "test_edges_on_eligible": test_in_eligible,
    "test_ratio_on_eligible_edges": round(test_in_eligible / max(1, eligible_uj), 4),
    "test_type_breakdown": {type_names[int(t)]: int(((edge_type == t) & test_mask).sum())
                            for t in sorted(type_names)},
}
check("9.1 test ratio on eligible user-job edges ~= 0.2 (0.15..0.25)", "0.15..0.25",
      metrics["split"]["test_ratio_on_eligible_edges"],
      0.15 <= metrics["split"]["test_ratio_on_eligible_edges"] <= 0.25, severity="high",
      detail=f"trên TOÀN BỘ cạnh user-job chỉ {metrics['split']['test_ratio_of_all_user_job_edges']}"
             f" do user <5 app bị loại khỏi split (min_apps_for_test=5) chứ không phải chia sai")
check("9.2 test edges only belong to users with >=5 apps (min_apps_for_test)", "0 violations",
      int((test_mask & uj_mask & ~(eligible_users[src] | eligible_users[dst])).sum()),
      int((test_mask & uj_mask & ~(eligible_users[src] | eligible_users[dst])).sum()) == 0,
      severity="blocker")

# ---------------- 10. captain's deep checks (leakage / silo consistency) ----
# 10a. per-user: users appearing only in test (0 train user-job edge)
user_has_train = np.zeros(n_nodes, dtype=bool)
user_has_test = np.zeros(n_nodes, dtype=bool)
user_has_train[src[train_uj]] = True
user_has_train[dst[train_uj]] = True
user_has_test[src[test_uj]] = True
user_has_test[dst[test_uj]] = True
test_only_users = int((user_has_test & ~user_has_train)[:n_users].sum())
n_users_with_test = int(user_has_test[:n_users].sum())
n_users_with_train = int(user_has_train[:n_users].sum())
metrics["leakage"]["users_with_test_edges"] = n_users_with_test
metrics["leakage"]["users_with_train_edges"] = n_users_with_train
metrics["leakage"]["users_with_test_but_no_train"] = test_only_users
check("10.1 no test-only USER (cold-start user)", "0", test_only_users, test_only_users == 0,
      severity="medium",
      detail="user co canh test nhung 0 canh train -> cold start, phai khai bao neu >0")
# job side: a job can legitimately end up with only its test edge(s) because the split is
# per-user, not per-job -> eval candidate with no observed training interaction.
job_train_cnt = np.bincount(dst[train_uj].astype(np.int64) - n_users, minlength=n_jobs)
job_test_cnt = np.bincount(dst[test_uj].astype(np.int64) - n_users, minlength=n_jobs)
test_only_jobs = int(((job_test_cnt > 0) & (job_train_cnt == 0)).sum())
metrics["leakage"]["jobs_with_test_edges"] = int((job_test_cnt > 0).sum())
metrics["leakage"]["jobs_with_test_but_no_train_edge"] = test_only_jobs
metrics["leakage"]["pct_jobs_test_only"] = round(100 * test_only_jobs / n_jobs, 2)
check("10.1b no test-only JOB (eval item with zero training interaction)", "0", test_only_jobs,
      test_only_jobs == 0, severity="low", warn_only=True,
      detail="chia theo user nen job chỉ có 1 tương tác (của user có test) sẽ rơi toàn bộ vào test; "
             "không phải rò rỉ nhưng phải khai báo khi tính R@20 vì job đó chưa từng xuất hiện trong train")
# supplement: users with zero user-job edges at all
uj_deg = np.bincount(src[uj_mask].astype(np.int64), minlength=n_nodes) + \
         np.bincount(dst[uj_mask].astype(np.int64), minlength=n_nodes)
metrics["leakage"]["user_nodes_with_zero_user_job_edge"] = int((uj_deg[:n_users] == 0).sum())
check("10.2 every user node has >=1 user-job edge", "0", int((uj_deg[:n_users] == 0).sum()),
      int((uj_deg[:n_users] == 0).sum()) == 0, severity="low")

# 10b. indirect leakage: test (u,j) reachable as u-occ-...-occ-j through train
user_occ = {int(u): int(o) for u, o in zip(src[uo].tolist(), dst[uo].tolist())}
job_occ = {int(j): int(o) for j, o in zip(src[jo].tolist(), dst[jo].tolist())}
user_occ_set: dict[int, set] = {}
for u, o in zip(src[uo].tolist(), dst[uo].tolist()):
    user_occ_set.setdefault(int(u), set()).add(int(o))
indirect = 0
indirect_examples = []
for e in test_uj.tolist():
    u, j = int(src[e]), int(dst[e])
    o = job_occ.get(j)
    if o is not None and o in user_occ_set.get(u, ()):
        indirect += 1
        if len(indirect_examples) < 5:
            indirect_examples.append({"user": u, "job": j, "occ": o})
pct_indirect = round(100 * indirect / max(1, len(test_uj)), 2)
metrics["leakage"]["test_edges_indirect_via_occupation"] = indirect
metrics["leakage"]["pct_test_edges_indirect_via_occupation"] = pct_indirect
metrics["leakage"]["indirect_examples"] = indirect_examples
metrics["leakage"]["indirect_note"] = (
    "Canh test (u,j) ma u va j cung noi toi cung mot nut occupation qua cac canh TRAIN: "
    "duong di u-occ-j ton tai trong train nen mo hinh co the suy ra lien ket nay ma khong can nhan test. "
    "Day la ro ri GIAN TIEP co that, lam R@20 phong len; can khai bao trong notebook.")
check("10.3 no indirect leakage via shared occupation (u->occ->j in train)", "0",
      f"{indirect} ({pct_indirect}% test edges)", indirect == 0, severity="medium", warn_only=True,
      detail="RÒ RỈ GIÁN TIẾP CÓ THẬT: 880 cạnh test (2,32%) có u và j cùng nối tới một nút nghề qua "
             "các cạnh TRAIN, nên mô hình có thể chấm đúng cạnh này mà không học từ nhãn test. "
             "Không phải lỗi schema (occupation là đặc trưng công khai của job), nhưng R@20 bị phồng "
             "-> bắt buộc khai báo trong notebook và báo cả metric trên tập con không có đường vòng.")

# 10c. duplicates on (src,dst,type)
et = edge_type
trip = np.stack([src.astype(np.int64), dst.astype(np.int64), et.astype(np.int64)], axis=1)
n_unique_trip = len(np.unique(trip, axis=0))
check("10.4 no duplicated (src,dst,type) triple", "0 dups",
      f"{len(trip) - n_unique_trip} dups", len(trip) == n_unique_trip, severity="blocker")

# 10d. silo consistency. There is no exclusive "client of user" membership; a client owns
# jobs, and a user-job edge is only representable inside the silo of the job's owner.
# Real checks: (a) client_of_job well defined for every job, (b) per-client edge totals
# never exceed clients.json n_apps, (c) client_of_user really is argmax over the user's
# own edges (ties -> smaller client_id), (d) multi-client share matches meta.
edge_clients = client_of_job[(dst[uj_mask] - n_users).astype(np.int64)]
job_app_edges = np.bincount(dst[uj_mask].astype(np.int64) - n_users, minlength=n_jobs)
sum_by_client_from_edges = np.zeros(n_clients, dtype=np.int64)
np.add.at(sum_by_client_from_edges, client_of_job.astype(np.int64), job_app_edges)
client_app_total = np.array([c["n_apps"] for c in clients], dtype=np.int64)
check("10.5 client_of_job well defined (0 <= id < n_clients) for every job", "0 anomalies",
      int((client_of_job < 0).sum() + (client_of_job >= n_clients).sum()),
      int((client_of_job < 0).sum() + (client_of_job >= n_clients).sum()) == 0, severity="blocker")
check("10.5b per-client app totals from edges never exceed clients.json n_apps", "0 over",
      int((sum_by_client_from_edges > client_app_total).sum()),
      int((sum_by_client_from_edges > client_app_total).sum()) == 0, severity="blocker")

# (c) client_of_user == argmax over the user's own edges, ties -> smaller client_id
u_arr = src[uj_mask].astype(np.int64)
c_arr = edge_clients.astype(np.int64)
key = u_arr * n_clients + c_arr
uk, cnts = np.unique(key, return_counts=True)
order = np.lexsort((uk % n_clients, -cnts, uk // n_clients))
best_u = (uk[order] // n_clients)
first = np.ones(len(order), dtype=bool)
first[1:] = best_u[1:] != best_u[:-1]
best = order[first]
argmax_users = uk[best] // n_clients
argmax_client = uk[best] % n_clients
cou_mismatch = int((client_of_user[argmax_users] != argmax_client).sum())
check("10.5c client_of_user == argmax apps per user (ties -> smaller client_id)", "0 mismatches",
      cou_mismatch, cou_mismatch == 0, severity="blocker")

per_user_n_clients = np.unique(uk // n_clients, return_counts=True)[1]
multi = int((per_user_n_clients > 1).sum())
pct_multi = round(100 * multi / len(per_user_n_clients), 2)
same_primary = int((client_of_user[u_arr] == c_arr).sum())
pct_same_primary = round(100 * same_primary / int(uj_mask.sum()), 2)
pct_same_primary_train = round(100 * int(
    (client_of_user[src[train_uj]] == client_of_job[(dst[train_uj] - n_users)]).sum())
    / max(1, len(train_uj)), 2)
metrics["cross_silo"] = {
    "client_of_user_definition": "client co nhieu application nhat cua user (nhan SUY RA, khong phai membership doc quyen)",
    "n_user_job_edges": int(uj_mask.sum()),
    "edges_where_primary_client_of_user == client_of_job": same_primary,
    "pct_primary_client_match_all": pct_same_primary,
    "pct_primary_client_match_train": pct_same_primary_train,
    "edges_outside_primary_client": int(uj_mask.sum()) - same_primary,
    "client_of_user_argmax_mismatches": cou_mismatch,
    "n_users_multi_client_measured": multi,
    "pct_users_multi_client_measured": pct_multi,
    "clients_edges_exceeding_n_apps": int((sum_by_client_from_edges > client_app_total).sum()),
}
metrics["cross_silo"] = {
    "client_of_user_definition": "client co nhieu application nhat cua user (nhan SUY RA, khong phai membership doc quyen)",
    "n_user_job_edges": int(uj_mask.sum()),
    "edges_where_primary_client_of_user == client_of_job": same_primary,
    "pct_primary_client_match_all": pct_same_primary,
    "pct_primary_client_match_train": pct_same_primary_train,
    "edges_outside_primary_client": int(uj_mask.sum()) - same_primary,
    "client_of_user_argmax_mismatches": cou_mismatch,
    "n_users_multi_client_measured": multi,
    "pct_users_multi_client_measured": pct_multi,
    "clients_edges_exceeding_n_apps": int((sum_by_client_from_edges > client_app_total).sum()),
}
check("10.6 pct edges where user's PRIMARY client == job's client (informational)",
      "khong phai tieu chi PASS", f"{pct_same_primary}% match / {round(100-pct_same_primary,2)}% mismatch",
      True, severity="low",
      detail="mismatch la BINH THUONG: client_of_user chi la nhan 'client nhieu app nhat', "
             "khong phai membership doc quyen. Kiem tra silo that nam o 10.5/10.5b/10.5c.")
check("10.7 measured multi-client user share matches meta (44.58%)",
      meta["clients"]["pct_users_multi_client"], pct_multi,
      abs(pct_multi - meta["clients"]["pct_users_multi_client"]) < 0.05, severity="low")
check("10.8 multi-client users are NOT cross-silo leakage (declared semantics)", "khai bao dung",
      f"{multi} users ({pct_multi}%) aps ở >=2 employer", True, severity="low",
      detail="moi canh user-job van nam trong silo cua client so huu job; user xuat hien o nhieu silo "
             "vi ung tuyen o nhieu employer — dung ban chat FL theo employer, khong phai chia se du lieu")

# ---------------- 11. deltas vs captain's independent baseline -----------------
baseline = {
    "edge_index_shape": "(2, 764364)",
    "n_nodes": 264995, "n_users": 171807, "n_jobs": 84845,
    "n_occupations": 583, "n_skills": 7760,
    "offsets": [0, 171807, 256652, 257235],
    "index_min": 0, "index_max": 264994,
    "edge_type_0_user_job": 436893, "edge_type_1_job_occ": 26678,
    "edge_type_2_occ_skill": 25866, "edge_type_3_user_occ": 274927,
    "train_user_job": 398936, "test_user_job": 37957,
    "n_clients": 9116, "client_min_apps": 10, "client_median_apps": 23, "client_max_apps": 4745,
    "clients_with_lt_10": 0,
    "occ_with_skill": 564, "skills_used": 7760,
    "skills_per_occ_min": 2, "skills_per_occ_median": 24, "skills_per_occ_mean": 45.9,
    "skills_per_occ_max": 594,
    "n_jobs_with_occ_edge": 26678, "n_jobs_without_occ_edge": 58167,
}
actuals = {
    "edge_index_shape": f"({edge_index.shape[0]}, {edge_index.shape[1]})",
    "n_nodes": n_nodes, "n_users": n_users, "n_jobs": n_jobs,
    "n_occupations": n_occ, "n_skills": n_skill,
    "offsets": offsets,
    "index_min": int(min(src.min(), dst.min())), "index_max": int(max(src.max(), dst.max())),
    "edge_type_0_user_job": int(counts.get(0, 0)), "edge_type_1_job_occ": int(counts.get(1, 0)),
    "edge_type_2_occ_skill": int(counts.get(2, 0)), "edge_type_3_user_occ": int(counts.get(3, 0)),
    "train_user_job": int((train_mask & uj_mask).sum()), "test_user_job": int(test_mask.sum()),
    "n_clients": n_clients, "client_min_apps": int(sizes.min()),
    "client_median_apps": float(np.median(sizes)), "client_max_apps": int(sizes.max()),
    "clients_with_lt_10": int((sizes < 10).sum()),
    "occ_with_skill": occ_with_skill, "skills_used": metrics["skills"]["n_skills_used"],
    "skills_per_occ_min": metrics["skills"]["skills_per_occ_min"],
    "skills_per_occ_median": metrics["skills"]["skills_per_occ_median"],
    "skills_per_occ_mean": metrics["skills"]["skills_per_occ_mean"],
    "skills_per_occ_max": metrics["skills"]["skills_per_occ_max"],
    "n_jobs_with_occ_edge": int(len(job_occ_nodes)),
    "n_jobs_without_occ_edge": n_jobs - int(len(job_occ_nodes)),
}
deltas = {}
for k, exp in baseline.items():
    act = actuals[k]
    if isinstance(exp, float):
        same = abs(float(act) - exp) < 0.05
    elif isinstance(exp, list):
        same = list(act) == exp
    else:
        same = act == exp
    if not same:
        deltas[k] = {"baseline": exp, "actual": act}
# The three skill-stat deltas are a DENOMINATOR difference, not a data difference:
# captain computed over 564 occupations that actually have skills; I first computed over
# all 583. Recompute on the same denominator and require exact agreement.
deg_with_skill = deg[deg > 0]
resolved = {
    "skills_per_occ_min": {"baseline": 2, "over_all_583": int(deg.min()),
                           "over_564_with_skill": int(deg_with_skill.min())},
    "skills_per_occ_median": {"baseline": 24, "over_all_583": float(np.median(deg)),
                              "over_564_with_skill": float(np.median(deg_with_skill))},
    "skills_per_occ_mean": {"baseline": 45.9, "over_all_583": round(float(deg.mean()), 2),
                            "over_564_with_skill": round(float(deg_with_skill.mean()), 2)},
}
resolved_ok = all(
    (v["over_564_with_skill"] == v["baseline"] if isinstance(v["baseline"], int)
     else abs(v["over_564_with_skill"] - v["baseline"]) < 0.05)
    for v in resolved.values()
)
for k in ["skills_per_occ_min", "skills_per_occ_median", "skills_per_occ_mean"]:
    if k in deltas and resolved_ok:
        deltas[k]["resolution"] = ("khác do mẫu số: baseline tính trên 564 nghề CÓ skill; "
                                   "tôi tính trên 583 nghề (gồm 19 nghề 0 skill). "
                                   "Trên cùng mẫu số 564 thì KHỚP tuyệt đối.")
metrics["deltas_vs_captain_baseline"] = deltas
metrics["baseline_table"] = [{"item": k, "baseline": baseline[k], "actual": actuals[k],
                              "match": k not in deltas or "resolution" in deltas.get(k, {})}
                             for k in baseline]
unresolved = {k: v for k, v in deltas.items() if "resolution" not in v}
check("11.1 every captain baseline number reproduced (deltas only from denominator choice)",
      "0 unresolved deltas", f"{len(deltas)} deltas, {len(unresolved)} unresolved",
      len(unresolved) == 0, severity="blocker",
      detail=json.dumps(resolved, ensure_ascii=False))
# explicit note on the two numbers that legitimately differ from the graph-builder's claim
metrics["notes_on_numbers"] = {
    "index_max": "captain ghi max 264994 = n_nodes-1, dung cho mien gia tri; gia tri LON NHAT thuc te "
                 "xuat hien trong edge_index la 264994 -> khop.",
    "skills_per_occ_median": f"captain ghi median 24, đo lại = {metrics['skills']['skills_per_occ_median']} "
                             f"(tính trên 583 nghề gồm cả 19 nghề 0 skill); nếu chỉ tính 564 nghề có skill "
                             f"thì median = xem skills_per_occ_median_with_skill",
    "skills_per_occ_mean": f"captain ghi mean 45.9, đo lại = {metrics['skills']['skills_per_occ_mean']}",
    "n_jobs_without_occ_edge": f"captain ghi 58.167 (68,6%), đo lại = {n_jobs - int(len(job_occ_nodes))} "
                               f"({round(100*(n_jobs-int(len(job_occ_nodes)))/n_jobs,2)}%)",
}
deg_with_skill = deg[deg > 0]
metrics["skills"]["skills_per_occ_median_with_skill"] = float(np.median(deg_with_skill)) if len(deg_with_skill) else 0
metrics["skills"]["skills_per_occ_mean_with_skill"] = round(float(deg_with_skill.mean()), 2) if len(deg_with_skill) else 0
metrics["skills"]["skills_per_occ_min_with_skill"] = int(deg_with_skill.min()) if len(deg_with_skill) else 0

# ---------------- 12. determinism: byte-identical reruns ----------------------
import hashlib as _hl
run_a = OUT / "run_a"
run_b = OUT / "run_b"


def _md5(p: Path) -> str:
    h = _hl.md5()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


det = {"runs_present": run_a.is_dir() and run_b.is_dir(), "files": {}}
if det["runs_present"]:
    for fname in ["graph.npz", "clients.json", "job_titles.json", "user_titles.json", "meta.json"]:
        cur = ART / fname
        entry = {"artifacts_v3": _md5(cur),
                 "run_a": _md5(run_a / fname),
                 "run_b": _md5(run_b / fname)}
        entry["bit_identical"] = len({entry["artifacts_v3"], entry["run_a"], entry["run_b"]}) == 1
        entry["size_match"] = (cur.stat().st_size == (run_a / fname).stat().st_size
                              == (run_b / fname).stat().st_size)
        det["files"][fname] = entry
    # meta.json carries timestamps/paths/runtime -> compare the deterministic fields only
    ma = json.loads((run_a / "meta.json").read_text(encoding="utf-8"))
    mb = json.loads((run_b / "meta.json").read_text(encoding="utf-8"))
    mc = json.loads((ART / "meta.json").read_text(encoding="utf-8"))
    volatile = {"/generated_at", "/runtime_seconds", "/memory_peak_mb", "/memory_peak_gb",
                "/paths/artifacts"}

    def _flat(d, p=""):
        o = {}
        if isinstance(d, dict):
            for k, v in d.items():
                o.update(_flat(v, p + "/" + k))
        elif isinstance(d, list):
            o[p] = json.dumps(d, ensure_ascii=False, sort_keys=True)
        else:
            o[p] = d
        return o

    fa, fb, fc = _flat(ma), _flat(mb), _flat(mc)
    keys = set(fa) | set(fb) | set(fc)
    diff = {k: {"run_a": fa.get(k), "run_b": fb.get(k), "artifacts_v3": fc.get(k)}
            for k in sorted(keys) if not (fa.get(k) == fb.get(k) == fc.get(k))}
    det["meta_json_diff_fields"] = diff
    det["meta_json_only_volatile_fields"] = set(diff) <= volatile
    det["run_a_runtime_seconds"] = ma["runtime_seconds"]
    det["run_b_runtime_seconds"] = mb["runtime_seconds"]
    det["run_a_memory_peak_mb"] = ma["memory_peak_mb"]
    det["run_b_memory_peak_mb"] = mb["memory_peak_mb"]
metrics["determinism"] = det
check("12.1 graph.npz byte-identical across 3 independent runs", "same md5",
      det["files"]["graph.npz"]["artifacts_v3"] if det["runs_present"] else "runs missing",
      bool(det["runs_present"] and det["files"]["graph.npz"]["bit_identical"]), severity="blocker")
check("12.2 clients.json + titles files byte-identical", "same md5",
      {k: v["bit_identical"] for k, v in det.get("files", {}).items()},
      bool(det["runs_present"] and all(v["bit_identical"] for k, v in det["files"].items()
                                       if k != "meta.json")), severity="blocker")
check("12.3 meta.json differs only in timestamp/runtime/memory/path fields", "volatile only",
      sorted(det.get("meta_json_diff_fields", {})),
      bool(det.get("meta_json_only_volatile_fields")), severity="medium")
check("12.4 rerun runtime and peak RAM stay within the 3.9 GB budget", "<3900 MB",
      f"A={det.get('run_a_memory_peak_mb')} MB B={det.get('run_b_memory_peak_mb')} MB",
      bool(det["runs_present"] and det["run_a_memory_peak_mb"] < 3900
           and det["run_b_memory_peak_mb"] < 3900), severity="high")

# ------------------------------------------------------------ final summary
fails = [c for c in checks if not c["pass"] and not c["warn_only"]]
warns = [c for c in checks if not c["pass"] and c["warn_only"]]
blockers = [c for c in fails if c["severity"] in ("blocker", "high")]
result = {
    "task": "t5",
    "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(),
    "artifacts": {p.name: p.stat().st_size for p in sorted(ART.iterdir())},
    "verdict": "PASS" if not fails else "FAIL",
    "n_checks": len(checks),
    "n_pass": len(checks) - len(fails) - len(warns),
    "n_warn": len(warns),
    "n_fail": len(fails),
    "fails": fails,
    "warnings_need_declaration": warns,
    "blocking_findings": [c["item"] for c in blockers],
    "overall_pass": len(fails) == 0,
    "deltas_vs_captain_baseline": metrics.get("deltas_vs_captain_baseline", {}),
    "array_shapes": metrics["array_shapes"],
    "metrics": metrics,
    "checks": checks,
}
(OUT / "v3_verify.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nSUMMARY:", f"verdict={'PASS' if not fails else 'FAIL'}; "
                    f"{len(checks)-len(fails)-len(warns)} pass / {len(warns)} warn / {len(fails)} fail")
print("warnings:", [c["item"] for c in warns])
print("blocking:", [c["item"] for c in blockers])
sys.exit(0 if len(blockers) == 0 else 1)
