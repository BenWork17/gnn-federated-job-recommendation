# README_V3 — Hệ gợi ý việc làm GNN + Học liên bang (client = nhà tuyển dụng)

Hướng dẫn chạy **đầu–cuối** cho toàn bộ hệ thống: dựng đồ thị từ CareerBuilder + O*NET →
huấn luyện GNN + FL trong notebook → WebAPI + PostgreSQL → UI giám sát node.
Mọi con số trong tài liệu này đều đo thật trên máy này (Windows 11, Python 3.13.0,
15,36 GB RAM, ổ E:).

> Trạng thái: **đã chạy end-to-end thật, 5/5 bước PASS** (xem §6).
> Ba phần khớp nhau: `api/` và notebook đọc **cùng** `artifacts/v3/graph.npz`;
> UI gọi đúng base URL + đúng tên field trong hợp đồng API.

---

## 1. Kiến trúc

```
 DỮ LIỆU THÔ (E:\2026\DUT\IOT\Cuoiki\NewData)              O*NET 29.3 (zip 13,3 MB)
   jobs.tsv      1.092.096 dòng  3,2 GB                     Occupation Data   1.016 nghề
   apps.tsv      1.603.111 dòng                             Alternate Titles  56.560
   users.tsv       389.708 dòng                             Technology Skills 32.681
   user_history.tsv 1.753.901 dòng                          (KHÔNG dùng Skills.txt)
            │                                                        │
            └──────────────┬─────────────────────────────────────────┘
                           ▼
              ┌──────────────────────────────────────┐
              │  src/prepare_v3.py                   │  streaming csv.reader
              │  1. quét jobs.tsv   → employer+nghề  │  KHÔNG pandas (RAM 3,9 GB)
              │  2. nạp O*NET       → nghề-skill     │  seed=42
              │  3. quét apps.tsv   → user-job       │  RAM đỉnh 347 MB
              │  4. dựng client     → 1 employer = 1 client
              │  5. quét history.tsv→ user-nghề      │
              │  6. build_graph     → train/test     │
              └──────────────────┬───────────────────┘
                                 ▼
        artifacts/v3/            graph.npz        3,6 MB  (21 mảng)
                                 clients.json     1,1 MB  (9.116 client)
                                 job_titles.json 11,9 MB  (84.845 job)
                                 user_titles.json 10,3 MB (156.189 user)
                                 meta.json       10,7 KB  (mọi số đo + filter_steps)
             ┌───────────────────┴────────────────────┐
             ▼                                        ▼
 ┌───────────────────────────┐          ┌──────────────────────────────────┐
 │ notebooks/01_gnn_fl.ipynb │          │ api/  (FastAPI)                  │
 │ 10 yêu cầu đề bài         │          │  artifacts.py  đọc graph.npz     │
 │ LightGCN/GraphSAGE/GAT    │          │  db.py         PgStore/InMemory  │
 │ FedAvg/FedProx, ablation  │          │  fl_sim.py     runner FL nền     │
 │ → results/v3/*.json, *.png│          │  main.py       10 endpoint + 2 WS│
 └───────────────────────────┘          └───────────────┬──────────────────┘
                                    ┌───────────────────┴───────────────┐
                                    ▼                                   ▼
                        ┌──────────────────────┐          ┌────────────────────────┐
                        │ PostgreSQL 14+       │          │ ui/  (HTML/CSS/JS)     │
                        │ 9 bảng + 9 index     │          │ bảng client, 2 biểu đồ │
                        │ load_to_pg.py (COPY) │          │ lưới node, log WS      │
                        └──────────────────────┘          └────────────────────────┘
```

Luồng một request gợi ý:

```
POST /api/recommend {user_id, k}
   → db.py InMemoryStore.recommend   (CSR: user→skill ⋈ skill→job, + popularity, − đã ứng tuyển)
   → hoặc PgStore.recommend          (SQL: user_skills ⋈ job_skills, ORDER BY overlap)
   → {user_id, items:[{job_id, title, score, employer, matched_skills}]}
```

---

## 2. Yêu cầu môi trường

| Thành phần | Phiên bản đã kiểm chứng | Ghi chú |
|---|---|---|
| Python | **3.13.0** | bắt buộc ≥ 3.10 (cú pháp `X \| None`, `match`) |
| RAM | ≥ 4 GB trống | `prepare_v3.py` đỉnh **347 MB**; API in-memory cỡ thật **451 MB** |
| Ổ đĩa | ≥ 10 GB trống cho `artifacts/` + `results/` | dữ liệu thô nằm ngoài repo |
| numpy | 2.4.2 | bắt buộc cho mọi thành phần |
| torch | 2.10.0+cpu | chỉ notebook cần (GNN); API/UI **không** cần |
| FastAPI / uvicorn | 0.135.2 / 0.42.0 | `pip install -r api/requirements.txt` |
| psycopg | 3.3.8 (`psycopg[binary]`) | chỉ cần khi dùng PostgreSQL |
| websockets | 16.0 | `smoke_test.py` dùng để test 2 WebSocket |
| PostgreSQL | **13.23 đã test**, khuyến nghị **14+** | xem ghi chú `--dry-run` bên dưới |
| Playwright + Chrome | 1.58.0 | chỉ cần nếu muốn chạy lại `ui/devtools/check_real_backend.py` |

