# Khảo sát nguồn KỸ NĂNG / NGÀNH có cấu trúc và job corpus giàu kỹ năng (t2)

Ngày đo: 2026-11-08 (Asia/Saigon). Máy đích: ổ E:, Python 3.13 + urllib (PowerShell/curl hỏng schannel trên host này, **chỉ Python tải được**).

Mọi số trong tài liệu này là **số ĐO ĐƯỢC**, không suy từ mô tả marketing. Bằng chứng máy đọc: `_newdata_audit/T2_EVIDENCE.json` + 12 file `t2_*.json` cùng thư mục, kèm script tái lập.

Nhãn mức tin cậy: **[ĐO]** = tôi trực tiếp tải/đếm · **[ĐO-MẪU]** = đo trên mẫu, có n · **[TL]** = suy từ tài liệu chính thức · **[CHƯA XÁC MINH]**.

---

## Phần A — TAXONOMY kỹ năng / ngành

### A1. ESCO (EU)

| Hạng mục | Giá trị | Mức |
|---|---|---|
| Phiên bản | v1.2.1 (release 6.2.0, cập nhật 2025-12-10) | [TL] |
| Số nghề | **2.942** occupation (`/api/search?type=occupation` → `total: 2942`) | [ĐO] |
| Số kỹ năng | **13.485** skill (`type=skill` → `total: 13485`) | [ĐO] |
| Số ngôn ngữ | **28**: bg, es, cs, da, de, et, el, en, fr, ga, hr, it, lv, lt, hu, mt, nl, pl, pt, ro, sk, sl, fi, sv, is, no, ar, uk | [ĐO] |
| **Tiếng Việt** | **KHÔNG CÓ.** Gọi `resource/occupation?...&language=vi` trả về đúng 28 preferredLabel, `'vi'` không nằm trong `preferredLabel` lẫn `alternativeLabel` — giống hệt khi gọi `language=en/fr/de` | [ĐO] |
| Phân cấp skill→nhóm | **CÓ.** 60/60 skill mẫu có `broaderHierarchyConcept` (nhóm kỹ năng); 38/60 có `broaderSkill`; 10/60 có `narrowerSkill` | [ĐO-MẪU n=60] |
| Loại skill | `skill` 49/60, `knowledge` 11/60 | [ĐO-MẪU n=60] |
| Mức tái dùng | sector-specific 29, cross-sector 18, occupation-specific 12, transversal 1 (trên 60) | [ĐO-MẪU n=60] |
| Map sang nghề | **CÓ, ma trận nghề–kỹ năng.** Trên 199 nghề mẫu: essential **TB 20,85** (median 19, min 3, max 90, p95 36); optional **TB 17,03** (median 16, max 108); **TB 37,88 cạnh/nghề** → ước **~111.441 cạnh** cho 2.942 nghề | [ĐO-MẪU n=199] |
| Độ phủ ngược | 78/80 skill mẫu (97,5 %) có ≥1 nghề liên kết | [ĐO-MẪU n=80] |
| Map sang ngành | Nghề map **1-1 sang ISCO-08** (ví dụ `calculation engineer` = `2149.2.1`, tổ tiên `C2149 → C214 → C21 → C2`). ESCO **có** crosswalk NACE và crosswalk O*NET chính thức | [ĐO] + [TL] |
| Giấy phép | **Quyết định 2011/833/EU**: tải/ dùng/ tái bản/ tái sử dụng miễn phí cho **mọi mục đích**, kèm điều kiện ghi công bắt buộc | [ĐO — đọc FAQ] |
| Offline-able | **CÓ.** CSV/ODS/RDF/TTL/XML/JSON-LD + **Local API** tải về. Gói CSV tiếng Anh có **19 file**: `occupations`, `skills`, `skillGroups`, `skillsHierarchy`, `occupationSkillRelations`, `skillSkillRelations`, `broaderRelationsOccPillar`, `broaderRelationsSkillPillar`, `ISCOGroups`, `digitalSkillsCollection`, `greenSkillsCollection`, `digCompSkillsCollection`, `languageSkillsCollection`, `transversalSkillsCollection`, `researchSkillsCollection`, `researchOccupationsCollection`, `greenShareOcc`, `conceptSchemes`, `dictionary` | [TL — trang cấu trúc gói] |
| Cần đăng ký | Không cần tài khoản. Form tải yêu cầu **chấp nhận privacy statement + nhập email** để nhận link | [TL] |
| Dung lượng | Vài chục MB (gói 1 ngôn ngữ, CSV) | [TL] |

