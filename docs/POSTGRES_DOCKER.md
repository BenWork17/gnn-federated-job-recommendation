# PostgreSQL qua Docker cho đồ án DSS

Cấu hình đã kiểm chứng trên máy này: Docker Desktop 29.1.3, PostgreSQL 16-alpine,
Windows 11, ổ E còn ~24 GB.

---

## Vì sao dùng port 5433, không phải 5432

Máy đã có **PostgreSQL cài native trên Windows** chiếm port 5432 (PID 6028).
Docker dùng **5433** để hai cái chạy song song, không đụng nhau.

Nếu bạn muốn dùng 5432 thì phải tắt PostgreSQL native trước:
```powershell
Get-Service *postgres* | Stop-Service
```

---

## Chạy trong 3 lệnh

```powershell
cd E:\2026\DUT\DSS\SauGK\CuoiKi

# 1. Khởi động (lần đầu ~10 giây, tải image ~250 MB)
docker compose up -d

# 2. Nạp dữ liệu (~5 phút, 21 triệu dòng)
python api/load_to_pg.py --dsn "postgresql://dss:dss_dev_2026@127.0.0.1:5433/dss_jobs" --truncate

# 3. Tối ưu (~15 giây, tạo materialized view + index)
Get-Content api/optimize.sql -Raw | docker exec -i dss-postgres psql -U dss -d dss_jobs
```

Sau đó chạy API:
```powershell
$env:DSS_PG_DSN = "postgresql://dss:dss_dev_2026@127.0.0.1:5433/dss_jobs"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Kiểm tra:
```powershell
python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
# Phải ra: {'status': 'ok', 'db': True, 'artifacts': True}
```

Nếu `db: False` → chưa set `DSS_PG_DSN`, API rơi về in-memory.

---

## Thông số

| Mục | Giá trị |
|---|---|
| Image | `postgres:16-alpine` |
| Container | `dss-postgres` |
| Port | **5433** → 5432 (trong container) |
| User / Password | `dss` / `dss_dev_2026` |
| Database | `dss_jobs` |
| Volume | `dss_pgdata` (bền, không mất khi `down`) |
| Schema | tự chạy `api/schema.sql` lần đầu tạo volume |

Cấu hình PostgreSQL (đặt trong `docker-compose.yml`):

| Tham số | Giá trị | Lý do |
|---|---|---|
| `work_mem` | 256 MB | JOIN + GROUP BY trên 2,6M dòng |
| `maintenance_work_mem` | 512 MB | tạo index nhanh |
| `shared_buffers` | 512 MB | cache 3,2 GB dữ liệu |
| `max_wal_size` | 2 GB | COPY 18M dòng không bị checkpoint giữa chừng |
| `shm_size` | 256 MB | tránh lỗi `could not resize shared memory` |

---

## Dữ liệu sau khi nạp

Đo thật trên máy này:

| Bảng | Số dòng |
|---|---|
| `users` | 171.807 |
| `jobs` | 84.845 |
| `apps` | 436.893 |
| `employers` | 9.116 |
| `job_skills` | 2.593.468 |
| `user_skills` | 18.017.133 |
| **Tổng** | **21.072.062** |

Kích thước DB: **3,2 GB**

---

## Lệnh quản lý

```powershell
docker compose up -d            # khởi động
docker compose stop             # dừng (giữ dữ liệu)
docker compose down             # xoá container (giữ volume)
docker compose down -v          # XOÁ CẢ DỮ LIỆU
docker compose logs -f postgres # xem log
docker stats dss-postgres       # CPU/RAM

# vào psql
docker exec -it dss-postgres psql -U dss -d dss_jobs
```

---

## Hiệu năng đã tối ưu

`recommend` từ **5.902 ms xuống 274–373 ms** (nhanh 17×). Hai thay đổi:

1. **Query** (`api/db.py`): gộp theo `job_id` TRƯỚC khi join `jobs`, thay vì join rồi
   `GROUP BY` 4 cột. Giảm từ 1.009 ms xuống 449 ms ở mức SQL.
2. **Index + materialized view** (`api/optimize.sql`):
   - `idx_job_skills_skill_job (skill, job_id)` — Index Only Scan
   - `mv_skill_jobs` — bảng skill→job đã gộp sẵn
   - `ANALYZE` đầy đủ để planner chọn đúng

Đo được sau tối ưu:

| Endpoint | Thời gian |
|---|---|
| `/health` | 89 ms |
| `/api/clients` | 39 ms |
| `/api/clients/{id}` | 156 ms |
| `/api/graph/summary` | 5,8 s (lần đầu, sau đó cache 2–25 ms) |
| `/api/recommend` | **274–373 ms** |
| `/api/train/start` | 42 ms |
| `/api/train/status` | 3 ms |

---

## Xử lý sự cố

**Container không lên**
```powershell
docker compose logs postgres
```
Hay gặp: port 5433 bị chiếm → đổi sang 5434 trong `docker-compose.yml`.

**`db: False` trong /health**
```powershell
# kiểm tra biến môi trường
echo $env:DSS_PG_DSN
# phải bắt đầu bằng postgresql://dss:dss_dev_2026@127.0.0.1:5433
```

**Nạp dữ liệu chậm hoặc bị ngắt**
```powershell
python api/load_to_pg.py --dsn "..." --truncate --batch-size 50000
```
Đo trên máy này: 316 giây với batch 50.000. Nếu chậm hơn 10 phút → kiểm
`docker stats` xem RAM, hoặc tăng `shm_size`.

**Schema không tự chạy**
Chỉ chạy lần đầu tạo volume. Nếu đã `down -v` rồi `up` lại thì chạy lại:
```powershell
Get-Content api/schema.sql -Raw | docker exec -i dss-postgres psql -U dss -d dss_jobs
```

**Sau khi tối ưu, query vẫn chậm**
```powershell
Get-Content api/optimize.sql -Raw | docker exec -i dss-postgres psql -U dss -d dss_jobs
```
Lệnh này idempotent — chạy lại nhiều lần an toàn.

---

## Khác biệt với `--dry-run`

| | `--dry-run` | Docker PostgreSQL |
|---|---|---|
| Cần Docker | không | có |
| `db` trong /health | `false` | `true` |
| `data_source` | `artifacts` | `postgres` |
| Dữ liệu | nạp `artifacts/v3` vào RAM | đọc từ DB 3,2 GB |
| Recommend | 10–20 ms | 274–373 ms |
| Train lịch sử | mất khi tắt | lưu trong `train_runs` |
| Phù hợp | demo nhanh, bảo vệ | chứng minh dùng DB thật |

Cả hai đều trả cùng số liệu (171.807 user, 9.116 client) vì cùng đọc `artifacts/v3`.
