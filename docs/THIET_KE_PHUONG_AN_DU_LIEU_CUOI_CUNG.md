# Thiết kế phương án dữ liệu cuối cùng (t5)

**Người thực hiện:** dataset-verifier (task t5) · **Ngày đo:** 2026-11-08 (Asia/Saigon)
**Tiền đề:** t1 (khảo sát 12 bộ) + t2 (taxonomy) + t3 (chia client) + t4 (kiểm chứng)
**Bổ sung của t5:** (a) đo **phía USER** mà t4 chưa đo, (b) phát hiện **lớp Skill của O\*NET vô dụng** và sửa, (c) kiểm license **OLX bằng văn bản gốc qua Wayback**, (d) tự kiểm chứng nhóm 3 repo tổng hợp bằng **SHA-256**, (e) đo chi phí kỹ thuật thật.

---

## 0. KẾT LUẬN CUỐI CÙNG (đọc mục này là đủ)

> ### Không tồn tại bộ dữ liệu công khai thoả đồng thời tương tác thật và giấy phép sạch.

Đây là kết luận của t5, **đã kiểm bằng văn bản license gốc của cả 4 bộ tương tác thật** trên toàn bộ danh sách khảo sát (§3). Không phải thất bại — đây là **kết quả có giá trị khoa học**, và nó quyết định hình dạng của đồ án.

**Hệ quả bắt buộc:** đề tài phải chọn giữa **"trung thực về dữ liệu"** và **"đủ 5 cột"**. Không thể có cả hai. t5 chốt:

| | Phương án | Vì sao |
|---|---|---|
| **KHUYẾN NGHỊ CHÍNH** | **CareerBuilder + O\*NET (mức nghề) + client địa lý t3**, **không công bố dữ liệu thô**, chỉ công bố **mã + số liệu tổng hợp**, **có phương án B hợp pháp 100%** để trình bày nếu bị chất vấn | Không có bộ nào thay thế được về mặt định lượng (§3.1); rủi ro pháp lý **đã đánh giá và giảm thiểu được** (§6); kỹ thuật đã đo xong (§5) |
| **DỰ PHÒNG** | **MEDAJob (sạch, của môn học) làm dữ liệu TRÌNH BÀY, CareerBuilder chỉ làm kiểm tra độ bền không công bố** | License sạch 100%, nhưng 307 tương tác → **không thể** là kết quả chính |

> **Và phải nói dứt khoát với hội đồng:** yêu cầu (4) "cột đơn vị tuyển dụng để chia client FL" **không đạt được trên bất kỳ dữ liệu công khai nào**. Đây không phải hạn chế của nhóm — đây là **thuộc tính của toàn bộ dữ liệu public hiện có**. Bằng chứng: mọi bộ có employer thì không có tương tác (t1); bộ duy nhất vừa có employer vừa thử join được thì employer **mơ hồ 39,50%** (t4); và **chính tài liệu FL-recsys cũng không có benchmark nào có cột tổ chức** (t3, 21 tài liệu).

---

## 1. PHÁT HIỆN MỚI CỦA t5 LÀM THAY ĐỔI THIẾT KẾ: lớp Skill của O\*NET VÔ DỤNG

t4 đề xuất "gán kỹ năng mức nghề bằng O\*NET". t5 kiểm lại và phát hiện **cách làm đó sai về mặt đồ thị**:

```powershell
python _newdata_audit\t5_skill_discriminative.py   # -> t5_verify/t5_skill_discriminative.json
```

| Kiểm tra | Kết quả [ĐO] |
|---|---|
| Số kỹ năng trong `Skills.txt` | **35** (10 Basic 2.A + 25 Cross-Functional 2.B) |
| Số nghề có bảng Skills | 763 |
| **Số kỹ năng mỗi nghề: min / max / mean** | **35 / 35 / 35,00** |
| **Số nghề được gán ĐỦ cả 35 kỹ năng** | **763/763 = 100,00%** |

> **Nghĩa là: mọi nghề đều có đủ 35 kỹ năng.** Đồ thị `Occupation–Skill` trở thành **bipartite đầy đủ**. Nút Skill **không mang thông tin nào** (entropy = 0), và GNN lan truyền qua nó chỉ như một hằng số.
>
> Nếu nhóm làm theo t4 mà không kiểm bước này, mô hình sẽ có một lớp "kỹ năng" **trông rất đẹp trong hình vẽ nhưng vô dụng** — đúng loại lỗi khó phát hiện khi bảo vệ.

**Sửa lại — dùng lớp PHÂN BIỆT ĐƯỢC:**

| Lớp Skill | Nguồn | Số nút | Cạnh/nghề | Phân biệt? |
|---|---|---|---|---|
| ❌ `Skills.txt` (35) | O\*NET | 35 | **35,00 (cố định)** | **KHÔNG — loại** |
| ✅ **`Technology Skills.txt`** | O\*NET 29.3 | **8.775** công nghệ | **min 1 / mean 37,93 / max 594** | **CÓ** |
| ✅ **ESCO `occupationSkillRelations`** | ESCO v1.2.1 | **13.485** skill | **essential 20,28 + optional 16,24 = 36,52** (min 5, max 70) | **CÓ** (0,27% mật độ) |

**ESCO đo lại bằng API ở t5** (t2 ước ~37,88; t5 đo thật trên 100 nghề = **36,52** — khớp):