**Cảnh báo kỹ thuật đo được:** API `/api/search` **chặn phân trang ở 500 dòng** — `offset=500` trả về rỗng dù `total=2942`. Muốn lấy đủ 2.942 nghề phải gọi theo từ khóa hoặc dùng gói CSV tải về. Đây là lý do tôi đo ma trận trên 500 nghề lấy được rồi lấy mẫu 199.

### A2. O*NET (US DOL)

Đã tải thật `db_29_3_text.zip` = **13.301.357 B**, giải nén **42 file**, đọc trực tiếp.

| Hạng mục | Giá trị | Mức |
|---|---|---|
| Số nghề | **1.016** dòng `Occupation Data.txt` (867 mã SOC-6 base, 23 nhóm lớn) | [ĐO] |
| Kỹ năng | **35** element: **10 Basic Skills (2.A)** + **25 Cross-Functional Skills (2.B)** | [ĐO] |
| Ma trận nghề–kỹ năng | **30.765 cạnh**, phủ 879 nghề, đúng **35 kỹ năng/nghề** (thang IM và LV đều 30.765 dòng) | [ĐO] |
| Knowledge | 33 element, 29.007 cạnh | [ĐO] |
| **Technology Skills** | **32.681 cạnh**, **8.775 phần mềm/công nghệ phân biệt**, phủ 923 nghề, 11.616 dòng gắn nhãn *Hot Technology* | [ĐO] |
| Tools Used | 41.662 cạnh, 18.105 dụng cụ phân biệt | [ĐO] |
| Abilities / Work Activities / Work Styles | 52 / 41 / 16 element | [ĐO] |
| Alternate Titles | **56.558** tên gọi thay thế (dùng để khớp `job_title` thực tế → nghề) | [ĐO] |
| Task Statements | 18.796 | [ĐO] |
| Phân cấp | **CÓ.** `Element ID` phân cấp dạng `2.A.1.a`; thêm `Content Model Reference` (628 dòng), `IWA Reference` (332 dòng), `DWA Reference` (2.087 dòng) | [ĐO] |
| Map sang nghề | Có sẵn (chính là ma trận trên). Map sang ESCO: **crosswalk chính thức** ESCO↔O*NET, công bố trên cả 2 cổng | [TL] |
| Giấy phép | **CC BY 4.0** (O*NET Database Content License) — ghi công + theo quy tắc nhãn hiệu O*NET | [ĐO — đọc license_db.html] |
| Offline-able | **CÓ.** Text DB đầy đủ, không cần đăng ký (đăng ký developer là tuỳ chọn) | [ĐO] |
| Dung lượng | 13,3 MB zip | [ĐO] |

**Điểm yếu lớn:** chỉ **35 kỹ năng**. Đây là *kỹ năng chung* (Reading Comprehension, Critical Thinking…), **không đủ để làm node Skill cho GNN**. Bù lại `Technology Skills` cho 8.775 phần mềm cụ thể nhưng chỉ gắn ở mức nghề, không ở mức tin tuyển dụng.

### A3. Lightcast và LinkedIn

| Nguồn | Trạng thái | Bằng chứng |
|---|---|---|
| Lightcast Open Skills | **Không mở.** Không có repo dataset kỹ năng nào; API là hợp đồng thương mại | [ĐO] — tìm GitHub `lightcast-io`, `open-skills`, `lightcast` chỉ ra project không liên quan |
| LinkedIn Skills Taxonomy | **Không public.** Trang tham chiếu LinkedIn Talent API trả 404; taxonomy chỉ qua Talent Solutions đối tác | [ĐO] |

**Kết luận A:** chỉ **ESCO** đủ làm taxonomy kỹ năng cho đồ thị. O*NET là nguồn **phụ** (crosswalk nghề, technology skills, alternate titles). Lightcast/LinkedIn: bỏ.

---

## Phần B — JOB CORPUS có cột skill TƯỜNG MINH

