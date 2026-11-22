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

# Bảng màu White + Signal Orange design system
ORANGE = "#FF5A1F"
ORANGE_DARK = "#C2410C"
INK = "#0F172A"
SKY = "#0EA5E9"
BLUE = SKY
RED = "#EF4444"
GREEN = "#10B981"
WARN = "#F59E0B"
PURPLE = "#8B5CF6"
GREY = "#64748B"

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
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap');

@property --beam-angle {
    syntax: "<angle>";
    initial-value: 0deg;
    inherits: false;
}
@keyframes beamSpin {
    from { --beam-angle: 0deg; }
    to   { --beam-angle: 360deg; }
}

/* ================= Nền và chữ ================= */
.stApp {
    font-family: 'Plus Jakarta Sans', 'Plex Sans', system-ui, -apple-system, sans-serif;
    background-color: #F8FAFC;
    background-image:
        radial-gradient(circle at 82% 8%, rgba(255, 90, 31, 0.16), transparent 42%),
        radial-gradient(circle at 10% 42%, rgba(251, 146, 60, 0.12), transparent 38%),
        radial-gradient(circle at 76% 88%, rgba(253, 186, 116, 0.14), transparent 44%),
        radial-gradient(#CBD5E1 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 100% 100%, 24px 24px;
}
h1, [data-testid="stTitle"] {
    font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif;
    letter-spacing: -0.035em;
    font-weight: 700;
    color: #0F172A;
}
h2, h3 {
    font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif;
    letter-spacing: -0.02em;
    font-weight: 700;
    color: #0F172A;
    margin-top: 0.4rem;
}
hr {
    margin: 1rem 0 !important;
    border-color: rgba(203, 213, 225, 0.7) !important;
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
    background: rgba(255, 255, 255, 0.66);
    backdrop-filter: blur(18px) saturate(175%);
    -webkit-backdrop-filter: blur(18px) saturate(175%);
    border: 1px solid rgba(255, 255, 255, 0.92);
    border-top: 2px solid #FF5A1F;
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(15, 23, 42, 0.05),
        0 12px 32px -10px rgba(15, 23, 42, 0.08);
    transform-style: preserve-3d;
    animation: riseIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
    transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
                box-shadow 0.3s ease,
                border-color 0.2s ease;
}
.hx-card:hover {
    transform: perspective(900px) rotateX(1.5deg) rotateY(-1.5deg) translateY(-3px);
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(255, 90, 31, 0.28),
        0 18px 38px -12px rgba(255, 90, 31, 0.20);
    border-color: #FDBA74 !important;
}

/* Số lớn trong thẻ: trượt lên + phóng nhẹ để mắt bắt được con số */
@keyframes numberPop {
    0%   { opacity: 0; transform: translateY(14px) scale(0.94); }
    60%  { opacity: 1; transform: translateY(-2px) scale(1.015); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}
.hx-metric {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.85rem;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.035em;
    transform: translateZ(8px);
    animation: numberPop 0.62s cubic-bezier(0.22, 1, 0.36, 1) both;
    font-variant-numeric: tabular-nums;   /* số không nhảy bề rộng */
}

/* ================= Bento Hero + Architectural Glass Cards ============== */
.hx-bento-hero {
    position: relative;
    border-radius: 14px;
    padding: 1.35rem 1.45rem;
    background: rgba(255, 255, 255, 0.68);
    backdrop-filter: blur(18px) saturate(175%);
    -webkit-backdrop-filter: blur(18px) saturate(175%);
    border: 1px solid rgba(255, 255, 255, 0.92);
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(15, 23, 42, 0.05),
        0 14px 36px -10px rgba(15, 23, 42, 0.09);
    transform-style: preserve-3d;
    animation: riseIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
    transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.3s ease;
    overflow: hidden;
}
.hx-bento-hero::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    padding: 1.5px;
    background: conic-gradient(from var(--beam-angle), transparent 72%, #FB923C 86%, #FF5A1F 95%, transparent 100%);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    pointer-events: none;
    animation: beamSpin 6s linear infinite;
}
.hx-bento-hero:hover {
    transform: perspective(900px) rotateX(1.5deg) rotateY(-1.5deg) translateY(-3px);
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(255, 90, 31, 0.22),
        0 20px 42px -12px rgba(255, 90, 31, 0.18);
}
.hx-kicker {
    font-family: 'JetBrains Mono', 'Plex Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #C2410C;
    margin-bottom: 0.45rem;
}
.hx-hero-row {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 0.9rem;
}
.hx-hero-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 3.1rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.04em;
    color: #0F172A;
    font-variant-numeric: tabular-nums;
    transform: translateZ(8px);
}
.hx-pill-orange {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.76rem;
    font-weight: 600;
    color: #C2410C;
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-radius: 999px;
    padding: 0.25rem 0.65rem;
}
.hx-track-list {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    margin-top: 0.35rem;
}
.hx-track-item {
    display: grid;
    grid-template-columns: 120px 1fr 52px;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.8rem;
}
.hx-track-lbl {
    color: #475569;
    font-weight: 600;
}
.hx-track-bar-bg {
    height: 8px;
    background: rgba(226, 232, 240, 0.7);
    border-radius: 999px;
    overflow: hidden;
}
.hx-track-bar-fill {
    height: 100%;
    border-radius: 999px;
}
.hx-track-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    font-weight: 600;
    color: #0F172A;
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.hx-bento-tile {
    border-radius: 12px;
    padding: 1rem 1.15rem;
    margin-bottom: 0.75rem;
    background: rgba(255, 255, 255, 0.66);
    backdrop-filter: blur(18px) saturate(175%);
    -webkit-backdrop-filter: blur(18px) saturate(175%);
    border: 1px solid rgba(255, 255, 255, 0.92);
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(15, 23, 42, 0.05),
        0 12px 32px -10px rgba(15, 23, 42, 0.08);
    transform-style: preserve-3d;
    animation: riseIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
    transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.3s ease, border-color 0.2s ease;
}
.hx-bento-tile:hover {
    transform: perspective(900px) rotateX(1.5deg) rotateY(-1.5deg) translateY(-3px);
    border-color: #FDBA74 !important;
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(255, 90, 31, 0.25),
        0 18px 36px -12px rgba(255, 90, 31, 0.16);
}
.hx-tile-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: #0F172A;
    font-variant-numeric: tabular-nums;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}
