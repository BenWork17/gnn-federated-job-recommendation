"""Chụp ảnh trạng thái ĐANG CHẠY với backend thật.

Backend mô phỏng chạy rất nhanh (12 vòng ~2s), nên phải chụp ngay sau khi bấm
Start thay vì chờ. Chụp nhiều mốc thời gian rồi giữ ảnh có trạng thái 'đang chạy'.
"""
from __future__ import annotations

import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent
SHOTS = UI_DIR / "screenshots"
PORT = 18086


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> int:
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(
        ("127.0.0.1", PORT), functools.partial(Handler, directory=str(UI_DIR))
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    info = {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            page = b.new_page(viewport={"width": 1600, "height": 1100})
            page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
            page.wait_for_timeout(2000)

            # 40 vòng, 10 client -> đủ dài để bắt trạng thái running
            page.eval_on_selector("#rounds", "el => { el.value = 40; el.dispatchEvent(new Event('input')); }")
            page.click("#startBtn")

            # thử chụp ở nhiều mốc, giữ ảnh đầu tiên có badge 'đang chạy'
            captured = False
            for i in range(30):
                page.wait_for_timeout(250)
                badge = page.inner_text("#runBadge").strip()
                if badge == "đang chạy" and i >= 2:
                    page.evaluate("window.scrollTo(0,0)")
                    page.wait_for_timeout(120)
                    page.screenshot(path=str(SHOTS / "backend-real-02-running.png"), full_page=True)
                    info["captured_at_ms"] = 250 * (i + 1)
                    info["badge"] = badge
                    info["round"] = page.inner_text("#runRound").strip()
                    info["reported"] = page.inner_text("#nodeReported").strip()
                    info["recall"] = page.inner_text("#roRecall").strip()
                    info["p50"] = page.inner_text("#roP50").strip()
                    captured = True
                    break
            info["captured"] = captured

            # đợi hoàn tất rồi chụp ảnh done
            for _ in range(120):
                page.wait_for_timeout(500)
                if page.inner_text("#runBadge").strip() == "hoàn tất":
                    break
            page.wait_for_timeout(400)
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(150)
            page.screenshot(path=str(SHOTS / "backend-real-03-done.png"), full_page=True)
            info["final_badge"] = page.inner_text("#runBadge").strip()
            info["final_round"] = page.inner_text("#runRound").strip()
            info["final_recall"] = page.inner_text("#roRecall").strip()
            b.close()
    finally:
        httpd.shutdown()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
