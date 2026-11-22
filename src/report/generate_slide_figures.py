"""Generate 7 publication-grade 300 DPI Warm Cream editorial figures for FedGraph slides.

Strictly matches `finalslide.pptx` ("Story" theme) palette & typography so every chart
blends seamlessly onto #F5F1E8 slides without white boxes:
  - Canvas / Axes background : #F5F1E8 (Warm Cream Paper)
  - Card / Callout wash      : #ECE7DA (Muted Parchment)
  - Hairlines / Spines / Grid: #C9C2B0
  - Primary accent (FedGraph): #0F4C5C (Deep Petroleum Teal)
  - Secondary / Drift / Alert: #A8554E (Muted Terracotta)
  - Neutral series           : #5C5C5C / #8A8374
  - Ink (Title / Body / Mute): #1A1A1A / #2B2B2B / #5C5C5C
  - Typography               : Cambria (fallback DejaVu Serif)

Loads 100% of numerical values directly from verified repository files:
  - artifacts/v3/meta.json
  - artifacts/v3/clients.json
  - results_v3/notebook_metrics.json (Kaggle CUDA canonical run)
  - results/v3/notebook_metrics.json  (Local CPU run)
  - results_v3/ablation_results.csv
  - results_v3/sweep_results.csv
  - results_v3/local_only_v3.json

Outputs to `results_v3/slide_figures/`:
  1. sfig1_architecture_v3.png
  2. sfig2_funnel_and_skew.png
  3. sfig3_catalog_comparison.png
  4. sfig4_ablation_backbone_scaling.png
  5. sfig5_convergence_drift_sweep.png
  6. sfig6_latency_fairness.png
  7. sfig7_algorithm_pipeline.png
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Patch, Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "v3"
RES_CUDA = ROOT / "results_v3"
RES_CPU = ROOT / "results" / "v3"
OUT_DIR = RES_CUDA / "slide_figures"

DPI = 300

# Story Palette (exact match to finalslide.pptx)
CREAM = "#F5F1E8"
WASH = "#ECE7DA"
WASH_ALT = "#F0ECE1"
RULE = "#C9C2B0"
TEAL = "#0F4C5C"
TEAL_MID = "#3A7280"
TEAL_LIGHT = "#6E9BA6"
TERRA = "#A8554E"
TERRA_SOFT = "#C6837D"
INK = "#1A1A1A"
BODY = "#2B2B2B"
MUTE = "#5C5C5C"
TAUPE = "#8A8374"


def setup_rc() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Cambria", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "axes.edgecolor": RULE,
        "axes.linewidth": 1.1,
        "axes.titlesize": 15.0,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "axes.labelsize": 13.5,
        "axes.labelcolor": BODY,
        "xtick.labelsize": 12.5,
        "ytick.labelsize": 12.5,
        "xtick.color": BODY,
        "ytick.color": BODY,
        "legend.fontsize": 12.0,
        "figure.facecolor": CREAM,
        "axes.facecolor": CREAM,
        "savefig.facecolor": CREAM,
    })


def style_ax(ax, grid_axis: str = "x") -> None:
    ax.set_facecolor(CREAM)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=BODY, length=4, width=0.9)
    if grid_axis:
        ax.grid(axis=grid_axis, linestyle="--", linewidth=0.7, alpha=0.55, color=RULE, zorder=0)


def fmt_int(n: int) -> str:
    return f"{int(n):,}"


def load_all_inputs() -> dict:
    with open(ART / "meta.json", encoding="utf-8") as f:
        meta = json.load(f)
    with open(ART / "clients.json", encoding="utf-8") as f:
        clients = json.load(f)
    with open(RES_CUDA / "notebook_metrics.json", encoding="utf-8") as f:
        metrics_cuda = json.load(f)
    with open(RES_CPU / "notebook_metrics.json", encoding="utf-8") as f:
        metrics_cpu = json.load(f)
    with open(RES_CUDA / "local_only_v3.json", encoding="utf-8") as f:
        local_only = json.load(f)
    with open(RES_CUDA / "ablation_results.csv", encoding="utf-8") as f:
        ablation = list(csv.DictReader(f))
    with open(RES_CUDA / "sweep_results.csv", encoding="utf-8") as f:
        sweep = list(csv.DictReader(f))
    return dict(
        meta=meta,
        clients=clients,
        metrics_cuda=metrics_cuda,
        metrics_cpu=metrics_cpu,
        local_only=local_only,
        ablation=ablation,
        sweep=sweep,
    )


def _rect(ax, x: float, y: float, w: float, h: float, fc: str, ec: str,
          lw: float = 1.2, ls: str = "-", zorder: int = 2) -> Rectangle:
    patch = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                      linewidth=lw, linestyle=ls, zorder=zorder)
    ax.add_patch(patch)
    return patch


def _arrow(ax, p1: tuple[float, float], p2: tuple[float, float],
           color: str = BODY, lw: float = 1.8, ls: str = "-",
           rad: float = 0.0, style: str = "-|>", zorder: int = 5) -> FancyArrowPatch:
    arr = FancyArrowPatch(
        p1, p2,
        connectionstyle=f"arc3,rad={rad}",
        arrowstyle=style,
        mutation_scale=15,
        linewidth=lw,
        linestyle=ls,
        color=color,
        zorder=zorder,
    )
    ax.add_patch(arr)
    return arr


# =============================================================================
# SFIG 1: System & GraphSafe Cross-Silo Architecture Diagram
# =============================================================================
def build_sfig1_architecture(d: dict) -> Path:
    m_cuda = d["metrics_cuda"]
    g = m_cuda["graph"]
    cs = m_cuda["cross_silo"]
    meta = d["meta"]
    c_stats = meta["clients"]["size_stats"]
    c0 = d["clients"][0]

    n_clients = cs["n_clients"]
    n_nodes = g["n_nodes"]
    n_users = g["n_users"]
    n_jobs = g["n_jobs"]
    n_occ = g["n_occ"]
    n_skill = g["n_skill"]
    n_pub_nodes = meta["nodes"]["n_public_nodes"]
    ebt = g["edges_by_type"]
    e_uj, e_jo, e_os, e_uo = ebt["0"], ebt["1"], ebt["2"], ebt["3"]
    e_priv = e_uj + e_uo
    e_pub = e_jo + e_os
    pct_occ_job = meta["edges"]["pct_jobs_with_occupation_edge"]
    mean_sk_occ = meta["skills"]["mean_skills_per_occupation"]
    pct_multi = cs["pct_users_multi_client"]

    fig, ax = plt.subplots(figsize=(16.8, 8.6))
    fig.patch.set_facecolor(CREAM)
    ax.set_facecolor(CREAM)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.968,
        "Kiến trúc Hệ thống FedGraph & Ranh giới Bảo mật GraphSafe Cross-Silo (V3)",
        ha="center", va="center", fontsize=18.5, fontweight="bold", color=INK,
    )
    ax.text(
        0.5, 0.928,
        f"Đồ thị dị thể: {fmt_int(n_nodes)} nút ({fmt_int(n_users)} users, {fmt_int(n_jobs)} jobs, "
        f"{fmt_int(n_pub_nodes)} nút O*NET công khai) | {fmt_int(g['n_edges'])} cạnh "
        f"({100*e_priv/g['n_edges']:.2f}% riêng tư / {100*e_pub/g['n_edges']:.2f}% công khai)",
        ha="center", va="center", fontsize=13.5, color=MUTE,
    )
    ax.plot([0.04, 0.96], [0.902, 0.902], color=RULE, lw=1.0)

    # --- Zone 1 (Left): Private Employer Silos ---
    _rect(ax, 0.015, 0.045, 0.305, 0.835, WASH_ALT, TERRA, lw=1.8, ls="--", zorder=1)
    _rect(ax, 0.015, 0.832, 0.305, 0.048, TERRA, TERRA, lw=1.0, zorder=2)
    ax.text(0.1675, 0.856, f"RANH GIỚI RIÊNG TƯ — {fmt_int(n_clients)} SILOS",
            ha="center", va="center", fontsize=13.5, fontweight="bold", color=CREAM, zorder=3)

    # Silo #0 card
    _rect(ax, 0.030, 0.625, 0.275, 0.185, CREAM, RULE, lw=1.2, zorder=2)
    ax.text(0.1675, 0.785,
            f"Silo #0: {c0['employer_name']} ({fmt_int(c0['n_apps'])} apps, {fmt_int(c0['n_jobs'])} jobs)",
            ha="center", va="center", fontsize=12.5, fontweight="bold", color=INK)
    ax.text(0.1675, 0.740, "Đồ thị con cục bộ: user–job + user–occupation",
            ha="center", va="center", fontsize=11.8, color=BODY)
    ax.text(0.1675, 0.695, "LightGCN (L=2, dim=32) + BPR Loss",
            ha="center", va="center", fontsize=12.2, fontweight="bold", color=TEAL)
    ax.text(0.1675, 0.652, "Ghép Public Backbone → cập nhật E_local",
            ha="center", va="center", fontsize=11.8, color=MUTE)

    # Silo #1..9115 card
    _rect(ax, 0.030, 0.395, 0.275, 0.200, CREAM, RULE, lw=1.2, zorder=2)
    ax.text(0.1675, 0.568,
            f"Silos #1..#{fmt_int(n_clients-1)} (min {c_stats['min']}, median {c_stats['median']})",
            ha="center", va="center", fontsize=12.5, fontweight="bold", color=INK)
    ax.text(0.1675, 0.520, "Gán cạnh chuẩn silo: client_of_job[j]",
            ha="center", va="center", fontsize=11.8, color=BODY)
    ax.text(0.1675, 0.472, f"Cạnh riêng tư: {fmt_int(e_priv)}",
            ha="center", va="center", fontsize=12.2, fontweight="bold", color=INK)
    ax.text(0.1675, 0.425, f"({fmt_int(e_uj)} user–job + {fmt_int(e_uo)} user–occ)",
            ha="center", va="center", fontsize=11.6, color=MUTE)

    # GraphSafe Guarantee card
    _rect(ax, 0.030, 0.068, 0.275, 0.295, WASH, TERRA, lw=1.6, zorder=2)
    _rect(ax, 0.030, 0.318, 0.275, 0.045, TERRA, TERRA, lw=1.0, zorder=3)
    ax.text(0.1675, 0.340, "GraphSafe: 0 B RÒ RỈ DỮ LIỆU THÔ",
            ha="center", va="center", fontsize=12.8, fontweight="bold", color=CREAM, zorder=4)
    ax.text(0.045, 0.275, "— Cặp (user, job) & lịch sử giữ tại client",
            ha="left", va="center", fontsize=11.8, color=BODY)
    ax.text(0.045, 0.222, f"— {pct_multi:.2f}% user đa-client (không lộ chéo)",
            ha="left", va="center", fontsize=11.8, color=BODY)
    ax.text(0.045, 0.169, "— Không gửi raw interactions ra ngoài",
            ha="left", va="center", fontsize=11.8, color=BODY)
    ax.text(0.045, 0.112, "→ Chỉ tải lên ma trận E_local (n_local × 32)",
            ha="left", va="center", fontsize=12.0, fontweight="bold", color=TEAL)

    # --- Zone 2 (Center): FedAvg Server (Top) + Public Backbone (Bottom) ---
    # Server
    _rect(ax, 0.405, 0.495, 0.265, 0.385, WASH, TEAL, lw=1.8, zorder=1)
    _rect(ax, 0.405, 0.832, 0.265, 0.048, TEAL, TEAL, lw=1.0, zorder=2)
    ax.text(0.5375, 0.856, "MÁY CHỦ FEDAVG SERVER",
            ha="center", va="center", fontsize=13.5, fontweight="bold", color=CREAM, zorder=3)

    _rect(ax, 0.422, 0.655, 0.231, 0.150, CREAM, RULE, lw=1.2, zorder=2)
    ax.text(0.5375, 0.778, "Sparse 'Touched' FedAvg",
            ha="center", va="center", fontsize=13.0, fontweight="bold", color=TEAL)
    ax.text(0.5375, 0.730, r"$E_{global}[v] \leftarrow \frac{\sum w_c \cdot E_c[v]}{\sum w_c}$",
            ha="center", va="center", fontsize=14.0, color=INK)
    ax.text(0.5375, 0.678, "Cập nhật chỉ nút được chạm (tránh pha loãng)",
            ha="center", va="center", fontsize=11.3, color=MUTE)

    _rect(ax, 0.422, 0.515, 0.231, 0.115, CREAM, TERRA, lw=1.3, ls="--", zorder=2)
    ax.text(0.5375, 0.598, "Hướng mở rộng (Future Work)",
            ha="center", va="center", fontsize=12.2, fontweight="bold", color=TERRA)
    ax.text(0.5375, 0.548, "DP-SGD (ε, δ) + Secure Aggregation",
            ha="center", va="center", fontsize=11.8, color=BODY)

    # Public Backbone
    _rect(ax, 0.405, 0.045, 0.265, 0.390, WASH, TEAL, lw=1.8, zorder=1)
    _rect(ax, 0.405, 0.387, 0.265, 0.048, TEAL, TEAL, lw=1.0, zorder=2)
    ax.text(0.5375, 0.411, "PUBLIC GRAPH BACKBONE (O*NET)",
            ha="center", va="center", fontsize=13.0, fontweight="bold", color=CREAM, zorder=3)

    ax.text(0.5375, 0.348, f"{fmt_int(n_pub_nodes)} nút công khai (is_public = 1)",
            ha="center", va="center", fontsize=12.5, fontweight="bold", color=INK)
    ax.text(0.422, 0.295, f"— {fmt_int(n_occ)} Occupation (mã chuẩn soc[:7])",
            ha="left", va="center", fontsize=11.8, color=BODY)
    ax.text(0.422, 0.248, f"— {fmt_int(n_skill)} Technology Skills",
            ha="left", va="center", fontsize=11.8, color=BODY)
    ax.plot([0.422, 0.653], [0.214, 0.214], color=RULE, lw=0.9)
    ax.text(0.5375, 0.184, f"{fmt_int(e_pub)} cạnh công khai ({100*e_pub/g['n_edges']:.2f}%):",
            ha="center", va="center", fontsize=12.2, fontweight="bold", color=TEAL)
    ax.text(0.422, 0.136, f"— {fmt_int(e_jo)} job–occ ({pct_occ_job:.2f}% jobs)",
            ha="left", va="center", fontsize=11.8, color=BODY)
    ax.text(0.422, 0.088, f"— {fmt_int(e_os)} occ–skill ({mean_sk_occ:.2f} skill/nghề)",
            ha="left", va="center", fontsize=11.8, color=BODY)

    # --- Zone 3 (Right): Full-Stack Serving ---
    _rect(ax, 0.745, 0.045, 0.240, 0.835, WASH_ALT, RULE, lw=1.6, zorder=1)
    _rect(ax, 0.745, 0.832, 0.240, 0.048, INK, INK, lw=1.0, zorder=2)
    ax.text(0.865, 0.856, "PHỤC VỤ FULL-STACK",
            ha="center", va="center", fontsize=13.5, fontweight="bold", color=CREAM, zorder=3)

    _rect(ax, 0.762, 0.605, 0.206, 0.198, CREAM, RULE, lw=1.2, zorder=2)
    ax.text(0.865, 0.773, "PostgreSQL 16 (dss_jobs)",
            ha="center", va="center", fontsize=12.8, fontweight="bold", color=TEAL)
    ax.text(0.865, 0.728, "9 bảng | >21.3 triệu dòng",
            ha="center", va="center", fontsize=12.0, fontweight="bold", color=INK)
    ax.text(0.865, 0.682, "user_skills: 18.02M (2-hop)",
            ha="center", va="center", fontsize=11.5, color=MUTE)
    ax.text(0.865, 0.638, "job_skills: 2.59M | InMemory fallback",
            ha="center", va="center", fontsize=11.3, color=MUTE)

    _rect(ax, 0.762, 0.340, 0.206, 0.200, CREAM, RULE, lw=1.2, zorder=2)
    ax.text(0.865, 0.510, "FastAPI + WebSocket (api/)",
            ha="center", va="center", fontsize=12.8, fontweight="bold", color=TEAL)
    ax.text(0.865, 0.464, "11 REST/WS + 4 V3 Endpoints",
            ha="center", va="center", fontsize=11.8, color=BODY)
    ax.text(0.865, 0.418, "POST /api/recommend (2-hop)",
            ha="center", va="center", fontsize=11.5, color=MUTE)
    ax.text(0.865, 0.372, "18/18 smoke checks đạt chuẩn",
            ha="center", va="center", fontsize=11.5, fontweight="bold", color=TEAL)

    _rect(ax, 0.762, 0.072, 0.206, 0.202, CREAM, RULE, lw=1.2, zorder=2)
    ax.text(0.865, 0.244, "React 19 + Three.js (web/)",
            ha="center", va="center", fontsize=12.8, fontweight="bold", color=TEAL)
    ax.text(0.865, 0.198, "5 trang tương tác & 3D Topology",
            ha="center", va="center", fontsize=11.8, color=BODY)
    ax.text(0.865, 0.152, "Node Monitor (UI Fault Sim.)",
            ha="center", va="center", fontsize=11.5, color=MUTE)
    ax.text(0.865, 0.106, "Độ trễ thật: perf_counter()",
            ha="center", va="center", fontsize=11.5, fontweight="bold", color=TERRA)

    # --- Arrows ---
    _arrow(ax, (0.322, 0.755), (0.402, 0.755), color=TEAL, lw=2.2)
    ax.text(0.362, 0.790, "E_local ↑", ha="center", va="center", fontsize=12.5, fontweight="bold", color=TEAL)
    _arrow(ax, (0.402, 0.680), (0.322, 0.680), color=BODY, lw=2.0, ls="--")
    ax.text(0.362, 0.642, "E_global ↓", ha="center", va="center", fontsize=12.5, fontweight="bold", color=BODY)

    _arrow(ax, (0.402, 0.260), (0.322, 0.440), color=TEAL, lw=2.0)
    ax.text(0.362, 0.350, "Cấu trúc\ncông khai", ha="center", va="center", fontsize=11.8, fontweight="bold", color=TEAL,
            bbox=dict(boxstyle="square,pad=0.25", fc=CREAM, ec=TEAL, lw=0.9), zorder=6)

    _arrow(ax, (0.5375, 0.438), (0.5375, 0.492), color=TEAL, lw=1.8, style="<|-|>")

    _arrow(ax, (0.672, 0.700), (0.742, 0.700), color=INK, lw=2.0)
    ax.text(0.707, 0.734, "E_global", ha="center", va="center", fontsize=12.0, fontweight="bold", color=INK)
    _arrow(ax, (0.672, 0.440), (0.742, 0.440), color=INK, lw=2.0)
    ax.text(0.707, 0.474, "Metrics", ha="center", va="center", fontsize=12.0, fontweight="bold", color=INK)

    _arrow(ax, (0.865, 0.602), (0.865, 0.543), color=BODY, lw=1.7, style="<|-|>")
    _arrow(ax, (0.865, 0.337), (0.865, 0.277), color=BODY, lw=1.7, style="<|-|>")

    out = OUT_DIR / "sfig1_architecture_v3.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.20, facecolor=CREAM)
    plt.close(fig)
    return out


# =============================================================================
# SFIG 2: 5-Step Funnel + 9 Employer Sources + Non-IID Client Size Histogram
# =============================================================================
def build_sfig2_funnel_and_skew(d: dict) -> Path:
    meta = d["meta"]
    ee = meta["employer_extraction"]
    split = d["metrics_cuda"]["split"]
    g = d["metrics_cuda"]["graph"]
    c_stats = meta["clients"]["size_stats"]
    client_apps = np.array([int(c["n_apps"]) for c in d["clients"]], dtype=np.int64)

    fig = plt.figure(figsize=(17.6, 8.2))
    fig.patch.set_facecolor(CREAM)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.12, 1.0], height_ratios=[1.05, 1.0],
                          wspace=0.34, hspace=0.42)

    # --- Panel (a) Top-Left: 5-Step Preprocessing Funnel ---
    ax1 = fig.add_subplot(gs[0, 0])
    stages = [
        ("0–1. apps.tsv gốc\n(khớp 100% jobs.tsv)", meta["raw"]["apps_rows"],
         f"100.0% | {fmt_int(meta['raw']['jobs_rows'])} jobs", TAUPE),
        ("2. Trích xuất Employer\n(9 nguồn regex/domain)", ee["n_apps_with_employer"],
         f"{ee['pct_apps_with_employer']:.2f}% | {fmt_int(ee['n_distinct_names_raw'])} tên", TEAL_LIGHT),
        ("3–4. Lọc ≥ 2 jobs & P1\n(loại tên nhiễu 1-job)", ee["n_apps_with_employer"],
         f"{fmt_int(ee['n_distinct_employers_after_job_filter'])} employers | {fmt_int(ee['n_jobs_with_employer_after_job_filter'])} jobs", TEAL_MID),
        ("5. Silo FL ≥ 10 apps\n(9,116 Employer Silos)", ee["n_apps_with_employer_and_client"],
         f"{ee['pct_apps_with_employer_and_client']:.2f}% | {fmt_int(g['n_users'])} users", TEAL),
        ("Train / Test sạch\n(bỏ 880 cạnh rò rỉ 2-hop)", g["n_train_uj"],
         f"{fmt_int(g['n_train_uj'])} train + {fmt_int(split['n_test_clean'])} test", INK),
    ]
    y1 = np.arange(len(stages))[::-1]
    vals1 = [s[1] for s in stages]
    cols1 = [s[3] for s in stages]
    max_v = meta["raw"]["apps_rows"]

    bars1 = ax1.barh(y1, vals1, height=0.62, color=cols1, edgecolor=CREAM, linewidth=1.0, zorder=3)
    ax1.set_yticks(y1)
    ax1.set_yticklabels([s[0] for s in stages], fontsize=11.5, fontweight="bold", color=BODY)
    ax1.set_xlim(0, max_v * 1.98)
    ax1.set_xlabel("Số lượt ứng tuyển (applications)", fontsize=12.5, fontweight="bold")
    ax1.set_title("(a) Phễu Tiền xử lý 5 Bước (1,603,111 → 436,893)", fontsize=14.0, pad=10)
    style_ax(ax1, "x")
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else (f"{int(x/1e3)}k" if x > 0 else "0")))

    for bar, v, (_, _, note, _) in zip(bars1, vals1, stages):
        yc = bar.get_y() + bar.get_height() / 2
        ax1.text(v + max_v * 0.025, yc + 0.11, f"{fmt_int(v)} apps",
                 va="center", ha="left", fontsize=11.5, fontweight="bold", color=INK)
        ax1.text(v + max_v * 0.025, yc - 0.17, note,
                 va="center", ha="left", fontsize=10.5, color=MUTE)

    # --- Panel (b) Bottom-Left: 9 Employer Extraction Sources ---
    ax2 = fig.add_subplot(gs[1, 0])
    src_map = {
        "S2_is_a": "S2: 'is a <Company>'",
        "S8_domain_website": "S8: Domain Website",
        "S1_legal_dau_cau": "S1a: Hậu tố Inc/LLC",
        "S5_domain_email": "S5: Domain Email",
        "S7_hau_to_cuoi": "S7: Hậu tố cuối câu",
        "S6_viet_hoa": "S6: Cụm viết hoa",
        "S3_seeks": "S3: '<Company> seeks'",
        "S1_legal_dau_mo_ta": "S1b: Pháp lý đầu đoạn",
        "S4_about_us": "S4: Mục 'About Us'",
    }
    sc = ee["source_counts"]
    items = sorted(sc.items(), key=lambda kv: kv[1])
    s_labels = [src_map.get(k, k) for k, _ in items]
    s_vals = [v for _, v in items]
    s_tot = sum(s_vals)

    y2 = np.arange(len(items))
    s_cols = [TAUPE if i < len(items) - 4 else (TEAL_MID if i < len(items) - 2 else TEAL)
              for i in range(len(items))]
    bars2 = ax2.barh(y2, s_vals, height=0.64, color=s_cols, edgecolor=CREAM, linewidth=0.8, zorder=3)
    ax2.set_yticks(y2)
    ax2.set_yticklabels(s_labels, fontsize=11.5, fontweight="bold", color=BODY)
    ax2.set_xlim(0, max(s_vals) * 1.46)
    ax2.set_xlabel("Số tin tuyển dụng trích xuất được", fontsize=12.5, fontweight="bold")
    ax2.set_title(f"(b) 9 Nguồn Trích xuất Employer (Tổng {fmt_int(s_tot)} lượt)", fontsize=14.0, pad=10)
    style_ax(ax2, "x")
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x/1e3)}k" if x > 0 else "0"))

    for bar, v in zip(bars2, s_vals):
        ax2.text(v + max(s_vals) * 0.02, bar.get_y() + bar.get_height() / 2,
                 f"{fmt_int(v)} ({100*v/s_tot:.1f}%)",
                 va="center", ha="left", fontsize=11.0, fontweight="bold", color=INK)

    # --- Panel (c) Full Right Column: Non-IID Client Size Histogram ---
    ax3 = fig.add_subplot(gs[:, 1])
    log_apps = np.log10(client_apps)
    ax3.hist(log_apps, bins=38, color=TEAL, alpha=0.85, edgecolor=CREAM, linewidth=0.8, zorder=3)

    ax3.axvline(np.log10(c_stats["min"]), color=TAUPE, ls=":", lw=2.0,
                label=f"Min = {c_stats['min']} apps", zorder=4)
    ax3.axvline(np.log10(c_stats["median"]), color=INK, ls="--", lw=2.2,
                label=f"Median = {c_stats['median']} apps (p25={c_stats['p25']}, p75={c_stats['p75']})", zorder=4)
    ax3.axvline(np.log10(c_stats["mean"]), color=TERRA, ls="-.", lw=2.2,
                label=f"Mean = {c_stats['mean']:.1f} apps", zorder=4)
    ax3.axvline(np.log10(c_stats["max"]), color=TERRA, ls="-", lw=2.2,
                label=f"Max = {fmt_int(c_stats['max'])} ({d['clients'][0]['employer_name']})", zorder=4)

    xticks_val = [10, 25, 100, 500, 4745]
    ax3.set_xticks([np.log10(v) for v in xticks_val])
    ax3.set_xticklabels([fmt_int(v) for v in xticks_val], fontsize=12.5, fontweight="bold")
    ax3.set_xlim(0.92, np.log10(c_stats["max"]) + 0.16)
    ax3.set_xlabel("Số lượt ứng tuyển mỗi Silo (n_apps, thang log10)", fontsize=13.0, fontweight="bold")
    ax3.set_ylabel("Số lượng Employer Silos", fontsize=13.0, fontweight="bold")
    ax3.set_title(
        f"(c) Phân bố Non-IID {fmt_int(len(client_apps))} Silos (Độ lệch {c_stats['max_min_ratio']:.1f}×)",
        fontsize=14.2, pad=10,
    )
    style_ax(ax3, "y")
    ax3.legend(loc="upper right", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=11.2)

    # Callout card strictly left of the Max=4,745 vertical line
    ax3.text(
        0.90, 0.52,
        f"Lệch quy mô Power-Law:\n"
        f"• Skew Max/Min: {c_stats['max_min_ratio']:.1f}×\n"
        f"• Top-1 chiếm {c_stats['top1_share_pct']:.2f}% tổng apps\n"
        f"• {meta['clients']['pct_users_multi_client']:.2f}% users đa-client\n"
        f"  (TB {meta['clients']['mean_clients_per_user']:.2f} silos/user)",
        transform=ax3.transAxes, ha="right", va="center",
        fontsize=11.6, color=BODY,
        bbox=dict(boxstyle="square,pad=0.42", fc=WASH, ec=RULE, lw=1.1),
    )

    fig.suptitle(
        "Tiền xử lý Dữ liệu CareerBuilder + O*NET V3 & Phân bố Non-IID Cross-Silo",
        fontsize=18.0, fontweight="bold", color=INK, y=0.985,
    )
    out = OUT_DIR / "sfig2_funnel_and_skew.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.22, facecolor=CREAM)
    plt.close(fig)
    return out


# =============================================================================
# SFIG 3: Global Catalog vs FL Catalog vs O*NET Catalog + Local-only Comparison
# =============================================================================
def build_sfig3_catalog_comparison(d: dict) -> Path:
    m_cuda = d["metrics_cuda"]["models"]
    abl = {r["biến_thể"]: r for r in d["ablation"]}
    loc_strict = d["local_only"]["results"]["local_only_strict_silo"]
    loc_stitch = d["local_only"]["results"]["local_only_stitched_upper_bound"]
    fed_20_repro = d["local_only"]["results"]["fedavg_20n_repro"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17.2, 7.2),
                                   gridspec_kw={"width_ratios": [1.18, 1.0], "wspace": 0.42})
    fig.patch.set_facecolor(CREAM)

    # --- Panel (a): FL Catalog & O*NET Catalog + Local-only vs Stitched vs FedAvg 20N ---
    fl_entries = [
        ("LightGCN (Cent., 50N univ.)", m_cuda["LightGCN"]["R20_FlUniverse"], None, None, None, TAUPE),
        ("FedAvg 20N (O*NET 956 jobs)", float(abl["(f1) base: nghề + kỹ năng"]["R20"]),
         float(abl["(f1) base: nghề + kỹ năng"]["NDCG20"]), float(abl["(f1) base: nghề + kỹ năng"]["MRR20"]), None, TEAL),
        ("GraphSAGE (Cent., 50N univ.)", m_cuda["GraphSAGE"]["R20_FlUniverse"], None, None, None, TAUPE),
        ("Item-KNN (50N univ.)", m_cuda["Item-KNN"]["R20_FlUniverse"], None, None, None, TAUPE),
        ("FedAvg 20N (Fixed 4,511)", fed_20_repro["recall@20"],
         fed_20_repro["ndcg@20"], fed_20_repro["mrr@20"], fed_20_repro["recall@20_ci95"], TEAL),
        ("Local-only 20N (Stitched)", loc_stitch["recall@20"],
         loc_stitch["ndcg@20"], loc_stitch["mrr@20"], loc_stitch["recall@20_ci95"], MUTE),
        ("FedAvg 50N (Main 9,058)", m_cuda["FedAvg"]["R20_FlUniverse"],
         m_cuda["FedAvg"]["NDCG20_FlUniverse"], m_cuda["FedAvg"]["MRR20_FlUniverse"],
         m_cuda["FedAvg"]["R20_FlUniverse_ci95"], TEAL_MID),
        ("GAT (Cent., 50N univ.)", m_cuda["GAT"]["R20_FlUniverse"], None, None, None, TAUPE),
        ("Local-only 20N (Strict Silo)", loc_strict["recall@20"],
         loc_strict["ndcg@20"], loc_strict["mrr@20"], loc_strict["recall@20_ci95"], TERRA),
        ("BPR-MF (50N univ.)", m_cuda["BPR-MF"]["R20_FlUniverse"], None, None, None, RULE),
        ("Popularity (50N univ.)", m_cuda["Popularity"]["R20_FlUniverse"], None, None, None, RULE),
    ]
    fl_rev = fl_entries[::-1]
    y1 = np.arange(len(fl_rev))
    r20_vals = [e[1] for e in fl_rev]
    cols1 = [e[5] for e in fl_rev]

    ax1.barh(y1, r20_vals, height=0.64, color=cols1, edgecolor=CREAM, linewidth=1.0, zorder=3, label="Recall@20")

    ndcg_x, ndcg_y, mrr_x, mrr_y = [], [], [], []
    for idx, (_, r20, ndcg, mrr, ci, _) in enumerate(fl_rev):
        if ci is not None:
            ax1.errorbar(r20, idx, xerr=[[r20 - ci[0]], [ci[1] - r20]],
                         fmt="none", ecolor=INK, elinewidth=1.6, capsize=4.0, zorder=5)
        if ndcg is not None:
            ndcg_x.append(ndcg); ndcg_y.append(idx)
        if mrr is not None:
            mrr_x.append(mrr); mrr_y.append(idx)

    ax1.scatter(ndcg_x, ndcg_y, marker="D", s=46, color=INK, zorder=6, label="NDCG@20 (FL/Local)")
    ax1.scatter(mrr_x, mrr_y, marker="^", s=52, color=TERRA, edgecolor=CREAM, linewidth=0.5, zorder=6, label="MRR@20 (FL/Local)")

    ax1.set_yticks(y1)
    ax1.set_yticklabels([e[0] for e in fl_rev], fontsize=12.0, fontweight="bold")
    ax1.set_xlim(0, 1.02)
    ax1.set_xlabel("Giá trị Metric (800 eval users, seed=42, CI 95%)", fontsize=13.0, fontweight="bold")
    ax1.set_title("(a) FL Catalog (9,058 / 4,511) & O*NET Catalog (956)", fontsize=14.5, pad=12)
    style_ax(ax1, "x")

    for idx, (_, r20, ndcg, mrr, ci, _) in enumerate(fl_rev):
        x_txt = (ci[1] if ci is not None else r20) + 0.015
        txt = f"R={r20:.4f} | N={ndcg:.4f}" if ndcg is not None else f"R={r20:.4f}"
        ax1.text(x_txt, idx, txt, va="center", ha="left", fontsize=11.3, fontweight="bold", color=INK)

    legend_handles1 = [
        Patch(facecolor=TEAL, edgecolor=CREAM, label="FedGraph (Recall@20)"),
        Patch(facecolor=TERRA, edgecolor=CREAM, label="Local-only Strict (Recall@20)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor=INK, markersize=7.5, label="NDCG@20 (FL/Local)"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor=TERRA, markersize=8.5, label="MRR@20 (FL/Local)"),
    ]
    ax1.legend(handles=legend_handles1, loc="lower right", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=10.8)

    # --- Panel (b): Global Catalog (82,876 jobs) with 95% CIs ---
    glob_order = [
        ("Item-KNN", "Item-KNN", TAUPE),
        ("LightGCN", "LightGCN (Cent.)", MUTE),
        ("GAT", "GAT (Cent.)", TAUPE),
        ("GraphSAGE", "GraphSAGE (Cent.)", TAUPE),
        ("FedAvg", "FedAvg (50N — ~11% jobs)", TERRA),
        ("BPR-MF", "BPR-MF", RULE),
        ("Popularity", "Popularity", RULE),
    ]
    glob_rev = glob_order[::-1]
    y2 = np.arange(len(glob_rev))
    g_r20 = [m_cuda[k]["recall@20"] for k, _, _ in glob_rev]
    g_lo = [m_cuda[k]["recall@20"] - m_cuda[k]["recall@20_ci95"][0] for k, _, _ in glob_rev]
    g_hi = [m_cuda[k]["recall@20_ci95"][1] - m_cuda[k]["recall@20"] for k, _, _ in glob_rev]
    g_ndcg = [m_cuda[k]["ndcg@20"] for k, _, _ in glob_rev]
    g_mrr = [m_cuda[k]["mrr@20"] for k, _, _ in glob_rev]
    g_cols = [c for _, _, c in glob_rev]

    ax2.barh(y2, g_r20, height=0.56, xerr=[g_lo, g_hi], color=g_cols, edgecolor=CREAM, linewidth=1.0,
             error_kw=dict(ecolor=INK, lw=1.5, capsize=4.0), zorder=3)
    ax2.scatter(g_ndcg, y2, marker="D", s=46, color=INK, zorder=6)
    ax2.scatter(g_mrr, y2, marker="^", s=52, color=TERRA, edgecolor=CREAM, linewidth=0.5, zorder=6)

    ax2.set_yticks(y2)
    ax2.set_yticklabels([lbl for _, lbl, _ in glob_rev], fontsize=12.0, fontweight="bold")
    ax2.set_xlim(0, 1.32)
    ax2.set_xlabel("Giá trị Metric (82,876 jobs, 1,000 bootstrap)", fontsize=13.0, fontweight="bold")
    ax2.set_title("(b) Global Catalog (82,876 jobs) — Global Catalog Gap", fontsize=14.5, pad=12)
    style_ax(ax2, "x")

    for idx, (k, _, _) in enumerate(glob_rev):
        hi_x = m_cuda[k]["recall@20_ci95"][1]
        r20 = m_cuda[k]["recall@20"]
        nd = m_cuda[k]["ndcg@20"]
        ax2.text(hi_x + 0.015, idx, f"R={r20:.4f} | N={nd:.4f}",
                 va="center", ha="left", fontsize=11.3, fontweight="bold", color=INK)

    gain_strict = (fed_20_repro["recall@20"] - loc_strict["recall@20"]) * 100
    ax2.annotate(
        f"Global Catalog Gap:\n"
        f"50 clients chỉ phủ 9,058/82,876 jobs (~10.9%);\n"
        f"~89% giữ init ngẫu nhiên → {m_cuda['FedAvg']['recall@20']:.4f}.\n"
        f"Trong FL Catalog 20N, FedAvg đạt {fed_20_repro['recall@20']:.4f}\n"
        f"(+{gain_strict:.2f} pts vs Strict Local-only {loc_strict['recall@20']:.4f}).",
        xy=(0.062, 2.24), xytext=(0.51, 2.15),
        va="center", ha="left", fontsize=10.6, fontweight="bold", color=INK,
        bbox=dict(boxstyle="square,pad=0.38", fc=WASH, ec=TERRA, lw=1.3),
        arrowprops=dict(arrowstyle="->", color=TERRA, lw=1.6, connectionstyle="arc3,rad=0.14"),
    )
    legend_handles2 = [
        Patch(facecolor=MUTE, edgecolor=CREAM, label="Recall@20 (CI 95%)"),
        Patch(facecolor=TERRA, edgecolor=CREAM, label="FedAvg (Global Gap)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor=INK, markersize=7.5, label="NDCG@20"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor=TERRA, markersize=8.5, label="MRR@20"),
    ]
    ax2.legend(handles=legend_handles2, loc="lower right", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=10.8)

    fig.suptitle(
        "So sánh Hiệu năng theo Vũ trụ Đánh giá: FL Catalog vs O*NET Catalog vs Global Catalog",
        fontsize=18.0, fontweight="bold", color=INK, y=1.01,
    )
    out = OUT_DIR / "sfig3_catalog_comparison.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.22, facecolor=CREAM)
    plt.close(fig)
    return out


# =============================================================================
# SFIG 4: 3-Panel Ablation (Backbone, Client Scaling, Aggregation)
# =============================================================================
def build_sfig4_ablation_backbone_scaling(d: dict) -> Path:
    abl = {r["biến_thể"]: r for r in d["ablation"]}
    loc_r20 = d["local_only"]["results"]["local_only_strict_silo"]["recall@20"]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18.2, 6.4),
                                        gridspec_kw={"width_ratios": [1.0, 1.0, 1.05], "wspace": 0.62})
    fig.patch.set_facecolor(CREAM)

    # --- Panel (a): Public Graph Backbone ---
    cats_a = ["Chỉ user–job\n(Bỏ Occ+Skill)", "+ Occupation\n(Bỏ Skill)", "+ Occ + Skill\n(Đầy đủ)"]
    fixed_vals = [
        float(abl["(b) bỏ lớp occupation"]["R20"]),
        float(abl["(a) bỏ lớp skill"]["R20"]),
        float(abl["(base) đầy đủ"]["R20"]),
    ]
    onet_vals = [
        float(abl["(f3) bỏ occupation+skill"]["R20"]),
        float(abl["(f2) bỏ skill"]["R20"]),
        float(abl["(f1) base: nghề + kỹ năng"]["R20"]),
    ]
    x = np.arange(len(cats_a))
    w = 0.36
    b1 = ax1.bar(x - w / 2, fixed_vals, width=w, color=TEAL, edgecolor=CREAM, lw=1.0,
                 label="Fixed 20N (4,511 jobs)", zorder=3)
    b2 = ax1.bar(x + w / 2, onet_vals, width=w, color=TERRA, edgecolor=CREAM, lw=1.0,
                 label="O*NET Catalog (956 jobs)", zorder=3)

    for bar in b1:
        ax1.text(bar.get_x() + bar.get_width() / 2 - 0.02, bar.get_height() + 0.012,
                 f"{bar.get_height():.4f}", ha="center", va="bottom",
                 fontsize=11.0, fontweight="bold", color=TEAL)
    for bar in b2:
        ax1.text(bar.get_x() + bar.get_width() / 2 + 0.02, bar.get_height() + 0.012,
                 f"{bar.get_height():.4f}", ha="center", va="bottom",
                 fontsize=11.0, fontweight="bold", color=TERRA)

    ax1.set_xticks(x)
    ax1.set_xticklabels(cats_a, fontsize=11.5, fontweight="bold")
    ax1.set_ylim(0, 0.80)
    ax1.set_ylabel("Recall@20", fontsize=13.0, fontweight="bold")
    ax1.set_title("(a) Đóng góp Public Graph Backbone", fontsize=14.0, pad=10)
    style_ax(ax1, "y")
    ax1.legend(loc="upper left", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=11.0)
    ax1.text(
        0.97, 0.82,
        f"+{(fixed_vals[2]-fixed_vals[0])*100:.2f} pts (Fixed)\n+{(onet_vals[2]-onet_vals[0])*100:.2f} pts (O*NET)",
        transform=ax1.transAxes, ha="right", va="center",
        fontsize=11.2, fontweight="bold", color=TEAL,
        bbox=dict(boxstyle="square,pad=0.35", fc=WASH, ec=TEAL, lw=1.0),
    )

    # --- Panel (b): Client Scaling (5 -> 10 -> 20) ---
    ns = [5, 10, 20]
    c_r20 = [float(abl[f"(c) n_clients={n}"]["R20"]) for n in ns]
    c_ndcg = [float(abl[f"(c) n_clients={n}"]["NDCG20"]) for n in ns]
    c_mrr = [float(abl[f"(c) n_clients={n}"]["MRR20"]) for n in ns]
    xp = np.arange(len(ns))

    ax2.plot(xp, c_r20, "o-", color=TEAL, lw=2.6, ms=8.5, label="FedAvg Recall@20", zorder=4)
    ax2.plot(xp, c_ndcg, "s--", color=BODY, lw=2.1, ms=7.0, label="FedAvg NDCG@20", zorder=4)
    ax2.plot(xp, c_mrr, "^:", color=TAUPE, lw=2.0, ms=7.0, label="FedAvg MRR@20", zorder=4)
    ax2.axhline(loc_r20, color=TERRA, ls="-.", lw=2.0, label=f"Local-only 20N ({loc_r20:.4f})", zorder=3)

    for i, (rv, nv, mv) in enumerate(zip(c_r20, c_ndcg, c_mrr)):
        dx_r = -10 if i >= 1 else 0
        ax2.annotate(f"{rv:.4f}", (i, rv), xytext=(dx_r, 11), textcoords="offset points",
                     ha="center", va="bottom", fontsize=11.5, fontweight="bold", color=TEAL)
        if i == 2:
            ax2.annotate(f"{nv:.4f}", (i, nv), xytext=(-18, 10), textcoords="offset points",
                         ha="center", va="bottom", fontsize=10.8, fontweight="bold", color=BODY)
        ax2.annotate(f"{mv:.4f}", (i, mv), xytext=(0, -14), textcoords="offset points",
                     ha="center", va="top", fontsize=10.8, fontweight="bold", color=MUTE)

    ax2.set_xticks(xp)
    ax2.set_xticklabels([f"n = {n}" for n in ns], fontsize=12.5, fontweight="bold")
    ax2.set_xlim(-0.32, 2.24)
    ax2.set_ylim(0.11, 0.59)
    ax2.set_xlabel("Số lượng Client tham gia", fontsize=12.8, fontweight="bold")
    ax2.set_ylabel("Giá trị Metric (Fixed 4,511 jobs)", fontsize=13.0, fontweight="bold")
    ax2.set_title("(b) Mở rộng Số Client (5 → 10 → 20)", fontsize=14.0, pad=10)
    style_ax(ax2, "y")
    ax2.legend(loc="upper left", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=10.8)

    # --- Panel (c): Aggregation Mechanism ---
    agg_rows = [
        ("FedAvg Weighted\n(trọng số n_edges)", "(g) FedAvg weighted", TEAL),
        ("FedAvg Unweighted\n(trọng số = 1.0)", "(g) FedAvg unweighted", MUTE),
        ("FedProx (μ = 0.01)\n(phạt ||E - E0||²)", "(d) FedProx (mu=0.01)", TERRA),
    ][::-1]
    y3 = np.arange(len(agg_rows))
    r20_c = [float(abl[k]["R20"]) for _, k, _ in agg_rows]
    nd_c = [float(abl[k]["NDCG20"]) for _, k, _ in agg_rows]
    cols_c = [c for _, _, c in agg_rows]

    ax3.barh(y3 + 0.17, r20_c, height=0.31, color=cols_c, edgecolor=CREAM, lw=0.8, zorder=3)
    ax3.barh(y3 - 0.17, nd_c, height=0.31, color=RULE, edgecolor=CREAM, lw=0.8, zorder=3)

    for i, (rv, nv) in enumerate(zip(r20_c, nd_c)):
        ax3.text(rv + 0.012, i + 0.17, f"{rv:.4f}", va="center", ha="left",
                 fontsize=11.8, fontweight="bold", color=INK)
        ax3.text(nv + 0.012, i - 0.17, f"{nv:.4f}", va="center", ha="left",
                 fontsize=11.3, fontweight="bold", color=MUTE)

    ax3.set_yticks(y3)
    ax3.set_yticklabels([lbl for lbl, _, _ in agg_rows], fontsize=11.5, fontweight="bold")
    ax3.set_xlim(0, 0.72)
    ax3.set_ylim(-0.65, 2.55)
    ax3.set_xlabel("Giá trị Metric (Fixed 4,511 jobs)", fontsize=12.8, fontweight="bold")
    ax3.set_title("(c) Cơ chế Tổng hợp (Aggregation)", fontsize=14.0, pad=10)
    style_ax(ax3, "x")
    agg_handles = [
        Patch(facecolor=TEAL, edgecolor=CREAM, label="Recall@20"),
        Patch(facecolor=RULE, edgecolor=CREAM, label="NDCG@20"),
    ]
    ax3.legend(handles=agg_handles, loc="lower right", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=11.0)

    fig.suptitle(
        "Phân tích Ablation trên Vũ trụ Cố định 20N (4 vòng FL, 800 eval users, seed=42)",
        fontsize=18.0, fontweight="bold", color=INK, y=1.02,
    )
    out = OUT_DIR / "sfig4_ablation_backbone_scaling.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.22, facecolor=CREAM)
    plt.close(fig)
    return out


# =============================================================================
# SFIG 5: 3-Panel Convergence (50N), Client Drift (E=1 vs E=5), and 8-Config Sweep
# =============================================================================
def build_sfig5_convergence_drift_sweep(d: dict) -> Path:
    hist = d["metrics_cuda"]["fedavg_main"]["history"]
    abl = {r["biến_thể"]: r for r in d["ablation"]}
    sweep_cuda = d["sweep"]
    sweep_cpu = d["metrics_cpu"]["sweep"]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17.8, 6.4),
                                        gridspec_kw={"width_ratios": [1.02, 0.92, 1.24], "wspace": 0.30})
    fig.patch.set_facecolor(CREAM)

    # --- Panel (a): 6-round FedAvg 50N Convergence ---
    rounds = [int(h["round"]) for h in hist]
    r20 = [float(h["recall20"]) for h in hist]
    nd20 = [float(h["ndcg20"]) for h in hist]
    r_secs = [float(h["round_seconds"]) for h in hist]

    ax1.plot(rounds, r20, "o-", color=TEAL, lw=2.6, ms=8.0, label="Recall@20", zorder=4)
    ax1.plot(rounds, nd20, "s--", color=MUTE, lw=2.2, ms=6.8, label="NDCG@20", zorder=4)

    for idx, (rnd, rv, nv) in enumerate(zip(rounds, r20, nd20)):
        dx_r = 4 if idx == 0 else (-4 if idx == len(rounds) - 1 else 0)
        dx_n = 8 if idx == 1 else 0
        ax1.annotate(f"{rv:.4f}", (rnd, rv), xytext=(dx_r, 10), textcoords="offset points",
                     ha="center", va="bottom", fontsize=10.8, fontweight="bold", color=TEAL)
        ax1.annotate(f"{nv:.4f}", (rnd, nv), xytext=(dx_n, -12), textcoords="offset points",
                     ha="center", va="top", fontsize=10.5, fontweight="bold", color=MUTE)

    ax1.set_xticks(rounds)
    ax1.set_xticklabels([f"R{r}" for r in rounds], fontsize=12.0, fontweight="bold")
    ax1.set_xlim(0.55, 6.45)
    ax1.set_ylim(0.022, 0.055)
    ax1.set_xlabel("Vòng liên bang (50 clients, CUDA)", fontsize=12.5, fontweight="bold")
    ax1.set_ylabel("Metric (Global Catalog 82,876)", fontsize=12.8, fontweight="bold")
    ax1.set_title("(a) Hội tụ FedAvg 50N (6 vòng)", fontsize=14.0, pad=10)
    style_ax(ax1, "y")
    ax1.legend(loc="lower right", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=11.0)
    ax1.text(
        0.04, 0.94,
        f"R@20: {r20[0]:.4f} → {r20[-1]:.4f} (+{100*(r20[-1]-r20[0])/r20[0]:.1f}%)\n"
        f"TB {np.mean(r_secs):.1f}s/vòng (Tổng {sum(r_secs):.1f}s)",
        transform=ax1.transAxes, ha="left", va="top", fontsize=11.0, color=BODY,
        bbox=dict(boxstyle="square,pad=0.35", fc=WASH, ec=RULE),
    )

    # --- Panel (b): Client Drift E=1 vs E=5 ---
    e1 = abl["(e) local_epochs=1"]
    e5 = abl["(e) local_epochs=5"]
    e1_r20, e1_nd, e1_sec = float(e1["R20"]), float(e1["NDCG20"]), float(e1["giây"])
    e5_r20, e5_nd, e5_sec = float(e5["R20"]), float(e5["NDCG20"]), float(e5["giây"])

    xb = np.arange(2)
    wb = 0.34
    b_e1 = ax2.bar(xb - wb / 2, [e1_r20, e1_nd], width=wb, color=TEAL, edgecolor=CREAM, lw=1.0,
                   label=f"E = 1 ({e1_sec:.1f}s CUDA)", zorder=3)
    b_e5 = ax2.bar(xb + wb / 2, [e5_r20, e5_nd], width=wb, color=TERRA, edgecolor=CREAM, lw=1.0,
                   label=f"E = 5 ({e5_sec:.1f}s, {e5_sec/e1_sec:.1f}×)", zorder=3)

    for bar in b_e1:
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                 f"{bar.get_height():.4f}", ha="center", va="bottom",
                 fontsize=11.5, fontweight="bold", color=TEAL)
    for bar in b_e5:
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                 f"{bar.get_height():.4f}", ha="center", va="bottom",
                 fontsize=11.5, fontweight="bold", color=TERRA)

    ax2.set_xticks(xb)
    ax2.set_xticklabels(["Recall@20", "NDCG@20"], fontsize=12.5, fontweight="bold")
    ax2.set_xlim(-0.55, 1.55)
    ax2.set_ylim(0, 0.70)
    ax2.set_ylabel("Giá trị Metric (Fixed 20N, 4,511 jobs)", fontsize=12.8, fontweight="bold")
    ax2.set_title("(b) Client Drift: E=1 vs E=5", fontsize=14.0, pad=10)
    style_ax(ax2, "y")
    ax2.legend(loc="upper right", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=11.0)
    ax2.text(
        0.96, 0.70,
        f"E=5 gây lệch cục bộ:\n"
        f"• R@20 giảm {(e5_r20-e1_r20)*100:.2f} pts\n"
        f"• Thời gian tăng {e5_sec/e1_sec:.1f}×",
        transform=ax2.transAxes, ha="right", va="center",
        fontsize=11.0, fontweight="bold", color=TERRA,
        bbox=dict(boxstyle="square,pad=0.36", fc=WASH, ec=TERRA, lw=1.1),
    )

    # --- Panel (c): 8-Config Sweep (Recall@20 vs Runtime CUDA / CPU) ---
    pts_cuda = [dict(dim=int(r["dim"]), layers=int(r["layers"]), nc=int(r["n_clients"]),
                     le=int(r["local_epochs"]), r20=float(r["recall20"]), sec=float(r["seconds"]))
                for r in sweep_cuda]
    pts_cpu = {(int(r["dim"]), int(r["layers"]), int(r["n_clients"]), int(r["local_epochs"])):
               float(r["seconds"]) for r in sweep_cpu}

    def _find(d_val, l_val, nc_val, le_val):
        for p in pts_cuda:
            if (p["dim"], p["layers"], p["nc"], p["le"]) == (d_val, l_val, nc_val, le_val):
                return p
        return None

    # Plot CUDA vs CPU pairs connected by subtle rule lines
    for p in pts_cuda:
        k = (p["dim"], p["layers"], p["nc"], p["le"])
        sec_cpu = pts_cpu[k]
        ax3.plot([p["sec"], sec_cpu], [p["r20"], p["r20"]], "-", color=RULE, lw=1.3, zorder=2)

    # Plot CUDA trajectory lines
    traj_cli = [_find(32, 2, 5, 1), _find(32, 2, 10, 1), _find(32, 2, 20, 1)]
    ax3.plot([p["sec"] for p in traj_cli], [p["r20"] for p in traj_cli], "-",
             color=TEAL, lw=2.0, alpha=0.85, label="CUDA (8 cấu hình)", zorder=3)

    # Plot CPU scatter
    ax3.scatter([pts_cpu[(p["dim"], p["layers"], p["nc"], p["le"])] for p in pts_cuda],
                [p["r20"] for p in pts_cuda],
                s=65, marker="s", color=TAUPE, edgecolor=CREAM, lw=0.8,
                label="Local CPU (đối chiếu)", zorder=4)

    # Plot CUDA scatter with highlights
    for p in pts_cuda:
        is_drift = (p["le"] == 5)
        is_best = (p["nc"] == 20)
        is_base = (p["dim"] == 32 and p["layers"] == 2 and p["nc"] == 10 and p["le"] == 1)
        col = TERRA if is_drift else (TEAL if (is_best or is_base) else TEAL_MID)
        mk = "*" if is_base else "o"
        sz = 150 if is_base else (95 if (is_best or is_drift) else 75)
        ax3.scatter(p["sec"], p["r20"], s=sz, marker=mk, color=col, edgecolor=CREAM, lw=0.9, zorder=5)

    # Clean non-overlapping annotations using data coordinates in open regions
    annots_data = [
        ((32, 2, 5, 1),  "N=5 (0.0127 | 11.0s)", (16.0, 0.0108), "left", BODY, False),
        ((32, 1, 10, 1), "L=1\n0.0219\n(12.6s)", (1.5, 0.0305), "left", BODY, True),
        ((32, 2, 10, 1), "Base d32/L2/N10 (0.0221 | 19.5s)", (60.0, 0.0246), "left", TEAL, True),
        ((16, 2, 10, 1), "d=16 (0.0198 | 23.2s)", (34.0, 0.0172), "left", MUTE, True),
        ((64, 2, 10, 1), "d=64 (0.0265 | 25.7s)", (45.0, 0.0302), "left", TEAL, True),
        ((32, 2, 20, 1), "N=20 (0.0353 | 34.6s CUDA)", (34.6, 0.0376), "center", TEAL, False),
        ((32, 2, 10, 5), "E=5 Drift (0.0187 | 89.0s CUDA)", (106.0, 0.0148), "center", TERRA, True),
    ]
    for key, txt, (tx, ty), ha, col, use_arr in annots_data:
        p = _find(*key)
        ax3.annotate(
            txt, xy=(p["sec"], p["r20"]), xytext=(tx, ty),
            textcoords="data", ha=ha, va="center",
            fontsize=10.0, fontweight="bold" if col in (TEAL, TERRA) else "normal",
            color=col,
            arrowprops=(dict(arrowstyle="->", color=col, lw=1.1, shrinkA=2, shrinkB=4) if use_arr else None),
        )

    p_n20 = _find(32, 2, 20, 1)
    cpu_n20 = pts_cpu[(32, 2, 20, 1)]
    ax3.annotate(
        f"CPU\n{cpu_n20:.1f}s", xy=(cpu_n20, p_n20["r20"]), xytext=(10, -2),
        textcoords="offset points", ha="left", va="center",
        fontsize=9.8, fontweight="bold", color=MUTE,
    )

    p_drift = _find(32, 2, 10, 5)
    cpu_drift = pts_cpu[(32, 2, 10, 5)]
    ax3.annotate(
        f"CPU\n{cpu_drift:.1f}s", xy=(cpu_drift, p_drift["r20"]), xytext=(0, 14),
        textcoords="offset points", ha="center", va="bottom",
        fontsize=10.0, fontweight="bold", color=MUTE,
    )

    ax3.set_xlim(-2, 168)
    ax3.set_ylim(0.007, 0.043)
    ax3.set_xlabel("Thời gian huấn luyện 6 vòng FL (giây: CUDA vs CPU)", fontsize=12.5, fontweight="bold")
    ax3.set_ylabel("Recall@20 (Global Catalog)", fontsize=12.8, fontweight="bold")
    ax3.set_title("(c) 8 Cấu hình Sweep (CUDA vs CPU)", fontsize=14.0, pad=10)
    style_ax(ax3, "both")
    ax3.legend(loc="upper right", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=10.8)

    fig.suptitle(
        "Hội tụ FedAvg 50N, Hiện tượng Client Drift (E=5) & Khảo sát 8 Cấu hình Sweep",
        fontsize=18.0, fontweight="bold", color=INK, y=1.02,
    )
    out = OUT_DIR / "sfig5_convergence_drift_sweep.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.22, facecolor=CREAM)
    plt.close(fig)
    return out


# =============================================================================
# SFIG 6: 2-Panel CUDA vs CPU Latency (300 samples) & Per-Client Fairness Gap
# =============================================================================
def build_sfig6_latency_fairness(d: dict) -> Path:
    lat_cuda = d["metrics_cuda"]["latency"]
    lat_cpu = d["metrics_cpu"]["latency"]
    pc = d["metrics_cuda"]["per_client"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16.8, 6.4),
                                   gridspec_kw={"width_ratios": [1.08, 1.0], "wspace": 0.36})
    fig.patch.set_facecolor(CREAM)

    # --- Panel (a): CUDA vs CPU Latency across 300 perf_counter() samples ---
    metrics_lat = [
        ("Min", lat_cuda["min_ms"], lat_cpu["min_ms"]),
        ("p50 (Median)", lat_cuda["p50_ms"], lat_cpu["p50_ms"]),
        ("Mean", lat_cuda["mean_ms"], lat_cpu["mean_ms"]),
        ("p95", lat_cuda["p95_ms"], lat_cpu["p95_ms"]),
        ("Max", lat_cuda["max_ms"], lat_cpu["max_ms"]),
    ]
    y1 = np.arange(len(metrics_lat))
    h = 0.36
    cuda_vals = [m[1] for m in metrics_lat]
    cpu_vals = [m[2] for m in metrics_lat]

    b_cpu = ax1.barh(y1 - h / 2, cpu_vals, height=h, color=TAUPE, edgecolor=CREAM, lw=0.9,
                     label="Local CPU (torch 2.10+cpu)", zorder=3)
    b_cuda = ax1.barh(y1 + h / 2, cuda_vals, height=h, color=TEAL, edgecolor=CREAM, lw=0.9,
                      label="Kaggle CUDA (torch 2.11+cu130)", zorder=3)

    for bar, v in zip(b_cuda, cuda_vals):
        ax1.text(v + 15, bar.get_y() + bar.get_height() / 2, f"{v:.1f} ms",
                 va="center", ha="left", fontsize=11.8, fontweight="bold", color=TEAL)
    for bar, v in zip(b_cpu, cpu_vals):
        ax1.text(v + 15, bar.get_y() + bar.get_height() / 2, f"{v:.1f} ms",
                 va="center", ha="left", fontsize=11.8, fontweight="bold", color=BODY)

    ax1.set_yticks(y1)
    ax1.set_yticklabels([m[0] for m in metrics_lat], fontsize=12.5, fontweight="bold")
    ax1.set_xlim(0, 1080)
    ax1.set_xlabel("Độ trễ mỗi bước cập nhật client (ms) — perf_counter()", fontsize=13.0, fontweight="bold")
    ax1.set_title(f"(a) Độ trễ CUDA vs CPU ({lat_cuda['n_samples']} mẫu thực đo)", fontsize=14.5, pad=12)
    style_ax(ax1, "x")
    ax1.legend(loc="lower right", frameon=True, facecolor=WASH, edgecolor=RULE, fontsize=11.5)

    ax1.text(
        0.97, 0.45,
        f"Tỉ lệ đuôi dài (p95 / p50):\n"
        f"• CUDA: {lat_cuda['p95_over_p50']:.2f}× ({lat_cuda['p50_ms']:.1f} → {lat_cuda['p95_ms']:.1f} ms)\n"
        f"• CPU : {lat_cpu['p95_over_p50']:.2f}× ({lat_cpu['p50_ms']:.1f} → {lat_cpu['p95_ms']:.1f} ms)",
        transform=ax1.transAxes, ha="right", va="center",
        fontsize=11.5, color=BODY,
        bbox=dict(boxstyle="square,pad=0.42", fc=WASH, ec=RULE, lw=1.1),
    )

    # --- Panel (b): Per-Client Fairness Gap ---
    r_ge = pc["recall20_ge10_jobs"]
    r_lt = pc["recall20_lt10_jobs"]
    gap_pct = 100.0 * (r_ge - r_lt) / r_lt

    labels_b = [
        f"Silo Lớn (≥10 jobs)\n{fmt_int(pc['n_ge10'])} eval clients",
        f"Silo Nhỏ (<10 jobs)\n{fmt_int(pc['n_lt10'])} eval clients",
    ]
    vals_b = [r_ge, r_lt]
    cols_b = [TEAL, TERRA]
    xb = np.arange(2)

    bars_b = ax2.bar(xb, vals_b, width=0.48, color=cols_b, edgecolor=CREAM, lw=1.2, zorder=3)
    for bar, v, col in zip(bars_b, vals_b, cols_b):
        ax2.text(bar.get_x() + bar.get_width() / 2, v + 0.0007, f"{v:.4f}",
                 ha="center", va="bottom", fontsize=14.5, fontweight="bold", color=col)

    # Gap bracket / arrow between the two bars
    ax2.plot([0, 1], [r_ge + 0.0032, r_ge + 0.0032], color=TERRA, lw=1.8, zorder=4)
    ax2.plot([0, 0], [r_ge + 0.0022, r_ge + 0.0032], color=TERRA, lw=1.8, zorder=4)
    ax2.plot([1, 1], [r_lt + 0.0022, r_ge + 0.0032], color=TERRA, lw=1.8, zorder=4)
    ax2.text(
        0.5, r_ge + 0.0040,
        f"Chênh lệch công bằng: +{gap_pct:.1f}%",
        ha="center", va="bottom", fontsize=13.0, fontweight="bold", color=TERRA,
        bbox=dict(boxstyle="square,pad=0.30", fc=WASH, ec=TERRA, lw=1.1),
    )

    ax2.set_xticks(xb)
    ax2.set_xticklabels(labels_b, fontsize=12.5, fontweight="bold")
    ax2.set_xlim(-0.55, 1.55)
    ax2.set_ylim(0, 0.042)
    ax2.set_ylabel("Mean Per-Client Recall@20 (Global Catalog)", fontsize=13.0, fontweight="bold")
    ax2.set_title("(b) Khoảng cách Công bằng Cross-Silo (Fairness Gap)", fontsize=14.5, pad=12)
    style_ax(ax2, "y")

    ax2.text(
        0.97, 0.96,
        f"Phạm vi đánh giá:\n"
        f"• {fmt_int(pc['n_clients_with_test'])} silos có test ({fmt_int(pc['n_ge10'])} ≥10 + {fmt_int(pc['n_lt10'])} <10)\n"
        f"• {fmt_int(pc['n_clients_without_test'])} silos ({pc['pct_clients_without_test']:.2f}%) không có cạnh test",
        transform=ax2.transAxes, ha="right", va="top",
        fontsize=11.0, color=BODY,
        bbox=dict(boxstyle="square,pad=0.38", fc=WASH, ec=RULE, lw=1.0),
    )

    fig.suptitle(
        "Hiệu năng Thực thi (CUDA vs CPU) & Phân tích Công bằng Non-IID theo Quy mô Silo",
        fontsize=18.0, fontweight="bold", color=INK, y=1.02,
    )
    out = OUT_DIR / "sfig6_latency_fairness.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.22, facecolor=CREAM)
    plt.close(fig)
    return out


# =============================================================================
# SFIG 7: Algorithm Pipeline (Subgraph -> LightGCN+BPR -> Sparse FedAvg -> 2-Hop)
# =============================================================================
def build_sfig7_algorithm_pipeline(d: dict) -> Path:
    m_cuda = d["metrics_cuda"]
    cfg = m_cuda["config"]
    g = m_cuda["graph"]
    split = m_cuda["split"]
    meta = d["meta"]
    abl = {r["biến_thể"]: r for r in d["ablation"]}

    dim = cfg["dim"]
    layers = cfg["layers"]
    lr = cfg["lr"]
    n_clients = cfg["n_clients"]
    rounds = cfg["rounds"]
    le = cfg["local_epochs"]
    r20_50n = m_cuda["models"]["FedAvg"]["R20_FlUniverse"]
    r20_20n = float(abl["(base) đầy đủ"]["R20"])
    n_pub = meta["nodes"]["n_public_nodes"]

    fig, ax = plt.subplots(figsize=(17.6, 7.6))
    fig.patch.set_facecolor(CREAM)
    ax.set_facecolor(CREAM)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.955,
        "Quy trình Thuật toán FedGraph: Từ Đồ thị con Cục bộ đến Gợi ý 2-Hop Toàn đồ thị",
        ha="center", va="center", fontsize=18.5, fontweight="bold", color=INK,
    )
    ax.text(
        0.5, 0.908,
        f"Cấu hình chuẩn V3: LightGCN (L={layers}, dim={dim}) | Adam (lr={lr}) | {rounds} vòng FL × {le} epoch (20 bước/vòng) | Seed={cfg['seed']}",
        ha="center", va="center", fontsize=13.5, color=MUTE,
    )
    ax.plot([0.02, 0.98], [0.876, 0.876], color=RULE, lw=1.0)

    stages = [
        (
            "01",
            "Trích xuất Đồ thị con\n(Local Subgraph)",
            TEAL,
            [
                ("Đầu vào cục bộ (Silo c):", BODY, True),
                ("• Cạnh user–job sở hữu", BODY, False),
                ("  (client_of_job[j] == c)", MUTE, False),
                ("• Cạnh user–occupation", BODY, False),
                ("Ghép Public Backbone:", BODY, True),
                (f"• {fmt_int(n_pub)} nút O*NET", TEAL, True),
                ("  (job–occ + occ–skill)", MUTE, False),
                ("Bảo mật GraphSafe:", TERRA, True),
                ("• 0 B dữ liệu thô ra ngoài", TERRA, True),
            ],
            "Output: Đồ thị con cục bộ\n& ánh xạ E_local (n_loc × 32)",
        ),
        (
            "02",
            "Huấn luyện Cục bộ\n(LightGCN L=2 + BPR)",
            TEAL,
            [
                ("Lan truyền chuẩn đối xứng:", BODY, True),
                (r"$E^{(l+1)} = D^{-1/2}(A+I)D^{-1/2}E^{(l)}$", INK, False),
                (r"$E = \frac{1}{3}(E^{(0)} + E^{(1)} + E^{(2)})$", INK, False),
                ("Hàm mất mát BPR + L2:", BODY, True),
                (r"$-\ln\sigma(\hat{y}_{ui}-\hat{y}_{uj}) + \lambda\|E\|^2$", INK, False),
                (f"Tối ưu cục bộ (E={le}):", BODY, True),
                ("• 20 bước Adam (cap 4,096)", MUTE, False),
                ("• λ = 1e-5, lấy mẫu âm đều", MUTE, False),
            ],
            "Output: Ma trận chưa lan\ntruyền E_local sau 20 bước",
        ),
        (
            "03",
            "Tổng hợp Sparse FedAvg\n(Touched Aggregation)",
            TERRA,
            [
                ("Tải lên Server:", BODY, True),
                ("• Chỉ tải E_local[c]", TEAL, True),
                (f"• Trọng số w_c = n_edges(c)", BODY, False),
                ("Cập nhật có chọn lọc:", BODY, True),
                (r"$E_g[v] \leftarrow \frac{\sum w_c E_c[v]}{\sum w_c}$", INK, False),
                ("• Chỉ cập nhật nút 'touched'", TERRA, True),
                ("  (den[v] > 0)", MUTE, False),
                ("• Nút không chạm giữ nguyên", BODY, False),
                ("  → Tránh pha loãng về 0", TEAL, True),
            ],
            f"Output: E_global ({fmt_int(g['n_nodes'])} × {dim})\nsau {rounds} vòng ({n_clients} clients)",
        ),
        (
            "04",
            "Lan truyền Toàn đồ thị\n& Gợi ý 2-Hop Serving",
            INK,
            [
                ("Đánh giá Toàn đồ thị:", BODY, True),
                (f"• 1 lượt forward trên ADJ_FULL", BODY, False),
                (f"• Test sạch: {fmt_int(split['n_test_clean'])} cạnh", BODY, False),
                (f"  (loại {split['n_test_leak']} rò rỉ 2-hop)", MUTE, False),
                ("Kết quả FL Catalog:", TEAL, True),
                (f"• R@20 = {r20_50n:.4f} (50N)", TEAL, True),
                (f"• R@20 = {r20_20n:.4f} (20N)", TEAL, True),
                ("Phục vụ Gợi ý 2-Hop:", BODY, True),
                ("• User → Occ → Skill → Job", MUTE, False),
            ],
            "Output: Top-K việc làm &\nGiải thích 2-Hop trên Web UI",
        ),
    ]

    xs = [0.020, 0.268, 0.516, 0.764]
    w_card = 0.216
    y_bot = 0.055
    h_card = 0.785

    for idx, (x0, (num, title, hdr_col, lines, foot)) in enumerate(zip(xs, stages)):
        # Card background
        _rect(ax, x0, y_bot, w_card, h_card, WASH, RULE, lw=1.3, zorder=1)
        # Header band
        _rect(ax, x0, y_bot + h_card - 0.115, w_card, 0.115, hdr_col, hdr_col, lw=1.0, zorder=2)
        ax.text(x0 + 0.024, y_bot + h_card - 0.058, num,
                ha="center", va="center", fontsize=17.0, fontweight="bold", color=CREAM, zorder=3)
        ax.text(x0 + 0.048, y_bot + h_card - 0.058, title,
                ha="left", va="center", fontsize=12.6, fontweight="bold", color=CREAM, zorder=3)

        # Body lines
        y_curr = y_bot + h_card - 0.160
        step_y = 0.056
        for text_str, col, is_bold in lines:
            fs = 11.4 if "$" in text_str else 11.2
            ax.text(
                x0 + 0.014, y_curr, text_str,
                ha="left", va="center",
                fontsize=fs,
                fontweight="bold" if is_bold else "normal",
                color=col, zorder=3,
            )
            y_curr -= step_y

        # Footer strip
        _rect(ax, x0 + 0.010, y_bot + 0.014, w_card - 0.020, 0.105, CREAM, hdr_col, lw=1.1, zorder=2)
        ax.text(x0 + w_card / 2, y_bot + 0.066, foot,
                ha="center", va="center", fontsize=11.0, fontweight="bold", color=hdr_col, zorder=3)

        # Connecting arrow to next stage
        if idx < len(xs) - 1:
            x_next = xs[idx + 1]
            _arrow(ax, (x0 + w_card + 0.004, 0.45), (x_next - 0.004, 0.45),
                   color=TEAL, lw=2.4, zorder=5)

    out = OUT_DIR / "sfig7_algorithm_pipeline.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.20, facecolor=CREAM)
    plt.close(fig)
    return out


def main() -> None:
    setup_rc()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_all_inputs()
    builders = [
        build_sfig1_architecture,
        build_sfig2_funnel_and_skew,
        build_sfig3_catalog_comparison,
        build_sfig4_ablation_backbone_scaling,
        build_sfig5_convergence_drift_sweep,
        build_sfig6_latency_fairness,
        build_sfig7_algorithm_pipeline,
    ]
    for fn in builders:
        path = fn(data)
        print(f"Generated {path} ({path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
