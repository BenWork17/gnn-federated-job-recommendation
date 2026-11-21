# WebAPI backend — GNN + Federated Learning job recommender

Backend FastAPI + PostgreSQL cho hệ gợi ý việc làm. Chia client theo **nhà tuyển dụng**
(employer = FL client), ghi metric từng vòng và **đo latency thật** cho từng node.

```
api/
├── schema.sql        DDL PostgreSQL 14+ (9 bảng + 9 index, có cột stop của t7)
├── load_to_pg.py     nạp artifacts/v3 vào PG bằng COPY (dùng chung loader với API)
├── main.py           FastAPI app + 11 endpoint (10 cũ + stop) + CORS
├── db.py             PgStore / InMemoryStore (cùng interface, CSR cho in-memory)
├── artifacts.py      đọc artifacts/v3 (theo edge_type, suy 2 lớp skill), fallback demo
├── fl_sim.py         runner FL chạy nền, đo latency bằng perf_counter, stop giữa chừng
├── smoke_test.py     test 18 mục: 9 REST + 2 WebSocket + 404 + 7 check stop
└── requirements.txt
```

`artifacts.py` là **một nguồn sự thật** về cách hiểu `graph.npz` (dùng chung cho
`main.py`, `db.py` và `load_to_pg.py`). Nó đọc `edge_type` để tách đúng 4 loại cạnh
rồi suy `job→skill` và `user→skill` qua lớp nghề — vì `graph.npz` không lưu cạnh
skill trực tiếp. Fallback demo chỉ kích hoạt khi thiếu file bắt buộc.

## 1. Cài đặt

```bash
pip install -r api/requirements.txt
```

## 2. Tạo database và nạp dữ liệu

```bash
# tạo DB
createdb -U postgres dss_jobs            # hoặc: psql -U postgres -c "CREATE DATABASE dss_jobs"

# tạo bảng (idempotent, chạy lại được)
psql -U postgres -d dss_jobs -f api/schema.sql

# nạp graph.npz + clients.json (cần src/prepare_v3.py đã chạy)
python api/load_to_pg.py --dsn "postgresql://postgres:postgres@127.0.0.1:5432/dss_jobs" \
                         --artifacts artifacts/v3 --batch-size 100000 --truncate
```

`load_to_pg.py` dùng `COPY ... FROM STDIN` (nhanh nhất), `--batch-size` mặc định 100.000.
Cờ `--truncate` xoá dữ liệu cũ trước khi nạp. DSN cũng đọc từ `DSS_PG_DSN`.

Script gọi thẳng `artifacts.load_artifacts()` (một nguồn sự thật với API), nên tách
đúng 4 loại cạnh theo `edge_type` và **suy 2 lớp skill qua nghề** (`job_skills` =
job→nghề→skill, `user_skills` = user→nghề→skill). Ngoài ra nạp luôn `title`,
`city`, `state`, `employer` từ `job_titles.json` (nếu có) — graph.npz không chứa
các cột này. Số đo thật với artifacts v3 đầy đủ: **270,6 s**, kết quả
`users 171.807 | jobs 84.845 (title 84.845) | apps 436.893 |
job_skills 2.593.468 | user_skills 18.017.133 | employers 9.116`.

> `sparsity_pct` của `/api/graph/summary` tính trên **user×job, job×skill,
> user×skill đã suy đủ** → 99,87 %. Đừng so với `meta.json:sparsity_pct`
> (0,002997) — con số đó chỉ tính trên lớp tương tác user–job gốc.

## 3. Chạy server

```bash
# có PostgreSQL
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# KHÔNG cần PostgreSQL (in-memory, dữ liệu demo) — để demo nhanh
python api/main.py --dry-run --port 8000
# hoặc: DSS_DRY_RUN=1 python -m uvicorn api.main:app --port 8000
```

Biến môi trường:

| Biến | Ý nghĩa |
|---|---|
| `DSS_PG_DSN` | DSN PostgreSQL (mặc định `postgresql://postgres:postgres@127.0.0.1:5432/dss_jobs`) |
| `DSS_DRY_RUN` | `1` = chỉ dùng in-memory, không kết nối DB |
| `DSS_ARTIFACT_DIR` | thư mục artifacts (mặc định `artifacts/v3`) |

