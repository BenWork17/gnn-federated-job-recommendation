# Giám sát node Federated Learning — hướng dẫn chạy và giải thích

Tab thứ 6 của web demo. Nhúng giao diện `ui/` vào Streamlit bằng iframe, và giải thích
**một node là gì, một vòng chạy ra sao, cái gì ở lại máy**.

---

## 1. Chạy trong 2 lệnh

```powershell
# Terminal 1 — backend + PostgreSQL
cd E:\2026\DUT\DSS\SauGK\CuoiKi
docker compose up -d
$env:DSS_PG_DSN = "postgresql://dss:dss_dev_2026@127.0.0.1:5433/dss_jobs"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Streamlit
cd E:\2026\DUT\DSS\SauGK\CuoiKi
python -m streamlit run app/streamlit_app.py --server.headless=true
```

Mở **http://127.0.0.1:8501** → sidebar → **🖥️ Giám sát node FL**.

Phải thấy badge xanh **"Backend đang chạy"** và bảng client có `randstad` ở dòng đầu
với 4.745 app.

Nếu backend tắt, tab vẫn mở nhưng hiện **DEMO MODE** và hướng dẫn 2 lệnh ở trên.

---

## 2. Vì sao phải chạy 2 terminal

```
Streamlit (8501)
  └─ iframe srcdoc (~574 KB, CSS/JS đã inline)
       └─ fetch + WebSocket → FastAPI (8000)
                                  └─ PostgreSQL Docker (5433, 3,7 GB, 21 triệu dòng)
```

Streamlit **không** chứa dữ liệu hay logic FL. Nó chỉ nhúng giao diện. Mọi số liệu
đến từ API. Tắt API thì tab không có số thật.

---

## 3. Bốn khối giải thích trên giao diện

| Khối | Trả lời câu hỏi | Có gì |
|---|---|---|
| **Một node là gì?** | "Cái ô vuông này là gì?" | Thẻ employer thật (randstad 4.745/4.215/603), dòng **MÔI TRƯỜNG CHẠY** |
| **Một vòng FL qua 5 bước** | "Nó chạy như thế nào?" | 5 khối, mỗi khối AI LÀM / DI CHUYỂN / KÍCH THƯỚC, khối hiện tại phát sáng |
| **Cái gì ở lại — cái gì truyền đi** | "Dữ liệu có đi không?" | 2 cột đối chiếu, số dòng thô thật vs byte thật từ WebSocket |
| **Trace một node** | "Bấm vào thì xem được gì?" | 4 trạng thái bằng chữ, timeline 5 vòng |

### Quy ước màu trên sơ đồ 5 bước

- 🟩 **xanh = ở lại máy** — bước 2 (train cục bộ), bước 4 (FedAvg). Ghi **`0 B`** vì không có gì đi ra.
- 🟧 **cam = truyền đi** — bước 1, 3, 5. Kèm số KB thật đo từ WebSocket.

Bước 2 và 4 ghi `0 B` là điểm quan trọng nhất khi trình bày: **hai bước trong năm không
phát sinh byte nào**, đó chính là chỗ dữ liệu được giữ lại.

### Bốn trạng thái của một node

| Trạng thái | Nghĩa |
|---|---|
| `idle` | chưa tham gia vòng nào |
| `training` | đang chạy SGD trên dữ liệu cục bộ của mình |
| `uploading` | đang gửi Δ embedding lên server |
| `waiting` | đã gửi xong, đang chờ server tổng hợp và gửi vòng mới |

---

## 4. Metric nào thật, metric nào mô phỏng

**Bắt buộc nói rõ khi bảo vệ.** API trả `"simulated_metrics": true`.

| Chỉ số trên console | Thật hay mô phỏng | Ghi chú |
|---|---|---|
| `latency_ms` (p50, p95) | **THẬT** | đo bằng `time.perf_counter` từng node |
| `bytes_up`, `bytes_down` | **THẬT** | 12,5–15,5 KB lên · 92,0–95,6 KB xuống mỗi node/vòng |
| Số client, bảng employer | **THẬT** | đọc từ PostgreSQL, 9.116 client |
| `recall20`, `ndcg20`, `mrr20`, `loss` | **MÔ PHỎNG** | sinh để minh hoạ vòng lặp, không phải kết quả huấn luyện |

Kết quả nghiên cứu thật nằm ở `results_v3/` (notebook Kaggle):

| | |
|---|---|
| LightGCN, vũ trụ FL | R@20 = **0,7151** |
| Item-KNN, catalog đầy đủ | R@20 = **0,5408** |
| FedAvg mô phỏng, vũ trụ FL | R@20 = 0,3905 |