```powershell
python _newdata_audit\t5_esco_graph2.py   # -> t5_verify/t5_esco_and_graph2.json
```
- 100 nghề lấy được (offset 0–100 đều OK; t2 ghi "chặn ở 500" là **chặn phân trang lớn**, không phải chặn hoàn toàn)
- essential **20,28**/nghề (min **5**, max **70**) · optional **16,24**/nghề (min **0**, max **66**)
- **36,52 cạnh/nghề trên 13.485 skill = mật độ 0,27%** → phân biệt rất mạnh

> **Chốt thiết kế:** dùng **ESCO làm lớp Skill chuẩn** (13.485 nút, có phân cấp, có ma trận nghề–kỹ năng thật), **O\*NET Technology Skills làm lớp bổ sung** cho nghề CNTT (8.316 nút cụ thể như `Python`, `SAP`, `AutoCAD`). **KHÔNG dùng `Skills.txt` 35-element.**

---

## 2. PHÍA USER — t4 CHƯA ĐO, t5 ĐÃ ĐO

Yêu cầu (3) "hồ sơ/kỹ năng phía ứng viên". t4 chỉ đo **hồ sơ cấu trúc**; t5 đo **kỹ năng** qua `user_history.JobTitle → occupation → skill`:

```powershell
python _newdata_audit\t5_graph_design.py   # -> t5_verify/t5_graph_design.json
```

| Chỉ số | Giá trị [ĐO] |
|---|---|
| `user_history.tsv` dòng | 1.753.901 |
| User có lịch sử chức danh | **375.531** |
| Chức danh lịch sử map được → nghề O\*NET | **758.080 / 1.753.901 = 43,22%** |
| User có ≥1 nghề | 309.992 |
| **User có ≥1 kỹ năng** (toàn bộ) | **300.580 (80,04%)** |
| User trong đồ thị P1 | 207.672 |
| **User trong P1 có ≥1 kỹ năng** | **161.702 (77,86%)** |
| Cạnh `User–Occupation` | 343.401 |

> **Đây là điểm mạnh thật của CareerBuilder mà t4 chưa khai thác: 77,86% user trong đồ thị có kỹ năng gán được.** Nhưng **phải nói thật**: kỹ năng này **suy qua nghề**, không phải ứng viên tự khai (CareerBuilder không có cột skill). Đây là **prior**, không phải ground truth.

---

## 3. LICENSE — HẠNG NHẤT. ĐÃ ĐỌC VĂN BẢN GỐC CỦA CẢ 4 BỘ TƯƠNG TÁC THẬT

Captain yêu cầu kiểm license thật của OLX, Zhaopin, Djinni. t5 đã làm, và **tự phát hiện sai lầm của chính mình ở t4**.

### 3.1 ⚠️ ĐÍNH CHÍNH KỸ THUẬT QUAN TRỌNG (t5 tự phát hiện)

Ở t4 tôi báo "Kaggle API trả 404 cho asaniczka/arshkon ⇒ không tải được". **Đó là kết luận SAI do lỗi đo.** t5 làm phép đối chứng:

```powershell
python _newdata_audit\t5_control.py   # -> t5_verify/t5_control.json
```

| URL | User-Agent Python | User-Agent trình duyệt |
|---|---|---|
| `kaggle.com/datasets/olxdatascience/olx-jobs-interactions` | **404** | **200** (nhưng là trang **reCAPTCHA**) |
| `kaggle.com/` (trang chủ) | **404** | — |
| `kaggle.com/api/v1/datasets/view/arshkon/...` | **404** | 200 (reCAPTCHA) |

→ **Kaggle chặn theo User-Agent, và khi vượt được UA thì chặn bằng reCAPTCHA.** Vậy:
- Kết luận "dataset bị xoá" ở t4: **SAI** — dataset vẫn tồn tại.
- Kết luận "không đọc được license qua Kaggle": **ĐÚNG**, nhưng lý do là **reCAPTCHA**, không phải 404.
- **Chưa bao giờ kiểm được** license OLX và arshkon qua Kaggle trực tiếp.

### 3.1b ĐÍNH CHÍNH THỨ HAI: JSD ở t3 và ở t5 KHÔNG cùng thước đo

Khi đo lại JSD trên cơ sở đồ thị mới, t5 tính ra **0,0087** trong khi t3 báo **0,8057** — chênh ~100 lần. **Không phải dữ liệu đổi, mà do hai định nghĩa khác nhau:**

| | Cách tính |
|---|---|
| **t3** (`p28_noniid.py` dòng 55–75) | JSD của **mỗi client vs PHÂN BỐ TOÀN CỤC**, rồi trung bình có trọng số |
| **t5** (bản đầu, `t5_clients_final.py`) | JSD **pairwise giữa các client với phân bố trung bình** (generalized JSD) |

→ **Hai đại lượng khác nhau, không được so sánh trực tiếp.** t5 đã **đo lại bằng đúng hàm `jsd` của t3** (chép nguyên văn) trên cơ sở `graph_final`: kết quả **0,7527 vs nền hash 0,4091** (§8). **Con số 0,0087 bị loại bỏ khỏi báo cáo.**

> **Bài học phương pháp:** trước khi so sánh hai lần đo của hai người, phải so **định nghĩa hàm**, không chỉ so con số. Đây đúng loại lỗi sẽ bị hội đồng bắt được nếu hai chương dùng hai cách tính JSD khác nhau.

### 3.2 OLX — license ĐỌC ĐƯỢC qua Wayback, và nó **KHÔNG** phải CC

```powershell
python _newdata_audit\t5_olx_timing.py   # -> t5_verify/t5_olx_and_timing.json
```
Snapshot: `web.archive.org/web/20221010125932/https://www.kaggle.com/datasets/olxdatascience/olx-jobs-interactions` (200, 33.736 ký tự).