| # | Nguồn | Số bản ghi | Cột thực tế | Giấy phép | Dung lượng | Đăng ký | Skill tường minh? |
|---|---|---|---|---|---|---|---|
| B1 | **kaggle asaniczka/1-3m-linkedin-jobs-and-skills-2024** | `linkedin_job_postings.csv` **1.348.454** dòng; `job_skills.csv` **1.296.381** dòng | postings: `job_link, last_processed_time, got_summary, got_ner, is_being_worked, job_title, company, job_location, first_seen, search_city`. skills: `job_link, job_skills` | **ODC-By** | **6.190.063.069 B (6,19 GB)** | Có (Kaggle account) | **CÓ nhưng là chuỗi NER**, phải `.split(", ")` |
| B2 | **kaggle ravindrasinghana/job-description-dataset** | **1.615.940** dòng × 23 cột | `Job Id, Experience, Qualifications, Salary Range, location, Country, latitude, longitude, Work Type, Company Size, Job Posting Date, Preference, Contact Person, Contact, Job Title, Role, Job Portal, Job Description, Benefits, skills, Responsibilities, Company, Company Profile` | **CC0** | **1.743.166.140 B (1.743.166.140 B = 1,74 GB)** | Có | `skills` điền **100,0 %** — nhưng **DỮ LIỆU TỔNG HỢP** |
| B3 | **HuggingFace lukebarousse/data_jobs** | **785.741** dòng × 17 cột | `job_title_short, job_title, job_location, job_via, job_schedule_type, job_work_from_home, search_location, job_posted_date, job_no_degree_mention, job_health_insurance, job_country, salary_rate, salary_year_avg, salary_hour_avg, company_name, job_skills, job_type_skills` | **Apache-2.0** | **231.152.089 B (231 MB)** | Không | **CÓ — list Python thật** |
| B4 | **Adzuna API** | 20 kết quả/trang, phân trang | `id, title, description, created, redirect_url, company.display_name, category.label/tag, location.area[], salary_min/max, contract_type, contract_time, lat/lon` | [CHƯA XÁC MINH] — `adzuna.com/terms` trả **403** cho host này | API | **Có app_id + app_key** | Không |
| B5 | **USAJobs API** | phân trang, `ResultsPerPage` | `MatchedObjectId, PositionID, PositionTitle, PositionURI, OrganizationName, DepartmentName, JobCategory[].Name/Code, QualificationSummary, PositionRemuneration, PositionLocation, OfferingType` | ToS + rate limit; tin tuyển dụng liên bang là public domain | API | **Có API key + email** (401 nếu không) | Không (`QualificationSummary` là free text) |
| B6 | **Arbeitnow** | một lượt quét: **3.511 tin / 15 trang** rồi **HTTP 429** | `slug, company_name, title, description, remote, url, tags, job_types, location, created_at` | ToS của Arbeitnow.com | API | **Không** | Không — `tags` là **896 nhãn ngành/chức năng**, không phải kỹ năng |

### Chi tiết đo được

**B1 — asaniczka.** Tải bị chặn: 6,19 GB vượt hạn mức 500 MB, và endpoint `api/v1/datasets/download` trả **404** khi không có session đã đăng nhập, nên tôi chỉ đọc được **data card**. Số đo từ card: `job_skills.csv` **1.296.381** dòng, **1.287.105** giá trị `job_skills` phân biệt (1.296.381 dòng), `got_summary=true` **96 %**, `got_ner≈96 %`, **584.544** công ty phân biệt. Tên cột lấy chính xác từ card HTML: `job_link, last_processed_time, got_summary, got_ner, is_being_worked, job_title, company, job_location, first_seen, search_city`.
Chất lượng skill: NER trên job summary nên **lẫn cả phúc lợi** — ví dụ một tin bán hàng cho ra `Customer service, Communication, Health Insurance, Dental Insurance, Vision Insurance, PTO`; có dòng chứa nguyên văn *"I'm unable to extract the requested data from the provided context…"*.