.hx-tile-sub {
    font-size: 0.82rem;
    color: #475569;
    margin-top: 0.25rem;
    line-height: 1.4;
}
.hx-editorial-card {
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
    background: rgba(255, 255, 255, 0.66);
    backdrop-filter: blur(18px) saturate(175%);
    -webkit-backdrop-filter: blur(18px) saturate(175%);
    border: 1px solid rgba(255, 255, 255, 0.92);
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(15, 23, 42, 0.05),
        0 12px 32px -10px rgba(15, 23, 42, 0.08);
    height: 100%;
}
.hx-editorial-body {
    font-size: 0.88rem;
    line-height: 1.55;
    color: #334155;
    margin-top: 0.35rem;
}
.hx-split-pill {
    display: flex;
    height: 10px;
    border-radius: 999px;
    overflow: hidden;
    margin: 0.75rem 0 0.5rem;
    background: #E2E8F0;
}

/* ================= Ô nêu phát hiện ================= */
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-14px); }
    to   { opacity: 1; transform: translateX(0); }
}
.hx-finding {
    background: rgba(255, 255, 255, 0.66);
    backdrop-filter: blur(18px) saturate(175%);
    -webkit-backdrop-filter: blur(18px) saturate(175%);
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(15, 23, 42, 0.05),
        0 12px 32px -10px rgba(15, 23, 42, 0.08);
    animation: slideInLeft 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
    transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
                box-shadow 0.25s ease,
                border-color 0.2s ease;
}
.hx-finding:hover {
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 10px 24px -8px rgba(15, 23, 42, 0.10);
}

