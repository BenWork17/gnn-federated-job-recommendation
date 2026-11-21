# Kiểm chứng thực nghiệm top ứng viên theo 5 yêu cầu cứng (t4)

**Người thực hiện:** dataset-verifier (task t4) · **Ngày đo:** 2026-11-08 (Asia/Saigon)
**Máy:** ổ E:, Python 3.13 + urllib (curl/Invoke-WebRequest hỏng — chỉ Python tải được, đã đính chính ở t1).

## 0. Cách đọc tài liệu này

Mọi con số dưới đây đều kèm **nhãn mức xác minh** và **lệnh tái lập**:

| Nhãn | Nghĩa |
|---|---|
| **[ĐO]** | Tôi trực tiếp tải/đọc dữ liệu thật trên máy này, có script + JSON bằng chứng trong `_newdata_audit/t4_verify/` |
| **[ĐO-MẪU]** | Đo trên mẫu, có ghi rõ cách lấy mẫu và n |
| **[TL]** | Suy từ tài liệu chính thức của nhà phát hành (đã đọc văn bản, không đo được vì không tải được dữ liệu) |
| **[KHÔNG ĐO ĐƯỢC]** | Bị chặn (không có tài khoản/approval) — nói thẳng, không suy đoán |

**Nguyên tắc:** *không tin mô tả*. Chỗ nào tôi chỉ đọc được tài liệu thì ghi [TL], chỗ nào đo được thì ghi [ĐO] + đường dẫn JSON.

---

## 1. Kết luận chạy thẳng (TL;DR)

> ### ⚠️ RÀNG BUỘC CỦA CAPTAIN ĐÃ ĐƯỢC ĐO — VÀ KẾT QUẢ LÀM THAY ĐỔI KẾT LUẬN CỦA t1

Captain yêu cầu đo thật tỉ lệ join theo title giữa CareerBuilder và `data_jobs`, vì `data_jobs` chỉ có job data/analytics. **Đã đo. Giả định đó ĐÚNG (98,61% title của `data_jobs` chứa từ khoá data), nhưng hệ quả nghiêm trọng hơn ước lượng của captain.**

**Phát hiện quyết định:** join theo title giữa CareerBuilder và `data_jobs` cho ra **22,76% application khớp** — nghe có vẻ tốt. **Nhưng 86,92% trong số khớp đó là TRÙNG CHUỖI VÔ NGHĨA:**

| Title CareerBuilder khớp "chính xác" với `data_jobs` | Số application |
|---|---|
| `administrative assistant` | 35.604 |
| `customer service representative` | 25.179 |
| `receptionist` | 16.419 |
| `executive assistant` | 9.994 |
| `customer service` | 6.428 |
| `staff accountant` | 5.291 |

Đây là **thư ký, lễ tân, chăm sóc khách hàng** — không phải nghề data. `data_jobs` có chúng vì bộ này thu thập tin từ LinkedIn/Brazil/Indonesia với tiêu chí lỏng, nên vẫn lọt vài tin văn phòng; ngược lại CareerBuilder 2012 có 35.604 application vào `administrative assistant`.

→ **Nếu join xong rồi gán `job_skills` của `data_jobs` cho `administrative assistant`, ta đang gán "python, sql, tableau" cho tin thư ký.** Đây là **sai ngữ nghĩa**, không phải sai kỹ thuật. Không dùng được.

**Bảng kết luận theo yêu cầu (chi tiết ở §5):**

| | Phương án | (1) Tương tác thật | (2) Kỹ năng tin | (3) Hồ sơ UV | (4) Client FL | (5) License | Đạt |
|---|---|---|---|---|---|---|---|
| **1** | **CareerBuilder + kỹ năng MỨC NGHỀ (O\*NET/ESCO) + client theo bang (t3)** | ✅ 1.603.111 | ⚠️ 93,07% tin có ≥1 kỹ năng — nhưng **kỹ năng của NGHỀ, không của TIN** | ✅ có | ✅ 21 client, min 3.107 | ⚠️ **CareerBuilder cấm dùng sau cuộc thi** | **4/5** |
| **2** | CareerBuilder + join title→`arshkon` để lấy employer | ✅ | ✅ thật (job_skills) nhưng **chỉ 1,97%** có `skills_desc` | ✅ | ❌ **39,50% app mơ hồ** (median 18 công ty/title, max 372); chỉ 7,11% xác định được 1 công ty | ✅ CC BY-SA | **2,5/5** |
| **3** | CareerBuilder + join title→`data_jobs` | ✅ | ✅ **nhưng 86,92% khớp là sai ngữ nghĩa** | ✅ | ✅ 100% cột employer nhưng **gán sai** | ✅ Apache-2.0 | **LOẠI** |

**Khuyến nghị:** phương án **1** — nhưng **phải đổi cách trình bày**: gọi nó là *"gán kỹ năng ở mức nghề (occupation-level skill prior)"*, **không** gọi là *"mỗi tin có cột kỹ năng"*. Và **giấy phép CareerBuilder là rủi ro thật** (§6), không phải chi tiết nhỏ.

---

## 2. Ba ứng viên được chọn để kiểm chứng

Chọn từ kết quả t1/t2/t3, theo mức độ hứa hẹn:

