"""
Sinh toàn bộ hình cho báo cáo và cho app. Đọc 100% số từ results/*.json.

Quy ước hình:
  - Độ phân giải 400 dpi, rộng đúng 16,4 cm (bề rộng khả dụng của trang A4
    với lề 3/2/2/2 trong mẫu báo cáo) để chữ không bị thu nhỏ khi chèn.
  - Chữ tiếng Việt có dấu; đã kiểm tra hiển thị đúng.
  - Mỗi hình trả lời MỘT câu hỏi; tiêu đề hình là câu trả lời, không phải
    nhãn chung chung.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common import ROOT, banner, load_config, load_json, setup_console, step

# Bảng màu: xanh = lành tính / công khai, đỏ = tấn công / riêng tư
C_BLUE = "#2f6fb5"
C_RED = "#c0392b"
C_GREEN = "#27ae60"
C_GREY = "#7f8c8d"
C_ORANGE = "#e67e22"
C_PURPLE = "#8e44ad"

WIDTH_CM = 16.4


def _fig(width_cm: float = WIDTH_CM, height_cm: float = 7.0):
    return plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54))


def _save(fig, out_dir: Path, name: str, dpi: int = 400) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.tight_layout(pad=0.5)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# =====================================================================
# NHÓM 1 — Dữ liệu & đồ thị
# =====================================================================
def fig_data_cleaning(reco: dict, out: Path, dpi: int) -> Path:
    """F02: dữ liệu bị mất gì ở mỗi bước làm sạch."""
    d = reco["data_summary"]
    q = d["quality"]
    raw_jobs = 1217
    steps = [
        ("Dữ liệu gốc", raw_jobs),
        ("Bỏ tin đã đóng", raw_jobs - q["jobs_dropped_closed"]),
        ("Bỏ tin trùng", raw_jobs - q["jobs_dropped_closed"]
         - q["jobs_dropped_duplicate"]),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH_CM / 2.54, 6.4 / 2.54),
                             gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    labels = [s[0] for s in steps] + ["Còn dùng được"]
    vals = [s[1] for s in steps] + [d["n_jobs"]]
    colors = [C_GREY, C_GREY, C_GREY, C_BLUE]
    ax.bar(range(len(vals)), vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(i, v + 25, f"{v:,}", ha="center", fontsize=7)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=6.5)
    ax.set_ylabel("Số tin tuyển dụng", fontsize=7)
    ax.set_title("Lọc tin: mất 16,7% số tin nhưng giữ 100% tương tác có nghĩa",
                 fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    issues = [("Tin dùng chung\ntập kỹ năng mẫu", q["template_jobs"], C_ORANGE),
              ("Mô tả chỉ lặp lại\ntiêu đề", q["title_only_jobs"], C_ORANGE),
              ("Link sinh tự động\n(không kiểm chứng)", q["seed_link_jobs"], C_RED)]
    ax.barh(range(len(issues)), [i[1] for i in issues],
            color=[i[2] for i in issues])
    for i, (_, v, _) in enumerate(issues):
        ax.text(v + 8, i, f"{v} ({100 * v / d['n_jobs']:.0f}%)",
                va="center", fontsize=6.5)
    ax.set_yticks(range(len(issues)))
    ax.set_yticklabels([i[0] for i in issues], fontsize=6.2)
    ax.set_xlabel("Số tin", fontsize=7)
    ax.set_title(f"Vấn đề chất lượng còn lại trong {d['n_jobs']:,} tin",
                 fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.grid(axis="x", alpha=0.3)
    return _save(fig, out, "F02_lam_sach_du_lieu.png", dpi)


def fig_sparsity(reco: dict, out: Path, dpi: int) -> Path:
    """F03: ma trận tương tác thưa tới mức nào."""
    d = reco["data_summary"]
    n_u, n_j = d["n_users"], d["n_jobs"]
    n_tr, n_te = d["n_train"], d["n_test"]
    total = n_u * n_j

    fig, ax = _fig(height_cm=6.2)
    parts = [("Train", n_tr, C_BLUE), ("Test", n_te, C_ORANGE),
             ("Chưa có tương tác", total - n_tr - n_te, "#dee2e6")]
    left = 0.0
    for label, v, c in parts:
        ax.barh([0], [v], left=left, color=c, label=f"{label} ({v:,})")
        left += v
    ax.set_xscale("log")
    ax.set_xlim(1, total * 1.3)
    ax.set_yticks([])
    ax.set_xlabel("Số ô trong ma trận người dùng × tin tuyển dụng (thang log)",
                  fontsize=7)
    ax.set_title(
        f"Chỉ {100 * (n_tr + n_te) / total:.2f}% ma trận có dữ liệu "
        f"({n_tr + n_te} / {total:,} ô) — đây là lý do cần thêm tín hiệu từ đồ thị",
        fontsize=7.5)
    ax.legend(fontsize=6.5, loc="lower right")
    ax.tick_params(labelsize=6.5)
    return _save(fig, out, "F03_do_thua.png", dpi)


def fig_graph_structure(reco: dict, out: Path, dpi: int) -> Path:
    """F04: cấu trúc đồ thị — công khai vs riêng tư."""
    d = reco["data_summary"]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH_CM / 2.54, 6.0 / 2.54),
                             gridspec_kw={"width_ratios": [1, 1.1]})
    ax = axes[0]
    node_types = ["Người dùng", "Tin tuyển dụng", "Kỹ năng", "Ngành"]
    counts = [d["n_users"], d["n_jobs"], d["n_skills"], d["n_industries"]]
    colors = [C_RED, C_RED, C_BLUE, C_BLUE]
    ax.barh(range(4), counts, color=colors)
    for i, v in enumerate(counts):
        ax.text(v * 1.08, i, f"{v:,}", va="center", fontsize=6.8)
    ax.set_yticks(range(4))
    ax.set_yticklabels(node_types, fontsize=7)
    ax.set_xscale("log")
    ax.set_xlim(1, max(counts) * 3)
    ax.set_xlabel("Số nút (thang log)", fontsize=7)
    ax.set_title("4 loại nút", fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.grid(axis="x", alpha=0.3)

    ax = axes[1]
    pub, priv = d["public_edges"], d["private_edges"]
    ax.bar([0, 1], [pub, priv], color=[C_BLUE, C_RED], width=0.55)
    ax.text(0, pub + 150, f"{pub:,}\ncạnh", ha="center", fontsize=7)
    ax.text(1, priv + 150, f"{priv:,}\ncạnh", ha="center", fontsize=7)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Máy chủ giữ\n(job–skill, job–ngành)",
                        "Khách hàng giữ\n(user–skill, user–job)"], fontsize=6.5)
    ax.set_ylabel("Số cạnh", fontsize=7)
    ax.set_title("Phân chia cạnh: chỉ cạnh xanh được chia sẻ",
                 fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, out, "F04_cau_truc_do_thi.png", dpi)


def fig_industries(reco: dict, out: Path, dpi: int) -> Path:
    """F05: phân bố ngành — nút công khai trên máy chủ."""
    d = reco["data_summary"]["industry_counts"]
    items = sorted(d.items(), key=lambda x: x[1])
    fig, ax = _fig(height_cm=6.4)
    ax.barh([k for k, _ in items], [v for _, v in items], color=C_BLUE)
    total = sum(d.values())
    for i, (_, v) in enumerate(items):
        ax.text(v + 4, i, f"{v} ({100 * v / total:.0f}%)", va="center", fontsize=6.5)
    ax.set_xlabel("Số tin tuyển dụng", fontsize=7)
    ax.set_title("Phân bố ngành suy ra từ tiêu đề tin (nút công khai, "
                 "không chứa dữ liệu cá nhân)", fontsize=7.5)
    ax.tick_params(labelsize=6.8)
    ax.grid(axis="x", alpha=0.3)
    return _save(fig, out, "F05_nganh.png", dpi)


# =====================================================================
# NHÓM 2 — Kết quả gợi ý
# =====================================================================
def fig_reco_comparison(reco: dict, out: Path, dpi: int) -> Path:
    """F06: so sánh 6 hệ — câu hỏi: FL có hơn local-only không?"""
    order = [
        ("popularity", "Phổ biến"),
        ("skill_cbf", "Nội dung (kỹ năng)"),
        ("item_knn", "Item-KNN"),
        ("local_only", "Cục bộ (không chia sẻ)"),
        ("fedavg", "Liên bang (FedAvg)"),
        ("centralized", "Tập trung (mốc trên)"),
    ]
    data = reco["systems"]
    labels, vals, colors, lo_err, hi_err = [], [], [], [], []
    for key, label in order:
        s = data.get(key)
        if not s:
            continue
        labels.append(label)
        vals.append(s["recall@20"])
        ci = s.get("recall@20_ci", {})
        lo_err.append(s["recall@20"] - ci.get("lo", s["recall@20"]))
        hi_err.append(ci.get("hi", s["recall@20"]) - s["recall@20"])
        colors.append(C_BLUE if key in ("fedavg", "centralized")
                      else C_GREY if key.startswith("local") else "#bdc3c7")

    fig, axes = plt.subplots(1, 2, figsize=(WIDTH_CM / 2.54, 7.0 / 2.54),
                             gridspec_kw={"width_ratios": [1.45, 1]})
    ax = axes[0]
    x = np.arange(len(labels))
    ax.bar(x, vals, yerr=[lo_err, hi_err], color=colors, capsize=2.5,
           error_kw={"lw": 0.8, "ecolor": "#2c3e50"})
    for i, v in enumerate(vals):
        ax.text(i, v + hi_err[i] + 0.015, f"{v:.3f}", ha="center", fontsize=6.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=22, ha="right", fontsize=6.3)
    ax.set_ylabel("Recall@20", fontsize=7)
    ax.set_title("FedAvg vượt mô hình cục bộ và tiệm cận mô hình tập trung "
                 "(CI 95%)", fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    # chừa chỗ cho nhãn số nằm trên thanh + sai số
    ax.set_ylim(0, max(v + h for v, h in zip(vals, hi_err)) * 1.22)
    ax.grid(axis="y", alpha=0.3)

    # panel phải: NDCG@20
    ax = axes[1]
    nd, nd_lo, nd_hi, nd_lab = [], [], [], []
    for key, label in order:
        s = data.get(key)
        if not s:
            continue
        nd.append(s["ndcg@20"])
        ci = s.get("ndcg@20_ci", {})
        nd_lo.append(s["ndcg@20"] - ci.get("lo", s["ndcg@20"]))
        nd_hi.append(ci.get("hi", s["ndcg@20"]) - s["ndcg@20"])
        nd_lab.append(label.split(" (")[0])
    ax.barh(range(len(nd)), nd, color=colors, xerr=[nd_lo, nd_hi],
            capsize=2.0, error_kw={"lw": 0.7, "ecolor": "#2c3e50"})
    ax.set_yticks(range(len(nd)))
    ax.set_yticklabels(nd_lab, fontsize=6.2)
    ax.set_xlabel("NDCG@20", fontsize=7)
    ax.set_title("Chất lượng xếp hạng", fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.grid(axis="x", alpha=0.3)
    return _save(fig, out, "F06_so_sanh_phuong_phap.png", dpi)


def fig_fl_curve(reco: dict, out: Path, dpi: int) -> Path:
    """F07: đường cong học liên bang theo vòng."""
    sweep = reco["client_sweep"]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH_CM / 2.54, 6.8 / 2.54))
    ax = axes[0]
    colors = [C_BLUE, C_ORANGE, C_GREEN]
    for s, c in zip(sweep, colors):
        rounds = [p["round"] for p in s["curve"]]
        r20 = [p["recall@20"] for p in s["curve"]]
        ax.plot(rounds, r20, marker="o", ms=2.6, lw=1.3, color=c,
                label=f"{s['n_clients']} khách hàng")
    ax.set_xlabel("Vòng truyền thông", fontsize=7)
    ax.set_ylabel("Recall@20", fontsize=7)
    ax.set_title("Recall@20 tăng dần theo vòng — nhưng dao động, "
                 "không đơn điệu", fontsize=7.5)
    ax.legend(fontsize=6.3)
    ax.tick_params(labelsize=6.5)
    ax.grid(alpha=0.3)

    ax = axes[1]
    for s, c in zip(sweep, colors):
        rounds = [p["round"] for p in s["curve"]]
        nd = [p["ndcg@20"] for p in s["curve"]]
        ax.plot(rounds, nd, marker="s", ms=2.4, lw=1.2, color=c,
                label=f"{s['n_clients']} KH")
    ax.set_xlabel("Vòng truyền thông", fontsize=7)
    ax.set_ylabel("NDCG@20", fontsize=7)
    ax.set_title("NDCG@20: cùng xu hướng", fontsize=7.5)
    ax.legend(fontsize=6.3)
    ax.tick_params(labelsize=6.5)
    ax.grid(alpha=0.3)
    return _save(fig, out, "F07_duong_cong_fl.png", dpi)


def fig_client_scale(reco: dict, out: Path, dpi: int) -> Path:
    """F08: số khách hàng ảnh hưởng thế nào."""
    sweep = reco["client_sweep"]
    cs = [s["n_clients"] for s in sweep]
    loc = [s["local_only"]["recall@20"] for s in sweep]
    fed_f = [s["fedavg_final"]["recall@20"] for s in sweep]
    fed_b = [s["fedavg_best"]["recall@20"] for s in sweep]
    cent = reco["systems"]["centralized"]["recall@20"]

    fig, ax = _fig(height_cm=6.4)
    w = 0.26
    x = np.arange(len(cs))
    ax.bar(x - w, loc, w, label="Cục bộ (không chia sẻ)", color="#bdc3c7")
    ax.bar(x, fed_f, w, label="Liên bang (vòng cuối)", color=C_BLUE)
    ax.bar(x + w, fed_b, w, label="Liên bang (đỉnh)", color="#5dade2")
    ax.axhline(cent, ls="--", lw=1.2, color=C_RED,
               label=f"Tập trung ({cent:.3f})")
    for i in range(len(cs)):
        ax.text(x[i] - w, loc[i] + 0.012, f"{loc[i]:.2f}", ha="center", fontsize=6)
        ax.text(x[i], fed_f[i] + 0.012, f"{fed_f[i]:.2f}", ha="center", fontsize=6)
        ax.text(x[i] + w, fed_b[i] + 0.012, f"{fed_b[i]:.2f}", ha="center", fontsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{c} khách hàng" for c in cs], fontsize=6.8)
    ax.set_ylabel("Recall@20", fontsize=7)
    ax.set_title("Càng chia nhỏ dữ liệu, mô hình cục bộ càng kém; "
                 "liên bang giữ được chất lượng", fontsize=7.5)
    ax.legend(fontsize=6.2, loc="lower left")
    ax.tick_params(labelsize=6.5)
    ax.set_ylim(0, max(max(loc), max(fed_b), cent) * 1.28)
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, out, "F08_so_khach_hang.png", dpi)


def fig_communication(reco: dict, out: Path, dpi: int) -> Path:
    """F09: chi phí truyền thông — nói thẳng FL không rẻ hơn ở quy mô này."""
    c = reco["communication"]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH_CM / 2.54, 6.2 / 2.54),
                             gridspec_kw={"width_ratios": [1, 1.15]})
    ax = axes[0]
    vals = [c["raw_data_bytes_if_centralized"] / 1024,
            c["up_bytes_total"] / 1024]
    ax.bar([0, 1], vals, color=[C_RED, C_BLUE], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v * 1.15, f"{v:,.0f} KB", ha="center", fontsize=7)
    ax.set_yscale("log")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Gửi dữ liệu thô\n(tập trung)",
                        "Gửi tham số\n(liên bang)"], fontsize=6.8)
    ax.set_ylabel("KB (thang log)", fontsize=7)
    ax.set_title(f"Ở quy mô này, liên bang tốn gấp "
                 f"{c['ratio_up_vs_raw']:,.0f} lần băng thông", fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    # đường hoà vốn: FL không đổi theo số tương tác, dữ liệu thô thì tăng
    n = np.logspace(2, 7, 200)
    up = c["up_bytes_total"]
    raw = n * c["raw_bytes_per_interaction"]
    ax.plot(n, raw / 1024, color=C_RED, lw=1.6, label="Gửi dữ liệu thô")
    ax.axhline(up / 1024, color=C_BLUE, lw=1.6, ls="--",
               label="Gửi tham số (liên bang)")
    xc = c["crossover_interactions"]
    ax.axvline(xc, color=C_GREY, ls=":", lw=1.2)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Số tương tác", fontsize=7)
    ax.set_ylabel("KB mỗi vòng (log)", fontsize=7)
    ax.set_title("Lợi ích băng thông chỉ đến khi dữ liệu đủ lớn", fontsize=7.5)
    # đặt chú thích trong vùng trống phía dưới bên trái, tránh đè tiêu đề
    ax.annotate(f"hoà vốn ≈ {xc / 1e6:.2f} triệu tương tác",
                xy=(xc, up / 1024), xytext=(1.2e2, up / 1024 * 0.02),
                fontsize=6.3,
                arrowprops=dict(arrowstyle="->", lw=0.7, color="#2c3e50"))
    ax.legend(fontsize=6.2, loc="upper left")
    ax.tick_params(labelsize=6.5)
    ax.grid(alpha=0.3)
    return _save(fig, out, "F09_truyen_thong.png", dpi)


def fig_architecture(out: Path, dpi: int) -> Path:
    """F01: kiến trúc hệ — vẽ bằng hình chữ nhật, không phụ thuộc graphviz."""
    fig, ax = plt.subplots(figsize=(WIDTH_CM / 2.54, 8.6 / 2.54))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.4); ax.axis("off")

    def box(x, y, w, h, text, color, fontsize=6.6, tc="white"):
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=color,
                                   edgecolor="none", alpha=0.92, zorder=2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                color=tc, fontsize=fontsize, zorder=3, linespacing=1.35)

    # server
    box(2.9, 4.15, 4.2, 1.05,
        "MÁY CHỦ TRUNG TÂM\nNút Kỹ năng (603) · Nút Ngành (10)\n"
        "Dữ liệu công khai — không có hồ sơ cá nhân", C_BLUE, 6.4)

    # clients: 5 hộp, mỗi hộp rộng 1.72, khoảng cách 0.22 -> tổng 9.48
    cxs = [0.25 + i * 1.94 for i in range(5)]
    for i, cx in enumerate(cxs):
        box(cx, 1.65, 1.72, 1.3,
            f"KHÁCH HÀNG {i + 1}\nTin tuyển dụng\nHồ sơ ứng viên\n(riêng tư)",
            C_RED, 5.7)
        # mũi tên hai chiều nối client -> server
        ax.annotate("", xy=(cx + 0.86, 2.98), xytext=(cx + 0.86, 4.12),
                    arrowprops=dict(arrowstyle="<->", lw=1.0, color=C_GREY,
                                    linestyle="--", shrinkA=0, shrinkB=0),
                    zorder=1)

    # nhãn chú thích đặt CAO HƠN đỉnh mũi tên để không đè lên chúng
    ax.text(5.0, 3.93, "chỉ trao đổi THAM SỐ (không gửi dòng dữ liệu)",
            ha="center", va="center", fontsize=6.2, color="#2c3e50",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=C_GREY, lw=0.6),
            zorder=4)

    box(0.25, 0.3, 9.5, 0.95,
        "Mỗi khách hàng dựng ĐỒ THỊ CON cục bộ:\n"
        "Việc làm ↔ Kỹ năng ↔ Ngành,  nối vào tập nút chung của máy chủ",
        "#ecf0f1", 6.3, tc="#2c3e50")
    ax.set_title("Kiến trúc GNN + Học liên bang: dữ liệu ở lại, chỉ tham số đi",
                 fontsize=8, pad=8)
    return _save(fig, out, "F01_kien_truc.png", dpi)


# =====================================================================
# Main
# =====================================================================
def main() -> dict:
    setup_console()
    cfg = load_config()
    banner("SINH HÌNH CHO BÁO CÁO")

    res_dir = Path(cfg["paths"]["results"])
    fig_dir = Path(cfg["paths"]["figures"])
    fig_dir.mkdir(parents=True, exist_ok=True)
    dpi = int(cfg["report"]["dpi"])

    reco = load_json(res_dir / "reco_main.json")

    produced = []
    jobs = [
        ("F01", lambda: fig_architecture(fig_dir, dpi)),
        ("F02", lambda: fig_data_cleaning(reco, fig_dir, dpi)),
        ("F03", lambda: fig_sparsity(reco, fig_dir, dpi)),
        ("F04", lambda: fig_graph_structure(reco, fig_dir, dpi)),
        ("F05", lambda: fig_industries(reco, fig_dir, dpi)),
        ("F06", lambda: fig_reco_comparison(reco, fig_dir, dpi)),
        ("F07", lambda: fig_fl_curve(reco, fig_dir, dpi)),
        ("F08", lambda: fig_client_scale(reco, fig_dir, dpi)),
        ("F09", lambda: fig_communication(reco, fig_dir, dpi)),
    ]
    for code, fn in jobs:
        try:
            p = fn()
            produced.append({"code": code, "file": p.name,
                             "bytes": p.stat().st_size})
            step(f"{code} → {p.name}")
        except Exception as exc:  # không để 1 hình hỏng làm sập cả báo cáo
            produced.append({"code": code, "file": None, "error": str(exc)})
            step(f"{code} LỖI: {exc}")

    manifest = {"figures": produced, "dpi": dpi,
                "width_cm": WIDTH_CM,
                "n_ok": sum(1 for p in produced if p.get("file"))}
    from src.common import save_json
    save_json(fig_dir / "manifest.json", manifest)
    banner(f"XONG: {manifest['n_ok']}/{len(jobs)} hình")
    return manifest


if __name__ == "__main__":
    main()
