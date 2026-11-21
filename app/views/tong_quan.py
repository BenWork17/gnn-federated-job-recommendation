"""Trang 1 — Tổng quan: đặt vấn đề trong 30 giây.

BỐ CỤC (đã đo lại, xem báo cáo của task t2):
- Dải số liệu nằm NGAY dưới header, trước mọi đoạn văn -> người xem thấy
  kết quả trước khi phải đọc.
- Phần văn dài và phần số liệu minh hoạ đứng CẠNH NHAU (2 cột), thay vì
  dàn dọc như trước.
- Khung "Cách xem bộ demo" (4 bước điều hướng) gập trong `st.expander`:
  thông tin vẫn còn nguyên, chỉ không chiếm chỗ khi chưa cần.
- Ba ô `finding()` trước đây dàn dọc 3 tầng -> 2 ô đầu sang 2 cột.
"""

from __future__ import annotations

import streamlit as st

from app.components import (BLUE, GREEN, data_note, finding, header, load_json, metric_row)
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

    # -----------------------------------------------------------------
    # 1. Dải số liệu lên đầu: 4 ô chiếm hết chiều rộng, nằm trên mọi
    #    đoạn văn để người xem nắm kết quả trong một cái liếc mắt.
    # -----------------------------------------------------------------
    st.subheader("Bốn con số quan trọng nhất")

    metric_row([
        {"value": f"{fed['recall@20']:.3f}",
         "label": "Recall@20 — mô hình FL",
         "help": f"Cục bộ (không chia sẻ): {loc['recall@20']:.3f} · "
                 f"Tập trung (mốc trên): {cent['recall@20']:.3f}",
         "color": BLUE},
        {"value": f"{cent['recall@20']:.3f}",
         "label": "Recall@20 — mốc tập trung",
         "help": "Mức trần nếu được gom toàn bộ dữ liệu về một máy chủ",
         "color": BLUE},
        {"value": f"{(fed['recall@20'] - loc['recall@20']) / (cent['recall@20'] - loc['recall@20']):.0%}",
         "label": "Phần khoảng cách FL lấy lại",
         "help": "So với việc mỗi khách hàng tự học riêng, không chia sẻ",
         "color": GREEN},
        {"value": "0",
         "label": "Dòng dữ liệu thô rời khỏi khách hàng",
         "help": "Chỉ tham số mô hình được trao đổi",
         "color": GREEN},
    ])

    # -----------------------------------------------------------------
    # 2. Hai cột: bên trái là lập luận "vì sao", bên phải là những con số
    #    minh hoạ cho chính lập luận đó. Trước đây hai phần này dàn dọc
    #    nên mỗi bên chỉ dùng nửa chiều ngang.
    # -----------------------------------------------------------------
    col_vi_sao, col_so_lieu = st.columns([1, 1], gap="medium")

    with col_vi_sao:
        st.subheader("Đặt vấn đề")
        st.markdown(
            """
            Mô hình gợi ý việc làm truyền thống giả định toàn bộ tin tuyển dụng và
            hồ sơ ứng viên nằm trên **một máy chủ duy nhất**. Thực tế dữ liệu tuyển
            dụng thuộc về nhiều nền tảng và doanh nghiệp khác nhau — gom hồ sơ cá
            nhân về một chỗ bị chặn bởi Luật Bảo vệ Dữ liệu Cá nhân và GDPR.

            **Cách giải**: dựng *đồ thị* để tận dụng quan hệ giữa người dùng, tin
            tuyển dụng, kỹ năng và ngành nghề; dùng *Federated Learning* để mô hình học
            mà dữ liệu gốc không rời khỏi nơi lưu trữ.
            """
        )

    with col_so_lieu:
        st.subheader("Dữ liệu và đồ thị")
        st.markdown(
            f"""
            **Dữ liệu**: {d['n_jobs']:,} tin tuyển dụng, {d['n_users']} ứng viên,
            {d['n_train'] + d['n_test']} tương tác thật.

            **Đồ thị**: {d['n_users']} nút người dùng + {d['n_jobs']:,} nút tin
            + {d['n_skills']} nút kỹ năng + {d['n_industries']} nút ngành.
            """
        )
        st.subheader("Ai giữ cái gì")
        st.markdown(
            f"""
            **Máy chủ trung tâm** giữ {d['public_edges']:,} cạnh công khai
            (tin–kỹ năng, tin–ngành) — dữ liệu không nhạy cảm.

            **Khách hàng** giữ {d['private_edges']:,} cạnh riêng tư
            (người dùng–kỹ năng, người dùng–tin). Máy chủ không bao giờ thấy
            phần này.
            """
        )

    # -----------------------------------------------------------------
    # 3. Ba phát hiện: hai ô đầu đứng cạnh nhau (2 cột), ô cảnh báo về cỡ
    #    tập kiểm thử giữ nguyên độ rộng để chữ không bị bó.
    # -----------------------------------------------------------------
    st.divider()
    st.subheader("Đọc kết quả cho đúng: cái gì đạt, cái gì chưa")

    col_f1, col_f2 = st.columns([1, 1], gap="medium")

    with col_f1:
        finding(
            "Federated Learning hoạt động: "
            f"{loc['recall@20']:.3f} → {fed['recall@20']:.3f} Recall@20",
            f"Khi mỗi khách hàng tự huấn luyện trên dữ liệu riêng (không chia sẻ), "
            f"Recall@20 chỉ đạt {loc['recall@20']:.3f}. Với FedAvg, con số này lên "
            f"{fed['recall@20']:.3f} — gần bằng mô hình tập trung "
            f"({cent['recall@20']:.3f}) mà dữ liệu gốc không hề rời khỏi khách hàng.",
            "good",
        )

    with col_f2:
        finding(
            "FL không tiết kiệm băng thông ở quy mô này",
            f"Gửi tham số tốn {reco['communication']['up_bytes_total'] / 1024:,.0f} KB, "
            f"trong khi gửi thẳng dữ liệu thô chỉ "
            f"{reco['communication']['raw_data_bytes_if_centralized'] / 1024:.0f} KB. "
            "Lợi ích thật của FL ở đây là **dữ liệu không rời chỗ**, không phải băng thông.",
            "info",
        )

    finding(
        f"Tập kiểm thử chỉ có {d['users_in_test']} ứng viên",
        "Khoảng tin cậy 95% vì thế khá rộng — nhiều khác biệt vài phần trăm "
        "giữa các phương pháp **chưa** có ý nghĩa thống kê. Con số đáng tin là "
        "thứ hạng tương đối, không phải chênh lệch nhỏ.",
        "warn",
    )

    # -----------------------------------------------------------------
    # 4. Khối điều hướng dài: gập lại, chỉ mở khi người xem cần.
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

    data_note(
        f"Số liệu lấy từ results/*.json do pipeline sinh ra. "
        f"Tập kiểm thử gợi ý chỉ có {d['users_in_test']} ứng viên — "
        "khoảng tin cậy vì thế khá rộng, được hiển thị ở trang Gợi ý."
    )