Nếu PostgreSQL không kết nối được, server **vẫn chạy** bằng in-memory fallback và
`/health` trả `db:false`. Không cần DB vẫn demo được toàn bộ endpoint.

`--dry-run` đọc **artifacts/v3 thật** (không phải dữ liệu demo) khi thư mục này
tồn tại: dựng CSR mất **~27 s**, RAM đỉnh **451 MB**. Chỉ khi thiếu
`graph.npz`/`clients.json` mới rơi về bộ demo tiền định (seed 42: 300 user /
800 job / 120 skill / 15 nghề / 10 employer).

**Hiệu năng chế độ PostgreSQL (đo thật, dữ liệu đầy đủ):**

| Endpoint | Lần đầu | Các lần sau | Ghi chú |
|---|---|---|---|
| `GET /api/graph/summary` | ~20 s | **2–25 ms** | 9 phép `count(*)` trên 18 M dòng; cache TTL 300 s + đun nóng ở startup |
| `POST /api/recommend` | **1,7 s** | 1,7 s | 1 user × ~190 skill ⋈ 2,6 M cạnh `job_skills` |
| `GET /api/clients` | 6–8 ms | 6–8 ms | có index `n_apps DESC` |
| `GET /api/clients/{id}` | ~100 ms | ~100 ms | `top_skills` = GROUP BY trên `job_skills` |

Chế độ in-memory nhanh hơn nhiều: `recommend` **10–20 ms**, `summary` **2 ms**
(vì CSR đã dựng sẵn trong RAM).

## 4. Hợp đồng API (tên field giữ nguyên, ui-dev code theo)

> t7 **chỉ thêm mới**, không đổi tên/kiểu field nào của 10 endpoint cũ:
> thêm `POST /api/train/stop/{run_id}` và 2 field `stopped` / `stopped_at_round`
> trong `GET /api/train/status/{run_id}`.

### `GET /health`
```json
{"status": "ok", "db": true, "artifacts": true}
```

### `GET /api/clients?limit=50&offset=0&sort=n_apps&order=desc`
`limit` tối đa **2000** (UI tải 1000/lần). `sort` ∈ `n_apps|n_users|n_jobs|client_id|name`.
```json
{"total": 3,
 "items": [{"client_id": 0, "name": "Alpha Corp", "n_apps": 88,
            "n_users": 14, "n_jobs": 20, "status": "active"}]}
```

### `GET /api/clients/{client_id}`
```json
{"client_id": 0, "name": "Alpha Corp", "n_apps": 88, "n_users": 14, "n_jobs": 20,
 "top_skills": ["skill-12", "skill-15", "skill-20"], "status": "active"}
```
Sai id → `404 {"detail": "..."}`.

### `GET /api/graph/summary`
```json
{"n_users": 40, "n_jobs": 60, "n_skills": 25, "n_occupations": 4,
 "n_edges_user_job": 157, "n_edges_job_skill": 171, "n_edges_user_skill": 117,
 "n_clients": 3, "sparsity_pct": 90.918367}
```

### `POST /api/recommend`
Body `{"user_id": 1, "k": 20}` →
```json
{"user_id": 1,
 "items": [{"job_id": 500054, "title": "occD", "score": 0.5,
            "employer": "Gamma Inc", "matched_skills": ["skill-3", "skill-7"]}]}
```
`user_id` không tồn tại → `items: []`.

### `POST /api/train/start`
Body `{"n_clients": 50, "rounds": 10, "algorithm": "fedavg", "local_epochs": 1}`
(`algorithm` ∈ `fedavg|fedprox`) →
```json
{"run_id": "5ef1ed98-064e-4b06-bc50-f3f6a0a5e18b", "status": "running",
 "n_clients": 12, "rounds": 3, "algorithm": "fedavg",
 "data_source": "artifacts", "simulated_metrics": true,
 "participants": [0, 1, 2, 3, 4, 5, 6, 8268, 5453, 507], "note": "..."}
```
`participants` = danh sách `client_id` **THẬT** backend chọn cho lượt chạy
(field thêm mới, không đổi field cũ). UI nên vẽ lưới node theo danh sách này
thay vì tự đoán từ trang `/api/clients` — nếu đoán, số ô lệch số node thật báo
cáo (từng thấy "10/13" khi backend chọn 10 client khác trang đầu).
`GET /api/train/status/{run_id}` trả cùng danh sách.

