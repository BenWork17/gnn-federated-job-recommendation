"""
Sinh CSS theme sáng + hiệu ứng động cho app.

VÌ SAO DÙNG CSS THAY VÌ API CỦA ALTAIR:
Altair 6.0 đã BỎ phương thức `.transition()` (có ở Altair 5), và Vega-Lite
không chấp nhận `config.animation` trong spec hợp lệ. Vì vậy không thể làm
animation bằng API biểu đồ. Cách duy nhất chạy được với bộ thư viện hiện có
là CSS: mỗi biểu đồ nằm trong một khối có class riêng, và CSS lo hiệu ứng
xuất hiện + chuyển động nhẹ.

NGUYÊN TẮC: hiệu ứng phải TÔN TRỌNG `prefers-reduced-motion` — người dùng đã
bật giảm chuyển động trong hệ điều hành thì không thấy animation. Đây không
chỉ là yêu cầu accessibility mà còn cần thiết khi trình chiếu (máy chiếu
đôi khi làm hiệu ứng nhấp nháy).
"""

from __future__ import annotations

import streamlit as st

# Bảng màu — dùng chung với figures.py để báo cáo và app cùng một "giọng"
BLUE = "#2f6fb5"
RED = "#c0392b"
GREEN = "#27ae60"
ORANGE = "#e67e22"
PURPLE = "#8e44ad"
GREY = "#7f8c8d"

# ---------------------------------------------------------------------
# Hằng số bố cục dùng chung cho các trang.
#
# VÌ SAO CẦN: Streamlit chỉ cho HTML thô đi qua `st.markdown(...,
# unsafe_allow_html=True)`, và mỗi lời gọi markdown là MỘT khối DOM riêng —
# thẻ <div> mở ở lời gọi này KHÔNG bọc được widget ở lời gọi sau. Vì vậy
# không thể "bọc" nội dung Streamlit bằng CSS grid thuần. Hai hằng dưới đây
# để các trang dùng thống nhất cùng một tên class, cùng một chỗ khai báo:
#
#   st.markdown(GRID_2, unsafe_allow_html=True)
#   st.markdown(DIV_END, unsafe_allow_html=True)
#
# Chúng hữu ích nhất khi phần thân giữa hai mốc là HTML tự viết (thẻ số
# liệu, ô phát hiện, chú thích) — lúc đó grid thật sự có tác dụng. Với
# widget Streamlit thuần, hãy tiếp tục dùng `st.columns` (vẫn responsive
# và giữ nguyên hành vi cũ).
# ---------------------------------------------------------------------
GRID_2 = '<div class="lx-grid-2">'
GRID_3 = '<div class="lx-grid-3">'
DIV_END = '</div>'