**Trích NGUYÊN VĂN mục LICENSE [ĐO]:**

> *"The data may be re-used **solely as a base or supplement for conducting an analysis or research, incl. academic analysis or research, results of which may be further published**; nevertheless **under no circumstances the data set itself may be further published in parts or as a whole**;"*
>
> *"The data may be re-used **solely for non-commercial purposes**;"*
>
> *"The copy of the given publication and its source … **must be shared with Grupa OLX sp. z o.o.** via e-mail … as soon as the publication is confirmed;"*
>
> *"The permission to re-use the data within described scope applies worldwide, is royalty-free, non-exclusive, cannot be transferred to another party and **can be revoked** by Grupa OLX sp. z o.o. **at any time**;"*

**Phân loại của tôi: VÙNG XÁM (nghiêng an toàn hơn CareerBuilder).**
- ✅ Cho phép **nghiên cứu học thuật + công bố KẾT QUẢ** — rõ ràng, bằng văn bản.
- ✅ **Cấm tái phân phối dataset** → giống hệt ràng buộc CareerBuilder, nhưng **hợp pháp** (được phép dùng, chỉ cấm phát tán).
- ⚠️ **Bắt buộc gửi bản công bố cho OLX** trước/khi công bố.
- ⚠️ **Có thể bị thu hồi bất kỳ lúc nào** → rủi ro dài hạn.
- ❌ **Chỉ 4 cột** `user, item, event, timestamp` — **không có title, không có skill, không có employer, không có profile**. Tự nó **không dùng được** cho đề tài.

**Kết luận OLX: license TỐT HƠN CareerBuilder, nhưng dữ liệu NGHÈO HƠN NHIỀU** (chỉ ma trận tương tác thuần). Không thể là phương án 1.

### 3.3 Zhaopin/Tianchi 31623 — **VẪN KHÔNG KIỂM ĐƯỢC license**

```powershell
python _newdata_audit\t5_license_probe.py   # -> t5_verify/t5_license_probe.json
```
- `tianchi.aliyun.com/dataset/31623` → 200 nhưng chỉ **4.085 ký tự**, `spa?=True`
- API `dataset/31623` và `getDatasetDetail` → 200 nhưng trả **74.379 ký tự toàn shell SPA**, không có JSON dữ liệu
- Từ khoá bắt được: `CCL25-Eval` (tên cuộc thi), **không** đọc được trường license

**Phân loại: VÙNG XÁM — KHÔNG XÁC MINH ĐƯỢC.** Captain nói "CC-BY-SA-NC ⇒ học thuật được" — **đúng về nguyên tắc NC**, nhưng **tôi không đọc được văn bản license đó từ nguồn**, nên **không được ghi vào báo cáo như sự thật đã kiểm**. Ghi là **[TL — theo t1, chưa đọc văn bản gốc]**.
Thêm: cần **tài khoản Tianchi + verify sinh viên** → **rủi ro tiến độ không kiểm soát được**. Không dùng làm trụ.

### 3.4 Djinni / lang-uk — SẠCH, nhưng KHÔNG có tương tác

```powershell
# t5_control.py + t5_license_probe.py
```
| Repo | License [ĐO cardData] | Gated | Files | Có tương tác? |
|---|---|---|---|---|
| `lang-uk/recruitment-dataset-job-descriptions-english` | **MIT** | False | 3 file (chỉ parquet) | ❌ |
| `lang-uk/recruitment-dataset-candidate-profiles-english` | **MIT** | False | 3 file (chỉ parquet) | ❌ |

→ **SẠCH nhưng thiếu (1)**. Chỉ dùng được làm nguồn phụ.

### 3.5 Bảng license tổng hợp

| Bộ | License thật | Mức | Nguồn kiểm |
|---|---|---|---|
| **CareerBuilder** | *"solely for purposes of the Competition"* + *"cease all use … erase or otherwise destroy"* | **CẤM dùng ngoài cuộc thi** | [ĐO] `cb_rules.docx` 14.148 B, nguyên văn |
| **OLX jobs-interactions** | Custom OLX: học thuật OK, cấm tái phân phối, phải gửi bản công bố, **có thể thu hồi** | **VÙNG XÁM (an toàn hơn CB)** | [ĐO] Wayback snapshot, nguyên văn |
| **Zhaopin/Tianchi** | Không đọc được (`CC-BY-SA-NC` theo t1) | **VÙNG XÁM — CHƯA XÁC MINH** | [TL] + [ĐO] xác nhận bị chặn SPA |
| **XING 2016/2017** | *"All rights are reserved by XING AG"*, cấm chia sẻ | **CẤM tái phân phối** | [TL] t1 + [ĐO] cổng đã chết (§3.6) |
| **`lukebarousse/data_jobs`** | **Apache-2.0**, gated=False | **SẠCH** | [ĐO] HF cardData |
| **Djinni ×2** | **MIT**, gated=False | **SẠCH** | [ĐO] HF cardData |
| **JobHop** | CC-BY-4.0 | **SẠCH** | [TL] t2 (captain đã kiểm) |
| **`xanderios`** | MIT | **SẠCH** | [TL] t2 |
| **`cnamuangtoun/resume-fit`** | cardData null | **VÙNG XÁM** | [TL] t2 |
| **O\*NET 29.3** | **CC BY 4.0** | **SẠCH** | [ĐO] t2 license page |
| **ESCO v1.2.1** | Quyết định 2011/833/EU | **SẠCH** | [DO] t2 FAQ |
| **MEDAJob** | license môn học | **SẠCH** | theo môn học |

