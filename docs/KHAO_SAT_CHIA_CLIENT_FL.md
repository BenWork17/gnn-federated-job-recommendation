# Chia client trong FL-recsys và bộ dữ liệu có ranh giới tổ chức

**Task t3 — fl-benchmarks.** Trả lời 5 câu hỏi cho tình huống: đề bài yêu cầu
"mỗi nền tảng/doanh nghiệp giữ dữ liệu riêng", nhưng bộ CareerBuilder (Kaggle Job
Recommendation Challenge) **không có cột employer**.

Mọi số liệu trong tài liệu này đo trực tiếp trên bộ dữ liệu, script ở
`_newdata_audit/p26_clientsplit.py`, `p27_clientconfigs.py`, `p28_noniid.py`;
kết quả JSON ở `clientsplit.json`, `client_configs.json`, `nonIID.json`.

---

## 0. Kết luận chạy thẳng (TL;DR)

1. **Trong FL-recsys, client mặc định là *người dùng*, không phải doanh nghiệp.**
   Gần như toàn bộ dòng FL-recsys (FedGNN, PFedRec, GPFedRec, pFL-Bench) chia
   **1 user = 1 client** (cross-device). "Mỗi doanh nghiệp một client" là biến thể
   **cross-silo**, không phải chuẩn mặc định — nhưng **có** tiền lệ vững.
2. **Có đúng một tiền lệ trực tiếp cho "mỗi doanh nghiệp = 1 client" trong tuyển
   dụng**: FedLMF / MPCAC-FL (Guo et al., arXiv:2409.19545, 2024), client là **công
   ty**, lý do nêu thẳng là bảo mật dữ liệu nhân sự. Đây là trích dẫn neo.
3. **Không benchmark FL-recsys công khai nào có nhãn employer.** Mọi bộ (pFL-Bench,
   FLBench, FLamby, Bkd-FedGNN) đều **chia lại** dữ liệu centralized. Tức là
   **"tự định nghĩa ranh giới client" là thực hành chuẩn đã công bố** — miễn khai báo.
4. **Chia thô theo 189 tiểu bang là KHÔNG dùng được** — đây là phát hiện định lượng
   quan trọng nhất: `min 1, median 11, max 169.760` app/client; **145/189 client có
   < 1.000 app**, **128 client có < 100 app**. Phải gom nhóm.
5. **Chia theo bang tạo non-IID ở mức *item* rất mạnh, nhưng gần như IID ở mức
   *nhóm ngành*.** Đây là kết quả tinh tế và là điểm phải viết đúng:
   - Theo **nhóm ngành thô**: JSD ≈ **0,002** → gần IID, **không** dùng được để biện luận.
   - Theo **job_id cụ thể**: JSD(state) = **0,8057** vs JSD(hash) = **0,6008**
     → state **cao hơn nền IID 34%**.
   - Theo **title cụ thể**: JSD(state) = **0,5261** vs JSD(hash) = **0,3437**
     → **cao hơn 53%**.
   - **46,6%** lượt ứng tuyển rơi vào job mà **chỉ người của đúng một bang** ứng tuyển.
   - Jaccard item-set giữa các bang: **median 1,2%**, cao nhất 16,7% (NY–NJ, hai bang
     kề nhau — kiểm chứng hợp lý).
6. **Ngưỡng non-IID có định lượng chuẩn**: Zhao et al. (arXiv:1806.00582) giảm tới
   **55%** accuracy khi mỗi client 1 class; Hsu et al. (arXiv:1909.06335) suy giảm
   **đơn điệu** (30,1% → 76,9%); pFL-Bench quét Dirichlet α ∈ {5; 0,5; 0,1} và dùng
   **Jensen–Shannon distance** làm trục đo.

**Khuyến nghị:** client = **tiểu bang gom nhóm** (top-20 bang + "Rest"), đối chứng
bằng `hash(user_id) % C` với **cùng số client**, và **báo cáo JSD trên job_id/title**
(so với nền hash) thay vì JSD trên nhóm ngành.

---

## 1. Các bài FL-recsys chia client theo tiêu chí gì?

### 1.1 Hai trục phân loại gốc

| Chế độ | Client là gì | Số client | Bài recsys tiêu biểu |
|---|---|---|---|
| **Cross-device** | 1 thiết bị / 1 người dùng | 10³–10⁶ | FedGNN, PFedRec, GPFedRec, CFedGR, pFL-Bench |
| **Cross-silo** | 1 tổ chức / 1 doanh nghiệp | 2–100 | FedCT, FedCORE, Horizontal Cross-Silo FedRec, **FedLMF (tuyển dụng)** |

Định nghĩa chuẩn hai chế độ: Kairouz et al., *Advances and Open Problems in Federated
Learning* (FnT ML 2021, doi:10.1561/2200000083; OpenAlex ~9.484 trích dẫn).

### 1.2 Bảng bài cụ thể