| # | Ứng viên | Lý do chọn | Trạng thái tải |
|---|---|---|---|
| **A** | **Kaggle CareerBuilder 2012** (Kaggle Job Recommendation Challenge) | Bộ DUY NHẤT có tương tác user–job THẬT, đang có trên đĩa | ✅ trên đĩa (4 file, 3,63 GB) |
| **B** | **HF `lukebarousse/data_jobs`** | Nguồn duy nhất có **cả** employer (100%) **và** kỹ năng tường minh (85,10%, list Python thật) | ✅ đã tải toàn bộ 231.152.089 B |
| **C** | **`arshkon/linkedin-job-postings`** (qua mirror công khai `datastax/linkedin_job_listings`) | Phương án dự phòng của captain: LinkedIn **mọi ngành** (không chỉ data), có `job_skills.csv` | ⚠️ tải được mirror `postings.csv` (516 MB); **`jobs/job_skills.csv` bị chặn** (§4.3) |

Ngoài ra tôi đo thêm **hai bộ phụ trợ** quyết định tính khả thi: **O\*NET 29.3** (cho phương án mức nghề) và **Djinni** (nguồn hồ sơ ứng viên).

---

## 3. Đếm thật: user / job / tương tác + mật độ

### 3.1 Bảng tổng hợp

| Ứng viên | User | Job | Tương tác | Mật độ = I/(U×J) | % | Cách đo |
|---|---|---|---|---|---|---|
| **A. CareerBuilder** (mốc, đã đo ở t1 — **không đo lại**) | 321.235 | 365.668 | 1.603.111 | 1,365e-05 | 0,001365% | [ĐO] `csv.reader` trên `apps.tsv` |
| **B. `lukebarousse/data_jobs`** | **0** | **785.741** | **0** | **N/A** | N/A | [ĐO] quét toàn bộ 231 MB, `csv.reader` |
| **C. `arshkon` (mirror datastax)** | **0** | **123.849** | **0** | **N/A** | N/A | [ĐO] stream toàn bộ `postings.csv` |
| phụ: **Djinni job descriptions** | 0 | 141.897 | 0 | N/A | N/A | [ĐO] đọc parquet thật |
| phụ: **O\*NET 29.3** | — | 1.016 nghề | 0 | N/A | N/A | [ĐO] tải `db_29_3_text.zip` 13.301.357 B |

> **Sự thật phải nói thẳng: B và C có ZERO tương tác người dùng–tin.** Chúng là **bảng tin tuyển dụng**, không phải log hành vi. Cột `applies`/`views` của chúng là **đếm gộp theo tin**, không có user ID → không dựng được ma trận user×item.

### 3.2 Kiểm tra lại con số mốc CareerBuilder

Tôi **không đo lại** mốc của captain, nhưng đo **phân bố** mà task yêu cầu (mốc chưa có median/p90/max per-user). Kết quả **khớp đúng** con số mốc → xác nhận mốc đáng tin:

```powershell
python _newdata_audit/t4_cb_dist.py   # -> _newdata_audit/t4_verify/t4_careerbuilder_dist.json
```

| Chỉ số | Giá trị [ĐO] |
|---|---|
| Tổng application | 1.603.111 (Train 1.417.514 / Test 185.597) |
| User phân biệt | 321.235 |
| Job phân biệt (có app) | 365.668 |
| Mật độ (user/job active) | **0,001365%** ← khớp mốc captain |
| **App/user: min / median / p90 / p99 / max** | 1 / **2** / **10** / 44 / **2.473** |
| App/user trung bình | 4,9905 |
| **User có ≥5 app** | **87.760 (27,32%)** |
| **User có ≥10 app** | **36.387 (11,33%)** ← khớp mốc captain |
| **App/job: min / median / p90 / p99 / max** | 1 / **2** / **10** / 41 / **208** |
| **Job chỉ có đúng 1 app** | **158.829 (43,44%)** ← khớp mốc captain |
| Job có ≥10 app | 37.538 (10,27%) ← khớp mốc captain |

→ **Đối chiếu chéo 4 chỉ số với mốc của captain: KHỚP 100%.** Mốc đáng tin.

### 3.3 Phân bố của hai bộ không có tương tác

Với B và C, các chỉ số "app/user", "app/job", "% job có ≥1 kỹ năng" phải định nghĩa lại — tôi báo cáo cái đo được thay vì bịa:

| Chỉ số thay thế | B. `data_jobs` | C. `arshkon` |
|---|---|---|
| Số dòng | 785.741 [ĐO] | 123.849 [ĐO] |
| **Job/công ty: min / median / p90 / p99 / max** | 1 / **2** / 9 / 62 / **6.664** [ĐO] | — (đo sau, xem §4.3) |
| Công ty phân biệt | **139.984** [ĐO] | **15.850** company_id [ĐO] |
| % job nằm ở công ty có ≥20 tin | **53,09%** [ĐO] | — |
| % job nằm ở top-20 công ty lớn nhất | **5,53%** [ĐO] | — |

> **Ý nghĩa cho FL:** `data_jobs` có 139.984 công ty nhưng **median chỉ 2 tin/công ty** và **p90 = 9**. Nếu chia client theo công ty, **một nửa số client có ≤2 tin** → không huấn luyện được. Đây **đúng cùng loại vấn đề** mà t3 đã cảnh báo với 189 bang (min 1 / median 11). Phải gom nhóm, không chia thô.

---

## 4. Bốn phép đo quyết định (phần captain yêu cầu)

