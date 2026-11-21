# Kịch bản demo — 6 phút

Tài liệu này là lời dẫn cụ thể khi bảo vệ: bấm vào đâu, nói câu gì, trong bao
lâu. Mục tiêu là để người xem hiểu **vấn đề → cách làm → kết quả → hạn chế**
mà không cần đọc báo cáo trước.

---

## Chuẩn bị trước 5 phút

**Bật demo:**

```powershell
cd E:\2026\DUT\DSS\SauGK\CuoiKi
$env:MPLCONFIGDIR = "$PWD\artifacts\.mplcache"
python -m streamlit run app/streamlit_app.py --server.headless=true
```

Mở trình duyệt ở địa chỉ Streamlit in ra (thường `http://localhost:8501`).

**Mở sẵn 2 tab:**

1. Tab 1: app Streamlit (trang Tổng quan).
2. Tab 2: `docs/BAO_CAO_GNN_FL.docx` — để sẵn ở phần Kết luận, phòng khi
   hội đồng hỏi chi tiết.

**Kiểm tra nhanh:** bấm qua cả 6 trang một lượt để chắc không trang nào lỗi
(mất ~30 giây).

> **Về giao diện:** app dùng theme sáng (nền trắng, xanh chủ đạo) khớp với
> 9 hình trong báo cáo. Có hiệu ứng động: thẻ số liệu trượt lên, biểu đồ
> hiện dần, và trang Mô phỏng liên bang có công tắc "▶ Tự chạy".
> Nếu máy chiếu bị nhấp nháy, bật "giảm chuyển động" trong Windows
> (Settings → Accessibility → Visual effects) — app tự tắt animation.

---

## Phút 0–1 · Đặt vấn đề (trang **Tổng quan**)

**Bấm:** trang Tổng quan (mặc định).

**Nói:**

> "Bài toán gợi ý việc làm thường được làm trên một máy chủ duy nhất: gom
> toàn bộ tin tuyển dụng và hồ sơ ứng viên về một chỗ rồi huấn luyện.
>
> Nhưng thực tế dữ liệu đó thuộc về nhiều nền tảng và doanh nghiệp khác nhau.
> Gom hồ sơ cá nhân về một chỗ là vi phạm Luật Bảo vệ Dữ liệu Cá nhân và GDPR.
>
> Cách giải của chúng em là kết hợp hai thứ: **đồ thị** để tận dụng quan hệ
> giữa người dùng, tin, kỹ năng, ngành; và **học liên bang** để mô hình học
> mà dữ liệu gốc không rời khỏi nơi lưu trữ."

**Chỉ vào 4 thẻ số liệu:**

> "Bốn con số: Recall@20 của mô hình liên bang là 0,497; mốc tập trung là
> 0,504; học liên bang lấy lại được 93% khoảng cách; và **0 dòng dữ liệu thô**
> rời khỏi khách hàng."

**Chỉ vào khối màu vàng:**

> "Nhưng em muốn nói ngay hai điểm chưa đạt: học liên bang ở quy mô này tốn
> băng thông gấp hơn sáu nghìn lần, và tập kiểm thử chỉ có 16 ứng viên nên
> khoảng tin cậy rất rộng. Trang cuối sẽ nói kỹ."

> **Mẹo:** nói hạn chế ngay từ đầu khiến hội đồng tin phần còn lại hơn.

---

## Phút 1–2.5 · Ranh giới dữ liệu (trang **Đồ thị việc làm**)

**Bấm:** Đồ thị việc làm.

**Nói:**

> "Đây là toàn bộ đồ thị dữ liệu: 1.014 tin tuyển dụng, 70 ứng viên, 603 kỹ
> năng và 10 ngành."

**Bấm: tắt công tắc "Hiện cạnh riêng tư".**