`run_id` (UUID) dùng trực tiếp được trong `/api/train/status/{run_id}`, `/api/train/stop/{run_id}` và `/ws/train/{run_id}`.

### `POST /api/train/stop/{run_id}`  ← thêm mới (t7)
Dừng **run phía server** (nút Stop trên UI không chỉ ngắt theo dõi của client nữa).
```json
{"run_id": "f2c30d9e-9b79-471d-aa18-5c7d2ba0bfa5",
 "status": "stopped", "stopped_at_round": 2, "already_stopped": false}
```
- Runner check cờ dừng ở **đầu mỗi vòng**, nên vòng đang chạy vẫn hoàn tất →
  `round_metrics` không bị dở dang; `stopped_at_round` = vòng cuối đã xong.
- Run đã `done`/`failed`/`stopped` → `already_stopped: true`, `status` giữ nguyên.
- `run_id` không tồn tại → `404`.
- Cột `train_runs.status` cập nhật thành `'stopped'` (kèm `stopped_at_round`, `ended_at`).

### `GET /api/train/status/{run_id}`
```json
{"run_id": "5ef1...", "status": "done", "round": 3, "total_rounds": 3,
 "metrics": [{"round": 1, "recall20": 0.50818, "ndcg20": 0.39638,
              "mrr20": 0.279499, "loss": 1.015248}],
 "latency_p50_ms": 0.1518, "latency_p95_ms": 16.7746, "bytes_total": 1084454,
 "data_source": "artifacts", "simulated_metrics": true,
 "stopped": false, "stopped_at_round": 0}
```
`stopped` và `stopped_at_round` là **field thêm mới (t7)**; toàn bộ field cũ giữ
nguyên tên và kiểu. `status` ∈ `running | done | failed | stopped`.

### `GET /api/train/runs`
```json
{"items": [{"run_id": "5ef1...", "started_at": "2026-11-08T20:59:40",
            "n_clients": 12, "rounds": 3, "status": "done"}]}
```

### `WS /ws/latency`
Mỗi tick:
```json
{"type": "tick", "run_id": "5ef1...", "round": 1, "client_id": 0,
 "latency_ms": 27.5812, "bytes_up": 35948, "bytes_down": 94848,
 "ts": "2026-11-08T20:59:40"}
```

### `WS /ws/train/{run_id}`
Mỗi vòng:
```json
{"type": "round", "run_id": "5ef1...", "round": 1,
 "metrics": {"round": 1, "recall20": 0.50818, "ndcg20": 0.39638,
             "mrr20": 0.279499, "loss": 1.015248},
 "latency_ms": 0.0}
```

> Client gửi text lên WebSocket sẽ bị bỏ qua (giữ kết nối). CORS mở `*` cho mọi
> origin để UI chạy từ `file://` (origin `null`) hoặc cổng tĩnh khác vẫn gọi được.

## 5. Ví dụ gọi bằng curl

```bash
curl -s http://127.0.0.1:8000/health

curl -s "http://127.0.0.1:8000/api/clients?limit=1000&offset=0"

curl -s http://127.0.0.1:8000/api/clients/0

curl -s http://127.0.0.1:8000/api/graph/summary

curl -s -X POST http://127.0.0.1:8000/api/recommend \
     -H "Content-Type: application/json" -d '{"user_id": 1, "k": 10}'

curl -s -X POST http://127.0.0.1:8000/api/train/start \
     -H "Content-Type: application/json" \
     -d '{"n_clients": 50, "rounds": 10, "algorithm": "fedavg", "local_epochs": 1}'

curl -s http://127.0.0.1:8000/api/train/status/<RUN_ID>

# dừng run phía server (t7)
curl -s -X POST http://127.0.0.1:8000/api/train/stop/<RUN_ID>

curl -s http://127.0.0.1:8000/api/train/runs
```

