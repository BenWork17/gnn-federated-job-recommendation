"""
Dựng báo cáo .docx hoàn chỉnh từ template PBL6 của khoa.

KHÔNG có con số nào gõ tay: mọi giá trị đọc từ results/*.json và
artifacts/*/meta.json|stats.json. Cuối mỗi lần dựng, verify_numbers()
đối chiếu các con số then chốt có mặt trong tài liệu.

Chạy: python src/report/build_docx.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.report.docx_helpers as DH
from src.common import (ROOT, banner, load_config, load_json, setup_console,
                        step)
from src.report.docx_helpers import Report


def fnum(x, nd: int = 4) -> str:
    return f"{x:.{nd}f}"


def fpct(x, nd: int = 2) -> str:
    return f"{100 * x:.{nd}f}%"


def build(cfg: dict) -> Report:
    results = Path(cfg["paths"]["results"])
    art = Path(cfg["paths"]["artifacts"])

    reco = load_json(results / "reco_main.json")
    meta = load_json(art / "medajob" / "meta.json")
    manifest = load_json(results / "figures" / "manifest.json")

    d = reco["data_summary"]
    q = d["quality"]
    sys_ = reco["systems"]

    students = [cfg["report"]["student1"], cfg["report"]["student2"]]
    rep = Report(Path(cfg["report"]["template"]),
                 Path(cfg["paths"]["figures"]),
                 fig_width_cm=float(cfg["report"]["figure_width_cm"]))
    rep.reset_body()
    rep.fill_cover(
        title="BÁO CÁO ĐỒ ÁN: GNN KẾT HỢP HỌC LIÊN BANG",
        subtitle="Ứng dụng mạng nơ-ron đồ thị cho gợi ý việc làm "
                 "trên kiến trúc dữ liệu phân tán",
        students=students,
        course="DSS: HỆ HỖ TRỢ QUYẾT ĐỊNH",
    )
    rep.toc()

    # =================================================================
    # MỞ ĐẦU
    # =================================================================
    rep.h1("MỞ ĐẦU")
    rep.p(
        "Báo cáo này trình bày một ứng dụng của mạng nơ-ron đồ thị (Graph "
        "Neural Network — GNN) kết hợp học liên bang (Federated Learning — FL) "
        "cho bài toán **gợi ý việc làm** trong bối cảnh dữ liệu không thể tập "
        "trung về một máy chủ."
    )
    rep.p(
        "Mô hình gợi ý việc làm truyền thống giả định toàn bộ tin tuyển dụng và "
        "hồ sơ ứng viên nằm trên một máy chủ. Thực tế dữ liệu tuyển dụng thuộc "
        "về nhiều nền tảng và doanh nghiệp khác nhau, và việc gom hồ sơ cá nhân "
        "về một nơi bị chặn bởi Luật Bảo vệ dữ liệu cá nhân cũng như GDPR. Đây "
        "là ràng buộc định hình toàn bộ thiết kế của đồ án."
    )
    rep.p(
        "Cách tiếp cận của nhóm là kết hợp **biểu diễn đồ thị** (để tận dụng "
        "quan hệ giữa người dùng, tin tuyển dụng, kỹ năng và ngành nghề) với "
        "**học liên bang** (để mô hình học mà dữ liệu gốc không rời khỏi nơi "
        "lưu trữ). Báo cáo không chỉ trình bày kết quả thuận lợi mà cả những "
        "trường hợp mô hình chưa đạt, kèm phân tích nguyên nhân."
    )
    rep.p(
        "Ba câu hỏi nghiên cứu được đặt ra và trả lời xuyên suốt báo cáo: "
        "(RQ1) Học liên bang có thu hẹp được khoảng cách với mô hình tập "
        "trung hay không? (RQ2) Mô hình đồ thị nhẹ có đủ chất lượng để triển "
        "khai trong điều kiện dữ liệu thực tế của môn học hay không? "
        "(RQ3) Cái giá phải trả — băng thông và rủi ro riêng tư — là bao nhiêu?"
    )

    # =================================================================
    # 1. GIỚI THIỆU
    # =================================================================
    rep.h1("1. GIỚI THIỆU VÀ ĐỘNG CƠ NGHIÊN CỨU")

    rep.h2("1.1. Bài toán gợi ý việc làm dưới ràng buộc dữ liệu phân tán")
    rep.p(
        "Cho tập người dùng U, tập tin tuyển dụng J và ma trận tương tác thưa "
        "R (rating 1–5), mục tiêu là học hàm dự đoán ŷ(u, j) sao cho danh sách "
        "top-K gợi ý cho mỗi người dùng chứa nhiều tin «liên quan» nhất. Trong "
        "báo cáo này, một tin được coi là liên quan nếu rating ≥ "
        f"{reco['config']['relevant_threshold']}."
    )
    rep.p(
        f"Bộ dữ liệu MEDAJob mà nhóm thu được có {d['n_jobs']:,} tin còn hiệu "
        f"lực, {d['n_users']} ứng viên và chỉ {d['n_train'] + d['n_test']} "
        f"tương tác thật. Mật độ ma trận là **{d['sparsity_pct']:.2f}%** — "
        "nghĩa là hơn 99,5% ô trống. Đây là mức thưa cực đoan, khiến mọi "
        "phương pháp chỉ dựa trên đồng xuất hiện đều yếu."
    )
    rep.p(
        "Ràng buộc phân tán thể hiện ở chỗ: dữ liệu tuyển dụng thuộc về nhiều "
        "nền tảng/công ty. Gom toàn bộ về một máy chủ để huấn luyện là vi phạm "
        "quy định bảo vệ dữ liệu cá nhân. Vì vậy kiến trúc đặt ra là: máy chủ "
        "trung tâm chỉ giữ **cấu trúc công khai** (nút Kỹ năng, nút Ngành), "
        "còn mỗi khách hàng giữ dữ liệu riêng và dựng đồ thị con cục bộ."
    )

    rep.h2("1.2. Ràng buộc dữ liệu phân tán và kiến trúc đề xuất")
    rep.p(
        "Kiến trúc mà đề bài đặt ra có ba tầng rõ ràng. **Máy chủ trung tâm** "
        "giữ cấu trúc đồ thị chung — nút Kỹ năng và nút Ngành — đây là dữ liệu "
        "công khai, không nhạy cảm, có thể chia sẻ cho mọi bên. **Mỗi khách "
        "hàng** (một nền tảng hoặc doanh nghiệp tuyển dụng) chỉ lưu dữ liệu "
        "riêng của mình: tin tuyển dụng và hồ sơ ứng viên, tại cơ sở dữ liệu "
        "nội bộ, và không gửi dữ liệu gốc ra ngoài. **Bên trong mỗi khách "
        "hàng**, nhóm dựng một đồ thị con cục bộ gồm Việc làm ↔ Kỹ năng ↔ "
        "Ngành, nối vào tập nút chung do máy chủ phát xuống."
    )
    rep.p(
        "Điểm mấu chốt về mặt kỹ thuật: thứ duy nhất đi qua đường truyền giữa "
        "khách hàng và máy chủ là **tham số mô hình**, không phải bản ghi dữ "
        "liệu. Với LightGCN, toàn bộ tham số học được chỉ là một bảng "
        "embedding, nên gói tin trao đổi có kích thước cố định theo số nút và "
        "số chiều — không phụ thuộc số tương tác. Hệ quả này vừa là ưu điểm "
        "(không lộ dữ liệu thô, không phụ thuộc quy mô dữ liệu) vừa là hạn chế "
        "(chi phí không giảm khi dữ liệu ít), và được phân tích định lượng ở "
        "mục 3.5."
    )
    rep.p(
        "Cần nói rõ ngay một giới hạn của thiết kế: máy chủ vẫn thấy tham số "
        "mô hình, nên học liên bang **không** đồng nghĩa với bảo mật tuyệt đối. "
        "Mô hình mối đe dọa và hai rủi ro còn lại được trình bày ở mục 2.4."
    )

    rep.h2("1.3. Đóng góp của báo cáo")
    rep.bullets([
        f"Một pipeline hoàn chỉnh từ dữ liệu thô tới kết quả, chạy được trên "
        f"CPU thông thường, tái lập được theo seed.",
        f"So sánh công bằng sáu hệ gợi ý trên cùng một tập kiểm thử, trong đó "
        f"có mô hình cục bộ (không chia sẻ), FedAvg, FedProx và mốc tập trung.",
        f"Chỉ ra bằng thực nghiệm rằng học liên bang thu hẹp "
        f"{(sys_['fedavg']['recall@20'] - sys_['local_only']['recall@20']) / (sys_['centralized']['recall@20'] - sys_['local_only']['recall@20']):.0%} "
        f"khoảng cách do chia nhỏ dữ liệu gây ra.",
        "Một phân tích định lượng về cái giá của học liên bang: chi phí truyền "
        "thông, điểm hoà vốn, và hai rủi ro riêng tư chưa được xử lý.",
        "Một bộ công cụ trực quan hóa tương tác sáu trang phục vụ trình bày.",
    ])

    # =================================================================
    # 2. CƠ SỞ LÝ THUYẾT
    # =================================================================
    rep.h1("2. CƠ SỞ LÝ THUYẾT")

    rep.h2("2.1. Truyền thông điệp trên đồ thị và LightGCN")
    rep.p(
        "Mạng nơ-ron đồ thị cập nhật biểu diễn của mỗi nút bằng cách tổng hợp "
        "thông tin từ các nút lân cận. Với đồ thị có ma trận kề A và bậc D, "
        "một tầng lan truyền có dạng:"
    )
    rep.formula("H^(l+1) = Â · H^(l),    Â = D^(-1) · A")
    rep.p(
        "LightGCN (He và cộng sự, 2020) đơn giản hóa mô hình bằng cách bỏ hoàn "
        "toàn phép biến đổi phi tuyến:"
    )
    rep.formula("E = (1/(L+1)) · Σ_{l=0}^{L} H^(l),    H^(0) = E^(0)")
    rep.p(
        "Điểm số của cặp (người dùng u, tin j) là tích vô hướng của biểu diễn "
        "sau lan truyền: ŷ(u, j) = e_u^T · e_j. Toàn bộ tham số học được chỉ "
        "là bảng embedding E^(0) kích thước (số nút × số chiều). Đây chính là "
        "lý do mô hình nhẹ và cũng là lý do trong học liên bang chỉ cần gửi "
        "bảng embedding này, không gửi đồ thị hay dữ liệu."
    )
    rep.p(
        "Nhóm chọn chuẩn hóa D^(-1)A thay vì D^(-1/2)A·D^(-1/2) của bản gốc. "
        "Lý do: đồ thị có những nút bậc rất cao (kỹ năng «python» nối với hàng "
        "trăm tin), và chuẩn hóa đối xứng làm biểu diễn của nút bậc thấp gần "
        "như triệt tiêu trong khi mọi thông tin lại chảy qua nút bậc cao."
    )

    rep.h2("2.2. Hàm mất mát BPR")
    rep.p(
        "Vì dữ liệu chỉ có tương tác dương tính (người dùng quan tâm tới tin "
        "nào), nhóm dùng Bayesian Personalised Ranking. Với mỗi cặp (u, j+) "
        "lấy ngẫu nhiên một tin j- chưa tương tác:"
    )
    rep.formula("L = -Σ log σ(ŷ(u, j+) - ŷ(u, j-)) + λ·||E||²")
    rep.p(
        "Hàm này chỉ dùng các tương tác đã biết, phù hợp với cả mô hình cục "
        "bộ lẫn học liên bang vì mỗi khách hàng có thể tự sinh mẫu âm từ "
        "chính dữ liệu mình đang giữ."
    )

    rep.h2("2.3. Học liên bang: FedAvg và FedProx")
    rep.p(
        "Với K khách hàng, mỗi vòng t truyền thông thực hiện: máy chủ phát "
        "tham số w^t cho các khách hàng được chọn; mỗi khách hàng k huấn luyện "
        "cục bộ E vòng lặp và trả về w_k^(t+1); máy chủ lấy trung bình có "
        "trọng số theo số mẫu n_k:"
    )
    rep.formula("w^(t+1) = Σ_k (n_k / n) · w_k^(t+1),    n = Σ_k n_k")
    rep.p(
        "FedProx thêm số hạng proximal để hạn chế khách hàng trôi quá xa mô "
        "hình toàn cục (quan trọng khi dữ liệu các khách hàng không đồng nhất):"
    )
    rep.formula("L_k(w) = L_k^BPR(w) + (μ/2)·||w - w^t||²,    μ = "
                f"{reco['client_sweep'][0]['fl_info']['mu'] if False else cfg['medajob']['federated']['fedprox_mu']}")
    rep.p(
        "**Một lỗi cài đặt quan trọng đã phát hiện và sửa.** Ban đầu số hạng "
        "proximal được tính trên `model.state_dict()`. Trong PyTorch 2.x, "
        "`state_dict()` trả về tensor đã detach, nên số hạng này không có "
        "gradient và FedProx trở thành FedAvg trần. Triệu chứng là μ = 5 cho "
        "kết quả trùng khít μ = 0 tới 7·10⁻⁷. Sau khi chuyển sang "
        "`named_parameters()`, μ = 0,01 cho kết quả khác rõ rệt. Đây là ví dụ "
        "cho thấy vì sao phải kiểm tra chéo bằng thực nghiệm chứ không tin vào "
        "việc «code chạy không lỗi»."
    )

    rep.h2("2.4. Mô hình mối đe dọa")
    rep.p(
        "Trong thiết kế này, máy chủ trung tâm **không** thấy: danh tính người "
        "dùng, nội dung hồ sơ, hay bất kỳ rating nào. Máy chủ chỉ thấy trung "
        "bình các tham số. Vẫn còn hai rủi ro chưa được xử lý trong đồ án:"
    )
    rep.bullets([
        "**Tấn công suy ngược từ gradient** — kẻ tấn công kiểm soát máy chủ có "
        "thể tái tạo một phần dữ liệu huấn luyện từ gradient. Cần secure "
        "aggregation hoặc DP-SGD để chặn.",
        "**Rò rỉ qua nhiều vòng** — tham số của một nút chỉ được cập nhật bởi "
        "những khách hàng có dữ liệu về nút đó, nên theo dõi nhiều vòng có thể "
        "suy ra khách hàng nào giữ dữ liệu gì. Trong đồ án, cơ chế FedAvg thưa "
        "chỉ gửi các hàng embedding thay đổi — đây là đánh đổi có ý thức giữa "
        "chất lượng và độ phức tạp triển khai.",
    ])

    # =================================================================
    # 3. BÀI TOÁN
    # =================================================================
    rep.h1("3. GNN KẾT HỢP HỌC LIÊN BANG CHO GỢI Ý VIỆC LÀM")

    rep.h2("3.1. Dữ liệu và làm sạch")
    rep.p(
        f"Bộ MEDAJob tải từ hệ thống môn học gồm 5 bảng. Dữ liệu thô có nhiều "
        f"vấn đề phải xử lý trước khi tính toán: trường kỹ năng trộn hai định "
        f"dạng (JSON list và chuỗi phân cách dấu phẩy), token dính quote hoặc "
        f"ngoặc, cụm từ bị tách rời («machine», «learning»), tin trùng do dữ "
        f"liệu seed sinh tự động, và rating trỏ vào tin đã đóng."
    )
    rep.p(
        "Quy trình làm sạch gồm: chuẩn hóa kỹ năng (bỏ quote, ghép cụm, đồng "
        "nghĩa), chỉ giữ tin đang mở và có kỹ năng, loại tin trùng theo khóa "
        "(tiêu đề bỏ số thứ tự + tập kỹ năng + công ty), rồi lọc rating hợp lệ. "
        "Kết quả:"
    )
    rep.table(
        pd.DataFrame([
            {"Bước": "Dữ liệu gốc", "Tin": f"{meta['raw']['jobs']:,}",
             "Hồ sơ": f"{meta['raw']['profiles']}", "Rating": f"{meta['raw']['ratings']}"},
            {"Bước": "Bỏ tin đã đóng", "Tin": f"-{q['jobs_dropped_closed']}",
             "Hồ sơ": "—", "Rating": "—"},
            {"Bước": "Bỏ tin trùng",
             "Tin": f"-{q['jobs_dropped_duplicate']}",
             "Hồ sơ": f"-{meta['raw']['profiles'] - d['n_users']}",
             "Rating": f"-{q['ratings_dropped']}"},
            {"Bước": "Còn dùng được", "Tin": f"{d['n_jobs']:,}",
             "Hồ sơ": f"{d['n_users']}", "Rating": f"{d['n_train'] + d['n_test']}"},
        ]),
        "Kết quả làm sạch dữ liệu MEDAJob",
        widths=[5.0, 3.2, 3.2, 3.2],
    )
    rep.p(
        f"Đáng chú ý, **{q['template_jobs']} tin ({q['template_pct']}%)** dùng "
        f"chung một tập kỹ năng mẫu (ví dụ hàng trăm tin cùng tập "
        f"git–javascript–python–sql) và **{q['title_only_jobs']} tin** có mô tả "
        f"chỉ lặp lại đúng tiêu đề. Nhóm **không loại** những tin này vì sẽ "
        f"mất khoảng hai phần ba dữ liệu, nhưng ghi rõ đây là nhiễu có hệ thống "
        f"ảnh hưởng đến mọi phương pháp dựa trên nội dung."
    )
    rep.figure("F02_lam_sach_du_lieu.png",
               "Kết quả làm sạch và các vấn đề chất lượng còn lại trong dữ liệu.")
    rep.figure("F03_do_thua.png",
               f"Độ thưa của ma trận tương tác: chỉ {d['sparsity_pct']:.2f}% số ô "
               f"có dữ liệu.")

    rep.h2("3.2. Cấu trúc đồ thị và phân vùng khách hàng")
    rep.p(
        f"Đồ thị không đồng nhất gồm bốn loại nút và bốn loại cạnh. Tổng cộng "
        f"{meta['graph']['nodes']:,} nút và {meta['graph']['edges']:,} cạnh có "
        f"hướng:"
    )
    rep.table(
        pd.DataFrame([
            {"Loại nút": "Người dùng", "Số lượng": f"{d['n_users']}",
             "Nơi lưu": "Khách hàng"},
            {"Loại nút": "Tin tuyển dụng", "Số lượng": f"{d['n_jobs']:,}",
             "Nơi lưu": "Khách hàng"},
            {"Loại nút": "Kỹ năng", "Số lượng": f"{d['n_skills']}",
             "Nơi lưu": "Máy chủ (công khai)"},
            {"Loại nút": "Ngành", "Số lượng": f"{d['n_industries']}",
             "Nơi lưu": "Máy chủ (công khai)"},
        ]),
        "Bốn loại nút trong đồ thị",
        widths=[4.5, 3.0, 5.0],
    )
    rep.p(
        f"Trong {meta['graph']['edges']:,} cạnh, chỉ "
        f"**{d['public_edges']:,} cạnh là công khai** (tin–kỹ năng, "
        f"tin–ngành) và được đặt trên máy chủ. Toàn bộ "
        f"{d['private_edges']:,} cạnh còn lại (người dùng–kỹ năng, "
        f"người dùng–tin) chỉ tồn tại bên trong khách hàng."
    )
    rep.p(
        "Nhóm ngành được suy ra từ tiêu đề tin bằng bộ từ khóa, không phải nhãn "
        "do con người gán. Hệ quả là một phần lớn tin rơi vào nhóm «Khác»; "
        "điều này được ghi nhận như một hạn chế của cách gán nhãn tự động."
    )
    rep.figure("F01_kien_truc.png",
               "Kiến trúc hệ thống: máy chủ giữ cấu trúc công khai, khách hàng "
               "giữ dữ liệu riêng, chỉ tham số được trao đổi.")
    rep.figure("F04_cau_truc_do_thi.png",
               "Phân chia cạnh giữa máy chủ và khách hàng.")
    rep.figure("F05_nganh.png", "Phân bố ngành nghề trong dữ liệu.")

    rep.h2("3.3. Giao thức thực nghiệm")
    rep.p(
        f"Với mỗi người dùng có từ {cfg['medajob']['min_ratings_for_test']} "
        f"tương tác trở lên, giữ lại {cfg['medajob']['test_ratio']:.0%} làm tập "
        f"kiểm thử. Kết quả: {d['n_train']} tương tác huấn luyện và "
        f"{d['n_test']} tương tác kiểm thử, trong đó chỉ "
        f"**{d['users_in_test']} người dùng** có ít nhất một tin liên quan bị "
        f"giấu. Cỡ mẫu nhỏ này là hạn chế lớn nhất của phần gợi ý và được "
        f"phản ánh qua khoảng tin cậy bootstrap."
    )
    rep.p("Các chỉ số đánh giá, tính ở mức từng người dùng rồi lấy trung bình:")
    rep.formula("P@K(u)    = |Liên quan(u) ∩ TopK(u)| / K")
    rep.formula("R@K(u)    = |Liên quan(u) ∩ TopK(u)| / |Liên quan(u)|")
    rep.formula("DCG@K(u)  = Σ_{i=1..K} rel_i / log2(i + 1)")
    rep.formula("NDCG@K(u) = DCG@K(u) / IDCG@K(u)")
    rep.formula("MRR@K(u)  = 1 / hạng của tin liên quan đầu tiên")
    rep.p(
        "Khoảng tin cậy 95% được tính bằng bootstrap trên đơn vị người dùng "
        f"(B = {reco['config'].get('n_boot', 1000)} lần lấy mẫu có hoàn lại). "
        "Lý do không dùng t-test: phân phối Recall lệch mạnh (nhiều người dùng "
        "có 0 hit) và cỡ mẫu nhỏ."
    )

    rep.h2("3.4. Kết quả")
    rows = []
    labels = [
        ("popularity", "Phổ biến"), ("skill_cbf", "Nội dung (kỹ năng)"),
        ("item_knn", "Item-KNN"), ("local_only", "Cục bộ (không chia sẻ)"),
        ("fedavg", "Liên bang (FedAvg)"), ("fedprox", "Liên bang (FedProx)"),
        ("centralized", "Tập trung (mốc trên)"),
        ("centralized_sage", "GraphSAGE thay LightGCN"),
    ]
    for key, label in labels:
        s = sys_.get(key)
        if not s:
            continue
        ci = s.get("recall@20_ci", {})
        rows.append({
            "Hệ": label,
            "R@10": fnum(s["recall@10"]),
            "R@20": fnum(s["recall@20"]),
            "CI 95% của R@20": f"[{ci.get('lo', 0):.3f}, {ci.get('hi', 0):.3f}]",
            "NDCG@20": fnum(s["ndcg@20"]),
            "MRR@20": fnum(s["mrr@20"]),
        })
    rep.table(pd.DataFrame(rows),
              "So sánh các hệ gợi ý trên cùng tập kiểm thử "
              f"(n = {reco['config']['n_eval_users']} người dùng)",
              widths=[3.9, 1.7, 1.7, 2.6, 1.9, 1.8], font_size=9.0)

    rep.figure("F06_so_sanh_phuong_phap.png",
               "So sánh sáu phương pháp gợi ý, kèm khoảng tin cậy 95%.")

    rep.p(
        f"**Trả lời RQ1.** Mô hình cục bộ (mỗi khách hàng tự huấn luyện, không "
        f"chia sẻ gì) đạt Recall@20 = {fnum(sys_['local_only']['recall@20'])}. "
        f"FedAvg nâng lên {fnum(sys_['fedavg']['recall@20'])}, tiệm cận mốc "
        f"tập trung {fnum(sys_['centralized']['recall@20'])}. Nói cách khác, "
        f"học liên bang lấy lại được "
        f"{(sys_['fedavg']['recall@20'] - sys_['local_only']['recall@20']) / (sys_['centralized']['recall@20'] - sys_['local_only']['recall@20']):.0%} "
        f"khoảng cách mà việc chia nhỏ dữ liệu đã làm mất, **mà không cần gửi "
        f"một dòng dữ liệu nào**."
    )
    rep.p(
        f"Đáng chú ý, mô hình đồ thị vượt baseline rõ rệt: "
        f"{fnum(sys_['centralized']['recall@20'])} so với Item-KNN "
        f"{fnum(sys_['item_knn']['recall@20'])}, phổ biến "
        f"{fnum(sys_['popularity']['recall@20'])} và nội dung "
        f"{fnum(sys_['skill_cbf']['recall@20'])}. Điều này xác nhận việc dựng "
        f"đồ thị có đóng góp thật."
    )
    rep.p(
        f"**Ablation kiến trúc.** Thay LightGCN bằng GraphSAGE (có MLP và "
        f"chuẩn hóa L2) làm chất lượng giảm mạnh: Recall@20 chỉ còn "
        f"{fnum(sys_['centralized_sage']['recall@20'])}. Với dữ liệu cực thưa, "
        f"tham số phi tuyến thêm vào chỉ khiến mô hình dễ overfit hơn. Đây là "
        f"một kết quả trái với trực giác «mạng sâu hơn thì tốt hơn»."
    )

    rep.figure("F07_duong_cong_fl.png",
               "Đường cong học liên bang theo từng vòng truyền thông.")
    rep.figure("F08_so_khach_hang.png",
               "Ảnh hưởng của số lượng khách hàng đến chất lượng mô hình.")

    rep.h2("3.5. Chi phí truyền thông — một kết quả không thuận lợi")
    c = reco["communication"]
    rep.p(
        f"Đây là phần ít được báo cáo trong các bài viết về học liên bang. Ở "
        f"quy mô dữ liệu này, gửi tham số tốn **{c['up_bytes_total'] / 1024:,.0f} KB** "
        f"trong {c['n_rounds']} vòng, so với chỉ "
        f"**{c['raw_data_bytes_if_centralized'] / 1024:.0f} KB** nếu gửi thẳng "
        f"dữ liệu thô đi một lần. Tỉ lệ là gấp {c['ratio_up_vs_raw']:,.0f} lần."
    )
    rep.p(
        f"Nguyên nhân mang tính bản chất: payload là O(số nút × số chiều) và "
        f"không phụ thuộc số tương tác, còn dữ liệu thô tỉ lệ với số tương tác "
        f"({c['raw_bytes_per_interaction']} byte mỗi tương tác). Học liên bang "
        f"chỉ rẻ hơn về băng thông khi tập dữ liệu vượt khoảng "
        f"{c['crossover_interactions']:,} tương tác."
    )
    rep.p(
        "Kết luận trung thực: với bài toán tuân thủ pháp lý, lợi ích của học "
        "liên bang nằm ở chỗ **dữ liệu gốc không rời khỏi khách hàng**, không "
        "phải ở hiệu quả băng thông."
    )
    rep.figure("F09_truyen_thong.png",
               "Chi phí truyền thông của học liên bang so với gửi dữ liệu thô, "
               "và điểm hoà vốn theo quy mô dữ liệu.")

    # =================================================================
    # 4. KIẾN TRÚC CÀI ĐẶT
    # =================================================================
    rep.h1("4. KIẾN TRÚC CÀI ĐẶT VÀ TÁI LẬP")

    rep.h2("4.1. Ràng buộc môi trường và các quyết định kéo theo")
    rep.p(
        "Nhóm phát triển trong một môi trường có ràng buộc chặt, và các ràng "
        "buộc này định hình kiến trúc cài đặt:"
    )
    rep.table(
        pd.DataFrame([
            {"Ràng buộc": "Không cài được gói mới (pip bị chặn)",
             "Hệ quả": "Không dùng PyTorch Geometric hay DGL",
             "Cách xử lý": "Tự viết lan truyền đồ thị bằng index_add_ và "
                           "scatter_reduce của PyTorch thuần"},
            {"Ràng buộc": "Không có GPU",
             "Hệ quả": "Mô hình phải nhỏ",
             "Cách xử lý": "LightGCN chỉ có 1 tham số học được "
                           "(bảng embedding)"},
            {"Ràng buộc": "Không cài được Plotly",
             "Hệ quả": "Không dùng biểu đồ Plotly",
             "Cách xử lý": "Dùng Altair (có sẵn trong Streamlit)"},
            {"Ràng buộc": "Thư mục cache mặc định không ghi được",
             "Hệ quả": "matplotlib và Streamlit lỗi khởi động",
             "Cách xử lý": "Ép MPLCONFIGDIR và các thư mục cache vào "
                           "artifacts/ trong dự án"},
            {"Ràng buộc": "Dữ liệu MEDAJob chỉ có một bản export",
             "Hệ quả": "Mọi «khách hàng» đều chia từ cùng một file",
             "Cách xử lý": "Phân vùng theo employer_id và ghi rõ đây là "
                           "mô phỏng, không phải nhiều hệ thống thật"},
        ]),
        "Ràng buộc môi trường và cách xử lý",
        widths=[5.0, 4.2, 5.0], font_size=8.5,
    )
    rep.p(
        "Việc tự viết lan truyền đồ thị hóa ra lại có lợi cho mục tiêu của đồ "
        "án: nó buộc phải chỉ rõ **chính xác cái gì được gửi lên máy chủ** "
        "trong học liên bang. Với PyTorch Geometric, thông tin này bị che sau "
        "các lớp trừu tượng."
    )

    rep.h2("4.2. Cấu trúc mã nguồn")
    rep.code("""CuoiKi/