> "Mọi cạnh đỏ vừa biến mất. Đó chính xác là phần mà **máy chủ trung tâm được
> phép thấy**: chỉ cấu trúc công khai giữa tin tuyển dụng với kỹ năng và ngành.
> Toàn bộ 7.208 cạnh còn lại — ai biết kỹ năng gì, ai thích tin nào — chỉ tồn
> tại bên trong khách hàng."

**Bấm: bật lại công tắc.**

> "Đây là điểm khác biệt so với mô hình tập trung thông thường: máy chủ không
> bao giờ giữ hồ sơ cá nhân nào."

**Bật công tắc 2D/3D** (nếu máy chiếu đủ mạnh):

> "Chế độ 3D dùng cùng dữ liệu, chỉ khác cách bố cục — bật tắt không làm mất
> nút hay cạnh nào."

---

## Phút 2.5–4 · Học liên bang hoạt động (trang **Mô phỏng liên bang**)

**Bấm:** Mô phỏng liên bang.

**Nói:**

> "Mỗi khách hàng tự huấn luyện trên dữ liệu riêng, gửi tham số lên, máy chủ
> lấy trung bình có trọng số."

**Bật "▶ Tự chạy"** (hoặc kéo thanh "Xem đến vòng" từ 1 lên 20, chậm).

> "Các em thấy Recall@20 tăng dần. Nhưng chú ý: nó **dao động**, không đơn
> điệu. Đó là hiện tượng thật của học liên bang khi dữ liệu các khách hàng
> khác nhau, không phải lỗi."

**Chỉ vào 4 thẻ số liệu:**

> "Cục bộ 0,402 — Liên bang 0,497 — Tập trung 0,504. Nói cách khác, học liên
> bang **lấy lại 93% khoảng cách** mà việc chia nhỏ dữ liệu đã làm mất, mà
> không gửi một dòng dữ liệu nào."

**Cuộn xuống khối "Chi phí truyền thông":**

> "Đây là phần ít ai báo cáo. Ở quy mô dữ liệu này, gửi tham số tốn gấp **6.565
> lần** băng thông so với gửi thẳng dữ liệu thô. Vì payload là số nút nhân số
> chiều, không phụ thuộc số tương tác.
>
> Nên lợi ích của học liên bang ở đây **không phải băng thông** — mà là dữ
> liệu không rời chỗ. Với bài toán tuân thủ pháp lý thì đó mới là điểm quyết
> định."

> **Mẹo:** tự nêu điểm yếu trước khi bị hỏi. Hội đồng sẽ hỏi đúng chỗ này nếu
> mình không nói.

---

## Phút 4–5 · Vì sao tin này được gợi ý (trang **Gợi ý cho ứng viên**)

**Bấm:** Gợi ý cho ứng viên.

**Chọn một ứng viên** trong dropdown (ví dụ ứng viên đầu tiên).

**Nói:**

> "Đây là hồ sơ thật: ứng viên có các kỹ năng này."

**Chỉ vào bảng, cột cuối "kỹ năng khớp":**

> "Cột này là phần quan trọng nhất: nó nói **vì sao** tin này được đề xuất. Em
> không muốn mô hình là hộp đen — người xem phải thấy được lý do."

**Bấm qua tab "Phổ biến":**

> "So sánh với cách xếp theo độ phổ biến: mọi ứng viên nhận cùng một danh sách.
> Đó là lý do cần mô hình cá nhân hoá."

**Cuộn xuống bảng chất lượng, chỉ vào cột CI:**

> "Khoảng tin cậy 95% rất rộng vì tập kiểm thử chỉ có 16 ứng viên. Em ghi rõ
> điều này: chênh lệch vài phần trăm giữa các phương pháp **chưa** đủ kết luận.
> Con số đáng tin là thứ hạng tương đối — mô hình đồ thị vượt hẳn baseline."

---

## Phút 5–6 · Kết luận (trang **Kết luận & hạn chế**)

**Bấm:** Kết luận & hạn chế.