### 4.1 Join theo title: ba mức chặt/lỏng/không khớp [ĐO]

```powershell
python _newdata_audit\t4_join_rates.py        # -> t4_join_rates.json
python _newdata_audit\t4_join_semantic.py     # -> t4_join_semantic.json
```

**Chuẩn hoá đã dùng** (ghi rõ để tái lập): lowercase → NFKD → bỏ hậu tố giới tính `(m/f/d)`, `(m/w/d)`, `(gn)` → bỏ `(Remote)/(Hybrid)` → bỏ năm 19xx/20xx → `&`→`and` → bỏ ký tự đặc biệt → gộp khoảng trắng.

**Mức CHẶT** = title CB == title bộ kia sau chuẩn hoá. **Mức LỎNG** = bỏ phần sau `-` `/` `|` `,` và bỏ token cuối (seniority) rồi so. **Mức NHÓM** = title CB chứa **toàn bộ** token đặc trưng (≥4 ký tự) của một `job_title_short`.

| Mức | Nguồn | App khớp | **% app** | User | % user | Job | % job |
|---|---|---|---|---|---|---|---|
| **CHẶT** | `data_jobs` | 183.994 | **11,48%** | 91.956 | 28,63% | 38.382 | 10,50% |
| **LỎNG** | `data_jobs` | 180.888 | **11,28%** | 95.408 | — | 33.836 | 9,25% |
| **NHÓM** (`job_title_short`) | `data_jobs` | 4.708 | **0,29%** | 3.302 | — | 1.847 | 0,51% |
| **CHẶT** | `arshkon` | 306.092 | **19,09%** | 145.312 | — | 68.395 | 18,70% |
| **LỎNG** | `arshkon` | 91.090 | **5,68%** | 63.794 | — | 20.887 | 5,71% |
| **KHÔNG KHỚP** | cả hai | 799.517 | **49,87%** | — | — | 193.573 | 55,33% |

**Cộng dồn:** `data_jobs` phủ **23,06%** app (369.590) · `arshkon` phủ **24,78%** app (397.182) · **hợp của cả hai 47,83%** (766.772 app).

**Nhưng phép đo này chưa nói lên điều gì về tính đúng đắn.** Đó là lý do phép đo 4.2.

### 4.2 Kiểm tra tính hợp lệ ngữ nghĩa — phép đo phát hiện bẫy [ĐO]

```powershell
python _newdata_audit\t4_datajobs_scope.py    # -> t4_datajobs_scope_check.json
python _newdata_audit\t4_join_semantic.py     # -> t4_join_semantic.json
```

**Bước 1 — xác nhận `data_jobs` đúng là bộ data-only:**

| Kiểm tra | Kết quả [ĐO] |
|---|---|
| `job_title_short` — chỉ có **10** giá trị | Data Analyst 196.075 · Data Engineer 186.241 · Data Scientist 172.286 · Business Analyst 49.063 · Software Engineer 44.929 · Senior Data Engineer 44.563 · Senior Data Scientist 36.957 · Senior Data Analyst 29.216 · Machine Learning Engineer 14.080 · Cloud Engineer 12.331 |
| % title chứa từ khoá data | **98,61%** |
| Mẫu title thật | "Senior Clinical Data Engineer / Principal Clinical Data Engineer", "Data Engineer/Scientist/Analyst, Mid or Senior (m/f/x)", "GCP Data Engineer", "Stagiaire Data Analyst (H/F) - Lyon" |

→ **Giả định của captain ĐÚNG: `data_jobs` là bộ data/analytics.**

**Bước 2 — nhưng cái khớp lại là nghề khác.** Tách application theo 2 trục: *có từ khoá data trong title* × *có khớp title*.

| | `data_jobs` | `arshkon` |
|---|---|---|
| App **data + khớp** | 47.726 (**2,977%**) | 55.904 (3,487%) |
| App **data + KHÔNG khớp** | 67.413 (4,205%) | 59.235 (3,695%) |
| App **NON-data + khớp** | **317.156 (19,784%)** | 693.490 (43,26%) |
| App **non-data + không khớp** | 1.170.783 (73,03%) | 794.449 (49,56%) |
| **Tổng khớp** | 364.882 (22,76%) | 749.394 (46,75%) |
| **% trong số khớp là NON-data** | **86,92%** ⚠️ | 92,54% (nhưng LinkedIn đa ngành nên **có thể đúng**) |

**Top-15 title khớp theo số application (CareerBuilder ⨝ `data_jobs`):**
`administrative assistant` 35.604 · `customer service representative` 25.179 · `receptionist` 16.419 · `executive assistant` 9.994 · `customer service` 6.428 · `staff accountant` 5.291 · `project manager` 4.985 · `sales representative` 4.257 · `office assistant` 4.083 · `data entry clerk` 3.393 · `financial analyst` 3.289 · `recruiter` 3.144 · `operations manager` 2.958 · `inside sales representative` 2.900 · `business analyst` 2.858

> **Đây là toàn bộ bẫy, đo được bằng số:** trần lý thuyết captain ước là ~2,4% application. **Số thật của "data + khớp" là 2,977%** (47.726 app) — sát ước lượng đó. Phần còn lại (317.156 app) là **rác trùng chuỗi**. Nếu nhóm báo cáo "ghép được 22,76% application" mà không tách hai loại này, đó là **báo cáo sai sự thật**.
>
> **Kết luận: `data_jobs` KHÔNG dùng được để join theo title.** Chỉ 2,977% application là vừa data vừa khớp — quá nhỏ để làm dataset, và phần lớn 67.413 app data còn lại vẫn không khớp vì title 2012 khác title 2023.

