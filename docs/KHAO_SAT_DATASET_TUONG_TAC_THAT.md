# Khảo sát bộ dữ liệu gợi ý việc làm có tương tác người dùng–tin THẬT

**Người thực hiện:** recsys-datasets (task t1) · **Ngày:** 2026-11-08
**Ràng buộc cứng của đề tài:** (1) tương tác user–job thật, (2) kỹ năng phía tin, (3) hồ sơ/kỹ năng phía ứng viên, (4) cột đơn vị tuyển dụng để chia client FL, (5) giấy phép dùng học thuật.

> **Quy ước mức xác minh** (bắt buộc đọc trước khi trích số):
> - **A = đã kiểm bằng schema/dữ liệu THẬT** — đọc trực tiếp header + quét toàn bộ file đếm dòng và đo **tỉ lệ lấp đầy (fill rate)** trên máy, hoặc qua API trả schema/dữ liệu thật (`datasets-server.huggingface.co/info|rows|statistics`).
> - **B = suy từ tài liệu chính thức của nhà phát hành** (trang mô tả, `.md` trong repo tổ chức, base paper có bảng số liệu, rules chính thức, **đặc tả DB của chính scraper sinh ra dữ liệu**). Không tự bịa schema từ mô tả marketing.
> - **C = chưa xác minh** — chỉ biết tên file/số byte, không đọc được cột.
>
> ### Ghi chú về mạng (đã đính chính — đừng hiểu sai là cả đội bị chặn mạng)
> Trên máy này: **`curl` hỏng** (luôn trả `000`), **`Invoke-WebRequest` của PowerShell hỏng**, **`web_fetch` thì chỉ đọc được trang, không tải file nhị phân**. **NHƯNG `python urllib.request` tải HTTPS bình thường** — đã tải thật 145.859.589 B và 237.415.736 B từ HuggingFace, tốc độ ~7 MB/s.
>
> ⚠️ **Bẫy đã mắc phải (ghi lại để không tái diễn):** lần đầu tôi test bằng cách pipe heredoc vào `python -`. Lệnh đó mở **REPL tương tác** chứ không chạy script, nên test "fail" là **dương tính giả** và tôi đã kết luận sai là mạng bị chặn. **Phải ghi script ra file `.py` rồi `python file.py`.**
>
> Mẫu tải đã dùng được:
> ```python
> import urllib.request
> req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
> with urllib.request.urlopen(req, timeout=180) as r, open(dest,'wb') as f:
>     while True:
>         c = r.read(1<<20)
>         if not c: break
>         f.write(c)
> ```
> **Cảnh báo kỹ thuật:** đếm dòng bằng `bytes.count(b'\n')` cho kết quả SAI với CSV có newline trong field. `xanderios` đếm thô ra 702.287 nhưng **parse CSV thật chỉ 33.246 dòng** (sai 21 lần). Luôn dùng `csv.reader`.

---

## 0. Kết luận đi trước (TL;DR)

> **ĐÍNH CHÍNH quan trọng (đọc trước):** phiên bản đầu của tài liệu này khẳng định "không bộ nào có employer_id". **Điều đó SAI.** Có ít nhất **3 bộ có cột employer thật, đã kiểm bằng dữ liệu thật**:
> - `lukebarousse/data_jobs` — `company_name` lấp đầy **100,00%** (785.740/785.741), **139.984 công ty phân biệt**
> - `xanderios/linkedin-job-postings` — `company_id` lấp đầy **98,03%** (32.592/33.246)
> - `datastax/linkedin_job_listings` — `company_name` lấp đầy **98,61%** (122.130/123.849)
> - Djinni job descriptions — `Company Name` lấp đầy **100,00%**, **4.997 công ty phân biệt** (mẫu 20.000 dòng)
>
> Kết luận đúng phải phát biểu là: **các bộ CÓ employer thì KHÔNG có tương tác user–job; bộ CÓ tương tác user–job thì KHÔNG có employer.** Đây là quan hệ loại trừ giữa (1) và (4), không phải "không bộ nào có employer".

1. **Không có một bộ public ĐƠN LẺ nào đạt đủ cả 5 ràng buộc.** Ràng buộc (4) và (1) loại trừ nhau trong toàn bộ danh sách khảo sát: không bộ nào vừa có tương tác user–job thật vừa có định danh đơn vị tuyển dụng.
2. **Phát hiện lớn nhất — `lukebarousse/data_jobs`:** bộ **DUY NHẤT** vừa có `company_name` (100%) vừa có **kỹ năng TƯỜNG MINH dạng cấu trúc**, không phải trích từ HTML: `job_skills` **85,10%** (668.704/785.741) là **list Python thật** (parse thành công 668.704/668.704, 0 lỗi), `job_type_skills` cùng tỉ lệ dạng **dict phân nhóm**. Thiếu: tương tác user–job và hồ sơ ứng viên.
3. Bộ tốt nhất về tương tác thật là **RecSys Challenge 2017 (XING)**: 7.267.094 tương tác dương, 6 loại tương tác tường minh, hồ sơ ứng viên phong phú, license học thuật. **Nhưng**: không có employer_id, kỹ năng chỉ là ID ẩn danh, và **phải xin approval qua tài khoản XING** → rủi ro tiến độ cao.
4. Bộ tương tác **đang có trên đĩa và đã kiểm schema thật** là **Kaggle CareerBuilder 2012** (1.603.111 application / 389.708 user / 1.092.096 job). Đã xác minh: **không có cột employer**, **không có cột kỹ năng**, Description/Requirements là HTML.
5. Đo trên dữ liệu thật: dùng **email domain trong text tin** làm proxy employer → phủ **21,32%** số application, nhưng top domain là **công ty headhunt** (volt.com, randstadusa.com, roberthalf.com) → proxy này đo *nhà tuyển dụng thuê ngoài*, không phải *doanh nghiệp tuyển dụng*. Không dùng làm nhãn FL tin cậy được.
6. **Khuyến nghị:** ghép **CareerBuilder (tương tác thật) + `lukebarousse/data_jobs` hoặc `arshkon` (employer + kỹ năng tường minh)** theo `company_name`/title; hoặc chia client FL theo block địa lý nếu không ghép được. Đừng đặt cược tiến độ vào XING hay Zhaopin.

---

## 1. Bảng tổng hợp (mỗi ứng viên 1 dòng)