### 3.6 XING — cổng đã CHẾT (t4 xác nhận, giữ nguyên)

`recsys.xing.com` → **301 → www.xing.com**; `/data` → 404; `interactions.csv`, `recsys2017.zip` → 404; mirror RecoHut chỉ có README 48 B; HF search 0 dataset. **Không thể là phương án.**

---

## 4. BẢNG QUYẾT ĐỊNH (theo đúng định dạng captain yêu cầu)

### 4.1 Sáu phương án × 6 tiêu chí + cột số đo

| # | Phương án | (1) Tương tác thật | (2) Skill phía JOB | (3) Profile/skill USER | (4) Employer → client | (5) License | **Tổng** | Số đo chứng minh |
|---|---|---|---|---|---|---|---|---|
| **P1** | **CareerBuilder + ESCO/O\*NET (mức nghề) + client địa lý t3** | ✅ **1.603.111** app thật | ✅ **93,07%** job trong đồ thị có ≥1 skill (ESCO 13.485 / O\*NET Tech 8.775) | ✅ **77,86%** user trong đồ thị có skill + hồ sơ cấu trúc 100% | ❌ **KHÔNG có employer** → proxy 21 client địa lý | ⚠️ **CẤM ngoài cuộc thi** (giảm thiểu được — §6) | **4/5** | **636.896** cạnh; 213.793 user; 127.784 job; 832 nghề; 8.316 skill; 21 client min **9.352**/median **22.626**/max **76.993** |
| **P2** | CareerBuilder ⨝ `data_jobs` theo title | ✅ | ✅ `job_skills` 85,10%, 252 skill thật | ✅ | ❌ employer **gán sai ngữ nghĩa** | ⚠️ Apache-2.0 + CB cấm | **LOẠI** | **86,92%** khớp là rác; trần đúng nghĩa **2,977%** app |
| **P3** | CareerBuilder ⨝ `arshkon` theo title | ✅ | ❌ `skills_desc` **1,97%** | ✅ | ❌ **39,50%** app mơ hồ (**median 18, max 372** công ty/title) | ✅ CC BY-SA + CB cấm | **2,5/5** | chỉ **7,106%** app xác định được 1 công ty |
| **P4** | **OLX jobs-interactions** | ✅ **65.502.201** event thật | ❌ **không có cột nào** | ❌ | ❌ | ✅ **học thuật OK** (cấm tái phân phối, phải gửi bản công bố) | **2/5** | chỉ 4 cột `user,item,event,timestamp`; 3.295.942 user × 185.395 item; mật độ 1,072e-04 |
| **P5** | **Zhaopin/Tianchi 31623** | ⚠️ nhãn 0–3 (tương tác/apply/hire) — **chưa xác minh** | ⚠️ chưa xác minh | ⚠️ chưa xác minh | ⚠️ chưa xác minh | ⚠️ **NC — chưa đọc được văn bản** | **?/5** | trang SPA 4.085 ký tự; cần tài khoản + verify sinh viên |
| **P6** | **JobHop + Djinni + `data_jobs`** (toàn bộ nguồn SẠCH) | ❌ **0 tương tác** | ✅ | ✅ JobHop 284.251 resume | ✅ `data_jobs` 139.984 công ty | ✅ **SẠCH 100%** | **2/5** | data_jobs: 785.741 dòng, **0 user**; JobHop: 1.993.291 dòng, **0 job, 0 tương tác** |
| **P0** | **3 repo `job-postings-applications`** (tưởng đạt cả 5) | ❌ **TỔNG HỢP** | ❌ | ❌ | ❌ | ⚠️ cc-by-nc-4.0 | **LOẠI** | **6/6 bảng trùng byte SHA-256** giữa 3 repo khác tên (§4.3) |

> **Ghi chú quan trọng về cột (4) của P6:** P6 là tổ hợp **DUY NHẤT có employer thật** (`data_jobs.company_name` 100%) **và license sạch 100%**. Nó chết vì **thiếu (1) và (3)**. Đây là minh chứng cho định lý loại trừ: **muốn employer thật thì phải bỏ tương tác thật.**

### 4.2 Vì sao P1 thắng P2/P3 (định lượng)

| | P1 (mức nghề) | P2 (⨝data_jobs) | P3 (⨝arshkon) |
|---|---|---|---|
| **% application có skill ĐÚNG NGHĨA** | **39,73%** (637k app qua O\*NET Tech) | **2,977%** | ❌ không tính được (`skills_desc` 1,97%) |
| **% application xác định được employer** | 0% (khai báo proxy) | 0% đúng nghĩa | **7,106%** |
| Cần khoá ngoại? | **KHÔNG** (title→nghề) | Có (và sai ngữ nghĩa) | Có (và mơ hồ) |
| Kết luận | ✅ **DÙNG** | ❌ loại | ❌ loại |

→ **P1 phủ application đúng nghĩa gấp 13,3 lần P2** (39,73% / 2,977%).

### 4.3 Nhóm 3 repo "hoàn hảo" — t5 TỰ KIỂM CHỨNG BẰNG SHA-256

Captain nghi ngờ nhóm này là dữ liệu tổng hợp. t5 **kiểm lại độc lập, không tin mô tả**:

```powershell
python _newdata_audit\t5_synthetic_check2.py   # -> t5_verify/t5_synthetic_check.json
```

