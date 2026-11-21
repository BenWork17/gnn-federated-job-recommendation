"""Trang 3 — Mô phỏng Federated Learning: từng vòng, từng khách hàng."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components import (BLUE, GREEN, GREY, ORANGE, RED, bar_chart, finding, header, line_chart, load_json, metric_row, render_chart)
from app.components import theme
from app.paths import PATHS


def render() -> None:
    header(
        "Mô phỏng Federated Learning",
        "Dữ liệu không rời khách hàng thì mô hình học được gì, và mỗi vòng "
        "tốn bao nhiêu?",
        kicker="FedAvg / FedProx trên MEDAJob",
    )

    reco = load_json(PATHS["reco"])
    sweep = reco["client_sweep"]
    comm = reco["communication"]

    st.markdown(
        """
        Mỗi **khách hàng** là một nền tảng tuyển dụng giữ dữ liệu riêng. Mỗi
        **vòng** gồm: máy chủ gửi tham số xuống → từng khách hàng tự huấn luyện
        trên đồ thị con của mình → gửi tham số đã cập nhật lên → máy chủ lấy
        trung bình. Trong suốt quá trình, **không dòng dữ liệu nào được gửi đi**.
        """
    )

    st.divider()

    # ------------------------------------------------------------------
    # MỘT hàng điều khiển duy nhất (5 ô, nhãn ngắn).
    #
    # BỐ CỤC CŨ: hàng 1 = [chọn số khách hàng | chọn chỉ số | 4 thẻ số liệu],
    # hàng 2 = [tự chạy | tốc độ | slider vòng]. Mỗi ô chỉ rộng 1/4 khung nên
    # nhãn bị xuống dòng, và thanh điều khiển chiếm HAI hàng dọc.
    # BỐ CỤC MỚI: gom cả 5 ô điều khiển lên cùng một hàng ngay dưới phần mở
    # đầu; dải số liệu tách ra thành một khối ngang riêng bên dưới. Dưới
    # ~1024px Streamlit tự cho các cột xuống dòng, nên không tràn ngang.
    # ------------------------------------------------------------------
    c1, c2, c3, c4, c5 = st.columns([1.05, 1.0, 0.85, 0.85, 2.25], gap="small")
    with c1:
        c_index = st.selectbox(
            "Số khách hàng", options=list(range(len(sweep))),
            format_func=lambda i: f"{sweep[i]['n_clients']} khách hàng")
    with c2:
        metric = st.selectbox("Chỉ số", ["recall@20", "ndcg@20", "mrr@20"],
                              format_func=lambda m: {
                                  "recall@20": "Recall@20",
                                  "ndcg@20": "NDCG@20",
                                  "mrr@20": "MRR@20"}[m])
    s = sweep[c_index]
    curve = pd.DataFrame(s["curve"])
    max_round = int(curve["round"].max())
    best_i = int(curve[metric].idxmax())

    jobs_pc = s["client_sizes"]["jobs_per_client"]
    users_pc = s["client_sizes"]["users_per_client"]
    clients = pd.DataFrame({
        "khách hàng": [f"KH {i + 1}" for i in range(len(jobs_pc))],
        "số tin": jobs_pc,
        "số ứng viên": users_pc,
    })
    clients["dữ liệu (KB)"] = (clients["số tin"] * 0.8).round(1)

    with c3:
        autoplay = st.toggle("▶ Tự chạy", value=False,
                             help="Tự phát lại từng vòng như video — tiện khi "
                                  "trình chiếu, không phải kéo tay.")
    with c4:
        speed = st.select_slider("Tốc độ", options=["Chậm", "Vừa", "Nhanh"],
                                 value="Vừa", disabled=not autoplay)
    with c5:
        upto = st.slider("Xem đến vòng", 1, max_round, max_round,
                         disabled=autoplay,
                         help="Kéo để xem chất lượng tăng dần theo từng vòng.")

    # MỘT dải số liệu ngang cho cả trang — thay cho 4 thẻ nhét trong một cột
    # hẹp (cột đó chỉ rộng 1/2 khung nên mỗi thẻ bị bó khoảng 200px).
    metric_row([
        {"value": f"{curve.loc[best_i, metric]:.3f}",
         "label": f"{metric} — đỉnh (vòng {int(curve.loc[best_i, 'round'])})",
         "color": BLUE},
        {"value": f"{s['fedavg_final'][metric]:.3f}",
         "label": f"{metric} — vòng cuối",
         "color": GREY},
        {"value": f"{s['local_only'][metric]:.3f}",
         "label": "Cục bộ (không chia sẻ)", "color": RED},
        {"value": f"{reco['systems']['centralized'][metric]:.3f}",
         "label": "Tập trung (mốc trên)", "color": GREEN},
    ])

    st.divider()
    st.subheader("Chạy từng vòng để thấy mô hình hội tụ")

    # Khối này được vẽ lại liên tục khi tự chạy, nhưng KHÔNG rerun cả trang.
    def _draw_curves(up_to: int) -> None:
        view = curve[curve["round"] <= up_to].copy()
        long = pd.DataFrame({
            "vòng": list(view["round"]) * 3,
            "giá trị": list(view[metric]) + list(view["train_loss"]) +
                       [reco["systems"]["centralized"][metric]] * len(view),
            "chuỗi": ([f"FedAvg ({s['n_clients']} KH)"] * len(view)
                      + ["Loss huấn luyện"] * len(view)
                      + ["Mốc tập trung"] * len(view)),
        })

        # (1) Biểu đồ CHÍNH — đường cong hội tụ — chiếm toàn bộ bề ngang.
        #     Trước đây nó chỉ được 2/3 khung, 1/3 còn lại là loss; nay loss
        #     xuống hàng phụ nên đường cong đọc được ở cỡ lớn.
        metric_long = long[long.chuỗi != "Loss huấn luyện"]
        render_chart(line_chart(metric_long, "vòng", "giá trị", "chuỗi",
                                title=f"{metric} theo vòng", height=300))

        # (2) Hai biểu đồ PHỤ chia đôi hàng — dùng `theme.grid` (container có
        #     khoá) vì mỗi st.markdown là một khối DOM riêng, không bọc được
        #     widget. CSS auto-fit tự hạ về 1 cột khi màn hẹp.
        loss_long = long[long.chuỗi == "Loss huấn luyện"]
        with theme.grid(2, "chart-phu"):
            with st.container():
                render_chart(line_chart(loss_long, "vòng", "giá trị", "chuỗi",
                                        title="Loss BPR trung bình (thấp tốt)",
                                        height=300), delay_ms=80)
            with st.container():
                render_chart(bar_chart(clients, "khách hàng", "số tin",
                                       title="Số tin mỗi khách hàng",
                                       y_title="số tin", x_title="khách hàng",
                                       height=300, value_fmt=",.0f"),
                             delay_ms=120)

    tick = (1.2 if speed == "Chậm" else 0.7 if speed == "Vừa" else 0.35) \
        if autoplay else None

    @st.fragment(run_every=tick)
    def _animated_curves() -> None:
        if not autoplay:
            _draw_curves(upto)
            return
        # tiến 1 vòng mỗi lần fragment tự chạy; quay lại đầu khi hết
        key = f"fl_round_{c_index}_{metric}"
        cur = st.session_state.get(key, 1) + 1
        if cur > max_round:
            cur = 1
        st.session_state[key] = cur
        _draw_curves(cur)

    _animated_curves()

    st.divider()
    st.subheader("Khách hàng nào đang tham gia?")

    # Bảng chi tiết gập lại: nội dung vẫn còn nguyên, nhưng không chiếm một
    # khối cao giữa trang khi người xem chỉ cần nhìn biểu đồ.
    with st.expander("Bảng dữ liệu chi tiết mỗi khách hàng", expanded=False):
        st.dataframe(clients, use_container_width=True, hide_index=True)

    st.markdown(
        f"""
        **Vòng {upto}** đang hiển thị. Mỗi vòng, cả **{s['n_clients']} khách hàng**
        đều tham gia. Dữ liệu mỗi khách hàng giữ lại tại chỗ; máy chủ chỉ nhận
        trung bình các hàng embedding đã thay đổi.
        """
    )

    st.divider()
    st.subheader("Chi phí truyền thông — con số ít ai nói")

    # Dải số liệu ngang, KHÔNG còn chia [1, 1] với khối chữ: khối chữ dài
    # nằm dưới toàn bộ bề ngang nên không bị ép trong nửa khung.
    metric_row([
        {"value": f"{comm['up_bytes_total'] / 1024:,.0f} KB",
         "label": "Tổng dữ liệu gửi lên server",
         "help": f"{comm['n_rounds']} vòng × {comm['n_clients']} khách hàng",
         "color": ORANGE},
        {"value": f"{comm['raw_data_bytes_if_centralized'] / 1024:.0f} KB",
         "label": "Nếu gửi thẳng dữ liệu thô",
         "color": RED},
    ])

    st.markdown(
        f"""
        Ở quy mô này, Federated Learning tốn **gấp
        {comm['ratio_up_vs_raw']:,.0f} lần** băng thông so với việc gửi
        dữ liệu thô đi một lần. Nguyên nhân: payload là
        `{comm['n_params']:,} tham số` gửi đi **mỗi vòng**, không phụ thuộc
        số tương tác; còn dữ liệu thô thì tỉ lệ với số tương tác
        ({comm['raw_bytes_per_interaction']} byte mỗi tương tác).
        """
    )

    with st.expander("Lợi ích thực tế của Federated Learning", expanded=False):
        st.markdown(
            f"Giá trị cốt lõi là **dữ liệu gốc không rời khách hàng**. "
            f"FL chỉ rẻ hơn về băng thông khi vượt khoảng "
            f"{comm['crossover_interactions']:,} tương tác (hình F09)."
        )

    st.divider()
    st.subheader("FedAvg so với FedProx")
    prox = reco["systems"]["fedprox"]
    fed = reco["systems"]["fedavg"]
    df = pd.DataFrame([
        {"phương pháp": "Cục bộ", "Recall@20": reco["systems"]["local_only"]["recall@20"],
         "NDCG@20": reco["systems"]["local_only"]["ndcg@20"]},
        {"phương pháp": "FedAvg", "Recall@20": fed["recall@20"],
         "NDCG@20": fed["ndcg@20"]},
        {"phương pháp": "FedProx (μ=0,01)", "Recall@20": prox["recall@20"],
         "NDCG@20": prox["ndcg@20"]},
        {"phương pháp": "Tập trung", "Recall@20": reco["systems"]["centralized"]["recall@20"],
         "NDCG@20": reco["systems"]["centralized"]["ndcg@20"]},
    ])
    st.dataframe(df.style.format({"Recall@20": "{:.4f}", "NDCG@20": "{:.4f}"}),
                 use_container_width=True, hide_index=True)
    st.caption("FedProx giảm «trôi» khi dữ liệu khác nhau và ổn định hơn NDCG@20.")

    st.divider()
    from app.views import giam_sat_node
    st.page_link(
        st.Page(giam_sat_node.render, title="Giám sát node FL", icon="🖥️",
                url_path="giam-sat-node"),
        label="Xem giám sát Node trực tiếp (CareerBuilder · 9.116 node) →",
        icon="🖥️",
    )
