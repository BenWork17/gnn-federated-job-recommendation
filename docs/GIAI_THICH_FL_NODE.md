# Giải thích FL node — đọc là hiểu, bảo vệ được

Tài liệu này để trả lời đúng một câu: **một node Federated Learning (FL) làm gì, và
cái gì rời khỏi máy nó?** Mọi con số đều lấy từ artifacts/hoặc log đo thật; chỗ nào
chưa đo được thì ghi rõ "chưa xác minh".

Nguồn số: `artifacts/v3/meta.json`, `artifacts/v3/clients.json`,
`ui/last_real_backend_pg.json`, `results/reco_main.json`, `docs/SO_LIEU_CHINH.md`.

---

## 1. Một node là gì

Mỗi node = **một nhà tuyển dụng** (employer). Dữ liệu của node là những đơn ứng
tuyển vào tin tuyển dụng **của chính nhà đó**: mã ứng viên, mã tin, mã đơn, thời
điểm ứng tuyển. Ví dụ node `randstad`: **4.745 application**, của **4.215 ứng
viên**, vào **603 tin**. Đó là toàn bộ thứ node này nhìn thấy. Toàn hệ có **9.116
node** như vậy, phủ **436.893** cặp (user, job) trên tổng **1.603.111** application
gốc của bộ CareerBuilder 2012.

Node `randstad` **không biết** ứng viên X có ứng tuyển ở `spherion` hay không. Nó
không có quyền đọc, không giữ bản sao, và cũng không được hỏi server. Server trung
tâm cũng không giữ hồ sơ nào. Vì thế node không phải "một mảnh của bảng dữ liệu
lớn" — nó là **một silo độc lập**, chỉ chia sẻ đúng một thứ: bảng embedding sau khi
tự học.

---

## 2. Một vòng FL chạy ra sao (5 bước)

**Bước 1 — Server gửi mô hình xuống.** Server gửi bảng embedding hiện tại cho N node
được chọn trong vòng đó. Kích thước cố định, không phụ thuộc số ứng viên của node.
Ở bản API, mỗi lần gửi là **24.000 tham số × 4 byte ≈ 96 KB**.

**Bước 2 — Node tự học trên dữ liệu của mình.** Node chạy vài bước SGD (vài epoch)
trên đồ thị cục bộ của nó. Tính toán xảy ra **trên máy node**. Dữ liệu không đi đâu
cả. Xong bước này node đã có một bảng embedding *riêng*, hơi khác bảng nhận được.

**Bước 3 — Node gửi LÊN phần đã thay đổi.** Chỉ những **hàng embedding thực sự bị
sửa** được gửi, kèm trọng số = số tương tác của nút đó. Không gửi user_id, job_id,
danh sách đơn, hay bất kỳ bản ghi thô nào. Đây là sparse FedAvg — gửi cả bảng
(như FedAvg trần) sẽ làm nút không có dữ liệu bị kéo về 0 và mô hình sụp sau vài
chục vòng.

**Bước 4 — Server cộng có trọng số (FedAvg).** Server cộng các delta, chia cho tổng
trọng số **của từng nút** (không chia tổng toàn cục). Nút không ai chạm tới giữ
nguyên giá trị cũ.

**Bước 5 — Server gửi mô hình mới xuống, sang vòng sau.** Lặp lại đến hết số vòng
(20 vòng ở cấu hình chính). Recall@20 đi từ 0,402 (chỉ học cục bộ) lên **0,497**
(FedAvg), mốc tập trung là 0,504 — tức lấy lại **93%** khoảng cách.

> Trung thực về bản demo: trong console, **latency là đo thật**
> (`time.perf_counter()` cho từng node mỗi vòng), còn **metric (Recall@20, loss) là
> mô phỏng** — response API ghi rõ `simulated_metrics: true`. Đừng nói "biểu đồ
> Recall trên console là kết quả huấn luyện thật".

---

## 3. Vì sao dữ liệu không rời máy

**Ở lại máy node — không bao giờ gửi:**
`user_id` · `job_id` · cặp (user, job) đã ứng tuyển · `ApplicationDate` · toàn bộ
hồ sơ ứng viên (city, degree, major, years experience…) · số đơn của từng ứng viên.

**Đi lên server — chỉ số thực:**
chỉ số hàng (`node_idx`, int64), vector embedding của hàng đó (`float32`),
trọng số (số tương tác của nút). Không có trường nào chứa định danh người.

**Số byte đo được** (log thật `ui/last_real_backend_pg.json`, run 12 vòng):

| Hạng mục | Giá trị đo |
|---|---|
| Mỗi node gửi lên | 12,5–15,5 KB/vòng |
| Mỗi node nhận xuống | 92,0–95,6 KB/vòng |
| Một vòng, 10 node | ~12,5 KB × 10 lên · ~95 KB × 10 xuống |
| Cả lượt 12 vòng | **12,56 MB** tổng |
| Tick WebSocket thô (6 mẫu smoke) | `bytes_up` 12.405–38.282 · `bytes_down` 94.269–97.309 |

