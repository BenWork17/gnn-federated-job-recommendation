# Khảo sát demo trực quan hoá trên mạng — gợi ý cho đồ án

**Ngày khảo sát:** 2026-11-01 · **Người thực hiện:** agent khảo sát
**Đối tượng:** đồ án *GNN + Federated Learning cho gợi ý việc làm*
**Trạng thái:** ✅ mục ① và ④ (sửa lỗi) **đã được triển khai** — xem mục **8** ở cuối.

> **Ghi chú lịch sử:** tài liệu này được viết khi đồ án còn một đề tài thứ hai
> về an ninh mạng IoT. Đề tài đó đã được gỡ bỏ (đề bài chỉ có một bài toán),
> nên mọi mục nói về IoT dưới đây chỉ còn giá trị tham khảo lịch sử.

---

## 0. TL;DR — 5 dòng

1. Thứ đáng nâng cấp nhất là **đồ thị việc làm 2D → 3D tương tác** — đã làm (mục 8.2).
2. Cách làm **không cần cài gì**: `pydeck 0.9.1` **đã có sẵn** trên máy, dựng được 3D thật
   (`OrbitView` + `ScatterplotLayer` có trục z). Đã **chạy thử trên dữ liệu thật**.
   ⚠️ **Nhưng `OrbitView` không hoạt động trong Streamlit** — bundle deck.gl của Streamlit
   chỉ đăng ký `MapView`, nên canvas trắng. Đã đổi sang `3d-force-graph` nhúng qua
   `st.components.v1.html`. Chi tiết chẩn đoán ở **mục 9**.
3. Đã kiểm chứng `pip install` **vẫn bị chặn** ngay cả khi đổi `TMP` sang ổ E
   (`Errno 13 Permission denied` trên file `.whl.metadata`) → **mọi demo cần cài gói mới đều loại**.
4. ✅ **Lỗi `job_nodes` (mục 2b) đã được sửa** — 200/200 tin giờ đúng dải, đồ thị từ 1.375 lên
   **1.915 cạnh**, và có **regression test** canh lỗi này.
5. Còn lại 2 thứ **rẻ mà tăng điểm cao**: animation lan truyền theo lớp GNN, và biểu đồ 3D
   "chi phí ↔ chất lượng" của Federated Learning.

---

## 1. Ràng buộc thực tế của môi trường (đã kiểm chứng, không suy đoán)

| Kiểm tra | Kết quả |
|---|---|
| Gói đang có | `streamlit 1.55.0`, `altair 6.0.0`, `pydeck 0.9.1`, `networkx 3.6.1`, `matplotlib 3.10.8`, `scikit-learn 1.8.0`, `torch 2.10.0` |
| Gói **KHÔNG** có | `plotly`, `pyvis`, `umap-learn`, `dtale`, `bokeh` |
| `pydeck` dựng 3D? | **Có** — `pdk.View(type="OrbitView")` + layer có `get_position=["x","y","z"]`; JSON sinh ra chứa `OrbitView`, `ScatterplotLayer`, `LineLayer` |
| Layer dùng được | `ScatterplotLayer`, `LineLayer`, `PathLayer`, `ColumnLayer`, `TextLayer`, `GridCellLayer`, `PointCloudLayer` — tất cả khởi tạo OK |
| `networkx.spring_layout(dim=3)` | **Có** (dùng được, khỏi viết lại layout 3D) |
| `pip install` | **BỊ CHẶN** — `Errno 13 Permission denied` trên `*.whl.metadata`; đổi `TMP/TEMP` sang `E:\...\artifacts\.pip-tmp` **không cứu được**; `python -m venv` cũng fail (`ensurepip` exit 1) |
| Tải file từ CDN | **Được** (test `cdn.jsdelivr.net/npm/3d-force-graph@1.73.4/...js` → 200). PowerShell `Invoke-WebRequest` thì hỏng TLS, phải dùng Python `urllib` |
| Playwright screenshot | **Bị chặn** (`WinError 5` khi tạo pipe) — đúng như README mục "Không chụp screenshot tự động được" |

