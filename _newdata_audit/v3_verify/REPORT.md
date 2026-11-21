# t5 — Kiểm chứng độc lập artifacts/v3

**Verdict: PASS** — 87 hạng mục kiểm tra: **84 PASS / 3 WARN / 0 FAIL**, không có blocking finding.
Script: [`verify_v3.py`](verify_v3.py) — chỉ đọc file thật (`graph.npz`, `clients.json`, `meta.json`, `job_titles.json`, `user_titles.json`, O*NET zip), không import code của t1.
Số đo đầy đủ: [`v3_verify.json`](v3_verify.json). Log: [`verify_run.log`](verify_run.log).

## Bảng đối chiếu với baseline của captain

| # | Hạng mục | Kỳ vọng (baseline captain) | Thực tế (tôi đo lại) | Kết luận |
|---|---|---|---|---|
| 1.1 | `edge_index` | (2, 764.364) int64 | (2, 764.364) int64 | PASS |
| 1.2 | `edge_type` / masks | (764.364,) int16 / bool | y hệt | PASS |
| 1.3 | n_nodes | 264.995 | 264.995 | PASS |
| 1.4 | khối nút | 171.807 u + 84.845 j + 583 o + 7.760 s | khớp tuyệt đối | PASS |
| 1.5 | offsets | [0, 171807, 256652, 257235] | khớp | PASS |
| 2.1 | self-loop | 0 | 0 | PASS |
| 2.2 | cạnh trùng (kể cả đảo chiều) | 0 | 0 trùng / 764.364 unique | PASS |
| 2.3 | index min/max | 0 / 264.994 | 0 / 264.994 | PASS |
| 3.1 | train ∩ test | 0 | 0 | PASS |
| 3.2 | train_mask | 726.407 (398.936 user-job + 327.471 khác) | khớp | PASS |
| 3.3 | test_mask | 37.957, 100% là user-job | khớp | PASS |
| 3.4 | edge_type 0/1/2/3 | 436.893 / 26.678 / 25.866 / 274.927 | khớp cả 4 | PASS |
| 5.1 | client | 9.116, id 0..9115 liên tục | khớp | PASS |
| 5.2 | min app/client | ≥10 | min = 10, không client nào <10 | PASS |
| 5.3 | tổng n_apps | 436.893 | 436.893 = số cạnh user-job | PASS |
| 5.4 | n_apps từng client | khớp clients.json | **0 mismatch trên 9.116 client** (đếm lại từ graph) | PASS |
| 6.1 | mã nghề | **7 ký tự** (soc[:7]) | 583/583 dài 7, cùng một cấp | PASS |
| 6.13 | job có cạnh nghề | 26.678 | 26.678 (31,44%); 58.167 job không nghề | PASS |
| 7.x | skill layer | không thoái hoá | 0% nghề có đủ 7.760 skill; 564/583 nghề có skill | PASS |
| 8.8 | job mồ côi (0 cạnh user-job) | 0 | 0 | PASS |
| 11.1 | khớp baseline | 0 lệch | 3 lệch, **cả 3 do mẫu số** (xem dưới) | PASS |
| 12.1 | tính tất định | md5 giống nhau | **graph.npz/clients.json/2 file titles byte-identical qua 3 lần chạy** | PASS |

### 3 số "lệch" của baseline — do mẫu số, không do dữ liệu
| Số | Captain | Tôi (583 nghề) | Tôi (564 nghề CÓ skill) |
|---|---|---|---|
| skill/nghề min | 2 | 0 | **2** ✓ |
| skill/nghề median | 24 | 23 | **24** ✓ |
| skill/nghề mean | 45,9 | 44,37 | **45,86** ✓ |

Captain tính trên 564 nghề có skill; tôi tính trên cả 583 (gồm 19 nghề 0 skill). Trên cùng mẫu số thì khớp tuyệt đối.

## 3 WARN — phải khai báo, không phải lỗi schema

