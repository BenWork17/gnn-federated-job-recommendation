"""
Chụp ảnh màn hình THẬT của app Streamlit để kiểm tra trực quan.

VÌ SAO CẦN: trong suốt quá trình làm, tôi chỉ kiểm được app bằng AppTest
(không lỗi) và HTTP 200 (server sống). Không có cách nào xác nhận giao diện
CÓ ĐẸP hay không — mà đó lại đúng là điều người dùng hỏi. Script này chụp
thật bằng Playwright + Chrome hệ thống.

CÁCH DÙNG:
    python app/screenshot_app.py

Yêu cầu: đã chạy `streamlit run app/streamlit_app.py` ở cổng 8501 (hoặc
truyền --port). Ảnh lưu vào artifacts/shots/.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "shots"

# Tên file -> (nhãn trang, số pixel cuộn thêm, giây chờ riêng nếu cần)
# Trang Gợi ý cần chờ vì nội dung nằm trong st.tabs + cache tính điểm.
# Trang Federated Learning simulation cần chờ vì nội dung nằm trong st.fragment(run_every=...)
# — fragment render sau lần chạy đầu, chờ ít quá sẽ chụp phải khung trống.
PAGES = [
    ("01_tong_quan.png", "Tổng quan", 0, None),
    ("02_do_thi.png", "Đồ thị việc làm", 520, None),
    ("03_lien_bang.png", "Federated Learning simulation", 420, 6.0),
    ("04_goi_y.png", "Gợi ý cho ứng viên", 340, 12.0),
    ("05_ket_luan.png", "Kết luận & hạn chế", 300, None),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8501)
    ap.add_argument("--wait", type=float, default=4.0,
                    help="giây chờ sau khi bấm chuyển trang")
    ap.add_argument("--full", action="store_true",
                    help="chụp toàn trang (dài) thay vì chỉ khung nhìn")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{args.port}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-crash-reporter"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000},
                                device_scale_factor=1.5)
        page.goto(base, wait_until="domcontentloaded", timeout=60_000)

        # Streamlit cần websocket để render nội dung: chờ tiêu đề xuất hiện
        try:
            page.wait_for_selector("h1", timeout=45_000)
        except Exception:
            print("CẢNH BÁO: không thấy h1 sau 45s — chụp trạng thái hiện tại")
        time.sleep(3)

        for fname, label, scroll, extra_wait in PAGES:
            # Chuyển trang bằng link trên sidebar
            try:
                link = page.get_by_role("link", name=label).first
                link.click(timeout=15_000)
                page.wait_for_timeout(int(args.wait * 1000))
            except Exception as exc:
                print(f"  [{label}] không bấm được link: {str(exc)[:70]}")
            if extra_wait:
                page.wait_for_timeout(int(extra_wait * 1000))
            if scroll:
                page.mouse.wheel(0, scroll)
                page.wait_for_timeout(1200)
            path = OUT / fname
            page.screenshot(path=str(path), full_page=args.full)
            print(f"  {fname}  ({path.stat().st_size:,} B)")

        browser.close()

    print(f"\nĐã lưu {len(PAGES)} ảnh vào {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