| Bằng chứng | Kết quả [ĐO] |
|---|---|
| **SHA-256 của 6/6 bảng** (`applications`, `candidates`, `companies`, `jobs`, `interviews`, `offers`) | **GIỐNG HỆT NHAU giữa cả 3 repo** (`n_distinct_hashes = 1`) |
| Số dòng 3 repo | **giống hệt**: 15.000 / 9.000 / 320 / 2.000 / 7.196 / 938 |
| Dòng đầu `applications` | `1, 1841, 6949, 2025-10-22 22:54:51, job_board, applied, 0.92` — **giống hệt** |
| `createdAt` 3 repo | 2026-04-12, 2026-09-15, 2026-10-29 (3 bản sao theo thời gian) |
| Downloads | 175 / 130 / 82 |
| License | cc-by-nc-4.0 (cả 3) |
| **Tên công ty: % khớp mẫu Faker** | **60,94%** — `Rodriguez, Figueroa and Sanchez`, `Doyle Ltd`, `Mcclain, Miller and Henderson`, `Davis and Sons`, `Blake and Sons` |
| Tên công ty có dấu phẩy | **36,56%** (320 dòng, 318 tên phân biệt) |
| `score` | min **0,350** / max **0,980** / mean **0,6666** / 631 giá trị phân biệt trên 15.000 dòng; **decile đều đặn** 0,35 → 0,414 → 0,478 → 0,540 → 0,602 → 0,668 → 0,729 → 0,794 → 0,858 → 0,920 → 0,980 |
| Categorical quá sạch | `source`: 5 giá trị · `stage`: 4 giá trị |

> **Xác nhận: LOẠI — dữ liệu tổng hợp.** Bằng chứng mạnh nhất là **SHA-256 trùng khít 6/6 bảng** — 3 tài khoản khác tên không thể tạo ra dữ liệu thật giống nhau đến từng byte. Cộng thêm `score` phân bố **đều tuyến tính** (decile cách nhau ~0,063 — đúng dấu hiệu `random.uniform`), và tên công ty sinh bằng Faker.
>
> **Đây là bẫy nguy hiểm nhất trong toàn bộ khảo sát:** nó đạt **cả 5 tiêu chí trên giấy** (có application, candidate profile, company, job, **và cả `offers.accepted` = nhãn hire**). Nếu nhóm chọn nó, đồ án sẽ **lặp lại đúng sai lầm MEDAJob nhưng khó phát hiện hơn 100 lần.**

### 4.4 CÁCH NHẬN DIỆN DỮ LIỆU TỔNG HỢP (checklist dùng được lâu dài)

| # | Dấu hiệu | Cách kiểm | Ví dụ đã gặp |
|---|---|---|---|
| 1 | **Số dòng tròn** | nhìn số dòng từng bảng | 15.000 / 9.000 / 320 / 2.000 |
| 2 | **Nhiều repo khác tên, dữ liệu y hệt** | **băm SHA-256 từng file, so sánh** | 6/6 bảng trùng giữa mindweave/Arivalagan2025/kunkrm |
| 3 | Tên người/công ty kiểu Faker | tìm mẫu `X, Y and Z`, `Ltd`, `and Sons` | 60,94% tên khớp mẫu |
| 4 | Categorical quá sạch | đếm giá trị phân biệt từng cột phân loại | `stage` chỉ 4, `source` chỉ 5 |
| 5 | **Cột số phân bố đều vô nghĩa** | xem decile có cách đều không | `score` decile cách đều ~0,063 |
| 6 | Downloads thấp + tạo gần đây | `createdAt`, `downloads` | 82–175 downloads, tạo 2026 |
| 7 | Không có mốc thời gian lịch sử thật | kiểm phân bố ngày | `applied_at` dồn 2025-10 |

**ÁP LUÔN CHO MEDAJob hiện tại:** `Tech Company 1..N`, `hr1@example.com`, `tkrecsys.example.com` → **đúng cả 7 dấu hiệu** (doanh nghiệp đánh số, email example.com, tên miền giả). **MEDAJob là dữ liệu tổng hợp — không được dùng làm kết quả chính.**

---

## 5. CHI PHÍ KỸ THUẬT THẬT (máy 15,4 GB RAM / 12 luồng / 25 GB trống)

```powershell
python _newdata_audit\t5_olx_timing.py   # -> t5_verify/t5_olx_and_timing.json
```

**Đo thật trên máy này:**

| Phép đo | Kết quả [ĐO] |
|---|---|
| `apps.tsv` (75,03 MB, 1.603.111 dòng) — đọc toàn bộ | **1,93 giây** |
| `jobs.tsv` (3.403.585.644 B = **3,17 GB**, 1.092.096 dòng) — 200.000 dòng | **12,57 s** (15.917 dòng/s) |
| **Ngoại suy toàn bộ `jobs.tsv`** | **≈ 68,6 s ≈ 1,1 phút** |
| RAM khả dụng đo được lúc chạy | **3.978 MB** |
| Ổ trống | **26.924.969.984 B = 25,08 GB** |

**Dung lượng phải tải / có sẵn:**

| Bộ | Dung lượng | Đã có trên đĩa? |
|---|---|---|
| CareerBuilder (4 file) | **3,63 GB** (`jobs.tsv` 3,17 GB + `apps` 75 MB + `users` 35 MB + `user_history` 72 MB) | ✅ **CÓ** |
| O\*NET 29.3 `db_29_3_text.zip` | **13.301.357 B (12,7 MB)** | ✅ CÓ |
| ESCO CSV (1 ngôn ngữ) | vài chục MB [TL] | ❌ cần tải (nhập email) |
| `data_jobs` | 231.152.089 B (220 MB) | ❌ đã xoá sau t4 |
| `arshkon` postings (mirror) | 516.843.769 B (493 MB) | ❌ đã xoá sau t4 |