> Trên máy này `curl`/`Invoke-WebRequest` hỏng. Dùng Python:
>
> ```bash
> python -c "import urllib.request,json;print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
> ```

WebSocket (Python):
```python
import websockets.sync.client as ws, json
with ws.connect("ws://127.0.0.1:8000/ws/latency") as s:
    print(json.loads(s.recv()))
```

## 6. Chạy test

```bash
# server phải đang chạy
python api/smoke_test.py                       # mặc định http://127.0.0.1:8000
API_BASE=http://127.0.0.1:8011 python api/smoke_test.py
```

`smoke_test.py` kiểm tra **đúng tên field** của mọi endpoint, gồm cả hai WebSocket.

## 7. Về mô phỏng huấn luyện (`fl_sim.py`)

- **Latency là số đo thật**: mỗi client chạy một "local update" numpy thật, thời gian
  đo bằng `time.perf_counter()`, ghi vào bảng `node_latency`.
- **Metric (recall20/ndcg20/mrr20/loss) là mô phỏng**, giảm dần theo vòng, KHÔNG phải
  kết quả huấn luyện GNN thật. Response có `simulated_metrics: true` để không nhầm.
- Khi `artifacts/v3/graph.npz` có sẵn: đọc `client_of_job` / `client_of_user` thật để
  chọn client (employer); khối lượng tính toán và bytes tỉ lệ với số node cục bộ.
- Chưa có artifacts: dùng bộ demo 300 user / 800 job / 10 employer, `data_source: "demo"`
  nằm ngay trong response để UI hiển thị nhãn "DEMO".

## 8. Ghi chú thiết kế

- `client_status`: `active` nếu `n_apps >= 10` (khớp ngưỡng chia client của prepare_v3),
  `warm` nếu `>= 5`, còn lại `idle`.
- `sparsity_pct` tính trên 3 mặt phẳng cạnh **đã suy đủ** (user–job, job–skill,
  user–skill): `100 * (1 - E / (U·J + J·S + U·S))`. Với artifacts v3 đầy đủ ra
  **99,872967 %**; con số `0,002997` trong `meta.json` chỉ tính lớp user–job gốc —
  đừng so trực tiếp hai số này.
- Skill của user suy **qua nghề** (user_history → occupation → skill), đúng như meta.json
  của prepare_v3; đây là suy diễn hợp lệ, không phải rò rỉ.
- Phân loại cạnh dựa trên **`edge_type`** của `graph.npz` (`0 user-job, 1 job-occ,
  2 occ-skill, 3 user-occ`). Nếu file không có `edge_type`, loader rơi về cách đoán
  theo khoảng chỉ số để tương thích ngược. **Bản cũ đoán thuần theo khoảng chỉ số**
  nên gộp nhầm `job-occ`/`occ-skill`/`user-occ` và cho `job-skill`/`user-skill` rỗng.
- `occ_ids` trong `graph.npz` là **danh sách mã nghề** (`soc[:7]`, 583 phần tử chuỗi)
  cho các **nút nghề**, KHÔNG phải mảng theo job. `Dataset.occ_ids` (chỉ số nghề theo
  job, `-1` nếu không có) được dựng lại từ cạnh `edge_type == 1`.

### Giới hạn dữ liệu cần biết

- `graph.npz` **không chứa** `title`, `city`, `state` của job. Loader đọc
  `job_titles.json` (do prepare_v3 xuất, 84.845/84.845 job) để điền `Dataset.titles`
  và `Dataset.employers`; nhờ đó `load_to_pg.py` nạp được title thật và API trả
  title đẹp thay vì `coalesce(title, occupation, 'Job #<id>')`. Thiếu file này thì
  vẫn chạy, chỉ là title rơi về occupation.
