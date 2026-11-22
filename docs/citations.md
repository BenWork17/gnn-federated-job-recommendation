# Tài liệu tham khảo khoa học đã kiểm chứng cho báo cáo & slide FedGraph

Tài liệu này tổng hợp **32 công trình khoa học và nguồn dữ liệu chuẩn hóa** đã được kiểm chứng trực tiếp qua tìm kiếm học thuật (exact Title, Authors, Venue, Year, DOI/URL) để phục vụ báo cáo cuối kỳ (`.docx`) và bộ slide thuyết trình (`.pptx`) cho hệ thống **FedGraph** (*GNN + Cross-Silo Federated Learning for Job Recommendation* trên bộ dữ liệu **CareerBuilder + O\*NET 29.3 V3**).

---

## Ma trận ánh xạ nhanh theo chương báo cáo & slide

| Nhóm chủ đề | Mã tài liệu gợi ý | Vị trí sử dụng chính trong Báo cáo & Slide |
|---|---|---|
| **1. Graph Collaborative Filtering & LightGCN** | `[GCF-1]` He et al. (2020), `[GCF-2]` Wang et al. (2019), `[GCF-3]` Rendle et al. (2009), `[GCF-4]` Hamilton et al. (2017), `[GCF-5]` Sarwar et al. (2001) | Chương 1 (Đặt vấn đề), Chương 2 (Cơ sở lý thuyết GNN/LightGCN & BPR Loss), Chương 4 (Đối chứng Centralized LightGCN `0.7151`, GraphSAGE `0.5113`, Item-KNN `0.4897` / Global `0.5408`). |
| **2. Federated Learning Foundations** | `[FL-1]` McMahan et al. (2017), `[FL-2]` Li et al. (2020), `[FL-3]` Kairouz et al. (2021), `[FL-4]` Karimireddy et al. (2020), `[FL-5]` Li et al. (2022) | Chương 2 (FedAvg, FedProx, Cross-Silo vs Cross-Device, Non-IID & Client Drift), Chương 4 (Phân tích Ablation `FedAvg weighted 0.4833` vs `FedProx μ=0.01 0.4627`, `local_epochs 1→5` gây Client Drift `0.4833→0.4565`). |
| **3. Privacy-Preserving FL & Compression** | `[SEC-1]` Abadi et al. (2016), `[SEC-2]` Bonawitz et al. (2017), `[SEC-3]` Zhu et al. (2019), `[SEC-4]` Lin et al. (2018) | Chương 1 & 2 (Rủi ro rò rỉ từ gradient `ΔW`), Chương 4 (Nén `ΔW` FP32/FP16/Top-20% trong Node Monitor), Chương 5 (Hạn chế chưa tích hợp DP-SGD & Secure Aggregation và hướng phát triển). |
| **4. Federated Graph Learning & FedRec** | `[FGL-1]` Wu et al. (2022), `[FGL-2]` Ammad-ud-din et al. (2019), `[FGL-3]` Muhammad et al. (2020), `[FGL-4]` Lin et al. (2020), `[FGL-5]` Lin et al. (2021), `[FGL-6]` Chen et al. (2022), `[FGL-7]` Zhang et al. (2021), `[FGL-8]` Baek et al. (2023), `[FGL-9]` He et al. (2021), `[FGL-10]` Fu et al. (2022), `[FGL-11]` Liu et al. (2025), `[FGL-12]` Sun et al. (2024) | Chương 1 & 2 (Related Work: Federated Recommendation & Subgraph Federated Learning), Chương 3 (Đặt vị thế kiến trúc lai **Public Graph Backbone (O\*NET) + Private Employer Silos** của FedGraph khác với User-level FedPerGNN hay sinh nút giả FedSage+). |
| **5. Job Recommendation & O\*NET Taxonomy** | `[JOB-1]` de Ruijt & Bhulai (2021), `[JOB-2]` Mashayekhi et al. (2024), `[JOB-3]` Giabelli et al. (2021), `[JOB-4]` Alonso et al. (2025), `[JOB-5]` Zhao et al. (2021), `[JOB-6]` National Center for O\*NET Development (2025) | Chương 1 (Bối cảnh bài toán gợi ý việc làm & ràng buộc dữ liệu doanh nghiệp), Chương 2 & 3 (Chuẩn hóa CareerBuilder + O\*NET 29.3, đồ thị kỹ năng 2-hop), Chương 5 (Hướng cải thiện O\*NET coverage `31.44%` → `>85%` bằng Transformer/Sentence-BERT theo `[JOB-4]`). |

---

## Nhóm 1: Graph Collaborative Filtering & LightGCN

### `[GCF-1]` LightGCN (SIGIR 2020)
- **Title:** LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation
- **Authors:** Xiangnan He, Kuan Deng, Xiang Wang, Yan Li, Yongdong Zhang, Meng Wang
- **Venue:** *Proceedings of the 43rd International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR '20)*, pp. 639–648
- **Year:** 2020
- **DOI / URL:** `10.1145/3397271.3401063` | https://doi.org/10.1145/3397271.3401063 | https://arxiv.org/abs/2002.02126
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Chứng minh bằng thực nghiệm (ablation study) rằng hai thành phần phổ biến trong GCN tiêu chuẩn là **feature transformation** (ma trận trọng số tuyến tính) và **nonlinear activation** không cải thiện mà còn làm giảm hiệu năng Collaborative Filtering. LightGCN chỉ giữ lại **neighborhood aggregation** tuyến tính qua chuẩn hóa bậc đối xứng và tổng có trọng số qua các tầng (layer combination).
  - *Liên kết FedGraph:* Là kiến trúc xương sống (backbone) của cả mô hình **Centralized LightGCN** (`Recall@20 = 0.7151` trên FL Catalog; `0.4002` trên Global Catalog) lẫn mô hình cục bộ tại mỗi employer silo trong **FedAvg / FedProx**. Việc bỏ ma trận biến đổi phi tuyến giúp không gian tham số đồng bộ giữa các client gọn nhẹ, giảm chi phí truyền thông $\Delta W$ trong Cross-Silo FL.

