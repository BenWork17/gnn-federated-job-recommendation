"""Kiểm thử tự phục hồi: mở UI khi backend CHẾT -> DEMO MODE; backend lên -> tự về LIVE.

Chạy: python ui/devtools/check_demo_recovery.py
"""
from __future__ import annotations

import functools
import http.server
import json
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent
ROOT = UI_DIR.parent
PORT = 18083
MOCK_PORT = 8012


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


def wait_port(port: int, timeout: float = 25.0) -> bool:
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

    out: dict[str, object] = {}
    mock = None
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            page = b.new_page(viewport={"width": 1600, "height": 1000})
            page.goto(f"http://127.0.0.1:{PORT}/index.html?api=http://127.0.0.1:{MOCK_PORT}")
            page.wait_for_timeout(3000)
            out["health_down"] = page.inner_text("#healthBadge").strip()
            out["demo_notice_down"] = page.evaluate(
                "getComputedStyle(document.getElementById('demoNotice')).display !== 'none'"
            )
            out["rows_down"] = page.eval_on_selector_all("#clientBody tr[data-client]", "els => els.length")
            out["body_len_down"] = len(page.inner_text("body"))
            page.screenshot(path=str(UI_DIR / "screenshots" / "10-demo-autofallback.png"), full_page=True)

            # backend lên trong lúc UI đang DEMO
            mock = start_mock()
            assert wait_port(MOCK_PORT), "mock backend không lên"
            page.wait_for_timeout(7000)
            out["health_recovered"] = page.inner_text("#healthBadge").strip()
            out["demo_notice_recovered"] = page.evaluate(
                "getComputedStyle(document.getElementById('demoNotice')).display !== 'none'"
            )
            out["client_total_recovered"] = page.inner_text("#clientTotal").strip()
            out["ws_recovered"] = page.inner_text("#wsBadge").strip()
            out["rows_recovered"] = page.eval_on_selector_all("#clientBody tr[data-client]", "els => els.length")
            page.screenshot(path=str(UI_DIR / "screenshots" / "11-demo-recovered.png"), full_page=True)
            b.close()
    finally:
        if mock:
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
