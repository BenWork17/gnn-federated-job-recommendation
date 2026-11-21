# %% [markdown]
# ## [7f] Đánh giá tách nhóm client — vì phân bố client rất lệch
#
# FedAvg bị **chi phối bởi client lớn**: max 4.320 cạnh train gấp **864 lần** min 5
# cạnh. Nếu chỉ báo trung bình toàn cục, con số bị kéo bởi vài client lớn và **không
# phản ánh chất lượng trên client nhỏ**.
#
# Vì vậy R@20 được báo **tách hai nhóm**: client **≥10 job** và client **<10 job**
# (418 client chỉ có **1 job**; 3.877 client có **≤3 job**).
#
# ⚠️ Đồng thời phải nói rõ: **2.096 client (23,0%)** không có cạnh test nào, nên
# metric per-client chỉ phủ **~7.020 client** trên 9.116 — không phải toàn bộ.

# %%
# ============================================================================
# [7g] R@20 theo nhóm client (chỉ trên client CÓ cạnh test)
# ============================================================================
T7d = time.perf_counter()

# --- client của từng cạnh test (theo JOB, silo thật) ---
client_of_test_edge = CLIENT_OF_JOB[uj_te_dst - O_J]
clients_with_test = np.unique(client_of_test_edge)
print(f"Client có ≥1 cạnh test: {clients_with_test.size:,}/{N_CLIENTS_TOTAL:,} "
      f"({100 * clients_with_test.size / N_CLIENTS_TOTAL:.1f}%)")
print(f"Client KHÔNG có test  : {N_CLIENTS_TOTAL - clients_with_test.size:,} "
      f"({100 * (N_CLIENTS_TOTAL - clients_with_test.size) / N_CLIENTS_TOTAL:.1f}%) "
      f"— không tính được metric per-client")
client_jobs_all = np.array([c["n_jobs"] for c in CLIENTS], dtype=np.int64)
big_clients = set(np.where(client_jobs_all >= 10)[0].tolist())
print(f"Client ≥10 job: {len(big_clients):,} | <10 job: {N_CLIENTS_TOTAL - len(big_clients):,}")


def per_client_recall20(E, max_users_per_client: int = 300, seed: int = 42) -> dict:
    """R@20 trung bình theo client, tách nhóm ≥10 job và <10 job."""
    E = E.detach().cpu().numpy() if torch.is_tensor(E) else E
    if E.shape[0] == N_NODES:
        get_u = lambda arr: E[arr]
        get_j = lambda arr: E[O_J + arr]
    else:
        get_u = lambda arr: E[arr]
        get_j = lambda arr: E[N_USERS + arr]
    rng = np.random.default_rng(seed)
    by_group = {"big": [], "small": []}
    per_client = {}
    for cid in clients_with_test.tolist():
        m = client_of_test_edge == cid
        us = np.unique(uj_te_src[m])
        if us.size == 0:
            continue
        if us.size > max_users_per_client:
            us = np.sort(rng.choice(us, max_users_per_client, replace=False))
        # catalog = các job có ≥1 cạnh train
        users_pos = []
        for u in us.tolist():
            ps = [j for j in POS_ALL.get(u, []) if CATALOG_POS[j] >= 0]
            if ps:
                users_pos.append((u, ps))
        if not users_pos:
            continue
        U = np.array([x[0] for x in users_pos])
        sc = get_u(U) @ get_j(CATALOG).T
        rec = []
        for r, (u, ps) in enumerate(users_pos):
            idx = [CATALOG_POS[j] for j in SEEN.get(u, []) if CATALOG_POS[j] >= 0]
            if idx:
                sc[r, idx] = -np.inf
            top = np.argpartition(-sc[r], 20)[:21]
            rank = np.full(CATALOG.size, 10 ** 6, dtype=np.int64)
            rank[top] = np.argsort(-sc[r][top])
            pr = rank[[CATALOG_POS[j] for j in ps]]
            rec.append(float((pr < 20).mean()))
        val = float(np.mean(rec))
        per_client[cid] = dict(recall20=val, n_users=len(users_pos),
                               n_jobs=int(client_jobs_all[cid]))
        by_group["big" if cid in big_clients else "small"].append(val)
    return dict(per_client=per_client, big=by_group["big"], small=by_group["small"])


FL_PERCLIENT = per_client_recall20(FL_E)
print("\n=== R@20 TÁCH NHÓM CLIENT (trung bình theo client, không theo user) ===")
for gname, label in [("big", "client ≥10 job"), ("small", "client <10 job")]:
    arr = np.array(FL_PERCLIENT[gname])
    if arr.size:
        lo, hi = bootstrap_ci(arr, seed=7)
        print(f"{label:16s}: n={arr.size:5,} client | R@20 = {arr.mean():.4f} "
              f"[{lo:.4f}, {hi:.4f}] | median {np.median(arr):.4f}")
    else:
        print(f"{label:16s}: không có client nào")
print(f"{'tất cả':16s}: n={len(FL_PERCLIENT['big']) + len(FL_PERCLIENT['small']):5,} client "
      f"(trên {N_CLIENTS_TOTAL:,} client, phần còn lại không có cạnh test)")

fig, ax = plt.subplots(1, 1, figsize=(7, 4))
data = [np.array(FL_PERCLIENT["big"]), np.array(FL_PERCLIENT["small"])]
labels = [f"≥10 job\n(n={data[0].size:,})", f"<10 job\n(n={data[1].size:,})"]
if data[0].size and data[1].size:
    ax.boxplot([d[~np.isnan(d)] for d in data], tick_labels=labels, showmeans=True)
    ax.set_ylabel("Recall@20 theo client")
    ax.set_title("Phân bố R@20 tách nhóm client — FedAvg bị chi phối bởi client lớn")
    ax.grid(alpha=.3, axis="y")
    fig.tight_layout()
    grp_path = os.path.join(FIG, "F06_r20_theo_nhom_client.png")
    fig.savefig(grp_path, dpi=160, bbox_inches="tight")
    print("Đã lưu hình:", grp_path)
plt.close(fig)
mark("[7f] Tách nhóm client", T7d, f"{len(FL_PERCLIENT['per_client']):,} client có test")