### 4.3 `arshkon` có tốt hơn `data_jobs`? Có về độ phủ — nhưng hỏng cột employer [ĐO]

```powershell
python _newdata_audit\t4_arshkon_titles.py     # tải postings.csv (516 MB) qua mirror
python _newdata_audit\t4_employer_ambiguity.py # -> t4_employer_ambiguity.json
```

| Chỉ số | Giá trị [ĐO] |
|---|---|
| Số dòng `postings.csv` (mirror datastax) | **123.849** |
| Title phân biệt có company | 69.792 |
| `company_id` phân biệt | **15.850** |
| **`skills_desc` lấp đầy** | **2.439 / 123.849 = 1,969%** ⚠️ |
| App CB khớp → **đúng 1 công ty** | 113.910 (**7,106%**) — 75.354 user |
| App CB khớp → **NHIỀU công ty** | **633.280 (39,503%)** — 212.187 user |
| App không khớp | 855.921 (53,391%) |
| **Median số công ty / title khớp mơ hồ** | **18 công ty** |
| **Max số công ty cho 1 title** | **372 công ty** |

> **Cột (4) employer: `arshkon` KHÔNG cứu được.** Ghép theo title là quan hệ **nhiều–nhiều**: title `receptionist` của CareerBuilder khớp với **18 công ty khác nhau** (median), cá biệt 372. Ta **không biết** tin thư ký năm 2012 ở CareerBuilder là của công ty nào. Nếu gán bừa 1 trong 18 → **nhãn employer sai**, và **client FL sai** → toàn bộ thí nghiệm FL mất ý nghĩa.
>
> Chỉ **7,11%** application là xác định được **đúng một** công ty. Không đủ để chia client theo employer.

**Và `arshkon` không có kỹ năng dùng được:** `skills_desc` chỉ **1,97%**. Còn bảng `jobs/job_skills.csv` (3.506.651 B) + `mappings/skills.csv` (679 B) theo t1 là **chưa tải được**:
- Kaggle API không auth: **404** cho cả `datasets/view` và `datasets/download` của `arshkon/linkedin-job-postings` [ĐO]
- HuggingFace search `linkedin_job_postings`, `asaniczka`, `1-3m-linkedin`, `job_skills`: **không có mirror nào chứa bảng skills** [ĐO]

→ **Trạng thái `job_skills.csv` của arshkon: vẫn mức C — CHƯA XÁC MINH số dòng.** Không được dùng làm trụ chính cho cột (2).

### 4.4 Phương án không ghép: kỹ năng ở MỨC NGHỀ [ĐO]

```powershell
python _newdata_audit\t4_onet_coverage.py     # -> t4_onet_occupation_coverage.json
python _newdata_audit\t4_pipeline_option1.py  # -> t4_pipeline_option1.json
```

**Ý tưởng:** thay vì join job_id (bất khả thi — không có khoá chung), ánh xạ **title → nghề O\*NET** rồi lấy **ma trận nghề–kỹ năng**. Đây là ghép **ở mức NGHỀ**, không phải mức tin.

**Chỉ số từ điển O\*NET 29.3 (đã tải thật 13.301.357 B, 42 file):**
- 49.849 khoá title (Alternate Titles 56.558 + Occupation Data 1.016 + Short Titles) [ĐO]
- **763 nghề** có bảng `Skills.txt` (35 element/nghề) [ĐO]
- **798 nghề** có `Technology Skills` [ĐO]

**Phủ trên toàn bộ CareerBuilder:**

| Chỉ số | Giá trị [ĐO] |
|---|---|
| Job có application | 365.668 |
| Job map được → nghề O\*NET | **129.120 (35,31%)** |
| **Application map được** | **641.952 (40,04%)** |
| Job map được **và** nghề có ≥1 kỹ năng | 120.175 (**93,07%** của phần map được) |
| **Application có kỹ năng gán được** | **598.307 (37,32%)** |
| Application có tech skill | 636.896 (39,73%) |

→ **Độ phủ 37–40% application — CAO GẤP ~13 LẦN phương án join `data_jobs` đúng nghĩa (2,977%)** và **không cần khoá ngoại**.

**Pipeline đầy đủ của phương án 1** (client = top-20 bang + REST, cấu hình G1 K=20 của t3), 3 biến thể:

| | Tương tác | User | Job | Mật độ | **% job có kỹ năng** | Client | min / median / max |
|---|---|---|---|---|---|---|---|
| **P0** toàn bộ CB (mốc) | 1.603.111 | 321.235 | 365.668 | 0,001365% | 32,86% | 21 | 23.430 / 56.765 / 191.000 |
| **P1** chỉ giữ tin map được O\*NET | **641.952** | **214.832** | **129.120** | 0,002314% | **93,07%** | 21 | 9.420 / 22.825 / 77.589 |
| **P2** = P1 + user≥5 & job≥5 | **270.763** | **32.614** | **32.330** | 0,025679% | **93,46%** | 21 | **3.107 / 10.267 / 36.412** |

