"""Xác nhận UI ghi log cảnh báo khi số client thật < số client người dùng chọn."""
from pathlib import Path

import functools
import http.server
import socketserver
import threading

from playwright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent
PORT = 18087


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> None:
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), functools.partial(Handler, directory=str(UI_DIR)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            page = b.new_page(viewport={"width": 1400, "height": 900})
            page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
            page.wait_for_timeout(2000)
            # backend thật chỉ có 10 client; chọn 50
            page.eval_on_selector("#nClients", "el => { el.value = 50; el.dispatchEvent(new Event('input')); }")
            page.eval_on_selector("#rounds", "el => { el.value = 2; el.dispatchEvent(new Event('input')); }")
            page.click("#startBtn")
            page.wait_for_timeout(2500)
            lines = page.eval_on_selector_all(
                "#log .log-line", "els => els.map(e => e.innerText.replace(/\\s+/g,' '))"
            )
            hits = [x for x in lines if "dùng 10/50" in x]
            print("cảnh báo có trong log:", bool(hits))
            for h in hits:
                print("  ", h)
            print("node cells:", page.eval_on_selector_all("#nodeGrid .node", "els => els.length"))
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(150)
            page.screenshot(path=str(UI_DIR / "screenshots" / "13-live-client-cap-warning.png"), full_page=True)
            b.close()
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()
