# Bảng tổng kết — 01_gnn_fl.ipynb

Sinh tự động lúc 2026-11-09 03:25:35 | SCALE=small | device=cuda

| Yêu cầu | Đạt | Số đo |
|---|---|---|
| [1] Mục tiêu + GraphSafe + 3 GNN | ĐẠT | 4 điều kiện GraphSafe; LightGCN/GraphSAGE/GAT đều huấn luyện thật |
| [2] MEDAJob (case study) + CareerBuilder (chính) | ĐẠT | 1.603.111 app | 377.132 job có employer | 697.396 app có employer | 9,116 client; ghi rõ MEDAJob do 20 tài khoản thử nghiệm |
| [3] EDA + tiền xử lý | ĐẠT | app/user median 1 | app/job median 2 | thưa 99.9973% | job có nghề 31.44% | client median 23 app |
| [4] Kiến trúc GNN + FL, cross-silo hợp lệ | ĐẠT | sơ đồ + giải thích; 16.29% cạnh test có client_of_user==client_of_job → phải gán theo client_of_job; 0 client rỗng |
| [5] Sweep dim/layers/n_clients/local_epochs | ĐẠT | 8 cấu hình; bảng + 4 biểu đồ |
| [6] Môi trường, cài đặt, mount Drive, hướng dẫn upload | ĐẠT | bootstrap tự dò ART | device=cuda | không cần torch_geometric | 5 bước upload Kaggle |
| [7] Recall@10/20, NDCG@20, MRR@20, coverage, CI 95%, baseline | ĐẠT | 6 hệ + FedAvg; R@20 FedAvg=0.0475 (vũ trụ FL: 0.3905) | Popularity=0.0154 | 3 tập: đầy đủ/37,077 sạch/bỏ 1,969 cold-start |
| [8] Ablation (a)-(e) + 2 bổ sung | ĐẠT | 15 biến thể; chấm trên vũ trụ cố định 4,511 job; nhóm (f) trên catalog job-có-nghề |
| [9] WebAPI + PostgreSQL | ĐẠT | sơ đồ kiến trúc + luồng request + 9 bảng + 11 endpoint; trỏ api/, ui/ |
| [10] UI giám sát node + độ trễ p50/p95 | ĐẠT | p50=236.49 ms | p95=315.45 ms | 300 mẫu perf_counter |

## Thời gian chạy

| Section | Giây | Ghi chú |
|---|---|---|
| [3] EDA | 1.12 |  |
| [4] Kiến trúc + chia client | 1.17 |  |
| [5] Phân tích tham số | 242.57 | 8 cấu hình |
| [6] Môi trường | 0.0 |  |
| [7] Đánh giá | 278.0 | 7 hệ |
| [7f] Tách nhóm client | 55.55 | 6,978 client có test |
| [8] Ablation | 354.76 | 15 biến thể |
| [9] WebAPI + PostgreSQL | 0.0 |  |
| [10] UI + độ trễ | 0.45 |  |
| Ghi metrics | 0.01 |  |
| **TỔNG** | **943.1** | ~15.7 phút |