### Không cần PostgreSQL vẫn chạy đủ 10 endpoint

```powershell
python api/main.py --dry-run --port 8000     # in-memory, đọc artifacts/v3 thật
```

`--dry-run` bỏ hẳn tầng DB: `InMemoryStore` dựng CSR từ `graph.npz` trong RAM
(**26,7 s**, đỉnh **451 MB**), `/health` trả `db:false`. Mọi endpoint còn lại
(`/api/clients`, `/api/recommend`, `/api/train/*`, 2 WebSocket) chạy y hệt.
Kết quả `train_runs`/`round_metrics`/`node_latency` chỉ nằm trong RAM, mất khi tắt.

Ngoài ra nếu PostgreSQL **có cài nhưng chưa nạp dữ liệu**, API tự rơi về in-memory
và vẫn phục vụ được (`db.py:make_store`); response có `data_source` để biết nguồn.

---

## 3. Các bước chạy tuần tự (copy–paste được)

Thời gian là **đo thật** trên máy này. Chạy trong PowerShell tại `E:\2026\DUT\DSS\SauGK\CuoiKi`.

### Bước 0 — cài phụ thuộc (~40 s)

```powershell
python -m pip install -r api/requirements.txt
python -m pip install numpy                      # đã có sẵn nếu chạy notebook
```

### Bước 1 — dựng artifacts từ dữ liệu thô (~10,6 phút)

```powershell
python src/prepare_v3.py
```

Đo thật: **635,4 s**, RAM đỉnh **347 MB**. Kết quả ghi vào `artifacts/v3/`.
In ra 5 bước lọc với `pct_apps_remaining`:

```
· Job có trong jobs.tsv: 1.603.111 (100.00%)
· Job + có employer:      483.752 (30.18%)
· Ngưỡng >= 10 app: giữ 9.116 / 71.007 employer
· Cặp (user, job) thuộc client hợp lệ: 436.893 (27.25% tổng app)
· Nút: 264.995 = 171.807 user + 84.845 job + 583 nghề + 7.760 kỹ năng
· Cạnh: 764.364 = user-job 436.893 | job-occ 26.678 | occ-skill 25.866 | user-occ 274.927
```

Chạy lại **cho kết quả giống hệt** (đã đối chiếu từng mảng — xem §5).

### Bước 2 — chạy WebAPI

```powershell
# (a) không cần PostgreSQL — nhanh nhất để xem UI
python api/main.py --dry-run --port 8000
```
Nạp artifacts thật mất **~27 s** trước khi cổng 8000 mở; sau đó `/health` trả trong **56 ms**.

```powershell
# (b) có PostgreSQL: tạo DB, nạp bảng, nạp dữ liệu
createdb -U postgres dss_jobs
psql -U postgres -d dss_jobs -f api/schema.sql
python api/load_to_pg.py --dsn "postgresql://postgres:postgres@127.0.0.1:5432/dss_jobs" --truncate
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

`load_to_pg.py` nạp **đủ** artifacts thật trong **270,6 s**:
`users 171.807 | jobs 84.845 (có title 84.845) | apps 436.893 | job_skills 2.593.468 |
user_skills 18.017.133 | employers 9.116`.

Kiểm tra nhanh:

```powershell
python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
# {'status': 'ok', 'db': False/True, 'artifacts': True}
```

### Bước 3 — kiểm thử hợp đồng API (~40 s, 18/18 PASS)

```powershell
python api/smoke_test.py                                # mặc định http://127.0.0.1:8000
$env:API_BASE='http://127.0.0.1:8002'; python api/smoke_test.py   # nếu chạy cổng khác
```

### Bước 4 — mở UI giám sát (~0 s, không build step)

```powershell
Start-Process ui\index.html          # cách 1: mở trực tiếp file://
# cách 2 (khuyến nghị, tránh CORS lạ):
python -m http.server 8080 --directory ui
# rồi mở http://127.0.0.1:8080/index.html
```

Nếu API không ở cổng 8000: `http://127.0.0.1:8080/index.html?api=http://127.0.0.1:8002`
(`API_BASE` là hằng duy nhất ở đầu `ui/assets/app.js`, ghi đè được bằng `?api=`).