- `employer` suy từ `client_of_job` + `clients.json` (client chính là employer) — đúng mô hình.
- `skill_names`: `graph.npz` không bắt buộc có; API/loader lần lượt thử `npz["skill_names"]`
  → `meta.json["skill_names"]` → `skills.json` → `"skill-<i>"`. Artifacts v3 có sẵn 7.760 tên.

### Đo hiệu năng in-memory ở cỡ dữ liệu thật

Dựng `InMemoryStore` với 389.708 user / 500.000 job / 8.316 skill / 1,6M+1,09M+1,75M cạnh
(dạng CSR, không phải list-of-set):

| Thao tác | Thời gian | RSS |
|---|---|---|
| dựng store | 11,3 s | 229 MB |
| `POST /api/recommend` | 51 ms | 233 MB |
| `client_detail` (client giữ toàn bộ 500k job, lần đầu) | 1,03 s | 240 MB |
| `clients(limit=1000)` | 0,01 ms | 240 MB |

→ Nằm gọn trong 3,9 GB RAM. `client_detail` có cache nên lần gọi sau tức thì.

---

## 9. Phụ lục — output chạy thật (không phải ví dụ)

Lưu tại [`_smoke_pg.txt`](_smoke_pg.txt) và [`_smoke_dryrun.txt`](_smoke_dryrun.txt).

### 9.1 Chế độ PostgreSQL thật (PostgreSQL 13.23, cổng 55432)

```
PASS GET /health :: 200 {'status': 'ok', 'db': True, 'artifacts': True} (77ms)
PASS GET /api/clients :: 200 total=3 n_items=3 item0={"client_id": 0, "name": "Alpha Corp", "n_apps": 88, "n_users": 14, "n_jobs": 20, "status": "active"} (10ms)
PASS GET /api/clients/{client_id} :: 200 {"client_id": 0, "name": "Alpha Corp", "n_apps": 88, "status": "active"} top_skills=['skill-12', 'skill-15', 'skill-20', 'skill-1'] (12ms)
PASS GET /api/clients/{id} 404 :: 404 {'detail': 'client_id 99999999 không tồn tại'}
PASS GET /api/graph/summary :: 200 {"n_users": 40, "n_jobs": 60, "n_skills": 25, "n_occupations": 4, "n_edges_user_job": 157, "n_edges_job_skill": 171, "n_edges_user_skill": 117, "n_clients": 3, "sparsity_pct": 90.918367} (15ms)
PASS POST /api/recommend :: 200 user_id=9001 tried=[1, 2, 3, 100, 150, 9001] n_items=5 item0={"job_id": 500038, "title": "occB", "score": 1.154701, "employer": "Beta LLC", "matched_skills": ["skill-7", "skill-24"]} (7ms)
PASS POST /api/train/start :: 200 run_id=87ac5ee5-d68b-419d-8d23-280b455084c6 source=artifacts (31ms)
PASS GET /api/train/status/{run_id} :: 200 status=done round=3/3 p50=0.1619 p95=12.2425 bytes_total=1093793 n_metrics=3 (4ms)
PASS GET /api/train/runs :: 200 n_runs=9 first={"run_id": "87ac5ee5-d68b-419d-8d23-280b455084c6", "started_at": "2026-11-08T21:15:25", "n_clients": 12, "rounds": 3, "status": "done"} (32ms)
PASS WS /ws/latency :: n_ticks=5 first={"type": "tick", "run_id": "87ac5ee5-...", "round": 1, "client_id": 0, "latency_ms": 20.0727, "bytes_up": 34877, "bytes_down": 94084, "ts": "2026-11-08T21:15:25"}
PASS WS /ws/train/{run_id} :: n_msgs=3 first={"type": "round", "run_id": "87ac5ee5-...", "round": 1, "metrics": {"round": 1, "recall20": 0.516878, "ndcg20": 0.403165, "mrr20": 0.284283, "loss": 1.009662}, "latency_ms": 0.0}

=== SUMMARY ===
11/11 checks passed
```

Dữ liệu đã ghi thật vào PostgreSQL (kiểm tra bằng psql sau khi chạy):
```
 runs | metrics | latency_rows
------+---------+--------------
    9 |      26 |           99
```