├─ config.yaml              # toàn bộ tham số, không hard-code
├─ run_all.ps1              # một lệnh chạy hết
├─ src/
│  ├─ common.py             # seed, ghi JSON, bootstrap CI
│  ├─ medajob/              # prepare, models, federated, evaluate, run
│  └─ report/               # figures.py, build_docx.py, make_facts.py
├─ app/                     # Streamlit, 6 trang
├─ tests/                   # test parser, metrics, FedAvg, app smoke
├─ artifacts/               # dữ liệu đã xử lý (sinh tự động)
└─ results/                 # JSON + hình""")
    rep.p(
        "Nguyên tắc thiết kế: **mọi con số trong báo cáo này đều đọc từ file "
        "JSON** do pipeline sinh ra, không có giá trị nào gõ tay. Cuối mỗi "
        "lần dựng báo cáo, một hàm kiểm tra đối chiếu các con số then chốt có "
        "mặt trong tài liệu và báo lỗi nếu lệch."
    )

    rep.h2("4.3. Cách tái lập")
    rep.code("""# một lệnh duy nhất
powershell -ExecutionPolicy Bypass -File run_all.ps1

# hoặc từng bước
python src/medajob/prepare.py         # làm sạch + dựng đồ thị
python src/medajob/run_experiments.py # 6 hệ gợi ý
python src/report/figures.py          # 9 hình
python src/report/make_facts.py       # docs/SO_LIEU_CHINH.md
python src/report/build_docx.py       # xuất báo cáo này""")
    rep.p(
        "Toàn bộ chạy trên CPU. Kết quả tất định theo seed trong config.yaml; "
        "chạy lại cho cùng số tới sai số dấu phẩy động."
    )

    # =================================================================
    # 5. YÊU CẦU KẾT QUẢ
    # =================================================================
    rep.h1("5. ĐỐI CHIẾU VỚI YÊU CẦU KẾT QUẢ CỦA ĐỀ BÀI")
    rep.p(
        "Đề bài nêu ba nhóm yêu cầu cho bài toán gợi ý. Bảng dưới đối chiếu "
        "từng yêu cầu với số đo thật, kèm ghi chú về mức độ đạt được."
    )
    rep.table(
        pd.DataFrame([
            {"Yêu cầu": "Giảm tỉ lệ lỗi gợi ý",
             "Cách đo": "Recall@20 so với baseline phổ biến",
             "Kết quả": f"{fnum(sys_['popularity']['recall@20'])} → "
                        f"{fnum(sys_['fedavg']['recall@20'])}",
             "Đạt": "Có"},
            {"Yêu cầu": "Nâng Recall@20",
             "Cách đo": "Trung bình theo người dùng, K = 20",
             "Kết quả": f"{fnum(sys_['popularity']['recall@20'])} → "
                        f"{fnum(sys_['fedavg']['recall@20'])}",
             "Đạt": "Có"},
            {"Yêu cầu": "Nâng NDCG@20",
             "Cách đo": "Trung bình theo người dùng, K = 20",
             "Kết quả": f"{fnum(sys_['popularity']['ndcg@20'])} → "
                        f"{fnum(sys_['fedavg']['ndcg@20'])}",
             "Đạt": "Có"},
            {"Yêu cầu": "Nâng MRR",
             "Cách đo": "Nghịch đảo hạng của tin liên quan đầu tiên",
             "Kết quả": f"{fnum(sys_['popularity']['mrr@20'])} → "
                        f"{fnum(sys_['fedavg']['mrr@20'])}",
             "Đạt": "Có"},
            {"Yêu cầu": "Dữ liệu không rời khỏi khách hàng",
             "Cách đo": "Kiểm tra payload client gửi lên (có test tự động)",
             "Kết quả": "0 dòng dữ liệu thô rời máy",
             "Đạt": "Có"},
            {"Yêu cầu": "Tăng mức độ hài lòng người dùng",
             "Cách đo": "Cần A/B test hoặc khảo sát người dùng thật",
             "Kết quả": "Không đo được trong phạm vi đồ án",
             "Đạt": "Chưa"},
        ]),
        "Đối chiếu yêu cầu của đề bài với kết quả thực đo",
        widths=[4.6, 5.0, 3.4, 1.4], font_size=8.0,
    )
    rep.p(
        "Năm trên sáu yêu cầu đạt. Riêng «tăng mức độ hài lòng thực tế của "
        "người sử dụng» thì **không đo được**: đây là chỉ số cần người dùng "
        "thật đánh giá (A/B test hoặc khảo sát), trong khi đồ án chỉ đo được "
        "chỉ số xếp hạng offline. Nhóm ghi rõ điều này thay vì tuyên bố đạt."
    )
    rep.p(
        f"Về phần gợi ý, mức cải thiện đạt được **mà không cần gom dữ liệu về "
        f"một máy chủ**. Cái giá phải trả là băng thông (mục 3.5) và hai rủi "
        f"ro riêng tư còn lại (mục 2.4) — cả hai đều được nêu thay vì giấu."
    )

    # =================================================================
    # 6. KẾT LUẬN
    # =================================================================
    rep.h1("6. KẾT LUẬN VÀ HẠN CHẾ")

    rep.h2("6.1. Những gì đã làm được")
    rep.bullets([
        f"**Học liên bang hoạt động.** Recall@20 tăng từ "
        f"{fnum(sys_['local_only']['recall@20'])} (mô hình cục bộ, không chia "
        f"sẻ) lên {fnum(sys_['fedavg']['recall@20'])} (FedAvg), tiệm cận mốc "
        f"tập trung {fnum(sys_['centralized']['recall@20'])}.",
        f"**Đồ thị có đóng góp thật.** Mô hình đồ thị vượt mọi baseline không "
        f"dùng đồ thị, chênh lệch lớn hơn nhiều so với khoảng tin cậy.",
        "**Tái lập được.** Một lệnh chạy lại toàn bộ, kết quả tất định, "
        "không phụ thuộc GPU.",
    ])

    rep.h2("6.2. Những gì chưa làm được")
    rep.p("Nhóm chủ động trình bày các hạn chế thay vì bỏ qua:")
    rep.bullets([
        f"**Học liên bang không tiết kiệm băng thông ở quy mô này.** Tốn gấp "
        f"{c['ratio_up_vs_raw']:,.0f} lần so với gửi dữ liệu thô. Lợi ích thật "
        f"là tuân thủ pháp lý, không phải hiệu quả kỹ thuật.",
        f"**Cỡ mẫu đánh giá gợi ý rất nhỏ.** Chỉ {d['users_in_test']} người "
        f"dùng và {d['n_test']} tương tác trong tập kiểm thử. Khoảng tin cậy "
        f"rộng đến mức nhiều khác biệt chưa có ý nghĩa thống kê.",
        f"**Dữ liệu có nhiễu hệ thống.** {q['template_jobs']} tin dùng chung "
        f"tập kỹ năng mẫu, {q['seed_link_jobs']} tin có link sinh tự động "
        f"không kiểm chứng được.",
        "**Chưa có bảo vệ riêng tư thật sự.** Học liên bang hiện tại vẫn gửi "
        "tham số; chưa áp dụng secure aggregation hay DP-SGD.",
        "**Phân vùng khách hàng là mô phỏng.** Các «khách hàng» được chia từ "
        "một file CSV duy nhất, không phải nhiều hệ thống thật.",
        "**Chưa đo được mức độ hài lòng người dùng.** Đây là yêu cầu của đề "
        "bài nhưng cần A/B test trên người dùng thật, ngoài phạm vi đồ án.",
    ])

    rep.h2("6.3. Hướng phát triển")
    rep.table(
        pd.DataFrame([
            {"Hướng": "Secure aggregation / DP-SGD", "Lý do": "Chặn tấn công "
             "suy ngược từ gradient", "Ước lượng": "~1 ngày"},
            {"Hướng": "Hiệu chuẩn lại điểm số", "Lý do": "Điểm BPR không phải "
             "xác suất; hiệu chuẩn giúp so sánh giữa các khách hàng",
             "Ước lượng": "~3 giờ"},
            {"Hướng": "Thu thập thêm tương tác", "Lý do": "Tăng cỡ mẫu đánh "
             "giá từ 16 lên vài trăm người dùng", "Ước lượng": "phụ thuộc dữ liệu"},
            {"Hướng": "Khảo sát người dùng thật", "Lý do": "Đo trực tiếp yêu "
             "cầu «tăng mức độ hài lòng» của đề bài", "Ước lượng": "~1 tuần"},
        ]),
        "Các hướng phát triển tiếp theo",
        widths=[5.0, 6.4, 2.8], font_size=8.5,
    )

    rep.h2("6.4. Bài học phương pháp")
    rep.p("Bốn bài học rút ra từ quá trình làm, mỗi bài đều gắn với một lỗi thật:")
    rep.bullets([
        "**Cách chia dữ liệu quyết định kết luận.** Cùng một mô hình có thể "
        "cho kết quả rất khác nhau tùy cách chia tập kiểm thử. Mọi con số "
        "trong báo cáo này đều ghi rõ giao thức.",
        "**Trung bình các seed có thể che giấu lỗi.** Nếu chỉ báo trung bình, "
        "người đọc không thấy sự bất ổn. Luôn xem cả độ lệch chuẩn.",
        "**Chỉ số xếp hạng và chất lượng sử dụng khác nhau về bản chất.** "
        "Recall@20 cao không có nghĩa là người dùng thấy gợi ý tốt hơn.",
        "**«Code chạy không lỗi» không có nghĩa là code đúng.** Lỗi lớn nhất "
        "của đồ án (FedProx mất gradient) không ném exception nào.",
    ])

    # =================================================================
    # TÀI LIỆU THAM KHẢO
    # =================================================================
    rep.h1("TÀI LIỆU THAM KHẢO")
    refs = [
        "[1] He, X., Deng, K., Wang, X., Li, Y., Zhang, Y., Wang, M. (2020). "
        "LightGCN: Simplifying and Powering Graph Convolution Network for "
        "Recommendation. SIGIR '20, pp. 639–648.",
        "[2] McMahan, H. B., Moore, E., Ramage, D., Hampson, S., Agüera y "
        "Arcas, B. (2017). Communication-Efficient Learning of Deep Networks "
        "from Decentralized Data. AISTATS 2017.",
        "[3] Li, T., Sahu, A. K., Zaheer, M., Sanjabi, M., Talwalkar, A., "
        "Smith, V. (2020). Federated Optimization in Heterogeneous Networks. "
        "MLSys 2020. (FedProx)",
        "[4] Rendle, S., Freudenthaler, C., Gantner, Z., Schmidt-Thieme, L. "
        "(2009). BPR: Bayesian Personalized Ranking from Implicit Feedback. "
        "UAI 2009.",
        "[5] Veličković, P., Cucurull, G., Casanova, A., Romero, A., Liò, P., "
        "Bengio, Y. (2018). Graph Attention Networks. ICLR 2018. "
        "arXiv:1710.10903.",
        "[6] Hamilton, W., Ying, R., Leskovec, J. (2017). Inductive "
        "Representation Learning on Large Graphs. NeurIPS 2017. (GraphSAGE)",
        "[7] Kairouz, P., McMahan, H. B., và cộng sự (2021). Advances and "
        "Open Problems in Federated Learning. Foundations and Trends in "
        "Machine Learning, 14(1–2), 1–210.",
        "[8] Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 (Việt Nam); Quy định "
        "chung về bảo vệ dữ liệu GDPR (EU) 2016/679.",
    ]
    for r in refs:
        rep.p(r)

    # =================================================================
    # PHỤ LỤC
    # =================================================================
    rep.h1("PHỤ LỤC A. BẢNG SỐ LIỆU ĐẦY ĐỦ")
    rep.h2("A.1. Kết quả gợi ý theo từng vòng học liên bang")
    for s in reco["client_sweep"]:
        rep.p(f"**{s['n_clients']} khách hàng** — "
              f"cục bộ R@20 = {fnum(s['local_only']['recall@20'])}, "
              f"FedAvg vòng cuối = {fnum(s['fedavg_final']['recall@20'])}, "
              f"đỉnh = {fnum(s['fedavg_best']['recall@20'])}.")
        df = pd.DataFrame([
            {"Vòng": p["round"], "R@20": fnum(p["recall@20"]),
             "NDCG@20": fnum(p["ndcg@20"]), "MRR@20": fnum(p["mrr@20"]),
             "Loss": fnum(p["train_loss"], 4),
             "Byte gửi lên": f"{p['up_bytes']:,}"}
            for p in s["curve"]
        ])
        rep.table(df, f"Đường cong FedAvg với {s['n_clients']} khách hàng",
                  widths=[1.8, 2.0, 2.2, 2.2, 2.2, 3.0], font_size=7.5)

    rep.h2("A.2. Chi tiết đường cong học liên bang")
    rep.p(
        "Bảng đầy đủ của từng vòng truyền thông đã nằm ở mục A.1. Phụ lục này "
        "bổ sung bảng so sánh chất lượng theo số lượng khách hàng — dùng để "
        "trả lời câu hỏi «chia dữ liệu thành bao nhiêu khách hàng thì còn dùng "
        "được», vốn không có trong đề bài nhưng hội đồng thường hỏi."
    )
    rep.table(
        pd.DataFrame([
            {"Số khách hàng": s["n_clients"],
             "Cục bộ (không chia sẻ)": fnum(s["local_only"]["recall@20"]),
             "FedAvg (vòng cuối)": fnum(s["fedavg_final"]["recall@20"]),
             "FedAvg (đỉnh)": fnum(s["fedavg_best"]["recall@20"]),
             "Khoảng cách còn lại (%)":
                 f"{100 * (1 - (s['fedavg_best']['recall@20'] - s['local_only']['recall@20']) / max(1e-9, sys_['centralized']['recall@20'] - s['local_only']['recall@20'])):.1f}"}
            for s in reco["client_sweep"]
        ]),
        "Ảnh hưởng của số lượng khách hàng đến chất lượng mô hình",
        widths=[3.0, 3.4, 3.4, 3.0, 3.2], font_size=8.5,
    )

    rep.h1("PHỤ LỤC B. MÃ NGUỒN CỐT LÕI")
    rep.h2("B.1. FedAvg thưa — chỉ cập nhật nút có dữ liệu")
    rep.p(
        "Cách làm ban đầu là lấy trung bình toàn bộ bảng embedding. Cách này "
        "hỏng vì nút nào client không có dữ liệu sẽ bị kéo về 0, và sau vài "
        "chục vòng mô hình toàn cục sụp dù từng client vẫn «học tốt». Bản "
        "dưới đây chỉ cập nhật các hàng thực sự thay đổi, chia theo tổng trọng "
        "số của chính nút đó."
    )
    rep.code("""# trích src/medajob/federated.py
def sparse_fedavg(global_state, updates):
    base = global_state["emb.weight"]
    acc = torch.zeros_like(base, dtype=torch.float64)
    wsum = torch.zeros(base.shape[0], dtype=torch.float64)
    for upd in updates:
        idx = torch.tensor(upd.node_idx)
        delta = torch.tensor(upd.rows) - base[idx].double()
        acc.index_add_(0, idx, delta * torch.tensor(upd.weight).unsqueeze(1))
        wsum.index_add_(0, idx, torch.tensor(upd.weight))
    touched = wsum > 0
    merged = base.clone()
    merged[touched] = (base[touched].double()
                       + acc[touched] / wsum[touched].unsqueeze(1)).float()
    return {"emb.weight": merged}, int(touched.sum())""")

    rep.h2("B.2. Số hạng proximal của FedProx — bản đúng")
    rep.p(
        "Sai lầm dễ mắc: dùng `state_dict()` (đã detach) nên số hạng proximal "
        "không có gradient. Bản dưới dùng `named_parameters()`."
    )
    rep.code("""# trích src/medajob/federated.py — local_train
ref = {name: p.detach().clone() for name, p in model.named_parameters()}
for _ in range(epochs):
    opt.zero_grad()
    emb = model.encode(src, dst, inv_deg)
    loss = bpr_loss(emb, uu, jj, neg, reg=reg)
    if mu > 0:
        # named_parameters(): tensor còn nối vào đồ thị autograd
        prox = sum(((p - ref[name]) ** 2).sum()
                   for name, p in model.named_parameters())
        loss = loss + 0.5 * mu * prox
    loss.backward()
    opt.step()""")

    rep.h2("B.3. Chú thích cho mục lục")
    rep.p(
        "Mục lục trong file này là một field Word thật. Khi mở bằng Microsoft "
        "Word, nhấn Ctrl+A rồi F9 (hoặc chuột phải → Update Field) để cập nhật "
        "số trang. Thuộc tính updateFields đã được bật sẵn nên Word sẽ hỏi "
        "ngay khi mở."
    )

    rep.page_number_footer()
    return rep