Trên giao diện có ghi nguyên văn dưới biểu đồ Recall:
> "Đường cong **mô phỏng** để minh hoạ vòng lặp FedAvg — không phải kết quả huấn luyện
> thật. Kết quả thật ở notebook Kaggle: LightGCN 0,7151 (vũ trụ FL)."

---

## 5. Phạm vi mô phỏng — nói thẳng

> **50 node chạy như 50 luồng trong MỘT tiến trình Python trên một máy.**
> Không phải 9.116 máy thật. Latency đo thật, nhưng không có độ trễ mạng giữa các máy.

Triển khai phân tán thật cần thêm:

| Việc | Đồ án đã làm? |
|---|---|
| Mỗi node một tiến trình/container riêng | ❌ chưa |
| Kênh truyền gRPC/HTTP giữa node và server | ❌ chưa |
| Secure aggregation | ❌ chưa |
| DP-SGD chống suy ngược gradient | ❌ chưa |

Đây là **mô phỏng vòng lặp FedAvg**, đủ để chứng minh cơ chế và đo chi phí truyền
thông, chưa phải hệ thống production.

---

## 6. Nếu iframe không hiển thị

Ba nguyên nhân, theo thứ tự hay gặp:

**1. Backend chưa chạy** — tab hiện DEMO MODE. Kiểm:
```powershell
python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
```
Phải ra `{'status': 'ok', 'db': True, 'artifacts': True}`.

**2. Bản inline chưa build hoặc đã cũ** — `ui/index.html` đổi mà chưa rebuild:
```powershell
python tools/build_ui_inline.py           # rebuild
python tools/build_ui_inline.py --check   # exit 0 = đồng bộ
```

**3. WebSocket bị chặn** — đã kiểm bằng Selenium + Chrome 157, **hoạt động bình
thường trong iframe srcdoc**, console 0 lỗi. Nếu môi trường khác chặn, giao diện vẫn
hiện và tự chuyển sang DEMO MODE, không trắng trang.

---

## 7. Kiểm chứng đã chạy

| Hạng mục | Kết quả |
|---|---|
| Backend `/health` | `{status: ok, db: True, artifacts: True}` |
| `/api/clients` | `total=9116`, `data_source=postgres` |
| CSS trong iframe | `rgb(233,237,240)` — load đúng |
| 4 panel giải thích | 5/5 có mặt |
| Bấm Start → WebSocket tick | **PASS** (log tăng ngay) |
| Lưới node | 50 ô |
| Canvas biểu đồ | 960×186 × 2 |
| Trace node | mở được, hiện randstad #0 |
| **Console errors** | **0** |
| `pytest tests/` | **72 passed** |
| `build_ui_inline.py --check` | exit 0 |

Ảnh: `ui/screenshots/nc-01-running.png`, `nc-02-done.png`, `nc-03-demo-mode.png`,
`t4-verify-inline.png`.

---

## 8. File liên quan

| File | Vai trò |
|---|---|
| `app/views/giam_sat_node.py` | Trang Streamlit, kiểm backend rồi nhúng iframe |
| `tools/build_ui_inline.py` | Nhúng CSS/JS/font vào 1 file HTML duy nhất |
| `ui/_inline/index_inline.html` | **Sinh tự động**, 574 KB — không sửa tay |
| `ui/index.html` + `assets/` | Giao diện gốc, chạy độc lập được ở cổng 8081 |
| `docs/GIAI_THICH_FL_NODE.md` | Giải thích chuyên sâu + kịch bản nói trước hội đồng |
| `api/main.py` | 11 endpoint, WebSocket `/ws/latency` |
| `docker-compose.yml` | PostgreSQL 16, cổng 5433 |

---

## 9. Kịch bản nói ngắn (3 câu)

> "Đây là 9.116 nhà tuyển dụng, mỗi nhà một node. Em bấm chạy, mỗi node tự huấn luyện
> trên dữ liệu của mình — các bước màu xanh ghi **0 byte**, nghĩa là trong bước huấn
> luyện cục bộ và bước tổng hợp, không có dữ liệu nào rời máy.
>
> Cái di chuyển chỉ là vector số thực: 12,8 KB gửi lên, 94,8 KB nhận xuống mỗi vòng.
> Ở lại máy là 9.563 dòng thô gồm mã ứng viên, mã tin, đơn ứng tuyển, ngày ứng tuyển.
>
> Em nói rõ giới hạn: đây là mô phỏng 50 node trong một tiến trình, chưa có secure
> aggregation và chưa có DP-SGD. Giá trị không phải tốc độ, mà là dữ liệu không rời máy."

Xem thêm `docs/GIAI_THICH_FL_NODE.md` để có 8 câu đầy đủ và 3 câu trả lời cho câu hỏi khó.