### 9.2 Chế độ `--dry-run` (không có PostgreSQL)

```
PASS GET /health :: 200 {'status': 'ok', 'db': False, 'artifacts': False} (101ms)
PASS GET /api/clients :: 200 total=10 n_items=5 item0={"client_id": 0, "name": "Acme Analytics", "n_apps": 1082, "n_users": 296, "n_jobs": 356, "status": "active"} (5ms)
PASS GET /api/clients/{client_id} :: 200 {"client_id": 0, "name": "Acme Analytics", "n_apps": 1082, "status": "active"} top_skills=['tool-101', 'AutoCAD', 'tool-050', 'tool-082'] (15ms)
PASS POST /api/recommend :: 200 user_id=1 n_items=5 item0={"job_id": 100623, "title": "Registered Nurses (Acme Analytics)", "score": 1.52172, "employer": "Acme Analytics", "matched_skills": ["MATLAB", "Spark", "tool-082"]} (5ms)
PASS POST /api/train/start :: 200 run_id=3e1b470b-9bae-4c96-8200-d4d231d8896a source=demo (39ms)
PASS GET /api/train/status/{run_id} :: 200 status=done round=3/3 p50=2.1574 p95=20.405 bytes_total=3358120 n_metrics=3 (5ms)
PASS WS /ws/latency :: n_ticks=5 first={"type": "tick", ..., "latency_ms": 4.2539, "bytes_up": 24881, "bytes_down": 95004, ...}
PASS WS /ws/train/{run_id} :: n_msgs=3 first={"type": "round", "round": 1, "metrics": {"recall20": 0.518228, ...}, "latency_ms": 0.0}

=== SUMMARY ===
11/11 checks passed
```

Lưu ý: `/health` ở chế độ dry-run trả `db:false` — đúng ngữ nghĩa (không có PostgreSQL),
không phải lỗi. UI nên coi `artifacts:false` là nhãn "DEMO".

### 9.3 CORS (UI gọi từ `file://` hoặc cổng khác)

```
OPTIONS /api/clients (Origin: null) -> 200
  access-control-allow-origin: *
  access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
  access-control-allow-headers: content-type
GET /health (Origin: http://127.0.0.1:8080) -> 200, access-control-allow-origin: *
```

### 9.4 Kiểm tra khi train đang chạy (run 20 vòng)

```
MIDRUN status: running round 4 / 20 n_metrics 4
ticks collected 20 first {'type': 'tick', 'round': 2, 'client_id': 0, 'latency_ms': 8.9439, ...}
```
→ `status:"running"`, `round` tăng dần, metrics dài dần theo vòng; WebSocket bắn tick ngay.

### 9.5 t7 — STOP phía server (output smoke test MỚI: 18/18)

`smoke_test.py` nay có **18 check** (11 cũ + 7 mới cho stop). Chạy lại cả hai chế độ.

**PostgreSQL mode** (`db:true`, `artifacts:true`):
```
PASS GET /health :: 200 {'status': 'ok', 'db': True, 'artifacts': True} (89ms)
PASS GET /api/train/status/{run_id} :: 200 status=done round=3/3 n_metrics=3 stopped=False (3ms)
PASS status có trường 'stopped' (field cũ giữ nguyên) :: keys=['bytes_total', 'data_source', 'latency_p50_ms', 'latency_p95_ms', 'metrics', 'round', 'run_id', 'simulated_metrics', 'status', 'stopped', 'stopped_at_round', 'total_rounds']
PASS POST /api/train/stop/{run_id} :: 200 body={"run_id": "f2c30d9e-...", "status": "stopped", "stopped_at_round": 2, "already_stopped": false} reached_before_stop=2 stop_duration=607ms
PASS status sau stop: stopped + round < total_rounds :: 200 status=stopped stopped=True round=2/40 stopped_at_round=2 n_metrics=2
PASS stop lần 2 -> already_stopped=true :: 200 body={"run_id": "f2c30d9e-...", "status": "stopped", "stopped_at_round": 2, "already_stopped": true}
PASS stop run đã done -> already_stopped=true :: 200 body={"run_id": "5f338766-...", "status": "done", "stopped_at_round": 3, "already_stopped": true}
PASS stop run_id lạ -> 404 :: 404 {'detail': 'run_id 00000000-0000-0000-0000-000000000000 không tồn tại'}
PASS start/stop liên tục 5 lần không rò :: rows=[(200, 'stopped', 'stopped', 1), (200, 'stopped', 'stopped', 1), (200, 'stopped', 'stopped', 1), (200, 'stopped', 'stopped', 1), (200, 'stopped', 'stopped', 1)]

=== SUMMARY ===
18/18 checks passed
```

