# Quyết định bộ dữ liệu cho đồ án GNN + Federated Learning cho gợi ý việc làm

**Người viết:** doc-writer (task t6) · **Ngày:** 2026-11-08 (Asia/Saigon)
**Nguồn số:** t1, t2, t3, t4, t5 + phép đo độc lập của t6 (mục 10). Không có số nào trong tài liệu này không truy được về một file bằng chứng.
**Người đọc:** sinh viên chuẩn bị bảo vệ đồ án trước hội đồng.

---

## Tóm tắt cho người đọc vội (5 dòng)

1. **Không tồn tại bộ dữ liệu công khai thoả đồng thời tương tác thật và giấy phép sạch.**
2. Bộ đang dùng (MEDAJob) không đủ về mặt thống kê, **và tầng tương tác của nó do 20 tài khoản thử nghiệm của sinh viên tạo ra** — không dùng làm kết quả chính.
3. Bộ CareerBuilder vừa crawl có tương tác thật nhưng thiếu employer, thiếu kỹ năng, thiếu rating, mật độ **0,001365%** (Bảng 1).
4. **Khuyến nghị chính (P1):** CareerBuilder + O\*NET Technology gán kỹ năng **ở mức nghề**, client chia theo địa lý — 636.896 cạnh tương tác thật, 709 nghề, 8.316 kỹ năng.
5. **Dự phòng (P6):** MEDAJob để trình bày + CareerBuilder chỉ làm kiểm tra độ bền, không công bố.

---

## 1. Vấn đề: vì sao MEDAJob không đủ

### 1.1 Quy mô và sức mạnh thống kê

| Chỉ số MEDAJob | Giá trị | Nguồn |
|---|---|---|
| Ứng viên | **70** | `artifacts/medajob/meta.json` |
| Tin tuyển dụng (sau làm sạch) | **1.014** | `meta.json` (thô 1.217) |
| Tương tác (train + test) | **307** (249 / 58) | `meta.json` |
| Ứng viên có mặt trong tập test | **16** (23% của 70) | `meta.json` |
| Nút kỹ năng / nút ngành | 603 / 10 | `meta.json` |
| Số tham số mô hình | 54.304 | `docs/SO_LIEU_CHINH.md` §3 |
| Tương tác huấn luyện | 249 | `meta.json` |
| **Tham số mỗi tương tác huấn luyện** | **218** | `_newdata_audit/p25_howmuch.py` |
| Độ thưa ma trận | 0,4325% | `meta.json` |
| Số employer_id phân biệt | 342 | `meta.json` |
| Số tin dùng chung tập kỹ năng mẫu | 682 (67,3%) | `meta.json` |

**Đọc bảng này thế nào:** mô hình có 54.304 tham số nhưng chỉ 249 tương tác để học. Quy tắc kinh nghiệm cần ≥10 mẫu mỗi tham số; ở đây thiếu vài bậc độ lớn. Không có regularization nào cứu được tỉ lệ đó.

### 1.2 Tuyên bố trung tâm "lấy lại 92,9% khoảng cách" không đứng vững

Bootstrap 20.000 lần trên đơn vị người dùng (`p25_howmuch.py`):

| Đại lượng | Giá trị |
|---|---|
| Điểm ước lượng "lấy lại 92,9% khoảng cách" | **92,9%** |
| CI 95% bootstrap của tỉ số đó | **[-300%, +450%]** |
| Tỉ lệ lần tỉ số < 0 (FL tệ hơn cục bộ) | **9,8%** |
| Tỉ lệ lần tỉ số > 1 (FL vượt cả tập trung) | **38,8%** |
| Số user cần để phát hiện hiệu ứng 0,05 (power 80%, α 5%) | **423** |
| Số user cần để phát hiện hiệu ứng 0,03 | **1.175** |
| Số user cần để phát hiện hiệu ứng 0,02 | **2.644** |
| Số user hiện có | **16** |
| Tin "liên quan" trung bình mỗi user test | **3,62** |
| Mỗi lần "hit" thêm làm R@20 nhảy trên một user | **0,28** (≈ 1/3,62) |

Khoảng tin cậy trải từ âm sang dương và vắt qua 1. Nghĩa là dữ liệu **không phân biệt được** ba khả năng: FL tốt hơn cục bộ, FL bằng cục bộ, FL tệ hơn cục bộ. Con số 92,9% là một điểm ước lượng trên 16 quan sát, không phải một kết luận.

Thêm một chi tiết làm mẫu số yếu đi: mỗi user test chỉ có trung bình **3,62** tin "liên quan" (rating ≥ 4). Với mẫu số nhỏ như vậy, Recall@20 chỉ nhận vài giá trị rời rạc; mỗi lần "hit" thêm làm chỉ số nhảy khoảng 0,28 trên một user.

### 1.3 MEDAJob: job corpus phần lớn là THẬT, nhưng TẦNG TƯƠNG TÁC là tài khoản thử nghiệm

> ⚠️ **ĐÍNH CHÍNH so với bản nháp và so với giả định ban đầu của nhóm.** Đo trực tiếp trên `E:\2026\DUT\DSS\SauGK\Lab03\job.csv` (1.217 dòng, 25 cột) cho kết quả **không** phải "toàn bộ MEDAJob là dữ liệu tổng hợp". Phải nói chính xác, nếu không hội đồng sẽ bắt lỗi ngược lại.

**Tầng tin tuyển dụng — phần lớn là thật:**

| Đo trên `job.csv` | Số | Tỉ lệ |
|---|---|---|
| Tổng số tin | **1.217** | 100% |
| Tin có ≥1 dấu hiệu sinh tự động | **58** | **4,77%** |
| Tin trông như thật (không dấu hiệu nào) | **1.159** | **95,23%** |
| `company_name` phân biệt | **554** | — |
| Tên công ty **có dấu tiếng Việt** (dấu hiệu crawl thật) | **358** tên / 801 tin | 65,82% |
| `company_name` khớp mẫu `Tech Company N` | 46 tin / **5** tên | 3,78% |
| `hr_contact` hoặc website hoặc `link` chứa `example.com` | **57** | 4,68% |
| `link` chứa `tkrecsys.example.com` | **52** | 4,27% |
| `job_title` kết thúc bằng 2 chữ số | **46** | 3,78% |

*(Ba dấu hiệu định danh trên **trùng nhau gần hết**, không phải ba bằng chứng độc lập: 46 tin `Tech Company N` và 46 tin có tiêu đề kết thúc bằng số **trùng nhau 45 tin**. Hợp của cả ba dấu hiệu là **58 tin (4,77%)** — đúng một cụm dữ liệu mồi, không phải nhiều cụm rải rác.)*

Tên công ty thật đọc được trong file: FPT Software Academy, Viettel AI, VinBigData, TIKI, TOPCV Việt Nam, Savvycom, Axon Active Vietnam, LG CNS Viet Nam, Saigon Technology, ZIGExN VeNtura. Đây là các doanh nghiệp Việt Nam có thật, không thể sinh bằng Faker.

Bằng chứng ngược chiều với "dữ liệu tổng hợp": các cột phân loại **không sạch** mà lộn xộn đúng kiểu dữ liệu crawl — `job_type` có **11** giá trị (lẫn `Full-time` và `full-time`, `Tại văn phòng`, `Không nêu rõ`), `experience_level` có **61** giá trị (lẫn `2 năm`, `Mid-Senior`, `Sinh viên/Thực tập sinh`, `Senior/Lead (8+ năm)`). Dữ liệu sinh tự động không tạo ra loại nhiễu này.

**Tầng tương tác — đây mới là chỗ hỏng, và hỏng nặng hơn:**

| Đo trên `ratings.csv` + `users.csv` | Số | Tỉ lệ |
|---|---|---|
| Dòng rating | **321** | 100% |
| **User phân biệt tạo ra toàn bộ rating** | **20** | — |
| User có username dạng mã sinh viên `sv` + 9–10 chữ số | **19** | **95,0%** |
| User có email `@dut.vn` hoặc `@dut.udn.vn` | **17** | 85,0% |
| User có `role = employer` | **19** | 95,0% |
| User có `role = candidate` | **1** | 5,0% |
| Rating có comment | **0** | 0% |
| Job được rating | **187** / 1.217 | 15,37% |
| Job **không** được rating | **1.030** | 84,63% |
| Rating ≥ 4 (nhãn "liên quan") | **240** | 74,77% |
| User sạch (70) **có** ≥1 rating | **19** | 27,14% |
| User sạch (70) **không có** rating nào | **51** | 72,86% |

Ví dụ nguyên văn username của các tài khoản tạo rating: `sv102220332`, `sv102220119`, `sv102220051`, `sv102230270`. Đây là **tài khoản thử nghiệm của sinh viên trong môn học**, không phải ứng viên thật. Toàn bộ 321 rating do 20 tài khoản này tạo ra, và 19 trong 20 mang `role = employer` — nghĩa là **nhà tuyển dụng đi rating tin của nhau**, không phải ứng viên ứng tuyển.

**Tầng hồ sơ ứng viên — mỏng và lẫn vai:**

| Đo trên `user_profiles.csv` | Số | Tỉ lệ |
|---|---|---|
| Dòng hồ sơ | **75** | — |
| Hồ sơ thuộc user `role = employer` | **41** | 54,67% |
| Hồ sơ thuộc user `role = candidate` | **34** | 45,33% |
| `cv_url` rỗng | **70** | 93,33% |
| `user_summary` rỗng | **43** | 57,33% |
| `profile_vector` có dữ liệu | **0** | **0%** |
| `title` phân biệt | **36** | — |