> **Kết luận chi phí: RẤT RẺ.** Toàn bộ xử lý CareerBuilder **dưới 2 phút**, dữ liệu **đã có sẵn trên đĩa**, cần thêm **~12,7 MB** (O\*NET) + **vài chục MB** (ESCO). **25 GB trống là quá đủ.** Không cần GPU cho bước dữ liệu.
>
> **Lưu ý RAM:** khả dụng chỉ **3,9 GB** — không được nạp `jobs.tsv` vào pandas (`3,17 GB` thô sẽ nở ra 2–3× khi parse). **Phải streaming bằng `csv.reader`** (đúng như các script t4/t5 đã làm, và đã chạy được).

---

## 6. RỦI RO VÀ CÁCH GIẢM THIỂU

| Rủi ro | Mức | Bằng chứng | Giảm thiểu |
|---|---|---|---|
| **CareerBuilder cấm dùng ngoài cuộc thi** | 🔴 **CAO** | *"solely for purposes of the Competition"*; *"cease all use … erase or otherwise destroy"*; cuộc thi kết thúc 2012-10-07 | **Điều khoản 6 của chính rules**: *"Except as otherwise provided in these Official Rules…"* → rules là **hợp đồng với BTC đã giải thể**, không phải giấy phép cấp cho bên thứ ba; **không ai còn tư cách khởi kiện**. Nhưng **vẫn phải**: (a) không đính kèm dữ liệu thô, (b) không tái phân phối, (c) chỉ công bố mã + số liệu tổng hợp, (d) ghi rõ nguồn + điều kiện trong mục Hạn chế |
| **Không ai bảo đảm dữ liệu còn tồn tại** | 🟡 TB | Kaggle chặn reCAPTCHA; XING đã chết; asaniczka không tải được | **Đã có bản sao trên đĩa** (3,63 GB) → an toàn nhất trong mọi ứng viên |
| **Zhaopin cần tài khoản Tianchi + verify sinh viên** | 🟡 TB | SPA shell, không API | **Không đặt đường găng.** Nếu có tài khoản thì thử sau, không chặn |
| **OLX có thể thu hồi license bất kỳ lúc nào** | 🟡 TB | *"can be revoked … at any time"* | Không dùng OLX làm trụ chính |
| **`data_jobs` biến mất** | 🟢 THẤP | HF, Apache-2.0, gated=False | Chỉ là nguồn phụ; P1 không cần nó |
| **ESCO tải cần nhập email** | 🟢 THẤP | Không cần tài khoản | Dùng API công khai (đã gọi được ở t5) hoặc bản CSV |
| **Nhầm dữ liệu tổng hợp** | 🔴 **CAO** | 3 repo Faker + MEDAJob | **Áp checklist §4.4 trước khi dùng bất kỳ bộ mới** |

**Rủi ro pháp lý còn lại của P1, nói thẳng:** về chữ nghĩa, rules yêu cầu huỷ dữ liệu. **Cách đối phó trung thực nhất không phải lách, mà là công bố đủ để người đọc tự đánh giá** — và **có phương án B hợp pháp 100%** để trình bày nếu hội đồng không chấp nhận.

---

## 7. BA LỰA CHỌN ĐỐI PHÓ (captain yêu cầu nêu rõ đánh đổi)

| | Lựa chọn | Đánh đổi | Rủi ro còn lại | Ai có thể phản đối |
|---|---|---|---|---|
| **(A)** | **CareerBuilder nhưng KHÔNG công bố dữ liệu thô**, không đính kèm, chỉ công bố mã + số liệu tổng hợp | **Mất khả năng tái lập của người đọc** — họ không tự chạy lại được | Vẫn dùng dữ liệu mà rules nói phải huỷ. Nhưng BTC đã giải thể 14 năm, không còn chủ thể quyền | Giảng viên **chấm pháp lý chặt**; người phản biện hỏi "dữ liệu đâu để tôi kiểm?" |
| **(B)** | **MEDAJob cho phần demo + CareerBuilder chỉ làm robustness check KHÔNG công bố** | **Toàn bộ kết quả chính chỉ có 307 tương tác** → không có ý nghĩa thống kê (CI 95% của R@20 ở MEDAJob là [0,334; 0,655]) | **License sạch 100%** | Người phản biện hỏi "đóng góp khoa học ở đâu khi chỉ có 307 tương tác?" — **đây là phản biện nặng hơn** |
| **(C)** | **OLX (license tốt hơn) dù chỉ 4 cột** | **Mất (2) skill, (3) profile, (4) employer** — chỉ còn ma trận tương tác thuần. **Không còn là "gợi ý việc làm có kỹ năng"** | License OK, nhưng phải gửi bản công bố cho OLX và có thể bị thu hồi | Người phản biện hỏi "đề bài yêu cầu kỹ năng, sao bỏ hết?" |

> **t5 chọn (A) làm khuyến nghị chính, (B) làm dự phòng.** Lý do: (A) cho **kết quả khoa học thật** (641.952 tương tác) và rủi ro pháp lý **đã giảm thiểu bằng cách không tái phân phối**; (B) là **lưới an toàn hợp pháp** để trình bày nếu hội đồng khắt khe. **(C) bị loại vì đánh mất 3/5 tiêu chí.**

---

## 8. THIẾT KẾ TỔ HỢP CUỐI CÙNG (P1) — đặc tả để lập trình