| # | Tên + URL chính thức | Schema thực tế (tên cột) | Số dòng (user / job / tương tác) | Loại tương tác | Cột employer? | Kỹ năng phía tin | Ngày tháng | Giấy phép + đăng ký | Mật độ = I/(U×J) | Mức xác minh | Đạt yêu cầu cứng? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **RecSys Challenge 2016 (XING)** — http://2016.recsyschallenge.com/ · data: https://recsys.xing.com/data | `impressions.csv`: `user_id, year, week, items`<br>`interactions.csv`: `user_id, item_id, interaction_type, created_at`<br>`users.csv`: `id, jobroles, career_level, discipline_id, industry_id, country, region, experience_n_entries_class, experience_years_experience, experience_years_in_current, edu_degree, edu_fieldofstudies`<br>`items.csv`: `id, title, career_level, discipline_id, industry_id, country, region, latitude, longitude, employment, tags, created_at, active_during_test`<br>`target_users.csv` | 1.500.000 user (150K target) / 1.300.000 item (327K active) / **8.800.000** interaction / 202.000.000 impression | Ngầm, **tường minh theo loại**: 1=click, 2=bookmark, 3=reply, 4=delete. **Không có rating 1–5** | **KHÔNG.** `items.csv` không có company/employer id. Chỉ có `industry_id`, `discipline_id`, `tags` (concept ID trích từ tags/skills **hoặc tên công ty** — không tách được) | **Có nhưng vô dụng**: `tags`, `title`, `jobroles`, `edu_fieldofstudies` là **ID số đã ẩn danh**, không công bố codebook → không map ra tên kỹ năng | Timestamp đã dịch (order giữ nguyên); 16 tuần | **Độc quyền XING AG** ("All rights are reserved"). Chỉ học thuật, cấm thương mại, **cấm chia sẻ dataset**, phải chấp nhận rules + **được organizer duyệt** | 8.8M/(1.5M×1.3M) = **4,51e-06** (0,00045%); theo item active: 1,79e-05 | **B** (TrainingDataset.md chính thức + bảng số liệu paper Liu et al. 2016). Không tải được để kiểm A | ❌ Thiếu (2) đọc được, (4). Chặn bởi approval |
| 2 | **RecSys Challenge 2017 (XING)** — http://2017.recsyschallenge.com/ · data: https://recsys.xing.com/ | `interactions.csv`: `user_id, item_id, created_at, interaction_type`<br>`users.csv`: `id, jobroles, career_level, discipline_id, industry_id, country, region, experience_n_entries_class, experience_years_experience, experience_years_in_current, edu_degree, edu_fieldofstudies, wtcj, premium`<br>`items.csv`: `id, industry_id, discipline_id, is_paid, career_level, country, latitude, longitude, region, employment, created_at, title, tags`<br>`targetItems.csv`, `targetUsers.csv` | Offline: **1.497.020** user / **1.306.054** item / **314.501.101** impression + **7.267.094** tương tác dương (click 6.867.579 + bookmark 281.672 + reply 117.843) + delete 906.836 + recruiter-interest 100.971. Online: 963.346 / 853.058 | Ngầm, 6 loại: 0=impression, 1=click, 2=bookmark, 3=reply, 4=delete, **5=recruiter interest** (nhà tuyển dụng quan tâm ứng viên). **Không rating** | **KHÔNG.** Không có company/employer id. `items.is_paid` cho biết tin trả phí, không cho biết công ty. `interaction_type=5` là hành vi phía công ty nhưng **không kèm định danh công ty** | Như #1: `tags`/`title` là concept ID ẩn danh | Timestamp dịch; offline 2017-03-03→04-16, online 2017-05-01→06-04 | Như #1: **bản quyền XING AG**, học thuật, cấm chia sẻ, cần approval | Dương: 7.267.094/(1.497.020×1.306.054) = **3,72e-06** (0,00037%)<br>Tất cả event: **1,65e-04** (0,0165%) | **B** (trang dataset chính thức + Table 1 của Abel et al., RecSys'17 workshop summary, đọc từ nguồn LaTeX gốc) | ❌ Thiếu (2) đọc được, (4). Chặn bởi approval |
| 3 | **Kaggle Job Recommendation Challenge (CareerBuilder 2012)** — https://www.kaggle.com/c/job-recommendation · **bản đang có trên đĩa** `E:\2026\DUT\IOT\Cuoiki\NewData` | `apps.tsv`: `UserID, WindowID, Split, ApplicationDate, JobID`<br>`users.tsv`: `UserID, WindowID, Split, City, State, Country, ZipCode, DegreeType, Major, GraduationDate, WorkHistoryCount, TotalYearsExperience, CurrentlyEmployed, ManagedOthers, ManagedHowMany`<br>`jobs.tsv`: `JobID, WindowID, Title, Description, Requirements, City, State, Country, Zip5, StartDate, EndDate`<br>`user_history.tsv`: `UserID, WindowID, Split, Sequence, JobTitle`<br>(+ `window_dates.tsv`, `test_users.tsv`, `splitjobs.zip` trong bản gốc — **thiếu trên đĩa**) | **1.603.111** application / **389.708** user (**321.235** user có application) / **1.092.096** job (**365.668** job có application)<br>`user_history.tsv`: 1.753.901 dòng, 375.531 user, **657.226** JobTitle phân biệt, TB 4,67 job lịch sử/user | **Tường minh**: `apps.tsv` = hành vi **apply** (đơn ứng tuyển thật). **Không rating 1–5** | **KHÔNG — đã kiểm bằng header thật.** Không có cột employer/company/job_board trong bất kỳ file nào | **KHÔNG có cột kỹ năng.** `Description` + `Requirements` là **HTML thô**: 1.009.435/1.092.096 tin (92,4%) chứa thẻ HTML → phải trích. Phía ứng viên: `user_history.JobTitle` (free text) + `DegreeType`/`Major` | `jobs.StartDate` 2012-03-02→2012-06-30; `EndDate` 2012-04-01→2012-07-30; `apps.ApplicationDate` 2012-04-01 00:00:21 → 2012-06-26 23:59:55 (quét toàn bộ) | **Không có license mở.** Rules chính thức: dữ liệu chỉ dùng **cho mục đích cuộc thi**, và "promptly after the Competition ends, Entrants must cease all use of the Data … and erase or otherwise destroy". Cần tài khoản Kaggle để tải | 1.603.111/(389.708×1.092.096) = **3,77e-06** (0,000377%)<br>Theo user/job active: **1,365e-05** (0,001365%) | **A — đã kiểm bằng schema + đếm dòng thật trên đĩa** (4 file, header khớp 100% tài liệu Kaggle) | ❌ Thiếu (2) structured, (4) employer, (5) license học thuật rõ ràng — nhưng là bộ **duy nhất đã kiểm thật** |
| 4 | **OLX Jobs Interactions** — https://www.kaggle.com/datasets/olxdatascience/olx-jobs-interactions | `interactions.csv`: `user, item, event, timestamp` — **chỉ 4 cột, 1 file duy nhất**. `README.txt` 5.076 B | **65.502.201** event / **3.295.942** user / **185.395** job ad (2 tuần 2020) | Ngầm, 8 loại tường minh: `click, bookmark, chat_click, contact_phone_click_1/2/3, contact_partner_click, contact_chat` | **KHÔNG.** Không có file metadata job nào → không có title, không company, không địa điểm | **KHÔNG có gì.** Không có text tin, không có kỹ năng | Unix timestamp, **đã cộng hằng số ẩn**; 2 tuần 2020 | Custom "Other": **được dùng cho nghiên cứu học thuật**, phi thương mại, **cấm đăng lại dataset**, phải acknowledge + **gửi bản publication cho OLX**, có thể bị thu hồi. Tải cần tài khoản Kaggle | 65.502.201/(3.295.942×185.395) = **1,072e-04** (0,01072%) | **A** (file list + byte size qua `api/v1/datasets/list`) + **B** (mô tả chính thức có cột + license đầy đủ) | ❌ Thiếu (2), (3), (4) — chỉ có ma trận tương tác thuần |
| 5 | **HF `xanderios/linkedin-job-postings`** — https://huggingface.co/datasets/xanderios/linkedin-job-postings | `job_id, company_id, title, description, max_salary, med_salary, min_salary, pay_period, formatted_work_type, location, applies, original_listed_time, remote_allowed, views, job_posting_url, application_url, application_type, expiry, closed_time, formatted_experience_level, skills_desc, listed_time, posting_domain, sponsored, work_type, currency, compensation_type, scraped` (**28 cột**) | **33.246** dòng (parse CSV thật; đếm thô theo `\n` ra 702.287 là SAI vì newline trong field). 1 file `job_postings.csv` 134.845.243 B | **KHÔNG có tương tác user–item.** Chỉ có `applies` (**48,84%** lấp đầy — quét toàn file) và `views` (**77,86%**) là **đếm gộp theo tin**, không có user ID | **CÓ `company_id`** — **98,03%** lấp đầy (32.592/33.246), float64 | **KHÔNG.** `skills_desc` chỉ **1,01%** lấp đầy (337/33.246). `description` là text thường | `original_listed_time` 2023-06-08 → 2023-11-04 | **MIT** (declared). Không cần đăng ký | N/A (không có ma trận user–item) | **A — đã tải & quét toàn bộ 134,8 MB bằng `csv.reader`** | ❌ Thiếu (1) tương tác thật — chỉ là bảng tin. **Thoả (4)** |
| 5b | **HF `datastax/linkedin_job_listings`** (mirror của arshkon, có thêm cột) — https://huggingface.co/datasets/datastax/linkedin_job_listings | `job_id, company_name, title, description, max_salary, pay_period, location, company_id, views, med_salary, min_salary, formatted_work_type, applies, original_listed_time, remote_allowed, job_posting_url, application_url, application_type, expiry, closed_time, formatted_experience_level, skills_desc, listed_time, posting_domain, sponsored, work_type, currency, compensation_type, normalized_salary, zip_code, fips` (**31 cột**) | **123.849** dòng (parse CSV thật). 1 file `postings.csv` 516.843.769 B | **KHÔNG có tương tác user–item** | **CÓ cả `company_name` và `company_id`**: `company_name` lấp đầy **98,61%** (122.130/123.849) | **KHÔNG.** `skills_desc` chỉ **1,97%** (2.439/123.849) | `listed_time` 2024-03 → 2024-04 | **Chưa thấy license khai báo** trên HF card (Kế thừa từ arshkon: CC BY-SA 4.0) | N/A | **A — đã quét toàn bộ 516,8 MB** | ❌ Thiếu (1), (2) structured. **Thoả (4) tốt nhất** |
| 5c | **HF `lukebarousse/data_jobs`** ⭐ **PHÁT HIỆN LỚN NHẤT** — https://huggingface.co/datasets/lukebarousse/data_jobs | `job_title_short, job_title, job_location, job_via, job_schedule_type, job_work_from_home, search_location, job_posted_date, job_no_degree_mention, job_health_insurance, job_country, salary_rate, salary_year_avg, salary_hour_avg, company_name, job_skills, job_type_skills` (**17 cột**) | **785.741** dòng (API + parse CSV thật). 1 file `data_jobs.csv` 231.152.089 B | **KHÔNG có tương tác user–job.** Không có cột user/applicant nào (đã kiểm) | ✅ **CÓ `company_name` — lấp đầy 100,00%** (785.740/785.741), **139.984 công ty phân biệt** | ✅ **CÓ KỸ NĂNG TƯỜNG MINH DẠNG CẤU TRÚC:** `job_skills` **85,10%** (668.704/785.741) — **list Python thật**, parse `ast.literal_eval` thành công 668.704/668.704 (**0 lỗi**), vd `['r','python','sql','nosql','power bi','tableau']`; `job_type_skills` **85,10%** — **dict phân nhóm** `{'analyst_tools':[...],'programming':[...]}`. **KHÔNG phải trích từ HTML** | `job_posted_date` (2023, theo mô tả tác giả) | **Apache-2.0** (theo card HF). Không cần đăng ký | N/A | **A — đã tải & quét toàn bộ 231 MB, đo fill rate chính xác từng cột** | ⚠️ **Thoả (2) + (4) + (5)**, thiếu (1) và (3) |
| 6 | **Kaggle `arshkon/linkedin-job-postings`** (bản gốc của #5b) — https://www.kaggle.com/datasets/arshkon/linkedin-job-postings | `postings.csv` (schema như #5b, 516.843.769 B). Thêm: `companies/companies.csv` (`company_id, name, description, company_size, country, state, city, zip_code, address, url`), `company_industries.csv`, `company_specialities.csv`, `employee_counts.csv`, `jobs/benefits.csv`, `jobs/job_industries.csv`, **`jobs/job_skills.csv` (3.506.651 B)**, `salaries.csv`, `mappings/industries.csv`, **`mappings/skills.csv` (679 B)**<br>**Schema `job_skills.csv` (từ đặc tả DB của scraper `DatabaseStructure.md`): `job_id, skill_abr`**<br>**Schema `mappings/skills.csv`: `skill_abr, skill_name`** | ~**123.849** job posting (khớp datastax mirror) | **KHÔNG có tương tác user–item** | **CÓ — tốt nhất trong danh sách**: `company_id` + `companies.name`, 98,61% | **CÓ — bảng kỹ năng CÓ CẤU TRÚC**, quan hệ nhiều-nhiều: `job_skills(job_id, skill_abr)` ⨝ `mappings/skills(skill_abr, skill_name)`. ⚠️ **Chưa tải được file để đếm dòng** (Kaggle API trả 404 không auth) → **số dòng `job_skills.csv` = CHƯA XÁC MINH** | 2023-11 → 2024-05 | **CC BY-SA 4.0** — học thuật OK, phải ghi công + share-alike. **Cần tài khoản Kaggle** | N/A (không có ma trận) | **A** cho `postings` (qua datastax mirror); **B** cho schema `job_skills`/`skills` (đặc tả DB chính thức của scraper sinh ra dataset); **C** cho số dòng `job_skills.csv` | ❌ Thiếu (1). **Nguồn thuộc tính tốt nhất** để ghép |
| 6b | **HF `lang-uk/recruitment-dataset-job-descriptions-english` (Djinni)** — https://huggingface.co/datasets/lang-uk/recruitment-dataset-job-descriptions-english | `Position, Long Description, Company Name, Exp Years, Primary Keyword, English Level, Published, Long Description_lang, id, __index_level_0__` (**10 cột**) | **141.897** dòng (`parquet` 145.859.589 B) | **KHÔNG có tương tác** | ✅ **CÓ `Company Name` — lấp đầy 100,00%** (mẫu 20.000 dòng / 142 row group), **4.997 công ty phân biệt** | **KHÔNG structured.** `Primary Keyword` chỉ **42 giá trị phân biệt** (quá thô); kỹ năng nằm trong `Long Description` text | `Published` 2020-10 → 2022-03 (ISO8601 có offset) | **MIT** | N/A | **A — đã tải & đọc schema parquet thật** | ❌ Thiếu (1), (2) structured. **Thoả (4)** |
| 6c | **HF `lang-uk/recruitment-dataset-candidate-profiles-english` (Djinni)** ⭐ **nguồn hồ sơ ứng viên** — https://huggingface.co/datasets/lang-uk/recruitment-dataset-candidate-profiles-english | `Position, Moreinfo, Looking For, Highlights, Primary Keyword, English Level, Experience Years (double), CV, CV_lang, id, __index_level_0__` (**11 cột**) | **210.250** dòng (`parquet` 237.415.736 B) | **KHÔNG có tương tác** | Không (phía ứng viên) | Không (phía ứng viên) | 2020–2023 | **MIT** | N/A | **A — đã tải & đọc schema parquet thật** | Bổ sung **(3) hồ sơ ứng viên thật**: `CV` 100%, `Experience Years` 100%, `Primary Keyword` 99,94%, `English Level` 99,80%, `Highlights` 49,45%, `Looking For` 47,33% |
| 7 | **Kaggle `kandij/job-recommendation-datasets`** — https://www.kaggle.com/datasets/kandij/job-recommendation-datasets | 5 file, Kaggle báo "57 columns" tổng: `Combined_Jobs_Final.csv` (158,6 MB), `Experience.csv` (2,8 MB), `Job_Views.csv` (3,3 MB), `Positions_Of_Interest.csv` (478 KB), `job_data.csv` (87,0 MB).<br>Đọc được từ preview: `job_data.csv` = `id, text` (mô tả tin, **đã stemming/bị cắt cụt**); `Positions_Of_Interest.csv` = `UserID, Position, Date1, Date2`; `Job_Views.csv` = `id, JobID, Title, Company, City, State, StateAbbr, <col>, Date` (**có Company!**) | `job_data.csv` 84.089 dòng; `Job_Views.csv` ~14.546 dòng; `Positions_Of_Interest.csv` ~14.500 dòng; `Combined_Jobs_Final.csv` ~? | **KHÔNG phải tương tác thật user→job.** `Job_Views.csv` = **đếm lượt xem theo tin** (cột số 42→14.616) + tên công ty, **không có user ID**. `Positions_Of_Interest.csv` = chức danh quan tâm, không trỏ tới JobID | **CÓ `Company` trong `Job_Views.csv`** — nhưng bảng này không có user | **KHÔNG** structured | 2014-08-14 → 2015-03-08 | **License = "Unknown"** (trường Kaggle). Đây là bản crawl lại, không phải dữ liệu gốc cuộc thi | N/A | **A** (file list + byte size + preview cột) | ❌ Thiếu (1). License Unknown = chặn (5) |
| 8 | **Kaggle `kshitizregmi/jobs-and-job-description`** — https://www.kaggle.com/datasets/kshitizregmi/jobs-and-job-description | 1 file `job_title_des.csv` (4.595.963 B), 2 cột theo mô tả: `Job Title`, `Job Description` | ~? (không đếm được) | **KHÔNG có tương tác** | **KHÔNG** | **KHÔNG** | Không có | **CC0** | N/A | **A** (file list); **B** (2 cột chỉ từ mô tả) | ❌ Thiếu (1),(2),(3),(4) |
| 9 | **Zhaopin 智联招聘人岗智能匹配 (Tianchi 31623)** — https://tianchi.aliyun.com/dataset/31623 | `table1_user.txt` (2,47 MB), `table2_jd.txt` (273,78 MB), `table3_action.txt` (48,13 MB). **Tên cột: CHƯA XÁC MINH** | **Chưa xác minh số dòng** | Paper OKRA (arXiv:2504.07108, ECIR'25) xác nhận nhãn **0–3**: 0=không tương tác, 1=tương tác, 2=application, 3=hire → **tương tác thật + tường minh** | **Chưa xác minh** | **Chưa xác minh** (paper nói có skills + job description/requirements dạng text) | Chưa xác minh | **CC-BY-SA-NC 4.0** (hiển thị trên trang). **Đã thử 4 endpoint API: đều trả shell SPA (HTML, không JSON)** → **XÁC NHẬN phải có tài khoản Tianchi + verify sinh viên**. | Chưa xác minh | **B** (license + tên file + nhãn 0–3 từ paper) / **C** (schema, số dòng) | ❌ **Không lấy được schema — bỏ qua, không làm điểm chặn.** Lưu ý: bộ còn lại trong OKRA là "proprietary commercial dataset" của XING, **không công bố** |
| 10 | **Kaggle `asaniczka/1-3m-linkedin-jobs-and-skills-2024`** — https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024 | **CHƯA XÁC MINH** (chỉ đọc mô tả marketing: job listings + skills) | ~1.300.000 job listing (theo mô tả) | Mô tả **không** nhắc tương tác user–item | Theo mô tả: có company name (chưa xác minh) | Theo mô tả: có (chưa xác minh) | 2024 | **ODC-By** | N/A | **C — chưa xác minh schema** | ❌ Thiếu (1) theo mô tả; **phải kiểm schema trước khi dùng** |
| 11 | **JobHop (UGent)** — https://huggingface.co/datasets/aida-ugent/JobHop | `resume_id, matched_code, start_date, end_date, university_level` | train **1.594.827** / val 199.587 / test 198.877 | **KHÔNG có tương tác user–job** (chỉ quỹ đạo nghề nghiệp) | Không | Chỉ `matched_code` (ESCO occupation) | Theo quý | **CC-BY-4.0** | N/A | **A** (`datasets-server/info`) | ❌ Thiếu (1) hoàn toàn |
| 12 | **Djinni (lang-uk)** — https://huggingface.co/datasets/lang-uk/recruitment-dataset-candidate-profiles-english · `-job-descriptions-english` | Ứng viên: `Position, Moreinfo, Looking For, Highlights, Primary Keyword, English Level, Experience Years, CV, CV_lang, id, __index_level_0__`<br>Tin: `Position, Long Description, Company Name, Exp Years, Primary Keyword, English Level, Published, Long Description_lang, id, __index_level_0__` | Ứng viên **210.250**; tin **141.897** | **KHÔNG có tương tác** — 2 bảng rời, không có khoá nối hành vi | **CÓ `Company Name`** phía tin | **KHÔNG structured** — chèn trong `Long Description`/`CV` text | 2020–2023 | **MIT** (cả 2) | N/A | **A** (`datasets-server/info` cả 2 repo) | ❌ Thiếu (1) |

---

## 2. Ba bộ "manh mối bắt buộc kiểm" — kết quả kiểm

### 2.1 RecSys Challenge 2016 (XING) — ứng viên số 1
- **Xác nhận KHÔNG có bảng ~1,5M job posting như nghi vấn ban đầu.** Trang chủ nói XING *nền tảng* có "more than 15 Million users và around 1 Million job postings", nhưng **dataset phát hành** chỉ là "semi-synthetic sample": 1.500.000 user và **1.300.000 item** (paper Liu et al., Table 1), trong đó chỉ **327.000 item là active** trong tuần test.
- **Dataset là bán tổng hợp (semi-synthetic)**: có user nhân tạo, có tương tác nhân tạo, timestamp dịch, ~1/3 ground truth giấu. → Không phải "tương tác thật 100%", dù phần lõi là log XING thật.
- **Download bắt buộc**: tài khoản XING → chấp nhận rules → **được organizer approve**. Không có mirror chính thức. (Đã kiểm `RecoHut-Datasets/xing` trên GitHub: repo **chỉ có README.md 48 B + .gitignore**, không có data — kiểm qua jsDelivr API.)
- **License**: "All rights are reserved by XING AG"; cấm chia sẻ dataset; cấm thương mại; chỉ học thuật. → Về mặt *giấy phép dùng học thuật* thì **đạt (5)**, nhưng **không thể tái phân phối** → không đính kèm được vào bài nộp.

### 2.2 RecSys Challenge 2017 (XING)
- **Đây là bộ giàu tương tác nhất trong tất cả ứng viên**: 314,5M impression + 7,27M tương tác dương + 906.836 delete + **100.971 recruiter-interest** (tín hiệu hai chiều: ứng viên quan tâm VÀ nhà tuyển dụng quan tâm).
- **Vẫn KHÔNG có employer_id.** Có `items.is_paid` và `users.premium` để cân bằng doanh thu, nhưng không có định danh công ty. → **Không chia client FL theo employer được.**
- Cùng rào cản approval + cấm chia sẻ như 2016.

### 2.3 Kaggle CareerBuilder — đối chiếu bản gốc vs bản nhóm đã crawl
- **Khớp 100%**: bản trên đĩa có đúng 4/7 file của cuộc thi (`apps.tsv`, `users.tsv`, `jobs.tsv`, `user_history.tsv`), header khớp từng ký tự với tài liệu chính thức. **Thiếu 3 file**: `window_dates.tsv`, `test_users.tsv`, `splitjobs.zip` (+ `popular_jobs.py/.csv`).
- **Bản gốc Kaggle KHÔNG có cột nào khác** — tài liệu chính thức liệt kê đúng các cột trên đĩa đã có. Không có employer, không có skills, không có rating. → **Xác nhận: thiếu employer_id và skills là thuộc tính của bộ dữ liệu gốc, không phải lỗi lúc crawl.**
- **Hệ quả quyết định:** nhóm không thể "crawl bù" employer từ CareerBuilder gốc — nó không tồn tại trong nguồn.
- **Ràng buộc pháp lý:** rules chính thức yêu cầu **huỷ toàn bộ dữ liệu sau cuộc thi** ("cease all use … and erase or otherwise destroy"). Đây là rủi ro (5) nghiêm trọng nếu dùng cho đồ án.

---

## 3. Đo lường mới (tự thực hiện trên dữ liệu thật)

### 3.1 Mật độ ma trận tương tác (mục 9)

| Bộ | Tương tác | User | Job | Mật độ | % |
|---|---|---|---|---|---|
| CareerBuilder (toàn bộ) | 1.603.111 | 389.708 | 1.092.096 | 3,767e-06 | 0,000377% |
| CareerBuilder (chỉ user/job có tương tác) | 1.603.111 | 321.235 | 365.668 | **1,365e-05** | 0,001365% |
| XING 2017 (chỉ tương tác dương) | 7.267.094 | 1.497.020 | 1.306.054 | 3,717e-06 | 0,000372% |
| XING 2017 (mọi event) | 322.776.002 | 1.497.020 | 1.306.054 | 1,651e-04 | 0,016509% |
| XING 2016 | 8.800.000 | 1.500.000 | 1.300.000 | 4,513e-06 | 0,000451% |
| XING 2016 (item active) | 8.800.000 | 1.500.000 | 327.000 | 1,794e-05 | 0,001794% |
| OLX | 65.502.201 | 3.295.942 | 185.395 | **1,072e-04** | 0,010720% |

→ **CareerBuilder và XING có mật độ cùng bậc (10⁻⁶–10⁻⁵)**, tức đều cực thưa; OLX dày hơn ~8–28 lần nhưng không có thuộc tính tin.

### 3.2 Thử nghiệm proxy employer trên CareerBuilder (đo trên 1.092.096 tin + 1.603.111 application)

| Phương pháp trích employer từ text | Kết quả | Đánh giá |
|---|---|---|
| Regex field "Company:/Employer:" tường minh | **0,17%** (34/20.000 tin) | Vô dụng |
| Hậu tố pháp lý (`Inc, LLC, Corp…`) — mẫu 20.000 tin | 30,93% | Nhiễu cao (khớp cả "Life Insurance", "Paid medical insurance") |
| Tên công ty ở dòng đầu (có hậu tố) — mẫu 50.000 | **2,03%** | Vô dụng |
| **Email domain (loại freemail)** | 131.634/1.092.096 tin = **12,05%**; phủ **341.797/1.603.111 application = 21,32%**; 16.106 domain | **Dùng được về mặt kỹ thuật nhưng sai ngữ nghĩa** |
| Domain website (loại domain nền tảng) — mẫu 50.000 | 12,92% phủ bởi 320 domain ≥5 tin; top là facebook/twitter/youtube | Nhiễu, loại |
| Block địa lý (City, State) — mẫu 100.000 | **7.333** block phân biệt; 69 block ≥200 tin phủ **36,21%** | Không phải employer, nhưng **ổn định và không cần NLP** |

**Top email domain (đo thật):** `volt.com` 13.675 · `randstadusa.com` 6.170 · `careerlisterapp.com` 3.827 · `roberthalf.com` 2.982 · `spherion.com` 2.928 · `adeccona.com` 2.059 · `webhrdept.com` 1.730 · `selfopportunity.com` 1.707.

→ **Phát hiện quan trọng:** các "employer" trích được **chính là công ty tuyển dụng/headhunt** (Volt, Randstad, Robert Half, Adecco, Spherion). Chỉ **20 domain ≥1.000 application** và chúng chỉ phủ **51.718 application (3,23%)**. Nếu dùng làm client FL, ta sẽ chia client theo *công ty thuê ngoài*, không theo *doanh nghiệp thật* — làm sai lệch hoàn toàn giả định FL "mỗi client là một đơn vị tuyển dụng".

### 3.3 Hồ sơ ứng viên CareerBuilder (độ đầy đủ, đo thật trên 389.708 user)

`City` 100% · `State` 99,87% · `ZipCode` 99,55% · `DegreeType` 100% · `Major` **75,14%** · `GraduationDate` **69,15%** · `WorkHistoryCount` 100% · `TotalYearsExperience` **96,36%** · `CurrentlyEmployed` **89,20%** · `ManagedOthers`/`ManagedHowMany` 100%.
`user_history`: 375.531/389.708 user (96,4%) có ≥1 job lịch sử; 657.226 JobTitle phân biệt; TB 4,67 job/user.

→ **Đạt (3) ở mức trung bình**: hồ sơ có cấu trúc (bằng cấp, chuyên ngành, số năm KN) + lịch sử chức danh free-text. **Không có kỹ năng dạng cấu trúc.**

### 3.4 Fill rate thật của các bộ mới kiểm (quét TOÀN BỘ file, không lấy mẫu 100 dòng)

**`lukebarousse/data_jobs` — 785.741 dòng, quét 100% file (50,6 s):**

| Cột | Lấp đầy | % | Ghi chú |
|---|---|---|---|
| `job_title_short` | 785.741 | **100,00%** | |
| `job_title` | 785.740 | **100,00%** | |
| `company_name` | 785.740 | **100,00%** | **139.984 công ty phân biệt** → thoả (4) |
| `job_location` | 784.696 | 99,87% | |
| **`job_skills`** | **668.704** | **85,10%** | **list Python thật, parse OK 668.704/668.704, 0 lỗi** → thoả (2) |
| **`job_type_skills`** | **668.704** | **85,10%** | dict phân nhóm |

⚠️ **Lưu ý về sai lệch mẫu:** đo trên 100 dòng đầu (API `rows`) cho `job_skills` = 89%. Quét toàn bộ file cho **85,10%**. Chênh 3,9 điểm — **luôn quét toàn bộ khi được**, đừng tin mẫu 100 dòng.

Ví dụ `job_skills` thật:
```
['r', 'python', 'sql', 'nosql', 'power bi', 'tableau']
['python', 'sql', 'c#', 'azure', 'airflow', 'dax', 'docker', 'kubernetes', 'jenkins']
['python', 'c++', 'java', 'matlab', 'aws', 'tensorflow', 'keras', 'pytorch']
```
**Không có cột user/applicant nào** (đã kiểm): `[h for h in header if 'user' in h.lower() or 'applicant' in h.lower()] == []`.

**`xanderios/linkedin-job-postings` — 33.246 dòng, quét 100% (26,6 s):** `applies` 16.238 (**48,84%**), `views` 25.886 (**77,86%**), `skills_desc` 337 (**1,01%**), `company_id` 32.592 (**98,03%**).
→ Số `applies`/`views` này **khác** mẫu 100 dòng (26%/55%) — lại là bằng chứng phải quét toàn bộ.

**`datastax/linkedin_job_listings` — 123.849 dòng, quét 100% (67,0 s):** `company_name` 122.130 (**98,61%**), `views` 122.160 (98,64%), `applies` 23.320 (**18,83%**), `skills_desc` 2.439 (**1,97%**).

**Djinni job descriptions — 141.897 dòng (mẫu 20.000 dòng / 142 row group):** `Company Name` **100,00%** (4.997 công ty phân biệt), `Position` 100%, `Primary Keyword` 100% nhưng chỉ **42 giá trị phân biệt** (quá thô để làm kỹ năng), `Long Description` 100%, `Published` 100%.

**Djinni candidate profiles — 210.250 dòng (mẫu 20.000 dòng / 211 row group):** `Position` 100%, `Moreinfo` 100%, `Experience Years` 100%, `CV` 100%, `Primary Keyword` 99,94%, `English Level` 99,80%, `Highlights` 49,45%, `Looking For` 47,33%.
→ **Đây là nguồn hồ sơ ứng viên thật tốt nhất tìm được**: 210.250 CV, license MIT, tải công khai không cần đăng ký.

### 3.5 Cột nào dùng được cho yêu cầu (2) kỹ năng JOB và (3) kỹ năng USER

| Bộ | (2) Kỹ năng phía JOB | (3) Kỹ năng/hồ sơ phía USER | Đánh giá |
|---|---|---|---|
| **`lukebarousse/data_jobs`** | ✅ **`job_skills`** (list, 85,10%) + **`job_type_skills`** (dict phân nhóm, 85,10%) | ❌ | **Tốt nhất cho (2)**, không cần NLP |
| **`arshkon`** | ✅ **`job_skills(job_id, skill_abr)` ⨝ `mappings/skills(skill_abr, skill_name)`** | ❌ | Chuẩn hoá tốt (skill_abr), nhưng cần tải Kaggle |
| **Djinni job desc** | ❌ chỉ `Primary Keyword` (42 giá trị) | — | Phải trích từ `Long Description` |
| **Djinni candidate profiles** | — | ✅ **`CV`** (100%) + `Highlights` + `Primary Keyword` + `Experience Years` | **Tốt nhất cho (3)**, nhưng kỹ năng phải trích từ CV text |
| **CareerBuilder** | ❌ | ⚠️ `user_history.JobTitle` + `Major` + `DegreeType` | Cả hai phía đều phải trích từ text/HTML |
| **XING 2016/2017** | ⚠️ `items.tags` (ID ẩn danh, không codebook) | ⚠️ `users.jobroles`, `edu_fieldofstudies` (ID ẩn danh) | **Không map ra tên kỹ năng được** |

---

## 4. Xếp hạng ứng viên + khuyến nghị

### 4.1 Xếp hạng theo mức đáp ứng ràng buộc cứng

| Hạng | Bộ | (1) Tương tác thật | (2) Kỹ năng tin | (3) Hồ sơ UV | (4) Employer | (5) License HT | Tổng | Ghi chú |
|---|---|---|---|---|---|---|---|---|
| **1** | **lukebarousse/data_jobs** | ❌ | ✅ **TƯỜNG MINH, 85,10%, list thật** | ❌ | ✅ **100,00%, 139.984 cty** | ✅ Apache-2.0 | **3/5** | ⭐ **Bộ duy nhất có cả (2) và (4) thật.** Thiếu (1),(3) |
| **2** | **XING 2017** | ✅ 7,27M dương, 5 loại | ⚠️ có nhưng ID ẩn danh | ✅ rất giàu | ❌ | ✅ (cấm chia sẻ) | **3,5/5** | Tốt nhất về (1)+(3); **chặn bởi approval** |
| **3** | **CareerBuilder 2012** (đang có) | ✅ 1,6M apply thật | ❌ HTML | ✅ khá | ❌ | ❌ rules cấm dùng sau thi | **2/5** | **Đã kiểm thật, sẵn sàng dùng ngay** |
| 4 | **Djinni (2 repo ghép)** | ❌ | ❌ (chỉ 42 Primary Keyword) | ✅ **CV thật 210.250** | ✅ **100,00%, 4.997 cty** | ✅ MIT | **2,5/5** | Nguồn (3)+(4) tốt, cùng nền tảng nên ghép tự nhiên |
| 5 | **arshkon LinkedIn** | ❌ | ✅ structured (job_skills⨝skills) | ❌ | ✅ **98,61%** | ✅ CC BY-SA | **2,5/5** | Nguồn thuộc tính tốt nhất; cần tài khoản Kaggle |
| 6 | **datastax LinkedIn** | ❌ | ❌ (skills_desc 1,97%) | ❌ | ✅ **98,61%** | ⚠️ chưa khai báo | **1,5/5** | Mirror công khai của arshkon `postings`, không có bảng skills |
| 7 | XING 2016 | ✅ 8,8M | ⚠️ ID ẩn danh | ✅ | ❌ | ✅ | 3,5/5 | Như 2017 nhưng ít loại tương tác hơn |
| 8 | OLX | ✅ 65,5M | ❌ | ❌ | ❌ | ✅ | 1,5/5 | Chỉ dùng làm **ma trận tương tác thuần** |
| 9 | xanderios LinkedIn | ❌ | ❌ (skills_desc 1,01%) | ❌ | ✅ **98,03%** | ✅ MIT | 1,5/5 | Bản rút gọn của arshkon, không có tên công ty |
| 10 | Zhaopin (Tianchi) | ⚠️ nhãn 0–3 theo paper | ⚠️ chưa xác minh | ⚠️ chưa xác minh | ⚠️ chưa xác minh | ✅ CC-BY-SA-NC | **?/5** | **Không lấy được schema — bỏ qua, không làm điểm chặn** |
| 11 | kandij | ❌ | ❌ | ❌ | ⚠️ Company nhưng không có user | ❌ Unknown | 0,5/5 | **Loại** |
| 12 | kshitizregmi | ❌ | ❌ | ❌ | ❌ | ✅ CC0 | 0,5/5 | **Loại** |
| 13 | asaniczka 1.3M | ❌ | ⚠️ chưa xác minh | ❌ | ⚠️ chưa xác minh | ✅ ODC-By | ?/5 | **Chưa xác minh** (Kaggle yêu cầu auth) |
| 14 | JobHop | ❌ | ❌ | ✅ | ❌ | ✅ | 1/5 | **Loại** |

### 4.2 Khuyến nghị hành động

**(A) ⭐ Ưu tiên mới — ghép 2 bộ để phủ (1)+(2)+(3)+(4):**
- Trục tương tác thật: **CareerBuilder** (đã có, 1.603.111 apply) hoặc XING 2017 (nếu xin được approval).
- Trục thuộc tính: **`lukebarousse/data_jobs`** (company_name 100% + job_skills list thật) hoặc **arshkon** (company_id + job_skills⨝skills).
- Ghép theo `company_name` đã chuẩn hoá + `job_title`/`job_title_short`.
- ⚠️ **Cảnh báo trung thực:** ghép là join ngoài miền (CareerBuilder 2012 vs LinkedIn 2023–2024 vs Djinni 2020–2023), **không có khoá ngoại thật**. Phải ghi rõ đây là *ghép suy luận* và báo cáo tỉ lệ khớp được, không được trình bày như dữ liệu nguyên bản.

**(B) Nếu không ghép được — dùng ngay, không chặn tiến độ:**
CareerBuilder + chia client FL bằng **block địa lý `(City, State)`** thay cho employer. Đo thật: 7.333 block, 69 block ≥200 tin phủ 36,21% job → đủ 5–12 client FL. **Phải ghi rõ** đây là proxy địa lý, không phải employer. Kỹ năng phía tin: trích từ HTML `Description`+`Requirements` (92,43% có HTML) — dùng ESCO/O*NET (xem kết quả của `skills-data`) làm từ điển.

**(C) Trung hạn — nếu xin được approval:** XING 2017 đúng ngữ nghĩa nhất. Nhưng **cấm tái phân phối** + cần tài khoản XING → xin trước, không để thành đường găng.

**(D) Zhaopin/Tianchi:** **đã xác nhận không lấy được** (4 endpoint API đều trả shell SPA; cần tài khoản + verify sinh viên). Giữ ở mức C, **bỏ qua, không chặn**. Lưu ý thêm: bộ còn lại trong paper OKRA là "proprietary commercial dataset" của XING, **cũng không công bố**.

### 4.3 Bộ nào ĐÃ XÁC MINH bằng schema thật vs chỉ suy từ tài liệu

| Đã xác minh schema THẬT (mức A) | Chỉ suy từ tài liệu chính thức (mức B) | Chưa xác minh (mức C) |
|---|---|---|
| • **`lukebarousse/data_jobs`** — tải & quét toàn bộ 231 MB, fill rate từng cột<br>• **`datastax/linkedin_job_listings`** — quét toàn bộ 516,8 MB<br>• **`xanderios/linkedin-job-postings`** — quét toàn bộ 134,8 MB<br>• **Djinni job descriptions** — tải parquet, đọc schema + 20/142 row group<br>• **Djinni candidate profiles** — tải parquet 237 MB, đọc schema + 20/211 row group<br>• CareerBuilder 2012 (header + đếm dòng trên đĩa)<br>• `aida-ugent/JobHop`<br>• `kandij/job-recommendation-datasets` (file list + preview cột)<br>• `kshitizregmi/jobs-and-job-description` (file list) | • RecSys 2016 (TrainingDataset.md + Table 1 paper)<br>• RecSys 2017 (trang dataset + Table 1 Abel et al. RecSys'17)<br>• Rules pháp lý CareerBuilder (file .docx chính thức)<br>• License OLX (README trên trang dataset)<br>• **Schema `job_skills.csv` + `mappings/skills.csv` của arshkon** (đặc tả DB chính thức `DatabaseStructure.md` của scraper sinh ra dataset) | • **Số dòng `jobs/job_skills.csv` của arshkon** (Kaggle API trả 404 không auth)<br>• **Zhaopin/Tianchi 31623 toàn bộ schema** (đã xác nhận phải có tài khoản)<br>• **`asaniczka/1-3m-linkedin-jobs-and-skills-2024` toàn bộ schema** |

---

## 4bis. Artifact tái lập được

Đã lưu tại `_newdata_audit/_dl/samples/` (đã xoá file lớn theo ràng buộc <500 MB):
- `djinni_job_descriptions_schema+10rows.json` (24.679 B) — `num_rows: 141897` + schema 10 cột + 10 dòng thật
- `djinni_candidate_profiles_schema+10rows.json` (24.735 B) — `num_rows: 210250` + schema 11 cột + 10 dòng thật
- `csv_headers.txt` (1.336 B) — header thật của xanderios, datastax, lukebarousse + header `job_skills`/`skills` của arshkon

Lệnh tái lập chính (Python — ghi ra file `.py` rồi chạy, **không pipe heredoc vào `python -`**):
```python
# đếm dòng + fill rate đúng cách (csv.reader, KHÔNG đếm b'\n')
import urllib.request, csv, io
url = "https://huggingface.co/datasets/lukebarousse/data_jobs/resolve/main/data_jobs.csv"
req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=300) as r:
    rd = csv.reader(io.TextIOWrapper(r, encoding='utf-8', errors='replace', newline=''))
    header = next(rd); idx = {h:i for i,h in enumerate(header)}
    n = 0; fill = {h:0 for h in header}
    for row in rd:
        n += 1
        for h,i in idx.items():
            if len(row) > i and row[i].strip(): fill[h] += 1
    print(n, {h: round(100*fill[h]/n,2) for h in header})
```

---

## 5. Phụ lục — nguồn đã đọc

- RecSys 2016: http://2016.recsyschallenge.com/ · https://github.com/recsyschallenge/2016/blob/master/TrainingDataset.md
- RecSys 2017: http://www.recsyschallenge.com/2017/ · https://github.com/recsyschallenge/2017 (baseline README)
- Số liệu XING 2016: Liu, Shi, Kumar, Zhu, Natarajan — *Temporal Learning and Sequence Modeling for a Job Recommender System* (arXiv:1608.03333), Table 1.
- Số liệu XING 2017: Abel, Deldjoo, Elahi, Kohlsdorf — *RecSys Challenge 2017: Offline and Online Evaluation* (DOI 10.1145/3109859.3109954), Table 1.
- CareerBuilder: https://www.kaggle.com/c/job-recommendation/data (mô tả file) · rules: `CB Kaggle Competition Official Rules 7 12 2012.docx` (storage.googleapis.com/kaggle-media/competitions/kaggle/3046/media/)
- OLX: https://www.kaggle.com/datasets/olxdatascience/olx-jobs-interactions
- LinkedIn: https://huggingface.co/datasets/xanderios/linkedin-job-postings · https://www.kaggle.com/datasets/arshkon/linkedin-job-postings · scraper: https://github.com/ArshKA/LinkedIn-Job-Scraper
- Zhaopin: https://tianchi.aliyun.com/dataset/31623 · OKRA (arXiv:2504.07108, ECIR 2025, Schellingerhout/Barile/Tintarev, Maastricht) + https://github.com/Roan-Schellingerhout/OKRA_ECIR — paper xác nhận nhãn Zhaopin 0–3 (0=không tương tác, 1=tương tác, 2=application, 3=hire); bộ còn lại là "proprietary commercial dataset" của XING, **không công bố**.
- TIMBRE (arXiv:2411.15146) — xác nhận "Xing dataset … is now unavailable", dùng JTH private (67k candidate–job, 26k candidate có job, 4k job).
- **`lukebarousse/data_jobs`**: https://huggingface.co/datasets/lukebarousse/data_jobs — schema qua `datasets-server.huggingface.co/info`, số dòng + fill rate quét toàn bộ `data_jobs.csv` (231.152.089 B).
- **`datastax/linkedin_job_listings`**: https://huggingface.co/datasets/datastax/linkedin_job_listings — quét toàn bộ `postings.csv` (516.843.769 B).
- **Djinni**: https://huggingface.co/datasets/lang-uk/recruitment-dataset-job-descriptions-english · `-candidate-profiles-english` — tải & đọc parquet thật.
- **Schema `job_skills` / `skills` của arshkon**: `DatabaseStructure.md` trong repo scraper https://github.com/ArshKA/LinkedIn-Job-Scraper (nguồn sinh ra chính dataset đó).