> **Kết luận ràng buộc:** chỉ dùng `st.components.v1.html` (có sẵn trong Streamlit, không cần gói
> ngoài) + `pydeck` + file `.js` tải sẵn. **Không** đề xuất `st-link-analysis`, `streamlit-agraph`,
> `streamlit-echarts` cho bản nộp — chúng cần `pip install`.

---

## 2. Đã chạy thử: đồ thị 3D trên dữ liệu thật của bạn

File: `artifacts/_proto_3d/proto_3d.py` · kết quả: `medajob_3d.html` (mở trực tiếp bằng trình duyệt)

| | Đồ thị việc làm |
|---|---|
| Nguồn | `artifacts/medajob/graph.npz` |
| Nội dung | 4 loại nút (ứng viên / tin / kỹ năng / ngành), cạnh **riêng tư tô đỏ**, cạnh công khai xám mờ |
| Layout | `nx.spring_layout(dim=3)` |
| Quy mô | 385 nút · 1.915 cạnh (2 chiều) |
| **Thời gian dựng** | **0,55 s** — JSON **768 KB** |
| Chạy được trong Streamlit? | Có, `st.pydeck_chart(deck)` |

Hai cách làm layout 3D, đã đo:

| Cách | Thời gian | Nhận xét |
|---|---|---|
| Mở rộng `spring_layout()` **sẵn có của app** lên `dim=3` | 0,57 s | **Khuyến nghị** — dùng lại code đã có, bố cục cùng "giọng" với bản 2D |
| `nx.spring_layout(dim=3)` | 0,22 s | Nhanh hơn, nhưng bố cục khác hẳn bản 2D → bật/tắt 2D–3D sẽ thấy hình "nhảy" |

---

## 2b. ⚠️ Phát hiện khi đối chiếu code (quan trọng hơn phần demo)

Trong lúc chạy prototype, tôi đối chiếu với **chính hàm `build_graph_view()`** của app và
phát hiện **cùng một lớp lỗi "cộng offset lần thứ hai" vẫn còn ở phần chọn tin**.

Trong `app/views/do_thi_viec_lam.py` (trạng thái lúc 16:51):

```python
ranked = sorted(job_edges.items(), key=lambda kv: (-kv[1], kv[0]))
job_nodes = [nU + j for j, _ in ranked[:n_job_sample]]   # ← j ĐÃ là id tuyệt đối
```

`job_edges` được dựng bằng `for a, b in zip(ei[0][e0], ei[1][e0])` rồi `job_edges[int(a)]`,
trong đó `a` là **node id tuyệt đối** (đã nằm trong `nU <= a < nU+nJ`). Vì vậy `j` đã là id
tuyệt đối; cộng thêm `nU` là **cộng hai lần**.

**Đã xác nhận bằng cách chạy chính `build_graph_view()` của app (bản mới nhất, 16:53):**

```
job_nodes app sinh ra : 200
  nằm đúng dải tin    : 171
  RƠI VÀO DẢI KỸ NĂNG :  29   ← lỗi, ví dụ [1087, 1099, 1145, 1151, 1103]
cạnh: 1.375 ({'Công khai': 948, 'Riêng tư': 427})
```

Hậu quả đo được (cùng một khung dữ liệu, chỉ đổi cách tính `job_nodes`):

| | nút "Tin tuyển dụng" | cạnh | công khai | riêng tư |
|---|---|---|---|---|
| Code hiện tại (cộng `nU` lần 2) | 171 | 1.375 | 948 | 427 |
| Bản đúng (dùng `j` nguyên) | **200** | **1.915** | **1.479** | 436 |

- **29/200 id rơi vào dải kỹ năng** (`nU+j` vượt qua `nU+nJ`), tức hình đang bỏ mất 29 tin
  tốt nhất và thay bằng nút kỹ năng.
- Hai cách chọn **chỉ trùng nhau 41/200 id** — không phải sai số nhỏ, mà là **chọn nhầm ~80%**.
- Mất **540 cạnh công khai** so với bản đúng.