**Bảng 1c — Chất lượng nội dung tin trong MEDAJob (đo trên `job.csv` 1.217 dòng + `meta.json`)**

| Chỉ số | Số | Tỉ lệ | Nguồn |
|---|---|---|---|
| Số tin sau làm sạch | **1.014** | — | `meta.json` |
| `job_description` trùng y hệt `job_title` | **741** / 1.217 | **60,89%** | [ĐO t6] |
| Tin "chỉ có tiêu đề" (`title_only_jobs`) | **707** / 1.014 | **69,72%** | `meta.json` |
| Tin dùng chung tập kỹ năng mẫu (`template_jobs`) | **682** / 1.014 | **67,3%** | `meta.json` |
| `job_description` rỗng | **22** / 1.217 | 1,81% | [ĐO t6] |
| `job_description` dài hơn 80 ký tự | **418** / 1.217 | 34,35% | [ĐO t6] |
| Số mô tả phân biệt | **1.002** / 1.217 | — | [ĐO t6] |

**Kết luận mục 1 — phát biểu chính xác để bảo vệ:**

MEDAJob sai ở **tầng tương tác**, không phải ở tầng tin tuyển dụng. Cụ thể:

1. **Yêu cầu cứng (1) "tương tác người dùng–tin THẬT" không đạt.** 321 rating do 20 tài khoản thử nghiệm của môn học tạo ra (95,0% username dạng mã sinh viên, 85,0% email `@dut.vn`), 0 comment, 84,63% tin không có rating nào.
2. **Yêu cầu (3) "hồ sơ ứng viên" đạt rất yếu.** 54,67% hồ sơ thuộc tài khoản `employer`, 93,33% không có CV, `profile_vector` rỗng 100%.
3. **Tầng tin tuyển dụng thì dùng được về nguồn gốc** (95,23% tin trông thật, 358 tên công ty Việt Nam có thật) nhưng **nội dung mỏng**: 60,89% mô tả trùng y hệt tiêu đề, 69,72% tin chỉ có tiêu đề, 67,3% tin dùng chung một tập kỹ năng mẫu — xem Bảng 1c.
4. **Tầng thống kê vẫn là vấn đề quyết định:** 16 user trong test, tham số gấp 218 lần số tương tác huấn luyện.

Nói cách khác: MEDAJob **không phải** "dữ liệu tổng hợp 100%" như cách nói tắt dễ gây phản bác. Nó là **một bộ tin tuyển dụng Việt Nam crawl thật, ghép với một tầng tương tác do sinh viên trong môn tự tạo để chạy thử**. Chính xác hơn, và cũng nặng hơn cho đồ án: **tầng tương tác — thứ đề bài cần nhất — không có dữ liệu thật đứng sau.**

*(Chi tiết máy đọc: `_newdata_audit/t6_verify/t6_medajob_provenance.json`.)*

---

## 2. Vì sao tìm mãi không ra: hai yêu cầu loại trừ nhau

### 2.1 Quan hệ loại trừ (1) ↔ (4) ↔ (5)

Khảo sát 12 ứng viên ở t1 rồi kiểm chứng thực nghiệm ở t4 cho ra một quy luật có thể phát biểu thành một câu:

> **Bộ có tương tác người dùng–tin thật thì không có cột đơn vị tuyển dụng. Bộ có cột đơn vị tuyển dụng thì không có tương tác thật. Bộ có cả hai trên giấy thì là dữ liệu tổng hợp.**

Đây không phải hạn chế của nhóm. Đây là thuộc tính của toàn bộ dữ liệu tuyển dụng công khai hiện có, và nó xuất phát từ một lý do kinh tế: log hành vi ứng tuyển là tài sản cạnh tranh của nền tảng, còn bảng tin tuyển dụng thì ai cũng crawl được. Không nền tảng nào công bố đồng thời cả hai.