### Bước 5 — notebook (Kaggle/Colab hoặc local)

```powershell
python notebooks/verify_notebook.py        # 7/7 kiểm tra tĩnh, ~5 s
# mở notebooks/01_gnn_fl.ipynb rồi Run All; đặt SCALE='tiny' | 'small' | 'full'
```

Đo thật: `SCALE=tiny` **328 s**; `SCALE=small` **1.400 s ≈ 23,3 phút** (Kaggle giới hạn 90 phút).
Kết quả ghi vào `results/v3/` (`notebook_metrics.json`, `SUMMARY.md`,
`sweep_results.csv`, `ablation_results.csv`, `figures/F01…F06.png`).

### Bước 6 — dọn dẹp (tuỳ chọn)

```powershell
# xoá bằng chứng chạy lại prepare_v3 (26,9 MB) sau khi đã kiểm tra determinism
Remove-Item -Recurse -Force artifacts\v3_rerun     # chỉ sau khi đã chạy tools/check_determinism_v3.py

# cluster PostgreSQL nháp dùng để kiểm thử (nếu bạn có tạo theo §6)
& "<thư mục cài PostgreSQL>\bin\pg_ctl.exe" -D _tmp\pgtest stop -m fast
Remove-Item -Recurse -Force _tmp\pgtest            # giải phóng ~4,2 GB
```

> Trạng thái sau khi t6 hoàn tất: đã dừng và xoá cluster nháp; ổ E: còn
> **24,97 GB** trống (> 5 GB yêu cầu). Không có file tạm nào > 100 MB trong
> `_newdata_audit/` (file lớn nhất là `db_29_3_text.zip` 12,7 MB — là input
> O*NET cần giữ). Trong toàn repo cũng không còn file > 100 MB.

---

## 4. Bảng 10 yêu cầu đề bài → nơi đáp ứng → số đo

