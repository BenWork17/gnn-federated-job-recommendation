# Quy ước thuật ngữ

Mục đích: **không dịch những từ đã là thuật ngữ chuyên ngành**. Dịch chúng ra
tiếng Việt làm người đọc chuyên môn khó đối chiếu với tài liệu, và làm báo cáo
trông thiếu chuyên nghiệp.

Quy tắc một dòng: **thuật ngữ giữ nguyên tiếng Anh; phần diễn giải viết tiếng
Việt.**

---

## 1. Giữ nguyên — KHÔNG dịch

| Dùng | Không dùng |
|---|---|
| **Federated Learning** (FL) | học liên bang, học phối hợp |
| **Federated Learning simulation** | mô phỏng liên bang, mô phỏng học liên bang |
| **GNN** (Graph Neural Network) | mạng nơ-ron đồ thị, đồ thị nơ-ron |
| **GraphSAGE** | — (tên kiến trúc, luôn giữ) |
| **LightGCN** | — |
| **FedAvg** / **FedProx** | trung bình liên bang |
| **Embedding** | nhúng, vector nhúng |
| **Attention** | cơ chế chú ý |
| **cold-start** | khởi đầu lạnh |
| **TF-IDF**, **cosine** | — |
| **Recall@K**, **NDCG@K**, **MRR@K** | độ phủ, độ hồi tưởng |
| **FPR**, **AUC**, **F1** | — |
| **baseline** | đường cơ sở, mốc so sánh |
| **epoch**, **seed**, **payload** | vòng huấn luyện, hạt giống, tải trọng |
| **node / edge** (trong ngữ cảnh đồ thị kỹ thuật) | đỉnh / cạnh¹ |
| **Dataset**, **log**, **label** | bộ dữ liệu², nhật ký, nhãn |

¹ Trong văn xuôi giải thích cho người ngoài, "nút" và "cạnh" vẫn dùng được —
miễn là lần đầu có nêu thuật ngữ tiếng Anh.
² "Bộ dữ liệu" chấp nhận được ở câu diễn giải, nhưng tên riêng (MEDAJob) thì
không dịch.

## 2. Dịch bình thường — đây không phải thuật ngữ

| Tiếng Anh | Tiếng Việt |
|---|---|
| privacy | riêng tư |
| accuracy | độ chính xác |
| embedding (khi nói về bảng tham số) | nhúng |
| bandwidth | băng thông |
| overfitting | quá khớp |
| sparse / sparsity | thưa / độ thưa |

## 3. Quy ước trình bày

- Lần xuất hiện **đầu tiên** trong một trang/tài liệu: viết đầy đủ
  `Federated Learning (FL)`, sau đó dùng `FL`.
- Tên trang trong sidebar **có thể** dùng tiếng Việt cho thân thiện
  (*Mô phỏng Federated Learning*), nhưng tiêu đề nội dung và bảng phải theo
  quy ước trên.
- Không viết hoa giữa câu: "học **F**ederated Learning" là sai.

---

## 4. Đã áp dụng ở đâu

Sửa trong `app/streamlit_app.py`, `app/views/*.py`, `app/screenshot_app.py`,
`app/_check_theme.py` — thay toàn bộ "học liên bang" → "Federated Learning" và
"mô phỏng liên bang" → "Federated Learning simulation".

Nếu thêm trang mới, đối chiếu bảng ở mục 1 trước khi viết tiếng Việt.