/* ================= Khung câu hỏi đầu trang ================= */
@keyframes fadeDown {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.hx-question {
    background: rgba(255, 247, 237, 0.88) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow:
        inset 0 1px 0 0 rgba(255, 255, 255, 0.95),
        0 1px 2px rgba(15, 23, 42, 0.04),
        0 8px 20px -6px rgba(249, 115, 22, 0.08);
    animation: fadeDown 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
}

/* ================= Biểu đồ ================= */
/* Mỗi biểu đồ được bọc trong div.hx-chart -> hiệu ứng xuất hiện so le */
@keyframes chartGrow {
    from { opacity: 0; transform: scale(0.985); }
    to   { opacity: 1; transform: scale(1); }
}
.hx-chart {
    animation: chartGrow 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
    border: 1px solid rgba(255, 255, 255, 0.92);
    border-radius: 12px;
    padding: 0.4rem;
    background: rgba(255, 255, 255, 0.66);
    backdrop-filter: blur(18px) saturate(175%);
    -webkit-backdrop-filter: blur(18px) saturate(175%);
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(15, 23, 42, 0.05),
        0 12px 32px -10px rgba(15, 23, 42, 0.08);
    transition: box-shadow 0.25s ease, border-color 0.2s ease;
}
.hx-chart:hover {
    border-color: #FDBA74;
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 10px 24px -8px rgba(249, 115, 22, 0.12);
}

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
    background: rgba(248, 250, 252, 0.88);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-right: 1px solid #E2E8F0;
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
/* Luôn hiển thị nút đóng/mở sidebar gốc của Streamlit (mặc định chỉ hiện khi hover) */
[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] {
    opacity: 1 !important;
    visibility: visible !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stExpandSidebarButton"] button,
[data-testid="collapsedControl"] button {
    background: #FFFFFF !important;
    border: 1px solid #FED7AA !important;
    border-radius: 8px !important;
    color: #C2410C !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08) !important;
    transition: background 0.15s ease, transform 0.15s ease !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stExpandSidebarButton"] button:hover,
[data-testid="collapsedControl"] button:hover {
    background: #FFF7ED !important;
    border-color: #FF5A1F !important;
    transform: scale(1.05);
}
/* Nút Thu nhỏ / Mở rộng thanh taskbar bên trái (chế độ Mini Icon-Rail) */
div[class*="st-key-sb-toggle-wrap"] button {
    background: #FFF7ED !important;
    border: 1px solid #FED7AA !important;
    color: #C2410C !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    padding: 0.35rem 0.65rem !important;
    min-height: 2.1rem !important;
    border-radius: 8px !important;
}
div[class*="st-key-sb-toggle-wrap"] button:hover {
    background: #FFEDD5 !important;
    border-color: #FF5A1F !important;
}
[data-testid="stSidebarNav"]::before {
    content: "ĐIỀU HƯỚNG";
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #64748B;
    padding: 0 0.75rem 0.45rem;
    display: block;
}
[data-testid="stSidebarNavLink"] {
    border-radius: 8px;
    padding: 0.48rem 0.75rem;
    margin: 2px 0.5rem;
    color: #475569;
    font-weight: 500;
    position: relative;
    transition: background 0.15s ease, color 0.15s ease;
}
[data-testid="stSidebarNavLink"]:hover {
    background: #FFF7ED !important;
    color: #0F172A !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: #FFF7ED !important;
    color: #C2410C !important;
    font-weight: 600 !important;
    box-shadow: inset 3px 0 0 #F97316;
}
[data-testid="stSidebarNavLink"][aria-current="page"] span {
    color: #C2410C !important;
    font-weight: 600 !important;
}

/* --- Custom 2D Stroke Icons (24x24, 1.8px stroke) via CSS mask-image --- */
[data-testid="stSidebarNavItems"] li a::before {
    content: "";
    width: 17px;
    height: 17px;
    flex: 0 0 17px;
    margin-right: 0.6rem;
    background-color: #64748B;
    -webkit-mask-size: contain;
    mask-size: contain;
    -webkit-mask-repeat: no-repeat;
    mask-repeat: no-repeat;
    -webkit-mask-position: center;
    mask-position: center;
    transition: background-color 0.15s ease;
}
[data-testid="stSidebarNavItems"] li a:hover::before {
    background-color: #0F172A;
}
[data-testid="stSidebarNavItems"] li a[aria-current="page"]::before {
    background-color: #EA580C;
}
/* 1. Tổng quan — Dashboard Grid */
[data-testid="stSidebarNavItems"] li:nth-child(1) a::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='7' height='9' rx='1.5'/%3E%3Crect x='14' y='3' width='7' height='5' rx='1.5'/%3E%3Crect x='14' y='12' width='7' height='9' rx='1.5'/%3E%3Crect x='3' y='16' width='7' height='5' rx='1.5'/%3E%3C/svg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='7' height='9' rx='1.5'/%3E%3Crect x='14' y='3' width='7' height='5' rx='1.5'/%3E%3Crect x='14' y='12' width='7' height='9' rx='1.5'/%3E%3Crect x='3' y='16' width='7' height='5' rx='1.5'/%3E%3C/svg%3E");
}
/* 2. Đồ thị việc làm — Graph Nodes */
[data-testid="stSidebarNavItems"] li:nth-child(2) a::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='5' r='2.5'/%3E%3Ccircle cx='5.5' cy='18' r='2.5'/%3E%3Ccircle cx='18.5' cy='18' r='2.5'/%3E%3Cpath d='M10.8 7.2 6.7 15.8M13.2 7.2l4.1 8.6M8 18h8'/%3E%3C/svg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='5' r='2.5'/%3E%3Ccircle cx='5.5' cy='18' r='2.5'/%3E%3Ccircle cx='18.5' cy='18' r='2.5'/%3E%3Cpath d='M10.8 7.2 6.7 15.8M13.2 7.2l4.1 8.6M8 18h8'/%3E%3C/svg%3E");
}
/* 3. Federated Learning simulation — Sync Cycle */
[data-testid="stSidebarNavItems"] li:nth-child(3) a::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'/%3E%3Cpath d='M3 3v5h5'/%3E%3Cpath d='M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16'/%3E%3Cpath d='M16 16h5v5'/%3E%3C/svg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'/%3E%3Cpath d='M3 3v5h5'/%3E%3Cpath d='M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16'/%3E%3Cpath d='M16 16h5v5'/%3E%3C/svg%3E");
}
/* 4. Gợi ý cho ứng viên — Target Match */
[data-testid="stSidebarNavItems"] li:nth-child(4) a::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='9'/%3E%3Ccircle cx='12' cy='12' r='5'/%3E%3Ccircle cx='12' cy='12' r='1.5'/%3E%3C/svg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='9'/%3E%3Ccircle cx='12' cy='12' r='5'/%3E%3Ccircle cx='12' cy='12' r='1.5'/%3E%3C/svg%3E");
}
/* 5. Giám sát node FL — Node Monitor */
[data-testid="stSidebarNavItems"] li:nth-child(5) a::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='4' width='18' height='7' rx='2'/%3E%3Crect x='3' y='13' width='18' height='7' rx='2'/%3E%3Cpath d='M7 7.5h.01M7 16.5h.01M11 7.5h6M11 16.5h6'/%3E%3C/svg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='4' width='18' height='7' rx='2'/%3E%3Crect x='3' y='13' width='18' height='7' rx='2'/%3E%3Cpath d='M7 7.5h.01M7 16.5h.01M11 7.5h6M11 16.5h6'/%3E%3C/svg%3E");
}
/* 6. Kết luận & hạn chế — Report Clipboard */
[data-testid="stSidebarNavItems"] li:nth-child(6) a::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='8' y='2' width='8' height='4' rx='1'/%3E%3Cpath d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/%3E%3Cpath d='M9 12h6M9 16h4'/%3E%3C/svg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='8' y='2' width='8' height='4' rx='1'/%3E%3Cpath d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/%3E%3Cpath d='M9 12h6M9 16h4'/%3E%3C/svg%3E");
}

