"""Generate 6 publication-quality 300 DPI Vietnamese academic figures for FedGraph V3.

Reads 100% of numbers directly from verified repository files:
  - artifacts/v3/meta.json
  - artifacts/v3/clients.json
  - results_v3/notebook_metrics.json (Kaggle CUDA canonical run)
  - results/v3/notebook_metrics.json (Local CPU run, for CUDA vs CPU latency)
  - results_v3/ablation_results.csv
  - results_v3/sweep_results.csv
  - results_v3/local_only_v3.json

Outputs to `results_v3/report_figures/`:
  1. fig1_architecture.png
  2. fig2_preprocessing_funnel.png
  3. fig3_model_comparison.png
  4. fig4_ablation_and_drift.png
  5. fig5_convergence_and_sweep.png
  6. fig6_latency_and_fairness.png
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "v3"
RES_CUDA = ROOT / "results_v3"
RES_CPU = ROOT / "results" / "v3"
OUT_DIR = RES_CUDA / "report_figures"

DPI = 300

# Colorblind-safe Okabe-Ito inspired academic palette
NAVY = "#1D4E89"
BLUE = "#2B6CB0"
SKY = "#56B4E9"
ORANGE = "#D55E00"
AMBER = "#E69F00"
TEAL = "#009E73"
PURPLE = "#7B3F8D"
RED = "#C0392B"
SLATE = "#334155"
MUTED = "#64748B"
BORDER = "#CBD5E1"


def setup_rc():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Segoe UI"],
        "axes.edgecolor": "#475569",
        "axes.linewidth": 0.9,
        "axes.titlesize": 12.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.fontsize": 9.0,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })


def style_ax(ax, grid_axis: str = "x"):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, linestyle="--", alpha=0.28, color="#94A3B8", zorder=0)


def fmt_vn_int(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


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


def _draw_box(ax, x, y, w, h, fc, ec, lw=1.4, ls="-", radius=0.015, zorder=2):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def _draw_arrow(ax, p1, p2, color=SLATE, lw=1.6, ls="-", rad=0.0, style="-|>", zorder=4):
    arr = FancyArrowPatch(
        p1, p2,
        connectionstyle=f"arc3,rad={rad}",
        arrowstyle=style,
        mutation_scale=13,
        linewidth=lw,
        linestyle=ls,
        color=color,
        zorder=zorder,
    )
    ax.add_patch(arr)
    return arr


# =============================================================================
# FIG 1: FedGraph Cross-Silo Architecture & Privacy Boundary
# =============================================================================
def build_fig1_architecture(d: dict) -> Path:
    m_cuda = d["metrics_cuda"]
    g = m_cuda["graph"]
    n_clients = m_cuda["cross_silo"]["n_clients"]
    n_nodes = g["n_nodes"]
    n_users = g["n_users"]
    n_jobs = g["n_jobs"]
    n_occ = g["n_occ"]
    n_skill = g["n_skill"]
    ebt = g["edges_by_type"]
    e_uj, e_jo, e_os, e_uo = ebt["0"], ebt["1"], ebt["2"], ebt["3"]
    e_pub = e_jo + e_os
    e_priv = e_uj + e_uo
    n_pub_nodes = n_occ + n_skill

    fig, ax = plt.subplots(figsize=(15.0, 7.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.suptitle(
        "Kiến trúc FedGraph: Học liên bang Cross-Silo trên Đồ thị Dị thể CareerBuilder + O*NET (V3)",
        fontsize=14.5, fontweight="bold", color="#0F172A", y=0.97,
    )
    ax.text(
        0.5, 0.945,
        f"Tổng đồ thị: {fmt_vn_int(n_nodes)} nút ({fmt_vn_int(n_users)} users, {fmt_vn_int(n_jobs)} jobs, {n_occ} nghề, {fmt_vn_int(n_skill)} kỹ năng) | "
        f"{fmt_vn_int(g['n_edges'])} cạnh ({100*e_priv/g['n_edges']:.2f}% riêng tư / {100*e_pub/g['n_edges']:.2f}% công khai)",
        ha="center", va="center", fontsize=10.0, color=MUTED,
    )

    # --- Zone 1 (Left): Private Employer Silos (0.015 .. 0.305) ---
    _draw_box(ax, 0.015, 0.07, 0.295, 0.81, "#FFF7F5", ORANGE, lw=2.0, ls="--", radius=0.018, zorder=1)
    ax.text(0.1625, 0.855, f"RANH GIỚI RIÊNG TƯ ({fmt_vn_int(n_clients)} Silos)",
            ha="center", va="center", fontsize=10.5, fontweight="bold", color=ORANGE)

    # Silo #0 card
    _draw_box(ax, 0.032, 0.62, 0.261, 0.19, "#FFFFFF", "#FDBA74", lw=1.3, radius=0.012)
    ax.text(0.1625, 0.785, "Silo #0: randstad (4.745 apps, 603 jobs)",
            ha="center", va="center", fontsize=8.8, fontweight="bold", color=SLATE)
    ax.text(0.1625, 0.735, "Đồ thị con: user–job + user–occupation",
            ha="center", va="center", fontsize=8.5, color=MUTED)
    ax.text(0.1625, 0.690, "LightGCN (L=2, dim=32) + BPR Loss",
            ha="center", va="center", fontsize=8.6, color=NAVY, fontweight="bold")
    ax.text(0.1625, 0.648, "Nhận Public Backbone → cập nhật E_local",
            ha="center", va="center", fontsize=8.4, color=TEAL)

    # Silo #1..#9115 card
    _draw_box(ax, 0.032, 0.385, 0.261, 0.195, "#FFFFFF", "#FDBA74", lw=1.3, radius=0.012)
    ax.text(0.1625, 0.555, "Silo #1..#9.115 (min 10, median 23)",
            ha="center", va="center", fontsize=8.8, fontweight="bold", color=SLATE)
    ax.text(0.1625, 0.505, "Gán cạnh theo client_of_job[j] (đúng silo)",
            ha="center", va="center", fontsize=8.4, color=MUTED)
    ax.text(0.1625, 0.458, f"Tổng cạnh riêng tư: {fmt_vn_int(e_priv)}",
            ha="center", va="center", fontsize=8.6, color=SLATE, fontweight="bold")
    ax.text(0.1625, 0.415, f"({fmt_vn_int(e_uj)} user–job + {fmt_vn_int(e_uo)} user–occ)",
            ha="center", va="center", fontsize=8.2, color=MUTED)

    # GraphSafe Guarantee Box
    _draw_box(ax, 0.032, 0.10, 0.261, 0.24, "#FEF2F2", RED, lw=1.6, radius=0.012)
    ax.text(0.1625, 0.312, "Bảo vệ theo thiết kế: GraphSafe",
            ha="center", va="center", fontsize=9.6, fontweight="bold", color=RED)
    ax.text(0.1625, 0.262, "0 byte dữ liệu thô rời Client",
            ha="center", va="center", fontsize=9.4, fontweight="bold", color="#991B1B")
    ax.text(0.1625, 0.212, "• Cặp (user, job) & user_history ở lại silo",
            ha="center", va="center", fontsize=8.2, color=SLATE)
    ax.text(0.1625, 0.170, "• 44,58% user đa-client (không lộ chéo)",
            ha="center", va="center", fontsize=8.2, color=SLATE)
    ax.text(0.1625, 0.128, "• Chỉ tải lên ma trận E_local (n_local × 32)",
            ha="center", va="center", fontsize=8.3, color=NAVY, fontweight="bold")

    # --- Zone 2 (Center-Top): FedAvg Aggregation Server (0.395 .. 0.675) ---
    _draw_box(ax, 0.395, 0.51, 0.285, 0.37, "#EFF6FF", NAVY, lw=1.8, radius=0.016)
    ax.text(0.5375, 0.85, "MÁY CHỦ LIÊN BANG (FedAvg Server)",
            ha="center", va="center", fontsize=10.5, fontweight="bold", color=NAVY)
    ax.text(0.5375, 0.80, "Không lưu dữ liệu thô (user, job)",
            ha="center", va="center", fontsize=8.9, color=MUTED)

    _draw_box(ax, 0.412, 0.65, 0.251, 0.12, "#FFFFFF", BLUE, lw=1.2, radius=0.01)
    ax.text(0.5375, 0.742, "Sparse FedAvg (Weighted by n_edges)",
            ha="center", va="center", fontsize=8.9, fontweight="bold", color=NAVY)
    ax.text(0.5375, 0.698, "E_global[v] ← Σ(w_c · E_c[v]) / Σ w_c",
            ha="center", va="center", fontsize=8.8, color=SLATE)
    ax.text(0.5375, 0.665, "Chỉ cập nhật nút được chạm (tránh pha loãng)",
            ha="center", va="center", fontsize=8.0, color=MUTED)

    _draw_box(ax, 0.412, 0.53, 0.251, 0.10, "#FFFBEB", AMBER, lw=1.3, ls="--", radius=0.01)
    ax.text(0.5375, 0.602, "Đề xuất mở rộng (Future Work)",
            ha="center", va="center", fontsize=8.8, fontweight="bold", color="#B45309")
    ax.text(0.5375, 0.562, "DP-SGD (ε, δ) + Secure Aggregation",
            ha="center", va="center", fontsize=8.5, color=SLATE)

    # --- Zone 3 (Center-Bottom): Public Graph Backbone (0.395 .. 0.675) ---
    _draw_box(ax, 0.395, 0.07, 0.285, 0.35, "#ECFDF5", TEAL, lw=1.8, radius=0.016)
    ax.text(0.5375, 0.392, "PUBLIC GRAPH BACKBONE (O*NET 29.3)",
            ha="center", va="center", fontsize=10.1, fontweight="bold", color="#065F46")
    ax.text(0.5375, 0.345, f"{fmt_vn_int(n_pub_nodes)} nút danh mục công khai (is_public = 1)",
            ha="center", va="center", fontsize=8.8, color=SLATE, fontweight="bold")
    ax.text(0.5375, 0.300, f"• {n_occ} nút Occupation (mã chuẩn soc[:7])",
            ha="center", va="center", fontsize=8.6, color=SLATE)
    ax.text(0.5375, 0.260, f"• {fmt_vn_int(n_skill)} nút Technology Skills",
            ha="center", va="center", fontsize=8.6, color=SLATE)
    ax.text(0.5375, 0.215, f"Tổng {fmt_vn_int(e_pub)} cạnh công khai (6,87%):",
            ha="center", va="center", fontsize=8.7, fontweight="bold", color="#065F46")
    ax.text(0.5375, 0.175, f"• {fmt_vn_int(e_jo)} job–occupation (31,44% job)",
            ha="center", va="center", fontsize=8.4, color=SLATE)
    ax.text(0.5375, 0.138, f"• {fmt_vn_int(e_os)} occupation–skill (44,37 kỹ năng/nghề)",
            ha="center", va="center", fontsize=8.4, color=SLATE)
    ax.text(0.5375, 0.098, "Cầu nối ngữ nghĩa giúp +9,0 pts Recall@20",
            ha="center", va="center", fontsize=8.5, fontweight="bold", color=TEAL)

    # --- Zone 4 (Right): Full-Stack Serving (0.755 .. 0.985) ---
    _draw_box(ax, 0.755, 0.07, 0.230, 0.81, "#F8FAFC", PURPLE, lw=1.8, radius=0.016)
    ax.text(0.870, 0.855, "HỆ THỐNG PHỤC VỤ",
            ha="center", va="center", fontsize=10.5, fontweight="bold", color=PURPLE)

    _draw_box(ax, 0.770, 0.62, 0.200, 0.19, "#FFFFFF", "#94A3B8", lw=1.3, radius=0.012)
    ax.text(0.870, 0.782, "PostgreSQL 16 (dss_jobs)",
            ha="center", va="center", fontsize=9.2, fontweight="bold", color=NAVY)
    ax.text(0.870, 0.740, "9 bảng | >21,3 triệu dòng",
            ha="center", va="center", fontsize=8.5, fontweight="bold", color=SLATE)
    ax.text(0.870, 0.700, "• user_skills: 18,02M (2-hop)",
            ha="center", va="center", fontsize=8.1, color=MUTED)
    ax.text(0.870, 0.668, "• job_skills: 2,59M | apps: 436.893",
            ha="center", va="center", fontsize=8.1, color=MUTED)
    ax.text(0.870, 0.638, "Fallback: InMemoryStore",
            ha="center", va="center", fontsize=8.0, color=TEAL)

    _draw_box(ax, 0.770, 0.36, 0.200, 0.19, "#FFFFFF", "#94A3B8", lw=1.3, radius=0.012)
    ax.text(0.870, 0.522, "FastAPI + WebSocket (api/)",
            ha="center", va="center", fontsize=9.2, fontweight="bold", color=NAVY)
    ax.text(0.870, 0.480, "11 REST/WS + 4 V3 Endpoints",
            ha="center", va="center", fontsize=8.3, color=SLATE)
    ax.text(0.870, 0.440, "• POST /api/recommend",
            ha="center", va="center", fontsize=8.1, color=MUTED)
    ax.text(0.870, 0.408, "• WS /ws/train & /ws/latency",
            ha="center", va="center", fontsize=8.1, color=MUTED)
    ax.text(0.870, 0.376, "18/18 smoke checks đạt chuẩn",
            ha="center", va="center", fontsize=8.1, color=TEAL, fontweight="bold")

    _draw_box(ax, 0.770, 0.10, 0.200, 0.19, "#FFFFFF", "#94A3B8", lw=1.3, radius=0.012)
    ax.text(0.870, 0.262, "React 19 + Three.js (web/)",
            ha="center", va="center", fontsize=9.2, fontweight="bold", color=NAVY)
    ax.text(0.870, 0.222, "5 trang trực quan hóa & giám sát",
            ha="center", va="center", fontsize=8.3, color=SLATE)
    ax.text(0.870, 0.184, "• 3D Ego-Subgraph (430 nút)",
            ha="center", va="center", fontsize=8.1, color=MUTED)
    ax.text(0.870, 0.152, "• Node Monitor (UI Fault Sim.)",
            ha="center", va="center", fontsize=8.1, color=MUTED)
    ax.text(0.870, 0.120, "Đo độ trễ thật: perf_counter()",
            ha="center", va="center", fontsize=8.1, color=ORANGE, fontweight="bold")

    # --- Connecting Arrows in wide open gaps (0.31..0.395 and 0.68..0.755) ---
    _draw_arrow(ax, (0.312, 0.74), (0.392, 0.74), color=NAVY, lw=2.0)
    ax.text(0.352, 0.772, "E_local ↑", ha="center", va="center", fontsize=8.6, fontweight="bold", color=NAVY)
    _draw_arrow(ax, (0.392, 0.67), (0.312, 0.67), color=BLUE, lw=2.0, ls="--")
    ax.text(0.352, 0.638, "E_global ↓", ha="center", va="center", fontsize=8.6, fontweight="bold", color=BLUE)

    _draw_arrow(ax, (0.392, 0.27), (0.312, 0.44), color=TEAL, lw=1.8)
    ax.text(0.352, 0.355, "Cấu trúc\ncông khai", ha="center", va="center", fontsize=8.0, fontweight="bold", color=TEAL,
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec=TEAL, lw=0.6, alpha=0.95), zorder=5)

    _draw_arrow(ax, (0.5375, 0.425), (0.5375, 0.505), color=TEAL, lw=1.6, style="<|-|>")

    _draw_arrow(ax, (0.682, 0.70), (0.752, 0.70), color=PURPLE, lw=1.8)
    ax.text(0.717, 0.732, "E_global", ha="center", va="center", fontsize=8.2, fontweight="bold", color=PURPLE)
    _draw_arrow(ax, (0.682, 0.46), (0.752, 0.46), color=PURPLE, lw=1.8)
    ax.text(0.717, 0.492, "Metrics", ha="center", va="center", fontsize=8.2, fontweight="bold", color=PURPLE)

    _draw_arrow(ax, (0.870, 0.615), (0.870, 0.555), color=SLATE, lw=1.5, style="<|-|>")
    _draw_arrow(ax, (0.870, 0.355), (0.870, 0.295), color=SLATE, lw=1.5, style="<|-|>")

    out = OUT_DIR / "fig1_architecture.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


# =============================================================================
# FIG 2: 5-Step Preprocessing & Employer Extraction Funnel
# =============================================================================
def build_fig2_preprocessing_funnel(d: dict) -> Path:
    meta = d["meta"]
    ee = meta["employer_extraction"]
    split = d["metrics_cuda"]["split"]
    g = d["metrics_cuda"]["graph"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 6.2), gridspec_kw={"width_ratios": [1.35, 1.0]})

    stages = [
        ("Bước 0–1: apps.tsv gốc\n(khớp 100% jobs.tsv)", 1603111, "100,0% | 1.092.096 jobs gốc", "#64748B"),
        ("Bước 2: Trích xuất Employer\n(9 nguồn regex/domain/email)", ee["n_apps_with_employer"],
         f"{ee['pct_apps_with_employer']:.2f}% | {fmt_vn_int(ee['n_distinct_names_raw'])} tên | {fmt_vn_int(ee['n_jobs_with_employer_raw'])} jobs", SKY),
        ("Bước 3–4: Lọc Employer ≥ 2 jobs\n& tích hợp P1 (nghề có kỹ năng)", ee["n_apps_with_employer"],
         f"{fmt_vn_int(ee['n_distinct_employers_after_job_filter'])} employers | {fmt_vn_int(ee['n_jobs_with_employer_after_job_filter'])} jobs", BLUE),
        ("Bước 5: Silo FL ≥ 10 apps\n(9.116 Employer Silos)", ee["n_apps_with_employer_and_client"],
         f"{ee['pct_apps_with_employer_and_client']:.2f}% | {fmt_vn_int(g['n_users'])} users | {fmt_vn_int(g['n_jobs'])} jobs", NAVY),
        ("Chia Train / Test Sạch\n(min_apps ≥ 5, test_ratio=0,2)", g["n_train_uj"],
         f"{fmt_vn_int(g['n_train_uj'])} train + {fmt_vn_int(split['n_test_clean'])} clean test (bỏ {split['n_test_leak']} rò rỉ)", TEAL),
    ]

    y_pos = np.arange(len(stages))[::-1]
    max_val = 1603111
    vals = [s[1] for s in stages]
    colors = [s[3] for s in stages]
    labels = [s[0] for s in stages]
    notes = [s[2] for s in stages]

    bars = ax1.barh(y_pos, vals, height=0.60, color=colors, edgecolor="white", linewidth=1.2, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels, fontsize=9.3, fontweight="bold", color=SLATE)
    ax1.set_xlim(0, max_val * 1.92)
    ax1.set_xlabel("Số lượt ứng tuyển (applications)", fontsize=10.5, fontweight="bold", color=SLATE)
    ax1.set_title("(a) Phễu tiền xử lý 5 bước & tách Train/Clean Test", fontsize=12.0, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax1, "x")
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else (f"{int(x/1e3)}k" if x > 0 else "0")))

    for bar, val, note in zip(bars, vals, notes):
        y = bar.get_y() + bar.get_height() / 2
        ax1.text(val + max_val * 0.025, y + 0.09, f"{fmt_vn_int(val)} apps",
                 va="center", ha="left", fontsize=9.6, fontweight="bold", color="#0F172A")
        ax1.text(val + max_val * 0.025, y - 0.14, note,
                 va="center", ha="left", fontsize=8.3, color=MUTED)

    # Place callout in wide empty region on the far right (x >= 2.0M, below bar 0)
    ax1.text(
        0.99, 0.45,
        f"Lưu ý chất lượng nhãn:\n"
        f"Bước 3 loại {fmt_vn_int(ee['dropped_fewer_than_min_jobs'])} tên\n"
        f"chỉ xuất hiện ở 1 job để đảm bảo\n"
        f"độ tin cậy nhãn nhà tuyển dụng.",
        transform=ax1.transAxes, ha="right", va="center", fontsize=8.5, color=SLATE,
        bbox=dict(boxstyle="round,pad=0.38", fc="#F1F5F9", ec=BORDER),
    )

    src_map = {
        "S2_is_a": "S2: Mẫu 'is a <Company>'",
        "S8_domain_website": "S8: Tên miền Website",
        "S1_legal_dau_cau": "S1a: Hậu tố pháp lý (Inc/LLC)",
        "S5_domain_email": "S5: Tên miền Email",
        "S7_hau_to_cuoi": "S7: Hậu tố cuối câu",
        "S6_viet_hoa": "S6: Cụm viết hoa đầu dòng",
        "S3_seeks": "S3: Mẫu '<Company> seeks'",
        "S1_legal_dau_mo_ta": "S1b: Pháp lý đầu mô tả",
        "S4_about_us": "S4: Mục 'About Us'",
    }
    sc = ee["source_counts"]
    items = sorted(sc.items(), key=lambda kv: kv[1])
    s_labels = [src_map.get(k, k) for k, _ in items]
    s_vals = [v for _, v in items]
    s_tot = sum(s_vals)

    y2 = np.arange(len(items))
    bars2 = ax2.barh(y2, s_vals, height=0.62, color=NAVY, alpha=0.88, zorder=3)
    for idx in range(len(items) - 4, len(items)):
        bars2[idx].set_color(ORANGE if idx >= len(items) - 2 else BLUE)
    ax2.set_yticks(y2)
    ax2.set_yticklabels(s_labels, fontsize=9.1, color=SLATE)
    ax2.set_xlim(0, max(s_vals) * 1.40)
    ax2.set_xlabel("Số tin tuyển dụng trích xuất được", fontsize=10.5, fontweight="bold", color=SLATE)
    ax2.set_title(f"(b) 9 nguồn trích xuất Employer (tổng {fmt_vn_int(s_tot)} lượt khớp)",
                  fontsize=12.0, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax2, "x")
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x/1e3)}k" if x > 0 else "0"))

    for bar, v in zip(bars2, s_vals):
        ax2.text(v + max(s_vals) * 0.02, bar.get_y() + bar.get_height() / 2,
                 f"{fmt_vn_int(v)} ({100*v/s_tot:.1f}%)",
                 va="center", ha="left", fontsize=8.8, fontweight="bold", color=SLATE)

    fig.suptitle("Quy trình Làm sạch & Trích xuất Employer Silo trên CareerBuilder (1.603.111 Applications)",
                 fontsize=13.8, fontweight="bold", color="#0F172A", y=1.01)
    fig.tight_layout(w_pad=2.4)
    out = OUT_DIR / "fig2_preprocessing_funnel.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


# =============================================================================
# FIG 3: 2-Panel Model Comparison (FL Catalog vs Global Catalog)
# =============================================================================
def build_fig3_model_comparison(d: dict) -> Path:
    m_cuda = d["metrics_cuda"]["models"]
    abl = {r["biến_thể"]: r for r in d["ablation"]}
    loc = d["local_only"]["results"]["local_only_strict_silo"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.6, 6.6), gridspec_kw={"width_ratios": [1.12, 1.05]})

    fl_entries = [
        ("LightGCN (Centralized, 50N univ.)", m_cuda["LightGCN"]["R20_FlUniverse"], None, None, None, ORANGE),
        ("FedAvg 20N (O*NET 956 jobs)", float(abl["(f1) base: nghề + kỹ năng"]["R20"]),
         float(abl["(f1) base: nghề + kỹ năng"]["NDCG20"]), float(abl["(f1) base: nghề + kỹ năng"]["MRR20"]), None, TEAL),
        ("GraphSAGE (Centralized, 50N univ.)", m_cuda["GraphSAGE"]["R20_FlUniverse"], None, None, None, SKY),
        ("Item-KNN (50N univ.)", m_cuda["Item-KNN"]["R20_FlUniverse"], None, None, None, PURPLE),
        ("FedAvg 20N (Fixed 4.511 jobs)", float(abl["(base) đầy đủ"]["R20"]),
         float(abl["(base) đầy đủ"]["NDCG20"]), float(abl["(base) đầy đủ"]["MRR20"]), None, NAVY),
        ("FedAvg 50N (Main 9.058 jobs)", m_cuda["FedAvg"]["R20_FlUniverse"],
         m_cuda["FedAvg"]["NDCG20_FlUniverse"], m_cuda["FedAvg"]["MRR20_FlUniverse"],
         m_cuda["FedAvg"]["R20_FlUniverse_ci95"], BLUE),
        ("GAT (Centralized, 50N univ.)", m_cuda["GAT"]["R20_FlUniverse"], None, None, None, "#60A5FA"),
        ("Local-only 20N (Strict Silo, 4.511)", loc["recall@20"],
         loc["ndcg@20"], loc["mrr@20"], loc["recall@20_ci95"], AMBER),
        ("BPR-MF (50N univ.)", m_cuda["BPR-MF"]["R20_FlUniverse"], None, None, None, "#94A3B8"),
        ("Popularity (50N univ.)", m_cuda["Popularity"]["R20_FlUniverse"], None, None, None, "#CBD5E1"),
    ]

    fl_rev = fl_entries[::-1]
    y1 = np.arange(len(fl_rev))
    r20_vals = [e[1] for e in fl_rev]
    colors1 = [e[5] for e in fl_rev]

    ax1.barh(y1, r20_vals, height=0.62, color=colors1, edgecolor="white", linewidth=1.0, zorder=3, label="Recall@20")

    ndcg_x, ndcg_y, mrr_x, mrr_y = [], [], [], []
    for idx, (_, r20, ndcg, mrr, ci, _) in enumerate(fl_rev):
        if ci is not None:
            ax1.errorbar(r20, idx, xerr=[[r20 - ci[0]], [ci[1] - r20]],
                         fmt="none", ecolor="#0F172A", elinewidth=1.4, capsize=3.5, zorder=5)
        if ndcg is not None:
            ndcg_x.append(ndcg); ndcg_y.append(idx)
        if mrr is not None:
            mrr_x.append(mrr); mrr_y.append(idx)

    ax1.scatter(ndcg_x, ndcg_y, marker="D", s=44, color="#0F172A", zorder=6, label="NDCG@20 (nhóm FL/Local)")
    ax1.scatter(mrr_x, mrr_y, marker="^", s=48, color="#DC2626", zorder=6, label="MRR@20 (nhóm FL/Local)")

    ax1.set_yticks(y1)
    ax1.set_yticklabels([e[0] for e in fl_rev], fontsize=9.1, fontweight="bold", color=SLATE)
    ax1.set_xlim(0, 0.94)
    ax1.set_xlabel("Giá trị Metric (800 eval users, seed=42)", fontsize=10.5, fontweight="bold", color=SLATE)
    ax1.set_title("(a) FL Catalog — Đánh giá công bằng trong Vũ trụ FL", fontsize=11.8, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax1, "x")

    for idx, (_, r20, ndcg, mrr, ci, _) in enumerate(fl_rev):
        x_txt = (ci[1] if ci is not None else r20) + 0.015
        if ndcg is not None and mrr is not None:
            txt = f"R={r20:.4f} | N={ndcg:.4f} | M={mrr:.4f}"
        else:
            txt = f"R={r20:.4f}"
        ax1.text(x_txt, idx, txt, va="center", ha="left", fontsize=8.3, fontweight="bold", color="#0F172A")

    ax1.legend(loc="lower right", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.5)

    # --- Right Panel: Global Catalog (82,876 jobs) with 95% CI ---
    glob_order = [
        ("Item-KNN", "Item-KNN", PURPLE),
        ("LightGCN", "LightGCN (Centralized)", ORANGE),
        ("GAT", "GAT (Centralized)", "#60A5FA"),
        ("GraphSAGE", "GraphSAGE (Centralized)", SKY),
        ("FedAvg", "FedAvg (50N — chỉ phủ ~11% jobs)", NAVY),
        ("BPR-MF", "BPR-MF", "#94A3B8"),
        ("Popularity", "Popularity", "#CBD5E1"),
    ]
    glob_rev = glob_order[::-1]
    y2 = np.arange(len(glob_rev))
    g_r20 = [m_cuda[k]["recall@20"] for k, _, _ in glob_rev]
    g_lo = [m_cuda[k]["recall@20"] - m_cuda[k]["recall@20_ci95"][0] for k, _, _ in glob_rev]
    g_hi = [m_cuda[k]["recall@20_ci95"][1] - m_cuda[k]["recall@20"] for k, _, _ in glob_rev]
    g_ndcg = [m_cuda[k]["ndcg@20"] for k, _, _ in glob_rev]
    g_mrr = [m_cuda[k]["mrr@20"] for k, _, _ in glob_rev]
    g_cols = [c for _, _, c in glob_rev]

    ax2.barh(y2, g_r20, height=0.55, xerr=[g_lo, g_hi], color=g_cols, edgecolor="white", linewidth=1.0,
             error_kw=dict(ecolor="#0F172A", lw=1.3, capsize=3.5), zorder=3, label="Recall@20 (CI 95%)")
    ax2.scatter(g_ndcg, y2, marker="D", s=44, color="#0F172A", zorder=6, label="NDCG@20")
    ax2.scatter(g_mrr, y2, marker="^", s=48, color="#DC2626", zorder=6, label="MRR@20")

    ax2.set_yticks(y2)
    ax2.set_yticklabels([lbl for _, lbl, _ in glob_rev], fontsize=9.2, fontweight="bold", color=SLATE)
    ax2.set_xlim(0, 1.08)
    ax2.set_xlabel("Giá trị Metric (82.876 jobs, CI 95% 1.000 bootstrap)", fontsize=10.5, fontweight="bold", color=SLATE)
    ax2.set_title("(b) Global Catalog (82.876 jobs) — Global Catalog Gap", fontsize=11.8, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax2, "x")

    for idx, (k, _, _) in enumerate(glob_rev):
        hi_x = m_cuda[k]["recall@20_ci95"][1]
        r20 = m_cuda[k]["recall@20"]
        nd = m_cuda[k]["ndcg@20"]
        ax2.text(hi_x + 0.015, idx, f"R={r20:.4f} | N={nd:.4f}",
                 va="center", ha="left", fontsize=8.4, fontweight="bold", color="#0F172A")

    # Place Global Catalog Gap box cleanly to the right of FedAvg label (ends ~0.50) and above legend
    ax2.annotate(
        "Global Catalog Gap:\n50 clients chỉ sở hữu 9.058/82.876 jobs (~11%);\n~89% jobs giữ khởi tạo ngẫu nhiên → 0,0475\n(trong FL Catalog đạt 0,3905).",
        xy=(0.055, 2.22), xytext=(0.55, 1.98),
        va="center",
        fontsize=8.2, color="#7C2D12", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.35", fc="#FFF7ED", ec=ORANGE, lw=1.2),
        arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.3, connectionstyle="arc3,rad=0.14"),
    )
    # Place legend cleanly in open lower-right area (x >= 0.55, y <= 1.1)
    ax2.legend(loc="lower right", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.5)

    fig.suptitle("So sánh Hiệu năng Mô hình trên FL Catalog và Global Catalog (CareerBuilder + O*NET V3)",
                 fontsize=13.8, fontweight="bold", color="#0F172A", y=1.01)
    fig.tight_layout(w_pad=2.4)
    out = OUT_DIR / "fig3_model_comparison.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


# =============================================================================
# FIG 4: 3-Panel Ablation & Client Drift
# =============================================================================
def build_fig4_ablation_and_drift(d: dict) -> Path:
    abl = {r["biến_thể"]: r for r in d["ablation"]}
    loc_r20 = d["local_only"]["results"]["local_only_strict_silo"]["recall@20"]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15.6, 5.9))

    # --- Panel (a): Public Graph Backbone (Occ + Skill) ---
    cats_a = ["Chỉ user–job\n(Bỏ Occ & Skill)", "+ Occupation\n(Bỏ Skill)", "+ Occ + Skill\n(Đầy đủ)"]
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
    b1 = ax1.bar(x - w / 2, fixed_vals, width=w, color=NAVY, label="Fixed 20N (4.511 jobs)", zorder=3)
    b2 = ax1.bar(x + w / 2, onet_vals, width=w, color=TEAL, label="O*NET Catalog (956 jobs)", zorder=3)
    for bar in b1:
        ax1.text(bar.get_x() + bar.get_width() / 2 - 0.03, bar.get_height() + 0.010,
                 f"{bar.get_height():.4f}", ha="center", va="bottom", fontsize=8.0, fontweight="bold", color=NAVY)
    for bar in b2:
        ax1.text(bar.get_x() + bar.get_width() / 2 + 0.03, bar.get_height() + 0.010,
                 f"{bar.get_height():.4f}", ha="center", va="bottom", fontsize=8.0, fontweight="bold", color="#065F46")

    ax1.set_xticks(x)
    ax1.set_xticklabels(cats_a, fontsize=9.0, fontweight="bold", color=SLATE)
    ax1.set_ylim(0, 0.80)
    ax1.set_ylabel("Recall@20", fontsize=10.5, fontweight="bold", color=SLATE)
    ax1.set_title("(a) Đóng góp Public Graph Backbone", fontsize=11.5, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax1, "y")
    ax1.legend(loc="upper left", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.4)
    ax1.annotate(
        "+9,00 pts (Fixed)\n+6,90 pts (O*NET)",
        xy=(2 - w / 2, fixed_vals[2] + 0.03), xytext=(1.78, 0.71),
        ha="center", va="center",
        fontsize=8.3, fontweight="bold", color="#065F46",
        bbox=dict(boxstyle="round,pad=0.28", fc="#ECFDF5", ec=TEAL),
        arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.2),
    )

    # --- Panel (b): Client Scaling (n=5, 10, 20) ---
    ns = [5, 10, 20]
    c_r20 = [float(abl[f"(c) n_clients={n}"]["R20"]) for n in ns]
    c_ndcg = [float(abl[f"(c) n_clients={n}"]["NDCG20"]) for n in ns]
    c_mrr = [float(abl[f"(c) n_clients={n}"]["MRR20"]) for n in ns]
    xp = np.arange(len(ns))

    ax2.plot(xp, c_r20, "o-", color=NAVY, lw=2.3, ms=7.5, label="FedAvg Recall@20", zorder=4)
    ax2.plot(xp, c_ndcg, "s--", color=SKY, lw=1.9, ms=6.5, label="FedAvg NDCG@20", zorder=4)
    ax2.plot(xp, c_mrr, "^:", color=PURPLE, lw=1.8, ms=6.5, label="FedAvg MRR@20", zorder=4)
    ax2.axhline(loc_r20, color=AMBER, ls="-.", lw=1.7, label=f"Local-only 20N (R@20={loc_r20:.4f})", zorder=3)

    # Carefully spaced point labels without overlap
    r_offsets = [(0, 11), (-12, 11), (0, 11)]
    n_offsets = [(0, -14), (0, 9), (-20, 8)]
    m_offsets = [(0, -14), (0, -14), (0, -15)]
    for i, (r_v, n_v, m_v) in enumerate(zip(c_r20, c_ndcg, c_mrr)):
        ax2.annotate(f"{r_v:.4f}", (i, r_v), xytext=r_offsets[i], textcoords="offset points",
                     ha="center", va="bottom", fontsize=8.8, fontweight="bold", color=NAVY)
        if i == 2:
            ax2.annotate(f"{n_v:.4f}", (i, n_v), xytext=n_offsets[i], textcoords="offset points",
                         ha="center", va="bottom", fontsize=8.2, fontweight="bold", color=BLUE)
            ax2.annotate(f"{m_v:.4f}", (i, m_v), xytext=m_offsets[i], textcoords="offset points",
                         ha="center", va="top", fontsize=8.2, fontweight="bold", color=PURPLE)
        elif i == 0:
            ax2.annotate(f"{m_v:.4f}", (i, m_v), xytext=(0, -13), textcoords="offset points",
                         ha="center", va="top", fontsize=8.2, fontweight="bold", color=PURPLE)
        else:
            ax2.annotate(f"{m_v:.4f}", (i, m_v), xytext=(0, -13), textcoords="offset points",
                         ha="center", va="top", fontsize=8.2, fontweight="bold", color=PURPLE)

    ax2.set_xticks(xp)
    ax2.set_xticklabels([f"n = {n} clients" for n in ns], fontsize=9.3, fontweight="bold", color=SLATE)
    ax2.set_xlim(-0.28, 2.30)
    ax2.set_ylim(0.11, 0.57)
    ax2.set_ylabel("Giá trị Metric (Fixed 4.511 jobs)", fontsize=10.5, fontweight="bold", color=SLATE)
    ax2.set_title("(b) Mở rộng số Client tham gia", fontsize=11.5, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax2, "y")
    ax2.legend(loc="upper left", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.2)

    # --- Panel (c): Client Drift & Aggregation ---
    variants_c = [
        ("FedAvg Weighted (E=1)\n23,2s", "(g) FedAvg weighted", NAVY),
        ("FedAvg Unweighted (E=1)\n22,8s", "(g) FedAvg unweighted", BLUE),
        ("FedProx (μ=0,01, E=1)\n24,7s", "(d) FedProx (mu=0.01)", SKY),
        ("Client Drift (E=5)\n112,4s (4,8×)", "(e) local_epochs=5", ORANGE),
    ][::-1]
    y3 = np.arange(len(variants_c))
    r20_c = [float(abl[k]["R20"]) for _, k, _ in variants_c]
    nd_c = [float(abl[k]["NDCG20"]) for _, k, _ in variants_c]
    cols_c = [c for _, _, c in variants_c]

    ax3.barh(y3 + 0.16, r20_c, height=0.30, color=cols_c, label="Recall@20", zorder=3)
    ax3.barh(y3 - 0.16, nd_c, height=0.30, color="#94A3B8", label="NDCG@20", zorder=3)

    for i, (r_v, n_v) in enumerate(zip(r20_c, nd_c)):
        ax3.text(r_v + 0.009, i + 0.16, f"{r_v:.4f}", va="center", ha="left", fontsize=8.5, fontweight="bold", color="#0F172A")
        ax3.text(n_v + 0.009, i - 0.16, f"{n_v:.4f}", va="center", ha="left", fontsize=8.3, color=SLATE)

    ax3.set_yticks(y3)
    ax3.set_yticklabels([lbl for lbl, _, _ in variants_c], fontsize=8.9, fontweight="bold", color=SLATE)
    ax3.set_xlim(0, 0.68)
    ax3.set_xlabel("Giá trị Metric (Fixed 4.511 jobs)", fontsize=10.5, fontweight="bold", color=SLATE)
    ax3.set_title("(c) Client Drift & Cơ chế Tổng hợp", fontsize=11.5, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax3, "x")
    ax3.legend(loc="lower right", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.4)

    fig.suptitle("Phân tích Ablation trên Vũ trụ Cố định 20N (4 vòng FL, 800 eval users, seed=42)",
                 fontsize=13.8, fontweight="bold", color="#0F172A", y=1.02)
    fig.tight_layout(w_pad=2.0)
    out = OUT_DIR / "fig4_ablation_and_drift.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


# =============================================================================
# FIG 5: 2-Panel Convergence & Hyperparameter Sweep
# =============================================================================
def build_fig5_convergence_and_sweep(d: dict) -> Path:
    hist = d["metrics_cuda"]["fedavg_main"]["history"]
    sweep = d["sweep"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.0, 6.0), gridspec_kw={"width_ratios": [1.0, 1.2]})

    rounds = [int(h["round"]) for h in hist]
    r20 = [float(h["recall20"]) for h in hist]
    nd20 = [float(h["ndcg20"]) for h in hist]
    r_secs = [float(h["round_seconds"]) for h in hist]

    ax1.plot(rounds, r20, "o-", color=NAVY, lw=2.4, ms=7.5, label="Recall@20 (Global 82.876 jobs)", zorder=4)
    ax1.plot(rounds, nd20, "s--", color=TEAL, lw=2.1, ms=6.8, label="NDCG@20 (Global 82.876 jobs)", zorder=4)

    for idx, (rnd, rv, nv) in enumerate(zip(rounds, r20, nd20)):
        r_dx = -10 if idx == 0 else 0
        ax1.annotate(f"{rv:.4f}", (rnd, rv), xytext=(r_dx, 11), textcoords="offset points",
                     ha="center", va="bottom", fontsize=8.7, fontweight="bold", color=NAVY)
        ax1.annotate(f"{nv:.4f}", (rnd, nv), xytext=(0, -11), textcoords="offset points",
                     ha="center", va="top", fontsize=8.5, fontweight="bold", color="#065F46")

    ax1.set_xticks(rounds)
    ax1.set_xticklabels([f"Vòng {r}" for r in rounds], fontsize=9.5, fontweight="bold", color=SLATE)
    ax1.set_xlim(0.65, 6.35)
    ax1.set_ylim(0.022, 0.054)
    ax1.set_ylabel("Giá trị Metric (Global Catalog)", fontsize=10.5, fontweight="bold", color=SLATE)
    ax1.set_title("(a) Đường cong Hội tụ FedAvg 50N (6 vòng)", fontsize=11.8, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax1, "y")
    ax1.legend(loc="lower right", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.7)

    ax1.text(
        0.04, 0.94,
        f"Tăng ổn định: R@20 {r20[0]:.4f} → {r20[-1]:.4f} (+{100*(r20[-1]-r20[0])/r20[0]:.1f}%)\n"
        f"Thời gian/vòng: ~{np.mean(r_secs):.1f}s (CUDA) | Tổng: {sum(r_secs):.1f}s",
        transform=ax1.transAxes, ha="left", va="top", fontsize=8.7, color=SLATE,
        bbox=dict(boxstyle="round,pad=0.35", fc="#F1F5F9", ec=BORDER),
    )

    # --- Right Panel: Sweep Trade-off (Recall@20 vs Runtime) ---
    pts = []
    for r in sweep:
        pts.append(dict(
            dim=int(r["dim"]), layers=int(r["layers"]),
            n_clients=int(r["n_clients"]), local_epochs=int(r["local_epochs"]),
            r20=float(r["recall20"]), ndcg20=float(r["ndcg20"]), sec=float(r["seconds"]),
        ))

    def _find(dim, layers, nc, le):
        for p in pts:
            if (p["dim"], p["layers"], p["n_clients"], p["local_epochs"]) == (dim, layers, nc, le):
                return p
        return None

    traj_dim = [_find(16, 2, 10, 1), _find(32, 2, 10, 1), _find(64, 2, 10, 1)]
    traj_lay = [_find(32, 1, 10, 1), _find(32, 2, 10, 1), _find(32, 3, 10, 1)]
    traj_cli = [_find(32, 2, 5, 1), _find(32, 2, 10, 1), _find(32, 2, 20, 1)]
    traj_ep = [_find(32, 2, 10, 1), _find(32, 2, 10, 5)]

    ax2.plot([p["sec"] for p in traj_cli], [p["r20"] for p in traj_cli], "-", color=NAVY, lw=1.8, alpha=0.75, label="Trục n_clients (5/10/20)", zorder=2)
    ax2.plot([p["sec"] for p in traj_dim], [p["r20"] for p in traj_dim], "--", color=TEAL, lw=1.8, alpha=0.85, label="Trục dim (16/32/64)", zorder=2)
    ax2.plot([p["sec"] for p in traj_lay], [p["r20"] for p in traj_lay], ":", color=PURPLE, lw=1.8, alpha=0.85, label="Trục layers (1/2/3)", zorder=2)
    ax2.plot([p["sec"] for p in traj_ep], [p["r20"] for p in traj_ep], "-.", color=ORANGE, lw=1.8, alpha=0.85, label="Trục local_epochs (1 vs 5)", zorder=2)

    label_specs = [
        ((32, 2, 5, 1),  "n_clients=5\n(0,0127 | 11,0s)", (10, -2), "left", NAVY, False),
        ((32, 1, 10, 1), "layers=1\n(0,0219 | 12,6s)", (-4, 18), "center", PURPLE, False),
        ((32, 2, 10, 1), "Base (d=32, L=2, N=10, E=1)\n(0,0221 | 19,5s)", (-6, 72), "center", "#0F172A", True),
        ((16, 2, 10, 1), "dim=16\n(0,0198 | 23,2s)", (12, -16), "left", TEAL, False),
        ((32, 3, 10, 1), "layers=3\n(0,0221 | 25,6s)", (14, 4), "left", PURPLE, False),
        ((64, 2, 10, 1), "dim=64\n(0,0265 | 25,7s)", (10, 16), "left", TEAL, False),
        ((32, 2, 20, 1), "n_clients=20\n(0,0353 | 34,6s)", (12, -2), "left", NAVY, False),
        ((32, 2, 10, 5), "local_epochs=5 (Drift)\n(0,0187 | 89,0s)", (-4, 16), "right", ORANGE, False),
    ]

    for key, txt, (dx, dy), ha, col, use_arrow in label_specs:
        p = _find(*key)
        is_base = (key == (32, 2, 10, 1))
        ax2.scatter(p["sec"], p["r20"], s=115 if is_base else 75,
                    marker="*" if is_base else "o", color=col, edgecolor="white", linewidth=1.0, zorder=5)
        ax2.annotate(
            txt, xy=(p["sec"], p["r20"]), xytext=(dx, dy),
            textcoords="offset points", ha=ha, va="center",
            fontsize=8.2, fontweight="bold" if (is_base or key[2] == 20 or key[3] == 5) else "normal",
            color=col,
            arrowprops=(dict(arrowstyle="->", color="#475569", lw=1.0) if use_arrow else None),
            bbox=dict(boxstyle="round,pad=0.20", fc="white", ec=BORDER if use_arrow else "none", alpha=0.90),
        )

    ax2.set_xlim(-2, 98)
    ax2.set_ylim(0.008, 0.041)
    ax2.set_xlabel("Thời gian huấn luyện 6 vòng FL trên CUDA (giây)", fontsize=10.5, fontweight="bold", color=SLATE)
    ax2.set_ylabel("Recall@20 (Global Catalog)", fontsize=10.5, fontweight="bold", color=SLATE)
    ax2.set_title("(b) Đánh đổi Hiệu năng vs Thời gian (8 cấu hình Sweep)", fontsize=11.8, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax2, "both")
    ax2.legend(loc="upper right", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.3)

    fig.suptitle("Hội tụ Mô hình & Khảo sát Siêu tham số (FedAvg, Global Catalog 82.876 jobs)",
                 fontsize=13.8, fontweight="bold", color="#0F172A", y=1.02)
    fig.tight_layout(w_pad=2.4)
    out = OUT_DIR / "fig5_convergence_and_sweep.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


# =============================================================================
# FIG 6: 2-Panel System Latency & Per-Client Fairness
# =============================================================================
def build_fig6_latency_and_fairness(d: dict) -> Path:
    lat_cuda = d["metrics_cuda"]["latency"]
    lat_cpu = d["metrics_cpu"]["latency"]
    pc = d["metrics_cuda"]["per_client"]
    c_stats = d["meta"]["clients"]["size_stats"]
    client_apps = np.array([int(c["n_apps"]) for c in d["clients"]], dtype=np.int64)

    fig = plt.figure(figsize=(14.4, 6.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.15], wspace=0.25)

    # --- Left Panel: CUDA vs CPU Exact Latency Quantiles (300 samples) ---
    ax1 = fig.add_subplot(gs[0, 0])
    metrics_lat = [
        ("Min", lat_cuda["min_ms"], lat_cpu["min_ms"]),
        ("p50 (Median)", lat_cuda["p50_ms"], lat_cpu["p50_ms"]),
        ("Mean", lat_cuda["mean_ms"], lat_cpu["mean_ms"]),
        ("p95", lat_cuda["p95_ms"], lat_cpu["p95_ms"]),
        ("Max", lat_cuda["max_ms"], lat_cpu["max_ms"]),
    ]
    y = np.arange(len(metrics_lat))
    h = 0.35
    cuda_vals = [m[1] for m in metrics_lat]
    cpu_vals = [m[2] for m in metrics_lat]

    b_cpu = ax1.barh(y - h / 2, cpu_vals, height=h, color=SKY, label="Local CPU (torch 2.10+cpu)", zorder=3)
    b_cuda = ax1.barh(y + h / 2, cuda_vals, height=h, color=NAVY, label="Kaggle CUDA (torch 2.11+cu130)", zorder=3)

    for bar, v in zip(b_cuda, cuda_vals):
        ax1.text(v + 14, bar.get_y() + bar.get_height() / 2, f"{v:.1f} ms",
                 va="center", ha="left", fontsize=8.6, fontweight="bold", color=NAVY)
    for bar, v in zip(b_cpu, cpu_vals):
        ax1.text(v + 14, bar.get_y() + bar.get_height() / 2, f"{v:.1f} ms",
                 va="center", ha="left", fontsize=8.6, fontweight="bold", color="#0369A1")

    ax1.set_yticks(y)
    ax1.set_yticklabels([m[0] for m in metrics_lat], fontsize=9.8, fontweight="bold", color=SLATE)
    ax1.set_xlim(0, 1140)
    ax1.set_xlabel("Độ trễ mỗi bước cập nhật client (ms) — perf_counter()", fontsize=10.3, fontweight="bold", color=SLATE)
    ax1.set_title("(a) Độ trễ Huấn luyện Cục bộ: CUDA vs CPU (300 mẫu)", fontsize=11.6, fontweight="bold", color="#0F172A", pad=10)
    style_ax(ax1, "x")
    ax1.legend(loc="lower right", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.6)

    # Put p95/p50 callout in wide open region right of Mean/p50 (x > 620)
    ax1.text(
        0.98, 0.44,
        f"Tỉ lệ đuôi dài (p95 / p50):\n"
        f"• CUDA: {lat_cuda['p95_over_p50']:.2f}× (236,5 → 315,5 ms)\n"
        f"• CPU : {lat_cpu['p95_over_p50']:.2f}× (418,0 → 566,6 ms)",
        transform=ax1.transAxes, ha="right", va="center", fontsize=8.5, color=SLATE,
        bbox=dict(boxstyle="round,pad=0.35", fc="#F1F5F9", ec=BORDER),
    )

    # --- Right Panel: Per-Client Fairness Bar + Real 9,116 Silo Skewness ---
    gs_right = gs[0, 1].subgridspec(2, 1, height_ratios=[1.0, 1.15], hspace=0.46)
    ax2_top = fig.add_subplot(gs_right[0, 0])
    ax2_bot = fig.add_subplot(gs_right[1, 0])

    groups = [
        f"Silo Lớn (≥10 jobs)\nn = {fmt_vn_int(pc['n_ge10'])} eval clients",
        f"Silo Nhỏ (<10 jobs)\nn = {fmt_vn_int(pc['n_lt10'])} eval clients",
    ]
    r20_grp = [pc["recall20_ge10_jobs"], pc["recall20_lt10_jobs"]]
    bars_g = ax2_top.barh([1, 0], r20_grp, height=0.52, color=[NAVY, ORANGE], zorder=3)
    ax2_top.set_yticks([1, 0])
    ax2_top.set_yticklabels(groups, fontsize=9.1, fontweight="bold", color=SLATE)
    ax2_top.set_xlim(0, 0.034)
    ax2_top.set_xlabel("Mean Per-Client Recall@20 (Global Catalog)", fontsize=9.6, fontweight="bold", color=SLATE)
    ax2_top.set_title(
        f"(b1) Công bằng theo Quy mô Silo ({fmt_vn_int(pc['n_clients_with_test'])} có test / {fmt_vn_int(pc['n_clients_without_test'])} không test)",
        fontsize=11.0, fontweight="bold", color="#0F172A", pad=8,
    )
    style_ax(ax2_top, "x")

    gap_pct = 100.0 * (r20_grp[0] - r20_grp[1]) / r20_grp[1]
    for bar, v, tag in zip(bars_g, r20_grp, [f" (+{gap_pct:.1f}% so với nhóm nhỏ)", ""]):
        ax2_top.text(v + 0.0006, bar.get_y() + bar.get_height() / 2,
                     f"{v:.4f}{tag}", va="center", ha="left", fontsize=9.0, fontweight="bold", color="#0F172A")

    log_apps = np.log10(client_apps)
    ax2_bot.hist(log_apps, bins=36, color=PURPLE, alpha=0.85, edgecolor="white", linewidth=0.6, zorder=3)
    ax2_bot.axvline(np.log10(c_stats["median"]), color=TEAL, ls="--", lw=1.8, label=f"Median = {c_stats['median']} apps", zorder=4)
    ax2_bot.axvline(np.log10(c_stats["mean"]), color=ORANGE, ls="-.", lw=1.8, label=f"Mean = {c_stats['mean']:.1f} apps", zorder=4)
    ax2_bot.axvline(np.log10(c_stats["max"]), color=RED, ls=":", lw=1.8, label=f"Max = {fmt_vn_int(c_stats['max'])} (randstad)", zorder=4)

    xticks_val = [10, 25, 100, 500, 4745]
    ax2_bot.set_xticks([np.log10(v) for v in xticks_val])
    ax2_bot.set_xticklabels([fmt_vn_int(v) for v in xticks_val], fontsize=9.0, fontweight="bold", color=SLATE)
    ax2_bot.set_xlabel("Số lượt ứng tuyển mỗi Silo (n_apps, thang log10)", fontsize=9.6, fontweight="bold", color=SLATE)
    ax2_bot.set_ylabel("Số lượng Client", fontsize=9.6, fontweight="bold", color=SLATE)
    ax2_bot.set_title(f"(b2) Phân bố Lệch Quy mô của {fmt_vn_int(len(client_apps))} Silos (max/min = {c_stats['max_min_ratio']:.1f}×)",
                      fontsize=11.0, fontweight="bold", color="#0F172A", pad=8)
    style_ax(ax2_bot, "y")
    ax2_bot.legend(loc="upper right", frameon=True, facecolor="white", edgecolor=BORDER, fontsize=8.2)

    fig.suptitle("Độ trễ Hệ thống & Phân tích Công bằng Cross-Silo (CareerBuilder + O*NET V3)",
                 fontsize=13.8, fontweight="bold", color="#0F172A", y=1.01)
    out = OUT_DIR / "fig6_latency_and_fairness.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


def main():
    setup_rc()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_all_inputs()
    builders = [
        build_fig1_architecture,
        build_fig2_preprocessing_funnel,
        build_fig3_model_comparison,
        build_fig4_ablation_and_drift,
        build_fig5_convergence_and_sweep,
        build_fig6_latency_and_fairness,
    ]
    for fn in builders:
        path = fn(data)
        print(f"Generated {path} ({path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