> **P1 là cấu hình nên dùng.** 641.952 tương tác thật, 214.832 user, 129.120 job, 21 client đều ≥9.420 tương tác (tỉ lệ max/min = 8,2× — chấp nhận được). P2 quá nhỏ (32.614 user) và mất 58% tương tác — chỉ dùng làm ablation.

---

## 5. Bảng so sánh 3 ứng viên × 6 tiêu chí (theo đúng yêu cầu task)

### 5.1 Bảng chính

| Tiêu chí | **A. CareerBuilder 2012** | **B. `lukebarousse/data_jobs`** | **C. `arshkon` LinkedIn** |
|---|---|---|---|
| **1. Số user / job / tương tác** | **321.235 / 365.668 / 1.603.111** [ĐO] | **0 / 785.741 / 0** [ĐO] | **0 / 123.849 / 0** [ĐO] |
| Cách đo | `csv.reader` toàn bộ `apps.tsv` 75 MB | quét toàn bộ 231.152.089 B | stream toàn bộ `postings.csv` 516 MB (mirror) |
| **2. Mật độ** | **1,365e-05** (0,001365%) [ĐO] | **N/A** — không có ma trận | **N/A** — không có ma trận |
| **3. Phân bố tương tác** | App/user: median **2**, p90 **10**, max **2.473**, **≥5: 87.760 (27,32%)**<br>App/job: median **2**, p90 **10**, max **208**, **1 app: 43,44%** [ĐO] | **Không áp dụng.** Thay thế: job/công ty median **2**, p90 **9**, max **6.664**, 139.984 công ty [ĐO] | **Không áp dụng.** 15.850 company_id; median 18 công ty/title (nghịch) [ĐO] |
| **4. % job có ≥1 kỹ năng trích được** | **0% có sẵn** → phải trích.<br>• Lexicon 60 term (tuỳ biến): **12,94%** [ĐO-MẪU n=43.678]<br>• Gazetteer O\*NET **strict** (4.066 cụm, đã loại nhiễu 1-token): **12,94%**, median 0 skill/tin [ĐO-MẪU n=43.678]<br>• **Gán mức NGHỀ (O\*NET): 93,07%** của phần map được, **= 37,32% tổng application** [ĐO] | **85,10%** (668.704/785.741), parse `ast.literal_eval` **0 lỗi** [ĐO toàn bộ]<br>TB **5,474** skill/tin, median **5**, max **53**, **252** skill phân biệt | `skills_desc` **1,97%** [ĐO]. Bảng `jobs/job_skills.csv` **CHƯA TẢI ĐƯỢC** → **chưa xác minh** (mức C) |
| **5. Cột phân vùng client?** | ❌ **KHÔNG** employer. Dùng **t3**: top-20 bang + REST = **21 client** (P1: min 9.420 / median 22.825 / max 77.589) [ĐO]<br>Đối chứng: `hash(user_id)%21` | ✅ **CÓ** `company_name` 100%, 139.984 công ty [ĐO]<br>❌ **Nhưng chia thô không dùng được**: median 2 tin/công ty, p50 client có ≤2 tin. Phải gom nhóm | ⚠️ **CÓ** `company_id` 15.850 [ĐO], nhưng **join title→employer mơ hồ**: chỉ **7,11%** app xác định được 1 công ty, **39,50%** mơ hồ (median 18, max 372) |
| **6. Giấy phép cho đồ án + công bố?** | ❌ **KHÔNG.** Rules chính thức (đã tải .docx 14.148 B, đọc nguyên văn): *"Entrants must use the Data provided to them **solely for purposes of the Competition**"* và *"promptly after the Competition ends, Entrants must **cease all use of the Data** … and **erase or otherwise destroy** all … computer entries"* [ĐO] | ✅ **Apache-2.0** (HF `cardData.license`, `gated: false`) [ĐO]. Cho phép dùng + công bố, phải ghi công | ✅ **CC BY-SA 4.0** (theo t1; mirror datastax **không khai báo** license riêng) [TL] |

### 5.2 Bảng "đạt / không đạt" theo 5 yêu cầu cứng

| Yêu cầu cứng | **A. CareerBuilder** | **B. `data_jobs`** | **C. `arshkon`** |
|---|---|---|---|
| **(1) Tương tác user–tin THẬT** | ✅ **ĐẠT** — 1.603.111 đơn ứng tuyển thật, 6 loại hành vi rõ ràng | ❌ **KHÔNG** — 0 cột user | ❌ **KHÔNG** — 0 cột user |
| **(2) Kỹ năng phía TIN** | ⚠️ **ĐẠT MỘT PHẦN** — không có cột sẵn; gán **mức nghề** phủ 93,07%/37,32% app; trích từ HTML chỉ ~12,94% | ✅ **ĐẠT** — `job_skills` list thật 85,10%, 0 lỗi parse | ⚠️ **KHÔNG KẾT LUẬN ĐƯỢC** — `skills_desc` 1,97%; bảng `job_skills` chưa tải được |
| **(3) Hồ sơ / kỹ năng ỨNG VIÊN** | ✅ **ĐẠT** — DegreeType 100%, Major 75,14%, TotalYearsExperience 96,36%, `user_history` 375.531 user / 657.226 JobTitle | ❌ **KHÔNG** | ❌ **KHÔNG** |
| **(4) Cột đơn vị tuyển dụng để chia client FL** | ❌ **KHÔNG có employer** → dùng **proxy bang** (t3, 21 client, đã đo) | ✅ **CÓ cột** nhưng ❌ **join sai ngữ nghĩa** (86,92% rác) và ❌ **chia thô hỏng** (median 2 tin/cty) | ⚠️ **CÓ cột** nhưng ❌ **join mơ hồ** — chỉ 7,11% app xác định được công ty |
| **(5) Giấy phép dùng học thuật + công bố** | ❌ **KHÔNG ĐẠT** — rules buộc **huỷ dữ liệu sau cuộc thi** | ✅ **ĐẠT** — Apache-2.0 | ✅ **ĐẠT** — CC BY-SA 4.0 |
| **Tổng** | **3,5/5** (1,2 một phần,3 đạt) | **2/5** (2,4-cột,5 đạt; hỏng 1,3) | **1/5** (chỉ 5 đạt; 4 mơ hồ) |