| # | Vấn đề | Số đo | Ảnh hưởng |
|---|---|---|---|
| **10.3** | **Rò rỉ gián tiếp qua nghề**: cạnh test (u→j) mà u và j cùng nối tới một nút nghề bằng cạnh TRAIN | **880 / 37.957 cạnh test = 2,32%** | Mô hình có thể chấm đúng các cạnh này mà không học từ nhãn test → **R@20 bị phồng nhẹ**. Bắt buộc khai báo trong notebook; nên báo thêm metric trên tập con không có đường vòng u–occ–j. |
| **10.1b** | Job chỉ có tương tác trong TEST, 0 cạnh train ("test-only job") | **1.969 job (2,32%)**, đều là job chỉ có 1 application | Chia theo user nên job 1 tương tác rơi trọn vào test. Không phải rò rỉ, nhưng là **cold-start item** khi tính R@20. |
| **6.12b** | `user_titles.json` chứa mã nghề **không phải nút đồ thị** | **202 mã / 1.655 user** (vd `17-3019`, `25-9099`); 1.217 user trong số đó vẫn có cạnh user-occ | Mọi mã đều dài 7 ký tự và **có thật trong O\*NET** (không trộn cấp), nhưng là dangling reference: `JOIN user_titles.occupation → occ node` sẽ miss 202 mã. Nguyên nhân: metadata lấy nghề của title sequence lớn nhất (nghề đó không có job nào → không thành nút), còn cạnh lấy toàn bộ nghề trong history. |

## Hai điểm đo được mà báo cáo của t1 KHÔNG nêu (`artifacts/v3_verify.txt`)
t1 kết luận "TAT CA PASS" — **không sai**, nhưng bỏ sót:
1. `min_apps_for_test=5` khiến **63,3% cạnh user-job không bao giờ vào test** (user <5 app). Tỉ lệ test trên *toàn bộ* cạnh user-job chỉ **8,69%**, không phải 20%. Trên tập đủ điều kiện (>5 app) là **19,55%** → chia đúng, nhưng con số 20% trong meta dễ bị đọc nhầm là trên toàn bộ cạnh.
2. `is_public` chỉ bật cho occ+skill (8.343), **job = 0 dù có employer metadata**. Tên trường dễ hiểu nhầm; nên đọc là `is_catalog_node`.

## Kiểm chứng sâu theo yêu cầu của captain
- **(a) Rò rỉ theo user**: user có test nhưng 0 train = **0** (không cold-start user). 20.067 user có cạnh test, tất cả đều có ≥5 app và ≥1 cạnh train.
- **(b) Rò rỉ gián tiếp**: **880 cạnh (2,32%)** — xem WARN 10.3.
- **(c) Trùng cạnh**: `(src,dst,type)` trùng = **0**; cạnh vô hướng trùng = **0** (nhờ quy ước 1 dòng/cạnh).
- **(d) Nhất quán silo**: `client_of_job` hợp lệ 100%; tổng app theo client từ cạnh **không vượt** `n_apps` của clients.json; `client_of_user` = **argmax chính xác** trên cả 171.807 user (hoà → client_id nhỏ hơn, 0 mismatch). Chỉ **43,15%** cạnh có `client_of_user[u] == client_of_job[j]` — **đây KHÔNG phải lỗi**: `client_of_user` chỉ là nhãn "client nhiều app nhất", không phải membership độc quyền. 44,58% user ứng tuyển ở ≥2 employer, đúng bản chất FL theo employer.
- **(e) Tất định**: chạy lại 2 lần trong thư mục sạch (`run_a`, `run_b`), **md5 giống hệt** bản `artifacts/v3` cho `graph.npz` (6c956541…), `clients.json`, `job_titles.json`, `user_titles.json`. `meta.json` chỉ khác `generated_at`, `runtime_seconds`, `memory_peak_mb/gb`, `paths.artifacts` — đúng các trường biến thiên. RAM đỉnh 348,6 MB và 347,1 MB (< 3,9 GB).

## Lỗi câu chữ trong meta (không ảnh hưởng dữ liệu)
`meta.json` ghi `"code_level": "soc[:7] (6 ký tự gốc)"` — **sai**: `soc[:7]` cho **7** ký tự (`11-1011`). Dữ liệu thì đúng (toàn bộ 7 ký tự, đồng nhất); chỉ câu mô tả sai và đã lan vào contract. Đề nghị sửa thành `soc[:7] (7 ký tự, dạng 11-1011)`.
