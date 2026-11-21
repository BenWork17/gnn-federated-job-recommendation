# Số liệu chính (tự động sinh)

**Không sửa tay file này.** Sinh lại bằng:
```powershell
python src/report/make_facts.py
```

Mọi tài liệu viết tay phải trích số từ đây, không gõ lại từ ký ức.

---

## 1. Dữ liệu MEDAJob

| Chỉ số | Giá trị |
|---|---|
| Tin tuyển dụng (sau làm sạch) | 1,014 |
| Ứng viên | 70 |
| Tương tác (train + test) | 307 |
| Tương tác train | 249 |
| Tương tác test | 58 |
| Ứng viên có mặt trong test | **16** |
| Nút kỹ năng | 603 |
| Nút ngành | 10 |
| Cạnh công khai | 6,002 |
| Cạnh riêng tư | 7,208 |
| Độ thưa ma trận | 0.43% |
| Tin dùng chung tập kỹ năng mẫu | 682 (67.3%) |

## 2. Kết quả gợi ý

| Hệ | R@10 | R@20 | CI 95% của R@20 | NDCG@20 | MRR@20 |
|---|---|---|---|---|---|
| Phổ biến | 0.1719 | 0.2448 | [0.115, 0.401] | 0.1363 | 0.1372 |
| Nội dung (kỹ năng) | 0.0781 | 0.1094 | [0.000, 0.250] | 0.0584 | 0.0773 |
| Item-KNN | 0.1979 | 0.3490 | [0.177, 0.526] | 0.1790 | 0.1385 |
| Cục bộ (không chia sẻ) | 0.3271 | 0.4021 | [0.250, 0.562] | 0.3103 | 0.3804 |
| Liên bang (FedAvg) | 0.2917 | 0.4969 | [0.334, 0.655] | 0.2734 | 0.2830 |
| Liên bang (FedProx) | 0.3229 | 0.4479 | [0.271, 0.625] | 0.3118 | 0.3715 |
| Tập trung (mốc trên) | 0.3281 | 0.5042 | [0.356, 0.661] | 0.2920 | 0.2904 |

**Học liên bang lấy lại 92.9% khoảng cách** so với mô hình tập trung.

## 3. Chi phí truyền thông

| Chỉ số | Giá trị |
|---|---|
| Số tham số | 54,304 |
| Byte mỗi lần chuyển | 217,216 |
| Tổng byte gửi lên | 19,617,500 (19,158 KB) |
| Dữ liệu thô nếu tập trung | 2,988 (3 KB) |
| Tỉ lệ | gấp 6,565 lần |
| Điểm hoà vốn | 1,634,792 tương tác |

## 4. Ảnh hưởng của số lượng khách hàng

| Số khách hàng | Cục bộ R@20 | FedAvg vòng cuối | FedAvg đỉnh |
|---|---|---|---|
| 5 | 0.4021 | 0.4969 | 0.4990 |
| 8 | 0.4198 | 0.5031 | 0.5448 |
| 12 | 0.2115 | 0.4333 | 0.4333 |

## 5. Bảng yêu cầu → kết quả

| Yêu cầu | Cách đo | Kết quả | Đạt |
|---|---|---|---|
| Giảm tỉ lệ lỗi gợi ý | Recall@20 so với baseline phổ biến | 0.2448 → 0.4969 | Có |
| Nâng Recall@20 | Trung bình theo người dùng, K = 20 | 0.2448 → 0.4969 | Có |
| Nâng NDCG@20 | Trung bình theo người dùng, K = 20 | 0.1363 → 0.2734 | Có |
| Nâng MRR | Nghịch đảo hạng tin liên quan đầu tiên | 0.1372 → 0.2830 | Có |
| Dữ liệu không rời khách hàng | Kiểm payload client (có test tự động) | 0 dòng dữ liệu thô rời máy | Có |
| Tăng mức độ hài lòng người dùng | Cần A/B test trên người dùng thật | Không đo được trong phạm vi đồ án | Chưa |

## 6. Các phát hiện

### [F1] Học liên bang lấy lại phần lớn khoảng cách do chia nhỏ dữ liệu

Cục bộ 0.4021 → FedAvg 0.4969 → tập trung 0.5042, tức lấy lại 92.9% khoảng cách, mà không gửi một dòng dữ liệu thô nào.

### [F2] Đồ thị có đóng góp thật, không phải trang trí

LightGCN đạt Recall@20 0.5042, vượt Item-KNN 0.3490, phổ biến 0.2448 và nội dung 0.1094.

### [F3] Học liên bang KHÔNG tiết kiệm băng thông ở quy mô này

Gửi tham số tốn gấp 6,565 lần so với gửi dữ liệu thô. Điểm hoà vốn là 1,634,792 tương tác. Lợi ích thật của FL ở đây là tuân thủ pháp lý, không phải byte.

### [F4] Thêm tham số phi tuyến làm giảm chất lượng khi dữ liệu cực thưa

Thay LightGCN bằng GraphSAGE (có MLP) khiến Recall@20 giảm còn 0.2135 so với 0.5042. Với 249 tương tác huấn luyện, mô hình đơn giản thắng.

### [F5] Cỡ mẫu đánh giá là hạn chế lớn nhất của phần gợi ý

Chỉ 16 ứng viên có mặt trong tập kiểm thử (58 tương tác), nên khoảng tin cậy 95% rất rộng và nhiều khác biệt giữa các phương pháp chưa có ý nghĩa thống kê.
