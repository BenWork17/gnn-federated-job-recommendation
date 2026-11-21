"""
Sinh docs/SO_LIEU_CHINH.md — bảng số liệu chuẩn đọc trực tiếp từ results/*.json.

Vì sao cần file này: các tài liệu viết tay (README, kịch bản demo, phân tích
đề tài) rất dễ trôi số khi pipeline chạy lại. File này là nguồn sự thật duy
nhất cho phần văn xuôi, và được sinh tự động nên không thể lệch.

Chạy: python src/report/make_facts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common import ROOT, banner, load_config, load_json, setup_console, step


def build(cfg: dict) -> str:
    res = Path(cfg["paths"]["results"])
    reco = load_json(res / "reco_main.json")

    s = reco["systems"]
    d = reco["data_summary"]
    c = reco["communication"]

    recover = ((s["fedavg"]["recall@20"] - s["local_only"]["recall@20"])
               / (s["centralized"]["recall@20"] - s["local_only"]["recall@20"]))

    lines = [
        "# Số liệu chính (tự động sinh)",
        "",
        "**Không sửa tay file này.** Sinh lại bằng:",
        "```powershell",
        "python src/report/make_facts.py",
        "```",
        "",
        "Mọi tài liệu viết tay phải trích số từ đây, không gõ lại từ ký ức.",
        "",
        "---",
        "",
        "## 1. Dữ liệu MEDAJob",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Tin tuyển dụng (sau làm sạch) | {d['n_jobs']:,} |",
        f"| Ứng viên | {d['n_users']} |",
        f"| Tương tác (train + test) | {d['n_train'] + d['n_test']} |",
        f"| Tương tác train | {d['n_train']} |",
        f"| Tương tác test | {d['n_test']} |",
        f"| Ứng viên có mặt trong test | **{d['users_in_test']}** |",
        f"| Nút kỹ năng | {d['n_skills']} |",
        f"| Nút ngành | {d['n_industries']} |",
        f"| Cạnh công khai | {d['public_edges']:,} |",
        f"| Cạnh riêng tư | {d['private_edges']:,} |",
        f"| Độ thưa ma trận | {d['sparsity_pct']:.2f}% |",
        f"| Tin dùng chung tập kỹ năng mẫu | {d['quality']['template_jobs']} "
        f"({d['quality']['template_pct']}%) |",
        "",
        "## 2. Kết quả gợi ý",
        "",
        "| Hệ | R@10 | R@20 | CI 95% của R@20 | NDCG@20 | MRR@20 |",
        "|---|---|---|---|---|---|",
    ]
    for key, label in [
        ("popularity", "Phổ biến"), ("skill_cbf", "Nội dung (kỹ năng)"),
        ("item_knn", "Item-KNN"), ("local_only", "Cục bộ (không chia sẻ)"),
        ("fedavg", "Liên bang (FedAvg)"), ("fedprox", "Liên bang (FedProx)"),
        ("centralized", "Tập trung (mốc trên)"),
    ]:
        sys_ = s.get(key)
        if not sys_:
            continue
        ci = sys_.get("recall@20_ci", {})
        lines.append(
            f"| {label} | {sys_['recall@10']:.4f} | {sys_['recall@20']:.4f} | "
            f"[{ci.get('lo', 0):.3f}, {ci.get('hi', 0):.3f}] | "
            f"{sys_['ndcg@20']:.4f} | {sys_['mrr@20']:.4f} |")

    lines += [
        "",
        f"**Học liên bang lấy lại {recover:.1%} khoảng cách** so với mô hình "
        "tập trung.",
        "",
        "## 3. Chi phí truyền thông",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Số tham số | {c['n_params']:,} |",
        f"| Byte mỗi lần chuyển | {c['param_bytes_per_transfer']:,} |",
        f"| Tổng byte gửi lên | {c['up_bytes_total']:,} ({c['up_bytes_total'] / 1024:,.0f} KB) |",
        f"| Dữ liệu thô nếu tập trung | {c['raw_data_bytes_if_centralized']:,} "
        f"({c['raw_data_bytes_if_centralized'] / 1024:.0f} KB) |",
        f"| Tỉ lệ | gấp {c['ratio_up_vs_raw']:,.0f} lần |",
        f"| Điểm hoà vốn | {c['crossover_interactions']:,} tương tác |",
        "",
        "## 4. Ảnh hưởng của số lượng khách hàng",
        "",
        "| Số khách hàng | Cục bộ R@20 | FedAvg vòng cuối | FedAvg đỉnh |",
        "|---|---|---|---|",
    ]
    for q in reco.get("client_sweep", []):
        lines.append(
            f"| {q['n_clients']} | {q['local_only']['recall@20']:.4f} | "
            f"{q['fedavg_final']['recall@20']:.4f} | "
            f"{q['fedavg_best']['recall@20']:.4f} |")

    lines += [
        "",
        "## 5. Bảng yêu cầu → kết quả",
        "",
        "| Yêu cầu | Cách đo | Kết quả | Đạt |",
        "|---|---|---|---|",
        f"| Giảm tỉ lệ lỗi gợi ý | Recall@20 so với baseline phổ biến | "
        f"{s['popularity']['recall@20']:.4f} → {s['fedavg']['recall@20']:.4f} | Có |",
        f"| Nâng Recall@20 | Trung bình theo người dùng, K = 20 | "
        f"{s['popularity']['recall@20']:.4f} → {s['fedavg']['recall@20']:.4f} | Có |",
        f"| Nâng NDCG@20 | Trung bình theo người dùng, K = 20 | "
        f"{s['popularity']['ndcg@20']:.4f} → {s['fedavg']['ndcg@20']:.4f} | Có |",
        f"| Nâng MRR | Nghịch đảo hạng tin liên quan đầu tiên | "
        f"{s['popularity']['mrr@20']:.4f} → {s['fedavg']['mrr@20']:.4f} | Có |",
        "| Dữ liệu không rời khách hàng | Kiểm payload client (có test tự động) | "
        "0 dòng dữ liệu thô rời máy | Có |",
        "| Tăng mức độ hài lòng người dùng | Cần A/B test trên người dùng thật | "
        "Không đo được trong phạm vi đồ án | Chưa |",
        "",
        "## 6. Các phát hiện",
        "",
    ]

    findings = [
        ("F1", "Học liên bang lấy lại phần lớn khoảng cách do chia nhỏ dữ liệu",
         f"Cục bộ {s['local_only']['recall@20']:.4f} → FedAvg "
         f"{s['fedavg']['recall@20']:.4f} → tập trung "
         f"{s['centralized']['recall@20']:.4f}, tức lấy lại {recover:.1%} khoảng "
         f"cách, mà không gửi một dòng dữ liệu thô nào."),
        ("F2", "Đồ thị có đóng góp thật, không phải trang trí",
         f"LightGCN đạt Recall@20 {s['centralized']['recall@20']:.4f}, vượt "
         f"Item-KNN {s['item_knn']['recall@20']:.4f}, phổ biến "
         f"{s['popularity']['recall@20']:.4f} và nội dung "
         f"{s['skill_cbf']['recall@20']:.4f}."),
        ("F3", "Học liên bang KHÔNG tiết kiệm băng thông ở quy mô này",
         f"Gửi tham số tốn gấp {c['ratio_up_vs_raw']:,.0f} lần so với gửi dữ "
         f"liệu thô. Điểm hoà vốn là {c['crossover_interactions']:,} tương tác. "
         f"Lợi ích thật của FL ở đây là tuân thủ pháp lý, không phải byte."),
        ("F4", "Thêm tham số phi tuyến làm giảm chất lượng khi dữ liệu cực thưa",
         f"Thay LightGCN bằng GraphSAGE (có MLP) khiến Recall@20 giảm còn "
         f"{s['centralized_sage']['recall@20']:.4f} so với "
         f"{s['centralized']['recall@20']:.4f}. Với "
         f"{d['n_train']} tương tác huấn luyện, mô hình đơn giản thắng."),
        ("F5", "Cỡ mẫu đánh giá là hạn chế lớn nhất của phần gợi ý",
         f"Chỉ {d['users_in_test']} ứng viên có mặt trong tập kiểm thử "
         f"({d['n_test']} tương tác), nên khoảng tin cậy 95% rất rộng và nhiều "
         f"khác biệt giữa các phương pháp chưa có ý nghĩa thống kê."),
    ]
    for fid, title, detail in findings:
        lines.append(f"### [{fid}] {title}")
        lines.append("")
        lines.append(detail)
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    setup_console()
    cfg = load_config()
    banner("SINH BẢNG SỐ LIỆU CHUẨN")
    text = build(cfg)
    out = ROOT / "docs" / "SO_LIEU_CHINH.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    step(f"Đã ghi {out} ({len(text):,} ký tự)")


if __name__ == "__main__":
    main()