Điều này **không làm app crash** (id vẫn < tổng số nút nên không lỗi index), nên rất dễ lọt —
đúng loại "lỗi phương pháp không gây lỗi chương trình" mà mục *Bài học phương pháp* trong
báo cáo đang nói tới. Nhưng nó làm **chính biểu đồ minh hoạ cho luận điểm "ranh giới dữ liệu"**
hiển thị sai mật độ.

> **Đề nghị:** sửa `job_nodes = [int(j) for j, _ in ranked[:n_job_sample]]`, và thêm
> regression test đúng kiểu repo đang làm:
> ```python
> def test_job_nodes_are_jobs():
>     node_df, _ = build_graph_view.__wrapped__()
>     ...
>     assert all(nU <= i < nU + nJ for i in job_nodes)
> ```
> Lưu ý: comment ngay trên đó đã ghi *"LỖI ĐÃ SỬA (hai lần)"* cho phần `top_skills` — cùng
> một gốc lỗi, phần `job_nodes` bị bỏ sót.

### ✅ Đã sửa (xem mục 8)

`job_nodes` giờ là `[int(j) for j, _ in ranked[:n_job_sample]]`, kèm `assert` chặn tái phát.
Kết quả sau khi sửa: **200/200 tin đúng dải**, **385 nút**, **1.915 cạnh**. Có 8 regression
test trong `tests/test_graph_view.py` canh cả lỗi này lẫn chế độ 3D.

---

## 3. Các demo trên mạng — phân loại theo "dùng được ngay / chỉ để tham khảo"

### 3.1 Dùng được NGAY (không cần cài gì) — ưu tiên cao

| Demo | Link | Vì sao liên quan | Lấy gì |
|---|---|---|---|
| **3d-force-graph — họ demo** | https://vasturiano.github.io/3d-force-graph/ (6,5k★) | Bộ demo 3D đồ thị đẹp nhất trên mạng. ✅ **Đang dùng trong app** (bundle tự chứa, nhúng qua `st.components`) | Giao diện, lực đẩy 3D, hover nhãn |
| ↳ *directional moving particles* | https://vasturiano.github.io/3d-force-graph/example/directional-links-particles/ | **Hạt chạy dọc cạnh** — đúng ẩn dụ "tham số chạy client → server" | Ý tưởng cho trang Mô phỏng liên bang |
| ↳ *large graph (~4k)* | https://vasturiano.github.io/3d-force-graph/example/large-graph/ | Mốc tham chiếu hiệu năng: 4k phần tử vẫn mượt | Ngưỡng để biết nên lấy mẫu bao nhiêu nút |
| ↳ *bloom effect* | https://vasturiano.github.io/3d-force-graph/example/bloom-effect/ | Hiệu ứng phát sáng cho nút "cảnh báo" | Tuỳ chọn thêm |
| **deck.gl OrbitView** | https://deck.gl/examples/plot | ⚠️ **Không dùng được trong Streamlit** — bundle chỉ có `MapView` (mục 9). Vẫn hữu ích nếu xuất HTML riêng | Tham khảo, không dùng cho app |
| **pydeck docs** | https://deck.gl/docs/api-reference/core/orbit-view | Như trên | Tham khảo |
| **Distill — Gentle Intro to GNN** | https://distill.pub/2021/gnn-intro/ | Hover một nút → thấy nó gom thông tin từ hàng xóm qua từng lớp. **Đây là demo sư phạm tốt nhất cho phần GNN** | Ý tưởng animation lan truyền theo lớp |
| **Distill — Convolutions on Graphs** | https://distill.pub/2021/understanding-gnns/ | Cùng nhóm, đi sâu hơn | — |

### 3.2 Rất liên quan nhưng phải cài gói → **chỉ để tham khảo**