`bytes_down` ≈ 96 KB khớp đúng kích thước mô hình (24.000 × 4 byte) — dấu hiệu các
con số này nhất quán với thiết kế, không phải số bịa.

Cần nói đúng bản chất hai bộ số, đừng lẫn:
- Số KB/vòng ở bảng trên là **byte backend báo ra trong từng tick** (console đọc
  `bytes_up`/`bytes_down`), tính theo mô hình kích thước cố định của bản demo.
- Số 217.216 byte/lần chuyển ở dưới là **bản nghiên cứu thật** (`results/reco_main.json`),
  đo từ bảng embedding 54.304 tham số float32.
Cả hai đều không chứa dữ liệu thô; chênh nhau vì hai cấu hình mô hình khác nhau.

**Chi phí thật của bản nghiên cứu** (MEDAJob, 20 vòng, 5 client): 54.304 tham số,
**217.216 byte mỗi lần chuyển**, tổng gửi lên 19.617.500 byte ⇒ trung bình
**980.875 byte/vòng** (5 client cùng gửi), gấp **6.565 lần** dữ liệu thô; điểm hoà
vốn băng thông là **1.634.792 tương tác**. Kết luận phải nói thẳng: **FL không tiết
kiệm băng thông ở quy mô này**. Lợi ích là tuân thủ dữ liệu, không phải byte.

**Giới hạn — nói ngay, đừng để bị hỏi:**
Đây **chưa phải bảo vệ tuyệt đối**. Server vẫn thấy vector cập nhật, và có tấn công
*gradient inversion* / *membership inference* suy ngược thông tin từ gradient. Đồ án
**chưa** cài DP-SGD, **chưa** có secure aggregation, **chưa** đo được mức rò rỉ
thực tế trên dữ liệu này ⇒ ghi "chưa xác minh". Câu đúng: "FL giảm mạnh bề mặt rò
rỉ vì dữ liệu thô không rời máy; nó không phải mã hoá".

---

## 4. Vì sao 9.116 node là đúng

Nhà tuyển dụng là **silo tự nhiên**: dữ liệu ứng tuyển phát sinh tại nhà đó, thuộc
nhà đó, và về mặt pháp lý (Luật Bảo vệ Dữ liệu Cá nhân, GDPR) không được gom về một
chỗ. Chia theo employer không phải chia cho đẹp — đó là ranh giới có thật ngoài đời.

Một ứng viên có thể ứng tuyển ở nhiều nhà: **44,58%** user (76.584 người) thuộc ≥2
client, trung bình **2,41** client/user. Nhưng mỗi employer **chỉ thấy phần của
mình** — `randstad` thấy đơn vào tin của `randstad`, không thấy đơn vào tin của
`spherion`. Đây là **cross-silo hợp lệ**, không phải rò rỉ: cùng một người xuất
hiện ở hai silo là bản chất thị trường tuyển dụng, không phải chia sẻ dữ liệu giữa
hai client.

Quy mô cũng kiểm được, không phải suy đoán: **9.116/9.116** client có ≥1 job, có ≥1
user, có ≥1 cạnh train; không client nào rỗng. Nhưng phân bố rất lệch — client nhỏ
nhất 10 application, lớn nhất 4.745 (**474,5 lần**), top-1 chỉ chiếm **1,09%**;
**418 client chỉ có 1 job**, **8.745 client (95,9%)** có ≥10 cạnh train. Vì thế phải
nói kèm: client bé góp gradient rất mỏng.

Cách biết một cạnh thuộc node nào rất đơn giản: đồ thị đầy đủ có **264.995 nút** và
**764.364 cạnh**, trong đó **436.893 cạnh user–job**; mỗi cạnh user–job thuộc về
client của **job** (`client_of_job[j]`). Không cần chia lại, chỉ cần tra bảng.

---

## 5. Kịch bản nói khi bảo vệ (đọc thuộc)

1. "Mỗi ô vuông trên màn hình là một nhà tuyển dụng. Cả hệ có 9.116 ô như vậy."
2. "Một node sở hữu đúng những đơn ứng tuyển vào tin của mình. Ví dụ randstad:
   4.745 đơn, của 4.215 ứng viên, vào 603 tin. Nó không biết những người đó còn
   ứng tuyển ở đâu khác."
3. "Một vòng chạy có 5 bước: server gửi bảng embedding xuống; node tự học trên dữ
   liệu của mình; node gửi lên **chỉ những hàng embedding đã đổi**; server cộng có
   trọng số; server gửi mô hình mới xuống."
4. "Dữ liệu thô không bao giờ đi. Ở lại máy là mã ứng viên, mã tin, đơn ứng tuyển,
   ngày ứng tuyển. Đi lên chỉ là vector số thực."
