"""Kiểm thử hành vi mất kết nối WS: badge 'disconnected' + tự thử lại mỗi 3s.

Kịch bản: mock backend đang chạy ở 8000, bắt đầu train, rồi tắt backend
(dừng process) ở giữa lượt chạy; UI phải chuyển badge sang disconnected và
liên tục thử lại. Sau đó bật backend lại và kiểm tra nó tự nối lại.

Chạy: python ui/devtools/check_ws_reconnect.py
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent
ROOT = UI_DIR.parent
PORT = 18082
MOCK_PORT = 8011


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_mock() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, str(UI_DIR / "devtools" / "mock_backend.py"), "--port", str(MOCK_PORT)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_port(port: int, timeout: float = 20.0) -> bool:
    import socket

    end = time.time() + timeout
    while time.time() < end:
        s = socket.socket()
        s.settimeout(0.4)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            time.sleep(0.3)
        finally:
            s.close()
    return False


def main() -> int:
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(
        ("127.0.0.1", PORT), functools.partial(Handler, directory=str(UI_DIR))
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    mock = start_mock()
    assert wait_port(MOCK_PORT), "mock backend không lên"

    out: dict[str, object] = {}
    logs: list[str] = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            page = b.new_page(viewport={"width": 1600, "height": 1000})
            page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
            # trỏ UI sang mock port bằng ?api= — UI đọc API_BASE từ query cho phép test
            page.goto(f"http://127.0.0.1:{PORT}/index.html?api=http://127.0.0.1:{MOCK_PORT}")
            page.wait_for_timeout(2500)
            out["before_health"] = page.inner_text("#healthBadge").strip()
            out["before_ws"] = page.inner_text("#wsBadge").strip()
            out["client_total"] = page.inner_text("#clientTotal").strip()

            page.eval_on_selector("#nClients", "el => { el.value = 20; el.dispatchEvent(new Event('input')); }")
            page.eval_on_selector("#rounds", "el => { el.value = 40; el.dispatchEvent(new Event('input')); }")
            page.click("#startBtn")
            page.wait_for_timeout(4000)
            out["running_badge"] = page.inner_text("#runBadge").strip()
            out["running_reported"] = page.inner_text("#nodeReported").strip()
            out["ws_during_run"] = page.inner_text("#wsBadge").strip()

            # --- tắt backend giữa lượt chạy
            mock.terminate()
            mock.wait(timeout=10)
            page.wait_for_timeout(3500)
            out["ws_after_kill"] = page.inner_text("#wsBadge").strip()
            out["health_after_kill"] = page.inner_text("#healthBadge").strip()
            out["demo_notice_after_kill"] = page.evaluate(
                "getComputedStyle(document.getElementById('demoNotice')).display !== 'none'"
            )
            out["run_state_after_kill"] = page.inner_text("#runBadge").strip()
            out["log_tail_kill"] = page.eval_on_selector_all(
                "#log .log-line", "els => els.slice(-6).map(e => e.innerText.replace(/\\s+/g,' '))"
            )
            page.screenshot(path=str(UI_DIR / "screenshots" / "08-ws-disconnected.png"), full_page=False)

            # đếm số lần thử lại: chờ 7s, badge phải vẫn disconnected và có log thử lại
            n_before = page.eval_on_selector_all("#log .log-line", "els => els.length")
            page.wait_for_timeout(7000)
            n_after = page.eval_on_selector_all("#log .log-line", "els => els.length")
            out["log_lines_grew_while_down"] = n_after - n_before
            out["retry_log_present"] = page.evaluate(
                "Array.from(document.querySelectorAll('#log .log-line')).some(e => e.innerText.includes('thử lại sau 3s'))"
            )

            # --- bật lại backend: UI phải tự phục hồi
            mock = start_mock()
            assert wait_port(MOCK_PORT), "mock backend không lên lại"
            page.wait_for_timeout(20000)
            out["ws_after_restore"] = page.inner_text("#wsBadge").strip()
            out["health_after_restore"] = page.inner_text("#healthBadge").strip()
            out["demo_notice_after_restore"] = page.evaluate(
                "getComputedStyle(document.getElementById('demoNotice')).display !== 'none'"
            )
            out["client_total_after_restore"] = page.inner_text("#clientTotal").strip()
            page.screenshot(path=str(UI_DIR / "screenshots" / "09-ws-restored.png"), full_page=False)
            out["page_errors"] = logs
            b.close()
    finally:
        try:
            mock.terminate()
            mock.wait(timeout=8)
        except Exception:
            pass
        httpd.shutdown()

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