| Demo | Link | Ghi chú |
|---|---|---|
| **st-link-analysis** (cytoscape.js) | https://github.com/timothyw/link-analysis · PyPI `0.4.0` (2025-06) | Đồ thị tương tác đẹp nhất cho Streamlit; kéo thả, chọn nút. **Không cài được** → nếu muốn, phải tự nhúng cytoscape.js thủ công |
| **streamlit-agraph** (vis.js) | https://github.com/ChrisDelClea/streamlit-agraph (483★) | Có demo: https://marvelous-graph.streamlit.app — bản cuối 2023, khá cũ |
| **streamlit-echarts** | https://github.com/andfanilo/streamlit-echarts (639★) | ECharts có `graph` 3D + `GL`; demo Streamlit Cloud còn sống |
| **pygwalker** | https://github.com/Kanaries/pygwalker (16k★) | Tableau-style kéo thả trên dataframe; **nặng**, không hợp bản nộp offline |
| **GNNLens2** (dmlc) | https://github.com/dmlc/GNNLens2 (263★) | Đúng thứ bạn cần: xem embedding + attention của GNN. Nhưng dừng từ 2022, cần cài |
| **GNNExplainer** | https://github.com/RexYing/gnn-model-explainer (1k★) | Giải thích dự đoán GNN — liên quan trực tiếp mục "vì sao tin này được gợi ý" |
| **PyVis** | https://github.com/WestHealth/pyvis (1,2k★) | Dễ dùng nhưng bản cuối 2024, cần cài |

### 3.3 Tham khảo ý tưởng (không dùng code)

| Demo | Link | Ý tưởng lấy được |
|---|---|---|
| **TensorFlow Embedding Projector** | https://projector.tensorflow.org/ | Giảm chiều embedding người dùng/tin xuống 3D rồi cho xoay — "cụm ứng viên giống nhau nằm gần nhau". Ấn tượng mạnh khi bảo vệ |
| **deck.gl globe-view** | https://deck.gl/examples/globe-view | Nếu muốn "bản đồ tấn công toàn cầu" cho IoT. Với IoT-23 thì **không có toạ độ địa lý thật** → chỉ nên làm nếu chấp nhận dữ liệu minh hoạ |
| **deck.gl Tile3DLayer** | https://deck.gl/docs/api-reference/geo-layers/tile-3d-layer | 3D Tiles — không phù hợp (cần dữ liệu địa lý) |
| **Flower (FL framework)** | https://github.com/adap/flower (7,2k★) · https://flower.ai/docs/framework/ | Cách họ **trực quan hoá vòng federated**; tham khảo cách đặt tên/khái niệm |
| **PySyft** | https://github.com/OpenMined/PySyft (10k★) | Cách diễn đạt "dữ liệu không rời khỏi client" |

---

## 4. Đề xuất cụ thể, xếp theo tỉ lệ "ấn tượng / công sức"

### ① Đồ thị việc làm 2D → **3D xoay được** ⭐ ưu tiên số 1
- Thêm toggle **"2D / 3D"** ngay trên trang *Đồ thị việc làm*; giữ bản Altair 2D làm mặc định
  (an toàn khi máy chiếu yếu), 3D là tuỳ chọn.
- Dùng `st.pydeck_chart`, `OrbitView`, `nx.spring_layout(dim=3)`. **Đã chạy được, 0,55 s.**
- Giá trị sư phạm: khi xoay, **cụm ứng viên–tin–kỹ năng tách ra theo chiều sâu**; tắt
  "Hiện cạnh riêng tư" thì các cụm rời nhau thấy rõ — mạnh hơn hẳn bản 2D.
- Rủi ro: thấp. Không đụng tới pipeline số liệu, chỉ thêm 1 hàm trong `app/components/`.
- ⚠️ Làm sau khi sửa lỗi mục **2b**, nếu không sẽ dựng 3D trên một đồ thị sai.

### ② (đã gỡ cùng đề tài IoT) Đồ thị luồng mạng
- Phần này thuộc đề tài thứ hai đã bị gỡ bỏ. Giữ lại đây chỉ để ghi nhận lịch sử:
  nếu sau này làm lại một bài toán phát hiện bất thường trên đồ thị, cách tiếp cận
  tương tự vẫn dùng được (`graph3d.py` đã tách riêng nên tái sử dụng được).

