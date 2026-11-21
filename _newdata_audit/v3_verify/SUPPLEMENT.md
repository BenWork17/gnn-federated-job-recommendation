# t5 — Hai phép đo bổ sung (theo yêu cầu captain)

Nguồn: `artifacts/v3/graph.npz` (chỉ đọc). Script: [`t5_supplement.py`](t5_supplement.py).
Số đo máy đọc: [`t5_supplement.json`](t5_supplement.json). Mask cho t4: [`test_clean_index.npz`](test_clean_index.npz).

## 1. Mức phồng do rò rỉ đường vòng + tập test "sạch"

| Hạng mục | Kỳ vọng captain | Đo được | KQ |
|---|---|---|---|
| Số cạnh test sạch (bỏ đường vòng u–occ–j) | 37.077 | **37.077** | PASS |
| Số cạnh test bị loại | 880 | **880** (2,32%) | PASS |
| Tỉ lệ test sạch / tổng cạnh test | — | **97,68%** | — |
| Số user còn lại trong test sạch | — | **19.719 / 20.067** (−348 user mất hết cạnh test) | — |
| Số job còn lại trong test sạch | — | **19.757 / 20.100** (−343 job) | — |

Tỉ lệ test sau khi làm sạch:
- trên **toàn bộ** cạnh user-job (436.893): **8,487%** (trước 8,688%)
- trên tập **đủ điều kiện** (user ≥5 app, 194.172 cạnh): **19,095%** (trước 19,548%)

→ Mức phồng tiềm năng của R@20 do đường vòng = **2,32% số cạnh test**, tương đương 880 ca; **348 user** sẽ không còn cạnh test nào sau khi làm sạch (phải loại khỏi mẫu đánh giá, không được tính là miss).

### File cho t4: `test_clean_index.npz`
| Array | Kiểu | Ý nghĩa |
|---|---|---|
| `is_clean` | bool[37957] | True = cạnh test không có đường vòng u–occ–j → **dùng làm mask đánh giá** |
| `detour_flag` | bool[37957] | đảo của `is_clean`, đọc trực tiếp nếu cần |
| `edge_pos` | int64[37957] | vị trí cột trong `edge_index` (đã kiểm: bằng `np.where(test_mask & edge_type==0)[0]`) |
| `user` | int64[37957] | chỉ số nút user (0..171806) |
| `job` | int64[37957] | chỉ số job trong khối job (0..84844); cộng 171807 để ra node index |

Thứ tự phần tử = đúng thứ tự cạnh test xuất hiện trong `edge_index`. Đã kiểm chéo: `edge_pos`, `user`, `job`, `detour_flag` tái tạo khớp 100% khi tính lại độc lập từ `graph.npz`.

## 2. Client theo đúng nghĩa silo — FL có chạy nổi 9.116 client?

| Hạng mục | Kỳ vọng | Đo được | KQ |
|---|---|---|---|
| Client có ≥1 job | 9.116/9.116 | **9.116** (0 client 0 job) | PASS |
| Client có ≥1 user | 9.116/9.116 | **9.116** (0 client 0 user) | PASS |
| Client có ≥1 cạnh train user-job | 9.116/9.116 | **9.116** (0 client rỗng khi train) | PASS |
| Client có ≥10 cạnh train | — | 8.745 (95,9%) | — |
| Client <2 cạnh train | 0 | **0** | PASS |
| Đối chiếu clients.json | khớp | n_jobs 0 mismatch, n_users 0 mismatch | PASS |

Phân bố mỗi client:

| Chỉ số | min | p25 | median | p75 | max | mean |
|---|---|---|---|---|---|---|
| n_jobs | 1 | 2 | 4 | 9 | 603 | 9,31 |
| n_users | 5 | 14 | 23 | 45 | 4.215 | 45,51 |
| cạnh train | 5 | 13 | 22 | 42 | 4.320 | — |

**Kết luận FL**: chạy được với cả 9.116 client — không client nào rỗng, client nhỏ nhất vẫn có 5 user / ≥1 job / 5 cạnh train. Nhưng phân bố rất lệch: **418 client chỉ có 1 job**, 3.877 client có ≤3 job, 109 client có <10 user. Với FedAvg, các client này góp gradient rất mỏng — nên báo thêm R@20 theo nhóm quy mô (≥10 job vs <10 job) thay vì chỉ trung bình toàn cục.

Test coverage: **2.040 client (22,4%) không có cạnh test nào**, và **2.096 client (23,0%)** không còn cạnh test sau khi làm sạch → metric per-client chỉ tính trên ~77% client.

## Ghi chú
- Việc sửa câu chữ `soc[:7]` (7 ký tự) nằm ở `src/prepare_v3.py` / `meta.json` do graph-builder làm; tôi không đụng file của họ.
- Không chạy lại toàn bộ verify; hai phép đo này độc lập và đọc trực tiếp từ `graph.npz` + `clients.json`.