### `[GCF-2]` NGCF (SIGIR 2019)
- **Title:** Neural Graph Collaborative Filtering
- **Authors:** Xiang Wang, Xiangnan He, Meng Wang, Fuli Feng, Tat-Seng Chua
- **Venue:** *Proceedings of the 42nd International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR '19)*
- **Year:** 2019
- **DOI / URL:** `10.1145/3331184.3331267` | https://doi.org/10.1145/3331184.3331267
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Khai thác **high-order connectivity** trên đồ thị tương tác hai phía (user–item bipartite graph) bằng cơ chế message passing để mã hóa tín hiệu cộng tác bậc cao vào embedding trước bước dự đoán.
  - *Liên kết FedGraph:* Đặt nền móng cho tư duy biểu diễn đồ thị đa tầng trong Related Work và làm rõ lý do FedGraph lựa chọn **LightGCN** (vượt NGCF ~16% theo `[GCF-1]` và nhẹ hơn nhiều khi đồng bộ gradient qua mạng trong Federated Learning).

### `[GCF-3]` BPR Loss (UAI 2009)
- **Title:** BPR: Bayesian Personalized Ranking from Implicit Feedback
- **Authors:** Steffen Rendle, Christoph Freudenthaler, Zeno Gantner, Lars Schmidt-Thieme
- **Venue:** *Proceedings of the 25th Conference on Uncertainty in Artificial Intelligence (UAI '09)*
- **Year:** 2009
- **DOI / URL:** `10.48550/arXiv.1205.2618` | https://arxiv.org/pdf/1205.2618
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất hàm mất mát xếp hạng cặp (**pairwise ranking loss**) dựa trên ước lượng hậu nghiệm cực đại (MAP) cho **implicit feedback** (ví dụ: lượt ứng tuyển hoặc nhấp chuột), tối ưu hóa xác suất để item đã tương tác xếp hạng cao hơn item chưa tương tác.
  - *Liên kết FedGraph:* Cung cấp công thức hàm mục tiêu chuẩn (**BPR Loss**) cho bài toán gợi ý từ dữ liệu ứng tuyển ẩn (implicit application edges `user–job`) tại từng client silo cũng như mô hình LightGCN tập trung.

### `[GCF-4]` GraphSAGE (NeurIPS 2017)
- **Title:** Inductive Representation Learning on Large Graphs
- **Authors:** William L. Hamilton, Zhitao (Rex) Ying, Jure Leskovec
- **Venue:** *Advances in Neural Information Processing Systems (NeurIPS '17)*, Vol. 30
- **Year:** 2017
- **DOI / URL:** `10.5555/3294771.3294869` / `10.48550/arXiv.1706.02216` | https://proceedings.neurips.cc/paper/2017/hash/5dd9db5e033da9c6fb5ba83c7a7ebea9-Abstract.html
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất cơ chế học quy nạp (inductive) bằng cách lấy mẫu lân cận cố định (neighborhood sampling) và tổng hợp đặc trưng nút, cho phép tổng quát hóa sang nút mới (**cold-start**) không thấy lúc huấn luyện.
  - *Liên kết FedGraph:* Là một trong các mô hình đối chứng tập trung quan trọng của FedGraph (`GraphSAGE Centralized`: `Recall@20 = 0.5113` trên FL Catalog; `0.1376` trên Global Catalog), giúp chứng minh ưu thế của kiến trúc LightGCN thuần truyền lan ID/cấu trúc trên đồ thị thưa tuyển dụng.

### `[GCF-5]` Item-KNN (WWW 2001)
- **Title:** Item-based collaborative filtering recommendation algorithms
- **Authors:** Badrul Sarwar, George Karypis, Joseph Konstan, John Riedl
- **Venue:** *Proceedings of the 10th International Conference on World Wide Web (WWW '01)*
- **Year:** 2001
- **DOI / URL:** `10.1145/371920.372071` | https://doi.org/10.1145/371920.372071
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Thuật toán lọc cộng tác kinh điển dựa trên độ tương đồng giữa các item (cosine / Pearson similarity trên ma trận tương tác).
  - *Liên kết FedGraph:* Là baseline phi tham số mạnh trên tập ứng viên lớn (**Global Catalog 82.876 tin**: `Item-KNN` đạt `Recall@20 = 0.5408`, vượt cả Centralized LightGCN `0.4002`), qua đó làm nổi bật bài toán **Global Catalog Gap** của mô hình Federated (`0.0475`) trong phần phân tích kết quả & hạn chế.

---

## Nhóm 2: Federated Learning Foundations

### `[FL-1]` FedAvg (AISTATS 2017)
- **Title:** Communication-Efficient Learning of Deep Networks from Decentralized Data
- **Authors:** H. Brendan McMahan, Eider Moore, Daniel Ramage, Seth Hampson, Blaise Agüera y Arcas
- **Venue:** *Proceedings of the 20th International Conference on Artificial Intelligence and Statistics (AISTATS '17)*, PMLR Vol. 54
- **Year:** 2017
- **DOI / URL:** https://proceedings.mlr.press/v54/mcmahan17a.html
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất thuật toán **Federated Averaging (FedAvg)** — mỗi client thực hiện nhiều bước SGD cục bộ rồi gửi cập nhật trọng số về server trung tâm tổng hợp theo trung bình có trọng số theo kích thước dữ liệu ($n_k / n$), giữ nguyên dữ liệu thô tại client.
  - *Liên kết FedGraph:* Là thuật toán điều phối lõi của FedGraph trên **9.116 employer silos** (`0 byte` dữ liệu thô rời client). Thực nghiệm V3 chứng minh `FedAvg weighted` (`0.4833`) vượt `FedAvg unweighted` (`0.4716`) trên kịch bản `20 nodes` Fixed FL Catalog và đạt `0.5756` trên `O*NET Catalog`.

### `[FL-2]` FedProx (MLSys 2020)
- **Title:** Federated Optimization in Heterogeneous Networks
- **Authors:** Tian Li, Anit Kumar Sahu, Manzil Zaheer, Maziar Sanjabi, Ameet Talwalkar, Virginia Smith
- **Venue:** *Proceedings of Machine Learning and Systems (MLSys '20)*
- **Year:** 2020
- **DOI / URL:** https://proceedings.mlsys.org/paper_files/paper/2020/file/1f5fe83998a09396ebe6477d9475ba0c-Paper.pdf | https://arxiv.org/abs/1812.06127
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Mở rộng FedAvg để xử lý **systems heterogeneity** (stragglers) và **statistical heterogeneity (Non-IID)** bằng cách thêm **proximal term** $\frac{\mu}{2}\|w - w^t\|^2$ vào hàm mục tiêu cục bộ nhằm kìm hãm **Client Drift**.
  - *Liên kết FedGraph:* Được cài đặt và đối chứng trực tiếp trong Ablation Study của FedGraph (`FedProx μ=0.01` đạt `0.4627` so với `FedAvg 0.4833`), cho thấy trên đồ thị ứng tuyển có Public Backbone chia sẻ và `local_epochs = 1`, ràng buộc proximal quá chặt có thể làm chậm tốc độ thích nghi cục bộ trong ngắn hạn (6 vòng).

### `[FL-3]` Advances and Open Problems in Federated Learning (FnT ML 2021)
- **Title:** Advances and Open Problems in Federated Learning
- **Authors:** Peter Kairouz, H. Brendan McMahan, et al. (59 co-authors)
- **Venue:** *Foundations and Trends® in Machine Learning*, Vol. 14, No. 1–2, pp. 1–210
- **Year:** 2021
- **DOI / URL:** `10.1561/2200000083` | https://doi.org/10.1561/2200000083
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Công trình tổng quan chuẩn mực phân biệt rõ mô hình **Cross-Silo FL** (tổ chức/doanh nghiệp có hạ tầng ổn định, dữ liệu phân mảnh theo tổ chức) với **Cross-Device FL**, đồng thời hệ thống hóa các thách thức về Non-IID, Straggler/Dropout, Communication Efficiency và Privacy.
  - *Liên kết FedGraph:* Làm cơ sở phân loại chính xác bài toán của FedGraph là **Cross-Silo Federated Learning** (mỗi client là một nhà tuyển dụng như `randstad` thay vì thiết bị cá nhân) và định nghĩa các yếu tố mô phỏng hệ thống trong trang **Giám sát Node FL** (Straggler latency, Client Dropout, Deadline).

### `[FL-4]` SCAFFOLD (ICML 2020)
- **Title:** SCAFFOLD: Stochastic Controlled Averaging for Federated Learning
- **Authors:** Sai Praneeth Karimireddy, Satyen Kale, Mehryar Mohri, Sashank J. Reddi, Sebastian U. Stich, Ananda Theertha Suresh
- **Venue:** *Proceedings of the 37th International Conference on Machine Learning (ICML '20)*, PMLR Vol. 119
- **Year:** 2020
- **DOI / URL:** https://proceedings.mlr.press/v119/karimireddy20a.html | https://arxiv.org/abs/1910.06378
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Phân tích lý thuyết hiện tượng **Client Drift** khi dữ liệu giữa các client là Non-IID và client thực hiện nhiều bước cập nhật cục bộ; đề xuất dùng control variates để hiệu chỉnh hướng gradient.
  - *Liên kết FedGraph:* Giải thích trực tiếp kết quả Ablation của FedGraph khi tăng `local_epochs` từ `1` lên `5`: `Recall@20` giảm từ `0.4833` xuống `0.4565` (đồng thời chậm gấp 5×) do **Client Drift** trên phân phối ứng viên-việc làm không đồng nhất giữa các doanh nghiệp.

### `[FL-5]` Non-IID Data Silos Experimental Study (ICDE 2022)
- **Title:** Federated Learning on Non-IID Data Silos: An Experimental Study
- **Authors:** Qinbin Li, Yiqun Diao, Quan Chen, Bingsheng He
- **Venue:** *Proceedings of the 38th IEEE International Conference on Data Engineering (ICDE '22)*
- **Year:** 2022
- **DOI / URL:** `10.1109/ICDE53745.2022.00077` | https://doi.org/10.1109/ICDE53745.2022.00077 | https://arxiv.org/abs/2102.02079
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đánh giá thực nghiệm toàn diện hiệu năng của FedAvg, FedProx và các biến thể trên nhiều dạng phân phối Non-IID (quantity skew, label skew, feature skew) trong bối cảnh **data silos**.
  - *Liên kết FedGraph:* Củng cố lập luận cho cấu trúc dữ liệu **CareerBuilder Cross-Silo** của FedGraph, nơi tồn tại độ lệch lớn về số lượng ứng tuyển giữa các nhà tuyển dụng (**quantity skew**: Top 1 `randstad` có `4.745` apps trong khi ngưỡng tối thiểu là `10` apps) và **44,58% user overlap** giữa các silo.

---

## Nhóm 3: Privacy-Preserving FL, Gradient Security & Compression

### `[SEC-1]` DP-SGD (CCS 2016)
- **Title:** Deep Learning with Differential Privacy
- **Authors:** Martín Abadi, Andy Chu, Ian J. Goodfellow, H. Brendan McMahan, Ilya Mironov, Kunal Talwar, Li Zhang
- **Venue:** *Proceedings of the 2016 ACM SIGSAC Conference on Computer and Communications Security (CCS '16)*
- **Year:** 2016
- **DOI / URL:** `10.1145/2976749.2978318` | https://doi.org/10.1145/2976749.2978318
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất thuật toán **DP-SGD** (cắt ngưỡng chuẩn gradient – *gradient clipping* kết hợp cộng nhiễu Gaussian) và **Moments Accountant** để theo dõi ngân sách riêng tư $(\varepsilon, \delta)$-Differential Privacy trong huấn luyện học sâu.
  - *Liên kết FedGraph:* Là chuẩn tham chiếu cho cơ chế bảo vệ quyền riêng tư mức toán học (**DP-SGD**) mà FedGraph đề xuất ở Chương 5 (Hạn chế & Hướng phát triển) nhằm bảo vệ vector cập nhật $\Delta W$ khỏi suy diễn thông tin ứng viên.

### `[SEC-2]` Practical Secure Aggregation (CCS 2017)
- **Title:** Practical Secure Aggregation for Privacy-Preserving Machine Learning
- **Authors:** Keith Bonawitz, Vladimir Ivanov, Ben Kreuter, Antonio Marcedone, H. Brendan McMahan, Sarvar Patel, Daniel Ramage, Aaron Segal, Karn Seth
- **Venue:** *Proceedings of the 2017 ACM SIGSAC Conference on Computer and Communications Security (CCS '17)*
- **Year:** 2017
- **DOI / URL:** `10.1145/3133956.3133982` | https://doi.org/10.1145/3133956.3133982
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Thiết kế giao thức mật mã **Secure Aggregation** hiệu quả cho FL, cho phép server chỉ tính được tổng $\sum_k \Delta W_k$ mà không thấy từng cập nhật riêng lẻ $\Delta W_k$ của mỗi client, đồng thời chịu được lỗi rớt kết nối (**client dropout**).
  - *Liên kết FedGraph:* Là công nghệ bổ sung trực tiếp được đề cập trong Chương 5 của FedGraph để che giấu $\Delta W$ trước server trung tâm, đặc biệt quan trọng khi mô phỏng các kịch bản có **client dropout (0–30%)** trên thực tế.

### `[SEC-3]` Deep Leakage from Gradients (NeurIPS 2019)
- **Title:** Deep Leakage from Gradients
- **Authors:** Ligeng Zhu, Zhijian Liu, Song Han
- **Venue:** *Advances in Neural Information Processing Systems (NeurIPS '19)*, Vol. 32
- **Year:** 2019
- **DOI / URL:** `10.48550/arXiv.1906.08935` | https://arxiv.org/abs/1906.08935
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Chứng minh rằng chỉ dựa vào gradient $\nabla W$ được chia sẻ trong học phân tán/FL, kẻ tấn công trung thực-nhưng-tò-mò (*honest-but-curious server*) vẫn có thể **tái tạo lại dữ liệu huấn luyện gốc** (gradient inversion attack).
  - *Liên kết FedGraph:* Tạo bằng chứng khoa học vững chắc giải thích vì sao dù FedGraph đảm bảo `0 byte raw data` rời khỏi client silo, việc truyền $\Delta W$ dạng thuần (chưa có Secure Aggregation hay DP-SGD) vẫn tiềm ẩn rủi ro suy ngược gradient — làm rõ ranh giới bảo mật hiện tại và động lực cho roadmap nâng cấp ở Chương 5.

### `[SEC-4]` Deep Gradient Compression (ICLR 2018)
- **Title:** Deep Gradient Compression: Reducing the Communication Bandwidth for Distributed Training
- **Authors:** Yujun Lin, Song Han, Huizi Mao, Yu Wang, William J. Dally
- **Venue:** *International Conference on Learning Representations (ICLR '18)*
- **Year:** 2018
- **DOI / URL:** `10.48550/arXiv.1712.01887` | https://openreview.net/forum?id=S1gUqlAWf | https://arxiv.org/abs/1712.01887
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất các kỹ thuật nén gradient (sparsification **Top-K**, quantization, momentum correction) giúp giảm mạnh băng thông truyền thông mà vẫn bảo toàn độ chính xác hội tụ.
  - *Liên kết FedGraph:* Cơ sở lý thuyết cho tính năng nén $\Delta W$ (`FP32` / `FP16` / `Top-20%` sparsification) và biểu đồ đánh đổi `Recall@20 theo MB` trong **FL Research Workbench** (`/giam-sat-node`) của FedGraph.

---

## Nhóm 4: Federated Graph Learning & Federated Recommendation

### `[FGL-1]` FedPerGNN / FedGNN (Nature Communications 2022)
- **Title:** A Federated Graph Neural Network Framework for Privacy-Preserving Personalization
- **Authors:** Chuhan Wu, Fangzhao Wu, Lingjuan Lyu, Tao Qi, Yongfeng Huang, Xing Xie
- **Venue:** *Nature Communications*, Vol. 13, Article No. 3091
- **Year:** 2022
- **DOI / URL:** `10.1038/s41467-022-30714-9` | https://doi.org/10.1038/s41467-022-30714-9
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất framework **FedPerGNN** (phát triển từ FedGNN) cho phép mỗi user client huấn luyện GNN cục bộ trên đồ thị tương tác cá nhân, bảo vệ cập nhật bằng **Local Differential Privacy (LDP)** và lấy mẫu **pseudo-interacted items**, đồng thời mở rộng đồ thị bậc cao thông qua giao thức trao đổi embedding ẩn danh giữa các user có item tương tác chung.
  - *Liên kết FedGraph:* Là công trình đối chứng trực tiếp quan trọng nhất trong **Related Work**:
    - *Điểm khác biệt cốt lõi:* FedPerGNN hướng đến **Cross-Device / User-level personalization** (mỗi client là 1 user chỉ giữ đồ thị bậc 1 của mình), phải dùng pseudo-items và giao thức mở rộng lân cận phức tạp; trong khi **FedGraph** thiết kế cho bài toán **Cross-Silo / Employer-level** (9.116 doanh nghiệp) và khai thác **Public Graph Backbone (O\*NET 52.544 cạnh công khai)** làm cầu nối ngữ nghĩa liên silo mà không cần trao đổi private user edges.

### `[FGL-2]` Federated Collaborative Filtering — FCF (arXiv 2019)
- **Title:** Federated Collaborative Filtering for Privacy-Preserving Personalized Recommendation System
- **Authors:** Muhammad Ammad-ud-din, Elena Ivannikova, Suleiman A. Khan, Were Oyomno, Qiang Fu, Kuan Eeik Tan, Adrian Flanagan
- **Venue:** *arXiv preprint arXiv:1901.09888*
- **Year:** 2019
- **DOI / URL:** `10.48550/arXiv.1901.09888` | https://arxiv.org/abs/1901.09888
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Công trình tiên phong chuyển hóa Matrix Factorization (Collaborative Filtering cho implicit feedback) sang mô hình Federated Learning: giữ user factor cục bộ trên thiết bị và chỉ đồng bộ cập nhật item factors lên server.
  - *Liên kết FedGraph:* Đánh dấu cột mốc khởi đầu của **Federated Recommendation** trong phần Tổng quan nghiên cứu liên quan, làm tiền đề cho sự chuyển dịch từ MF tuyến tính sang GNN đa tầng (LightGCN) trong FedGraph.

### `[FGL-3]` FedFast (KDD 2020)
- **Title:** FedFast: Going Beyond Average for Faster Training of Federated Recommender Systems
- **Authors:** Khalil Muhammad, Qinqin Wang, Diarmuid O'Reilly-Morgan, Elias Z. Tragos, Barry Smyth, Neil Hurley, James Geraci, Aonghus Lawlor
- **Venue:** *Proceedings of the 26th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '20)*
- **Year:** 2020
- **DOI / URL:** `10.1145/3394486.3403176` | https://doi.org/10.1145/3394486.3403176
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Cải thiện tốc độ hội tụ cho hệ gợi ý liên bang bằng kỹ thuật lấy mẫu client đại diện (*ActvSAMP*) và tổng hợp trọng số thích ứng (*ActvAGG*) thay cho lấy mẫu ngẫu nhiên thuần túy của FedAvg.
  - *Liên kết FedGraph:* Hỗ trợ trực tiếp cho phân tích ở Chương 5 của FedGraph về hướng khắc phục **Global Catalog Gap** (`0.0475` ở 50N FedAvg) thông qua chiến lược **Stratified Client Sampling** qua nhiều vòng hơn trên `9.116` silos.

### `[FGL-4]` MetaMF (SIGIR 2020)
- **Title:** Meta Matrix Factorization for Federated Rating Predictions
- **Authors:** Yujie Lin, Pengjie Ren, Zhumin Chen, Zhaochun Ren, Dongxiao Yu, Jun Ma, Maarten de Rijke, Xiuzhen Cheng
- **Venue:** *Proceedings of the 43rd International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR '20)*
- **Year:** 2020
- **DOI / URL:** `10.1145/3397271.3401081` | https://doi.org/10.1145/3397271.3401081
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Dùng meta-network sinh tham số mô hình cá nhân hóa cho từng client trong môi trường Federated Recommender System với tài nguyên tính toán hạn chế.
  - *Liên kết FedGraph:* Bổ sung bức tranh các phương pháp Federated Matrix Factorization trước khi GNN trở thành xu hướng chủ đạo trong gợi ý liên bang.

### `[FGL-5]` FedRec (IEEE Intelligent Systems 2021)
- **Title:** FedRec: Federated Recommendation With Explicit Feedback
- **Authors:** Guanyu Lin, Feng Liang, Weike Pan, Zhong Ming
- **Venue:** *IEEE Intelligent Systems*, Vol. 36, No. 5, pp. 21–30 (Early Access 2020)
- **Year:** 2021
- **DOI / URL:** `10.1109/MIS.2020.3017205` | https://doi.org/10.1109/MIS.2020.3017205
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất cơ chế trung bình lai (hybrid filling) và lấy mẫu ảo trên phản hồi tường minh để tránh lộ danh sách item thực sự mà người dùng đã đánh giá khi gửi gradient lên server.
  - *Liên kết FedGraph:* Làm rõ vấn đề **lộ thông tin item từ gradient embedding** (trong bài toán của FedGraph là tập tin tuyển dụng `job` mà ứng viên nộp đơn ở mỗi silo), đồng thời phân biệt giữa bài toán explicit feedback (`FedRec`) và implicit feedback trên đồ thị không đồng nhất (`FedGraph`).

### `[FGL-6]` FedGraph (IEEE TPDS 2022)
- **Title:** FedGraph: Federated Graph Learning With Intelligent Sampling
- **Authors:** Fahao Chen, Peng Li, Toshiaki Miyazaki, Celimuge Wu
- **Venue:** *IEEE Transactions on Parallel and Distributed Systems (TPDS)*, Vol. 33, Issue 8 (Early Access 2021)
- **Year:** 2022
- **DOI / URL:** `10.1109/TPDS.2021.3125565` | https://doi.org/10.1109/TPDS.2021.3125565
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất nền tảng **Federated Graph Learning** cho bài toán cross-client graph learning thông qua cộng tác liên miền (cross-domain collaboration) và lấy mẫu lân cận thông minh bằng Deep Reinforcement Learning (DRL) để cân bằng độ chính xác và chi phí truyền thông.
  - *Liên kết FedGraph:* Trùng tên gọi **FedGraph** trong tài liệu học thuật nên rất cần phân biệt rõ trong Related Work: công trình TPDS 2022 của Chen et al. tập trung vào node classification với DRL sampling trên các đồ thị con có thể trao đổi thông tin chéo, còn đồ án **FedGraph** của nhóm là hệ thống gợi ý việc làm Cross-Silo LightGCN dựa trên **Public Graph Backbone (O\*NET)** và **Private Employer Silos**.

### `[FGL-7]` FedSage / FedSage+ (NeurIPS 2021)
- **Title:** Subgraph Federated Learning with Missing Neighbor Generation
- **Authors:** Ke Zhang, Carl Yang, Xiaoxiao Li, Lichao Sun, Siu Ming Yiu
- **Venue:** *Advances in Neural Information Processing Systems (NeurIPS '21)*, Vol. 34
- **Year:** 2021
- **DOI / URL:** `10.48550/arXiv.2106.13430` | https://arxiv.org/abs/2106.13430
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Chỉ ra bài toán **missing cross-subgraph edges** khi một đồ thị lớn bị phân mảnh thành các đồ thị con cục bộ; đề xuất mô hình sinh lân cận bị thiếu (*Neighbor Generator* — FedSage+) để phục hồi liên kết liên client.
  - *Liên kết FedGraph:* Phản ánh chính xác thách thức của **FedGraph** khi `44,58%` ứng viên ứng tuyển đa công ty (mất các cạnh liên silo khi nhìn từ một employer). Thay vì dùng generative model ước lượng cạnh ẩn như FedSage+, FedGraph tận dụng cấu trúc tri thức công khai **O\*NET (`job–occupation–skill`)** làm cầu nối tự nhiên giúp tăng **+9.0% Recall@20** (`0.3933` → `0.4833`) trong Ablation Study.

### `[FGL-8]` FED-PUB (ICML 2023)
- **Title:** Personalized Subgraph Federated Learning
- **Authors:** Jinheon Baek, Wonyong Jeong, Jiongdao Jin, Jaehong Yoon, Sung Ju Hwang
- **Venue:** *Proceedings of the 40th International Conference on Machine Learning (ICML '23)*, PMLR Vol. 202
- **Year:** 2023
- **DOI / URL:** `10.48550/arXiv.2206.10206` | https://proceedings.mlr.press/v202/baek23a.html
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Đề xuất **FED-PUB** sử dụng đồ thị cộng đồng ẩn và tổng hợp tương đồng chức năng (*functional embedding similarity*) để cá nhân hóa mô hình giữa các đồ thị con không đồng nhất (Non-IID subgraphs).
  - *Liên kết FedGraph:* Tài liệu hiện đại (ICML 2023) khẳng định xu hướng khai thác cấu trúc tương đồng cộng đồng/ngữ nghĩa trong **Subgraph Federated Learning** để giảm nhiễu khi tổng hợp các silo có phân phối cục bộ khác nhau.

### `[FGL-9]` FedGraphNN (ICLR 2021 DPML Workshop / arXiv 2021)
- **Title:** FedGraphNN: A Federated Learning System and Benchmark for Graph Neural Networks
- **Authors:** Chaoyang He, Keshav Balasubramanian, Emir Ceyani, Carl Yang, Han Xie, Lichao Sun, Lifang He, Liangwei Yang, Philip S. Yu, Yu Rong, Peilin Zhao, Junzhou Huang, Murali Annavaram, Salman Avestimehr
- **Venue:** *ICLR 2021 Workshop on Distributed and Private Machine Learning (DPML) / arXiv:2104.07145*
- **Year:** 2021
- **DOI / URL:** `10.48550/arXiv.2104.07145` | https://arxiv.org/abs/2104.07145
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Hệ thống benchmark chuẩn hóa cho Federated Graph Neural Networks trên cả mức đồ thị (graph-level), mức nút (node-level) và dự đoán liên kết (link-level) với kiến trúc tách biệt dữ liệu Non-IID.
  - *Liên kết FedGraph:* Là cơ sở tham chiếu về thiết kế thực nghiệm benchmark và kiến trúc tách biệt dữ liệu đồ thị trong Federated Graph Learning.

### `[FGL-10]` Federated Graph Machine Learning Survey (ACM SIGKDD Explorations 2022)
- **Title:** Federated Graph Machine Learning: A Survey of Concepts, Techniques, and Applications
- **Authors:** Xingbo Fu, Binchi Zhang, Yushun Dong, Chen Chen, Jundong Li
- **Venue:** *ACM SIGKDD Explorations Newsletter*
- **Year:** 2022
- **DOI / URL:** `10.1145/3575637.3575644` | https://doi.org/10.1145/3575637.3575644
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Phân loại hệ thống hóa các kịch bản **Federated Graph Learning** (Inter-graph FL, Intra-graph FL — Horizontal & Vertical) và chỉ rõ thách thức cấu trúc liên kết giữa các đồ thị con bị cắt đứt.
  - *Liên kết FedGraph:* Giúp định vị chính xác bài toán **FedGraph** thuộc nhóm **Intra-graph Horizontal/Subgraph FL** (các silo chia sẻ một phần thực thể ứng viên và một khung tri thức nghề nghiệp công khai).

### `[FGL-11]` Federated GNN Survey (IEEE TNNLS 2025)
- **Title:** Federated Graph Neural Networks: Overview, Techniques, and Challenges
- **Authors:** Rui Liu, Pengwei Xing, Zichao Deng, Anran Li, Cuntai Guan, Han Yu
- **Venue:** *IEEE Transactions on Neural Networks and Learning Systems (TNNLS)* (Early Access 2024)
- **Year:** 2025
- **DOI / URL:** `10.1109/TNNLS.2024.3360429` | https://doi.org/10.1109/TNNLS.2024.3360429
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Tổng quan cập nhật về Federated GNNs, phân tích sâu các bài toán về tính không đồng nhất đồ thị (graph heterogeneity), bảo mật kết nối liên client và chi phí truyền thông.
  - *Liên kết FedGraph:* Làm tài liệu tổng quan cập nhật nhất để đối chiếu vị trí của FedGraph trong bối cảnh nghiên cứu hiện đại.

### `[FGL-12]` Survey on Federated Recommendation Systems (IEEE TNNLS 2024)
- **Title:** A Survey on Federated Recommendation Systems
- **Authors:** Zehua Sun, Yonghui Xu, Y. Liu, Weiliang He, Ya Li Jiang, Fangzhao Wu, Li-zhen Cui
- **Venue:** *IEEE Transactions on Neural Networks and Learning Systems (TNNLS)*
- **Year:** 2024
- **DOI / URL:** `10.1109/TNNLS.2024.3354924` | https://doi.org/10.1109/TNNLS.2024.3354924
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Tổng kết toàn diện các mô hình gợi ý liên bang (FedRec), phân tích tam giác đánh đổi **Accuracy – Privacy – Communication Efficiency** và nhấn mạnh khoảng trống ứng dụng vào các miền đặc thù có đồ thị tri thức như tuyển dụng.
  - *Liên kết FedGraph:* Cung cấp khung tiêu chí đánh giá học thuật để biện minh cho bộ chỉ số (`Recall@20`, `NDCG@20`, `MRR@20`, chi phí băng thông MB theo mức nén $\Delta W$, và latency `p50/p95`) trong FedGraph.

---

## Nhóm 5: Job Recommendation, CareerBuilder & O\*NET Skill Taxonomy

### `[JOB-1]` Job Recommender Systems: A Review (arXiv 2021)
- **Title:** Job Recommender Systems: A Review
- **Authors:** Corné de Ruijt, Sandjai Bhulai
- **Venue:** *arXiv preprint arXiv:2111.13576*
- **Year:** 2021
- **DOI / URL:** `10.48550/arXiv.2111.13576` | https://arxiv.org/abs/2111.13576
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Tổng quan chuyên sâu về hệ gợi ý việc làm (Job Recommender Systems – JRS), phân tích đặc thù **tính chất hai phía (reciprocal matching)**, độ thưa cực cao của tương tác ứng tuyển, và vấn đề **cold-start** cho tin tuyển dụng mới.
  - *Liên kết FedGraph:* Giải thích vì sao bài toán gợi ý việc làm khác biệt với gợi ý phim/thương mại điện tử (nhiều tin chỉ tồn tại ngắn hạn, `1.969` cold-start jobs trong V3) và vai trò của tri thức kỹ năng/nghề nghiệp để bù đắp độ thưa tương tác.

### `[JOB-2]` Challenge-Based Survey of E-Recruitment RS (ACM Computing Surveys 2024)
- **Title:** A Challenge-Based Survey of E-Recruitment Recommendation Systems
- **Authors:** Yoosof Mashayekhi, Nan Li, Bo Kang, Jefrey Lijffijt, Tijl De Bie
- **Venue:** *ACM Computing Surveys*, Vol. 56, Issue 10
- **Year:** 2024
- **DOI / URL:** `10.1145/3659942` | https://doi.org/10.1145/3659942
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Phân tích hệ gợi ý tuyển dụng theo góc độ thách thức: quyền riêng tư dữ liệu ứng viên/doanh nghiệp (GDPR), thiên lệch (bias), tính giải thích thông qua kỹ năng (**skill-based explainability**) và khoảng cách giữa đánh giá offline với **Online A/B Test**.
  - *Liên kết FedGraph:* Ủng hộ trực tiếp cả hai luận điểm cốt lõi của FedGraph: (1) động lực tuân thủ GDPR / bảo vệ dữ liệu ứng tuyển bằng Cross-Silo FL, và (2) đánh giá trung thực hạn chế ở Chương 5 về việc chưa triển khai **Online A/B Test** đo CTR và sự hài lòng thực tế.

### `[JOB-3]` Skills2Job — Graph Databases for Skill-Based Job Recommendation (Applied Soft Computing 2021)
- **Title:** Skills2Job: A recommender system that encodes job offer embeddings on graph databases
- **Authors:** Anna Giabelli, Lorenzo Malandri, Fabio Mercorio, Mario Mezzanzanica, Andrea Seveso
- **Venue:** *Applied Soft Computing*, Vol. 101, 107049
- **Year:** 2021
- **DOI / URL:** `10.1016/j.asoc.2020.107049` | https://doi.org/10.1016/j.asoc.2020.107049
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Xây dựng biểu diễn đồ thị liên kết **kỹ năng (skills)** và **tin tuyển dụng (job offers)** trên cơ sở dữ liệu đồ thị để tính embedding phục vụ gợi ý nghề nghiệp chính xác hơn so với đối khớp từ khóa thuần túy.
  - *Liên kết FedGraph:* Chứng minh tính hiệu quả của mô hình hóa **skill-job graph** và hỗ trợ trực tiếp cho thiết kế đồ thị không đồng nhất 4 loại nút (`User – Job – Occupation – Skill`) cùng suy luận `user_skills` 2-hop của FedGraph.

### `[JOB-4]` Job Matching and Skill Recommendation with Transformers & O\*NET (Big Data Research 2025)
- **Title:** A novel approach for job matching and skill recommendation using transformers and the O*NET database
- **Authors:** Rubén Alonso, Danilo Dessí, Antonello Meloni, Diego Reforgiato Recupero
- **Venue:** *Big Data Research*
- **Year:** 2025
- **DOI / URL:** `10.1016/j.bdr.2025.100509` | https://doi.org/10.1016/j.bdr.2025.100509
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Kết hợp các thực thể nghề nghiệp và kỹ năng từ cơ sở dữ liệu **O\*NET** với mô hình **Transformer** (semantic embeddings) để đối khớp ngữ nghĩa giữa hồ sơ ứng viên và mô tả công việc, khắc phục giới hạn so khớp chuỗi chính xác.
  - *Liên kết FedGraph:* Minh chứng thực tiễn cho hướng phát triển số 1 của FedGraph ở Chương 5: dùng **Sentence-BERT / Transformer semantic similarity** để nâng tỷ lệ ánh xạ `job–occupation` O\*NET từ `31.44%` hiện tại lên `>85%` trên toàn bộ `84.845` tin tuyển dụng.

### `[JOB-5]` CareerBuilder Large-Scale Job Matching (arXiv 2021)
- **Title:** Embedding-based Recommender System for Job to Candidate Matching on Scale
- **Authors:** Jing Zhao, Jingya Wang, Madhav Sigdel, Bopeng Zhang, Phuong Hoang, Mengshu Liu, Mohammed Korayem
- **Venue:** *arXiv preprint arXiv:2107.00221* (CareerBuilder Research)
- **Year:** 2021
- **DOI / URL:** `10.48550/arXiv.2107.00221` | https://arxiv.org/abs/2107.00221
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Trình bày kiến trúc học biểu diễn embedding cho hệ thống gợi ý việc làm quy mô công nghiệp tại **CareerBuilder**, giải quyết bài toán khớp tin tuyển dụng – ứng viên ở quy mô hàng triệu bản ghi.
  - *Liên kết FedGraph:* Tài liệu tham khảo thực tiễn gắn liền với nguồn dữ liệu **CareerBuilder** mà FedGraph sử dụng để trích xuất `171.807` users, `84.845` jobs và `9.116` nhà tuyển dụng (FL silos).

### `[JOB-6]` O\*NET 29.3 Database (U.S. Department of Labor, 2025)
- **Title:** O*NET 29.3 Database
- **Authors / Organization:** National Center for O*NET Development (U.S. Department of Labor, Employment and Training Administration)
- **Venue:** *Official Relational Database Release (Version 29.3)*
- **Year:** 2025
- **URL:** https://www.onetcenter.org/database.html
- **Tóm tắt học thuật & Liên kết với FedGraph:**
  - *Đóng góp cốt lõi:* Hệ thống phân loại nghề nghiệp và kỹ năng chuẩn quốc gia Hoa Kỳ (Occupational Information Network), cung cấp ánh xạ chuẩn hóa giữa mã nghề nghiệp (SOC/O\*NET occupations) và danh mục kỹ năng công nghệ (Technology Skills).
  - *Liên kết FedGraph:* Nguồn dữ liệu chính xác tạo nên **Public Graph Backbone (`583` O\*NET Occupations, `7.760` Tech Skills, `52.544` public edges)** của FedGraph, đóng vai trò cầu nối ngữ nghĩa giữa các client silos độc lập.

---

## Gợi ý chuẩn trích dẫn IEEE cho cuối Báo cáo `.docx`

```text
[1] X. He, K. Deng, X. Wang, Y. Li, Y. Zhang, and M. Wang, "LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation," in Proc. 43rd Int. ACM SIGIR Conf. Res. Develop. Inf. Retr. (SIGIR '20), 2020, pp. 639-648, doi: 10.1145/3397271.3401063.
[2] X. Wang, X. He, M. Wang, F. Feng, and T.-S. Chua, "Neural Graph Collaborative Filtering," in Proc. 42nd Int. ACM SIGIR Conf. Res. Develop. Inf. Retr. (SIGIR '19), 2019, doi: 10.1145/3331184.3331267.
[3] S. Rendle, C. Freudenthaler, Z. Gantner, and L. Schmidt-Thieme, "BPR: Bayesian Personalized Ranking from Implicit Feedback," in Proc. 25th Conf. Uncertainty Artif. Intell. (UAI '09), 2009, doi: 10.48550/arXiv.1205.2618.
[4] W. L. Hamilton, Z. Ying, and J. Leskovec, "Inductive Representation Learning on Large Graphs," in Adv. Neural Inf. Process. Syst. (NeurIPS '17), vol. 30, 2017.
[5] B. Sarwar, G. Karypis, J. Konstan, and J. Riedl, "Item-based collaborative filtering recommendation algorithms," in Proc. 10th Int. Conf. World Wide Web (WWW '01), 2001, doi: 10.1145/371920.372071.
[6] H. B. McMahan, E. Moore, D. Ramage, S. Hampson, and B. Agüera y Arcas, "Communication-Efficient Learning of Deep Networks from Decentralized Data," in Proc. 20th Int. Conf. Artif. Intell. Statist. (AISTATS '17), PMLR vol. 54, 2017.
[7] T. Li, A. K. Sahu, M. Zaheer, M. Sanjabi, A. Talwalkar, and V. Smith, "Federated Optimization in Heterogeneous Networks," in Proc. Mach. Learn. Syst. (MLSys '20), 2020.
[8] P. Kairouz et al., "Advances and Open Problems in Federated Learning," Found. Trends Mach. Learn., vol. 14, no. 1-2, pp. 1-210, 2021, doi: 10.1561/2200000083.
[9] S. P. Karimireddy, S. Kale, M. Mohri, S. J. Reddi, S. U. Stich, and A. T. Suresh, "SCAFFOLD: Stochastic Controlled Averaging for Federated Learning," in Proc. 37th Int. Conf. Mach. Learn. (ICML '20), PMLR vol. 119, 2020.
[10] Q. Li, Y. Diao, Q. Chen, and B. He, "Federated Learning on Non-IID Data Silos: An Experimental Study," in Proc. IEEE 38th Int. Conf. Data Eng. (ICDE '22), 2022, doi: 10.1109/ICDE53745.2022.00077.
[11] M. Abadi et al., "Deep Learning with Differential Privacy," in Proc. 2016 ACM SIGSAC Conf. Comput. Commun. Secur. (CCS '16), 2016, doi: 10.1145/2976749.2978318.
[12] K. Bonawitz et al., "Practical Secure Aggregation for Privacy-Preserving Machine Learning," in Proc. 2017 ACM SIGSAC Conf. Comput. Commun. Secur. (CCS '17), 2017, doi: 10.1145/3133956.3133982.
[13] L. Zhu, Z. Liu, and S. Han, "Deep Leakage from Gradients," in Adv. Neural Inf. Process. Syst. (NeurIPS '19), vol. 32, 2019, doi: 10.48550/arXiv.1906.08935.
[14] Y. Lin, S. Han, H. Mao, Y. Wang, and W. J. Dally, "Deep Gradient Compression: Reducing the Communication Bandwidth for Distributed Training," in Int. Conf. Learn. Represent. (ICLR '18), 2018, doi: 10.48550/arXiv.1712.01887.
[15] C. Wu, F. Wu, L. Lyu, T. Qi, Y. Huang, and X. Xie, "A Federated Graph Neural Network Framework for Privacy-Preserving Personalization," Nature Communications, vol. 13, art. 3091, 2022, doi: 10.1038/s41467-022-30714-9.
[16] M. Ammad-ud-din et al., "Federated Collaborative Filtering for Privacy-Preserving Personalized Recommendation System," arXiv:1901.09888, 2019, doi: 10.48550/arXiv.1901.09888.
[17] K. Muhammad et al., "FedFast: Going Beyond Average for Faster Training of Federated Recommender Systems," in Proc. 26th ACM SIGKDD Int. Conf. Knowl. Discov. Data Min. (KDD '20), 2020, doi: 10.1145/3394486.3403176.
[18] Y. Lin et al., "Meta Matrix Factorization for Federated Rating Predictions," in Proc. 43rd Int. ACM SIGIR Conf. Res. Develop. Inf. Retr. (SIGIR '20), 2020, doi: 10.1145/3397271.3401081.
[19] G. Lin, F. Liang, W. Pan, and Z. Ming, "FedRec: Federated Recommendation With Explicit Feedback," IEEE Intell. Syst., vol. 36, no. 5, pp. 21-30, 2021, doi: 10.1109/MIS.2020.3017205.
[20] F. Chen, P. Li, T. Miyazaki, and C. Wu, "FedGraph: Federated Graph Learning With Intelligent Sampling," IEEE Trans. Parallel Distrib. Syst., vol. 33, no. 8, 2022, doi: 10.1109/TPDS.2021.3125565.
[21] K. Zhang, C. Yang, X. Li, L. Sun, and S. M. Yiu, "Subgraph Federated Learning with Missing Neighbor Generation," in Adv. Neural Inf. Process. Syst. (NeurIPS '21), vol. 34, 2021, doi: 10.48550/arXiv.2106.13430.
[22] J. Baek, W. Jeong, J. Jin, J. Yoon, and S. J. Hwang, "Personalized Subgraph Federated Learning," in Proc. 40th Int. Conf. Mach. Learn. (ICML '23), PMLR vol. 202, 2023, doi: 10.48550/arXiv.2206.10206.
[23] C. He et al., "FedGraphNN: A Federated Learning System and Benchmark for Graph Neural Networks," ICLR 2021 Workshop on DPML / arXiv:2104.07145, 2021, doi: 10.48550/arXiv.2104.07145.
[24] X. Fu, B. Zhang, Y. Dong, C. Chen, and J. Li, "Federated Graph Machine Learning: A Survey of Concepts, Techniques, and Applications," ACM SIGKDD Explor. Newsl., 2022, doi: 10.1145/3575637.3575644.
[25] R. Liu, P. Xing, Z. Deng, A. Li, C. Guan, and H. Yu, "Federated Graph Neural Networks: Overview, Techniques, and Challenges," IEEE Trans. Neural Netw. Learn. Syst., 2025, doi: 10.1109/TNNLS.2024.3360429.
[26] Z. Sun, Y. Xu, Y. Liu, W. He, Y. L. Jiang, F. Wu, and L.-z. Cui, "A Survey on Federated Recommendation Systems," IEEE Trans. Neural Netw. Learn. Syst., 2024, doi: 10.1109/TNNLS.2024.3354924.
[27] C. de Ruijt and S. Bhulai, "Job Recommender Systems: A Review," arXiv:2111.13576, 2021, doi: 10.48550/arXiv.2111.13576.
[28] Y. Mashayekhi, N. Li, B. Kang, J. Lijffijt, and T. De Bie, "A Challenge-Based Survey of E-Recruitment Recommendation Systems," ACM Comput. Surv., vol. 56, no. 10, 2024, doi: 10.1145/3659942.
[29] A. Giabelli, L. Malandri, F. Mercorio, M. Mezzanzanica, and A. Seveso, "Skills2Job: A recommender system that encodes job offer embeddings on graph databases," Appl. Soft Comput., vol. 101, art. 107049, 2021, doi: 10.1016/j.asoc.2020.107049.
[30] R. Alonso, D. Dessí, A. Meloni, and D. Reforgiato Recupero, "A novel approach for job matching and skill recommendation using transformers and the O*NET database," Big Data Res., art. 100509, 2025, doi: 10.1016/j.bdr.2025.100509.
[31] J. Zhao, J. Wang, M. Sigdel, B. Zhang, P. Hoang, M. Liu, and M. Korayem, "Embedding-based Recommender System for Job to Candidate Matching on Scale," arXiv:2107.00221, 2021, doi: 10.48550/arXiv.2107.00221.
[32] National Center for O*NET Development, "O*NET 29.3 Database," U.S. Department of Labor, Employment and Training Administration, 2025. [Online]. Available: https://www.onetcenter.org/database.html
```