### ③ Animation lan truyền theo lớp GNN (kiểu Distill)
- Nút chọn "lớp 1 / 2 / 3"; mỗi bước làm sáng vùng lân cận của nút đang chọn.
- Trả lời đúng câu hỏi hội đồng hay hỏi: *"GNN khác gì MLP?"* → "nhìn được nó gom thông tin
  từ mấy bước lân cận". Rất rẻ: chỉ tô màu/độ mờ, không cần thư viện mới.
- Lưu ý: `app/` đã có sẵn cơ chế `st.fragment(run_every=...)` — dùng lại, **đừng** dùng `time.sleep()`.

### ④ Chi phí ↔ chất lượng Federated Learning — biểu đồ 3D "bậc thang"
- 3 trục: vòng · Recall@20 · byte truyền. Số liệu **đã có sẵn** trong
  `results/reco_main.json` (`communication.*`, `fedprox_curve`).
- Hiện con số "tốn gấp 6.565 lần băng thông" chỉ là một câu chữ trong khối văn bản → biến
  thành hình thì mạnh hơn nhiều.
- Cách rẻ nhất: scatter 3D bằng pydeck `ScatterplotLayer` (z = byte), hoặc `ColumnLayer`
  dựng cột 3D.

### ⑤ (đã gỡ cùng đề tài IoT) Trang hiệu chuẩn
- Phần này thuộc đề tài thứ hai đã bị gỡ bỏ. Với bài toán gợi ý, khái niệm tương đương là
  hiệu chuẩn **điểm số BPR** — nhưng điểm BPR không phải xác suất nên không vẽ histogram
  xác suất được; đây là hướng phát triển ghi trong báo cáo.

### ⑥ (Tuỳ chọn, đẹp nhất nhưng đắt nhất) nhúng **3d-force-graph** thủ công
- Tải `3d-force-graph.min.js` (~1 MB, **đã test tải được**) vào `app/assets/`, nhúng bằng
  `st.components.v1.html`, truyền `nodes`/`links` qua `json.dumps`.
- Được: hạt chạy dọc cạnh, phát sáng, kéo thả nút — đẹp hơn pydeck nhiều.
- Mất: ~1 MB trong repo, và **phải tự viết cầu nối** Streamlit ↔ JS (click nút không trả
  về Python được nếu không làm custom component). Chỉ nên làm nếu còn thời gian.

---

## 5. Những gì **KHÔNG** nên làm (để tránh mất điểm)

1. **Đừng** thêm phụ thuộc mới vào `requirements.txt` — môi trường không cài được, người
   chấm chạy `run_all.ps1` sẽ vỡ. Giữ đúng triết lý "chỉ dùng thứ đang có" mà README đã nêu.
2. **Đừng** thay Altair bằng Plotly/Dash — vừa không cài được, vừa phá tính nhất quán màu
   giữa 9 hình báo cáo và app.
3. **Đừng** đụng vào `theme.py`/`prefers-reduced-motion` — app đã xử lý accessibility tốt;
   thêm animation 3D phải **tôn trọng** cờ giảm chuyển động đó.
4. **Đừng** thêm lại nội dung về đề tài an ninh mạng IoT — đề bài chỉ có một bài toán.

---

## 6. Nếu agent chính cần triển khai — thứ tự đề nghị

```
Bước 0  [TRƯỚC TIÊN] sửa job_nodes (mục 2b) + regression test
Bước 1  app/components/__init__.py — đổi spring_layout(dim=2) thành dim tham số
Bước 2  app/components/graph3d.py  — nhúng 3d-force-graph (đã làm thay pydeck)
Bước 3  do_thi_viec_lam.py         — toggle 2D/3D, tái dùng build_graph_view()
Bước 4  fl_sim.py                  — scatter 3D vòng × Recall × byte
```

