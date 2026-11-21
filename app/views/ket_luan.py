"""Trang 6 — Kết luận: đạt gì, chưa đạt gì, làm tiếp thế nào.

BỐ CỤC (đã đo lại, xem báo cáo của task t6):
- Trước đây trang này có **0 cột**: 8 ô `finding()` + 1 bảng + 2 bảng markdown +
  1 danh sách + 1 khối code dàn hết theo chiều dọc, nên mỗi dòng chữ chỉ dùng
  một phần chiều ngang và trang cao 2.519px (1920px, sidebar đóng).
- Bảng "đạt / chưa đạt" để FULL-WIDTH với cột «kết luận» tô màu (xanh = Đạt,
  đỏ = Chưa) thay vì một khối bảng 1 cột dọc. Đã thử tách thành 2 bảng cạnh
  nhau (`st.columns([1,1])`): ở 1024px mỗi bảng chỉ còn ~490px nên bảng bị
  CẮT mất cột «thực đo» và «kết luận» — đúng thứ không được phép xảy ra. Giữ
  một bảng full-width thì mọi ô vẫn đọc được ở mọi bề rộng.
- Ba ô "đã làm được" và năm ô "chưa làm được" xếp thành 2 cột thay vì mỗi ô
  một tầng; ô nói về phạm vi toàn bộ dữ liệu để full-width.
- Khối "Nếu có thêm thời gian" gập trong `st.expander`: nội dung còn nguyên,
  chỉ không chiếm chỗ khi người xem chưa cần.
- "Bài học phương pháp" và "Cách tái lập" đứng cạnh nhau (2 cột).

VÌ SAO DÙNG `theme.grid(2, ...)` CHỨ KHÔNG PHẢI `st.columns`:
`theme.grid` tạo container có khoá; CSS của Streamlit biến nó thành lưới
`auto-fit minmax(420px, 1fr)` và TỰ hạ xuống 1 cột dưới 900px. Với đúng 2
khối con thì ở 1919px chỉ có 2 cột — đúng ý đồ. (Nếu nhét 4 khối con thì
`auto-fit` cho ra 4 cột ở bề rộng lớn, nên đã tách thành 2 lưới riêng, mỗi
lưới 2 khối.) Đo ở 1024px + sidebar mở (khung chỉ còn 724px): lưới tự xếp
dọc, không tràn ngang, khối code không bị bóp — đây là lý do không dùng
`st.columns([1,1])` (luôn 2 cột, làm khối code chỉ còn ~350px).

RÀNG BUỘC NỘI DUNG: đây là trang kết luận học thuật — các câu đánh giá
đạt/chưa đạt được giữ NGUYÊN VĂN. Task này chỉ đổi cách bày; phần chữ tiếng
Việt chỉ thêm một dòng đếm suy ra trực tiếp từ chính bảng bên dưới
("Đếm từ bảng bên dưới: 5/6 yêu cầu đạt · 1 yêu cầu chưa đạt.").
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components import finding, header, load_json, theme
from app.paths import PATHS


def render() -> None:
    header(
        "Kết luận và hạn chế",
        "Đề bài đặt ra những yêu cầu nào, cái nào đã đạt, cái nào chưa và vì sao?",
        kicker="Tổng hợp kết quả",
    )

    reco = load_json(PATHS["reco"])

    d = reco["data_summary"]
    fed = reco["systems"]["fedavg"]
    loc = reco["systems"]["local_only"]
    cent = reco["systems"]["centralized"]
    c = reco["communication"]
    pop = reco["systems"]["popularity"]

    # -----------------------------------------------------------------
    # 1. Bảng đối chiếu yêu cầu — TÁCH 2 CỘT theo kết luận đạt / chưa đạt.
    #    Số dòng đếm từ chính danh sách `rows` bên dưới, nên nhãn không bao
    #    giờ lệch với bảng. Bộ cột dữ liệu giữ nguyên (yêu cầu / cách đo /
    #    thực đo / kết luận) — không lược bỏ thông tin nào.
    # -----------------------------------------------------------------
    st.subheader("1. Yêu cầu của đề bài và kết quả thực đo")
    st.markdown(
        "Bảng dưới đây đối chiếu **từng yêu cầu** trong đề bài với số đo thật. "
        "Cột «cách đo» cho biết con số được tính như thế nào — không có con số "
        "nào được tuyên bố mà không kèm cách đo."
    )

    rows = [
        {"yêu cầu": "Giảm tỉ lệ lỗi gợi ý",
         "cách đo": "Recall@20 so với baseline phổ biến",
         "thực đo": f"{pop['recall@20']:.4f} → {fed['recall@20']:.4f}",
         "kết luận": "Đạt"},
        {"yêu cầu": "Nâng Recall@20",
         "cách đo": "Trung bình theo người dùng, K = 20",
         "thực đo": f"{pop['recall@20']:.4f} → {fed['recall@20']:.4f}",
         "kết luận": "Đạt"},
        {"yêu cầu": "Nâng NDCG@20",
         "cách đo": "Trung bình theo người dùng, K = 20",
         "thực đo": f"{pop['ndcg@20']:.4f} → {fed['ndcg@20']:.4f}",
         "kết luận": "Đạt"},
        {"yêu cầu": "Nâng MRR",
         "cách đo": "Nghịch đảo hạng tin liên quan đầu tiên",
         "thực đo": f"{pop['mrr@20']:.4f} → {fed['mrr@20']:.4f}",
         "kết luận": "Đạt"},
        {"yêu cầu": "Dữ liệu không rời khỏi khách hàng",
         "cách đo": "Kiểm payload client gửi lên (có test tự động)",
         "thực đo": "0 dòng dữ liệu thô rời máy",
         "kết luận": "Đạt"},
        {"yêu cầu": "Tăng mức độ hài lòng người dùng",
         "cách đo": "Cần A/B test trên người dùng thật",
         "thực đo": "Không đo được trong phạm vi đồ án",
         "kết luận": "Chưa"},
    ]

    rows_dat = [r for r in rows if r["kết luận"] == "Đạt"]
    rows_chua = [r for r in rows if r["kết luận"] != "Đạt"]

    # Dòng đếm suy ra trực tiếp từ `rows` ở trên — không phải câu đánh giá mới.
    st.info(
        f"Đếm từ bảng bên dưới: **{len(rows_dat)}/{len(rows)} yêu cầu đạt** · "
        f"{len(rows_chua)} yêu cầu chưa đạt."
    )

    # Bảng giữ NGUYÊN 4 cột và nguyên từng ô; chỉ tô màu cột "kết luận"
    # (xanh = Đạt, đỏ = Chưa) để đọc được ngay mà không phải quét từng dòng.
    tbl = pd.DataFrame(rows)

    def _to_mau(row: pd.Series) -> list[str]:
        mau = ("color:#1e8449;font-weight:700" if row["kết luận"] == "Đạt"
               else "color:#a93226;font-weight:700")
        return ["" if col != "kết luận" else mau for col in row.index]

    st.dataframe(
        tbl.style.apply(_to_mau, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    # -----------------------------------------------------------------
    # 2. Ba ô "đã làm được": hai ô đầu đứng cạnh nhau, ô thứ ba (nói về
    #    ranh giới dữ liệu) giữ nguyên độ rộng để câu không bị bó.
    # -----------------------------------------------------------------
    st.subheader("2. Điều đã làm được")

    with theme.grid(2, "da-lam-duoc"):
        with st.container():
            finding(
                "FL thu hẹp khoảng cách với mô hình tập trung",
                f"Recall@20: cục bộ {loc['recall@20']:.3f} → liên bang {fed['recall@20']:.3f} "
                f"→ tập trung {cent['recall@20']:.3f}. FL lấy lại được "
                f"{(fed['recall@20'] - loc['recall@20']) / (cent['recall@20'] - loc['recall@20']):.0%} "
                "khoảng cách mà việc chia nhỏ dữ liệu đã làm mất, **mà không cần gửi "
                "một dòng dữ liệu nào**.",
                "good",
            )
        with st.container():
            finding(
                "Mô hình đồ thị vượt baseline rõ rệt",
                f"Recall@20 của GNN ({cent['recall@20']:.3f}) so với Item-KNN "
                f"({reco['systems']['item_knn']['recall@20']:.3f}), phổ biến "
                f"({pop['recall@20']:.3f}) và content-based "
                f"({reco['systems']['skill_cbf']['recall@20']:.3f}). Việc dựng đồ thị "
                "có đóng góp thật, không phải trang trí.",
                "good",
            )

    finding(
        "Đường ranh giới dữ liệu được kiểm bằng test tự động",
        "Payload client gửi lên chỉ gồm chỉ số nút, vector float32 và trọng số "
        "— không có user_id, job_id hay rating nào. Kích thước payload cũng "
        "không phụ thuộc số bản ghi, nên số tương tác của một khách hàng không "
        "bị suy ra từ kích thước gói tin.",
        "good",
    )

    # -----------------------------------------------------------------
    # 3. Năm ô "chưa làm được": 2 + 2 cột, ô cuối full-width vì nói về
    #    nhiễu ảnh hưởng tới MỌI phương pháp (phạm vi rộng hơn một ô).
    # -----------------------------------------------------------------
    st.subheader("3. Điều CHƯA làm được — nói thẳng")

    with theme.grid(2, "chua-lam-duoc-1"):
        with st.container():
            finding(
                "FL không tiết kiệm băng thông ở quy mô dữ liệu này",
                f"Gửi tham số tốn gấp {c['ratio_up_vs_raw']:,.0f} lần so với gửi dữ liệu "
                f"thô. Chỉ rẻ hơn khi vượt khoảng {c['crossover_interactions']:,} tương "
                "tác. Ở quy mô nhỏ, FL là lựa chọn vì **tuân thủ pháp lý**, không phải "
                "vì hiệu quả kỹ thuật.",
                "warn",
            )
        with st.container():
            finding(
                "Cỡ mẫu đánh giá gợi ý rất nhỏ",
                f"Chỉ {d['users_in_test']} ứng viên có mặt trong tập kiểm thử, "
                f"{d['n_test']} tương tác. Khoảng tin cậy 95% rộng đến mức nhiều khác "
                "biệt giữa các phương pháp chưa có ý nghĩa thống kê. Cần thu thập thêm "
                "dữ liệu thật trước khi kết luận chắc chắn.",
                "warn",
            )

    with theme.grid(2, "chua-lam-duoc-2"):
        with st.container():
            finding(
                "Chưa đo được mức độ hài lòng của người dùng",
                "Đây là một yêu cầu của đề bài nhưng cần A/B test hoặc khảo sát trên "
                "người dùng thật. Đồ án chỉ đo được chỉ số xếp hạng offline, nên "
                "**không** tuyên bố đạt yêu cầu này.",
                "bad",
            )
        with st.container():
            finding(
                "Chưa có bảo vệ riêng tư thật sự",
                "FL hiện tại vẫn gửi tham số lên máy chủ. Kẻ tấn công kiểm "
                "soát máy chủ có thể suy ngược một phần dữ liệu từ gradient. Cần "
                "secure aggregation hoặc DP-SGD để chặn — chưa làm trong đồ án.",
                "bad",
            )

    finding(
        "Dữ liệu có nhiễu hệ thống",
        f"{d['quality']['template_jobs']} tin ({d['quality']['template_pct']}%) "
        "dùng chung một tập kỹ năng mẫu, và một phần tin có link sinh tự động "
        "không kiểm chứng được. Nhóm không loại bỏ vì sẽ mất khoảng hai phần ba "
        "dữ liệu, nhưng ghi rõ đây là nhiễu ảnh hưởng đến mọi phương pháp.",
        "warn",
    )

    # -----------------------------------------------------------------
    # 4. Hướng làm tiếp: gập lại — thông tin còn nguyên, chỉ không chiếm
    #    chỗ khi người xem chưa mở.
    # -----------------------------------------------------------------
    with st.expander("4. Nếu có thêm thời gian", expanded=False):
        st.markdown(
            """
            | Hướng | Vì sao | Ước lượng |
            |---|---|---|
            | **Secure aggregation / DP-SGD** | FL hiện tại vẫn gửi tham số; kẻ tấn công tinh vi có thể suy ngược thông tin từ gradient | ~1 ngày |
            | **Hiệu chuẩn lại điểm số** | Điểm BPR không phải xác suất; hiệu chuẩn giúp so sánh giữa các khách hàng | ~3 giờ |
            | **Thu thập thêm tương tác** | Tăng cỡ mẫu đánh giá từ 16 lên vài trăm ứng viên | phụ thuộc dữ liệu |
            | **Khảo sát người dùng thật** | Đo trực tiếp yêu cầu «tăng mức độ hài lòng» của đề bài | ~1 tuần |
            """
        )

    # -----------------------------------------------------------------
    # 5 + 6. Bài học phương pháp và cách tái lập đứng cạnh nhau: hai khối
    #        này đều là chữ ngắn, trước đây chiếm hai tầng dọc riêng.
    #        Dùng theme.grid để TỰ xếp dọc dưới 900px — khối code không bị
    #        bóp khi sidebar mở trên màn 1024px.
    # -----------------------------------------------------------------
    with theme.grid(2, "hoc-va-tai-lap"):
        with st.container():
            st.subheader("5. Bài học phương pháp")
            st.markdown(
                """
                1. **Cách chia dữ liệu quyết định kết luận.** Cùng một mô hình có thể
                   cho kết quả rất khác nhau tùy cách chia tập kiểm thử. Mọi con số
                   trong báo cáo này đều ghi rõ giao thức.
                2. **Trung bình các seed che giấu lỗi.** Nếu chỉ báo trung bình, người
                   đọc không thấy sự bất ổn. Luôn xem cả độ lệch chuẩn.
                3. **Chỉ số xếp hạng và chất lượng sử dụng khác nhau về bản chất.**
                   Recall@20 cao không có nghĩa là người dùng thấy gợi ý tốt hơn.
                4. **Mô hình nhẹ thắng mô hình phức tạp khi dữ liệu nhỏ.** GraphSAGE
                   (có MLP) kém hơn LightGCN (chỉ lan truyền tuyến tính) trên tập
                   MEDAJob này; thêm tham số chỉ làm mô hình dễ overfit hơn.
                """
            )

        with st.container():
            st.subheader("6. Cách tái lập toàn bộ")
            st.code(
                """# một lệnh duy nhất, sinh lại mọi số liệu, hình và báo cáo
powershell -ExecutionPolicy Bypass -File run_all.ps1

# hoặc chạy từng bước
python src/medajob/prepare.py          # làm sạch + dựng đồ thị
python src/medajob/run_experiments.py  # centralized / local / FedAvg / FedProx
python src/report/figures.py           # 9 hình cho báo cáo
python src/report/make_facts.py        # docs/SO_LIEU_CHINH.md
python src/report/build_docx.py        # xuất .docx""",
                language="powershell",
            )
            st.caption(
                "Toàn bộ chạy trên CPU, không cần GPU. Kết quả tất định theo seed "
                "trong config.yaml nên chạy lại cho cùng số."
            )