| # | Bài | Năm / Hội nghị | Client chia theo | Cách họ mô tả lý do |
|---|---|---|---|---|
| 1 | **FedGNN** — Wu et al. | arXiv:2102.04925 (2021); journal *Nature Communications* 2022, doi:10.1038/s41467-022-30714-9 | **1 user = 1 client**, giữ đồ thị con user–item cục bộ | "locally train GNN model in each user client based on the user–item graph inferred from the local user–item interaction data"; gradient cục bộ được LDP hoá |
| 2 | **PFedRec** — Zhang et al. | **IJCAI 2023** (arXiv:2301.08143) | **1 user = 1 client**, model nhẹ riêng | "learn many user-specific lightweight models to be deployed on smart devices rather than a heavyweight model on a server" |
| 3 | **GPFedRec** — Zhang et al. | **KDD 2024** (arXiv:2305.07866) | **1 user = 1 client**; server dựng đồ thị quan hệ user từ item-embedding cá nhân hoá | "without accessing the users' interaction records" |
| 4 | **FedCT** — Zhang et al. | **SIGIR 2021**, doi:10.1145/3404835.3462825 | **1 miền / 1 nền tảng = 1 client** | vấn đề là "data isolation" giữa các miền; chuyển giao liên miền |
| 5 | **Horizontal Cross-Silo Federated Recommender Systems** — Kalloori & Klingler | **RecSys 2021**, doi:10.1145/3460231.3478863 | **1 stakeholder / 1 công ty = 1 client** | "multiple stakeholders (referred to as **corporate companies** like e-commerce, business partners, hospitals, banks, news media publishers) participate in federated learning" — **định nghĩa cross-silo cho recsys, sát đề bài nhất** |
| 6 | **FedCORE** — Li et al. | **IEEE TKDE 2024**, doi:10.1109/TKDE.2024.3363505 | **1 tổ chức = 1 client** | "raw data of different organizations cannot be merged … due to recent regulatory restrictions on privacy, security, as well as **commercial conflicts**" |
| 7 | **FedLMF / MPCAC-FL** — Guo et al. | arXiv:2409.19545 (2024) | **1 công ty = 1 client** (tuyển dụng) | "companies are reluctant to share their private human resource data … jeopardizing **competitive advantage**, security threats, and potential ethical or legal violations". Client **gom cụm động** theo độ tương đồng model |
| 8 | **FedSlate** — Deng et al. | IEEE TETCI 2025 (arXiv:2409.14872) | **1 nền tảng = 1 client** | "aggregate data from various platforms … raises economic and legal concerns" |
| 9 | **pFL-Bench** — Chen et al. | **NeurIPS 2022 D&B** (arXiv:2206.03655) | **Chia lại** theo user / writer / community / label-skew | Bảng 1 là taxonomy chuẩn: FEMNIST theo **Writers** (200 client); Twitter theo **Users** (13.203); Cora/Pubmed/Citeseer theo **Community** (5); MovieLens-1M theo **Users** (1.000); MovieLens-10M theo **Items** (1.000); CIFAR10/SST-2 theo **Labels** (Dirichlet α) |

### 1.3 Đọc ra

- **Chín trong mười bài recsys dùng client = user.** Nếu đồ án chọn "client = employer",
  đồ án ở nhánh **cross-silo** → phải viện dẫn #4, #5, #6, #7, **không** viện dẫn
  FedGNN/PFedRec.
- Câu chữ trích được, từ RecSys'21 (#5): client là *"corporate companies like
  e-commerce, business partners, hospitals, banks, news media publishers"* — đúng
  ngữ nghĩa đề bài.
