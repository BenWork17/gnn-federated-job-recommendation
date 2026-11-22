"""Reproducible Local-only LightGCN evaluation on CareerBuilder + O*NET V3 (20N Fixed FL Catalog).

Matches the exact 20N Fixed FL Catalog protocol from `notebooks/_p1.py`..`_p4.py`
(`ablation_results.csv`):
  - Catalog: 4,511 train-seen jobs owned by the top 20 clients (by train edges)
  - Eval users: 800 sampled users (`np.random.default_rng(42).choice(..., 800, replace=False)`)
  - Model: LightGCN (`dim=32`, `layers=2`, `lr=0.05`, `reg=1e-5`, `local_epochs=1`, `rounds=4`, `seed=42`)
  - Bootstrap: 1,000 resamples (`seed=42`) for 95% CI

Compares:
  1. Local-only (Strict Silo Scoring): Each of the 20 clients trains independently
     on its own local subgraph (`include_occ=True, include_skill=True`) for 4 rounds
     x 20 Adam steps = 80 local steps with NO FedAvg parameter aggregation.
     At evaluation, client c scores only its owned jobs `client_of_job[j] == c`
     using its locally propagated embeddings `propagate(E_c, adj_c, layers=2)` for
     users present in client c's local subgraph (unobserved cross-silo users receive
     `-1e9` for client c's jobs).
  2. Local-only (Post-hoc Stitched Mean-User + Global Prop, upper-bound sensitivity):
     Same independently trained `E_c` (NO FedAvg during training), then for evaluation
     only, each user's embedding is averaged across clients observing that user,
     each job's embedding comes from its owning client `c`, and `full_forward`
     propagates once on `ADJ_FULL`.
  3. FedAvg (20N, 4 rounds): Exact reproduction check against `ablation_results.csv`
     (`R@20 = 0.4833`, `NDCG@20 = 0.3469`, `MRR@20 = 0.3150`).

Outputs `results_v3/local_only_v3.json`.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import torch

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "v3"
OUT = ROOT / "results_v3" / "local_only_v3.json"

DIM = 32
LAYERS = 2
LR = 0.05
REG_W = 1e-5
LOCAL_EPOCHS = 1
ROUNDS = 4
N_CLIENTS = 20
EVAL_USERS_N = 800
N_BOOT = 1000
SEED = 42


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_v3_graph():
    g = np.load(ART / "graph.npz", allow_pickle=False)
    edge_index = g["edge_index"].astype(np.int64)
    edge_type = g["edge_type"].astype(np.int16)
    train_mask = g["train_mask"].astype(bool)
    test_mask = g["test_mask"].astype(bool)
    n_nodes = int(g["n_nodes"])
    n_users = int(g["n_users"])
    n_jobs = int(g["n_jobs"])
    n_occ = int(g["n_occupations"])
    n_skill = int(g["n_skills"])
    offsets = [int(x) for x in g["offsets"]]
    client_of_job = g["client_of_job"].astype(np.int64)

    with open(ART / "clients.json", encoding="utf-8") as f:
        clients = json.load(f)

    return dict(
        edge_index=edge_index,
        edge_type=edge_type,
        train_mask=train_mask,
        test_mask=test_mask,
        n_nodes=n_nodes,
        n_users=n_users,
        n_jobs=n_jobs,
        n_occ=n_occ,
        n_skill=n_skill,
        offsets=offsets,
        client_of_job=client_of_job,
        n_clients_total=len(clients),
    )


def build_norm_adj_full(edge_index: np.ndarray, train_mask: np.ndarray, n_nodes: int):
    src = edge_index[0][train_mask]
    dst = edge_index[1][train_mask]
    row = np.concatenate([src, dst])
    col = np.concatenate([dst, src])
    A = sp.coo_matrix((np.ones(row.size, dtype=np.float32), (row, col)), shape=(n_nodes, n_nodes)).tocsr()
    A.sum_duplicates()
    A = A + sp.eye(n_nodes, dtype=np.float32, format="csr")
    deg = np.asarray(A.sum(1)).ravel()
    dinv = 1.0 / np.sqrt(np.maximum(deg, 1.0))
    M = (sp.diags(dinv) @ A @ sp.diags(dinv)).tocoo()
    return torch.sparse_coo_tensor(
        torch.from_numpy(np.vstack([M.row, M.col]).astype(np.int64)),
        torch.from_numpy(M.data.astype(np.float32)),
        (n_nodes, n_nodes),
    ).coalesce()


def norm_adj_local(le: np.ndarray, n: int):
    row = np.concatenate([le[0], le[1]])
    col = np.concatenate([le[1], le[0]])
    A = sp.coo_matrix((np.ones(row.size, dtype=np.float32), (row, col)), shape=(n, n)).tocsr()
    A.sum_duplicates()
    A = A + sp.eye(n, dtype=np.float32, format="csr")
    deg = np.asarray(A.sum(1)).ravel()
    dinv = 1.0 / np.sqrt(np.maximum(deg, 1.0))
    M = (sp.diags(dinv) @ A @ sp.diags(dinv)).tocoo()
    return torch.sparse_coo_tensor(
        torch.from_numpy(np.vstack([M.row, M.col]).astype(np.int64)),
        torch.from_numpy(M.data.astype(np.float32)),
        (n, n),
    ).coalesce()


def propagate(E: torch.Tensor, adj, layers: int) -> torch.Tensor:
    h = E
    acc = [E]
    for _ in range(layers):
        h = torch.sparse.mm(adj, h)
        acc.append(h)
    return torch.stack(acc).mean(0)


def bpr_loss_from_scores(pos: torch.Tensor, neg: torch.Tensor, reg_term: torch.Tensor, reg_w: float = REG_W) -> torch.Tensor:
    return -torch.nn.functional.logsigmoid(pos - neg).mean() + reg_w * reg_term


def prepare_shards_and_eval(data: dict):
    edge_index = data["edge_index"]
    edge_type = data["edge_type"]
    train_mask = data["train_mask"]
    test_mask = data["test_mask"]
    n_nodes = data["n_nodes"]
    n_users = data["n_users"]
    n_jobs = data["n_jobs"]
    n_occ = data["n_occ"]
    n_skill = data["n_skill"]
    o_u, o_j, o_o, o_s = data["offsets"]
    client_of_job = data["client_of_job"]
    n_clients_total = data["n_clients_total"]

    et_user_job, et_job_occ, et_occ_skill, et_user_occ = 0, 1, 2, 3
    m_tr = train_mask & (edge_type == et_user_job)
    m_te = test_mask & (edge_type == et_user_job)
    uj_tr_src = edge_index[0][m_tr]
    uj_tr_dst = edge_index[1][m_tr]
    uj_te_src = edge_index[0][m_te]
    uj_te_dst = edge_index[1][m_te]

    client_of_train_edge = client_of_job[uj_tr_dst - o_j]
    order_c = np.argsort(client_of_train_edge, kind="stable")
    e_u_sorted = uj_tr_src[order_c]
    e_j_sorted = uj_tr_dst[order_c]
    e_c_sorted = client_of_train_edge[order_c]
    slice_start = np.searchsorted(e_c_sorted, np.arange(n_clients_total), side="left")
    slice_end = np.searchsorted(e_c_sorted, np.arange(n_clients_total), side="right")
    client_train_edges = slice_end - slice_start

    m_job_occ = edge_type == et_job_occ
    m_occ_skill = edge_type == et_occ_skill
    m_user_occ = edge_type == et_user_occ

    occ_of_job = sp.csr_matrix(
        (np.ones(int(m_job_occ.sum()), dtype=np.float32), (edge_index[0][m_job_occ] - o_j, edge_index[1][m_job_occ] - o_o)),
        shape=(n_jobs, n_occ),
    )
    skill_of_occ = sp.csr_matrix(
        (np.ones(int(m_occ_skill.sum()), dtype=np.float32), (edge_index[0][m_occ_skill] - o_o, edge_index[1][m_occ_skill] - o_s)),
        shape=(n_occ, n_skill),
    )
    occ_of_user = sp.csr_matrix(
        (np.ones(int(m_user_occ.sum()), dtype=np.float32), (edge_index[0][m_user_occ] - o_u, edge_index[1][m_user_occ] - o_o)),
        shape=(n_users, n_occ),
    )

    occ_of_job_l = [occ_of_job.indices[occ_of_job.indptr[i]:occ_of_job.indptr[i + 1]] + o_o for i in range(n_jobs)]
    skill_of_occ_l = [skill_of_occ.indices[skill_of_occ.indptr[i]:skill_of_occ.indptr[i + 1]] + o_s for i in range(n_occ)]
    occ_of_user_l = [occ_of_user.indices[occ_of_user.indptr[i]:occ_of_user.indptr[i + 1]] + o_o for i in range(n_users)]

    ranked = np.argsort(-client_train_edges, kind="stable")
    selected_cids = ranked[:N_CLIENTS].tolist()

    shards = []
    for cid in selected_cids:
        a, b = slice_start[cid], slice_end[cid]
        uu = np.unique(e_u_sorted[a:b])
        jj = np.unique(e_j_sorted[a:b] - o_j)

        occ_set = set()
        for j in jj:
            occ_set.update(occ_of_job_l[j].tolist())
        for u in uu:
            occ_set.update(occ_of_user_l[u].tolist())
        occ_nodes = np.fromiter(occ_set, dtype=np.int64, count=len(occ_set))

        sk_set = set()
        for o in occ_nodes:
            sk_set.update(skill_of_occ_l[o - o_o].tolist())
        skill_nodes = np.fromiter(sk_set, dtype=np.int64, count=len(sk_set))

        nodes = np.concatenate([uu, jj + o_j, occ_nodes, skill_nodes]).astype(np.int64)
        n_local = nodes.size
        gmap = -np.ones(n_nodes, dtype=np.int64)
        gmap[nodes] = np.arange(n_local)

        keep = (gmap[edge_index[0]] >= 0) & (gmap[edge_index[1]] >= 0) & train_mask
        le = gmap[edge_index[:, keep]]

        is_u = nodes < n_users
        is_j = (nodes >= o_j) & (nodes < o_j + n_jobs)
        m_uj = is_u[le[0]] & is_j[le[1]]

        shards.append(
            dict(
                cid=int(cid),
                nodes=nodes,
                adj=norm_adj_local(le, n_local),
                lu=le[0][m_uj].astype(np.int64),
                lj=le[1][m_uj].astype(np.int64),
                n=n_local,
                nu=int(is_u.sum()),
                nj=int(is_j.sum()),
                n_occ=int(occ_nodes.size),
                n_skill=int(skill_nodes.size),
                w=float(m_uj.sum()),
                gmap=gmap,
            )
        )

    # Exact 20N Fixed FL Catalog & 800 eval users
    job_train_deg = np.bincount(uj_tr_dst - o_j, minlength=n_jobs)
    catalog_all = np.where(job_train_deg >= 1)[0]
    universe = np.where(np.isin(client_of_job, np.asarray(selected_cids)))[0]
    catalog_u = np.intersect1d(catalog_all, universe)
    assert catalog_u.size == 4511, f"Expected 4,511 jobs in 20N catalog, got {catalog_u.size}"

    pos_all = {}
    for u, j in zip(uj_te_src.tolist(), (uj_te_dst - o_j).tolist()):
        pos_all.setdefault(u, []).append(j)

    seen = {}
    for u, j in zip(uj_tr_src.tolist(), (uj_tr_dst - o_j).tolist()):
        seen.setdefault(u, []).append(j)

    pos_u = -np.ones(n_jobs, dtype=np.int64)
    pos_u[catalog_u] = np.arange(catalog_u.size)
    pos_map_u = {}
    for u, js in pos_all.items():
        sel_js = [int(pos_u[j]) for j in js if pos_u[j] >= 0]
        if sel_js:
            pos_map_u[u] = sel_js

    users_u = np.array(sorted(pos_map_u), dtype=np.int64)
    n_eval = int(min(EVAL_USERS_N, users_u.size))
    ev_u = np.sort(np.random.default_rng(SEED).choice(users_u, n_eval, replace=False))
    evp_u = [np.array(pos_map_u[int(u)], dtype=np.int64) for u in ev_u]

    return dict(
        shards=shards,
        selected_cids=selected_cids,
        catalog_u=catalog_u,
        ev_u=ev_u,
        evp_u=evp_u,
        seen=seen,
        pos_u=pos_u,
    )


def local_train_step(shard: dict, E_init_local: torch.Tensor, rounds_to_run: int, seed_base: int, continue_across_rounds: bool = True):
    """Train one client locally.

    When `continue_across_rounds=True`, the client runs `rounds_to_run` sequential
    rounds (each 20 Adam steps, matching FedAvg's step budget per round) on its own
    local embedding matrix with NO server aggregation between rounds.
    """
    lu = torch.from_numpy(shard["lu"])
    lj = torch.from_numpy(shard["lj"])
    adj = shard["adj"]
    n = shard["n"]

    E = torch.nn.Parameter(E_init_local.detach().clone())
    n_edges_local = int(lu.numel())
    losses = []
    latencies_ms = []

    for rnd in range(1, rounds_to_run + 1):
        t0 = time.perf_counter()
        opt = torch.optim.Adam([E], lr=LR)
        gen = torch.Generator().manual_seed(seed_base * 1000 + rnd)
        if n_edges_local > 4096:
            sel = torch.randperm(n_edges_local, generator=gen)[:4096]
            lu_b, lj_b = lu[sel], lj[sel]
        else:
            lu_b, lj_b = lu, lj

        n_steps = int(max(20, min(100, 20 * LOCAL_EPOCHS)))
        last_loss = 0.0
        for _ in range(n_steps):
            out = propagate(E, adj, LAYERS)
            eu = out[lu_b]
            pos = (eu * out[lj_b]).sum(1)
            neg_idx = torch.randint(0, n, (lu_b.numel(),), generator=gen)
            neg = (eu * out[neg_idx]).sum(1)
            loss = bpr_loss_from_scores(pos, neg, E.pow(2).mean())
            opt.zero_grad()
            loss.backward()
            opt.step()
            last_loss = float(loss.detach())
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        losses.append(last_loss)

    with torch.no_grad():
        out_local = propagate(E.detach(), adj, LAYERS)
    return E.detach(), out_local, losses, latencies_ms


def fedavg_train(shards: list, n_nodes: int, adj_full) -> tuple[torch.Tensor, float, list]:
    """Reproduce exact 20N FedAvg (4 rounds) from `notebooks/_p2.py` + `_p4.py`."""
    set_seed(SEED)
    E_global = torch.randn(n_nodes, DIM) * 0.1
    t0 = time.perf_counter()
    latencies_ms = []

    for rnd in range(1, ROUNDS + 1):
        num = torch.zeros(n_nodes, DIM)
        den = torch.zeros(n_nodes)
        for sh in shards:
            tc = time.perf_counter()
            lu = torch.from_numpy(sh["lu"])
            lj = torch.from_numpy(sh["lj"])
            adj = sh["adj"]
            n = sh["n"]
            E0 = E_global[sh["nodes"]].detach().clone()
            E = torch.nn.Parameter(E0.clone())
            opt = torch.optim.Adam([E], lr=LR)
            gen = torch.Generator().manual_seed(SEED * 1000 + rnd)
            n_edges_local = int(lu.numel())
            if n_edges_local > 4096:
                sel = torch.randperm(n_edges_local, generator=gen)[:4096]
                lu_b, lj_b = lu[sel], lj[sel]
            else:
                lu_b, lj_b = lu, lj
            n_steps = int(max(20, min(100, 20 * LOCAL_EPOCHS)))
            for _ in range(n_steps):
                out = propagate(E, adj, LAYERS)
                eu = out[lu_b]
                pos = (eu * out[lj_b]).sum(1)
                neg_idx = torch.randint(0, n, (lu_b.numel(),), generator=gen)
                neg = (eu * out[neg_idx]).sum(1)
                loss = bpr_loss_from_scores(pos, neg, E.pow(2).mean())
                opt.zero_grad()
                loss.backward()
                opt.step()
            latencies_ms.append((time.perf_counter() - tc) * 1000.0)
            w = sh["w"]
            idx = torch.from_numpy(sh["nodes"])
            num.index_add_(0, idx, E.detach() * w)
            den.index_add_(0, idx, torch.full((n,), float(w)))
        touched = den > 0
        E_global = E_global.clone()
        E_global[touched] = num[touched] / den[touched][:, None]

    with torch.no_grad():
        E_prop = propagate(E_global.detach(), adj_full, LAYERS)
    dt = time.perf_counter() - t0
    return E_prop, dt, latencies_ms


def compute_metrics_from_scores(sc: np.ndarray, users: np.ndarray, pos_list: list, catalog: np.ndarray, seen: dict, n_jobs: int):
    pos_of_catalog = -np.ones(n_jobs, dtype=np.int64)
    pos_of_catalog[catalog] = np.arange(catalog.size)
    for r, u in enumerate(users.tolist()):
        idx = [pos_of_catalog[j] for j in seen.get(u, []) if pos_of_catalog[j] >= 0]
        if idx:
            sc[r, idx] = -np.inf

    idcg = np.zeros(64)
    for k in range(1, 64):
        idcg[k] = (1.0 / np.log2(np.arange(2, 2 + min(k, 20)))).sum()

    n_cat = catalog.size
    n = sc.shape[0]
    out = {"recall@10": np.full(n, np.nan), "recall@20": np.full(n, np.nan), "ndcg@20": np.full(n, np.nan), "mrr@20": np.full(n, np.nan)}
    top1 = np.zeros(n, dtype=np.int64)
    topm = 64
    for r in range(n):
        s = sc[r]
        pos = pos_list[r]
        if pos.size == 0:
            continue
        cand = np.argpartition(-s, topm)[: topm + 1]
        cand = cand[np.argsort(-s[cand])]
        rank = np.full(n_cat, 10**6, dtype=np.int64)
        rank[cand] = np.arange(cand.size)
        pr = rank[pos]
        out["recall@10"][r] = float((pr < 10).mean())
        out["recall@20"][r] = float((pr < 20).mean())
        dcg = (1.0 / np.log2(pr[pr < 20] + 2)).sum()
        out["ndcg@20"][r] = dcg / max(idcg[min(pos.size, 20)], 1e-9)
        out["mrr@20"][r] = 0.0 if (pr >= 20).all() else 1.0 / (pr.min() + 1)
        top1[r] = catalog[cand[0]]

    def bootstrap_ci(vec: np.ndarray, n_boot: int = N_BOOT, alpha: float = 0.05, seed: int = SEED):
        v = np.asarray(vec, dtype=np.float64)
        v = v[~np.isnan(v)]
        rng = np.random.default_rng(seed)
        means = np.empty(n_boot)
        for i in range(n_boot):
            means[i] = v[rng.integers(0, v.size, v.size)].mean()
        return [round(float(np.percentile(means, 100 * alpha / 2)), 4), round(float(np.percentile(means, 100 * (1 - alpha / 2))), 4)]

    summary = {
        "recall@10": round(float(np.nanmean(out["recall@10"])), 4),
        "recall@20": round(float(np.nanmean(out["recall@20"])), 4),
        "ndcg@20": round(float(np.nanmean(out["ndcg@20"])), 4),
        "mrr@20": round(float(np.nanmean(out["mrr@20"])), 4),
        "coverage@10": round(float(len(set(top1[top1 >= 0].tolist())) / n_cat), 4),
    }
    for key in ("recall@10", "recall@20", "ndcg@20", "mrr@20"):
        summary[f"{key}_ci95"] = bootstrap_ci(out[key])
    return summary


def main():
    t_all = time.perf_counter()
    set_seed(SEED)
    data = load_v3_graph()
    prep = prepare_shards_and_eval(data)
    shards = prep["shards"]
    catalog_u = prep["catalog_u"]
    ev_u = prep["ev_u"]
    evp_u = prep["evp_u"]
    seen = prep["seen"]
    o_j = data["offsets"][1]
    n_nodes = data["n_nodes"]
    n_jobs = data["n_jobs"]
    client_of_job = data["client_of_job"]

    # 1. Local-only LightGCN: independent training per client, NO FedAvg aggregation
    set_seed(SEED)
    E_init = torch.randn(n_nodes, DIM) * 0.1

    t_loc = time.perf_counter()
    local_raw = {}
    local_prop = {}
    all_lat_ms = []
    client_losses = []
    for sh in shards:
        cid = sh["cid"]
        E_c, out_c, losses_c, lat_c = local_train_step(
            sh,
            E_init[sh["nodes"]],
            rounds_to_run=ROUNDS,
            seed_base=SEED,
        )
        local_raw[cid] = E_c
        local_prop[cid] = out_c.cpu().numpy()
        all_lat_ms.extend(lat_c)
        client_losses.append(losses_c[-1])
    local_train_sec = time.perf_counter() - t_loc

    # Rule A (Primary): Strict Silo Scoring (no parameter sharing, no global ADJ_FULL)
    # Each client c scores only its owned jobs (client_of_job[j] == c) for users
    # present in client c's local subgraph. Unobserved user-client pairs get -1e9.
    sc_strict = np.full((ev_u.size, catalog_u.size), -1e9, dtype=np.float32)
    cat_cids = client_of_job[catalog_u]
    shard_by_cid = {sh["cid"]: sh for sh in shards}

    observed_user_client_pairs = 0
    users_with_any_local_obs = 0
    users_with_positive_in_observed_client = 0

    # Pre-map catalog positions per client
    cat_indices_by_cid = {sh["cid"]: np.where(cat_cids == sh["cid"])[0] for sh in shards}
    cat_local_j_by_cid = {}
    for sh in shards:
        cid = sh["cid"]
        c_idx = cat_indices_by_cid[cid]
        gmap = sh["gmap"]
        cat_local_j_by_cid[cid] = gmap[o_j + catalog_u[c_idx]]

    for r, u in enumerate(ev_u.tolist()):
        has_obs = False
        obs_cids = set()
        for sh in shards:
            cid = sh["cid"]
            lu_idx = sh["gmap"][u]
            if lu_idx >= 0:
                has_obs = True
                observed_user_client_pairs += 1
                obs_cids.add(cid)
                c_idx = cat_indices_by_cid[cid]
                if c_idx.size > 0:
                    lj_idx = cat_local_j_by_cid[cid]
                    u_vec = local_prop[cid][lu_idx]
                    j_mat = local_prop[cid][lj_idx]
                    sc_strict[r, c_idx] = j_mat @ u_vec
        if has_obs:
            users_with_any_local_obs += 1
        pos_cids = set(client_of_job[catalog_u[evp_u[r]]].tolist())
        if not obs_cids.isdisjoint(pos_cids):
            users_with_positive_in_observed_client += 1

    strict_metrics = compute_metrics_from_scores(sc_strict.copy(), ev_u, evp_u, catalog_u, seen, n_jobs)

    # Rule B (Sensitivity): Post-hoc stitched client-owned embeddings + mean user embedding
    # across observed clients + single full_forward on ADJ_FULL (still NO FedAvg during training).
    adj_full = build_norm_adj_full(data["edge_index"], data["train_mask"], n_nodes)
    num = torch.zeros(n_nodes, DIM)
    den = torch.zeros(n_nodes)
    for sh in shards:
        cid = sh["cid"]
        idx = torch.from_numpy(sh["nodes"])
        num.index_add_(0, idx, local_raw[cid])
        den.index_add_(0, idx, torch.ones(sh["n"]))
    E_stitched = E_init.clone()
    touched = den > 0
    E_stitched[touched] = num[touched] / den[touched][:, None]
    with torch.no_grad():
        E_stitched_prop = propagate(E_stitched, adj_full, LAYERS).cpu().numpy()
    sc_stitched = E_stitched_prop[ev_u] @ E_stitched_prop[o_j + catalog_u].T
    stitched_metrics = compute_metrics_from_scores(sc_stitched.copy(), ev_u, evp_u, catalog_u, seen, n_jobs)

    # 2. Quick reproduction check: FedAvg (20N, 4 rounds) on exact same setup
    E_fedavg_prop, fedavg_sec, fedavg_lat_ms = fedavg_train(shards, n_nodes, adj_full)
    E_fedavg_np = E_fedavg_prop.cpu().numpy()
    sc_fedavg = E_fedavg_np[ev_u] @ E_fedavg_np[o_j + catalog_u].T
    fedavg_metrics = compute_metrics_from_scores(sc_fedavg.copy(), ev_u, evp_u, catalog_u, seen, n_jobs)

    payload = {
        "experiment": "Local-only LightGCN vs FedAvg (20N Fixed FL Catalog)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "environment": {
            "device": "cpu",
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "torch": torch.__version__,
        },
        "config": {
            "n_clients": N_CLIENTS,
            "n_catalog": int(catalog_u.size),
            "n_eval_users": int(ev_u.size),
            "dim": DIM,
            "layers": LAYERS,
            "lr": LR,
            "reg": REG_W,
            "local_epochs": LOCAL_EPOCHS,
            "rounds": ROUNDS,
            "total_local_steps_per_client": ROUNDS * max(20, min(100, 20 * LOCAL_EPOCHS)),
            "seed": SEED,
            "n_boot": N_BOOT,
        },
        "silo_cross_client_stats": {
            "eval_users_with_ge1_train_edge_in_20N": int(users_with_any_local_obs),
            "eval_users_with_test_positive_in_seen_client": int(users_with_positive_in_observed_client),
            "pct_eval_users_cross_silo_only": round(100.0 * (1.0 - users_with_positive_in_observed_client / ev_u.size), 2),
            "avg_seen_clients_per_eval_user_in_20N": round(observed_user_client_pairs / ev_u.size, 3),
        },
        "evaluation_rules": {
            "local_only_strict_silo": (
                "Primary Local-only rule (no FedAvg aggregation, no global graph propagation). "
                "Each of the 20 clients trains its own local subgraph E_c independently for 4 rounds x 20 Adam steps = 80 steps "
                "(continuing locally without server averaging) and produces local propagated embeddings out_c = propagate(E_c, adj_c, L=2). "
                "For eval user u and catalog job j owned by client c = client_of_job[j], score(u, j) = out_c[u] @ out_c[j] if u appears in client c's local subgraph, "
                "and -1e9 if client c has never observed u (cannot transfer preferences across silos without FL aggregation)."
            ),
            "local_only_stitched_eval_upper_bound": (
                "Sensitivity check (no FedAvg during training, post-hoc stitched eval only). "
                "Uses the exact same independently trained E_c matrices, stitches client embeddings by averaging nodes across clients that observed them, "
                "and runs full_forward once on ADJ_FULL at evaluation time. Included to isolate training-time aggregation vs eval-time cross-silo propagation."
            ),
        },
        "results": {
            "local_only_strict_silo": {
                **strict_metrics,
                "train_seconds": round(local_train_sec, 2),
                "mean_final_loss": round(float(np.mean(client_losses)), 6),
                "latency_p50_ms": round(float(np.percentile(all_lat_ms, 50)), 2),
            },
            "local_only_stitched_upper_bound": {
                **stitched_metrics,
                "train_seconds": round(local_train_sec, 2),
            },
            "fedavg_20n_repro": {
                **fedavg_metrics,
                "train_seconds": round(fedavg_sec, 2),
                "latency_p50_ms": round(float(np.percentile(fedavg_lat_ms, 50)), 2),
            },
        },
        "total_script_seconds": round(time.perf_counter() - t_all, 2),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Saved {OUT} in {payload['total_script_seconds']}s")
    print("Local-only (strict silo):", json.dumps(payload["results"]["local_only_strict_silo"], indent=2))
    print("Local-only (stitched upper):", json.dumps(payload["results"]["local_only_stitched_upper_bound"], indent=2))
    print("FedAvg (20N repro):", json.dumps(payload["results"]["fedavg_20n_repro"], indent=2))


if __name__ == "__main__":
    main()