_CSS = """
<style>
/* ================= Nền và chữ ================= */
.stApp {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafd 100%);
}

/* ================= Khung trang: dùng hết chiều ngang =================
   VẤN ĐỀ ĐÃ SỬA: bản trước đặt `.block-container { max-width: 1250px }`.
   Trên màn 1920px (sidebar đóng) phần nội dung chỉ rộng 1250px, nên mỗi bên
   còn (1920 - 1250) / 2 = 335px trống — nhìn như app bị "bó" vào giữa.
   Cách sửa: cho khung nội dung theo 100% bề rộng còn lại, chỉ chặn trần ở
   màn SIÊU rộng (>= 2200px) để dòng chữ không dài quá mức đọc được.
   Dùng cả `.block-container` và `[data-testid="stMainBlockContainer"]` vì
   Streamlit 1.55 gắn cả hai lên cùng một phần tử; khai báo theo test-id
   giúp không phụ thuộc vào tên class nội bộ của Streamlit.
   ==================================================================== */
.block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 1.25rem !important;
    padding-bottom: 2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
    width: 100% !important;
}
/* Trần hợp lý cho màn siêu rộng: 2000px, canh giữa */
@media (min-width: 2200px) {
    .block-container,
    [data-testid="stMainBlockContainer"] {
        max-width: 2000px !important;
        margin-inline: auto !important;
    }
}
/* Màn hẹp (1024–1366px): bớt padding hai bên để nội dung không bị bó */
@media (max-width: 1366px) {
    .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-left: 1.4rem !important;
        padding-right: 1.4rem !important;
    }
}

/* ================= Khoảng trống dọc ================= */
/* Streamlit mặc định gap 1rem giữa mọi khối dọc; thu lại một chút để nội
   dung lên cao hơn mà không chồng chữ. */
div[data-testid="stVerticalBlock"] { gap: 0.85rem; }
[data-testid="stMetric"] { padding: 0.4rem 0.6rem; }

/* ================= Utility bố cục dùng chung =================
   Cách dùng (xem hằng số GRID_2 / GRID_3 / DIV_END ở cuối file):
       st.markdown(GRID_2, unsafe_allow_html=True)
       ... nội dung ...
       st.markdown(DIV_END, unsafe_allow_html=True)
   ============================================================ */
/* .lx-tight: bỏ khoảng hở phía trên của chính nó và phần tử ngay sau */
.lx-tight { margin-top: 0 !important; margin-bottom: 0 !important; }
.lx-tight + * { margin-top: 0 !important; }

/* .lx-full: ép phần tử (và con trực tiếp) rộng hết khung */
.lx-full,
.lx-full > * { width: 100% !important; max-width: 100% !important; }

/* Lưới tự co: số cột tự giảm khi hẹp, không bao giờ tràn ngang
   (auto-fit + minmax: mỗi cột tối thiểu 420/300px, rộng ra thì chia đều) */
.lx-grid-2,
.lx-grid-3 {
    display: grid;
    gap: 0.85rem;
    width: 100%;
    align-items: start;
    margin: 0.35rem 0 0.15rem 0;
}
.lx-grid-2 { grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); }
.lx-grid-3 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
/* Dưới 900px: một cột, tránh tràn ngang trên laptop nhỏ / tablet */
@media (max-width: 900px) {
    .lx-grid-2,
    .lx-grid-3 { grid-template-columns: 1fr; }
}
/* Nội dung nhét trong lưới không được vượt cột */
.lx-grid-2 > *,
.lx-grid-3 > * { min-width: 0; max-width: 100%; }

/* ĐƯỜNG DÙNG THẬT SỰ HIỆU QUẢ VỚI WIDGET STREAMLIT
   --------------------------------------------------------------
   `st.markdown('<div class="lx-grid-2">')` chỉ tạo MỘT khối rỗng — Streamlit
   đóng thẻ ngay, nên nó KHÔNG bọc được các widget gọi sau. Muốn lưới bọc
   thật thì dùng container có khoá:

       with st.container(key="lx-grid-2-a"):
           st.metric(...)
           st.metric(...)

   Streamlit 1.55 gắn khoá thành class `.st-key-<key>` lên chính khối dọc,
   nên các selector dưới đây biến khối đó thành lưới. Dùng `[class*=...]`
   để khoá có hậu tố tuỳ ý (a, b, 1, 2...) mà vẫn khớp. */
div[data-testid="stVerticalBlock"][class*="st-key-lx-grid-2"] {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 0.85rem;
    align-items: start;
}
div[data-testid="stVerticalBlock"][class*="st-key-lx-grid-3"] {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 0.85rem;
    align-items: start;
}
@media (max-width: 900px) {
    div[data-testid="stVerticalBlock"][class*="st-key-lx-grid-2"],
    div[data-testid="stVerticalBlock"][class*="st-key-lx-grid-3"] {
        grid-template-columns: 1fr;
    }
}
div[data-testid="stVerticalBlock"][class*="st-key-lx-grid-2"] > *,
div[data-testid="stVerticalBlock"][class*="st-key-lx-grid-3"] > * {
    min-width: 0;
    max-width: 100%;
}


/* ================= Thẻ số liệu ================= */
@keyframes riseIn {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
.hx-card {
    animation: riseIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
    transition: transform 0.18s ease, box-shadow 0.18s ease,
                border-color 0.18s ease;
}
.hx-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 22px rgba(47, 111, 181, 0.16);
    border-color: #b9cde6 !important;
}

/* Số lớn trong thẻ: trượt lên + phóng nhẹ để mắt bắt được con số */
@keyframes numberPop {
    0%   { opacity: 0; transform: translateY(14px) scale(0.94); }
    60%  { opacity: 1; transform: translateY(-2px) scale(1.015); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}
.hx-metric {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.5px;
    animation: numberPop 0.62s cubic-bezier(0.22, 1, 0.36, 1) both;
    font-variant-numeric: tabular-nums;   /* số không nhảy bề rộng */
}

/* ================= Ô nêu phát hiện ================= */
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-14px); }
    to   { opacity: 1; transform: translateX(0); }
}
.hx-finding {
    animation: slideInLeft 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
    transition: box-shadow 0.2s ease;
}
.hx-finding:hover { box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08); }

/* ================= Khung câu hỏi đầu trang ================= */
@keyframes fadeDown {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.hx-question { animation: fadeDown 0.4s ease both; }

/* ================= Biểu đồ ================= */
/* Mỗi biểu đồ được bọc trong div.hx-chart -> hiệu ứng xuất hiện so le */
@keyframes chartGrow {
    from { opacity: 0; transform: scale(0.985); }
    to   { opacity: 1; transform: scale(1); }
}
.hx-chart {
    animation: chartGrow 0.55s ease both;
    border-radius: 10px;
    transition: box-shadow 0.2s ease;
}
.hx-chart:hover { box-shadow: 0 3px 14px rgba(47, 111, 181, 0.10); }

/* Altair nhúng SVG/Canvas: làm tròn + nền trắng để hợp theme sáng */
.hx-chart .stVegaLiteChart,
.hx-chart [data-testid="stVegaLiteChart"] {
    background: #ffffff;
    border-radius: 10px;
}

/* Đường và cột của Vega mượt hơn khi dữ liệu đổi (Streamlit vẽ lại) */
.hx-chart canvas, .hx-chart svg { transition: opacity 0.25s ease; }

/* ================= Thanh bên ================= */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f6f8fb 0%, #eef3f9 100%);
    border-right: 1px solid #e3e8ef;
}
/* Sidebar mặc định của Streamlit 1.55 đã là 300px (DEFAULT_WIDTH="300",
   kéo được trong khoảng 200–600px), nền tảng này "vừa" rồi — nội dung hai
   bên không dính sát vì `.block-container` giữ padding 2rem. Chỉ chặn sàn
   để không ai kéo hẹp đến mức nhãn điều hướng xuống dòng.
   QUAN TRỌNG: phải kèm `[aria-expanded="true"]`. Lỗi đã đo được khi thiếu
   điều kiện này: min-width áp cả lên sidebar ĐANG ĐÓNG, nên nó vẫn chiếm
   290px bên trái dù người dùng đã đóng — đúng khoảng trống cần xoá. */
@media (min-width: 1200px) {
    [data-testid="stSidebar"][aria-expanded="true"] { min-width: 290px !important; }
}
[data-testid="stSidebar"] a {
    transition: background 0.15s ease, color 0.15s ease;
    border-radius: 8px;
}
[data-testid="stSidebar"] a:hover { background: #e4edf8; }

/* ================= Nút ================= */
.stButton > button {
    transition: transform 0.12s ease, box-shadow 0.18s ease,
                background 0.18s ease;
    font-weight: 600;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 5px 14px rgba(47, 111, 181, 0.22);
}
.stButton > button:active { transform: translateY(0); }

/* ================= Bảng dữ liệu ================= */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #e3e8ef;
    overflow: hidden;
    animation: chartGrow 0.4s ease both;
}

/* ================= Thanh tiến trình / slider ================= */
.stSlider [data-baseweb="slider"] div[role="slider"] {
    box-shadow: 0 0 0 3px rgba(47, 111, 181, 0.18);
    transition: box-shadow 0.15s ease;
}

/* ================= Nhịp đập cho cảnh báo ================= */
@keyframes pulseRing {
    0%   { box-shadow: 0 0 0 0 rgba(192, 57, 43, 0.34); }
    70%  { box-shadow: 0 0 0 12px rgba(192, 57, 43, 0); }
    100% { box-shadow: 0 0 0 0 rgba(192, 57, 43, 0); }
}
.hx-alert-live { animation: pulseRing 1.8s infinite; }

/* ================= Tôn trọng người dùng giảm chuyển động ================= */
@media (prefers-reduced-motion: reduce) {
    .hx-card, .hx-finding, .hx-question, .hx-chart, .hx-metric,
    [data-testid="stDataFrame"], .hx-alert-live {
        animation: none !important;
        transition: none !important;
    }
}

/* =====================================================================
   TRANG "ĐỒ THỊ VIỆC LÀM" — hero section (bố cục mới)
   ---------------------------------------------------------------------
   Toàn bộ dưới đây là class MỚI, tiền tố `gx-` (graph experience), thêm
   cho bố cục hero của trang Đồ thị việc làm. KHÔNG sửa rule cũ nào ở
   trên: các trang khác vẫn dùng nguyên `.hx-*` / `.lx-*`.

   VÌ SAO PHẢI VIẾT CSS RIÊNG: Streamlit chỉ cho HTML thô đi qua
   `st.markdown(..., unsafe_allow_html=True)`, nên 4 thẻ số liệu và bảng
   chi tiết phải tự "mang" giao diện theo. Nếu để mặc định thì chúng là
   chữ trần, không phân biệt được với nội dung khác.
   ===================================================================== */

/* --- Tiêu đề gọn: h1 nhỏ hơn mặc định để đồ thị lên cao hơn --------- */
.gx-title {
    font-size: 1.9rem;
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: -0.4px;
    margin: 0 0 0.55rem 0;
    color: #1f2733;
}

/* --- Khung chứa đồ thị hero: viền mảnh, bo góc, nền trắng ---------- */
div[data-testid="stVerticalBlock"][class*="st-key-gx-graph-card"] {
    border: 1px solid #e3e8ef;
    border-radius: 12px;
    background: #ffffff;
    padding: 0;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(31, 39, 51, 0.06);
}
/* iframe của components.html phải khít khung, không để hở nền xám */
div[data-testid="stVerticalBlock"][class*="st-key-gx-graph-card"] iframe {
    display: block;
    border: 0;
    width: 100%;
}

/* --- Tỉ lệ hai cột của HERO: đồ thị rộng, panel phải GỌN -------------
   VÌ SAO CẦN: `st.columns` chỉ nhận TỈ LỆ. Tỉ lệ [4, 1] cho cột phải
   355px ở màn 1920px — quá rộng, đồ thị mất 355px chiều ngang trong khi
   người dùng yêu cầu "4 con số thu nhỏ thành 4 thẻ nhỏ nằm bên phải".
   Tỉ lệ cố định cũng sai khi mở/đóng sidebar (khung nội dung đổi từ
   1556px sang 1856px). Vì vậy chặn cột phải bằng px + media query.

   BÁM VÀO ĐÂU: khối `st.columns` của hero được nhận diện qua `:has()` trên
   khoá `.st-key-gx-graph-card` (khoá này CÓ trong DOM — đã đo). Không bọc
   hero trong `st.container(key=...)`: Streamlit render container chứa
   columns thành `stLayoutWrapper` KHÔNG mang class khoá (đã đo trong DOM).
   Chưa có fallback cho trình duyệt thiếu `:has()` (Chrome 105+, Safari 15.4+,
   Firefox 121+ đều có) — khi thiếu, tỉ lệ dự phòng [1, 0.2] vẫn dùng được,
   chỉ là cột phải rộng hơn ý muốn.
   ==================================================================== */
div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card) {
    display: flex !important;
    /* LỖI ĐÃ SỬA — cột phải bị đẩy XUỐNG DƯỚI đồ thị khi sidebar mở.
       Streamlit đặt `flex-wrap: wrap` trên stHorizontalBlock. Ràng buộc
       `flex: 0 0 300px` cho cột phải là KHÔNG ĐỦ: cột trái (đồ thị) vẫn
       giữ `width` theo tỉ lệ cột của Streamlit (1540px ở sidebar mở), nên
       1540 + 300 + gap > 1540 khả dụng -> wrap -> 4 thẻ rơi xuống dưới.
       Đo được: sidebar MỞ thì thẻ ở top=889 (DƯỚI), sidebar ĐÓNG (blockW
       1839) thì đúng bên phải — nên ảnh chụp lúc đóng trông như đã ổn.
       `nowrap` + `flex-basis: 0` cho cột trái mới ép được hai cột nằm ngang. */
    flex-wrap: nowrap !important;
    align-items: flex-start;
    gap: 1.1rem;
}
div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card) > div {
    min-width: 0;
}
/* Cột TRÁI (chứa đồ thị) co giãn hết phần còn lại.
   `flex-basis: 0` (không phải `auto`) để nó KHÔNG đòi đủ bề rộng tỉ lệ
   Streamlit ban cho — đó chính là nguyên nhân gây wrap. */
div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card) > div:first-child {
    flex: 1 1 0 !important;
    width: auto !important;
    max-width: none !important;
    min-width: 0 !important;
}
/* Cột PHẢI (4 thẻ + panel) rộng cố định, KHÔNG co theo tỉ lệ */
div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card) > div:last-child {
    flex: 0 0 280px !important;
    width: 280px !important;
    max-width: 280px !important;
}
/* Màn rộng: cho panel phải 300px (đồ thị vẫn thừa chỗ) */
@media (min-width: 1800px) {
    div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card) > div:last-child {
        flex: 0 0 300px !important;
        width: 300px !important;
        max-width: 300px !important;
    }
}
/* Màn hẹp: thu còn 250px để đồ thị không bị bóp */
@media (max-width: 1366px) {
    div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card) > div:last-child {
        flex: 0 0 250px !important;
        width: 250px !important;
        max-width: 250px !important;
    }
}
/* Rất hẹp: bỏ cạnh nhau, panel phải xuống DƯỚI đồ thị cho khỏi tràn chữ */
@media (max-width: 1000px) {
    div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card) {
        flex-direction: column;
    }
    div[data-testid="stHorizontalBlock"]:has(.st-key-gx-graph-card) > div:last-child {
        flex: 1 1 auto !important;
        width: 100% !important;
        max-width: 100% !important;
        margin-top: 0.6rem;
    }
}

/* --- 4 thẻ số liệu THU NHỎ (xếp dọc ở cột phải) --------------------- */
.gx-mini-card {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 8px;
    line-height: 1.25;
}
.gx-mini-val {
    font-size: 18px;
    font-weight: 700;
    color: #1f2733;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;   /* số không nhảy bề rộng */
}
.gx-mini-lab {
    font-size: 11px;
    color: #7f8c8d;
    margin-top: 2px;
}
/* Hai vạch màu nhỏ để phân biệt cạnh công khai / riêng tư */
.gx-mini-card.is-public { border-left: 3px solid #2f6fb5; }
.gx-mini-card.is-private { border-left: 3px solid #c0392b; }

/* --- Bảng chi tiết nút (cột phải) ----------------------------------- */
.gx-panel {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-left: 4px solid #2f6fb5;
    border-radius: 0 8px 8px 0;
    padding: 9px 11px;
    margin: 0.35rem 0 0.5rem 0;
    animation: fadeDown 0.3s ease both;
}
.gx-panel-kind {
    font-size: 11px;
    font-weight: 700;
    color: #5b6675;
}
.gx-panel-name {
    font-size: 14px;
    font-weight: 700;
    line-height: 1.35;
    margin: 4px 0 3px 0;
    color: #111824;
    overflow-wrap: anywhere;
}
.gx-panel-meta {
    font-size: 11px;
    color: #5b6675;
}

/* --- Tiêu đề phụ trong cột phải ------------------------------------- */
.gx-side-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #7f8c8d;
    margin: 0.5rem 0 0.3rem 0;
}

/* --- Một dòng láng giềng ------------------------------------------- */
.gx-nbr {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    padding: 3px 4px;
    border-radius: 6px;
    transition: background 0.12s ease;
}
.gx-nbr:hover { background: #eef4fb; }
.gx-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex: 0 0 auto;
}
.gx-hit-kind {
    flex: 0 0 auto;
    font-size: 10px;
    color: #7f8c8d;
}
.gx-hint {
    font-size: 11px;
    color: #7f8c8d;
    line-height: 1.5;
    padding: 4px 2px;
}

/* --- Nút bấm trong danh sách kết quả tìm kiếm ----------------------- */
/* Cột phải hẹp (~300px) nên nút phải canh trái và cắt chữ bằng ellipsis,
   nếu không nhãn dài của tin tuyển dụng sẽ xuống 3–4 dòng. */
div[data-testid="stVerticalBlock"] [class*="st-key-gx-hit-"] button {
    justify-content: flex-start;
    text-align: left;
    padding: 3px 8px;
    min-height: 1.9rem;
    font-size: 12px;
    font-weight: 500;
    border-color: #e9eef5;
}
div[data-testid="stVerticalBlock"] [class*="st-key-gx-hit-"] button p {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
/* Màn hẹp: 4 thẻ số liệu và cột phải xếp DỌC lên trên đồ thị.
   Dùng `flex-direction: column` trên khối cột của Streamlit. */
@media (max-width: 1100px) {
    .gx-mini-card { margin-bottom: 6px; }
}
@media (prefers-reduced-motion: reduce) {
    .gx-panel, .gx-nbr { animation: none !important; transition: none !important; }
}
</style>
"""