| # | Yêu cầu | File / dòng đáp ứng | Số đo chứng minh |
|---|---|---|---|
| 1 | Mục tiêu + GraphSafe + 3 GNN | `notebooks/01_gnn_fl_source.py:1–330` (cell 0 và [1]); `src/prepare_v3.py:972` (`build_graph`) | 4 điều kiện GraphSafe; LightGCN/GraphSAGE/GAT huấn luyện thật (81,7 s / 44,9 s / 37,1 s) |
| 2 | Bộ dữ liệu MEDAJob (case study) + CareerBuilder (chính) | `notebooks/01_gnn_fl_source.py:333` ([2b]); `src/prepare_v3.py:562` (`scan_jobs`), `:669` (`scan_apps`) | 1.603.111 app · 1.092.096 job · 389.708 user · 1.753.901 history; 335.755 job có employer (30,74%) |
| 3 | EDA + tiền xử lý | `notebooks/01_gnn_fl_source.py:478` ([3b] EDA); `src/prepare_v3.py:317` (`clean_employer_name`), `:378` (`employer_from_text`) | app/user median 1 · app/job median 2 · thưa **99,99726 %** · job có nghề **31,44 %** · client median **23** app |
| 4 | Kiến trúc GNN + FL, cross-silo hợp lệ | `notebooks/01_gnn_fl_source.py:662` ([4b] thư viện), `:1079` ([4d] vòng FL); client gán theo `client_of_job` | **16,29 %** cạnh test có `client_of_user == client_of_job` → phải gán theo `client_of_job`; **0** client rỗng; 45,71 % cạnh train cùng client |
| 5 | Sweep dim / layers / n_clients / local_epochs | `notebooks/01_gnn_fl_source.py` cell [5c]; `results/v3/sweep_results.csv` | **8 cấu hình**; R@20: dim 16→64 = 0,0198→0,0265; n_clients 5→10→20 = 0,0127→0,0221→0,0353; local_epochs 1 vs 5 = 0,0221 vs 0,0187 |
| 6 | Môi trường, cài đặt, mount Drive, upload | `notebooks/01_gnn_fl.ipynb` cell 0 (bootstrap tự dò `ART`); `notebooks/verify_notebook.py` | không hard-code `E:\`; `SCALE ∈ {tiny,small,full}`; không `torch_geometric`; 5 bước upload Kaggle; chạy offline |
| 7 | Recall@10/20, NDCG@20, MRR@20, coverage, CI 95 %, baseline | `notebooks/01_gnn_fl_source.py:1245` ([5b] metric), `:1836` ([7d] bảng 3 tập) | Xem §7.1: 6 hệ + FedAvg, kèm CI 95 %; 3 tập test (37.957 đầy đủ / 37.077 sạch / bỏ 1.969 cold-start) |
| 8 | Ablation (a)–(e) + bổ sung | `notebooks/01_gnn_fl_source.py:2162` ([8b]), `:2277` ([8c] nhóm f) | **15 biến thể** trên vũ trụ cố định 4.511 job: bỏ skill −5,0 %, bỏ nghề −18,6 %, FedProx −4,3 %, unweighted −2,4 % |
| 9 | WebAPI + PostgreSQL | `api/schema.sql` (9 bảng + 9 index), `api/main.py:107–300` (10 endpoint + 2 WS), `api/load_to_pg.py` | PG mode **18/18 PASS** (db:true); in-memory **18/18 PASS**; nạp thật 270,6 s; 436.893 app |
| 10 | UI giám sát node + độ trễ p50/p95 | `ui/index.html:80–135` (lưới node + 2 canvas), `ui/assets/app.js:604` (`buildNodeGrid`), `:920` (WebSocket) | 10/10 node báo cáo; 2 biểu đồ realtime qua WS (không polling); p50 1–2 ms, p95 4–23 ms; log đúng dạng `round X client Y latency Z ms`; **0 lỗi console** |

---

## 5. Tái lập (deterministic)

### 5.1 Seed và tham số

| Nơi | Seed / tham số | Ý nghĩa |
|---|---|---|
| `src/prepare_v3.py` | `--seed 42` | chia train/test theo user (`np.random.default_rng(42)`) |
| `src/prepare_v3.py` | `--min-apps 10`, `--min-jobs-per-employer 2` | ngưỡng tạo client |
| `src/prepare_v3.py` | `TEST_RATIO 0.2`, `MIN_APPS_FOR_TEST 5` | chỉ user ≥5 app mới có cạnh test |
| notebook | `seed=42` (`config/seed`) | khởi tạo trọng số GNN + chia shard FL |
| notebook | `dim=32, layers=2, n_clients=50, rounds=6, local_epochs=1, lr=0.05` | cấu hình chính |
| `api/fl_sim.py` | `cfg.seed=7` + `crc32(run_id)` | seed của runner mô phỏng |
| `api/artifacts.py` | `build_demo_dataset(seed=42)` | dữ liệu demo (khi thiếu artifacts) |

### 5.2 Kiểm tra determinism của `prepare_v3.py`

Có script sẵn — chạy lại toàn bộ vào thư mục khác rồi so sánh:

```powershell
python src/prepare_v3.py --out-dir artifacts/v3_rerun    # ~10,6 phút
python tools/check_determinism_v3.py                     # exit 0 = tất định
```

Kết quả thật:

```
OK   graph.npz: 21/21 mảng giống hệt
OK   clients.json       44c0ba0dd07bb6df / 44c0ba0dd07bb6df
OK   job_titles.json    efb89bba4345f7cf / efb89bba4345f7cf
OK   user_titles.json   661a49821b41bfbf / 661a49821b41bfbf
OK   meta.json (bỏ generated_at, runtime_seconds, memory_peak_mb, memory_peak_gb, artifacts)

