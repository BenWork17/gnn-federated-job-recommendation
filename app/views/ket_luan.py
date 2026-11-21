"""Trang 5 — Kết luận và hạn chế trên CareerBuilder + O*NET (V3)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.components import finding, header, load_json, theme
from app.paths import PATHS, ROOT


def _fmt_int(n: int | float) -> str:
    return f"{int(n):,}".replace(",", ".")


def _fmt_dec(x: float, nd: int = 4) -> str:
    return f"{float(x):.{nd}f}".replace(".", ",")


def _v3_paths() -> tuple[str, str]:
    v3_dir = Path(PATHS.get("v3", ROOT / "artifacts" / "v3"))
    metrics_path = str(
        PATHS.get("v3_metrics", ROOT / "results" / "v3" / "notebook_metrics.json")
    )
    meta_path = str(v3_dir / "meta.json")
    return metrics_path, meta_path


def render() -> None:
    header(
        "Kết luận và hạn chế",
        "Đề bài đặt ra những yêu cầu nào trên CareerBuilder + O*NET (V3), cái nào đã đạt, cái nào chưa và vì sao?",
        kicker="Tổng hợp kết quả · CareerBuilder + O*NET (V3) · 9.116 Node FL",
    )

    metrics_path, meta_path = _v3_paths()
    metrics = load_json(metrics_path)
    meta = load_json(meta_path)

    g = metrics["graph"]
    sp = metrics["split"]
    cs = metrics["cross_silo"]
    eda = metrics["eda"]
    models = metrics["models"]
    ab_map = {r["biến_thể"]: r for r in metrics["ablation"]}
    lat = metrics["latency"]

    pop = models["Popularity"]
    lgcn = models["LightGCN"]
    knn = models["Item-KNN"]
    sage = models["GraphSAGE"]
    fed = models["FedAvg"]
    ab_base = ab_map["(base) đầy đủ"]
    ab_no_occ = ab_map["(b) bỏ lớp occupation"]
    ab_occ_cat = ab_map["(f1) base: nghề + kỹ năng"]

    # -----------------------------------------------------------------
    # 1. Bảng đối chiếu yêu cầu — FULL-WIDTH với cột «kết luận» tô màu
    # -----------------------------------------------------------------
    st.subheader("1. Yêu cầu của đề bài và kết quả thực đo")
    st.markdown(
        "Bảng dưới đây đối chiếu **từng yêu cầu** trong đề bài với số đo thực nghiệm trên bộ dữ liệu "
        "**CareerBuilder + O*NET (V3)**. Cột «cách đo» cho biết giao thức tính toán cụ thể — "
        "không có con số nào được tuyên bố mà không kèm hệ quy chiếu và cách đo."
    )

    rows = [
        {
            "yêu cầu": "Giảm tỉ lệ lỗi gợi ý & Nâng Recall@20",
            "cách đo": "Recall@20 so với baseline Popularity (Vũ trụ toàn cục 82.876 tin & Vũ trụ FL 9.058 / 4.511 tin)",
            "thực đo": (
                f"Popularity {_fmt_dec(pop['recall@20'])} ({_fmt_dec(pop['R20_FlUniverse'])} vũ trụ FL) → "
                f"LightGCN {_fmt_dec(lgcn['recall@20'])} ({_fmt_dec(lgcn['R20_FlUniverse'])} vũ trụ FL) & "
                f"FedAvg {_fmt_dec(fed['R20_FlUniverse'])} (50 node) / {_fmt_dec(ab_base['R20'])} (20 node) / "
                f"{_fmt_dec(ab_occ_cat['R20'])} (catalog có nghề)"
            ),
            "kết luận": "Đạt",
        },
        {
            "yêu cầu": "Nâng NDCG@20 & MRR@20",
            "cách đo": "Trung bình trên 800 ứng viên kiểm thử (Bootstrap CI 95%, K = 20)",
            "thực đo": (
                f"NDCG@20: {_fmt_dec(pop['ndcg@20'])} → {_fmt_dec(fed['NDCG20_FlUniverse'])} (vũ trụ FL) / "
                f"{_fmt_dec(ab_base['NDCG20'])} (20 node) · "
                f"MRR@20: {_fmt_dec(pop['mrr@20'])} → {_fmt_dec(fed['MRR20_FlUniverse'])} / {_fmt_dec(ab_base['MRR20'])}"
            ),
            "kết luận": "Đạt",
        },
        {
            "yêu cầu": "Mở rộng quy mô thực tế & Cross-Silo FL",
            "cách đo": "Đồ thị 4 thực thể CareerBuilder + O*NET; gán cạnh (u,j) theo client_of_job[j]; kiểm tra payload",
            "thực đo": (
                f"{_fmt_int(g['n_nodes'])} nút · {_fmt_int(g['n_edges'])} cạnh · {_fmt_int(cs['n_clients'])} nhà tuyển dụng (node FL) · "
                "0 dòng dữ liệu ứng tuyển thô rời máy khách"
            ),
            "kết luận": "Đạt",
        },
        {
            "yêu cầu": "Kiểm chứng Ablation (15 biến thể) & Sweep tham số (8 cấu hình)",
            "cách đo": "Cắt bỏ từng lớp nút (Skill, Occupation), đổi quy mô Node (5/10/20), thuật toán & local_epochs",
            "thực đo": (
                f"Cầu nối Occupation + Skill tăng +{_fmt_dec((ab_base['R20'] - ab_no_occ['R20']) * 100, 1)}% Recall@20 "
                f"({_fmt_dec(ab_no_occ['R20'])} → {_fmt_dec(ab_base['R20'])}); 5 → 20 node tăng gấp đôi (0,2398 → 0,4833)"
            ),
            "kết luận": "Đạt",
        },
        {
            "yêu cầu": "Hệ thống WebAPI + PostgreSQL + Giám sát độ trễ Node thời gian thực",
            "cách đo": "Kiểm tra schema PostgreSQL (dss_jobs), REST/WebSocket API và đo 300 mẫu perf_counter",
            "thực đo": (
                f"9 bảng PostgreSQL (21+ triệu bản ghi cạnh & kỹ năng) · 11 endpoint REST/WS · "
                f"độ trễ huấn luyện p50 = {_fmt_dec(lat['p50_ms'], 1)} ms, p95 = {_fmt_dec(lat['p95_ms'], 1)} ms"
            ),
            "kết luận": "Đạt",
        },
        {
            "yêu cầu": "Tăng mức độ hài lòng người dùng trực tuyến",
            "cách đo": "Cần A/B test trên người dùng thật",
            "thực đo": (
                f"Đồ án đánh giá offline trên {_fmt_int(g['n_test_uj'])} lượt ứng tuyển test "
                f"({_fmt_int(sp['n_test_clean'])} test sạch sau khi lọc rò rỉ)"
            ),
            "kết luận": "Chưa",
        },
    ]

    rows_dat = [r for r in rows if r["kết luận"] == "Đạt"]
    rows_chua = [r for r in rows if r["kết luận"] != "Đạt"]

    st.info(
        f"Đếm từ bảng bên dưới: **{len(rows_dat)}/{len(rows)} yêu cầu đạt** · "
        f"{len(rows_chua)} yêu cầu chưa đạt."
    )

    tbl = pd.DataFrame(rows)

    def _to_mau(row: pd.Series) -> list[str]:
        mau = (
            "color:#1e8449;font-weight:700"
            if row["kết luận"] == "Đạt"
            else "color:#a93226;font-weight:700"
        )
        return ["" if col != "kết luận" else mau for col in row.index]

    st.dataframe(
        tbl.style.apply(_to_mau, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    # -----------------------------------------------------------------
    # 2. Ba ô "đã làm được"
    # -----------------------------------------------------------------
    st.subheader("2. Điều đã làm được")

    with theme.grid(2, "da-lam-duoc"):
        with st.container():
            finding(
                "Triển khai Cross-Silo Federated Learning trên 9.116 nhà tuyển dụng thật",
                f"Giải quyết bài toán thị trường thực tế nơi <b>{_fmt_dec(cs['pct_users_multi_client'], 2)}% ứng viên</b> "
                f"(76.584 người) nộp đơn ở nhiều công ty và chỉ <b>{_fmt_dec(cs['pct_same_client_test'], 2)}% cạnh test</b> "
                f"nằm cùng client với cạnh train chính. Trên vũ trụ FL, <b>FedAvg đạt Recall@20 = 0,3905</b> "
                f"(50 node · 9.058 tin), <b>0,4833</b> (20 node · 4.511 tin cố định) và <b>0,5756</b> "
                f"(catalog 956 tin có nghề O*NET), vượt xa baseline Popularity (<b>0,0542</b>).",
                "good",
            )
        with st.container():
            finding(
                "Chứng minh thực nghiệm giá trị cầu nối của Nghề O*NET & Kỹ năng",
                f"Nghiên cứu cắt bỏ 15 biến thể khẳng định: khung xương công khai gồm <b>{_fmt_int(g['n_occ'])} nghề O*NET</b> "
                f"và <b>{_fmt_int(g['n_skill'])} kỹ năng công nghệ</b> giúp nâng Recall@20 từ <b>0,3933</b> "
                f"(khi bỏ Occupation + Skill) lên <b>0,4589</b> (chỉ giữ Occupation) và đạt <b>0,4833</b> "
                f"(đầy đủ Occupation + Skill, tức <b>+9,0 điểm phần trăm</b>); trên tập trung, "
                f"<b>LightGCN đạt 0,7151</b> (vũ trụ FL) / <b>0,4002</b> (vũ trụ toàn cục) và "
                f"<b>GraphSAGE đạt 0,5113</b> / <b>0,1376</b>.",
                "good",
            )

    finding(
        "Hệ thống Full-Stack PostgreSQL (21+ triệu bản ghi) + FastAPI + Giám sát Node thời gian thực",
        "Đồ thị V3 (<b>264.995 nút</b>, <b>764.364 cạnh gốc</b>) cùng <b>2.593.468</b> cạnh <code>job_skills</code> "
        "và <b>18.017.133</b> cạnh <code>user_skills</code> được nạp trực tiếp vào <b>9 bảng PostgreSQL</b>, "
        "phục vụ qua <b>11 endpoint REST/WebSocket</b> với độ trễ vòng huấn luyện thực đo "
        "<b>p50 = 418,0 ms</b>, <b>p95 = 566,6 ms</b> (300 mẫu) và kiểm chứng tự động <b>0 dòng dữ liệu ứng tuyển thô</b> rời khỏi silo.",
        "good",
    )

    # -----------------------------------------------------------------
    # 3. Năm ô "chưa làm được": 2 + 2 cột, ô cuối full-width
    # -----------------------------------------------------------------
    st.subheader("3. Điều CHƯA làm được — nói thẳng")

    with theme.grid(2, "chua-lam-duoc-1"):
        with st.container():
            finding(
                f"Độ phủ mã nghề O*NET trên tin tuyển dụng hiện đạt {_fmt_dec(eda['pct_jobs_with_occ'], 2)}%",
                f"Trong <b>{_fmt_int(g['n_jobs'])} tin tuyển dụng</b> của 9.116 nhà tuyển dụng, có "
                f"<b>{_fmt_int(eda['n_jobs_with_occ'])} tin ({_fmt_dec(eda['pct_jobs_with_occ'], 2)}%)</b> ánh xạ được sang "
                f"mã nghề O*NET-SOC; <b>{_fmt_int(meta['edges']['n_jobs_without_occupation_edge'])} tin còn lại</b> vẫn giữ "
                "cạnh user–job nhưng thiếu cầu nối job–occupation–skill nên kỹ năng chưa lan truyền tới.",
                "warn",
            )
        with st.container():
            finding(
                "Khoảng cách giữa FedAvg và LightGCN tập trung trên toàn bộ 82.876 tin",
                "Do dữ liệu phân mảnh cực mạnh qua <b>9.116 silo</b> (trung vị chỉ <b>23 đơn/client</b>, "
                "<b>22,38% client không có cạnh test</b>) và mỗi đợt chỉ lấy mẫu 20–50 node, "
                "FedAvg đạt <b>0,3905–0,5756</b> trong vũ trụ FL nhưng mới đạt <b>0,0475</b> khi chấm trên "
                "toàn bộ <b>82.876 tin</b> toàn cục (so với LightGCN tập trung <b>0,4002</b> và Item-KNN <b>0,5408</b>).",
                "warn",
            )

    with theme.grid(2, "chua-lam-duoc-2"):
        with st.container():
            finding(
                "Chưa đo được mức độ hài lòng người dùng trực tuyến",
                "Đồ án đánh giá offline trên <b>37.957 lượt ứng tuyển test</b> (<b>37.077 lượt test sạch</b> "
                "sau khi loại 880 cạnh rò rỉ và tách 1.969 tin cold-start); cần A/B test trực tuyến "
                "trên ứng viên và nhà tuyển dụng thật.",
                "bad",
            )
        with st.container():
            finding(
                "Chưa áp dụng DP-SGD / Secure Aggregation",
                "Máy chủ điều phối chỉ nhận vector cập nhật embedding từ các node nhà tuyển dụng (không nhận "
                "dữ liệu thô), nhưng tham số vẫn ở dạng rõ; cần bổ sung mật mã tổng hợp an toàn hoặc nhiễu vi phân.",
                "bad",
            )

    finding(
        "Hao hụt khi trích xuất tên nhà tuyển dụng từ văn bản tin tuyển dụng gốc",
        f"Từ <b>{_fmt_int(meta['raw']['apps_rows'])} đơn ứng tuyển gốc</b> của CareerBuilder, quy trình lọc 5 bước "
        f"(trích tên công ty bằng regex/domain, yêu cầu nhà tuyển dụng ≥ 2 tin và ≥ 10 đơn) giữ lại "
        f"<b>{_fmt_int(g['edges_by_type']['0'])} đơn ({_fmt_dec(meta['employer_extraction']['pct_apps_with_employer_and_client'], 2)}%)</b> "
        "của 9.116 nhà tuyển dụng để đổi lấy độ chính xác của nhãn silo.",
        "warn",
    )

    # -----------------------------------------------------------------
    # 4. Hướng làm tiếp: gập lại
    # -----------------------------------------------------------------
    with st.expander("4. Nếu có thêm thời gian", expanded=False):
        st.markdown(
            """
            | Hướng cải tiến | Vì sao cần thiết trên V3 | Ước lượng |
            |---|---|---|
            | **Mở rộng ánh xạ nghề O*NET bằng Sentence-BERT** | Nâng độ phủ cạnh `job–occupation` từ `31,44%` (`26.678` tin) lên `>85%` trên toàn bộ `84.845` tin tuyển dụng | ~2 ngày |
            | **Stratified Client Sampling trên 9.116 Node** | Lấy mẫu phân tầng nhiều vòng hơn qua toàn bộ `9.116` silo để thu hẹp khoảng cách Recall@20 trên vũ trụ toàn cục `82.876` tin | ~1–2 ngày |
            | **Secure Aggregation / DP-SGD** | Bảo vệ cập nhật embedding của từng nhà tuyển dụng trước nguy cơ suy ngược gradient trên máy chủ điều phối | ~1 ngày |
            | **Thử nghiệm A/B trực tuyến (Online A/B Test)** | Đo trực tiếp tỷ lệ nhấp (CTR), tỷ lệ nộp đơn thành công và mức độ hài lòng của ứng viên thật | ~1–2 tuần |
            """
        )

    # -----------------------------------------------------------------
    # 5 + 6. Bài học phương pháp và cách tái lập đứng cạnh nhau (2 cột)
    # -----------------------------------------------------------------
    with theme.grid(2, "hoc-va-tai-lap"):
        with st.container():
            st.subheader("5. Bài học phương pháp")
            st.markdown(
                """
                1. **Quy tắc gán cạnh Cross-Silo quyết định tính hợp lệ của Federated Learning.**
                   Vì `44,58%` ứng viên nộp đơn ở nhiều công ty và chỉ `16,29%` cạnh test nằm cùng
                   client với cạnh train chính, cạnh `(u, j)` bắt buộc thuộc về `client_of_job[j]`
                   (nhà tuyển dụng sở hữu tin), tuyệt đối không gán theo `client_of_user[u]`.
                2. **Khung xương công khai (`Occupation + Skill`) là cầu nối sống còn giữa các Silo.**
                   Chuẩn hóa mã nghề O*NET về 6 ký tự gốc (`soc[:7]`) và dùng `Technology Skills.txt`
                   (`7.760` kỹ năng, tránh `Skills.txt` có entropy bằng 0) giúp tăng `+9,0%` Recall@20
                   (`0,3933` → `0,4833`) mà không cần chia sẻ dữ liệu ứng tuyển.
                3. **Train cục bộ quá nhiều epoch gây hiện tượng Client Drift.**
                   Tăng `local_epochs` từ `1` lên `5` làm thời gian chạy tăng gần 5 lần
                   (`39,7s` → `195,5s`) nhưng `Recall@20` lại giảm từ `0,4833` xuống `0,4565`.
                4. **Đánh giá minh bạch trên đa hệ quy chiếu và kiểm soát rò rỉ dữ liệu.**
                   Luôn công bố đồng thời kết quả trên Vũ trụ toàn cục (`82.876` tin), Vũ trụ FL
                   (`9.058` / `4.511` tin), tập kiểm thử đầy đủ (`37.957` cạnh) và tập kiểm thử sạch
                   (`37.077` cạnh sau khi loại `880` cạnh trùng cặp) kèm Bootstrap CI 95%.
                """
            )

        with st.container():
            st.subheader("6. Cách tái lập toàn bộ")
            st.code(
                """# 1. Tiền xử lý CareerBuilder + O*NET & dựng đồ thị V3 (264.995 nút, 9.116 node FL)
python src/prepare_v3.py

# 2. Khởi chạy PostgreSQL (Docker cổng 5433) và nạp 21+ triệu bản ghi đồ thị
docker compose up -d
python -m api.load_to_pg

# 3. Khởi động FastAPI Backend (11 endpoint REST/WS giám sát Node FL)
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# 4. Chạy giao diện thuyết trình Streamlit (5 trang đồng bộ V3)
python -m streamlit run app/streamlit_app.py""",
                language="powershell",
            )