### 5.3 Bảng phương án GHÉP (theo yêu cầu mới của captain)

| Phương án ghép | % application join được | User còn lại | Job còn lại | Đủ 5 cột? | Giấy phép |
|---|---|---|---|---|---|
| **CareerBuilder ⨝ `data_jobs` (title)** | **2,977% đúng nghĩa** (47.726 app)<br>22,76% nếu tính cả rác trùng chuỗi (364.882) | 91.956 (nhưng chỉ ~40k thuộc phần đúng nghĩa) | 38.382 | ❌ **(4) sai ngữ nghĩa** — employer gán bừa | ⚠️ Apache-2.0 tốt, **nhưng CareerBuilder cấm** |
| **CareerBuilder ⨝ `arshkon` (title)** | **19,09% chặt** (306.092) / 24,78% cộng dồn / **nhưng chỉ 7,11% xác định được 1 công ty** | 145.312 (chặt) / 75.354 (employer xác định) | 68.395 | ❌ **(4) mơ hồ 39,50%**, **(2) chỉ 1,97% có skill** | ✅ CC BY-SA + ❌ CareerBuilder |
| **CareerBuilder + kỹ năng MỨC NGHỀ (O\*NET)** | **40,04% application map được nghề** (641.952); **37,32% có ≥1 kỹ năng** | **214.832** | **129.120** | ⚠️ (4) dùng **proxy bang** — khai báo là proxy; (2) kỹ năng **của nghề, không của tin** | ✅ O\*NET CC BY 4.0 + ❌ CareerBuilder |

---

## 6. Cảnh báo giấy phép — rủi ro lớn nhất, đã kiểm bằng văn bản gốc

Tôi tải và đọc **nguyên văn** file rules chính thức của cuộc thi (không suy từ mô tả):

```
https://storage.googleapis.com/kaggle-media/competitions/kaggle/3046/media/CB%20Kaggle%20Competition%20Official%20Rules%207%2012%202012.docx
→ 14.148 B, giải nén word/document.xml, 20.144 ký tự
```

**Ba câu trích nguyên văn [ĐO]:**

1. *"Entrants must use the Data provided to them **solely for purposes of the Competition**, including but not limited to preparing their Entries, developing and testing their algorithms…"*
2. *"Except as otherwise provided in these Official Rules, **promptly after the Competition ends**, Entrants must **cease all use of the Data** provided by Sponsor and **erase or otherwise destroy** all waste paper, fax paper, photocopy paper and other physical media and **computer entries or other electronic media**…"*
3. Danh sách dữ liệu (USER DATA / WORK HISTORY / JOB APPLICATIONS / JOB DETAILS) **không có** trường employer nào → xác nhận **thiếu employer là thuộc tính nguồn**, không phải lỗi crawl.

> **Đây là rủi ro (5) KHÔNG nhỏ.** Cuộc thi kết thúc **2012**; theo câu 2, về mặt chữ nghĩa **phải huỷ dữ liệu từ 2012**. Dùng nó cho đồ án 2026 và **công bố báo cáo** là **vùng xám pháp lý**, không phải "học thuật là được".
>
> **Cách xử lý trung thực (đề xuất):** khai báo rõ trong báo cáo rằng dữ liệu đến từ một cuộc thi Kaggle đã kết thúc và rules gốc hạn chế tái sử dụng; **không đính kèm dữ liệu thô** vào bài nộp; chỉ công bố **mã + số liệu tổng hợp**. Nếu hội đồng khắt khe, **phải có phương án B** — và phương án B tốt nhất là **XING 2017** (license cho học thuật rõ ràng hơn, nhưng cần approval — xem §7).

---

## 7. Ứng viên đã loại / không đo được (nói thẳng)