KẾT LUẬN: TẤT ĐỊNH (giống hệt)
```

Script chỉ bỏ qua các trường **thay đổi theo lần chạy**: `generated_at`,
`runtime_seconds`, `memory_peak_mb/gb`, `artifacts` (kích thước file) và
`paths.artifacts` (chính là `--out-dir`). Mọi thứ còn lại — gồm `filter_steps`,
`employer_extraction`, `edges`, `clients.size_stats` — phải trùng khít.

Lần chạy 1: 821,6 s / đỉnh 341,3 MB. Lần chạy 2: 635,4 s / đỉnh 346,8 MB.
Thời gian và bộ nhớ khác nhau, **dữ liệu ra giống hệt**.

> `artifacts/v3_rerun/` (26,9 MB) là bằng chứng cho lần đối chiếu này; có thể xoá
> sau khi chạy xong `tools/check_determinism_v3.py`.

### 5.3 Kiểm tra hợp đồng API

```powershell
python api/smoke_test.py     # 18/18 PASS, gồm cả 2 WebSocket và 7 check stop
```

`smoke_test.py` assert `set(fields)` **bằng đúng** hợp đồng của từng endpoint, nên
đổi tên field là fail ngay.

### 5.4 Kiểm tra UI (Playwright)

```powershell
python ui/devtools/check_real_backend.py     # cần API đang chạy ở cổng 8000
```

Kết quả lưu ở `ui/devtools/last_real_backend.json`, ảnh ở `ui/screenshots/backend-real-0*.png`.

---

## 6. Kết quả chạy end-to-end thật (bằng chứng)

| Bước | Lệnh | Kết quả | Thời gian |
|---|---|---|---|
| a | `python src/prepare_v3.py` | **PASS** — sinh đủ 5 file trong `artifacts/v3/` | 635,4 s |
| b | `python api/main.py --dry-run --port 8000` → `GET /health`, `GET /api/clients` | **PASS** — `{'status':'ok','db':False,'artifacts':True}`; `total=9116`, item0 = `randstad n_apps=4745` | 56 ms / 2 ms |
| c | `POST /api/recommend {user_id: 1133690, k: 5}` | **PASS** — 5 item kèm score, vd `job_id=381995 "Accounts Receivable Clerk" score=11.114488`, `matched_skills` 10 phần tử | 10 ms |
| d | `POST /api/train/start {n_clients:10, rounds:12}` rồi `GET /api/train/status` | **PASS** — recall20 0,3785→0,6162 qua 12 vòng, p50 1–2 ms, p95 4–23 ms, `participants` 10 client | 12 vòng ≈ 7 s |
| e | `python ui/devtools/check_real_backend.py` | **PASS** — 1 biểu đồ Recall@20 (12 điểm) + 1 biểu đồ p50/p95 + lưới **10/10** node, 0 lỗi console | 45 s |
| — | `python api/smoke_test.py` (in-memory) | **PASS 18/18** | 40 s |
| — | `POST /api/train/start` ở chế độ **PostgreSQL thật** + `load_to_pg.py` | **PASS 18/18**, `db:true`, 171.807 user / 84.845 job / 436.893 app / 2.593.468 job_skill / 18.017.133 user_skill | nạp 270,6 s |
| — | `python notebooks/verify_notebook.py` | **PASS 7/7** | 5 s |

Chi tiết output thật:

```
PASS GET /health :: 200 {'status': 'ok', 'db': False, 'artifacts': True} (56ms)
PASS GET /api/clients :: 200 total=9116 n_items=5
     item0={"client_id": 0, "name": "randstad", "n_apps": 4745, "n_users": 4215, "n_jobs": 603, "status": "active"}
PASS GET /api/graph/summary :: 200 {"n_users": 171807, "n_jobs": 84845, "n_skills": 7760,
     "n_occupations": 583, "n_edges_user_job": 436893, "n_edges_job_skill": 2593468,
     "n_edges_user_skill": 18017133, "n_clients": 9116, "sparsity_pct": 99.872967}
PASS POST /api/recommend :: 200 user_id=1133690 n_items=5
     item0={"job_id": 381995, "title": "Accounts Receivable Clerk", "score": 11.114488,
            "employer": "nationalfoodgroup.com", "matched_skills": [...]}
PASS WS /ws/latency :: n_ticks=5 {"type":"tick","round":1,"client_id":0,"latency_ms":1.4038,...}
PASS WS /ws/train/{run_id} :: n_msgs=3 {"type":"round","round":1,
     "metrics":{"recall20":0.514499,"ndcg20":0.401309,"mrr20":0.282974,"loss":1.020653}}