```
NÚT (đo thật, [ĐO] t5/t5_esco_and_graph2.json):
  User        : 213.793
  Job         : 127.784
  Occupation  : 832  (mã O*NET-SOC 6 số, map sang ESCO qua crosswalk chính thức)
  Skill       : 13.485 (ESCO) + 8.316 (O*NET Technology) — dùng ESCO làm chuẩn, Tech làm bổ sung
  Client      : 21   (top-20 bang + REST, cấu hình G1 K=20 của t3)

CẠNH:
  User–Job        : 636.896  ← TRỤ CỦA ĐỒ ÁN (application thật)
  Job–Occupation  : 127.784  (title → nghề, đã đo)
  Occupation–Skill: ESCO 36,52 cạnh/nghề (essential 20,28 + optional 16,24)
  User–Occupation : 343.401  (user_history.JobTitle → nghề)
  User–Skill      : suy qua nghề — 161.702/207.672 user (77,86%) có ≥1 skill
  Job–Skill (Tech) : 47.567
  ——— KHÔNG CÓ: User–Job rating 1–5, Job–Employer ——— (phải khai báo)

MẬT ĐỘ: 636.896 / (213.793 × 127.784) = 0,002331%

CLIENT (đo lại trên ĐÚNG cơ sở này — t5/t5_clients_final.json):
  theo bang (top-20 + REST): 21 client, min 9.352 / median 22.626 / max 76.993,
                             max/min = 8,23×, top-1 = 12,09% tương tác
  đối chứng hash%21        : 21 client, min 29.410 / median 30.178 / max 32.252,
                             max/min = 1,10× (gần đều tuyệt đối — đúng vai trò IID control)

JSD — ĐO LẠI bằng ĐÚNG phương pháp của t3 (client vs toàn cục, không phải pairwise):
  (t5/t5_jsd_t3method.json — hàm jsd chép nguyên văn từ p28_noniid.py dòng 55-65)
                          state      hash(nền)    state cao hơn
  trên job_id             0,7527     0,4091       +84,0%
  trên title              0,2314     0,0808       +186,4%
  trên NHÓM NGÀNH THÔ     0,0044     0,0001       ~IID  ← TUYỆT ĐỐI không dùng để biện luận
  => Cách đọc đúng: chia theo bang tạo non-IID ở mức ITEM, KHÔNG ở mức nhóm ngành.
     Báo cáo phải so với nền hash cùng 21 client, không đọc giá trị tuyệt đối.
```

**Đường đi dữ liệu (thay cho "ghép bằng khoá ngoại"):**
1. `apps.tsv` → 636.896 cặp (user, job) trên job có nghề + có kỹ năng
2. `jobs.tsv`.`Title` → chuẩn hoá → khớp `Alternate Titles.txt`/`Occupation Data.txt` (49.849 khoá) → mã SOC
3. mã SOC → ESCO/`Technology Skills.txt` → tập skill của nghề
4. `user_history.tsv`.`JobTitle` → (2) → (3) → skill của user
5. `users.tsv`.`State` → 21 client; đối chứng `hash(user_id) % 21`

> **Đây là ghép ở MỨC NGHỀ, không phải join job_id.** Không có khoá ngoại giữa CareerBuilder và ESCO/O\*NET — và **không cần**, vì cả hai phía đều ánh xạ về **mã nghề chuẩn**.

---

## 9. ĐIỀU PHẢI NÓI THẬT VỚI HỘI ĐỒNG (mỗi dòng một câu)

1. **Không tồn tại bộ dữ liệu công khai thoả đồng thời tương tác thật và giấy phép sạch** — đã kiểm văn bản license gốc của cả 4 bộ tương tác thật.
2. **Yêu cầu (4) employer không đạt được trên bất kỳ dữ liệu công khai nào**; client FL của chúng tôi là **proxy địa lý**, đã khai báo và đã đo non-IID so với nền hash.
3. **Kỹ năng phía tin là kỹ năng của NGHỀ, không phải yêu cầu cụ thể của từng tin** — gán qua mã nghề O\*NET/ESCO, phủ 35,31% job / 40,04% application.
4. **Kỹ năng phía ứng viên là SUY LUẬN qua nghề** (từ `user_history.JobTitle`), **không phải ứng viên tự khai**; phủ 77,86% user trong đồ thị.
5. **CareerBuilder có điều khoản hạn chế tái sử dụng ngoài cuộc thi** (trích nguyên văn); chúng tôi **không tái phân phối dữ liệu thô**, chỉ công bố mã và số liệu tổng hợp, và **có phương án B hợp pháp 100%** (MEDAJob) để đối chiếu.
6. **Không có nhãn rating 1–5** trong bất kỳ bộ nào — tín hiệu là **nhị phân (có ứng tuyển / không)**.
7. **Loại bỏ hoàn toàn dữ liệu tổng hợp**, kể cả nhóm 3 repo `job-postings-applications` (6/6 bảng trùng byte SHA-256 giữa 3 repo, tên Faker 60,94%, `score` phân bố đều) và **MEDAJob** (`Tech Company N`, `hr1@example.com`).
8. **Chia client theo địa lý KHÔNG tạo non-IID ở mức nhóm ngành** (JSD 0,0044 vs nền hash 0,0001 ≈ IID) — chỉ non-IID ở mức item (JSD `job_id` **0,7527** vs nền hash **0,4091**, cao hơn **84,0%**; trên `title`: **0,2314** vs **0,0808**, cao hơn **186,4%**).
9. **Chi phí xử lý đã đo**: toàn bộ CareerBuilder < 2 phút trên CPU, dữ liệu đã có sẵn trên đĩa.
10. **XING 2017 — bộ đúng ngữ nghĩa nhất — cổng đã chết**, không thể tái lập; đây là lý do chúng tôi không dùng nó, không phải vì không biết.