DB sau khi chạy (psql) — status `'stopped'` ghi đúng, `stopped_at_round` khớp số vòng thật:
```
                run_id                | status  | rounds | stopped_at_round | has_ended
--------------------------------------+---------+--------+------------------+-----------
 5f338766-7abf-40af-90eb-0b8fbef0df90 | done    |      3 |                  | t
 f2c30d9e-9b79-471d-aa18-5c7d2ba0bfa5 | stopped |     40 |                2 | t
 877aa792-160f-44e8-a6a0-f6efda560481 | stopped |     40 |                1 | t
 ...
```

**`--dry-run`** (không PostgreSQL): `18/18 checks passed`, cùng nội dung stop,
`POST /api/train/stop` trả `stopped_at_round=2` với `stop_duration=527ms`.

**WebSocket thông báo dừng** — kết nối `/ws/train/{run_id}` rồi stop, client nhận
ngay message cuối có `status:"stopped"` (để UI tắt spinner, không chờ vô hạn):
```
stop -> 200 {'run_id': '1dff1c70-...', 'status': 'stopped', 'stopped_at_round': 2, 'already_stopped': False}
WS messages: 3 | có message stop: True
{'type': 'round', 'run_id': '1dff1c70-...', 'round': 2, 'metrics': {...},
 'latency_ms': 0.0, 'status': 'stopped', 'stopped': True, 'stopped_at_round': 2}
final status: stopped stopped True round 2 / 30
```


**Không rò task** — test riêng 20 lần start/stop liên tiếp gọi thẳng `FLSimulator`:
```
20 lần start/stop — status: {'stopped'} | số lần: 20
task còn sống sau khi dừng: 0
_tasks dict còn giữ: 0 -> []
run tự nhiên: done round 2 / 2 stopped False
stop run lạ: None
task còn sống cuối cùng: 0 []
KET_LUAN: PASS
```

### 9.6 Chạy với artifacts v3 ĐẦY ĐỦ (số thật, t6)

Toàn bộ số ở §9.1/§9.2 là bộ nhỏ (40 user/60 job/3 employer) dùng để kiểm tra
hợp đồng. Dưới đây là **artifacts v3 thật** (171.807 user / 84.845 job / 9.116 client)
sau khi `api/artifacts.py` được sửa để đọc `edge_type` + suy 2 lớp skill.

**In-memory (`--dry-run`)** — dựng store 26,7 s, RSS đỉnh 451 MB:

```
PASS GET /health :: 200 {'status': 'ok', 'db': False, 'artifacts': True} (56ms)
PASS GET /api/clients :: 200 total=9116 n_items=5
     item0={"client_id": 0, "name": "randstad", "n_apps": 4745, "n_users": 4215, "n_jobs": 603, "status": "active"} (2ms)
PASS GET /api/clients/0 :: 200 {"client_id": 0, "name": "randstad", "n_apps": 4745, "status": "active"}
     top_skills=['Microsoft Excel', 'Microsoft Office software', 'Microsoft Word', 'Microsoft PowerPoint'] (10ms)
PASS GET /api/graph/summary :: 200 {"n_users": 171807, "n_jobs": 84845, "n_skills": 7760,
     "n_occupations": 583, "n_edges_user_job": 436893, "n_edges_job_skill": 2593468,
     "n_edges_user_skill": 18017133, "n_clients": 9116, "sparsity_pct": 99.872967} (19ms)
PASS POST /api/recommend :: 200 user_id=1133690 n_items=5 (10ms)
     item0={"job_id": 381995, "title": "Accounts Receivable Clerk", "score": 11.114488,
            "employer": "nationalfoodgroup.com", "matched_skills": [...10 skill...]}
PASS POST /api/train/start :: 200 run_id=a14186e4-... source=artifacts
     participants=[0,1,2,3,4,5,6,8268,5453,507] (53ms)
PASS WS /ws/latency :: n_ticks=5 first={"type":"tick","round":1,"client_id":0,"latency_ms":1.4038,...}
PASS WS /ws/train/{run_id} :: n_msgs=3 first={"type":"round","round":1,
     "metrics":{"recall20":0.514499,"ndcg20":0.401309,"mrr20":0.282974,"loss":1.020653}}

=== SUMMARY ===
18/18 checks passed
```