**Chỉ vào bảng đối chiếu yêu cầu:**

> "Bảng này đối chiếu từng yêu cầu đề bài với số đo thật. Năm trên sáu yêu cầu
> đạt. Riêng 'tăng mức độ hài lòng người dùng' thì **chưa** — cái đó cần A/B
> test trên người dùng thật, ngoài phạm vi đồ án. Em không tuyên bố đạt."

**Cuộn xuống mục "Điều CHƯA làm được":**

> "Và đây là những gì chưa làm được, em liệt kê đầy đủ: học liên bang không
> tiết kiệm băng thông, cỡ mẫu đánh giá rất nhỏ, chưa đo được mức hài lòng
> người dùng, và chưa có bảo vệ riêng tư thật sự — vẫn gửi tham số nên vẫn có
> thể bị suy ngược từ gradient."

**Cuộn xuống "Bài học phương pháp":**

> "Bài học lớn nhất: lỗi nguy hiểm nhất trong quá trình làm là **FedProx mất
> gradient** — số hạng proximal tính trên `state_dict()` đã detach, nên FedProx
> trở thành FedAvg trần. Lỗi này không ném exception nào, chỉ lộ ra khi thấy
> μ = 5 cho kết quả trùng khít μ = 0."

**Kết:**

> "Tất cả số liệu này tái lập được bằng một lệnh, có regression test riêng cho
> từng lỗi em vừa nêu, và báo cáo chi tiết ở file .docx."

---

## Câu hỏi thường gặp — trả lời sẵn

| Câu hỏi | Trả lời |
|---|---|
| "Sao không dùng PyTorch Geometric?" | "Môi trường phát triển chặn cài gói mới. Em tự viết lan truyền bằng `index_add_` và `scatter_reduce`. Hóa ra có lợi: buộc phải chỉ rõ chính xác cái gì được gửi lên server trong học liên bang." |
| "Sao không dùng MovieLens cho nhiều dữ liệu?" | "MovieLens không có thuộc tính kỹ năng của tin và không có cột đơn vị tuyển dụng. Dùng nó thì phải bịa một trong hai thứ đó, làm mất ý nghĩa của cả đồ thị lẫn cách chia khách hàng." |
| "FedAvg kém hơn tập trung, vậy có ý nghĩa gì?" | "Đúng, kém 0,007. Nhưng mô hình tập trung **không triển khai được** vì phải gom hồ sơ cá nhân. Câu hỏi đúng là: liên bang có lấy lại được phần lớn khoảng cách không? Câu trả lời là 93%." |
| "16 ứng viên thì kết luận được gì?" | "Chỉ kết luận được thứ hạng tương đối, không kết luận được chênh lệch nhỏ. Em có báo cáo CI 95% và ghi rõ hạn chế này ở cả báo cáo lẫn app." |
| "Học liên bang có thật sự bảo mật?" | "Chưa hoàn toàn. Server vẫn thấy tham số, và có tấn công suy ngược từ gradient. Cần secure aggregation hoặc DP-SGD — em ghi ở mục hướng phát triển." |
| "Sao không có slide?" | "Em ưu tiên bản demo chạy được và báo cáo đầy đủ. Kịch bản trình bày 6 phút ở `docs/KICH_BAN_DEMO.md` chính là nội dung slide." |

---

## Phương án dự phòng

**Nếu app không lên:**

1. Kiểm tra đã set `MPLCONFIGDIR` chưa.
2. Chạy lại với cổng khác: `--server.port=8502`.
3. **Dự phòng cuối:** mở `docs/BAO_CAO_GNN_FL.docx` — toàn bộ hình và bảng
   nằm trong đó, trình bày trực tiếp từ Word.

**Nếu bị hỏi số liệu mà không nhớ:** mọi con số đều ở trang
**Kết luận & hạn chế**, trong `docs/SO_LIEU_CHINH.md`, và trong
`results/reco_main.json`.
