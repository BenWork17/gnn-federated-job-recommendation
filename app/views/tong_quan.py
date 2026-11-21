"""Trang 1 — Tổng quan: đặt vấn đề trong 30 giây trên bộ dữ liệu CareerBuilder + O*NET (V3)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components import bar_chart, data_note, finding, header, load_json, render_chart
from app.components.three_hero import render_fl_three_hero
from app.paths import PATHS


def render() -> None:
    header(
        "GNN + Federated Learning cho gợi ý việc làm",
        "Vì sao không thể gom dữ liệu tuyển dụng của 9.116 nhà tuyển dụng về một máy chủ, "
        "và đồ thị tri thức CareerBuilder + O*NET (264.995 nút) giải quyết bài toán phân mảnh đó như thế nào?",
        kicker="DSS · Đồ án cuối kỳ · Phan Gia Bảo 102220265 · Nguyễn Văn Chương 102220267 · CareerBuilder + O*NET (V3)",
    )

    meta = load_json(str(PATHS["v3"] / "meta.json"))
    metrics = load_json(PATHS["v3_metrics"])

    nodes_info = meta["nodes"]
    edges_info = meta["edges"]
    by_type = edges_info["by_type"]
    clients_info = meta["clients"]
    models = metrics["models"]

    n_nodes = int(nodes_info["n_nodes"])            # 264,995
    n_users = int(nodes_info["n_users"])            # 171,807
    n_jobs = int(nodes_info["n_jobs"])              # 84,845
    n_occ = int(nodes_info["n_occupations"])        # 583
    n_skills = int(nodes_info["n_skills"])          # 7,760
    n_clients = int(clients_info["n_clients"])      # 9,116

    e_user_job = int(by_type["0_user_job"])         # 436,893
    e_job_occ = int(by_type["1_job_occupation"])    # 26,678
    e_occ_skill = int(by_type["2_occupation_skill"])  # 25,866
    e_user_occ = int(by_type["3_user_occupation"])  # 274,927
    n_edges = int(edges_info["n_edges_stored"])     # 764,364

    pub_edges = e_job_occ + e_occ_skill             # 52,544
    priv_edges = e_user_job + e_user_occ            # 711,820

    # Chỉ số trên Vũ trụ FL (9.058 tin) & Vũ trụ cố định / catalog có nghề O*NET
    r20_lightgcn_fl = float(models["LightGCN"]["R20_FlUniverse"])       # 0.7151
    r20_sage_fl = float(models["GraphSAGE"]["R20_FlUniverse"])          # 0.5113
    r20_knn_fl = float(models["Item-KNN"]["R20_FlUniverse"])            # 0.4897
    r20_fed_fl = float(models["FedAvg"]["R20_FlUniverse"])              # 0.3905
    r20_pop_fl = float(models["Popularity"]["R20_FlUniverse"])          # 0.0542
    r20_fed_fixed = 0.4833  # Ablation base (20 node, 4.511 tin cố định)
    r20_fed_occ = 0.5756    # Ablation f1 (20 node, 956 tin có mã nghề O*NET)

    max_r = max(r20_lightgcn_fl, 1e-6)
    pop_w = min(100.0, r20_pop_fl / max_r * 100.0)
    fed_fl_w = min(100.0, r20_fed_fl / max_r * 100.0)
    fed_occ_w = min(100.0, r20_fed_occ / max_r * 100.0)
    sage_w = min(100.0, r20_sage_fl / max_r * 100.0)
    cent_w = 100.0

    # -----------------------------------------------------------------
    # 1. Top Bento Hero Stage: Three.js 3D FL Topology + Border Beam KPI
    # -----------------------------------------------------------------
    col_3d, col_kpi = st.columns([1.3, 1.05], gap="medium")

    with col_3d:
        with st.container(key="hx-three-frame"):
            render_fl_three_hero(height=375, n_clients=n_clients)

    with col_kpi:
        st.markdown(
            f"""
            <div class="hx-bento-hero" style="min-height:375px;display:flex;flex-direction:column;justify-content:space-between;">
              <div>
                <div class="hx-kicker">01 // HIỆU NĂNG GNN &amp; FEDERATED LEARNING (RECALL@20)</div>
                <div class="hx-hero-row">
                  <span class="hx-hero-val">{r20_lightgcn_fl:.4f}</span>
                  <span class="hx-pill-orange">LightGCN · Vũ trụ FL (9.058 tin)</span>
                </div>
                <div style="font-size:0.8rem;color:#475569;margin-top:0.2rem;line-height:1.4">
                  <b>FedAvg (FL)</b> đạt <b>{r20_fed_fl:.4f}</b> (50 node · 9.058 tin), <b>{r20_fed_fixed:.4f}</b> (vũ trụ cố định 4.511 tin)
                  và <b>{r20_fed_occ:.4f}</b> trên catalog 956 tin có mã nghề O*NET — gấp <b>7,2–10,6×</b> Popularity ({r20_pop_fl:.4f}).
                </div>
              </div>
              <div class="hx-track-list">
                <div class="hx-track-item">
                  <span class="hx-track-lbl">Popularity</span>
                  <div class="hx-track-bar-bg">
                    <div class="hx-track-bar-fill" style="width:{pop_w:.1f}%;background:#94A3B8"></div>
                  </div>
                  <span class="hx-track-num">{r20_pop_fl:.4f}</span>
                </div>
                <div class="hx-track-item">
                  <span class="hx-track-lbl" style="color:#C2410C">FedAvg (50N)</span>
                  <div class="hx-track-bar-bg">
                    <div class="hx-track-bar-fill" style="width:{fed_fl_w:.1f}%;background:#FF5A1F"></div>
                  </div>
                  <span class="hx-track-num" style="color:#C2410C">{r20_fed_fl:.4f}</span>
                </div>
                <div class="hx-track-item">
                  <span class="hx-track-lbl" style="color:#C2410C">FedAvg (O*NET)</span>
                  <div class="hx-track-bar-bg">
                    <div class="hx-track-bar-fill" style="width:{fed_occ_w:.1f}%;background:#EA580C"></div>
                  </div>
                  <span class="hx-track-num" style="color:#C2410C">{r20_fed_occ:.4f}</span>
                </div>
                <div class="hx-track-item">
                  <span class="hx-track-lbl" style="color:#0EA5E9">GraphSAGE</span>
                  <div class="hx-track-bar-bg">
                    <div class="hx-track-bar-fill" style="width:{sage_w:.1f}%;background:#0EA5E9"></div>
                  </div>
                  <span class="hx-track-num" style="color:#0EA5E9">{r20_sage_fl:.4f}</span>
                </div>
                <div class="hx-track-item">
                  <span class="hx-track-lbl" style="color:#0F172A">LightGCN</span>
                  <div class="hx-track-bar-bg">
                    <div class="hx-track-bar-fill" style="width:{cent_w:.1f}%;background:#0F172A"></div>
                  </div>
                  <span class="hx-track-num">{r20_lightgcn_fl:.4f}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # 2. Three Compact Glass Metric Tiles
    # -----------------------------------------------------------------
    col_t1, col_t2, col_t3 = st.columns([1, 1, 1], gap="medium")

    with col_t1:
        st.markdown(
            f"""
            <div class="hx-bento-tile" style="margin-bottom:0">
              <div class="hx-kicker">02 // QUY MÔ ĐỒ THỊ V3 &amp; POSTGRESQL</div>
              <div class="hx-tile-val">
                <span class="sb-dot"></span>{n_nodes:,} nút · {n_edges:,} cạnh
              </div>
              <div class="hx-tile-sub">
                <b>{n_users:,}</b> ứng viên · <b>{n_jobs:,}</b> tin tuyển dụng · <b>{n_occ:,}</b> mã nghề O*NET-SOC · <b>{n_skills:,}</b> kỹ năng công nghệ.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_t2:
        st.markdown(
            f"""
            <div class="hx-bento-tile" style="margin-bottom:0">
              <div class="hx-kicker">03 // LIÊN BANG ĐA SILO (CROSS-SILO FL)</div>
              <div class="hx-tile-val">{n_clients:,} Node FL</div>
              <div class="hx-tile-sub">
                Mỗi nhà tuyển dụng (&ge; 10 đơn) là 1 silo độc lập · <b>{clients_info['pct_users_multi_client']}%</b> ứng viên nộp đơn đa công ty (TB <b>{clients_info['mean_clients_per_user']}</b> client/user) · <b>0</b> dòng dữ liệu thô rời silo.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_t3:
        st.markdown(
            f"""
            <div class="hx-bento-tile" style="margin-bottom:0">
              <div class="hx-kicker">04 // ĐÁNH GIÁ THỰC NGHIỆM &amp; ĐỘ TRỄ</div>
              <div class="hx-tile-val">37.957 cạnh test</div>
              <div class="hx-tile-sub">
                Tập train <b>398.936</b> cạnh user–job · Kiểm định <b>37.077</b> cạnh test sạch (CI 95%) · Độ trễ suy luận <b>p50 = {metrics['latency']['p50_ms']:.0f} ms</b> (p95 = {metrics['latency']['p95_ms']:.0f} ms).
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # 3. Two Styled Glass Narrative Cards
    # -----------------------------------------------------------------
    col_l, col_r = st.columns([1, 1], gap="medium")

    total_e = max(pub_edges + priv_edges, 1)
    pub_pct = pub_edges / total_e * 100.0
    priv_pct = 100.0 - pub_pct

    with col_l:
        st.markdown(
            f"""
            <div class="hx-editorial-card">
              <div class="hx-kicker">VÌ SAO CẦN FEDERATED GRAPH TRÊN CAREERBUILDER + O*NET</div>
              <div class="hx-editorial-body">
                Từ <b>1.092.096</b> tin tuyển dụng và <b>1.603.111</b> lượt ứng tuyển thô của CareerBuilder, hệ thống trích xuất
                <b>{n_clients:,}</b> nhà tuyển dụng hợp lệ và ánh xạ vào chuẩn <b>O*NET-SOC ({n_occ} nghề · {n_skills:,} kỹ năng công nghệ)</b>.
                Vì mỗi nhà tuyển dụng chỉ giữ quan sát ứng tuyển vào tin của chính mình (<b>{e_user_job:,}</b> cạnh user–job),
                mô hình cục bộ bị mù thông tin chéo dù <b>{clients_info['pct_users_multi_client']}%</b> ứng viên ứng tuyển ở nhiều công ty.
                <b>Federated GNN</b> cho phép hợp tác học biểu diễn qua cầu nối công khai <b>Nghề O*NET – Kỹ năng</b> mà không chia sẻ lịch sử ứng tuyển.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_r:
        st.markdown(
            f"""
            <div class="hx-editorial-card">
              <div class="hx-kicker">PHÂN TÁCH CÔNG KHAI (SERVER) / RIÊNG TƯ (CLIENT) &amp; POSTGRESQL</div>
              <div class="hx-split-pill">
                <div style="width:{pub_pct:.1f}%;background:#FF5A1F"></div>
                <div style="width:{priv_pct:.1f}%;background:#0F172A"></div>
              </div>
              <div class="hx-editorial-body">
                <b style="color:#C2410C">{pub_edges:,} cạnh công khai ({pub_pct:.1f}%)</b> nằm trên Server
                (<b>{e_job_occ:,}</b> cạnh tin–nghề + <b>{e_occ_skill:,}</b> cạnh nghề–kỹ năng) ·
                <b style="color:#0F172A">{priv_edges:,} cạnh riêng tư ({priv_pct:.1f}%)</b> giữ tuyệt đối tại Client
                (<b>{e_user_job:,}</b> cạnh ứng tuyển user–job + <b>{e_user_occ:,}</b> cạnh lịch sử nghề user–occupation).
                Khi suy bắc cầu 2 bước qua nghề trong PostgreSQL (<code>dss_jobs</code>), hệ thống phục vụ
                <b>2.593.468</b> liên kết <code>job_skills</code> và <b>18.017.133</b> liên kết <code>user_skills</code>.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # 4. Bảng & Biểu đồ so sánh trực quan 7 hệ thống gợi ý trên 2 hệ quy chiếu
    # -----------------------------------------------------------------
    st.subheader("So sánh thực nghiệm 7 hệ thống gợi ý trên CareerBuilder + O*NET (V3)")

    order_7 = ["Popularity", "BPR-MF", "GAT", "GraphSAGE", "Item-KNN", "LightGCN", "FedAvg"]
    rows_7 = []
    for name in order_7:
        m = models[name]
        ci = m.get("recall@20_ci95", [0.0, 0.0])
        rows_7.append({
            "Hệ thống": name,
            "Nhóm": {
                "baseline": "Baseline phi đồ thị",
                "graph": "GNN tập trung",
                "federated": "Federated GNN",
            }.get(m.get("kind", "baseline" if name == "Item-KNN" else "graph"), "Baseline CF"),
            "Recall@20 (Vũ trụ FL 9.058 tin)": float(m["R20_FlUniverse"]),
            "Recall@20 (Toàn cục 82.876 tin)": float(m["recall@20"]),
            "NDCG@20 (Toàn cục)": float(m["ndcg@20"]),
            "MRR@20 (Toàn cục)": float(m["mrr@20"]),
            "CI 95% (Toàn cục)": f"[{ci[0]:.4f}, {ci[1]:.4f}]" if len(ci) == 2 else "—",
            "Thời gian (s)": round(float(m["seconds"]), 1),
        })
    df_7 = pd.DataFrame(rows_7)

    c_chart1, c_chart2 = st.columns(2, gap="medium")
    with c_chart1:
        df_fl_u = df_7.sort_values("Recall@20 (Vũ trụ FL 9.058 tin)", ascending=False)
        render_chart(
            bar_chart(
                df_fl_u,
                "Recall@20 (Vũ trụ FL 9.058 tin)",
                "Hệ thống",
                color_col="Nhóm",
                horizontal=True,
                title="Recall@20 trên Vũ trụ FL (9.058 tin · Top-50 nhà tuyển dụng)",
                x_title="Recall@20",
                y_title="Hệ thống",
                height=280,
                value_fmt=".4f",
            ),
            delay_ms=50,
        )
    with c_chart2:
        df_full_u = df_7.sort_values("Recall@20 (Toàn cục 82.876 tin)", ascending=False)
        render_chart(
            bar_chart(
                df_full_u,
                "Recall@20 (Toàn cục 82.876 tin)",
                "Hệ thống",
                color_col="Nhóm",
                horizontal=True,
                title="Recall@20 trên Vũ trụ đầy đủ (82.876 tin · 9.116 nhà tuyển dụng)",
                x_title="Recall@20",
                y_title="Hệ thống",
                height=280,
                value_fmt=".4f",
            ),
            delay_ms=110,
        )

    st.dataframe(df_7, hide_index=True, width="stretch")

    finding(
        "Điểm nhấn thực nghiệm trên hai hệ quy chiếu đánh giá",
        "Trên <b>Vũ trụ FL (9.058 tin thuộc 50 nhà tuyển dụng tham gia liên bang)</b>, "
        "<b>LightGCN tập trung</b> đạt <b>Recall@20 = 0,7151</b>, <b>GraphSAGE</b> đạt <b>0,5113</b>, "
        "<b>Item-KNN</b> đạt <b>0,4897</b>, và <b>FedAvg (50 node)</b> đạt <b>0,3905</b> (CI 95% [0,3577; 0,4258]) "
        "— tăng lên <b>0,4833</b> trên vũ trụ cố định 4.511 tin và <b>0,5756</b> trên catalog 956 tin có mã nghề O*NET. "
        "Trên <b>Vũ trụ toàn cục (82.876 tin)</b>, <b>Item-KNN (0,5408)</b> và <b>LightGCN (0,4002)</b> dẫn đầu nhờ "
        "nhìn thấy toàn bộ đồ thị, trong khi FedAvg chỉ huấn luyện trên 50/9.116 silo (~11% lượng tin) nhưng vẫn vượt xa "
        "<b>Popularity (0,0154)</b> và <b>BPR-MF (0,0222)</b> mà không cần gom bất kỳ đơn ứng tuyển thô nào.",
        "good",
    )

    data_note(
        "Nguồn số liệu: artifacts/v3/meta.json & results/v3/notebook_metrics.json · "
        "Đồng bộ 100% với cơ sở dữ liệu PostgreSQL (dss-postgres: 9.116 employers, 171.807 users, 84.845 jobs, 436.893 applications)."
    )

    # -----------------------------------------------------------------
    # 5. Khối điều hướng gập lại (khớp đúng 5 mục mới)
    # -----------------------------------------------------------------
    with st.expander("Cách xem bộ demo này (5 mục đồng nhất dữ liệu CareerBuilder + O*NET V3)"):
        st.markdown(
            """
            1. **Đồ thị việc làm** — trực quan hóa 2D/3D đồ thị 4 thực thể (`264.995` nút, `764.364` cạnh): phân tách rõ `52.544` cạnh công khai trên máy chủ (`job–occupation`, `occupation–skill`) và `711.820` cạnh riêng tư ở máy khách (`user–job`, `user–occupation`).
            2. **Federated Learning simulation** — mô phỏng quá trình hội tụ FedAvg / FedProx qua từng vòng giao tiếp, kiểm chứng 15 biến thể Ablation Study (vai trò cầu nối Nghề O*NET + Kỹ năng) và 8 cấu hình Sweep siêu tham số.
            3. **Giám sát node FL** — bảng điều khiển vận hành kết nối trực tiếp FastAPI + PostgreSQL (`dss_jobs`), giám sát từng silo nhà tuyển dụng thật (`randstad`, `allmedstaffing.com`, `spherion`...) và kiểm thử suy luận gợi ý thời gian thực.
            4. **Kết luận & hạn chế** — tổng hợp bảng nghiệm thu yêu cầu đề bài, phân tích thẳng thắn các hạn chế kỹ thuật và lộ trình mở rộng.
            """
        )