**B2 — ravindra: TỔNG HỢP, không dùng được làm dữ liệu thị trường.** Đo trên khối 6 MB giữa file (5.551 dòng): `Company Size` có **5.412 giá trị khác nhau / 5.551 dòng** (gần như duy nhất), `Qualifications` chỉ **10** giá trị, `Job Portal` chỉ **4** giá trị, `Preference` chỉ `Male/Both/Female`. Cặp công ty–quốc gia vô lý: **BT Group → Gibraltar**, **Truist Financial → Maldives**, **Prudential Financial → San Marino**, **UltraTech Cement → Madagascar**. `Salary Range` có khoảng **181.794.758.338 – 62.170.523.408.759,90**. `Job Description` là template lặp theo `Role`. Cột `skills` điền 100 % nhưng giá trị là chuỗi ghép không phân tách, và bản thân tin là bịa.

**B3 — lukebarousse/data_jobs: phát hiện tốt nhất cho mục B.** Tôi đã **tải toàn bộ 231.152.089 B** rồi đo **100 % số dòng**, sau đó xoá file:
- `job_skills` non-null **668.704 / 785.741 = 85,10 %** (0,8510); trong đó **668.704 parse thành list không rỗng, 0 lỗi parse** (list Python thật, không phải trích từ HTML).
- Trung bình **5,45 kỹ năng/tin**; **246 kỹ năng phân biệt** trên mẫu 200k. Top: sql 114.809, python 113.999, aws 43.259, azure 39.349, r 39.243, excel 38.073, tableau 37.869, spark 34.190, power bi 29.280, java 25.397.
- `job_type_skills` điền **85,10 %**, dạng dict phân nhóm: `{'analyst_tools': ['power bi','tableau'], 'programming': ['r','python','sql','nosql']}`.
- `company_name` điền **100,00 %**, **139.982** công ty phân biệt.
- Khoảng thời gian `job_posted_date`: **2023-01-01 → 2023-12-31**.
- **KHÔNG có cột user/applicant, KHÔNG có applies/views.** Không có cột industry.

**B6 — Arbeitnow.** Không cần key, nhưng bị **429 từ trang 16**. `tags` điền 96,5 % với 896 nhãn khác nhau, top: Remote 187, Engineering 171, Sales 140, Customer Success 87 — đây là **nhãn ngành/chức năng**, không phải kỹ năng. 1.399 công ty phân biệt.

---

## Phần C — PROFILE ứng viên có kỹ năng

| # | Nguồn | Số bản ghi | Cột thực tế | Giấy phép | Dung lượng | Đăng ký | Skill phía user? |
|---|---|---|---|---|---|---|---|
| C1 | **HF aida-ugent/JobHop** (v2) | **1.993.291** work-experience (train 1.594.827 + val 199.587 + test 198.877); **355.315** quỹ đạo | **`resume_id, matched_code, start_date, end_date, university_level`** | **CC-BY-4.0** | **11.572.872 B (11,6 MB)** tổng; train parquet **9.213.302 B** | Không | **KHÔNG** |
| C2 | **HF cnamuangtoun/resume-job-description-fit** | train **6.241** + test **1.759** = **8.000** | `resume_text, job_description_text, label` | **KHÔNG CÓ GIẤY PHÉP** (`cardData` null, không tag license) | **68.616.017 B (68,62 MB)** | Không | **KHÔNG** |

### Chi tiết đo được

**C1 — JobHop.** Đã tải `JobHop_v2_train.parquet` (9.213.302 B) và đọc thật. **Cột thực tế khác README**: README mô tả v2 dùng `person_id / esco_code / education_level`, nhưng parquet phát hành lại chứa `resume_id / matched_code / start_date / end_date / university_level` (tên kiểu v1). Đo được: **284.251** `resume_id` phân biệt, **2.983** `matched_code` phân biệt, `matched_code` **không có null**, `unknown` chiếm **6,93 %** (0,0693) dòng (110.573). Phân bố học vấn: Secondary 621.996, Bachelor 552.146, Master 231.452, None 182.610, PhD 6.623.

Join sang ESCO: lấy mẫu 60 mã, tra đúng mã qua `/api/search`: **57/60 = 95,0 %** khớp chính xác vào `occupation.code` của ESCO (3 mã trượt: `2422.12.4`, `7115.6`, `2149.17`). Vậy JobHop **nối được** sang cây nghề ESCO.