t3 xác nhận cùng kết luận từ phía literature: trong 21 tài liệu FL-recsys đã kiểm, **không benchmark công khai nào có nhãn tổ chức cho recsys**. Mọi benchmark (pFL-Bench NeurIPS'22, FLBench, FLamby) đều lấy dữ liệu centralized rồi **chia lại**. Nghĩa là việc tự định nghĩa ranh giới client là thực hành chuẩn đã công bố, không phải né tránh.

### 2.2 Bảng 1 — Ma trận loại trừ trên 5 tiêu chí cứng

Ký hiệu: ✅ đạt · ⚠️ đạt một phần · ❌ không đạt · ? chưa xác minh

| Bộ dữ liệu | (1) Tương tác thật | (2) Kỹ năng tin | (3) Hồ sơ UV | (4) Employer | (5) License | Điểm |
|---|---|---|---|---|---|---|
| **CareerBuilder 2012** | ✅ 1.603.111 | ❌ 0% có sẵn | ✅ | ❌ | ❌ **CẤM** | 2/5 |
| **XING 2017** (RecSys) | ✅ 7.267.094 | ⚠️ ID ẩn danh | ✅ | ❌ | ⚠️ cấm tái phân phối | 3,5/5 |
| **XING 2016** (RecSys) | ✅ 8.800.000 (bán tổng hợp) | ⚠️ ID ẩn danh | ✅ | ❌ | ⚠️ cấm tái phân phối | 3,5/5 |
| **OLX jobs-interactions** | ✅ 65.502.201 | ❌ 0 cột | ❌ | ❌ | ⚠️ **VÙNG XÁM** | 1,5/5 |
| **`lukebarousse/data_jobs`** | ❌ 0 user | ✅ 85,10% | ❌ | ✅ 139.984 cty | ✅ Apache-2.0 | 3/5 |
| **`arshkon` LinkedIn** | ❌ 0 user | ⚠️ `skills_desc` 1,97% | ❌ | ✅ 15.850 cty | ✅ CC BY-SA 4.0 | 2,5/5 |
| **`datastax` LinkedIn (mirror)** | ❌ 0 user | ❌ 1,97% | ❌ | ✅ 98,61% | ⚠️ chưa khai báo | 1,5/5 |
| **`xanderios` LinkedIn** | ❌ 0 user | ❌ 1,01% | ❌ | ✅ 98,03% | ✅ MIT | 1,5/5 |
| **Djinni job descriptions** | ❌ 0 user | ❌ chỉ 42 keyword | — | ✅ 100%, 4.997 cty | ✅ MIT | 2,5/5 |
| **Djinni candidate profiles** | ❌ 0 user | — | ✅ CV 100% | — | ✅ MIT | bổ trợ (3) |
| **JobHop (UGent)** | ❌ 0 tương tác | ❌ | ⚠️ không phát hành skill | ❌ | ✅ CC-BY-4.0 | 1/5 |
| **Zhaopin/Tianchi 31623** | ⚠️ nhãn 0–3, chưa xác minh | ? | ? | ? | ? **chưa đọc được** | ?/5 |
| **`asaniczka` 1,3M** | ❌ theo mô tả | ? | ❌ | ? | ✅ ODC-By | ?/5 |
| **`kandij`** | ❌ không có user | ❌ | ❌ | ⚠️ Company không có user | ❌ Unknown | 0,5/5 |
| **`kshitizregmi`** | ❌ | ❌ | ❌ | ❌ | ✅ CC0 | 0,5/5 |
| **`ravindra`** | ❌ | ⚠️ 100% nhưng **tổng hợp** | ❌ | ⚠️ | ✅ CC0 | **LOẠI** |
| **3 repo `job-postings-applications`** | ⚠️ trên giấy | ⚠️ trên giấy | ⚠️ trên giấy | ⚠️ trên giấy | ⚠️ cc-by-nc-4.0 | **LOẠI** |

**Không có dòng nào có đủ 5 dấu ✅.** Cột (4) và (1) chưa từng cùng ✅ trên một dòng.

### 2.2b Bảng 1b — Mật độ ma trận tương tác (đo trên dữ liệu thật)

| Bộ | Tương tác | User | Job | Mật độ | % |
|---|---|---|---|---|---|
| **CareerBuilder (toàn bộ)** | 1.603.111 | 389.708 | 1.092.096 | 3,767e-06 | 0,000377% |
| **CareerBuilder (chỉ user/job có tương tác)** | 1.603.111 | 321.235 | 365.668 | **1,365e-05** | **0,001365%** |
| XING 2017 (chỉ tương tác dương) | 7.267.094 | 1.497.020 | 1.306.054 | 3,717e-06 | 0,000372% |
| XING 2017 (mọi event) | 322.776.002 | 1.497.020 | 1.306.054 | 1,651e-04 | 0,016509% |
| XING 2016 | 8.800.000 | 1.500.000 | 1.300.000 | 4,513e-06 | 0,000451% |
| OLX | 65.502.201 | 3.295.942 | 185.395 | **1,072e-04** | 0,010720% |

CareerBuilder và XING cùng bậc 10⁻⁶–10⁻⁵, tức đều cực thưa. OLX dày hơn 8–28 lần nhưng không có thuộc tính tin.

### 2.3 Bảng 2 — Vì sao ba hướng "cứu" cột (4) đều thất bại, kèm số đo

| Hướng | Kết quả đo | Kết luận |
|---|---|---|
| Trích employer từ text CareerBuilder — regex field `Company:` tường minh | **0,17%** (34/20.000 tin) | Vô dụng |
| Trích employer từ text — tên công ty ở dòng đầu | **2,03%** (mẫu 50.000) | Vô dụng |
| Trích employer từ text — hậu tố pháp lý (`Inc, LLC`) | 30,93% nhưng nhiễu (khớp cả "Life Insurance") | Loại |
| **Email domain trong text tin** | phủ **12,05%** tin / **21,32%** application | **Sai ngữ nghĩa** |
| Top email domain đo được | `volt.com` 13.675 · `randstadusa.com` 6.170 · `roberthalf.com` 2.982 | Toàn **công ty headhunt**, không phải doanh nghiệp tuyển dụng |
| Ghép title → `arshkon` để lấy `company_id` | **7,106%** app xác định được đúng 1 công ty | Không đủ |
| Ghép title → `arshkon`, phần mơ hồ | **39,503%** app; median **18** công ty/title; max **372** | Gán bừa = nhãn sai = client FL sai |
| Ghép title → `data_jobs` | **23,055%** app khớp, nhưng **86,92%** là trùng chuỗi vô nghĩa | **Loại** |
| Ghép title → `data_jobs`, top title khớp nhiều application nhất | `administrative assistant` **35.604** app | **rác trùng chuỗi**, không phải nghề data |

Ví dụ cụ thể của "trùng chuỗi vô nghĩa": title `administrative assistant` khớp chính xác giữa CareerBuilder và `data_jobs` với **35.604** application. `data_jobs` có tin thư ký vì bộ này thu thập tiêu chí lỏng. Nếu ghép rồi gán `job_skills` của `data_jobs` cho tin đó, ta gán `python/sql/tableau` cho tin thư ký. Đây là **sai ngữ nghĩa**, không phải sai kỹ thuật, và không có cách sửa bằng code.

---

## 3. Cách nhận diện dữ liệu tổng hợp (mục dùng được lâu dài)

Đây là phần quan trọng nhất của tài liệu. Bài học của đồ án không phải "tìm được bộ dữ liệu", mà là **đã học được cách phân biệt dữ liệu thật với dữ liệu sinh tự động**. Hội đồng sẽ hỏi đúng câu này.

### 3.1 Checklist 7 dấu hiệu

| # | Dấu hiệu | Cách kiểm | Ngưỡng cảnh báo |
|---|---|---|---|
| 1 | **Số dòng tròn** | đếm từng bảng | 1.000 / 5.000 / 15.000 / 320 |
| 2 | **Nhiều repo khác tên, dữ liệu y hệt** | **băm SHA-256 từng file, so sánh** | ≥2 repo cho cùng hash |
| 3 | Tên người/công ty kiểu Faker | tìm mẫu `X, Y and Z`, `Ltd`, `and Sons` | >30% tên khớp mẫu |
| 4 | Categorical quá sạch | đếm giá trị phân biệt | ≤5 giá trị cho cột đáng lẽ đa dạng |
| 5 | **Cột số phân bố đều vô nghĩa** | xem decile có cách đều | decile cách nhau hằng số |
| 6 | Downloads thấp + tạo gần đây | `createdAt`, `downloads` | tạo trong 6 tháng, <200 download |
| 7 | Không có mốc thời gian lịch sử thật | xem phân bố ngày | toàn bộ dồn vào 1–2 tháng gần đây |

### 3.2 Ví dụ đã bắt được — nhóm 3 repo "hoàn hảo"

Nhóm `mindweave` / `Arivalagan2025` / `kunkrm`, dataset `job-postings-applications`, đạt **cả 5 tiêu chí trên giấy**: có application, có candidate profile, có company, có job, **và cả `offers.accepted` làm nhãn hire**.

t5 kiểm lại độc lập bằng SHA-256, không tin mô tả:

| Bằng chứng | Kết quả [ĐO] |
|---|---|
| SHA-256 của **6/6 bảng** (`applications`, `candidates`, `companies`, `jobs`, `interviews`, `offers`) | **GIỐNG HỆT** giữa cả 3 repo (`n_distinct_hashes = 1`) |
| Số dòng 3 repo | giống hệt: 15.000 / 9.000 / 320 / 2.000 / 7.196 / 938 |
| Dòng đầu `applications` | `1, 1841, 6949, 2025-10-22 22:54:51, job_board, applied, 0.92` — giống hệt |
| `createdAt` 3 repo | 2026-04-12, 2026-09-15, 2026-10-29 |
| Downloads | 175 / 130 / 82 |
| Tên công ty khớp mẫu Faker | **60,94%** |
| Tên công ty có dấu phẩy | **36,56%** (318 tên / 320 dòng) |
| `score` | min 0,350 / max 0,980 / mean 0,6666 · 631 giá trị trên 15.000 dòng |
| Decile của `score` | 0,35 → 0,414 → 0,478 → 0,540 → 0,602 → 0,668 → 0,729 → 0,794 → 0,858 → 0,920 → 0,980 (cách đều ~0,063) |
| `source` / `stage` | 5 giá trị / 4 giá trị |

Bằng chứng mạnh nhất là **SHA-256 trùng khít 6/6 bảng**. Ba tài khoản khác tên không thể tạo ra dữ liệu thật giống nhau đến từng byte. Cộng thêm `score` phân bố đều tuyến tính — đúng dấu hiệu `random.uniform` — và tên công ty sinh bằng Faker.

**Vì sao đây là bẫy nguy hiểm nhất:** nó đạt cả 5 tiêu chí **trên giấy**. Nếu nhóm chọn nó, đồ án lặp lại đúng sai lầm MEDAJob nhưng khó phát hiện hơn nhiều lần.

### 3.3 Áp checklist cho MEDAJob — kết quả KHÔNG phải "đúng cả 7"

Áp checklist một cách trung thực cho ra kết quả **khác** với cách nói tắt "MEDAJob là dữ liệu tổng hợp". Chỉ **2/7** dấu hiệu đúng ở tầng tin, còn tầng tương tác thì hỏng vì lý do khác hẳn.

| # | Dấu hiệu | Số đo trên MEDAJob | Kết |
|---|---|---|---|
| 1 | Số dòng tròn | 1.217 tin / 75 hồ sơ / 321 rating | ❌ **KHÔNG** — không số nào tròn |
| 2 | Repo khác tên, dữ liệu y hệt | không kiểm được (dữ liệu nội bộ môn học) | — không kết luận |
| 3 | Tên Faker | 46 tin / **5** tên `Tech Company N` = **3,78%**; **358** tên công ty Việt Nam có thật, **95,23%** tin trông thật | ⚠️ **MỘT PHẦN** — có nhưng chỉ 3,78% |
| 4 | Categorical quá sạch | `job_type` **11** giá trị (lẫn `full-time`/`Full-time`/`Tại văn phòng`); `experience_level` **61** giá trị | ❌ **NGƯỢC LẠI** — lộn xộn kiểu crawl |
| 5 | Cột số phân bố đều | `rating`: 1→22, 2→19, 3→40, 4→115, 5→125 | ❌ **KHÔNG đều** — lệch rõ về 4–5 (74,77%) |
| 6 | Downloads thấp + mới tạo | export môn học 2026-09 → 2026-10 | ✅ ĐÚNG (nhưng do là bài tập, không phải dấu hiệu bịa) |
| 7 | Không có mốc lịch sử thật | toàn bộ `created_at` trong 1 tháng | ✅ ĐÚNG |

**Vậy MEDAJob hỏng ở đâu?** Không phải vì tin tuyển dụng bịa. Mà vì **tầng tương tác do tài khoản thử nghiệm của sinh viên tạo ra**: 321 rating đến từ **20** tài khoản, **19** trong đó có username dạng `sv` + mã sinh viên, **17** dùng email `@dut.vn`, **19** mang `role = employer`, **0** rating có comment. Đây là dữ liệu **thử nghiệm phần mềm**, không phải hành vi ứng tuyển.

**Câu phải nói với hội đồng (chính xác, không nói quá):**

> *"Tầng tin tuyển dụng của MEDAJob là dữ liệu crawl thật từ thị trường Việt Nam (95,23% tin không có dấu hiệu sinh tự động, 358 tên công ty thật). Nhưng tầng tương tác — thứ đề bài cần nhất — do 20 tài khoản thử nghiệm của sinh viên trong môn tạo ra, 84,63% tin không có rating nào. Vì vậy MEDAJob không dùng được làm bằng chứng cho hành vi ứng tuyển thật, dù không phải toàn bộ là dữ liệu bịa."*

Nói theo cách này **chặt hơn** và **khó bị phản bác hơn** cách nói "toàn bộ là tổng hợp", vì mọi con số đều kiểm lại được từ file gốc.

---

## 4. Bảng khảo sát các bộ dữ liệu công khai

### 4.1 Bảng 3 — Tên, schema, số dòng, license, mức xác minh

Mức xác minh: **A** = đã tải/đọc file thật · **B** = suy từ tài liệu chính thức của nhà phát hành · **C** = chưa xác minh.

| # | Bộ | Schema chính (cột) | Số dòng | License | Mức |
|---|---|---|---|---|---|
| 1 | **CareerBuilder 2012** (Kaggle Job Recommendation) | `apps.tsv`: UserID, WindowID, Split, ApplicationDate, JobID · `users.tsv`: 13 cột hồ sơ (City, State, DegreeType, Major, TotalYearsExperience…) · `jobs.tsv`: JobID, Title, Description, Requirements, City, State… · `user_history.tsv`: UserID, Sequence, JobTitle | app **1.603.111** · user **389.708** (**321.235** có app) · job **1.092.096** (**365.668** có app) · user_history **1.753.901** | **CẤM** ngoài cuộc thi | **A** |
| 2 | **XING 2017** (RecSys Challenge) | `interactions.csv`: user_id, item_id, created_at, interaction_type · `users.csv`: 14 cột · `items.csv`: 13 cột | user **1.497.020** · item **1.306.054** · impression **314.501.101** · dương **7.267.094** | **CẤM** tái phân phối (XING AG) | **B** (cổng đã chết) |
| 3 | **XING 2016** (RecSys Challenge) | `impressions.csv`, `interactions.csv`, `users.csv`, `items.csv`, `target_users.csv` | user **1.500.000** · item **1.300.000** · interaction **8.800.000** · impression **202.000.000** | **CẤM** tái phân phối | **B** |
| 4 | **OLX jobs-interactions** | `interactions.csv`: **user, item, event, timestamp** (4 cột, 1 file) | event **65.502.201** · user **3.295.942** · item **185.395** | **VÙNG XÁM** (học thuật OK, cấm tái phân phối, gửi bản công bố, **có thể thu hồi**) | **A** + **B** |
| 5 | **`lukebarousse/data_jobs`** (HF) | 17 cột: job_title_short, job_title, company_name, **job_skills**, **job_type_skills**, job_posted_date, salary… | **785.741** · company **139.984** | **SẠCH** — Apache-2.0 | **A** |
| 6 | **`arshkon` LinkedIn** (Kaggle) | `postings.csv` 31 cột + `companies/`, `company_industries/`, `jobs/job_skills.csv` (job_id, skill_abr), `mappings/skills.csv` | **123.849** · company_id **15.850** | **SẠCH** — CC BY-SA 4.0 | **A** (postings) / **C** (job_skills) |
| 7 | **`datastax` LinkedIn** (HF mirror) | 31 cột, company_name + company_id | **123.849** | chưa khai báo | **A** |
| 8 | **`xanderios` LinkedIn** (HF) | 28 cột, company_id | **33.246** | **SẠCH** — MIT | **A** |
| 9 | **Djinni job descriptions** (HF) | Position, Long Description, **Company Name**, Exp Years, Primary Keyword, Published | **141.897** · company **4.997** | **SẠCH** — MIT | **A** |
| 10 | **Djinni candidate profiles** (HF) | Position, Moreinfo, Looking For, Highlights, Primary Keyword, **CV**, Experience Years | **210.250** | **SẠCH** — MIT | **A** |
| 11 | **JobHop** (UGent, HF) | resume_id, matched_code, start_date, end_date, university_level | **1.993.291** · resume **284.251** · mã **2.983** | **SẠCH** — CC-BY-4.0 | **A** |
| 12 | **Zhaopin/Tianchi 31623** | table1_user.txt (2,47 MB), table2_jd.txt (273,78 MB), table3_action.txt (48,13 MB) — **tên cột chưa xác minh** | **chưa xác minh** | **chưa đọc được** (SPA shell 4.085 ký tự) | **C** |
| 13 | **`asaniczka` 1,3M LinkedIn** | linkedin_job_postings.csv (10 cột: job_link, job_title, company…) + job_skills.csv (job_link, job_skills) | postings **1.348.454** · skills **1.296.381** · **6,19 GB** | **SẠCH** — ODC-By | **C** cho schema skill |
| 14 | **`kandij`** | Job_Views.csv (id, JobID, Title, **Company**, Date), Positions_Of_Interest.csv (UserID, Position) | job_data **84.089** · Job_Views ~14.546 | **Unknown** | **A** |
| 15 | **`kshitizregmi`** | job_title_des.csv (Job Title, Job Description) | **chưa xác minh** | **SẠCH** — CC0 | **B** |
| 16 | **`ravindra`** job-description | 23 cột, `skills` điền 100% | **1.615.940** · **1,74 GB** | CC0 | **A** — **nhưng TỔNG HỢP** |

### 4.2 Bảng 4 — Hai bộ phụ trợ bắt buộc (taxonomy)

| Bộ | Nghề | Kỹ năng | Cạnh/nghề | Phân cấp | License | Tiếng Việt |
|---|---|---|---|---|---|---|
| **ESCO v1.2.1** | **2.942** | **13.485** | **36,52** (essential 20,28 min 5 max 70 + optional 16,24) | Có (60/60 có `broaderHierarchyConcept`) | **2011/833/EU** — miễn phí mọi mục đích, bắt buộc ghi công | **KHÔNG CÓ** (28 ngôn ngữ, không có `vi`) |
| **O\*NET 29.3** | **1.016** | `Skills.txt`: **35** element · `Technology Skills.txt`: **8.775** công cụ | Skills.txt: **35,00 cố định** · Technology: min 1 / median 22 / mean 35,41 / max 426 | Có (`Element ID` + IWA 332 + DWA 2.088) | **CC BY 4.0** | Không |

### 4.3 Bảng 5 — License: phân loại ba mức và hệ quả

| Mức | Bộ | Trích văn bản gốc (đã đọc) | Hệ quả cho đồ án |
|---|---|---|---|
| **CẤM** | CareerBuilder | *"use the Data provided to them **solely for purposes of the Competition**"* · *"promptly after the Competition ends, Entrants must **cease all use of the Data** … and **erase or otherwise destroy**"* — Competition Period 2012-08-02 → 2012-10-07 | Không được công bố lại dữ liệu thô. Phải khai báo rõ trong mục Hạn chế |
| **CẤM** | XING 2016/2017 | *"All rights are reserved by XING AG"*, cấm chia sẻ dataset | Không đính kèm được. Thêm nữa cổng đã chết |
| **VÙNG XÁM** | OLX | *"solely as a base or supplement for conducting an analysis or research, **incl. academic** … under no circumstances **the data set itself may be further published**"* · *"**non-commercial**"* · *"**can be revoked** … at any time"* | Dùng được nhưng có thể bị thu hồi, và chỉ 4 cột |
| **VÙNG XÁM** | Zhaopin | **không đọc được văn bản** — trang SPA trả shell 4.085 ký tự; 4 endpoint API đều không trả JSON | Ghi là "chưa xác minh", không ghi như sự thật |
| **SẠCH** | `data_jobs`, Djinni ×2, `xanderios`, O\*NET, ESCO, JobHop, MEDAJob | Apache-2.0 · MIT · MIT · CC BY 4.0 · 2011/833/EU · CC-BY-4.0 | Không rủi ro pháp lý |

Lưu ý: đánh giá license của OLX và Zhaopin **không đọc trực tiếp từ Kaggle/Tianchi** — Kaggle chặn theo User-Agent rồi chặn bằng reCAPTCHA (đối chứng ở t5: cùng URL, python UA trả 404 nhưng browser UA trả 200). Với OLX, license đọc được qua một snapshot Wayback của trang dataset (bản lưu năm 2022, ghi trong `t5_verify/olx_wayback.html`).

---

## 5. KHUYẾN NGHỊ CHÍNH — P1: CareerBuilder + ESCO/O\*NET gán ở MỨC NGHỀ

### 5.1 Ý tưởng cốt lõi

Không ghép hai bộ bằng khoá ngoại (không có khoá, và mọi phép ghép đã đo đều hỏng). Thay vào đó, **đưa cả hai phía về cùng một mã nghề chuẩn**:

```
jobs.tsv.Title ──chuẩn hoá──> mã nghề O*NET/ESCO ──> tập kỹ năng của nghề
user_history.JobTitle ──────> mã nghề ─────────────> tập kỹ năng của user
```

Đây là ghép **ở mức nghề**, không phải join `job_id`. Cả hai phía đều ánh xạ về mã nghề nên không cần khoá ngoại.

### 5.2 Bảng 6 — Đặc tả đồ thị P1 (số đo trên đồ thị cuối)

> **Cấu hình chuẩn:** cấp mã nghề **GỐC 6 ký tự** (`O*NET-SOC` bỏ hậu tố `.xx`) + lớp skill **O\*NET Technology Skills**. Mọi số dưới đây đo lại sau khi sửa lỗi trộn cấp (mục 10.3b), script `_newdata_audit/t6_bang6.py`, bằng chứng `t6_verify/t6_bang6.json`.

| Thành phần | Số lượng | Ghi chú |
|---|---|---|
| **Cạnh User–Job** | **636.896** | **trụ của đồ án** — application thật |
| Nút User | **213.793** | |
| Nút Job | **127.784** | |
| **Nút Occupation** | **709** | mã O\*NET-SOC **gốc** 6 ký tự (sửa từ 832) |
| Nút Skill (Technology) | **8.316** | 94,77% vocabulary công nghệ của O\*NET |
| Cạnh User–Occupation | **352.306** | từ `user_history.JobTitle` |
| **Cạnh Occupation–Skill** | **28.416** | tổng qua các nghề; TB **40,08** kỹ năng/nghề |
| Cạnh Job–Occupation | **127.784** | title → nghề (mỗi job đúng 1 nghề) |
| Cạnh User–Skill | **23.159.948** | suy qua nghề, không phải tự khai |
| Mật độ ma trận User×Job | **0,002331%** | |
| Kỹ năng trung bình mỗi job (nối trực tiếp) | **102,56** | 13.105.686 / 127.784 |
| **% job trong P1 có ≥1 kỹ năng** | **100%** | P1 định nghĩa là job có nghề **và** nghề có skill |
| **% job map được nghề có ≥1 kỹ năng** | **98,97%** | 127.784 / 129.120 |
| **% user trong P1 có ≥1 kỹ năng** | **79,62%** | 170.227 / 213.793 |
| % application map được nghề (không lọc skill) | **40,044%** | 641.952 / 1.603.111 |
| % application có ≥1 kỹ năng | **39,729%** | 636.896 / 1.603.111 |
| Số client FL | **21** | top-20 bang + REST |
| Client: min / median / max | **9.352 / 22.626 / 76.993** | max/min = **8,23×**, top-1 = **12,09%** |
| Đối chứng `hash(user_id) % 21` | **29.410 / 30.178 / 32.252** | max/min = **1,10×** |

**Ba số đã bị thay sau khi sửa lỗi — ghi lại để đối chiếu:**

| Số cũ | Số đúng | Vì sao sai |
|---|---|---|
| 832 nút Occupation | **709** | cộng dồn qua mã đầy đủ nhưng tra skill bằng mã gốc |
| 47.567 cạnh Job–Skill | **28.416** (Occupation–Skill) | phồng **67,4%** do đếm trùng nhóm mã |
| 343.401 cạnh User–Occupation | **352.306** | đếm trên mã đầy đủ thay vì mã gốc |

*Lưu ý về tên gọi: số **47.567** trong bản cũ mang nhãn "Job–Skill" nhưng thực chất là tổng qua **nghề** (Occupation–Skill), vì CareerBuilder không có cạnh job→skill trực tiếp — mỗi job thừa hưởng skill của nghề. Nhãn đã sửa cho đúng.*

### 5.3 Bảng 7 — Vì sao P1 thắng các phương án ghép khác

| | P1 (mức nghề) | P2 (⨝ `data_jobs`) | P3 (⨝ `arshkon`) |
|---|---|---|---|
| % application có kỹ năng **đúng nghĩa** | **39,73%** (636.896 app) | **2,977%** (47.726) | không tính được (`skills_desc` 1,97%) |
| % application xác định được employer | 0% (khai báo proxy) | 0% đúng nghĩa | **7,106%** |
| Tỉ số phủ đúng nghĩa so với P2 | **13,3×** (39,729 / 2,977) | 1× | — |
| Cần khoá ngoại? | **KHÔNG** | Có, và sai ngữ nghĩa | Có, và mơ hồ |
| Kết luận | ✅ **DÙNG** | ❌ loại | ❌ loại |

P1 phủ application đúng nghĩa gấp **13,3 lần** P2.

### 5.4 Bảng 8 — Ba lý do định lượng chọn P1

| Lý do | Số đo | So sánh |
|---|---|---|
| Tương tác thật, không tổng hợp | **636.896** cạnh, **213.793** user, **127.784** job | gấp **2.075×** MEDAJob về tương tác |
| Đạt (2) và (3) ở mức dùng được | **98,97%** job map được có ≥1 skill · **79,62%** user trong P1 có ≥1 skill | MEDAJob: 603 skill nhưng 67,3% tin dùng chung 1 tập mẫu |
| Chi phí gần bằng 0, không rủi ro mất dữ liệu | **đã có 3,63 GB trên đĩa** · `apps.tsv` đọc **1,93 s** · `jobs.tsv` ngoại suy **68,6 s** | cần thêm **12,7 MB** (O\*NET) + vài chục MB (ESCO) |

### 5.5 Bảng 9 — Phát hiện quyết định: lớp Skill của O\*NET `Skills.txt` VÔ DỤNG

Đây là phát hiện của t5, t6 **kiểm lại độc lập** trên zip thật (`_newdata_audit/t6_verify/t6_onet_skill_layers.json`).

| Kiểm tra | `Skills.txt` | `Technology Skills.txt` |
|---|---|---|
| Số dòng | 61.530 | **32.681** |
| Số nghề | **879** | **923** |
| Số mục từ vựng | **35** element | **8.775** công cụ |
| Mục/nghề: min / median / mean / max | **35 / 35 / 35,00 / 35** | **1 / 22 / 35,41 / 426** |
| Số nghề được gán **đủ tất cả** | **879 / 879 = 100%** | **0 / 923** |
| Mục hiếm nhất phủ bao nhiêu % nghề | **100,0%** | 8.677 công cụ phủ ≤5% nghề |
| Top 3 công cụ phổ biến (số nghề) | không áp dụng (mọi nghề có đủ 35) | Microsoft Excel **859** · Microsoft Office software **813** · Microsoft Word **784** |
| Verdict | ❌ **KHÔNG phân biệt — loại** | ✅ **PHÂN BIỆT — dùng** |

Đọc bảng này: mọi nghề đều có **đủ 35/35** kỹ năng, và kỹ năng hiếm nhất vẫn phủ **100%** nghề. Nghĩa là đồ thị `Occupation–Skill` trở thành **bipartite đầy đủ**; nút Skill có entropy bằng 0 và không mang thông tin nào. GNN lan truyền qua nó chỉ như một hằng số.

Nếu nhóm làm theo hướng "dùng `Skills.txt`", đồ án sẽ có một lớp "kỹ năng" **trông đẹp trong hình vẽ nhưng vô dụng** — đúng loại lỗi khó phát hiện khi bảo vệ. Top 3 công cụ của `Technology Skills.txt` (Microsoft Excel 859 nghề, Microsoft Office software 813, Microsoft Word 784) là các công cụ phổ biến; phần lớn 8.775 công cụ còn lại là đặc trưng riêng của từng nghề.

**Sửa:** dùng **O\*NET Technology** làm lớp Skill của đồ thị (8.316 nút cụ thể như `Python`, `SAP`, `AutoCAD`; **40,08** kỹ năng/nghề ở cấp mã gốc). **ESCO** (13.485 skill, 36,52 cạnh/nghề) giữ vai trò **taxonomy chuẩn hoá + phân cấp**, không phải lớp cạnh chính của P1. **Không dùng `Skills.txt` 35-element.**

---

## 6. DỰ PHÒNG — P6: MEDAJob trình bày + CareerBuilder kiểm tra độ bền

| | P6 |
|---|---|
| Cấu trúc | MEDAJob cho toàn bộ phần trình bày; CareerBuilder chỉ chạy robustness check, **không công bố số liệu chi tiết** |
| License | **SẠCH 100%** — không rủi ro pháp lý |
| Quy mô | **307** tương tác / **70** user / **1.014** job |
| CI 95% của R@20 (FedAvg) | **[0,334; 0,655]** — rộng 0,32 |
| Rủi ro bị phản biện | "Đóng góp khoa học ở đâu khi chỉ có 307 tương tác?" — **nặng hơn** rủi ro license của P1 |

**Cảnh báo bắt buộc nếu chọn P6:** phải khai báo **tầng tương tác của MEDAJob do 20 tài khoản thử nghiệm của sinh viên tạo ra** (mục 1.3 và 7.1). Nếu trình bày MEDAJob như "dữ liệu người dùng thật" thì đó là **báo cáo sai**, và hội đồng có thể kiểm bằng cách mở `users.csv` xem username. Câu nói an toàn: *"MEDAJob được dùng làm **case study phương pháp**, không phải bằng chứng thực nghiệm về hành vi ứng tuyển."*

### Bảng 10 — Ba lựa chọn đối phó và đánh đổi

| | Lựa chọn | Đánh đổi | Ai có thể phản đối |
|---|---|---|---|
| **(A)** | CareerBuilder nhưng **không công bố dữ liệu thô**, chỉ công bố mã + số liệu tổng hợp — **chọn làm chính** | Mất khả năng tái lập của người đọc | Giảng viên chấm pháp lý chặt; người phản biện hỏi "dữ liệu đâu để tôi kiểm?" |
| **(B)** | MEDAJob demo + CareerBuilder robustness không công bố — **dự phòng** | Kết quả chính chỉ 307 tương tác, không có ý nghĩa thống kê | Người phản biện hỏi "đóng góp khoa học ở đâu?" |
| **(C)** | OLX dù chỉ 4 cột | Mất (2) skill, (3) profile, (4) employer — không còn là "gợi ý việc làm có kỹ năng" | Người phản biện hỏi "đề bài yêu cầu kỹ năng, sao bỏ hết?" — **loại** |

---

## 7. Sáu điều phải nói thật với hội đồng

Mỗi dòng một câu, đọc nguyên văn được.

1. **Không có cột `employer_id` trên bất kỳ dữ liệu công khai nào.** Client FL của chúng em là **proxy địa lý**, không phải ranh giới pháp lý của doanh nghiệp. Đây là thuộc tính của dữ liệu, không phải hạn chế của nhóm.
2. **License CareerBuilder cấm dùng ngoài cuộc thi đã kết thúc 2012.** Chúng em **không công bố dữ liệu thô**, chỉ công bố mã và số liệu tổng hợp, và có phương án B hợp pháp 100% để đối chiếu.
3. **Kỹ năng phía ứng viên là SUY QUA NGHỀ** (từ `user_history.JobTitle`), không phải ứng viên tự khai. Đây là prior, không phải ground truth.
4. **ESCO không có tiếng Việt** — đã kiểm bằng API, 28 ngôn ngữ, `vi` không nằm trong `preferredLabel` lẫn `alternativeLabel`. Cách xử lý: giữ `skill_uri` làm khoá, dịch nhãn hiển thị ở tầng UI.
5. **86,92% khớp khi join CareerBuilder với `data_jobs` là rác vô nghĩa; trần đúng nghĩa chỉ 2,977%.**
6. **Chia client theo bang tạo non-IID ở mức ITEM nhưng gần IID ở mức NHÓM NGÀNH** — xem Bảng 11; không được dùng con số nhóm ngành để biện luận "cách chia tạo non-IID".

### 7.1 Ba điều bổ sung về MEDAJob — phải nói kèm, nếu không sẽ bị bắt lỗi ngược

Ba dòng dưới đây **không thay** 6 điều trên, mà sửa cách nói tắt dễ bị phản bác "anh nói cả bộ là dữ liệu bịa, chứng minh đi".

| # | Điều phải nói | Số đo |
|---|---|---|
| a | **Tầng tin tuyển dụng của MEDAJob là crawl thật**, không phải bịa. | **95,23%** tin (1.159/1.217) không có dấu hiệu sinh tự động; **358** tên công ty Việt Nam có thật |
| b | **Tầng tương tác là tài khoản thử nghiệm**, không phải hành vi ứng tuyển. | **321** rating đến từ **20** tài khoản; **19/20** username dạng `sv` + mã sinh viên; **17/20** email `@dut.vn`; **0** rating có comment |
| c | **Phần lớn đồ thị là nút cô lập**, nên kể cả về kỹ thuật cũng không đủ. | **84,63%** tin (1.030/1.217) không có rating nào; **72,86%** user sạch (51/70) không có tương tác |

*(Cách diễn giải "tài khoản thử nghiệm" là **suy luận** từ username dạng mã sinh viên và domain `@dut.vn`, không phải nhãn có sẵn trong dữ liệu. Phần đo được là: 20 tài khoản, 19 username dạng `sv`+chữ số, 17 email `@dut.vn`, 19 mang `role = employer`.)*

### Bảng 11 — Số đo non-IID: phải đọc đúng mức

Đo bằng **đúng một hàm JSD** (client vs phân bố toàn cục, trung bình có trọng số), trên cùng 21 client:

| Mức đo | Chia theo **bang** | Nền **hash % 21** | Chênh |
|---|---|---|---|
| `job_id` cụ thể | **0,7527** | 0,4091 | **+84,0%** |
| `title` (chuẩn hoá) | **0,2314** | 0,0808 | **+186,4%** |
| **Nhóm ngành thô** | **0,0044** | 0,0001 | **≈ IID — KHÔNG dùng** |

Ba bằng chứng độc lập, không phụ thuộc JSD:

| Đo | Giá trị | Ý nghĩa |
|---|---|---|
| % app trên job chỉ **1 bang** ứng tuyển | **46,6%** | gần nửa khối lượng là độc quyền địa phương |
| % app trên job **≥2 bang** dùng chung | **60,2%** | phần lớn *khối lượng* nằm trên item dùng chung |
| Jaccard item-set giữa các bang | median **1,2%**, min 0,6% (IN–AZ), max **16,7%** (NY–NJ) | hai bang **kề nhau** overlap cao nhất → tín hiệu địa lý thật |
| % app có `user.State == job.State` | **84,05%** | thị trường lao động có cấu trúc địa lý mạnh |
| % ứng viên chỉ ứng tuyển trong **1 bang** | **78,9%** | |

Bảng 11b — Số đã bị loại (ghi lại để không ai trích nhầm)

| Đại lượng | Định nghĩa hàm | Giá trị | Trạng thái |
|---|---|---|---|
| JSD `job_id` (bản đo đầu) | pairwise giữa các client với phân bố trung bình | **0,0087** | ❌ **loại** — khác định nghĩa, không so sánh được với Bảng 11 |
| JSD `job_id` nền hash (bản đo đầu) | như trên | **0,0005** | ❌ loại cùng lý do |
| JSD `job_id` (dùng trong báo cáo) | client vs phân bố toàn cục, trung bình có trọng số | **0,7527** (Bảng 11) | ✅ dùng |

**Cách đọc:** con số tuyệt đối 0,7527 **không** có nghĩa, vì vũ trụ item rất lớn nên lấy mẫu IID hoàn hảo cũng cho JSD ≠ 0. Chỉ **phần vượt nền hash** (+84,0% trên `job_id`) mới là tín hiệu non-IID thật.

*(Bài học phương pháp: trước khi so hai lần đo của hai người, phải so **định nghĩa hàm**, không chỉ so con số. Đây đúng loại lỗi hội đồng sẽ bắt nếu hai chương dùng hai cách tính JSD khác nhau.)*

---

## 8. Cảnh báo kỹ thuật (đo trên máy làm đồ án)

| Chỉ số | Giá trị | Hệ quả |
|---|---|---|
| RAM khả dụng | **3.978 MB** | **KHÔNG nạp `jobs.tsv` (3,17 GB) vào pandas** — parse sẽ nở 2–3×, tràn RAM |
| Cách đúng | **streaming `csv.reader`** | đúng như các script t4/t5 đã chạy được |
| Ổ trống | **25,08 GB** | đủ |
| `apps.tsv` (75,03 MB, 1.603.111 dòng) | đọc toàn bộ **1,93 s** | |
| `jobs.tsv` 200.000 dòng | **12,57 s** (15.917 dòng/s) | |
| Ngoại suy `jobs.tsv` (1.092.096 dòng) | **≈ 68,6 s ≈ 1,1 phút** | toàn bộ xử lý P1 dưới **2 phút** trên CPU |
| Dữ liệu CareerBuilder trên đĩa | **3,63 GB** | đã có, không cần tải lại |

Ba bẫy kỹ thuật đã mắc, ghi để không tái diễn:

| Bẫy | Triệu chứng | Cách tránh |
|---|---|---|
| Đếm dòng bằng `bytes.count(b'\n')` | `xanderios` đếm thô 702.287 nhưng thật **33.246** — sai 21 lần | luôn dùng `csv.reader` |
| Đo trên mẫu 100 dòng | `data_jobs` mẫu cho 89%, quét toàn bộ **85,10%**; `xanderios.applies` mẫu 26%, thật **48,84%** | quét toàn bộ file |
| Pipe heredoc vào `python -` | mở REPL, test "fail" là dương tính giả | ghi script ra `.py` rồi chạy |

---

## 9. Bước tiếp theo, theo thứ tự ưu tiên

| Ưu tiên | Việc | Vì sao trước | Trạng thái |
|---|---|---|---|
| **1** | Dựng partition **G1 K=20** (21 client) + `hash % 21`, lưu ra file | đầu vào cho mọi thực nghiệm FL sau | ⬜ chưa |
| **2** | Dựng đồ thị P1 đầy đủ theo Bảng 6, có script tái lập | không có đồ thị thì không có kết quả | ⬜ chưa |
| **3** | Sửa lớp Skill: **bỏ `Skills.txt` 35-element**, dùng ESCO + O&ast;NET Technology | nếu bỏ qua, lớp kỹ năng vô dụng và hội đồng sẽ bắt | ⬜ chưa |
| **4** | Chạy lại toàn bộ thực nghiệm trên P1, báo cáo kèm CI bootstrap | 16 user → 213.793 user, CI sẽ hẹp lại thực chất | ⬜ chưa |
| **5** | Viết mục **Hạn chế** với 6 điều ở mục 7, nguyên văn | đây là phần quyết định điểm phản biện | ⬜ chưa |
| **6** | Thêm **item embedding riêng theo client** cho đuôi dài | 46,6% traffic là item độc quyền 1 bang → FedAvg một bảng chung hỏng đuôi dài | ⬜ chưa |
| **7** | (tuỳ chọn) Thử Zhaopin nếu xin được tài khoản Tianchi | **không đặt đường găng** | ⬜ chưa |

**Ba hướng đã bị số liệu bác bỏ — đừng thử lại:**

| Hướng | Số đo bác bỏ |
|---|---|
| Ghép CareerBuilder ⨝ `data_jobs` theo title | **86,92%** khớp là rác; trần đúng nghĩa **2,977%** |
| Ghép CareerBuilder ⨝ `arshkon` để lấy employer | chỉ **7,106%** app xác định được 1 công ty; **39,503%** mơ hồ (median 18 công ty/title) |
| Dùng nhóm 3 repo `job-postings-applications` | SHA-256 trùng **6/6** bảng; **60,94%** tên Faker; `score` decile cách đều |

---

## 10. Bằng chứng và tái lập

### 10.1 Phép đo t6 tự thực hiện (độc lập với t1–t5)

| File | Nội dung | Bytes |
|---|---|---|
| `_newdata_audit/t6_verify/t6_onet_skill_layers.json` | Bảng 9: `Skills.txt` 879 nghề × đủ 35/35 vs `Technology Skills.txt` 923 nghề / 8.775 công cụ | 835 |
| `_newdata_audit/t6_verify/t6_medajob_provenance.json` | **Nguồn gốc MEDAJob**: 3 tầng (tin / tương tác / hồ sơ) + độ phủ tương tác + độ lệch rating | 2.570 |
| `_newdata_audit/t6_verify/t6_doc_check.json` | Kết quả tự kiểm file báo cáo (mục 10.5) | 1.462 |
| `_newdata_audit/t6_verify/t6_soc_levels.json` | **Bảng 13**: hai cấp gộp mã SOC + cơ chế gộp + hệ quả trộn cấp | 1.696 |
| `_newdata_audit/t6_verify/t6_canonical.json` | **Ma trận 4 tổ hợp** (2 định nghĩa P1 × 2 cấp mã), tất cả nhất quán + tái hiện số sai của t5 | 4.106 |
| `_newdata_audit/t6_verify/t6_bang6.json` | **Số chuẩn của Bảng 6** sau khi sửa lỗi trộn cấp | 964 |
| `_newdata_audit/t6_verify/t6_graph_design_fixed.json` | Kết quả `t6_graph_design_fixed.py` (bản sửa tối thiểu của t5) | 1.314 |
| `_newdata_audit/t6_verify_soc_levels.py` | Script Bảng 13 | 5.150 |
| `_newdata_audit/t6_graph_design_fixed.py` | Bản sửa tối thiểu của `t5_graph_design.py` (chỉ đổi cấp mã) | 9.346 |
| `_newdata_audit/t6_canonical.py` | Script ma trận 4 tổ hợp | 9.848 |
| `_newdata_audit/t6_bang6.py` | Script số chuẩn Bảng 6 | 6.752 |
| `_newdata_audit/t6_verify_onet_skills.py` | Script Bảng 9 | 3.199 |
| `_newdata_audit/t6_probe_medajob_full.py` | Script **toàn bộ** số đo MEDAJob ở mục 1.3 và 3.3 | 7.774 |
| `_newdata_audit/t6_check_doc.py` | Script tự kiểm tài liệu (U+FFFD, số trong bảng, 6 điều mục 7) | 5.145 |
| `_newdata_audit/t6_probe_filters.py` | Đối chiếu 879 vs 923 vs 1.016 nghề giữa các bảng O\*NET | 1.279 |

Lệnh tái lập:

```powershell
cd E:\2026\DUT\DSS\SauGK\CuoiKi
$env:PYTHONUTF8='1'
python _newdata_audit\t6_verify_onet_skills.py     # -> t6_verify/t6_onet_skill_layers.json
python _newdata_audit\t6_probe_medajob_full.py     # -> t6_verify/t6_medajob_provenance.json
python _newdata_audit\t6_verify_soc_levels.py      # -> t6_verify/t6_soc_levels.json  (Bảng 13)
python _newdata_audit\p25_howmuch.py               # bootstrap CI của tuyên bố 92,9%
python _newdata_audit\t6_check_doc.py              # -> t6_verify/t6_doc_check.json, in PASS/FAIL
```

Ba script dưới đây đọc toàn bộ CareerBuilder (3,63 GB), chạy **~10–12 phút** mỗi script:

```powershell
python _newdata_audit\t6_graph_design_fixed.py     # -> t6_verify/t6_graph_design.json  (bản ĐÃ SỬA)
python _newdata_audit\t6_canonical.py              # -> t6_verify/t6_canonical.json     (4 tổ hợp)
python _newdata_audit\t6_bang6.py                  # -> t6_verify/t6_bang6.json         (Bảng 6)
```

### 10.2 Bảng 12 — Số liệu t1–t5 dùng trong tài liệu này

| Số liệu | Nguồn |
|---|---|
| MEDAJob 70/1.014/307/16 | `artifacts/medajob/meta.json` |
| 218 tham số/tương tác, CI [-300%, +450%], 3,62 tin/user, 0,28 bước nhảy | `_newdata_audit/p25_howmuch.py` |
| CareerBuilder 1.603.111 / 389.708 / 1.092.096 | `_newdata_audit/t5_verify/t5_matrix.json` |
| Mật độ, phân bố app/user, app/job | `t5_matrix.json`, `t4_verify/t4_careerbuilder_dist.json` |
| Đồ thị P1 (636.896 cạnh, 213.793 user, 127.784 job, **709** nghề, 8.316 skill) | `_newdata_audit/t6_verify/t6_bang6.json` |
| **98,97%** job map được có skill, **79,62%** user P1 có skill, **352.306** cạnh user–nghề | `t6_verify/t6_bang6.json`, `t6_canonical.json` |
| 21 client + hash đối chứng | `t5_verify/t5_clients_final.json` |
| JSD theo phương pháp t3 | `t5_verify/t5_jsd_t3method.json` |
| 46,6% / 60,2% / Jaccard 1,2% / 84,05% / 78,9% | `_newdata_audit/nonIID.json`, `geo.json` |
| G0 189 client (min 1 / median 11 / max 169.760; 145 <1.000; 128 <100) | `_newdata_audit/client_configs.json` |
| Join rate 3 mức + 86,92% rác + 2,977% + 13,3× | `t5_matrix.json`, `t4_verify/t4_join_semantic.json` |
| Employer mơ hồ 7,106% / 39,503% / median 18 / max 372 | `t4_verify/t4_employer_ambiguity.json` |
| License 4 bộ tương tác thật (nguyên văn) | `t5_verify/t5_license_real.json`, `cb_rules.txt`, `olx_wayback.html` |
| SHA-256 3 repo tổng hợp | `t5_verify/t5_synthetic_check.json` |
| ESCO 2.942 / 13.485 / 36,52 / không có `vi` | `t5_verify/t5_esco_and_graph2.json`, `t2_esco_*.json` |
| Bảng 13 (mục 10.3): cấp mã SOC đầy đủ 879/923 vs mã gốc 763/798; mean 35,41 vs 37,93; max 426 vs 594 | `_newdata_audit/t6_verify/t6_soc_levels.json` |
| Top 3 công cụ 859 / 813 / 784 nghề | `t6_verify/t6_onet_skill_layers.json` |
| Timing và RAM | `t5_verify/t5_olx_and_timing.json` |
| `data_jobs` 785.741 / 85,10% / 139.984 cty | `t4_verify/t4_lukebarousse.json` |

### 10.3 Bảng 13 — Chênh lệch 879 / 798 / 763 nghề: do CẤP GỘP mã SOC, không phải mâu thuẫn

Hai lần đo ra số khác nhau vì **gộp ở hai cấp mã nghề khác nhau**, không phải vì lọc dữ liệu.

| Cách gộp mã `O*NET-SOC Code` | `Skills.txt`: số nghề | `Technology Skills.txt`: số nghề / mean / max | Ai đo |
|---|---|---|---|
| **Mã ĐẦY ĐỦ** (giữ hậu tố `.00`, `.01`, `.03`…) | **879** | **923** / **35,41** / **426** | [ĐO t6] |
| **Mã GỐC 6 ký tự** (cắt `[:7]`, bỏ hậu tố) | **763** | **798** / **37,93** / **594** | [ĐO t5] |

Ba phép đo chứng minh cơ chế:

| Kiểm tra | Kết quả [ĐO t6] |
|---|---|
| Mọi mã O\*NET trong cả 4 bảng đều **có** hậu tố `.xx` | `Occupation Data` 1.016/1.016 · `Alternate Titles` 1.016/1.016 · `Skills.txt` 879/879 · `Technology Skills.txt` 923/923 |
| Số nhóm mã gốc | `Skills.txt` **763** · `Technology Skills.txt` **798** · `Alternate Titles` **867** |
| Nhóm mã gốc chứa >1 mã chi tiết | **67 / 798 = 8,4%** |
| Số mã chi tiết bị gộp vào nhóm gốc | **125** → 923 − 125 = **798** |

**Cơ chế:** cắt `[:7]` biến `11-1011` thành khoá chung cho cả `11-1011.00` (49 công cụ) và `11-1011.03` (21 công cụ). Hai mã chi tiết bị **gộp làm một**, nên:

- **số nghề GIẢM** (923 → 798),
- **số công cụ mỗi nghề TĂNG** ở mean và max, vì tập hợp là **union** của hai nghề (57 công cụ, lớn hơn 49 và 21).

Ví dụ kiểm chứng được: nhóm `11-1011` → union **57** công cụ so với 49 và 21 của từng nghề riêng.

> **Ghi chú bắt buộc cho người làm sau:** mean/max khác nhau giữa hai lần đo là do **cấp gộp SOC**, không phải lỗi dữ liệu. Phải **khai báo dùng cấp nào** và dùng **nhất quán một cấp** trong toàn pipeline.

### 10.3b Bảng 14 — Một điểm KHÔNG nhất quán trong pipeline t5 phát hiện khi kiểm lại, đã sửa

Kiểm script `t5_graph_design.py` và `t4_onet_coverage.py` cho thấy **nút Occupation và cạnh skill dùng hai cấp mã khác nhau**:

| Chỗ trong pipeline | Cấp mã dùng | Dòng |
|---|---|---|
| Nút Occupation (`p1_socs`, lấy từ `title2soc`) | mã **đầy đủ** (có `.xx`) | `t5_graph_design.py` dòng 73, 83, 181 |
| Cạnh `Job–Skill` / nút Skill (`skills_per_soc`, `tech_per_soc`) | mã **gốc** `[:7]` | dòng 94, 101, 134, 168, 182–194 |

Hệ quả định lượng — đo trên toàn bộ 923 mã nghề chi tiết (`t6_verify/t6_soc_levels.json`):

| Cách dùng cấp mã | Mã nghề | Tập skill **phân biệt** | Mã **trùng** tập skill với mã khác |
|---|---|---|---|
| Nút = mã đầy đủ, **skill tra mã gốc** (bản t5 — TRỘN) | 923 | **792** | **203** |
| Nút = mã đầy đủ, **skill tra mã đầy đủ** (nhất quán) | 923 | **916** | **13** |

Nghĩa là ở bản trộn, **203 nút Occupation khác nhau chia sẻ y nguyên tập kỹ năng** với nút khác — làm mất phân biệt giữa chúng. Dùng nhất quán thì chỉ còn **13** mã trùng.

Ảnh hưởng tới từng con số đã báo — **đã đo lại, không suy đoán**. Script `t6_canonical.py`, bằng chứng `t6_verify/t6_canonical.json`:

| Số đã báo | Trạng thái | Số đúng sau khi sửa |
|---|---|---|
| **636.896** cạnh `User–Job` | ✅ **KHÔNG đổi** | 636.896 (chỉ phụ thuộc `apps.tsv` + ánh xạ title → nghề) |
| **213.793** user / **127.784** job | ✅ **KHÔNG đổi** | 213.793 / 127.784 |
| **8.316** nút Skill | ✅ **KHÔNG đổi** | 8.316 |
| **832** nút Occupation | ❌ **SAI** | **709** |
| **47.567** cạnh `Job–Skill` | ❌ **SAI, và sai cả nhãn** | **28.416** cạnh **Occupation–Skill**; phồng **67,4%** |
| **343.401** cạnh `User–Occupation` | ❌ **SAI** | **352.306** |
| **93,07%** job có skill | ❌ **SAI** (đo trên cấp gốc nhưng lọc theo 35 element) | **98,97%** (127.784 / 129.120) |
| **77,86%** user có skill | ❌ **SAI** | **79,62%** (170.227 / 213.793) |
| **40,044%** app map được nghề | ✅ **ĐÚNG** | 641.952 / 1.603.111 (không lọc skill) |
| **37,322%** app có skill | ❌ **SAI** | **39,729%** (636.896 / 1.603.111) |

**Vì sao 47.567 phồng tới 67,4%:** `sum(len(tech.get(s[:7])) for s in p1_socs)` cộng dồn qua **832 mã đầy đủ**, nhưng mỗi lần tra lại bằng khoá **gốc** — nên một nhóm mã bị cộng lặp đúng bằng số mã chi tiết trong nhóm.

Kiểm chứng trên một nhóm cụ thể (nhóm `11-1011`):

| Cách tính | Số cạnh đếm được |
|---|---|
| Code t5 (trộn): cộng qua 2 mã chi tiết, mỗi mã tra ra cùng 1 tập | **114** |
| Đúng (gốc): cộng 1 lần cho nhóm | **57** |
| Phồng ở nhóm này | **100,0%** |

**Hai định nghĩa P1 khác nhau — đây là nguồn gốc của bảng số lẫn lộn trong bản trước:**

| Script | P1 lọc theo | Cạnh User–Job | User | Nghề (cấp gốc) |
|---|---|---|---|---|
| `t5_graph_design.py` | nghề có ≥1 trong **35 Skills.txt** | 598.307 | 207.672 | 683 |
| `t5_esco_graph2.py` | nghề có ≥1 **Technology Skill** | **636.896** | **213.793** | 709 |

Bản trước của tài liệu này **trộn hai script**: lấy 636.896/213.793 của script thứ hai nhưng lấy 832/47.567 (số sai) và 93,07%/77,86% của script thứ nhất. Đó là lý do các số không khớp nhau. Nay đã chốt **một cấu hình duy nhất** (Bảng 6): cấp gốc + Technology Skills, tức `t5_esco_graph2.py` sau khi sửa.

**Cách sửa đã áp dụng — chọn MỘT cấp và dùng khắp nơi:**

| Phương án | Nút Occupation | Cạnh skill | Số nút nghề | Nút Skill | job/nghề | Ghi chú |
|---|---|---|---|---|---|---|
| **A — ĐÃ CHỌN** | mã **gốc** 6 ký tự | `[:7]` | **709** | **8.316** | **180,2** | nhất quán, phân bố đều hơn |
| B | mã **đầy đủ** | mã **đầy đủ** | 814 | 8.256 | 148,2 | chia quá nhỏ, ít nút Skill hơn |

Lý do chọn A (đo được, không suy đoán):

1. **Cấp gốc phân bố đều hơn:** 180,2 job/nghề so với 148,2 — nút Occupation dày hơn, embedding học được.
2. **Giữ nhiều nút Skill hơn:** 8.316 so với 8.256.
3. **Khớp thực hành tuyển dụng và crosswalk ESCO/ISCO-08**, vốn dùng SOC 6 ký tự.
4. `jobs.tsv` của CareerBuilder **không có cột mã nghề nào** (11 cột: JobID, WindowID, Title, Description, Requirements, City, State, Country, Zip5, StartDate, EndDate), nên mọi ánh xạ phải qua **tên nghề** rồi cắt về mã gốc.

**Đã sửa trong code:** `_newdata_audit/t6_graph_design_fixed.py` (bản sửa tối thiểu của `t5_graph_design.py`) và cấu hình chuẩn trong `t6_bang6.py`. Script gốc `t5_graph_design.py` **giữ nguyên** để đối chiếu lịch sử, không ghi đè bằng chứng cũ.

*(Ba suy đoán của tôi đã bị số liệu bác bỏ, ghi lại: (a) "t5 lọc theo nghề có trong CareerBuilder" — sai, t5 chỉ cắt `[:7]`; (b) "các con số cạnh vẫn đúng" — sai, 47.567 và 343.401 đều sai; (c) "832 là số đúng, chỉ cần ghi cảnh báo" — sai, phải sửa thành 709.)*

### 10.4 Bảng 15 — Lỗi trộn cấp SOC: đã sửa, ghi lại để người sau không lặp

Đây là **lỗi thật trong code**, không phải chuyện nhỏ. Ghi lại đầy đủ.

| | |
|---|---|
| **Triệu chứng** | `47.567` cạnh Job–Skill và `832` nút Occupation không tái lập được ở **bất kỳ** cấp mã nào khi tính nhất quán |
| **Nguyên nhân** | `p1_socs` giữ mã **đầy đủ** (`11-1011.00`) nhưng `sum(len(tech.get(s[:7])))` tra bằng mã **gốc** (`11-1011`) → một nhóm mã bị cộng lặp |
| **Vị trí** | `t5_graph_design.py` dòng 94, 101 (tra skill bằng gốc) vs dòng 181 (`p1_socs` lấy mã đầy đủ); `t5_esco_graph2.py` dòng 144 vs 169 |
| **Mức phồng** | cạnh Occupation–Skill phồng **67,4%** (28.416 → 47.567); nút Occupation 832 thay vì **709** |
| **Cách phát hiện** | đối chiếu chéo: cùng một tập nghề nhưng số cạnh khác nhau giữa hai lần tính; rồi kiểm nhóm `11-1011` có 2 mã chi tiết cho ra 114 thay vì 57 |
| **Cách sửa** | gom về mã gốc **ngay tại nguồn**: `p1_socs = {s[:7] for _,_,s in p1}` rồi tra `tech[s]`, không tra `tech[s[:7]]` |
| **Đã sửa ở đâu** | `_newdata_audit/t6_graph_design_fixed.py` (bản sửa tối thiểu) và `t6_bang6.py` (cấu hình chuẩn) |
| **Phòng tái diễn** | nguyên tắc: **một cấp mã duy nhất** cho cả nút lẫn cạnh; nếu đổi cấp thì đổi ở chỗ **đọc dữ liệu**, không đổi ở chỗ **tra cứu** |

**Bài học phương pháp:** lỗi này không làm chương trình báo sai (không exception, không cảnh báo), và các con số vẫn "hợp lý" — nên nó chỉ lộ ra khi **đối chiếu hai cách tính độc lập**. Nếu chỉ chạy một lần rồi tin, lỗi sẽ vào thẳng báo cáo.

### 10.5 Bảng 16 — Kết quả tự kiểm tài liệu này

Chạy `t6_check_doc.py`, kết quả:

| Tiêu chí | Cách kiểm | Kết quả |
|---|---|---|
| Không có ký tự hỏng U+FFFD | quét từng dòng | **0 dòng** |
| File giải mã UTF-8 hợp lệ | `raw.decode("utf-8")` | **hợp lệ** |
| Mọi số trong văn xuôi có trong bảng | tách bảng vs văn xuôi, so từng token số | **0 số không truy được** |
| Đủ 6 điều ở mục 7 | đếm mục `^\d\.` trong §7 | **6/6** |
| Câu bắt buộc ở phần mở đầu | so khớp chuỗi | **có** |
| Đủ 10 mục cấu trúc | so khớp heading | **10/10** |

Bốn loại token được phân loại riêng thay vì tính là "số liệu": tham chiếu mục (`1.1`, `4.3`… — đối chiếu heading có thật), mã chuẩn (`RFC 2606`), năm (`2022`), và **mã nghề SOC** (`11-1011`, `1011.00`) / tên tài khoản thử nghiệm.

### 10.6 Bảng 17 — Những số "chưa xác minh" — ghi đúng trạng thái

| Số | Trạng thái | Vì sao |
|---|---|---|
| Số dòng `jobs/job_skills.csv` của `arshkon` | **chưa xác minh** (mức C) | Kaggle chặn UA + reCAPTCHA; không có mirror HF chứa bảng skills |
| Toàn bộ schema Zhaopin/Tianchi 31623 | **chưa xác minh** (mức C) | trang SPA trả shell 4.085 ký tự; cần tài khoản + verify sinh viên |
| License Zhaopin | **chưa đọc được** | không đọc được văn bản từ nguồn, giữ ở mức [TL] |
| Schema `asaniczka` cột skill | **chưa xác minh** | 6,19 GB > hạn mức; endpoint download 404 không auth |
| `kshitizregmi` số dòng | **chưa xác minh** | chỉ đọc được file list, không tải |

Xem thêm Bảng 11b (mục 7) về hai con số JSD đã bị loại.