Prototype đã chạy được ở `artifacts/_proto_3d/proto_3d.py` — **có thể copy thẳng** phần
`layout_3d()` và 2 hàm `build_*()` rồi đổi `pdk.Deck` thành giá trị trả về cho `st.pydeck_chart`.

**Kiểm thử tối thiểu nên thêm** (khớp phong cách repo — mỗi lỗi thật một regression test):
- `test_deck3d.py`: JSON pydeck parse được, có đúng số layer, **không có toạ độ NaN**.
- Test `job_nodes` phải nằm trọn trong dải `[nU, nU+nJ)` — đây chính là lỗi ở mục 2b.
- Test rằng khi tắt "cạnh riêng tư" thì số cạnh trong deck **giảm đúng** bằng số cạnh
  `Riêng tư` của đồ thị con (đây chính là con số đang được nói trong kịch bản demo).

---

## 7. Nguồn đã kiểm chứng (đều trả HTTP 200 tại thời điểm khảo sát)

- https://vasturiano.github.io/3d-force-graph/ — 6.520★, cập nhật 2026-09-29
- https://deck.gl/examples/plot (OrbitView) · https://deck.gl/docs/api-reference/core/orbit-view — deck.gl 14.724★
- https://distill.pub/2021/gnn-intro/ · https://distill.pub/2021/understanding-gnns/
- https://projector.tensorflow.org/
- https://github.com/ChrisDelClea/streamlit-agraph — 483★
- https://github.com/andfanilo/streamlit-echarts — 639★
- https://github.com/dmlc/GNNLens2 — 263★ (dừng 2022)
- https://github.com/RexYing/gnn-model-explainer — 1.063★
- https://github.com/adap/flower — 7.193★
- https://streamlit.io/components — danh mục component chính thức

*Ghi chú: `web_search` không dùng được trong phiên này (thiếu `DEEPSEEK_API_KEY`). Toàn bộ thông
tin trên lấy bằng `web_fetch` trực tiếp + GitHub API + PyPI JSON API, nên số ★ và ngày cập nhật
là số đo thật, không phải ước lượng.*

---

## 8. Những gì đã triển khai (2026-11-01, sau khảo sát)

### 8.1 Sửa lỗi `job_nodes`

`app/views/do_thi_viec_lam.py`:

```python
# trước
job_nodes = [nU + j for j, _ in ranked[:n_job_sample]]
# sau
job_nodes = [int(j) for j, _ in ranked[:n_job_sample]]
assert all(nU <= j < nU + nJ for j in job_nodes), \
    "job_nodes phải nằm trọn trong dải nút tin tuyển dụng"
```

Kết quả đo lại:

| | nút | tin | cạnh | công khai | riêng tư |
|---|---|---|---|---|---|
| Trước | 370 | 171 | 1.375 | 948 | 427 |
| **Sau** | **385** | **200** | **1.915** | **1.479** | **436** |

### 8.2 Thêm chế độ 3D

| File | Thay đổi |
|---|---|
| `app/components/__init__.py` | `spring_layout(..., dim=2)` — thêm tham số `dim`, cùng công thức cho 2D và 3D |
| `app/components/graph3d.py` | **mới** — `graph_html_3d()` / `render_graph_3d()`, nhúng `3d-force-graph` + bảng điều khiển |
| `app/assets/3d-force-graph.min.js` | **mới** — bundle 690 KB, đã gói sẵn Three.js, chạy offline |
| `tools/fetch_3d_asset.py` | **mới** — tải bundle một lần (cần mạng), để tái lập được |
| `app/views/do_thi_viec_lam.py` | `build_graph_view(dim=...)` trả thêm cột `z` khi `dim=3`; thêm radio **2D / 3D** |
| `tests/test_graph_view.py` | **mới** — 13 regression test |

Chi tiết kỹ thuật đáng lưu ý:

- **Không ghim cứng nút**: toạ độ truyền bằng `x/y/z`, **không** `fx/fy/fz`. Bản đầu dùng
  `fx/fy/fz` nên lực đẩy 3D vô hiệu — đồ thị đặc và khó đọc. Đây là lỗi *thứ ba* của phần 3D
  trong phiên này.