**Nhưng README nói rõ JobHop KHÔNG phát hành kỹ năng**: *"it also extracts standardized job titles, free-text descriptions, company and institution names, technical skills, languages, certificates, contract type, and work-schedule type. Those fields are used internally to produce the ESCO codes and education levels; the public release contains only the structured fields listed in the table above."* → **không có cột skill, không có tin tuyển dụng, không có employer, không có tương tác.**

**C2 — resume-job-description-fit.** Đã tải cả 2 file và đọc. cột `resume_text, job_description_text, label`; nhãn train: No Fit 3.143 / Potential Fit 1.556 / Good Fit 1.542; test: No Fit 857 / Good Fit 458 / Potential Fit 444. Không có cột skill, không employer, không rating. `label` là **nhãn fit do người gán**, không phải hành vi click/apply. **Giấy phép không khai báo** → rủi ro cho yêu cầu (5).

---

## CHI PHÍ BIẾN ĐỔI (bao nhiêu bước để thành cột skill của job / của user)

Đếm "bước" = một phép biến đổi dữ liệu phải viết code, không tính đọc file.

| Nguồn | → `job.skills` | Số bước | → `user.skills` | Số bước |
|---|---|---|---|---|
| **ESCO** | Không phải job; là **từ điển đích**. Từ `occupations.csv` + `occupationSkillRelations.csv` dựng bảng `occupation_code → [skill_uri]` 1 lần | **2** (join 2 file theo URI) | Từ `user.occupation_code` tra bảng trên | **1** (lookup) |
| **O*NET** | `Skills.txt` + `Technology Skills.txt` → `onet_soc → [element]` | **2** | như trên, qua crosswalk ESCO↔O*NET | **2** (lookup + crosswalk) |
| **B1 asaniczka** | `job_skills.split(", ")` → chuẩn hoá chữ thường → **khớp mờ sang ESCO** (13.485 nhãn, phần lớn là cụm tự do như "Point to point wiring") | **3–4** (split, lowercase, fuzzy-match, ngưỡng) — matching là bước đắt nhất, tỉ lệ khớp **chưa đo được** | không có user | — |
| **B2 ravindra** | đã có `skills` nhưng **dữ liệu tổng hợp** | 1 (nhưng vô nghĩa) | không có user | — |
| **B3 data_jobs** | `ast.literal_eval(job_skills)` → list → khớp sang ESCO (246 nhãn phân biệt, sạch, chữ thường) | **2** (parse + match; 0 % lỗi parse) | không có user | — |
| **B4 Adzuna** | trích từ `description` bằng NER rồi match ESCO | **3** | không có user | — |
| **B5 USAJobs** | trích từ `QualificationSummary` | **3** | không có user | — |
| **B6 Arbeitnow** | `tags` là nhãn ngành, không phải skill → phải NER từ `description` | **4** | không có user | — |
| **C1 JobHop** | không có job | — | `user.resume_id → matched_code → ESCO occupation → occupationSkillRelations` | **2** (join 95 %) |
| **C2 resume-fit** | `job_description_text` phải NER | **3** | `resume_text` phải NER | **3** (và **không có giấy phép**) |

---

## KẾT LUẬN

### Tổ hợp cho đồ thị User–Job–Skill–Industry đầy đủ nhất

**Khuyến nghị: `lukebarousse/data_jobs` (B3) làm lớp Job–Skill + `ESCO v1.2.1` (A1) làm taxonomy + JobHop (C1) làm lớp User–Occupation.**

```
Node:
  Job      ← B3.data_jobs: 785.741 tin, 2023, Apache-2.0
  Skill    ← ESCO: 13.485 skill, có phân cấp nhóm, 28 ngôn ngữ (KHÔNG có tiếng Việt)
  Occupation ← ESCO: 2.942 nghề, map 1-1 ISCO-08
  Industry ← ISCO nhóm lớn (23) hoặc NACE crosswalk
  User     ← JobHop: 284.251 resume_id (chỉ khi chấp nhận miền Bỉ/Flanders)

Cạnh:
  Job   –Skill  : từ B3.job_skills (85,10 % tin có ≥1 skill, TB 5,45 skill/tin) match sang ESCO
  Job   –Occupation : từ B3.job_title khớp ESCO qua O*NET Alternate Titles (56.558 tên)
  Occupation–Skill  : ESCO occupationSkillRelations (~111.441 cạnh ước tính)
  User  –Occupation : JobHop.resume_id → matched_code (join 95,0 %)
  User  –Skill       : suy qua Occupation (KHÔNG phải kỹ năng tự khai)
```

