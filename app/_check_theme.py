"""
Kiểm tra trực quan: render biểu đồ Altair ra PNG để so sánh trước/sau theme.

VÌ SAO CẦN SCRIPT NÀY: trong môi trường này không chụp được screenshot app
(sandbox chặn Playwright), và không cài được vl-convert/kaleido. Nhưng ta có
thể chuyển spec Altair -> HTML + dùng thư viện vẽ sẵn của Python để DỰNG LẠI
hình dạng biểu đồ với đúng bảng màu/kích thước, nhờ đó kiểm tra được:
  - bảng màu có khớp báo cáo không
  - nhãn số có hiển thị không
  - lưới/trục có bị đậm quá không

Script này KHÔNG thay thế việc xem app thật — nó chỉ kiểm tra phần "da"
(theme) có đúng cấu hình. Ghi rõ điều đó trong output.

Chạy: python app/_check_theme.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / ".mplcache"))
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from app.components import BLUE, GREEN, ORANGE, PALETTE, RED, GREY

OUT = ROOT / "artifacts" / "theme_check.png"


def draw_simulated() -> Path:
    """Dựng lại bố cục giống các biểu đồ chính, dùng đúng bảng màu app."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    fig.patch.set_facecolor("#ffffff")

    # --- 1. Cột dọc có nhãn số (giống bar_chart) ---
    ax = axes[0]
    labels = ["Phổ biến", "Nội dung", "Item-KNN", "Cục bộ", "Liên bang",
              "Tập trung"]
    vals = [0.2448, 0.1094, 0.3490, 0.4021, 0.4969, 0.5042]
    colors = [GREY, GREY, "#bdc3c7", "#95a5a6", BLUE, BLUE]
    bars = ax.bar(range(len(vals)), vals, color=colors, width=0.68)
    for i, (b, v) in enumerate(zip(bars, vals)):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.3f}",
                ha="center", fontsize=9.5, color="#3d4757")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([l.replace(" ", "\n", 1) for l in labels], fontsize=8.5)
    ax.set_ylabel("Recall@20", fontsize=10, color="#1f2733", fontweight="bold")
    ax.set_title("So sánh hệ gợi ý", fontsize=12, fontweight="bold",
                 color="#1f2733", loc="left", pad=12)
    ax.set_ylim(0, 0.60)
    _style(ax)

    # --- 2. Cột ngang có nhãn số ---
    ax = axes[1]
    names = ["Khác", "Software Eng.", "Product", "AI/ML", "Data", "QA"]
    counts = [484, 176, 76, 67, 60, 59]
    bars = ax.barh(range(len(names)), counts, color=BLUE, height=0.66)
    for b, v in zip(bars, counts):
        ax.text(v + 8, b.get_y() + b.get_height() / 2, f"{v:,}",
                va="center", fontsize=9.5, color="#3d4757")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Số tin", fontsize=10, color="#1f2733", fontweight="bold")
    ax.set_title("Phân bố ngành", fontsize=12, fontweight="bold",
                 color="#1f2733", loc="left", pad=12)
    ax.set_xlim(0, 560)
    _style(ax)

    # --- 3. Đường nhiều chuỗi (giống line_chart) ---
    ax = axes[2]
    rounds = list(range(1, 21))
    import math
    a = [0.35 + 0.15 * (1 - math.exp(-r / 5)) for r in rounds]
    b = [0.30 + 0.19 * (1 - math.exp(-r / 7)) for r in rounds]
    c = [0.38 + 0.11 * (1 - math.exp(-r / 4)) for r in rounds]
    for series, color, label in [(a, BLUE, "5 khách hàng"),
                                 (b, ORANGE, "8 khách hàng"),
                                 (c, GREEN, "12 khách hàng")]:
        ax.plot(rounds, series, color=color, linewidth=2.4, marker="o",
                markersize=4.5, label=label)
    ax.axhline(0.5042, color=RED, linestyle="--", linewidth=1.3,
               label="Tập trung")
    ax.set_xlabel("Vòng", fontsize=10, color="#1f2733", fontweight="bold")
    ax.set_ylabel("Recall@20", fontsize=10, color="#1f2733", fontweight="bold")
    ax.set_title("Federated Learning hội tụ", fontsize=12, fontweight="bold",
                 color="#1f2733", loc="left", pad=12)
    ax.set_ylim(0.25, 0.56)
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    _style(ax)

    fig.suptitle("KIỂM TRA THEME SÁNG — mô phỏng bằng matplotlib, "
                 "không phải ảnh chụp app",
                 fontsize=9, color="#7f8c8d", y=0.005)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT, dpi=170, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    return OUT


def _style(ax) -> None:
    """Áp đúng phong cách theme: nền trắng, lưới mảnh, viền nhạt."""
    ax.set_facecolor("#ffffff")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d7dee8")
        ax.spines[side].set_linewidth(1.0)
    ax.grid(axis="y", color="#eef2f7", linewidth=1.0)
    ax.set_axisbelow(True)
    ax.tick_params(colors="#3d4757", labelsize=9)


def main() -> int:
    # 1. Kiểm tra theme config đã nạp
    import streamlit.config as sc
    sc.get_config_options()
    base = sc.get_option("theme.base")
    primary = sc.get_option("theme.primaryColor")
    bg = sc.get_option("theme.backgroundColor")
    print("Theme config.toml:")
    print(f"  base            = {base}")
    print(f"  primaryColor    = {primary}")
    print(f"  backgroundColor = {bg}")
    assert base == "light", "theme.base phải là light"
    assert bg == "#ffffff", "nền phải trắng"

    # 2. Kiểm tra bảng màu khớp giữa app và báo cáo
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "figs", ROOT / "src" / "report" / "figures.py")
    figs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(figs)
    pairs = [("BLUE", BLUE, figs.C_BLUE), ("RED", RED, figs.C_RED),
             ("GREEN", GREEN, figs.C_GREEN), ("ORANGE", ORANGE, figs.C_ORANGE)]
    print("\nBảng màu app vs báo cáo:")
    ok = True
    for name, app_c, fig_c in pairs:
        same = app_c.lower() == fig_c.lower()
        ok &= same
        print(f"  {name:8} app={app_c}  figures={fig_c}  "
              f"{'KHỚP' if same else 'LỆCH'}")
    assert ok, "bảng màu app và báo cáo phải khớp"

    # 3. Dựng ảnh mô phỏng
    out = draw_simulated()
    print(f"\nẢnh mô phỏng theme: {out} ({out.stat().st_size:,} B)")
    print("\nLƯU Ý: ảnh này chỉ kiểm tra bảng màu/bố cục, KHÔNG phải ảnh chụp "
          "app thật (sandbox không chụp được screenshot).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