| Ứng viên | Trạng thái | Bằng chứng |
|---|---|---|
| **RecSys 2017 XING** | **KHÔNG TẢI ĐƯỢC — cổng đã chết** | `https://recsys.xing.com/` → **301 → https://www.xing.com/** (trang chủ mạng xã hội XING, không còn cổng challenge) [ĐO]. `recsys.xing.com/data` → **404**. Các endpoint `interactions.csv`, `datasets/recsys2017.zip` → **404**. Mirror `RecoHut-Datasets/xing` chỉ có **README.md 48 B + .gitignore** [ĐO]. HF search `xing`, `recsys2017`, `recsys-challenge-2017` → **không có dataset** [ĐO] |
| Số liệu XING 2017 (7.267.094 dương, 314.501.101 impression) | **Vẫn mức B — không đo lại được** | Đã thử: trang challenge 2017 **không nêu** con số nào (grep "314", "7.267", "1.497" → **0 hit**) [ĐO]. arXiv API: **0 kết quả** cho `"RecSys Challenge 2017"`. OpenAlex DOI `10.1145/3109859.3109954` trả abstract **không có bảng số liệu**; Semantic Scholar **CLOSED**, không có PDF. CEUR Vol-1892 `overview.pdf` tải được nhưng là **workshop summary**, không có Table 1 của Abel et al. |
| **Zhaopin/Tianchi 31623** | **Không lấy được schema** (giữ nguyên kết luận t1) | Trang trả **200** nhưng là SPA shell; API dataset không trả JSON [ĐO]. Cần tài khoản + verify sinh viên. **Không dùng làm điểm chặn** |
| **`asaniczka/1-3m-linkedin-jobs-and-skills-2024`** | **Không tải được** | Kaggle API không auth: `datasets/list`, `datasets/view`, `datasets/download` → **404** cả 3 [ĐO]. 6,19 GB > hạn mức 500 MB. HF search `asaniczka`, `linkedin-jobs-and-skills`, `1-3m-linkedin` → **0 kết quả** (không có mirror) [ĐO] |
| **`arshkon` bảng `job_skills.csv`** | **CHƯA XÁC MINH (mức C)** | Kaggle API 404; không có mirror HF chứa bảng skills [ĐO] |
| **`ravindrasinghana/job-description-dataset`** | **LOẠI — dữ liệu tổng hợp** | Theo t2: Company Size **5.412 giá trị/5.551 dòng**, BT Group→Gibraltar. Không đưa vào bảng xếp hạng |
| **Diễn biến mạng (đính chính kỹ thuật)** | Python `urllib` **tải được**; `curl`/`Invoke-WebRequest` hỏng | Đã tải thật: 231.152.089 B (`data_jobs`), 516 MB (`postings.csv`), 13.301.357 B (O\*NET), 145.859.589 B (Djinni jobs) [ĐO] |

---

## 8. Xếp hạng cuối + khuyến nghị

### 8.1 Xếp hạng theo mức đáp ứng 5 yêu cầu cứng

| Hạng | Phương án | Điểm | Vì sao |
|---|---|---|---|
| **🥇 PHƯƠNG ÁN 1** | **CareerBuilder + gán kỹ năng MỨC NGHỀ (O\*NET 29.3) + client theo bang (t3: top-20 + REST)** | **4/5** | Duy nhất có (1) tương tác thật **và** (3) hồ sơ ứng viên **và** (2) phủ kỹ năng 37,32% app **và** (4) 21 client đã đo. Chỉ hỏng (5) giấy phép |
| **🥈 PHƯƠNG ÁN 2** | CareerBuilder + join title→`arshkon` | **2,5/5** | Được (1),(3),(5); (2) chỉ 1,97%; (4) mơ hồ 39,50% |
| **🥉 PHƯƠNG ÁN 3** | `data_jobs` làm bộ chính (785.741 job, 139.984 công ty, Apache-2.0) | **2/5** | Được (2),(4-cột),(5); **mất hoàn toàn (1) và (3)**. Nếu dùng thì phải tự sinh tương tác → **quay lại đúng vấn đề MEDAJob** |
| **LOẠI** | CareerBuilder ⨝ `data_jobs` theo title | **0/5** | 86,92% khớp là sai ngữ nghĩa — gán skill data cho tin thư ký. **Không bảo vệ được** |

### 8.2 Khuyến nghị cụ thể, có thể hành động ngay

**(A) Chốt phương án 1 với cách trình bày trung thực:**

```
Node:  User  ← CareerBuilder users.tsv (389.708) + user_history (657.226 JobTitle)
       Job   ← CareerBuilder jobs.tsv (1.092.096) — lọc còn 129.120 tin map được nghề
       Skill ← O*NET 29.3 (35 element/nghề + 32.681 Technology Skills, CC BY 4.0)
               + ESCO v1.2.1 làm taxonomy chuẩn hoá (13.485 skill, 2.942 nghề)
       Occupation ← O*NET 1.016 nghề / ESCO 2.942 nghề, crosswalk chính thức

Cạnh:  User–Job        : 641.952 application THẬT (P1) — đây là trụ của đồ án
       Job–Occupation   : từ title, phủ 35,31% job (129.120)
       Occupation–Skill : O*NET Skills.txt (763 nghề) + Technology Skills (798 nghề)
       User–Occupation  : từ user_history.JobTitle (375.531 user có lịch sử)
```

**Câu phải nói với hội đồng (nguyên văn được):**
> *"Bộ dữ liệu không có cột kỹ năng ở mức tin. Chúng tôi gán kỹ năng ở **mức nghề**: ánh xạ tiêu đề tin → nghề O\*NET (phủ 35,31% số tin, 40,04% số lượt ứng tuyển), rồi dùng ma trận nghề–kỹ năng của O\*NET. Vì vậy kỹ năng là **prior của nghề**, không phải yêu cầu cụ thể của từng tin. Chúng tôi báo cáo rõ giới hạn này và không trình bày nó như cột kỹ năng của tin."*