/* --- Framed Sidebar Footer Card --- */
.sb-footer {
    background: rgba(255, 255, 255, 0.84);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(226, 232, 240, 0.9);
    border-radius: 10px;
    padding: 0.75rem 0.85rem;
    margin-top: 0.75rem;
    box-shadow:
        inset 0 1px 0 0 rgba(255, 255, 255, 0.95),
        0 1px 2px rgba(15, 23, 42, 0.04),
        0 8px 20px -6px rgba(15, 23, 42, 0.06);
}
.sb-footer-title {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.82rem;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 0.35rem;
}
.sb-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #F97316;
    display: inline-block;
    flex: 0 0 auto;
}
.sb-footer-authors {
    font-size: 0.76rem;
    line-height: 1.45;
    color: #475569;
    margin-bottom: 0.5rem;
}
.sb-footer-badge {
    display: inline-block;
    font-size: 0.71rem;
    font-weight: 600;
    color: #C2410C;
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-radius: 6px;
    padding: 0.2rem 0.5rem;
}

/* ================= Nút & Page Link ================= */
.stButton > button {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    color: #0F172A;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85), 0 1px 2px rgba(15, 23, 42, 0.05);
    transition: transform 0.18s cubic-bezier(0.22, 1, 0.36, 1),
                box-shadow 0.18s ease,
                border-color 0.18s ease,
                background 0.18s ease;
    font-weight: 600;
}
.stButton > button:hover {
    transform: translateY(-1px);
    background: #FFF7ED;
    border-color: #FDBA74;
    color: #C2410C;
    box-shadow: 0 6px 14px -3px rgba(255, 90, 31, 0.18);
}
.stButton > button:active {
    transform: translateY(1px) scale(0.985);
    box-shadow: inset 0 2px 4px rgba(15, 23, 42, 0.12);
    transition-duration: 0.08s;
}
.stButton > button[kind="primary"],
[data-testid="baseButton-primary"] {
    background: linear-gradient(180deg, #FF5A1F 0%, #EA580C 100%) !important;
    border-color: #EA580C !important;
    color: #FFFFFF !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.32), 0 2px 6px -1px rgba(234, 88, 12, 0.28);
}
.stButton > button[kind="primary"]:hover,
[data-testid="baseButton-primary"]:hover {
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35), 0 8px 18px -4px rgba(255, 90, 31, 0.38);
}
[data-testid="stPageLink-NavLink"] {
    background: rgba(255, 255, 255, 0.72);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 0.48rem 0.85rem;
    font-weight: 600;
    color: #0F172A;
    box-shadow: inset 0 1px 0 #FFFFFF, 0 1px 2px rgba(15, 23, 42, 0.04);
    transition: transform 0.18s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.18s ease, background 0.18s ease;
}
[data-testid="stPageLink-NavLink"]:hover {
    transform: translateY(-1px);
    background: #FFF7ED;
    border-color: #FDBA74;
    color: #C2410C;
}