- **Loc cạnh theo nút**: khi bỏ chọn một loại nút, cạnh nối vào nút đã ẩn bị bỏ theo — nếu
  không sẽ còn "cạnh treo" lơ lửng. Bản 2D cũ có biến `present` tính nhưng không dùng.
- **Điều khiển trong iframe, không ở Streamlit**: đặt ở Streamlit thì mỗi lần bấm là một lần
  rerun, iframe nạp lại 1 MB HTML và lực đẩy chạy lại từ đầu → đồ thị "nhảy". Đánh đổi:
  trạng thái đồ thị không đồng bộ với Streamlit.
- **Tâm cụm khai báo bằng Python** (`_CLUSTER_CENTERS`, `SPREAD`) rồi chèn vào JS, để test
  Python kiểm được khoảng cách mà không phải đọc chuỗi JS. Tứ diện ban đầu chỉ cách 260 <
  2×150 → cụm chồng nhau; đã nới lên 440.
- **Thông báo lỗi thay vì khung trắng**: kiểm WebGL2 trước khi vẽ, bọc khởi tạo trong
  `try/catch`. Nếu thất bại thì hiện hướng dẫn chuyển sang tab 2D.
- **Không phụ thuộc CDN lúc chạy**: bundle JS nằm trong `app/assets/`, nên bảo vệ offline vẫn chạy.

#### Bảng điều khiển 3D

| Điều khiển | Cách làm |
|---|---|
| Chụm theo liên kết | toạ độ gốc từ `spring_layout` của Python, để d3 tự chạy trong `graphData` |
| Tách cụm theo loại | dời cụm về tâm tứ diện, giữ hình dạng cục bộ, co giãn về bán kính `SPREAD` |
| Xếp tầng | như trên nhưng tâm theo trục Y và nén `dy` còn 14% để thành mặt phẳng |
| Bậc ≥ n | lọc `nodes`/`links` rồi nạp lại `graphData`, giữ nguyên chế độ sắp xếp |
| Làm nổi khi rê/bấm | dựng bản đồ kề một lần, tô xám mọi nút ngoài vùng liên quan |

> ⚠️ **Không dùng `d3Force`/`d3ReheatSimulation`** để chỉnh lực đẩy. Hai API này bật
> `engineRunning` mà không bảo đảm `layout` đã dựng, gây `Cannot read properties of
> undefined (reading 'tick')`. Chi tiết ở mục 9.

### 8.3 Kiểm thử

```
15 passed tests/test_graph_view.py          (mới)
53 passed tests/ (trừ test_app_smoke.py)     tổng 60 test thu thập được
```

`test_app_smoke.py` không chạy được **trong sandbox phiên này** (`PermissionError` khi
`tempfile` gọi `chmod`), nhưng đã xác minh riêng bằng `AppTest`: cả chế độ 2D và 3D render
không exception.

### 8.4 Việc còn lại (theo thứ tự ưu tiên)

1. **③ Animation lan truyền theo lớp GNN** (kiểu Distill) — trả lời trực quan câu hỏi
   "GNN khác gì MLP".
2. **④ Scatter 3D chi phí ↔ chất lượng** Federated Learning.

---

## 9. ⚠️ Sự cố pydeck "trắng tinh" — chẩn đoán đầy đủ

Đây là lỗi **tôi đã gây ra và tự sửa**; ghi lại vì nó suýt nữa đã lọt vào bản nộp, và vì
nó tiết lộ một ràng buộc của Streamlit mà tài liệu không nói rõ.

### Triệu chứng

Chọn tab **3D** → khung **trắng hoàn toàn**, không lỗi, không cảnh báo. Tab 2D vẫn bình
thường. `AppTest` báo **không có exception** — nên kiểm thử tự động hoàn toàn không bắt được.

### Cách chẩn đoán

1. Grep bundle deck.gl trong Streamlit (`streamlit/static/static/js/index.*.js`, 2,5 MB,
   tổng static 15,3 MB):

   ```
   OrbitView : 0        ← không có!
   MapView   : 2
   displayName="...View" duy nhất tìm được: MapView
   ```