**(B) Về cột (4) employer — chốt dùng proxy địa lý, đã có số:**
- 21 client (top-20 bang + REST), P1: min **9.420** / median **22.825** / max **77.589** application
- Đối chứng bắt buộc: `hash(user_id) % 21`
- Báo cáo JSD **trên `job_id`/`title` so với nền hash cùng 21 client** — **tuyệt đối không** báo JSD trên nhóm ngành (chỉ 0,0007–0,0027 ≈ IID, t3 đã cảnh báo)

**(C) Về giấy phép — phải xử lý trước khi nộp:**
- Rủi ro thật, đã trích nguyên văn §6. Đề xuất: **không đính kèm dữ liệu thô**, chỉ công bố mã + số liệu tổng hợp, và **ghi rõ nguồn + điều kiện hạn chế** trong phần "Hạn chế".
- Nếu cần license sạch 100%: **XING 2017 là ứng viên đúng ngữ nghĩa nhất nhưng cổng đã chết** — không thể lấy trong thời gian đồ án. **Đừng đặt đường găng vào đây.**

### 8.3 Điều KHÔNG nên làm (đã đo, đừng thử lại)

1. ❌ **Join CareerBuilder với `data_jobs` theo title** — 86,92% rác. Đã đo, đã bác.
2. ❌ **Chia client thô theo employer trong `data_jobs`** — median 2 tin/công ty, nửa số client ≤2 tin.
3. ❌ **Dùng `arshkon` làm nguồn skill** — `skills_desc` 1,97%; bảng `job_skills` không tải được.
4. ❌ **Chia client thô theo 189 bang** — 128 client <100 app (t3).
5. ❌ **Đếm dòng bằng `bytes.count(b'\n')`** — đã gây sai 21 lần ở xanderios (t1).
6. ❌ **Tin mẫu 100 dòng** — `data_jobs` mẫu cho 89%, thật 85,10% (t1); `xanderios` `applies` mẫu 26%, thật 48,84%.

---

## 9. Artifact tái lập được

Tất cả trong `_newdata_audit/t4_verify/`:

| File | Nội dung | Bytes |
|---|---|---|
| `t4_lukebarousse.json` | Quét toàn bộ 785.741 dòng: fill rate 17 cột, 139.984 công ty, phân bố job/công ty, 252 skill, top-20 | 4.586 |
| `t4_careerbuilder_dist.json` | Phân bố app/user & app/job (median/p90/p99/max), đối chiếu mốc captain | 1.401 |
| `t4_join_rates.json` | Tỉ lệ join 3 mức × 2 nguồn, theo app/user/job | 2.782 |
| `t4_join_semantic.json` | **Phép đo phát hiện bẫy**: 4 ô data-kw × matched, top-15 title rác | 3.466 |
| `t4_datajobs_scope_check.json` | Xác nhận `data_jobs` data-only (98,61%), phân bố 10 `job_title_short` | 5.239 |
| `t4_employer_ambiguity.json` | **Employer mơ hồ**: 7,11% unique / 39,50% multi / median 18 công ty/title | 1.006 |
| `t4_onet_occupation_coverage.json` | Phủ mức nghề: 40,04% app map được, 37,32% có skill | 1.112 |
| `t4_pipeline_option1.json` | Pipeline P0/P1/P2 với 21 client, min/median/max | 2.039 |
| `t4_join_retention.json` | Hậu-join theo lớp A/B/C + lọc user≥K, job≥K | 2.188 |
| `t4_cb_skills_strict.json` | Gazetteer O\*NET strict: 12,94% tin có ≥1 skill (n=43.678) | 1.204 |
| `t4_licenses.json` | License 3 repo HF (`cardData`) + rules CareerBuilder nguyên văn | 6.113 |
| `t4_xing_probe.json`, `t4_xing_docs.json`, `t4_xing_portal.json`, `t4_xing_papers.json`, `t4_xing_paper_lookup.json` | Bằng chứng cổng XING đã chết + nỗ lực tìm số liệu | — |
| `cb_rules.docx` / `cb_rules.txt` | Rules chính thức CareerBuilder (nguồn cho §6) | 14.148 / 20.144 |
| `c2017_home.html`, `c2016_TrainingDataset.md`, `recohut_xing_README.md` | Trang tài liệu XING đã đọc | — |

**Script tái lập** (đều là `.py` ghi ra file rồi chạy — **không pipe heredoc vào `python -`**, đó là bẫy REPL đã ghi ở t1):

```powershell
python _newdata_audit\t4_lukebarousse.py          # quét toàn bộ data_jobs
python _newdata_audit\t4_cb_dist.py               # phân bố CareerBuilder
python _newdata_audit\t4_join_rates.py            # tỉ lệ join 3 mức
python _newdata_audit\t4_join_semantic.py         # kiểm tra ngữ nghĩa (BẪY)
python _newdata_audit\t4_datajobs_scope.py        # xác nhận data_jobs data-only
python _newdata_audit\t4_employer_ambiguity.py    # employer mơ hồ
python _newdata_audit\t4_onet_coverage.py         # phủ mức nghề
python _newdata_audit\t4_pipeline_option1.py      # pipeline P0/P1/P2
python _newdata_audit\t4_licenses.py              # license + rules gốc
```

**Dọn dẹp:** đã xoá `postings_raw.csv` (516 MB) sau khi rút 5 cột. Còn `data_jobs.csv` 220 MB, `jobs.parquet` 139 MB, `db_29_3_text.zip` 12,7 MB — xoá được sau khi nhóm dùng xong (`Remove-Item _newdata_audit\t4_verify\*`).