/* ================= shadcn / BaseWeb Inputs & Selects ================= */
[data-baseweb="input"],
[data-baseweb="textarea"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.03);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
[data-baseweb="input"]:focus-within,
[data-baseweb="textarea"]:focus-within {
    border-color: #FF5A1F !important;
    box-shadow: 0 0 0 3px rgba(255, 90, 31, 0.14) !important;
}
[data-baseweb="select"] > div {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
[data-baseweb="select"] > div:focus-within {
    border-color: #FF5A1F !important;
    box-shadow: 0 0 0 3px rgba(255, 90, 31, 0.14) !important;
}
[data-baseweb="tag"] {
    background: #FFF7ED !important;
    color: #C2410C !important;
    border: 1px solid #FED7AA !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
[data-baseweb="popover"] > div {
    background: rgba(255, 255, 255, 0.94) !important;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    box-shadow: 0 12px 30px -8px rgba(15, 23, 42, 0.14) !important;
}
[data-baseweb="popover"] li:hover {
    background: #FFF7ED !important;
    color: #C2410C !important;
}

/* ================= Vercel / shadcn Segmented Tabs ================= */
[data-baseweb="tab-list"] {
    background: rgba(241, 245, 249, 0.85);
    padding: 4px;
    border-radius: 10px;
    border: 1px solid #E2E8F0;
    gap: 4px;
}
[data-baseweb="tab"] {
    border-radius: 7px !important;
    padding: 0.42rem 0.95rem !important;
    color: #475569 !important;
    font-weight: 500 !important;
    border-bottom: none !important;
    transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}
[data-baseweb="tab"]:hover {
    color: #0F172A !important;
}
[data-baseweb="tab"][aria-selected="true"] {
    background: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), inset 0 -2px 0 #FF5A1F !important;
}
[data-baseweb="tab-highlight"] {
    display: none !important;
}

/* ================= Frosted Glass Expanders & Alerts ================= */
[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.72);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    box-shadow: inset 0 1px 0 #FFFFFF, 0 4px 14px -6px rgba(15, 23, 42, 0.06);
    transition: border-color 0.2s ease;
}
[data-testid="stExpander"]:hover {
    border-color: #FDBA74 !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600;
    color: #0F172A;
}
[data-testid="stAlert"] {
    background: rgba(255, 255, 255, 0.82) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    box-shadow: inset 0 1px 0 #FFFFFF, 0 4px 14px -6px rgba(15, 23, 42, 0.06);
}

/* ================= Radios, Checkboxes & Sliders ================= */
[data-baseweb="radio"] input:checked + div,
[data-baseweb="checkbox"] input:checked + div {
    border-color: #FF5A1F !important;
    background-color: #FF5A1F !important;
}
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: #FFFFFF !important;
    border: 2px solid #FF5A1F !important;
    box-shadow: 0 0 0 3px rgba(255, 90, 31, 0.16);
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}
.stSlider [data-baseweb="slider"] div[role="slider"]:hover {
    transform: scale(1.1);
    box-shadow: 0 0 0 5px rgba(255, 90, 31, 0.22);
}

