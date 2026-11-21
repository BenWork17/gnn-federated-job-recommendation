"""Tìm phần tử gây tràn ngang ở viewport hẹp + kiểm tra sticky topbar."""
from __future__ import annotations

import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent
PORT = 18081


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> None:
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(
        ("127.0.0.1", PORT), functools.partial(Handler, directory=str(UI_DIR))
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        for w in (430, 390, 768, 1024, 1280, 1600):
            page = b.new_page(viewport={"width": w, "height": 900})
            page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="domcontentloaded")
            page.wait_for_timeout(2200)
            info = page.evaluate(
                """() => {
                    const vw = document.documentElement.clientWidth;
                    const out = [];
                    document.querySelectorAll('*').forEach(el => {
                        const r = el.getBoundingClientRect();
                        if (r.width === 0 && r.height === 0) return;
                        if (r.right > vw + 1 || r.left < -1) {
                            out.push({tag: el.tagName, id: el.id, cls: el.className && String(el.className).slice(0,60),
                                      left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width)});
                        }
                    });
                    return {vw, scrollWidth: document.documentElement.scrollWidth,
                            bodyScroll: document.body.scrollWidth,
                            offenders: out.slice(0, 12)};
                }"""
            )
            print(w, json.dumps(info, ensure_ascii=False))
            page.close()
        b.close()
    httpd.shutdown()


if __name__ == "__main__":
    main()