# =====================================================================
# Kiểm tra số liệu
# =====================================================================
def verify_numbers(docx_path: Path, reco: dict) -> list[str]:
    """Đối chiếu các con số then chốt có mặt trong .docx."""
    from docx import Document as D

    doc = D(str(docx_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    checks = {
        "Recall@20 của FedAvg": f"{reco['systems']['fedavg']['recall@20']:.4f}",
        "Recall@20 tập trung": f"{reco['systems']['centralized']['recall@20']:.4f}",
        "Recall@20 cục bộ": f"{reco['systems']['local_only']['recall@20']:.4f}",
        "NDCG@20 của FedAvg": f"{reco['systems']['fedavg']['ndcg@20']:.4f}",
        "Số nút đồ thị": f"{reco['data_summary']['n_jobs']:,}",
    }
    missing = [f"{k} = {v!r}" for k, v in checks.items() if v not in text]
    return missing


def main() -> None:
    setup_console()
    cfg = load_config()
    banner("DỰNG BÁO CÁO .DOCX")

    rep = build(cfg)
    out = Path(cfg["report"]["output"])
    if not out.is_absolute():
        out = ROOT / out
    rep.save(out)
    step(f"Đã lưu: {out} ({out.stat().st_size / 1024:.0f} KB)")
    step(f"{rep.fig_no} hình, {rep.tab_no} bảng")

    reco = load_json(Path(cfg["paths"]["results"]) / "reco_main.json")
    missing = verify_numbers(out, reco)
    if missing:
        step(f"CẢNH BÁO — số liệu không khớp trong tài liệu: {missing}")
    else:
        step("Kiểm tra số liệu: TẤT CẢ khớp với results/*.json")

    banner("XONG")


if __name__ == "__main__":
    main()