/* ================= Bảng dữ liệu ================= */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #E2E8F0;
    background: rgba(255, 255, 255, 0.84);
    box-shadow: inset 0 1px 0 #FFFFFF, 0 6px 18px -6px rgba(15, 23, 42, 0.06);
    overflow: hidden;
    animation: chartGrow 0.4s ease both;
}

/* ================= Three.js 3D Hero Window Frame ================= */
div[data-testid="stVerticalBlock"][class*="st-key-hx-three-frame"] {
    border: 1px solid rgba(255, 255, 255, 0.92);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.62);
    backdrop-filter: blur(18px) saturate(175%);
    -webkit-backdrop-filter: blur(18px) saturate(175%);
    padding: 0;
    overflow: hidden;
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 0 0 1px rgba(15, 23, 42, 0.05),
        0 14px 36px -10px rgba(255, 90, 31, 0.14);
}
div[data-testid="stVerticalBlock"][class*="st-key-hx-three-frame"] iframe {
    display: block;
    border: 0;
    width: 100%;
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
    .hx-card, .hx-bento-hero, .hx-bento-hero::after, .hx-bento-tile,
    .hx-finding, .hx-question, .hx-chart, .hx-metric,
    .gx-mini-card, .stButton > button,
    [data-testid="stDataFrame"], .hx-alert-live {
        animation: none !important;
        transition: none !important;
        transform: none !important;
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
    color: #0F172A;
}

/* --- Khung chứa đồ thị hero: viền mảnh, bo góc, nền trắng ---------- */
div[data-testid="stVerticalBlock"][class*="st-key-gx-graph-card"] {
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    background: #FFFFFF;
    padding: 0;
    overflow: hidden;
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 14px 36px -12px rgba(249, 115, 22, 0.14),
        0 2px 6px rgba(15, 23, 42, 0.05);
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
    background: rgba(255, 255, 255, 0.84);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(226, 232, 240, 0.9);
    border-radius: 10px;
    padding: 8px 10px;
    margin-bottom: 8px;
    line-height: 1.25;
    box-shadow:
        inset 0 1px 0 0 rgba(255, 255, 255, 0.95),
        0 1px 2px rgba(15, 23, 42, 0.04),
        0 8px 20px -6px rgba(15, 23, 42, 0.06);
    transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
                border-color 0.2s ease,
                box-shadow 0.25s ease;
}
.gx-mini-card:hover {
    transform: translateY(-2px);
    border-color: #FDBA74 !important;
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 12px 26px -8px rgba(249, 115, 22, 0.16);
}
.gx-mini-val {
    font-size: 18px;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;   /* số không nhảy bề rộng */
}
.gx-mini-lab {
    font-size: 11px;
    color: #64748B;
    margin-top: 2px;
}
/* Hai vạch màu nhỏ để phân biệt cạnh công khai / riêng tư */
.gx-mini-card.is-public { border-left: 3px solid #F97316; }
.gx-mini-card.is-private { border-left: 3px solid #EF4444; }

/* --- Bảng chi tiết nút (cột phải) ----------------------------------- */
.gx-panel {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #F97316;
    border-radius: 0 8px 8px 0;
    padding: 9px 11px;
    margin: 0.35rem 0 0.5rem 0;
    animation: fadeDown 0.3s ease both;
}
.gx-panel-kind {
    font-size: 11px;
    font-weight: 700;
    color: #64748B;
}
.gx-panel-name {
    font-size: 14px;
    font-weight: 700;
    line-height: 1.35;
    margin: 4px 0 3px 0;
    color: #0F172A;
    overflow-wrap: anywhere;
}
.gx-panel-meta {
    font-size: 11px;
    color: #64748B;
}

/* --- Tiêu đề phụ trong cột phải ------------------------------------- */
.gx-side-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #64748B;
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
.gx-nbr:hover { background: #FFF7ED; }
.gx-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex: 0 0 auto;
}
.gx-hit-kind {
    flex: 0 0 auto;
    font-size: 10px;
    color: #64748B;
}
.gx-hint {
    font-size: 11px;
    color: #64748B;
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
    border-color: #E2E8F0;
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