**Điểm mạnh so với hiện trạng:** thay bộ MEDAJob 70 user/1.014 job/307 tương tác tổng hợp bằng **785.741 tin thật có cột skill**, và cột `company_name` điền **100 %** với **139.982** công ty — đây là **ứng viên cho cột đơn vị tuyển dụng để chia client FL**.

### Mất gì (phải nói thẳng với hội đồng)

1. **MẤT TƯƠNG TÁC NGƯỜI DÙNG–TIN THẬT.** Cả 3 nguồn B đều là *tin tuyển dụng*, không có click/apply/rating. Yêu cầu cứng (1) **không được thoả bởi tổ hợp này**. Không có cột `applies`/`views`/`rating` trong bất kỳ bộ nào ở trên. Bộ CareerBuilder 1,6 M tương tác vẫn là nguồn duy nhất cho (1), và nó **không nối được** sang B3 vì không có job_id chung.

2. **MẤT SKILL PHÍA ỨNG VIÊN.** JobHop cố tình **không phát hành** technical skills (trích nguyên văn README ở trên). C2 không có cột skill. Vậy `User–Skill` chỉ suy được **qua nghề**, không phải kỹ năng ứng viên tự khai. Đây là điểm yếu học thuật lớn nếu đề tài định mô hình hoá "user có kỹ năng gì".

3. **MẤT NGÀNH Ở MỨC TIN.** Không bộ B nào có cột `industry`. Chỉ suy được: B3 → `job_title_short` (không phải ngành) → nghề ESCO → ISCO nhóm lớn (23 nhóm). Adzuna có `category` (ngành) nhưng cần key và không có skill.

4. **MẤT TÍNH ĐA DẠNG MIỀN.** B3 chỉ là **data/analytics roles, năm 2023**. JobHop là **Bỉ/Flanders** (91,4 % tiếng Hà Lan). Ghép 2 bộ này là ghép **hai thị trường khác nhau** — phải khai báo rõ trong bài, không được trình bày như một dataset thống nhất.

5. **KHÔNG CÓ TIẾNG VIỆT Ở TAXONOMY.** ESCO có 28 ngôn ngữ, **không có `vi`** (đã kiểm bằng API). Nếu hội đồng hỏi "sao dùng taxonomy tiếng Anh": trả lời được rằng **không tồn tại taxonomy kỹ năng chuẩn nào có nhãn tiếng Việt** — ESCO, O*NET, Lightcast, LinkedIn đều không. Cách xử lý: giữ **mã URI/`skill_uri` làm khoá**, nhãn tiếng Anh chỉ là hiển thị, và tự dịch nhãn hiển thị sang tiếng Việt ở tầng UI (không đổi khoá).

6. **RỦI RO GIẤY PHÉP.** B1 ODC-By (ổn, cần ghi công), B2 CC0 nhưng **dữ liệu tổng hợp — không dùng**, B3 Apache-2.0 (ổn), ESCO 2011/833/EU (ổn, phải ghi công), O*NET CC BY 4.0 (ổn), **C2 không có giấy phép → không dùng được cho (5)**. Adzuna ToS **chưa đọc được** (403) → **chưa xác minh**.

### Nếu buộc phải chọn 1 tổ hợp tối thiểu để bảo vệ

- **Bắt buộc:** `ESCO v1.2.1` (taxonomy, offline, miễn phí) + `lukebarousse/data_jobs` (785.741 job, skill tường minh 85,10 %, Apache-2.0).
- **Cho client FL:** dùng `company_name` của data_jobs (**139.982** công ty, điền 100 %) — nhưng xem cảnh báo của t3 về việc chia client theo employer.
- **Cho user:** hoặc JobHop (nếu chấp nhận miền Bỉ, không có skill), hoặc **tự sinh user giả lập từ ESCO** và khai báo rõ là synthetic — nhưng khi đó quay lại đúng vấn đề của MEDAJob.