=== SUMMARY === 18/18 checks passed
```

---

## 7. Kết quả nghiên cứu (số thật, `SCALE=small`, seed 42)

### 7.1 So sánh 7 hệ — hai vũ trụ đánh giá

Vũ trụ **đầy đủ** (82.876 job có trong train) vs vũ trụ **FL** (9.058 job mà mọi
mô hình đều thấy được — so sánh công bằng):

| Mô hình | R@10 | **R@20** | NDCG@20 | MRR@20 | coverage@10 | R@20 (vũ trụ FL) | giây |
|---|---|---|---|---|---|---|---|
| Popularity | 0,0098 | 0,0154 | 0,0058 | 0,0037 | 0,000024 | 0,0542 | 1,5 |
| Item-KNN | 0,4265 | **0,5408** | 0,3147 | 0,2850 | 0,008748 | 0,4897 | 4,1 |
| BPR-MF | 0,0162 | 0,0222 | 0,0118 | 0,0113 | 0,007385 | 0,0850 | 6,6 |
| LightGCN | 0,3152 | 0,4002 | 0,2351 | 0,2173 | 0,004573 | **0,7151** | 81,7 |
| GraphSAGE | 0,0815 | 0,1376 | 0,0633 | 0,0525 | 0,004332 | 0,5113 | 44,9 |
| GAT | 0,1040 | 0,1414 | 0,0835 | 0,0828 | 0,003934 | 0,3739 | 37,1 |
| FedAvg (FL) | 0,0402 | 0,0475 | 0,0365 | 0,0471 | 0,005164 | 0,3905 | 129,6 |

**Đọc bảng này cho đúng:** trên vũ trụ đầy đủ, Item-KNN (0,5408) thắng vì nó
"nhớ" được cặp user–job phổ biến; LightGCN (0,4002) thua. Nhưng khi **cùng vũ trụ**
(chỉ job mà mọi hệ đều xếp hạng được), LightGCN **0,7151** vượt Item-KNN 0,4897.
Đây là so sánh công bằng; báo cả hai để không chọn cherry-pick.

### 7.2 Ablation (15 biến thể, vũ trụ cố định 4.511 job)

| Biến thể | Ghi chú | R@10 | R@20 | Δ vs base | NDCG@20 | MRR@20 |
|---|---|---|---|---|---|---|
| (base) đầy đủ | nghề + kỹ năng, FedAvg weighted | 0,4445 | **0,4833** | +0,0 % | 0,3469 | 0,3150 |
| (a) bỏ lớp skill | không đưa nút kỹ năng vào | 0,4076 | 0,4589 | **−5,0 %** | 0,3307 | 0,2990 |
| (b) bỏ lớp occupation | bỏ nút nghề (kéo theo cả kỹ năng) | 0,3332 | 0,3933 | **−18,6 %** | 0,2657 | 0,2343 |
| (c) n_clients = 5 | 5 client lớn nhất | 0,2300 | 0,2398 | −50,4 % | 0,1900 | 0,1799 |
| (c) n_clients = 10 | 10 client lớn nhất | 0,3159 | 0,3512 | −27,3 % | 0,2546 | 0,2320 |
| (c) n_clients = 20 | 20 client lớn nhất | 0,4445 | 0,4833 | +0,0 % | 0,3469 | 0,3150 |
| (d) FedAvg | trung bình có trọng số | 0,4445 | 0,4833 | +0,0 % | 0,3469 | 0,3150 |
| (d) FedProx (μ=0,01) | thêm phạt ‖E − E_global‖² | 0,4167 | 0,4627 | −4,3 % | 0,3334 | 0,3026 |
| (e) local_epochs = 1 | 1 epoch cục bộ/vòng | 0,4445 | 0,4833 | +0,0 % | 0,3469 | 0,3150 |
| (e) local_epochs = 5 | 5 epoch cục bộ/vòng | 0,3943 | 0,4565 | −5,5 % | 0,3055 | 0,2703 |
| (g) FedAvg weighted | trọng số = số cạnh user–job | 0,4445 | 0,4833 | +0,0 % | 0,3469 | 0,3150 |
| (g) FedAvg unweighted | mọi client trọng số 1 | 0,4385 | 0,4716 | −2,4 % | 0,3369 | 0,3040 |
| (f1) base, catalog 956 job | chỉ job có nghề | 0,5121 | 0,5756 | +19,1 % | 0,4303 | 0,3910 |
| (f2) bỏ skill, catalog 956 | chỉ job có nghề | 0,4770 | 0,5270 | +9,0 % | 0,3982 | 0,3635 |
| (f3) bỏ nghề+skill, 956 | chỉ job có nghề | 0,4517 | 0,5066 | +4,8 % | 0,3753 | 0,3390 |

**Kết luận ablation:** lớp **nghề** đóng góp nhiều nhất (−18,6 % khi bỏ), lớn hơn
hẳn lớp **kỹ năng** (−5,0 %). Nhiều client hơn thì tốt hơn (đến 20). FedProx
**kém** FedAvg ở đây vì dữ liệu không dịch chuyển mạnh về phân phối; trung bình
có trọng số tốt hơn không trọng số 2,4 %.

### 7.3 Độ trễ đo thật (300 mẫu, `perf_counter`)

| p50 | p95 | mean | max | min | p95/p50 |
|---|---|---|---|---|---|
| 418,0 ms | 566,6 ms | 430,9 ms | 861,1 ms | 286,1 ms | 1,36 |

Đây là latency **một vòng cập nhật cục bộ** của client (numpy thật, CPU).
API `node_latency` đo riêng từng node mỗi vòng (p50 1–2 ms, p95 4–23 ms) — nhẹ hơn
vì chỉ tính phần "local update" mô phỏng, ghi rõ `simulated_metrics: true`.

---

## 8. Giới hạn đã biết (khai báo trung thực)

1. **Client KHÔNG phải nhãn gốc — là employer trích tự động từ text.**
   Chỉ **30,74 %** job (335.755/1.092.096) trích được employer; sau lọc chất lượng
   còn **26,72 %** (291.761). Sau ngưỡng ≥10 app còn **9.116 client**, phủ
   **27,25 %** application (436.893/1.603.111). Con số 43,50 % mà khảo sát ban đầu
   nêu là trước khi lọc chất lượng — chênh lệch nằm ở blacklist, hậu tố pháp lý và
   yêu cầu ≥2 job/employer, **không phải** do trích kém (xem `meta.json:filter_steps`).

2. **Skill phía user là SUY QUA NGHỀ, không phải tự khai.**
   `user_history.JobTitle` → mã nghề O*NET → tập kỹ năng của nghề đó. Chỉ
   **19,17 %** dòng user_history map được nghề (336.267/1.753.901). Đồ thị **không**
   lưu cạnh user–skill trực tiếp; user chạm skill qua 2 bước nhảy user→nghề→skill.
   Vì vậy `user_skills` trong PostgreSQL (18.017.133 dòng) là **suy diễn**, không
   phải dữ liệu gốc.

3. **69,7 % job không map được nghề O*NET.** Chỉ **31,44 %** job (26.678/84.845)
   có cạnh job–nghề. Nguyên nhân: title CareerBuilder không khớp O*NET. Các job
   này **vẫn là nút hợp lệ** và giữ nguyên cạnh user–job; chúng chỉ thiếu đường
   lan skill. Nếu ép mọi job phải có nghề thì mất 2/3 tương tác và app phủ tụt
   27 % → 9 % (đã cân nhắc và từ chối — xem `meta.json:job_metadata.note`).

4. **Rò rỉ gián tiếp 2,32 %.** 880/37.957 cạnh test có user và job cùng nối một
   nút nghề qua cạnh **train** → R@20 bị phồng nhẹ. Đã báo metric trên tập con
   **không có đường vòng** (`clean_recall20` trong mọi bảng). Notebook còn báo
   thêm tập bỏ 1.969 job cold-start (`n_jobs_cold_start`).

5. **Test-only job 2,32 %.** 1.969/84.845 job chỉ có cạnh test, 0 cạnh train
   (do split theo user) → là cold-start item khi tính R@20.

6. **Client cực lệch.** max 4.745 app vs min 10 app (**474×**); top-1 chiếm 1,09 %
   tổng app. FedAvg vì thế bị client lớn chi phối — đã tách nhóm client trong [7f].

7. **Cross-silo là hợp lệ, không phải rò rỉ.** 44,58 % user (76.584) ứng tuyển ở
   ≥2 employer, trung bình 2,41 client/user. Mỗi client chỉ sở hữu quan sát
   "user X ứng tuyển vào job **của tôi**" — đó là định nghĩa silo tự nhiên của FL,
   không phải rò rỉ nhãn.

8. **Số client thật là 9.116, KHÔNG phải ~14.740.** Con số 14.740 đo trên bộ
   employer kiểu probe cũ (chưa lọc blacklist/hậu tố, còn rác kiểu "if you").
   Bộ lọc chất lượng là nguyên nhân chênh, đã ghi trong `meta.json`.

9. **Metric trong API là MÔ PHỎNG.** `fl_sim.py` chạy local update numpy **thật**
   và đo latency bằng `perf_counter` **thật**, nhưng `recall20/ndcg20/mrr20/loss`
   là đường cong giảm dần theo vòng. Mọi response có `simulated_metrics: true`
   và `data_source` để không ai nhầm với kết quả huấn luyện GNN thật (số thật
   nằm ở §7 và `results/v3/`).

10. **License CareerBuilder cấm phát tán dữ liệu thô.** Repo **không** chứa
    `jobs.tsv`/`apps.tsv`/`users.tsv`/`user_history.tsv`. Chỉ chứa **dẫn xuất**
    (graph.npz, clients.json, thống kê). Người nhận repo phải tự có dữ liệu gốc
    theo license của mình rồi chạy `src/prepare_v3.py`. `job_titles.json`/
    `user_titles.json` chứa text trích từ tin tuyển dụng — cũng là dữ liệu dẫn
    xuất, **không** phát tán ra ngoài phạm vi học thuật.

11. **`occ_ids` trong graph.npz là DANH SÁCH MÃ NGHỀ, không phải mảng theo job.**
    583 phần tử chuỗi `soc[:7]` (vd `"11-1011"`), đánh chỉ số cho nút nghề. Ai
    đọc nhầm thành `occ_ids[job]` sẽ lỗi. `api/artifacts.py` dựng `occ_ids` theo
    job từ cạnh `edge_type == 1`.

12. **`/api/graph/summary` ở chế độ PostgreSQL mất ~20 s lần đầu** (9 phép
    `count(*)` trên `user_skills` 18 M dòng). Đã cache TTL 300 s + đun nóng ở
    startup nên các lần sau còn **2–25 ms**. `POST /api/recommend` ở PG mất
    **1,7 s** (một user có ~190 skill × 2,6 M cạnh job_skill); in-memory chỉ **10–20 ms**.

13. **PostgreSQL chết giữa chừng KHÔNG làm API trả 500.** Đã gặp thật và đã sửa:
    dừng cluster trong lúc server đang chạy từng làm `/api/clients` trả **500**
    (`psycopg.OperationalError`), khiến UI tưởng mất backend. Nay `PgStore` tự
    *degrade* một lần sang in-memory (đọc artifacts thật), `/health` báo
    `db:false` trung thực, và run đang chạy vẫn kết thúc `done` với đủ metric —
    đã kiểm chứng: DB chết → `GET /api/clients` 200 (9.116 client thật),
    `POST /api/train/start` + status = `done`, 4/4 vòng, metrics đủ.

---

## 9. Cấu trúc thư mục

```
Cuoiki/
├── README_V3.md              ← tài liệu này (hướng dẫn chạy cuối)
├── README.md                 báo cáo cũ (pipeline medajob trước đây)
├── src/prepare_v3.py         dựng đồ thị + chia client (1.583 dòng)
├── artifacts/v3/             graph.npz, clients.json, meta.json, *_titles.json
├── api/
│   ├── schema.sql            9 bảng + 9 index
│   ├── load_to_pg.py         COPY artifacts → PostgreSQL (270,6 s)
│   ├── main.py               10 endpoint + 2 WebSocket + CORS
│   ├── db.py                 PgStore / InMemoryStore (CSR) cùng interface
│   ├── artifacts.py          đọc graph.npz (edge_type), suy 2 lớp skill, fallback demo
│   ├── fl_sim.py             runner FL nền, latency thật, metric mô phỏng
│   ├── smoke_test.py         18 check hợp đồng
│   └── README.md             hợp đồng API chi tiết
├── ui/
│   ├── index.html            1 màn hình: topbar, lưới node, 2 biểu đồ, bảng client, log
│   ├── assets/app.js         API_BASE + WS + Chart.js
│   ├── assets/app.css        font self-host, chạy offline
│   ├── vendor/               chart.umd.min.js + 6 woff2
│   ├── devtools/             mock backend + 6 script Playwright
│   └── screenshots/          16 ảnh
├── notebooks/
│   ├── 01_gnn_fl.ipynb       44 cell (25 code), 10 yêu cầu
│   ├── 01_gnn_fl_source.py   bản percent-format để review
│   └── verify_notebook.py    7 kiểm tra tĩnh
├── results/v3/               notebook_metrics.json, SUMMARY.md, sweep/ablation CSV, 6 hình
└── docs/                     khảo sát, quyết định dữ liệu, báo cáo
```

---

## 10. Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Connection refused` ở cổng 8000 ngay sau khi start | API đang nạp `graph.npz` (~27 s in-memory) | chờ ~30 s rồi thử lại; xem log |
| UI hiện dải vàng "DEMO" | API chưa chạy hoặc cổng khác | chạy `python api/main.py --dry-run --port 8000`, hoặc mở `index.html?api=http://127.0.0.1:<port>` |
| `/health` trả `artifacts:false` | chưa chạy `prepare_v3.py` | chạy bước 1; API sẽ phục vụ dữ liệu demo |
| `/health` đang `db:true` tự chuyển `db:false` | PostgreSQL vừa chết | API tự chuyển in-memory (đọc artifacts thật) và ghi log `[db] PostgreSQL không dùng được (...) -> chuyển sang in-memory (artifacts)`. Khởi động lại DB rồi **restart API** để dùng lại PG |
| `UnicodeEncodeError: 'charmap'` | console Windows cp1252 | `$env:PYTHONIOENCODING='utf-8'` (mọi script đã tự `reconfigure` stdout) |
| `psycopg.OperationalError: password authentication failed` | mật khẩu `postgres` khác mặc định | `$env:DSS_PG_DSN='postgresql://<user>:<pw>@127.0.0.1:5432/dss_jobs'` |
| `load_to_pg.py` báo thiếu artifacts | chưa có `artifacts/v3/graph.npz` | chạy bước 1 trước |
| UI Việt hoá lỗi font | thiếu woff2 trong `ui/vendor/` | kiểm tra 6 file `.woff2` còn đủ |

---

## 11. Tài liệu liên quan

- `api/README.md` — hợp đồng 10 endpoint chi tiết, ví dụ curl, chạy test
- `ui/README.md` — 6 màn hình bắt buộc, cách kiểm thử, bảng ảnh
- `results/v3/SUMMARY.md` — tóm tắt kết quả notebook
- `docs/QUYET_DINH_BO_DU_LIEU.md` — vì sao chọn/lọc dữ liệu như vậy
- `docs/SO_LIEU_CHINH.md` — bảng số liệu chính
- `artifacts/v3/meta.json` — **mọi** thống kê + `filter_steps` + ghi chú từng quyết định