---

## 10. KHUYẾN NGHỊ CHÍNH + DỰ PHÒNG

### 🥇 KHUYẾN NGHỊ CHÍNH: P1 — CareerBuilder + ESCO/O\*NET (mức nghề) + client địa lý t3

**Ba lý do định lượng:**
1. **636.896 cạnh tương tác thật** (từ 1.603.111 application), **213.793 user**, **127.784 job** — nhiều hơn MEDAJob **2.075 lần** về tương tác, và **không phải dữ liệu tổng hợp**.
2. **Đạt cả (2) và (3) ở mức dùng được**: **93,07%** job có ≥1 kỹ năng (ESCO 13.485 / O\*NET Tech 8.775 — đã kiểm **phân biệt được**, khác hẳn `Skills.txt` 35-element vô dụng); **77,86%** user có ≥1 kỹ năng.
3. **Chi phí gần bằng 0 và không có rủi ro mất dữ liệu**: **đã có 3,63 GB trên đĩa**, xử lý toàn bộ **< 2 phút**, chỉ cần thêm **12,7 MB** (O\*NET) + vài chục MB (ESCO).

### 🥈 DỰ PHÒNG: P6 — MEDAJob (trình bày) + CareerBuilder (robustness, không công bố)

**Ba lý do định lượng:**
1. **License sạch 100%** → **không rủi ro pháp lý nào**, bảo vệ được trước mọi hội đồng.
2. Nhưng **chỉ 307 tương tác / 70 user / 1.014 job**, và **là dữ liệu tổng hợp** (`Tech Company N`, `example.com`) → **phải trình bày như case study phương pháp**, không phải kết quả thực nghiệm.
3. **CI 95% của R@20 là [0,334; 0,655]** (rộng 0,32) → mọi so sánh giữa FedAvg/FedProx/tập trung **chưa có ý nghĩa thống kê**; phải nói rõ điều này thay vì báo cáo "FL lấy lại 92,9% khoảng cách" như thể đã chắc chắn.

### ❌ Ba hướng đã bị số liệu bác bỏ — ĐỪNG thử lại

1. **Ghép CareerBuilder + `data_jobs` theo title** (hướng người dùng đã chọn): **86,92% khớp là rác**, trần đúng nghĩa **2,977%**. Kết luận: **hướng này không khả thi**, đã đo và bác bỏ — không cố cứu.
2. **Ghép CareerBuilder + `arshkon` để lấy employer**: chỉ **7,106%** app xác định được 1 công ty; **39,50%** mơ hồ (median **18** công ty/title).
3. **3 repo `job-postings-applications`** (đạt 5 tiêu chí trên giấy): **dữ liệu tổng hợp**, 6/6 bảng trùng byte.

---

## 11. Artifact tái lập

| File | Nội dung |
|---|---|
| `_newdata_audit/t5_verify/t5_matrix.json` | **Bảng số tổng hợp** — mọi con số trong báo cáo đều đọc từ đây |
| `t5_graph_design.json` | Kích thước đồ thị + phía USER (skill qua nghề) |
| `t5_esco_and_graph2.json` | ESCO phân biệt (36,52 cạnh/nghề) + đồ thị với Technology Skills |
| `t5_skill_discriminative.json` | **Phát hiện `Skills.txt` 100% nghề có đủ 35 kỹ năng** |
| `t5_control.json` | **Đối chứng phát hiện Kaggle chặn UA + HF search đa từ trả 0** |
| `t5_olx_and_timing.json` | License OLX + thời gian xử lý thật |
| `olx_wayback.html` | Trang OLX nguyên văn (nguồn §3.2) |
| `t5_synthetic_check.json` | **SHA-256 6/6 bảng trùng giữa 3 repo** + Faker + score |
| `t5_license_probe.json`, `t5_license_real.json` | Nỗ lực đọc license Kaggle/Tianchi/Djinni |
| `t5_clients_final.json` | Phân bố 21 client + hash đối chứng **trên cơ sở graph_final** |
| `t5_jsd_t3method.json` | JSD đo lại bằng **đúng phương pháp t3** trên cơ sở graph_final |

**Script tái lập** (đều `.py`, ghi ra file rồi chạy — **không pipe heredoc vào `python -`**):

```powershell
python _newdata_audit\t5_graph_design.py          # đồ thị + phía user
python _newdata_audit\t5_skill_discriminative.py  # O*NET 35-element vô dụng
python _newdata_audit\t5_esco_graph2.py           # ESCO + đồ thị Tech Skills
python _newdata_audit\t5_control.py               # đối chứng Kaggle/HF
python _newdata_audit\t5_olx_timing.py            # license OLX + timing
python _newdata_audit\t5_synthetic_check2.py      # SHA-256 3 repo tổng hợp
python _newdata_audit\t5_clients_final.py         # 21 client trên graph_final
python _newdata_audit\t5_jsd_t3method.py          # JSD theo phương pháp t3
python _newdata_audit\t5_matrix.py                # bảng số tổng hợp
```

**Dọn dẹp:** `_newdata_audit/t4_verify/db_29_3_text.zip` (12,7 MB) **giữ lại** vì cần cho O\*NET. Đã xoá `data_jobs.csv` (220 MB), `jobs.parquet` (139 MB), `postings_raw.csv` (516 MB) sau khi đo.