**PostgreSQL thật** (`load_to_pg.py` 270,6 s; `db:true`): `18/18 checks passed`,
`GET /api/clients total=9116`, summary giống hệt in-memory, `POST /api/recommend`
trả 5 item trong **1,7 s** (chậm hơn in-memory vì truy vấn SQL trên 2,6 M cạnh
`job_skills`; đã thêm `idx_job_skills_job` + `idx_user_skills_user` + ANALYZE để
tránh seq-scan).

> **Đã sửa trong t6 (2 lỗi chặn tích hợp):**
> 1. `artifacts.py` ép `z["occ_ids"]` sang `int64` nhưng file thật chứa mã nghề
>    dạng chuỗi (`"11-1011"`) → `ValueError` → API **âm thầm rơi về dữ liệu demo**
>    (10 client giả). Nay đọc dạng chuỗi và dựng `occ_ids` theo job từ `edge_type==1`.
> 2. `_classify_edges` đoán loại cạnh theo khoảng chỉ số nên `job_skill`/`user_skill`
>    **rỗng** (0 cạnh) dù đồ thị có lớp nghề. Nay tách theo `edge_type` rồi suy
>    2 bước qua nghề: `job_skill = 2.593.468`, `user_skill = 18.017.133`.
> 3. `smoke_test.py` đoán `user_id` là 1,2,3… (đúng với demo, sai với dữ liệu thật
>    vì user_id là ID gốc CareerBuilder) → nay đọc user_id thật từ `graph.npz`.
> 4. `POST /api/train/start` thêm field `participants` (client_id thật) để UI vẽ
>    lưới node khớp số node báo cáo (trước đó UI đoán 13 ô → hiện "10/13").

### 9.7 PostgreSQL chết giữa chừng — tự degrade, KHÔNG trả 500

Đã kiểm chứng thật: bật API với PG (2 employer), `GET /api/clients` → 200; sau đó
`pg_ctl stop -m immediate` rồi gọi lại:

```
[db] PostgreSQL không dùng được (OperationalError: consuming input failed:
     server closed the connection unexpectedly) -> chuyển sang in-memory (artifacts)
GET /api/clients?limit=3      200  {"total": 9116, "items": [...randstad...]}
GET /api/graph/summary        200  {"n_users": 171807, ... "n_clients": 9116}
GET /api/clients/0            200  {"client_id": 0, "name": "randstad", ...}
GET /health                   200  {'status': 'ok', 'db': False, 'artifacts': True}
POST /api/train/start (5 client × 4 vòng)   → status = done, 4/4 vòng, đủ metric
```

Cơ chế: `PgStore._degrade(exc)` chuyển **một lần** sang `InMemoryStore` (đọc
`artifacts/v3` thật), và mọi hàm đọc/ghi (`clients`, `client_detail`, `summary`,
`recommend`, `create_run`, `set_run_status`, `add_round`, `add_latencies`, `runs`,
`run_status`) đều bọc `_safe` / try-except để gọi lại trên fallback. Run đang chạy
giữ được metric vì `add_round` ghi tiếp vào fallback thay vì ném lỗi.

> Muốn dùng lại PostgreSQL sau khi DB sống lại: **restart API** (degrade là vĩnh
> viễn trong tiến trình đó, có chủ đích để không "nhấp nháy" giữa hai nguồn số).


