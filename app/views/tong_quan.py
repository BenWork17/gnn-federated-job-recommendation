"""Trang 1 — Tổng quan: đặt vấn đề trong 30 giây."""

from __future__ import annotations

import streamlit as st

from app.components import header, load_json
from app.components.three_hero import render_fl_three_hero
from app.paths import PATHS


def render() -> None:
    header(
        "GNN + Federated Learning cho gợi ý việc làm",
        "Vì sao không thể gom dữ liệu tuyển dụng về một máy chủ, "
        "và đồ thị giúp gì?",
        kicker="DSS · Đồ án cuối kỳ · Phan Gia Bảo 102220265 · Nguyễn Văn Chương 102220267",
    )

    reco = load_json(PATHS["reco"])
    d = reco["data_summary"]
    fed = reco["systems"]["fedavg"]
    loc = reco["systems"]["local_only"]
    cent = reco["systems"]["centralized"]

    gap_pct = (fed["recall@20"] - loc["recall@20"]) / max(
        cent["recall@20"] - loc["recall@20"], 1e-9
    )
    up_kb = reco["communication"]["up_bytes_total"] / 1024
    raw_kb = reco["communication"]["raw_data_bytes_if_centralized"] / 1024

    max_r = max(cent["recall@20"], 1e-6)
    loc_w = min(100.0, loc["recall@20"] / max_r * 100.0)
    fed_w = min(100.0, fed["recall@20"] / max_r * 100.0)
    cent_w = 100.0

    # -----------------------------------------------------------------
    # 1. Top Bento Hero Stage: Three.js 3D FL Topology + Border Beam KPI
    # -----------------------------------------------------------------
    col_3d, col_kpi = st.columns([1.35, 1], gap="medium")

    with col_3d:
        with st.container(key="hx-three-frame"):
            render_fl_three_hero(height=360, n_clients=9116)

    with col_kpi:
        st.markdown(
            f"""
            <div class="hx-bento-hero" style="min-height:360px;display:flex;flex-direction:column;justify-content:space-between;">
              <div>
                <div class="hx-kicker">01 // FEDAVG RECALL@20</div>
                <div class="hx-hero-row">
                  <span class="hx-hero-val">{fed['recall@20']:.3f}</span>
                  <span class="hx-pill-orange">▲ +{gap_pct:.0%} khoảng cách lấy lại</span>
                </div>
              </div>
              <div class="hx-track-list">
                <div class="hx-track-item">
                  <span class="hx-track-lbl">Cục bộ</span>
                  <div class="hx-track-bar-bg">
                    <div class="hx-track-bar-fill" style="width:{loc_w:.1f}%;background:#94A3B8"></div>
                  </div>
                  <span class="hx-track-num">{loc['recall@20']:.3f}</span>
                </div>
                <div class="hx-track-item">
                  <span class="hx-track-lbl" style="color:#C2410C">FedAvg (FL)</span>
                  <div class="hx-track-bar-bg">
                    <div class="hx-track-bar-fill" style="width:{fed_w:.1f}%;background:#FF5A1F"></div>
                  </div>
                  <span class="hx-track-num" style="color:#C2410C">{fed['recall@20']:.3f}</span>
                </div>
                <div class="hx-track-item">
                  <span class="hx-track-lbl" style="color:#0F172A">Tập trung</span>
                  <div class="hx-track-bar-bg">
                    <div class="hx-track-bar-fill" style="width:{cent_w:.1f}%;background:#0F172A"></div>
                  </div>
                  <span class="hx-track-num">{cent['recall@20']:.3f}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # 2. Two Compact Glass Metric Tiles
    # -----------------------------------------------------------------
    col_t1, col_t2 = st.columns([1, 1], gap="medium")

    with col_t1:
        st.markdown(
            """
            <div class="hx-bento-tile" style="margin-bottom:0">
              <div class="hx-kicker">02 // BẢO MẬT TUYỆT ĐỐI</div>
              <div class="hx-tile-val">
                <span class="sb-dot"></span>0 dòng dữ liệu thô
              </div>
              <div class="hx-tile-sub">
                Dữ liệu ứng viên ở lại máy khách; <b>9.116</b> node CareerBuilder chỉ trao đổi tham số mô hình.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_t2:
        st.markdown(
            f"""
            <div class="hx-bento-tile" style="margin-bottom:0">
              <div class="hx-kicker">03 // ĐÁNH ĐỔI BĂNG THÔNG &amp; CỠ MẪU</div>
              <div class="hx-tile-val">{up_kb:,.0f} KB</div>
              <div class="hx-tile-sub">
                Gửi tham số so với {raw_kb:.0f} KB dữ liệu thô · Tập test <b>{d['users_in_test']} ứng viên</b> (đọc theo thứ hạng).
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

    pub = int(d["public_edges"])
    priv = int(d["private_edges"])
    total_e = max(pub + priv, 1)
    pub_pct = pub / total_e * 100.0
    priv_pct = 100.0 - pub_pct

    with col_l:
        st.markdown(
            f"""
            <div class="hx-editorial-card">
              <div class="hx-kicker">VÌ SAO CẦN FEDERATED GRAPH</div>
              <div class="hx-editorial-body">
                Dữ liệu tuyển dụng phân mảnh qua nhiều nền tảng và bị ràng buộc bởi Luật Bảo vệ Dữ liệu Cá nhân / GDPR.
                Hệ thống dựng đồ thị gồm <b>{d['n_jobs']:,}</b> tin, <b>{d['n_users']}</b> ứng viên,
                <b>{d['n_skills']}</b> kỹ năng và <b>{d['n_industries']}</b> ngành để học biểu diễn mà không gom dữ liệu thô.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_r:
        st.markdown(
            f"""
            <div class="hx-editorial-card">
              <div class="hx-kicker">PHÂN TÁCH CÔNG KHAI / RIÊNG TƯ</div>
              <div class="hx-split-pill">
                <div style="width:{pub_pct:.1f}%;background:#FF5A1F"></div>
                <div style="width:{priv_pct:.1f}%;background:#0F172A"></div>
              </div>
              <div class="hx-editorial-body">
                <b style="color:#C2410C">{pub:,} cạnh công khai</b> (tin – kỹ năng – ngành) nằm trên Server ·
                <b style="color:#0F172A">{priv:,} cạnh riêng tư</b> (ứng viên – kỹ năng / tin) giữ tuyệt đối tại Client.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # 4. Khối điều hướng gập lại
    # -----------------------------------------------------------------
    with st.expander("Cách xem bộ demo này"):
        st.markdown(
            """
            1. **Đồ thị việc làm** — thấy dữ liệu nào nằm ở máy chủ, dữ liệu nào ở khách hàng.
            2. **Federated Learning simulation** — chạy từng vòng, xem tham số đi và chất lượng tăng.
            3. **Gợi ý cho ứng viên** — so sánh trực tiếp các phương pháp trên một hồ sơ thật.
            4. **Kết luận & hạn chế** — bảng đạt/không và hướng làm tiếp.
            """
        )