5. "Đo thật: mỗi node gửi lên khoảng 12 đến 15 KB một vòng, nhận xuống khoảng 95 KB.
   Cả lượt 12 vòng tốn 12,56 MB. Không có một dòng dữ liệu thô nào trong đó."
6. "Kết quả: học cục bộ được Recall@20 0,402, FedAvg được 0,497, tập trung 0,504 —
   lấy lại 93% khoảng cách mà không gom dữ liệu."
7. "Em nói rõ hạn chế: FL ở quy mô này tốn băng thông gấp 6.565 lần gửi dữ liệu thô,
   và chưa có DP-SGD nên chưa chống được tấn công suy ngược từ gradient."
8. "Nên giá trị của phần này không phải tốc độ, mà là **dữ liệu không rời máy** —
   điều mà mô hình tập trung không làm được về mặt pháp lý."

### Ba câu hội đồng hay hỏi

**"Sao không gom dữ liệu về một chỗ cho nhanh?"**
> "Nhanh hơn thật — tập trung được 0,504 so với 0,497. Nhưng gom nghĩa là chuyển
> 436.893 đơn ứng tuyển kèm hồ sơ cá nhân từ 9.116 nhà tuyển dụng về một máy chủ.
> Việc đó vi phạm Luật Bảo vệ Dữ liệu Cá nhân và GDPR, nên mô hình đó không triển
> khai được. Câu hỏi đúng là: giữ dữ liệu tại chỗ thì mất bao nhiêu chất lượng? Trả
> lời: 0,007 Recall@20, tức 7% khoảng cách, đổi lấy việc dữ liệu không rời máy."

**"Bảo mật thật không hay chỉ là che mắt?"**
> "Thật ở mức dữ liệu thô: không có user_id, job_id, ngày ứng tuyển nào được gửi
> lên — có test tự động kiểm tra cấu trúc gói tin client. Nhưng em không nói là bảo
> mật tuyệt đối: server vẫn thấy vector cập nhật, và có tấn công suy ngược từ
> gradient. Muốn chắc hơn phải thêm DP-SGD hoặc secure aggregation — đồ án chưa làm,
> em ghi ở phần hướng phát triển."

**"9.116 node thì mỗi node học được gì?"**
> "Mỗi node học phần embedding liên quan tới ứng viên và tin của chính nó, rồi đóng
> góp phần đó. Node lớn như randstad đóng góp nhiều hàng hơn node chỉ có 1 job — 418
> node như vậy. Nhờ FedAvg, node nhỏ vẫn hưởng mô hình do các node lớn học được, dù
> nó không thấy dữ liệu của họ."

---

## 6. Nếu bị hỏi khó

| Câu hỏi | Trả lời ngắn | Số liệu chứng minh |
|---|---|---|
| "Gửi tham số tốn bao nhiêu so với gửi dữ liệu?" | Tốn **nhiều hơn** 6.565 lần ở quy mô này; FL chỉ rẻ hơn khi vượt 1,63 triệu tương tác | 19.617.500 byte tham số vs 2.988 byte dữ liệu thô; 54.304 tham số × 4 byte |
| "Node gửi lên cái gì, có id người không?" | Chỉ số hàng + vector float32 + trọng số; không id, không ngày | Test `tests/test_federated.py::test_payload_contains_no_raw_data`; 12,5–15,5 KB/node/vòng |
| "9.116 node có node nào rỗng không?" | Không. 100% có ≥1 job, ≥1 user, ≥1 cạnh train; nhưng 418 node chỉ 1 job | 9.116/9.116; min 10 app, max 4.745 app; 8.745 node ≥10 cạnh train |
| "Một người xuất hiện ở nhiều node thì có phải rò rỉ?" | Không. Mỗi node chỉ thấy đơn vào tin của mình — cross-silo hợp lệ | 44,58% user (76.584) thuộc ≥2 client, TB 2,41 client/user |
| "Metric trên console có phải kết quả huấn luyện thật?" | Không. Latency đo thật, metric mô phỏng | API trả `simulated_metrics: true`; latency từ `perf_counter()` |

---

## 7. Ba chỗ chưa xác minh (nói trước khi bị hỏi)

1. **WebSocket trong iframe Streamlit** — chưa xác minh chạy được trong môi trường
   nhúng `components.html`. Nếu bị chặn, UI vẫn vẽ được bằng polling
   `GET /api/train/status/{run_id}`.
2. **Mức rò rỉ riêng tư định lượng** — chưa đo tấn công gradient inversion trên dữ
   liệu này. Chỉ khẳng định được "không gửi dữ liệu thô", không khẳng định "không
   suy ngược được".
3. **Recall@20 0,497** đo trên **16 ứng viên** trong tập kiểm thử (58 tương tác) ⇒
   chỉ kết luận được thứ hạng tương đối, không kết luận được chênh lệch nhỏ.

---

*Số liệu tái lập: `python src/report/make_facts.py` sinh `docs/SO_LIEU_CHINH.md`;
log UI thật ở `ui/last_real_backend_pg.json`.*