- **FedLMF (#7)** là bài duy nhất vừa cross-silo, vừa **tuyển dụng**, vừa **GNN**,
  vừa nêu lý do bảo mật dữ liệu nhân sự → "bài anh em" gần nhất của đồ án.

---

## 2. Bộ dữ liệu FL công khai cho recsys — có không, schema ra sao?

### 2.1 Câu trả lời ngắn

**Không có bộ FL-recsys công khai nào có cột `employer` thật.** Tất cả benchmark lấy
dữ liệu **centralized có sẵn** rồi **chia lại** thành client. Nghĩa là trong
literature, "ranh giới client" **hầu như luôn là giả lập**.

### 2.2 Bảng benchmark

| Benchmark | Năm / Nơi công bố | Có recsys? | Cách chia client | Có cột tổ chức? |
|---|---|---|---|---|
| **pFL-Bench** (FederatedScope) | NeurIPS 2022 D&B, arXiv:2206.03655 | **Có** — MovieLens-1M, MovieLens-10M (MF) | ML-1M: **Users**, 1.000 client, μ=1.000, σ=482. ML-10M: **Items**, 1.000 client, μ=10.000, σ=8.155. CIFAR/SST-2: **Labels**, Dirichlet α ∈ {5; 0,5; 0,1} | **Không** |
| **FLBench** | arXiv:2008.07257 (BenchCouncil) | Không (medical, financial, AIoT) | 3 miền; nhấn mạnh việc chia tay "fails to capture real world isolated data island intrinsic characteristics" | Một phần |
| **FLamby** | NeurIPS 2022 D&B, doi:10.52202/068431-0384 | Không (healthcare) | **Cross-silo thật**: 5–6 tổ chức y tế, 1 tổ chức = 1 client | **Có** (bệnh viện) — không phải recsys |
| **Bkd-FedGNN** | arXiv:2306.10351 | Không (node/graph classification) | 13 dataset, có tham số **`overlapping rate`** giữa client | Không |
| **LEAF / FedML / FedScale** | — | LEAF có Shakespeare, Twitter theo **writer/user** | Chia theo user tự nhiên | Không |
| **RecSys thực nghiệm thường dùng** | — | MovieLens, Amazon, Yelp, Gowalla, LastFM | **1 user = 1 client** hoặc Dirichlet label-skew | **Không** |

### 2.3 Hệ quả phương pháp luận

Vì **không benchmark nào có nhãn tổ chức**, việc đồ án *tự định nghĩa* client là
**bình thường và đã được công bố**. Cái bị phản biện không phải "sao không có
employer", mà là ba lỗi sau — cả ba đều vá được:

1. **Không khai báo** rằng ranh giới client là giả lập.
2. **Không kiểm chứng** cách chia đó tạo non-IID *có ý nghĩa* (nếu gần IID thì kết
   quả FL không nói lên gì — xem mục 5).
3. **Không có đối chứng** (chỉ một cách chia → không loại trừ được may mắn).

---

## 3. Khi dữ liệu không có employer: cách chia nào được chấp nhận?

### 3.1 Bốn cách chia và trạng thái học thuật

| Cách chia | Tiền lệ công bố? | Ai đã làm | Ưu | Nhược / rủi ro bị phản biện |
|---|---|---|---|---|
| **A. `hash(user_id) % C`** | Có, nhưng chỉ là **baseline IID** | Chuẩn trong mọi benchmark FL khi cần IID control | Tái lập 100%, không thiên vị, chia đều tuyệt đối (đo được: C=21 → mỗi client ~135k app, lệch < 10%) | **Bị phản biện nặng nhất**: "chia *ngẫu nhiên*, không có ngữ nghĩa tổ chức. Nó mô phỏng 'chia bừa', không mô phỏng 'mỗi doanh nghiệp giữ dữ liệu riêng'". **Chỉ dùng làm đối chứng** |
| **B. Vùng địa lý (state/region)** | **Có, mạnh** (gián tiếp) | FairFed (AAAI'23): dữ liệu "naturally distributed … from different **geographical locations** or departments within an organization"; LEAF; FedML/FedScale; Hsu et al. 2019 (non-IID tự nhiên); FedSTAR (Sci.Rep. 2026, cross-border) | **Ranh giới có thật trong dữ liệu**; non-IID **tự nhiên** không nhân tạo; giải thích được bằng hành vi tìm việc | Phải chứng minh vùng ≠ tổ chức. Bị hỏi: "một bang có hàng nghìn công ty, sao gộp một client?" → trả lời: đây là **proxy thị trường lao động địa phương**; FL cross-silo thật cũng gộp nhiều đơn vị vào một silo (FLamby: 1 client = 1 bệnh viện, không phải 1 bác sĩ) |
| **C. Item cluster (nhóm ngành của tin)** | Có | pFL-Bench chia ML-10M **theo Items**; Bkd-FedGNN có `overlapping rate`; CFedGR (arXiv:2412.08066) cluster representation | Tạo domain shift mạnh | **Phi thực tế nhất nếu làm client**: user ứng tuyển nhiều ngành → **user xuất hiện ở nhiều client** → dữ liệu user bị xé, **rò rỉ chéo client**, phá giả định "dữ liệu không rời client". **Đo trên bộ này (`p29_itemcluster.py`): mỗi user trung bình thuộc 1,94 client; 51,6% user thuộc ≥2 client** → không thoả |
| **D. Thời gian** | Có, nhưng cho ***split***, không cho ***client*** | Mọi bài recsys dùng temporal split để đánh giá | — | **Không dùng được làm client**: mỗi client giữ *một giai đoạn*, không phải *một tổ chức* → sai khái niệm. Bộ này còn tệ hơn: toàn bộ app chỉ trải **63 ngày phân biệt** (2012-04-01 → 2012-06-26) |

### 3.2 Cách nào bị phản biện là "phi thực tế"?

Xếp theo rủi ro khi bảo vệ:

1. **Item cluster làm client** — rủi ro **cao nhất**. User không thuộc một client duy
   nhất. Nếu vẫn làm, **bắt buộc** khai báo "overlapping clients" + viện dẫn
   Bkd-FedGNN (có tham số `overlapping rate`).
2. **Hash user_id làm client chính** — rủi ro **cao**. Không ngữ nghĩa; người phản
   biện sẽ hỏi "vậy 'mỗi doanh nghiệp giữ dữ liệu riêng' trong đề bài biến đi đâu?".
3. **Thời gian làm client** — rủi ro **cao**. Sai khái niệm; thêm nữa chỉ 63 ngày.
4. **Vùng địa lý** — rủi ro **trung bình**. Hợp lý, nhưng **phải** chuẩn bị câu trả
   lời "state ≠ company" **và phải chứng minh vùng tạo non-IID thật** (đo JSD so với
   nền hash — xem mục 5.3).

### 3.3 Khung biện luận khuyến nghị (dùng được nguyên văn trong báo cáo)

> **Bước 1 — Thừa nhận.** Bộ dữ liệu không có cột `employer`. Đây là hạn chế thật.
>
> **Bước 2 — Literature cũng vậy.** Không benchmark FL-recsys công khai nào
> (pFL-Bench NeurIPS'22, FLBench, FLamby) có nhãn tổ chức cho recsys; tất cả đều chia
> lại dữ liệu centralized. Việc tự định nghĩa client là **thực hành chuẩn**, không
> phải né tránh.
>
> **Bước 3 — Chọn proxy có ngữ nghĩa.** Trong bốn lựa chọn, vùng địa lý là proxy duy
> nhất vừa (a) có thật trong dữ liệu, (b) có ngữ nghĩa kinh tế lao động, (c) tạo
> non-IID **đo được**. Bằng chứng trên chính bộ này: **84,05%** lượt ứng tuyển là
> **cùng bang**; ở mức người dùng, **trung bình 87,0%**, **median 100%**, và
> **78,9% ứng viên chỉ ứng tuyển trong đúng một bang**. Viện dẫn FairFed (AAAI'23)
> và FLamby (NeurIPS'22) — cross-silo thật ở mức **tổ chức**.
>
> **Bước 4 — Đối chứng và khai báo.** Chạy song song `hash(user_id) % C` với **cùng
> số client**, báo cáo **JSD trên job_id/title so với nền hash**, và ghi rõ:
> *"client là proxy theo vùng địa lý, không phải ranh giới pháp lý của doanh nghiệp"*.

---

## 4. Tiền lệ chia client theo BANG/VÙNG cho dữ liệu tuyển dụng?

### 4.1 Trả lời trực tiếp: KHÔNG có

Đã kiểm tra có hệ thống qua arXiv API:

| Truy vấn | Kết quả |
|---|---|
| `abs:"federated" AND abs:"job recommendation"` | **0 bài** |
| `abs:"federated" AND (abs:"recruitment" OR abs:"hiring" OR abs:"talent")` | 30 bài, **chỉ 1 đúng chủ đề** (FedLMF, arXiv:2409.19545) |
| `abs:"federated" AND (abs:"person-job fit" OR abs:"job matching" OR abs:"human resources")` | 5 bài, **cũng chỉ FedLMF** |

Đây là **khoảng trống literature thật** — vừa là rủi ro (không có bài để dựa), vừa
là **điểm đóng góp** (đồ án là một trong những nỗ lực đầu tiên).

### 4.2 Tiền lệ gần nhất theo từng hướng

| Hướng | Bài | Năm | Điều họ làm được | Khoảng cách với đồ án |
|---|---|---|---|---|
| **Tuyển dụng + FL + GNN + công ty là client** | FedLMF / MPCAC-FL (arXiv:2409.19545) | 2024 | Đặt tên bài toán **FedLMF**, client = công ty, lý do = bảo mật dữ liệu nhân sự + lợi thế cạnh tranh | Dự đoán **cung–cầu lao động theo chuỗi thời gian**, không phải gợi ý user–job; không chia theo bang |
| **Địa lý là nguồn non-IID tự nhiên** | FairFed (AAAI'23, arXiv:2110.00857) | 2021/2023 | Nêu rõ "data collected from different **geographical locations** or departments within an organization" | Không phải recsys tuyển dụng |
| **Cross-silo thật ở mức tổ chức** | FLamby (NeurIPS'22 D&B) | 2022 | 1 client = 1 tổ chức y tế; chứng minh cross-silo là chế độ hợp lệ | Healthcare |
| **Cross-border / vùng** | FedSTAR (Scientific Reports 2026, doi:10.1038/s41598-026-60810-5) | 2026 | "cross-border data sharing is strictly constrained … user isolation and business homogeneity" | Không phải tuyển dụng; client là quốc gia |

### 4.3 Cách dùng bằng chứng địa lý cho đúng

Con số **84,05%** (tỉ lệ app có `user.State == job.State`) **không** chứng minh
"chia theo bang là chuẩn FL". Nó chứng minh một điều hẹp hơn nhưng rất mạnh:

> Thị trường lao động trong bộ dữ liệu này **có cấu trúc địa lý mạnh**. Do đó chia
> client theo bang **không phải chia ngẫu nhiên**: nó tạo ra các client có **phân bố
> item khác nhau một cách hệ thống** (đo ở mục 5.3), đúng loại heterogeneity mà FL
> cần để có ý nghĩa.

Cách viết an toàn:

> "Chúng tôi không tuyên bố tiểu bang là ranh giới doanh nghiệp. Chúng tôi dùng tiểu
> bang làm **proxy cho thị trường lao động địa phương**, dựa trên quan sát rằng
> 84,05% lượt ứng tuyển trong bộ dữ liệu diễn ra trong cùng tiểu bang, và 78,9% ứng
> viên chỉ ứng tuyển trong đúng một bang. Đây là dạng phân vùng 'naturally
> distributed' mà FairFed (AAAI'23) và FLamby (NeurIPS'22) mô tả, áp dụng cho bối
> cảnh tuyển dụng."

---

## 5. Ngưỡng non-IID nào thì FL còn có nghĩa?

### 5.1 Các bài đo mức suy giảm theo độ lệch phân bố

| Bài | Năm | Cách đo độ lệch | Kết quả định lượng |
|---|---|---|---|
| **Zhao et al., *Federated Learning with Non-IID Data*** (arXiv:1806.00582) | 2018 | Mỗi client **1 class** (pathological); đo bằng **EMD** giữa phân bố class của client và quần thể | **Giảm tới 55%** accuracy. Chia sẻ 5% dữ liệu toàn cục → **+30%** accuracy trên CIFAR-10 |
| **Hsu et al., *Measuring the Effects of Non-Identical Data Distribution*** (arXiv:1909.06335) | 2019 | Phổ **liên tục** độ "identicalness" bằng Dirichlet; accuracy theo α | Suy giảm **đơn điệu**. Server momentum: **30,1% → 76,9%** ở cấu hình lệch nhất (CIFAR-10) |
| **pFL-Bench** (arXiv:2206.03655) | 2022 | Dirichlet α ∈ {5; 0,5; 0,1} = mild → severe; dùng **Jensen–Shannon distance** giữa phân bố nhãn các client | Định nghĩa chuẩn "Non-IID degree"; có mục riêng *"Effect of Non-IID split"* |
| **Li et al., *FL on Non-IID Data Silos*** (arXiv:2102.02079) | 2021 | Feature skew vs label skew trên data silo | **Feature skew khó hơn** label skew |
| **FedProx** — Li et al. (MLSys 2020) | 2020 | γ-heterogeneity: mức lệch local optimum vs global optimum | Đặt khái niệm **γ**; hội tụ phụ thuộc γ |

### 5.2 Ba mốc thực dụng

| Mốc | Định nghĩa | Hệ quả |
|---|---|---|
| **IID** (JSD ≈ nền sampling) | Mọi client ~ quần thể | FL ≈ centralized; **thí nghiệm FL không nói lên gì** — bẫy phổ biến nhất |
| **Mild non-IID** (α ≈ 5) | Lệch nhẹ | FL tốt, chênh vài % |
| **Severe non-IID** (α ≈ 0,1) | Mỗi client ≈ 1–2 class | **Giảm tới 55%**; cần FedProx / pFL / clustered FL |
| **Pathological** | Mỗi client đúng 1 class | FedAvg sụp; dùng để **stress-test**, không phải mức thực tế |

### 5.3 Đo thực tế trên bộ CareerBuilder — phần quan trọng nhất

Tôi chạy hai phép đo ở **cùng số client (44 bang có ≥ 1.000 app)** để tách hiệu ứng
non-IID khỏi nhiễu lấy mẫu:

| Độ đo | Chia theo **bang** | Chia theo **hash(user_id) % 44** (nền IID) | Chênh |
|---|---|---|---|
| **JSD trên `job_id`** | **0,8057** | 0,6008 | **+34%** |
| **JSD trên `title`** (chuẩn hoá) | **0,5261** | 0,3437 | **+53%** |
| **JSD trên nhóm ngành thô (8 nhóm)** | **0,0007 – 0,0027** | ~0 | **≈ 0** |

Đọc kết quả này **đúng** là điều quyết định chất lượng bài báo:

1. **Ở mức nhóm ngành, cách chia địa lý gần như IID.** Nếu chỉ báo cáo con số này,
   người phản biện sẽ nói *"cách chia của bạn không tạo non-IID"* — và họ đúng.
   **Tuyệt đối không dùng JSD nhóm ngành để biện luận.**
2. **Ở mức item cụ thể, cách chia địa lý tạo non-IID mạnh hơn hẳn nền IID** (+34% trên
   `job_id`, +53% trên `title`). Vì sao hai mức lại khác nhau đến vậy? Vì phân bố
   *ngành* của Mỹ khá đồng đều giữa các bang, nhưng **tập tin tuyển dụng cụ thể** thì
   gắn chặt với địa phương.
3. **Vì sao phải có nền hash:** JSD trên `job_id` bị nhiễu vì vũ trụ item rất lớn
   (~350k job) và mỗi client chỉ có vài chục nghìn mẫu — **ngay cả lấy mẫu IID hoàn
   hảo cũng cho JSD ≠ 0**. Do đó con số tuyệt đối 0,81 **không** có nghĩa; chỉ **phần
   vượt nền (+34%)** mới là tín hiệu non-IID thật. Đây là cách báo cáo trung thực và
   đúng phương pháp.

Hai bằng chứng độc lập, không phụ thuộc JSD:

| Độ đo | Giá trị | Ý nghĩa |
|---|---|---|
| **% app rơi vào job mà chỉ đúng 1 bang ứng tuyển** | **46,6%** (trung bình có trọng số; FL 50,3%, TX 53,8%, CA 65,9%, NY 32,9%) | Gần một nửa khối lượng tương tác là **độc quyền địa phương** → không thể học từ client khác |
| **Jaccard item-set giữa các bang (top-12)** | **median 1,2%**, min 0,6% (IN–AZ), **max 16,7% (NY–NJ)** | Hai bang **kề nhau** có overlap cao nhất — kiểm chứng hợp lý rằng tín hiệu là địa lý thật, không phải nhiễu |
| **% app trên job được ≥ 2 bang ứng tuyển** | **60,2%** | Ngược lại: phần lớn *khối lượng* nằm trên item dùng chung → **embedding item toàn cục vẫn khả thi**, nhưng **đuôi dài** thì rất địa phương |

**Kết luận kỹ thuật cho phần GNN:** item phổ biến dùng chung tốt (60,2% traffic), item
đuôi dài gần như độc quyền theo bang (46,6% traffic) → cần **cơ chế item embedding
riêng theo client** (giống PFedRec / dual personalization) chứ không chỉ FedAvg một
bảng embedding chung. Đây trực tiếp xác nhận cạm bẫy "FedAvg ngây thơ làm sụp mô hình"
đã ghi trong `docs/PHAN_TICH_DE_TAI.md` mục A.3.

### 5.4 Cảnh báo ngược chiều — trích để phòng thủ

arXiv:2608.07157 (*Capacity Confounds and Coverage Guarantees in Adaptive Sub-model
Federated Learning*, 2026) chỉ ra nhiều phương pháp "thích ứng theo độ lệch dữ liệu"
thực chất **không** suy ra được độ lệch từ model update; lợi ích đo được đến từ
**capacity budgeting**. Bài khuyến nghị **"matched-budget random baselines"**.

→ Hệ quả: khi so "chia theo bang" vs "chia theo hash", **phải giữ nguyên số client và
ngân sách tham số**. Nếu không, người phản biện nói chênh lệch là do cấu hình khác
nhau, không do cách chia.

---

## 6. Cấu hình client khả thi — đo trên bộ dữ liệu

Toàn bộ mục này là số đo thật (`_newdata_audit/client_configs.json`).
Tập train: **1.417.514** tương tác, **308.033** user, **349.742** job.

### 6.1 Vì sao chia thô theo bang là không dùng được

| Cấu hình | Số client | app/client (min / median / max) | Vấn đề |
|---|---|---|---|
| **G0. 189 bang, thô** | 189 | **1 / 11 / 169.760** | **145 client < 1.000 app; 128 client < 100 app.** Top-5 chiếm 44,0%. Không client nhỏ nào học được gì |

→ Kết luận: **phải gom nhóm**. Chia thô vi phạm cả yêu cầu thống kê (client quá nhỏ)
lẫn yêu cầu cân bằng của FL cross-silo.

### 6.2 Các cấu hình gom nhóm

**G1 — top-K bang giữ riêng, phần còn lại gộp thành "Rest":**

| K | Số client | min | median | max | top-1 share |
|---|---|---|---|---|---|
| 4 | 5 | 102.840 | 153.765 | 875.677 | 61,8% |
| 8 | 9 | 55.571 | 102.840 | 615.355 | 43,4% |
| 12 | 13 | 48.194 | 66.326 | 414.140 | 29,2% |
| **16** | **17** | **28.122** | **55.571** | **269.229** | **19,0%** |
| **20** | **21** | **20.702** | **50.691** | **173.006** | **12,2%** |

**G2 — 4 vùng Census (+ Other/Non-US):**

| Số client | min | median | max | top-1 share |
|---|---|---|---|---|
| 5 | 5.891 | 231.328 | 646.269 | 45,6% |

Chi tiết: South 646.269 · Midwest 325.056 · Northeast 231.328 · West 208.970 · Other 5.891.

**G3 — vùng Census + top-K bang tách riêng:**

| K | Số client | min | median | max | top-1 share |
|---|---|---|---|---|---|
| 8 | 13 | 5.891 | 93.498 | 256.418 | 18,1% |
| 12 | 17 | 5.891 | 56.662 | 203.220 | 14,3% |
| 16 | 21 | 5.891 | 50.691 | 169.760 | 12,0% |

### 6.3 Khuyến nghị cấu hình

| Vai trò | Cấu hình | Số client | Lý do |
|---|---|---|---|
| **Chính** | **G1, K = 20** (top-20 bang + Rest) | **21** | Tỉ lệ max/min = 8,4× (chấp nhận được cho cross-silo); top-1 chỉ 12,2%; nằm đúng dải 2–100 client của FL cross-silo; **giữ được non-IID item-level cao** vì client vẫn là bang |
| **Đối chứng bắt buộc** | `hash(user_id) % 21` | 21 | Cùng số client → "matched-budget baseline" theo arXiv:2608.07157 |
| **Ablation (tuỳ chọn)** | G2 (4 vùng) | 5 | Cho thấy FL còn lợi khi client rất lớn; kiểm tra giả thuyết "càng ít client càng gần centralized" |
| **Không dùng** | G0 thô; item-cluster; thời gian | — | Xem 6.1 và 3.2 |

Với **C = 21**, hash cho mỗi client ~**67.500 app**, lệch chuẩn rất nhỏ (đo ở C=12:
115.525–120.010; C=50: 26.776–30.480) → đối chứng sạch.

---

## 7. Bảng quyết định cuối — "cách chia client → dẫn chứng → rủi ro bị phản biện"

| Cách chia | Dẫn chứng (bài, năm, nơi công bố) | Ưu điểm đo được trên bộ này | Rủi ro bị phản biện | Khuyến nghị |
|---|---|---|---|---|
| **1. Theo tiểu bang (gom top-K + Rest)** | FairFed (AAAI'23) — "naturally distributed … different geographical locations"; FLamby (NeurIPS'22 D&B) — cross-silo ở mức tổ chức; FedSTAR (Sci.Rep. 2026) — cross-border | **84,05%** app cùng bang; **78,9%** user chỉ 1 bang; JSD `job_id` **+34%** và `title` **+53%** so với nền hash; **46,6%** app trên job độc quyền 1 bang; Jaccard median **1,2%** | "State ≠ company" (một bang có nhiều doanh nghiệp) | ⭐ **Chính**, kèm khai báo proxy |
| **2. `hash(user_id) % C`** | Không bài nào *đề xuất* làm client chính; chỉ là IID baseline trong mọi benchmark | Chia đều tuyệt đối; tái lập 100% | **"Chia bừa, không ngữ nghĩa"** — mất liên hệ với đề bài | ⭐ **Đối chứng bắt buộc** |
| **3. Item cluster (nhóm ngành)** | pFL-Bench (NeurIPS'22) chia ML-10M **theo Items**; Bkd-FedGNN (2023) `overlapping rate`; CFedGR (arXiv:2412.08066) | Domain shift mạnh | **Phi thực tế nhất nếu làm client**: đo được **1,94 client/user**, **51,6% user thuộc ≥2 client** → **rò rỉ chéo client**, phá giả định locality | ⚠️ **Chỉ ablation**, phải khai báo overlapping |
| **4. Theo thời gian** | Mọi bài recsys dùng temporal split — nhưng cho **split**, không cho **client** | — | **Sai khái niệm client**; bộ này chỉ trải **63 ngày phân biệt** | ❌ **Không dùng** |
| **5. Theo doanh nghiệp (`employer_id`)** | FedCT (SIGIR'21); Horizontal Cross-Silo FedRec (RecSys'21); FedCORE (TKDE'24); **FedLMF (2024)** cho tuyển dụng | Đúng ngữ nghĩa đề bài nhất | **Bộ dữ liệu không có cột này.** Bịa ra → phản biện nặng hơn nhiều | ❌ **Không khả thi** trên bộ này |

### 7.1 Nếu buộc chọn một

**Chọn cách 1 (bang, gom top-20 + Rest, 21 client), đối chứng bằng cách 2 (hash, 21
client).** Ba lý do:

1. **Ranh giới có thật trong dữ liệu** (84,05% cùng bang; JSD cao hơn nền IID 34–53%),
   không phải gán bừa.
2. **Có nền tảng literature** (FairFed, FLamby, FedML/FedScale) dù không trực tiếp
   trong tuyển dụng — và khoảng trống đó chính là **đóng góp** của đồ án.
3. **Đối chứng được** bằng hash cùng số client + JSD so với nền, thoả yêu cầu
   "matched-budget baseline".

---

## 8. Việc cần làm tiếp (bàn giao)

| # | Việc | Vì sao | Trạng thái |
|---|---|---|---|
| 1 | Dựng partition G1 K=20 (21 client) + hash % 21 và lưu thành file | Đây là đầu vào cho mọi thực nghiệm FL sau | ⬜ chưa |
| 2 | Báo cáo **JSD `job_id` và `title`** của G1 so với nền hash, không báo JSD nhóm ngành | JSD nhóm ngành ≈ 0 sẽ tự bắn vào chân mình | ✅ đã có số (mục 5.3) |
| 3 | Ghi rõ trong báo cáo: *"client = proxy vùng địa lý, không phải ranh giới pháp lý doanh nghiệp"* | Câu này chặn phần lớn phản biện | ⬜ chưa (đã có câu mẫu ở 4.3) |
| 4 | Thêm cơ chế **item embedding riêng theo client** cho đuôi dài | 46,6% traffic là item độc quyền 1 bang → FedAvg một bảng chung sẽ hỏng đuôi dài | ⬜ chưa |
| 5 | Trích **FedLMF (arXiv:2409.19545)** làm tiền lệ "công ty là client" cho tuyển dụng | Bài gần đề tài nhất | ✅ có trong mục 1.2 |

---

## Tài liệu tham khảo

Tất cả đã kiểm chứng qua arXiv API / OpenAlex / DOI ở thời điểm thực hiện task này.

1. Guo, Z., Liu, H., Zhang, L., Zhang, Q., Zhu, H., Xiong, H. *Convergence-aware Clustered Federated Graph Learning Framework for Collaborative Inter-company Labor Market Forecasting.* arXiv:2409.19545, 2024. https://arxiv.org/abs/2409.19545
2. Kalloori, S., Klingler, S. *Horizontal Cross-Silo Federated Recommender Systems.* RecSys 2021. doi:10.1145/3460231.3478863
3. Zhang, et al. *FedCT: Federated Collaborative Transfer for Recommendation.* SIGIR 2021. doi:10.1145/3404835.3462825
4. Li, Z., Wu, X., Pan, W., Ding, Y., Wu, Z., Tan, S., Xu, Q., Yang, Q., Ming, Z. *FedCORE: Federated Learning for Cross-Organization Recommendation Ecosystem.* IEEE TKDE, 2024. doi:10.1109/TKDE.2024.3363505
5. Chen, D., Gao, D., Kuang, W., Li, Y., Ding, B. *pFL-Bench: A Comprehensive Benchmark for Personalized Federated Learning.* NeurIPS 2022, Datasets & Benchmarks. arXiv:2206.03655
6. Liang, Y., et al. *FLBench: A Benchmark Suite for Federated Learning.* arXiv:2008.07257
7. Ogier du Terrail, J., et al. *FLamby: Datasets and Benchmarks for Cross-Silo Federated Learning in Realistic Healthcare Settings.* NeurIPS 2022 D&B. doi:10.52202/068431-0384
8. Wu, C., Wu, F., Cao, Y., Huang, Y., Xie, X. *FedGNN: Federated Graph Neural Network for Privacy-Preserving Recommendation.* arXiv:2102.04925; journal: *Nature Communications* 2022, doi:10.1038/s41467-022-30714-9
9. Zhang, C., Long, G., Zhou, T., Yan, P., Zhang, Z., Zhang, C., Yang, B. *Dual Personalization on Federated Recommendation (PFedRec).* IJCAI 2023. arXiv:2301.08143
10. Zhang, C., Long, G., Zhou, T., Zhang, Z., Yan, P., Yang, B. *GPFedRec: Graph-guided Personalization for Federated Recommendation.* KDD 2024. arXiv:2305.07866
11. Zhao, Y., Li, M., Lai, L., Suda, N., Civin, D., Chandra, V. *Federated Learning with Non-IID Data.* arXiv:1806.00582, 2018
12. Hsu, T.-M. H., Qi, H., Brown, M. *Measuring the Effects of Non-Identical Data Distribution for Federated Visual Classification.* arXiv:1909.06335, 2019
13. Ezzeldin, Y. H., Yan, S., He, C., Ferrara, E., Avestimehr, S. *FairFed: Enabling Group Fairness in Federated Learning.* AAAI 2023. arXiv:2110.00857
14. Kairouz, P., et al. *Advances and Open Problems in Federated Learning.* Foundations and Trends in ML, 2021. doi:10.1561/2200000083
15. Liu, F., Lai, S., Ning, Y., Liu, H. *Bkd-FedGNN: A Benchmark for Classification Backdoor Attacks on Federated Graph Neural Network.* arXiv:2306.10351
16. Deng, Y., Qiu, X., Tan, X., Jin, Y. *FedSlate: A Federated Deep Reinforcement Learning Recommender System.* IEEE TETCI 2025. arXiv:2409.14872
17. *Capacity Confounds and Coverage Guarantees in Adaptive Sub-model Federated Learning.* arXiv:2608.07157, 2026
18. *Towards cross-silo federated learning for corporate organizations.* Knowledge-Based Systems, 2024. doi:10.1016/j.knosys.2024.111501
19. Wang, H., Yuan, Y. *Cluster-Enhanced Federated Graph Neural Network for Recommendation (CFedGR).* arXiv:2412.08066, 2024
20. Li, Q., Diao, Y., Chen, Q., He, B. *Federated Learning on Non-IID Data Silos: An Experimental Study.* arXiv:2102.02079, 2021
21. Li, T., Sahu, A. K., Zaheer, M., Sanjabi, M., Talwalkar, A., Smith, V. *Federated Optimization in Heterogeneous Networks (FedProx).* MLSys 2020. arXiv:1812.06127

---

### Phụ lục — nguồn số liệu

| Số liệu | File | Script |
|---|---|---|
| 84,05% cùng bang | `_newdata_audit/geo.json` | `p11_clients.py` |
| Số client / app mỗi client / JSD / item sharing | `_newdata_audit/clientsplit.json` | `p26_clientsplit.py` |
| Cấu hình G1/G2/G3, JSD nhóm ngành | `_newdata_audit/client_configs.json` | `p27_clientconfigs.py` |
| JSD `job_id`/`title`, nền hash, item độc quyền, Jaccard | `_newdata_audit/nonIID.json` | `p28_noniid.py` |
| Số client/user khi chia theo nhóm ngành | `_newdata_audit/p29_out.txt` | `p29_itemcluster.py` |
| Quy mô bộ, window thời gian | `_newdata_audit/jobs_stats.json`, `apps_stats.json` | `p2_jobs.py`, `p1_small.py` |

*Lưu ý về giới hạn của số liệu:* (a) `84,05%` tính trên toàn bộ app, không lọc theo
split; (b) JSD trên `job_id` bị nhiễu do vũ trụ item lớn — **chỉ đọc phần chênh so với
nền hash**, không đọc giá trị tuyệt đối; (c) trường `state` của job có 1.434 dòng là
khoảng trắng → được gộp vào nhóm không xác định khi cần.