def inject_theme() -> None:
    """Chèn CSS một lần cho mỗi lần render trang."""
    st.markdown(_CSS, unsafe_allow_html=True)


def chart_block_open(delay_ms: int = 0, key: str = "") -> None:
    """Mở khối bọc biểu đồ. delay_ms tạo hiệu ứng xuất hiện so le."""
    st.markdown(
        f"<div class='hx-chart' style='animation-delay:{delay_ms}ms'>",
        unsafe_allow_html=True,
    )


def chart_block_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Bọc lưới cho WIDGET Streamlit (cách dùng thật sự hiệu quả)
# ---------------------------------------------------------------------
def grid(cols: int, key: str):
    """Trả về container dạng LƯỚI, dùng được với `with`.

    VÌ SAO KHÔNG DÙNG GRID_2/DIV_END CHO WIDGET:
    `st.markdown('<div class="lx-grid-2">')` tạo một khối HTML RỖNG rồi đóng
    ngay; các widget gọi sau nằm ngoài div đó nên lưới không bọc được gì.
    Cách duy nhất hoạt động là container có khoá — Streamlit gắn khoá thành
    class `.st-key-<key>`, và CSS ở trên biến đúng khối đó thành lưới.

    Dùng:
        with grid(3, "the-so-lieu"):
            st.metric(...)
            st.metric(...)
            st.metric(...)

    Không có media query riêng cần viết thêm: `auto-fit` + `minmax` trong
    CSS tự hạ số cột khi màn hẹp, nên 1024px vẫn không tràn ngang.
    """
    n = 2 if int(cols) <= 2 else 3
    return st.container(key=f"lx-grid-{n}-{key}")