2. Xem pydeck serialize view thành gì:

   ```json
   "views": [{"@@type": "OrbitView", "controller": true}]
   ```

3. Truy cách Streamlit resolve `@@type`: nó dùng `jsonConverter` (thư viện `j2`) tra vào
   registry `classes`. Registry này được nạp bằng `Object.assign(this.classes, e["views"])`
   với **chỉ** `MapView`.

4. Kết luận: `"@@type": "OrbitView"` tra ra `undefined` → deck.gl không có view hợp lệ →
   canvas rỗng.

### Kiểm chứng đây không phải lỗi dữ liệu

Cùng một `pdk.Deck` xuất ra file HTML riêng (nạp deck.gl 9 từ CDN qua
`@deck.gl/jupyter-widget`) **vẫn vẽ được** — chứng tỏ toạ độ, layer, dữ liệu đều đúng. Chỉ
trong Streamlit là trắng.

### Cách sửa

Thay `pydeck`/`OrbitView` bằng **`3d-force-graph` nhúng qua `st.components.v1.html`**:

- Bundle tự chứa (690 KB, đã gói Three.js) → không cần CDN, app vẫn offline.
- Đánh đổi: iframe sandbox **không trả sự kiện click về Python được**. Trang này chỉ cần
  xem/xoay nên chấp nhận được; muốn tương tác hai chiều phải viết custom component (cần
  `pip install` — đang bị chặn).

### Bài học

Smoke test (`assert not at.exception`) **không đủ** cho visualization. Nó chỉ chứng minh
Python chạy hết, không chứng minh có gì được vẽ. Vì vậy test mới kiểm thêm: bundle JS tồn
tại, mọi cạnh trỏ tới nút có thật, và HTML chứa thông báo lỗi cho người dùng.

### Lỗi runtime thứ hai: `Cannot read properties of undefined (reading 'tick')`

Sau khi thay sang 3d-force-graph, đồ thị vẫn báo lỗi runtime này.

**Truy nguyên trong bundle** — `tickFrame` làm:

```js
t.engineRunning && ( ... t.layout[a ? "tick" : "step"]() ... )
```

`t.layout` **chỉ** được gán bên trong một nhánh của handler `graphData` (nhánh dựng
d3-force/ngraph layout), còn `t.engineRunning = true` thì đặt **vô điều kiện** ở cuối handler.
Nếu nhánh đó không chạy, `engineRunning` bật mà `layout` vẫn `undefined` → frame kế tiếp nổ.

`d3ReheatSimulation()` và `d3Force(...)` đều gọi `resetCountdown()`, tức bật `engineRunning`.
Bản trước dùng cả hai để chỉnh lực đẩy → rơi đúng vào đường dẫn lỗi.

**Cách sửa:** bỏ hoàn toàn API d3. Mọi thay đổi bố cục tính toạ độ ở JS rồi nạp lại qua
`graphData()` — đường này để thư viện tự dựng lại layout bên trong nó. Chỉ dùng 6 method cấp
cao: `graphData`, `nodeColor`, `linkColor`, `onNodeHover`, `onNodeClick`, `zoomToFit`.

Có **2 test canh** việc này: `test_no_unsafe_d3_api_calls` (cấm đúng danh sách API nguy hiểm)
và `test_all_graph_methods_are_verified` (mọi method gọi trên `Graph` phải nằm trong
`ALLOWED_METHODS`).

**Kiểm chứng không dùng trình duyệt:** chạy HTML thật trong `jsdom` với `ForceGraph3D` giả
(để loại WebGL khỏi phương trình), rồi bấm qua cả 4 chế độ:

```
khởi động  | nút=385 cạnh=1915
tách cụm   | nút=385 cạnh=1915
xếp tầng   | nút=385 cạnh=1915
bậc>=5     | nút=309 cạnh=1695
số lỗi runtime: 0
gọi API d3 nguy hiểm: không có
```
