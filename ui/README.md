# UI giám sát node FL — FL Node Console

Giao diện quản lý quá trình chạy tạo các node và mô phỏng đánh giá độ trễ thực tế
giữa các node (yêu cầu #10 của đề bài). HTML + CSS + JS thuần, **không build step**,
không framework, không npm. Chart.js và font IBM Plex được chép sẵn vào `vendor/`
nên chạy được cả khi offline.

```
ui/
├── index.html              màn hình duy nhất
├── assets/
│   ├── app.css             bảng đo kỹ thuật: giấy lạnh, đường kẻ mảnh, số mono
│   └── app.js              toàn bộ logic (API base ở đầu file)
├── vendor/
│   ├── chart.umd.min.js    Chart.js 4.4.1 (bản local, không cần CDN)
│   └── fonts/              IBM Plex Sans + Plex Mono (woff2, subset latin)
├── screenshots/            ảnh chụp từ Playwright
└── devtools/               script kiểm thử + mock backend (không thuộc sản phẩm)
```

## Cách mở

Ba cách, chọn cách nào cũng được:

**1. Mở thẳng file** — nhấp đúp `ui/index.html`, hoặc:

```powershell
start E:\2026\DUT\DSS\SauGK\CuoiKi\ui\index.html
```

**2. Serve tĩnh** (khuyến nghị khi demo, tránh giới hạn của `file://`):

```powershell
cd E:\2026\DUT\DSS\SauGK\CuoiKi\ui
python -m http.server 8080
# mở http://127.0.0.1:8080/index.html
```

**3. Đổi backend khác cổng 8000** — thêm query string, không cần sửa file:

```
index.html?api=http://127.0.0.1:8011
```

Mặc định UI trỏ tới `http://127.0.0.1:8000`. Cấu hình nằm ở **một chỗ duy nhất**:
hằng `API_BASE` ở đầu `assets/app.js`.

## Sáu thành phần bắt buộc

| # | Thành phần | Ở đâu |
|---|---|---|
| 1 | Thanh trên: `/health`, DB, artifacts, tổng client, nút Start Training | `.topbar` |
| 2 | Bảng client: client_id, tên employer, n_apps, n_users, n_jobs, status; phân trang; sắp xếp theo n_apps | `.table-panel` |
| 3 | Panel điều khiển: slider client 5..200, số vòng 1..50, FedAvg/FedProx, Start/Stop | `.control-panel` |
| 4 | Biểu đồ realtime: Recall@20 theo vòng, latency p50/p95 theo vòng (qua WebSocket, không polling) | `.charts-row` |
| 5 | Lưới node: mỗi client một ô vuông, xanh < 50 ms / vàng < 200 ms / đỏ ≥ 200 ms | `.node-grid` |
| 6 | Log dòng chảy: mỗi message WS một dòng `round X client Y latency Z ms` | `.log-panel` |

Thêm: dải tóm tắt đồ thị (9 chỉ số từ `/api/graph/summary`) và panel chi tiết client
khi bấm một dòng bảng hoặc một ô node (gọi `/api/clients/{client_id}`).

## Chế độ DEMO

UI **không bao giờ trắng trang**. Nếu không gọi được `/health`:

- tự chuyển sang **DEMO MODE**, hiện dải cảnh báo vàng ghi rõ lý do và base URL đang dùng;
- nạp bộ dữ liệu giả lập đúng quy mô thật (9.116 client, 171.807 user, 84.845 job — đo từ `artifacts/v3`);
- nút **Chạy demo** mô phỏng cả lượt huấn luyện: tick latency từng client, metric từng vòng;
- tự dò lại `/health` mỗi 3 giây; backend sống lại thì tự về chế độ live và giữ nguyên lượt chạy;
- có nút **Chế độ** để chuyển tay giữa live và demo.

Khi **đang chạy** mà backend chập chờn, UI **không** rơi vào DEMO — nó giữ dữ liệu cuối
và bật badge `disconnected`, tránh việc mất lượt chạy thật vì một lần timeout.

## Mất kết nối WebSocket

Badge ở thanh trên hiện `live · 2 kênh` / `live` / `disconnected` / `demo`.
Khi đứt, mỗi kênh (`/ws/latency`, `/ws/train/{run_id}`) tự thử lại **mỗi 3 giây**,
ghi một dòng log mỗi lần thử, và nối lại ngay khi backend trở lại.

## Hợp đồng API đã dùng

```
GET  /health                          {status, db, artifacts}
GET  /api/clients?limit=&offset=       {total, items:[{client_id,name,n_apps,n_users,n_jobs,status}]}
GET  /api/clients/{client_id}          thêm top_skills[]
GET  /api/graph/summary                9 chỉ số
POST /api/train/start                  {n_clients, rounds, algorithm, local_epochs} -> {run_id}
GET  /api/train/status/{run_id}        fallback một lần sau khi start (không polling)
WS   /ws/latency                       {type:'tick', run_id, round, client_id, latency_ms, bytes_up, bytes_down, ts}
WS   /ws/train/{run_id}                {type:'round', round, metrics, latency_ms}
```

UI tải client theo lô `limit=1000` cho tới hết `total` để phân trang và sắp xếp phía
client. Nếu backend chặn (trả ít hơn `total`), UI tự chuyển sang phân trang phía server
và gửi kèm `sort` / `order`.

Latency p50/p95 trên biểu đồ chỉ lấy từ các vòng **đã chốt** (có message `type:'round'`),
tính bằng percentile trên đúng tập tick của vòng đó — không lẫn tick giữa các vòng.

## Kiểm thử

`devtools/` chứa toàn bộ script kiểm chứng (không cần cho sản phẩm):

```powershell
$env:PYTHONIOENCODING='utf-8'
python ui\devtools\run_checks.py          # live + demo + file:// + mobile, tự dựng mock riêng cổng 8013
python ui\devtools\check_real_backend.py  # chạy với backend THẬT ở cổng 8000
python ui\devtools\check_ws_reconnect.py  # giết backend giữa lượt chạy -> disconnected -> tự nối lại
python ui\devtools\check_demo_recovery.py # mở UI khi backend chết -> DEMO -> backend lên -> tự về LIVE
python ui\devtools\check_deep.py          # dữ liệu thật trong Chart.js, lưới 200 node, đếm log
python ui\devtools\find_overflow.py       # soát tràn ngang ở 6 độ rộng viewport
```

`devtools/mock_backend.py` implement đúng hợp đồng trên, dùng khi backend thật chưa sẵn:

```powershell
python ui\devtools\mock_backend.py --port 8011
```

## Kết quả kiểm chứng

Chạy với **backend thật** `python api/main.py --dry-run --port 8000`:

- `/health` → badge `online`; `db:false`, `artifacts:false` hiện đúng là `không` / `thiếu`;
- dải tóm tắt: 300 user, 800 job, 120 skill, 15 nghề, 2.429 / 3.528 / 1.678 cạnh, 10 client, độ thưa 97,95 %;
- bảng client đúng 10 dòng, sắp xếp n_apps giảm dần (1.082 → 13);
- bấm dòng → panel chi tiết hiện `top_skills` thật từ backend;
- Start Training 10 client × 4 vòng → `run_id` thật, lưới 10 ô, 10/10 node báo cáo;
- biểu đồ Recall@20: 0,4750 → 0,5617 → 0,5798 → 0,5987;
- biểu đồ latency p50/p95: 0,96 / 6,85 → 1,57 / 8,48 → 1,85 / 19,97 → 2,34 / 14,48 ms;
- log đúng định dạng `round 4 client 7 latency 0 ms · 13.5 KB↑ 92.4 KB↓`;
- badge chuyển `đang chạy` → `hoàn tất`, vòng `4 / 4`, 0 lỗi console.

Chạy với mock (60 client × 6 vòng): lưới 60 ô đủ 3 màu (24 xanh / 33 vàng / 3 đỏ),
`60/60` node báo cáo, p50 55 ms, p95 195 ms, 250 dòng log, 0 lỗi console.
Lưới 200 node cuộn được trong khung 300 px.

Ảnh trong `screenshots/`:

| File | Nội dung |
|---|---|
| `01-live-idle.png` | live, chưa chạy |
| `02-live-running.png` | đang chạy, lưới node 3 màu + log |
| `03-live-done.png` | hoàn tất |
| `04-demo-mode.png` | DEMO MODE, dữ liệu giả lập |
| `05-demo-running.png` | DEMO đang mô phỏng |
| `06-file-url.png` | mở bằng `file://` |
| `07-mobile.png` | 430 px, không tràn ngang |
| `08-ws-disconnected.png` | badge disconnected khi backend chết |
| `12-live-200clients.png` | lưới 200 node |
| `13-live-client-cap-warning.png` | cảnh báo khi backend ít client hơn slider |
| `backend-real-01/02/03` | backend thật: idle / running / done |

## Ghi chú

- Font tự host nên không phụ thuộc Google Fonts; Chart.js local, có fallback CDN.
- Bảng và log dùng `tabular-nums` để số không nhảy khi cập nhật realtime.
- Có focus ring, điều hướng bảng bằng Enter/Space, tôn trọng `prefers-reduced-motion`.
- Nếu backend có ít client hơn số người dùng chọn trên slider, UI ghi rõ trong log
  (ví dụ: "Chỉ có 10 client trong dữ liệu — dùng 10/50 client đã chọn") và chỉ vẽ
  đúng số node có thật, không giả vờ đã chạy đủ.
- Nút **Stop** chỉ ngắt theo dõi phía UI — hợp đồng API chưa có endpoint dừng phía server,
  và UI ghi rõ điều đó trong log thay vì giả vờ đã dừng lượt chạy.
