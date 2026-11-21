"""Chạy UI + kiểm thử bằng Playwright, chụp ảnh màn hình.

- Phục vụ thư mục ui/ qua http://127.0.0.1:8080 (cũng kiểm tra CORS tới :8000).
- Test LIVE: /health ok, tải client, start training, tick WS, biểu đồ, lưới node.
- Test DEMO: backend tắt -> phải hiện DEMO MODE, không trắng trang.

Chạy: python ui/devtools/run_checks.py
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent
SHOTS = UI_DIR / "screenshots"
SHOTS.mkdir(exist_ok=True)
PORT = 18080
MOCK_PORT = 8013
ROOT = UI_DIR.parent
URL = f'http://127.0.0.1:{PORT}/index.html?api=http://127.0.0.1:{MOCK_PORT}'


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # im lặng
        pass


def start_mock() -> subprocess.Popen:
    """Mock backend riêng để test UI, không đụng cổng 8000 (backend thật)."""
    return subprocess.Popen(
        [sys.executable, str(UI_DIR / "devtools" / "mock_backend.py"), "--port", str(MOCK_PORT)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_port(port: int, timeout: float = 30.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        sk = socket.socket()
        sk.settimeout(0.4)
        try:
            sk.connect(("127.0.0.1", port))
            return True
        except OSError:
            time.sleep(0.3)
        finally:
            sk.close()
    return False


def serve() -> socketserver.TCPServer:
    handler = functools.partial(Handler, directory=str(UI_DIR))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def run(page, label: str):
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type in ("error",) else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    return errors


def main() -> int:
    httpd = serve()
    mock = start_mock()
    if not wait_port(MOCK_PORT):
        print('mock backend không lên được')
        return 1
    url = URL
    results: dict[str, object] = {}
    console: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": 1600, "height": 1100}, device_scale_factor=1)
        page = ctx.new_page()
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))

        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1500)

        # --- trạng thái live
        results["health"] = page.inner_text("#healthBadge").strip()
        results["demo_visible_live"] = page.evaluate(
            "getComputedStyle(document.getElementById('demoNotice')).display !== 'none'"
        )
        results["client_total"] = page.inner_text("#clientTotal").strip()
        results["rows_live"] = page.eval_on_selector_all("#clientBody tr[data-client]", "els => els.length")
        results["row1"] = page.eval_on_selector_all(
            "#clientBody tr[data-client]", "els => els.slice(0,3).map(e => e.innerText.replace(/\\s+/g,' '))"
        )
        results["ws_badge_live"] = page.inner_text("#wsBadge").strip()
        results["summary_users"] = page.inner_text("#sUsers").strip()
        results["chart_ok"] = page.evaluate("typeof Chart !== 'undefined' && !!document.getElementById('chartRecall')")
        page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(150); page.screenshot(path=str(SHOTS / "01-live-idle.png"), full_page=True)

        # --- sort theo n_apps (click lần 1 = tăng dần)
        page.click(".th-sort[data-sort='n_apps']")
        page.wait_for_timeout(300)
        asc_first = page.inner_text("#clientBody tr[data-client] td.num")
        results["sort_asc_first"] = asc_first
        page.click(".th-sort[data-sort='n_apps']")
        page.wait_for_timeout(300)
        desc_first = page.inner_text("#clientBody tr[data-client] td.num")
        results["sort_desc_first"] = desc_first

        # --- phân trang
        page.select_option("#pageSize", "100")
        page.wait_for_timeout(300)
        results["rows_page_100"] = page.eval_on_selector_all("#clientBody tr[data-client]", "els => els.length")
        page.click("#nextPage")
        page.wait_for_timeout(300)
        results["page_info_after_next"] = page.inner_text("#pageInfo").strip()
        page.click("#prevPage")
        page.wait_for_timeout(200)

        # --- chọn dòng -> panel chi tiết
        page.click("#clientBody tr[data-client]")
        page.wait_for_timeout(600)
        results["detail_visible"] = page.is_visible("#detailBox")
        results["detail_name"] = page.inner_text("#detailName").strip()
        results["detail_chips"] = page.eval_on_selector_all("#detailSkills .skill-chip", "els => els.length")

        # --- bật auto-scroll, bắt đầu train
        page.fill("#nClients", "60") if False else page.eval_on_selector(
            "#nClients", "el => { el.value = 60; el.dispatchEvent(new Event('input')); }"
        )
        page.eval_on_selector("#rounds", "el => { el.value = 6; el.dispatchEvent(new Event('input')); }")
        page.click("#startBtn")
        page.wait_for_timeout(1200)
        results["run_id_live"] = page.inner_text("#runId").strip()
        results["node_cells"] = page.eval_on_selector_all("#nodeGrid .node", "els => els.length")

        page.wait_for_timeout(6000)
        results["nodes_reported"] = page.inner_text("#nodeReported").strip()
        results["node_p50"] = page.inner_text("#nodeP50").strip()
        results["node_p95"] = page.inner_text("#nodeP95").strip()
        results["recall_chart_points"] = page.evaluate(
            "document.getElementById('chartRecall') && window.Chart ? null : null"
        )
        results["recall_readout"] = page.inner_text("#roRecall").strip()
        results["latency_readout_p50"] = page.inner_text("#roP50").strip()
        results["log_lines"] = page.eval_on_selector_all("#log .log-line", "els => els.length")
        results["log_sample"] = page.eval_on_selector_all(
            "#log .log-line", "els => els.slice(-8).map(e => e.innerText.replace(/\\s+/g,' '))"
        )
        results["node_colors"] = page.evaluate(
            """() => {
                const out = {ok:0, warn:0, bad:0, pending:0};
                document.querySelectorAll('#nodeGrid .node').forEach(n => out[n.dataset.state] = (out[n.dataset.state]||0)+1);
                return out;
            }"""
        )
        page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(150); page.screenshot(path=str(SHOTS / "02-live-running.png"), full_page=True)

        # --- đợi tới hết run
        page.wait_for_timeout(9000)
        results["run_status_after"] = page.inner_text("#runBadge").strip()
        results["run_round_after"] = page.inner_text("#runRound").strip()
        page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(150); page.screenshot(path=str(SHOTS / "03-live-done.png"), full_page=True)

        results["console_errors_live"] = list(console)
        console.clear()

        # --- DEMO MODE: trỏ UI sang cổng không có backend
        page2 = ctx.new_page()
        page2.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page2.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
        page2.route("**/health", lambda route: route.abort())
        page2.route("**/api/**", lambda route: route.abort())
        page2.goto(url, wait_until="domcontentloaded")
        page2.wait_for_timeout(2500)
        results["demo_notice_demo"] = page2.evaluate(
            "getComputedStyle(document.getElementById('demoNotice')).display !== 'none'"
        )
        results["demo_reason"] = page2.inner_text("#demoReason").strip()
        results["demo_health"] = page2.inner_text("#healthBadge").strip()
        results["demo_rows"] = page2.eval_on_selector_all("#clientBody tr[data-client]", "els => els.length")
        results["demo_ws_badge"] = page2.inner_text("#wsBadge").strip()
        results["demo_body_text_len"] = len(page2.inner_text("body"))
        page2.evaluate("window.scrollTo(0,0)"); page2.wait_for_timeout(150); page2.screenshot(path=str(SHOTS / "04-demo-mode.png"), full_page=True)

        page2.click("#demoRunBtn")
        page2.wait_for_timeout(5000)
        results["demo_nodes"] = page2.eval_on_selector_all("#nodeGrid .node", "els => els.length")
        results["demo_reported"] = page2.inner_text("#nodeReported").strip()
        results["demo_recall"] = page2.inner_text("#roRecall").strip()
        results["demo_log_lines"] = page2.eval_on_selector_all("#log .log-line", "els => els.length")
        page2.evaluate("window.scrollTo(0,0)"); page2.wait_for_timeout(150); page2.screenshot(path=str(SHOTS / "05-demo-running.png"), full_page=True)

        # --- file:// (không cần server tĩnh)
        page3 = ctx.new_page()
        page3.on("pageerror", lambda e: console.append(f"pageerror(file): {e}"))
        page3.goto((UI_DIR / "index.html").as_uri() + f"?api=http://127.0.0.1:{MOCK_PORT}", wait_until="domcontentloaded")
        page3.wait_for_timeout(3000)
        results["file_url_health"] = page3.inner_text("#healthBadge").strip()
        results["file_url_rows"] = page3.eval_on_selector_all("#clientBody tr[data-client]", "els => els.length")
        results["file_url_body_len"] = len(page3.inner_text("body"))
        page3.evaluate("window.scrollTo(0,0)"); page3.wait_for_timeout(150); page3.screenshot(path=str(SHOTS / "06-file-url.png"), full_page=True)

        # --- mobile
        page4 = ctx.new_page()
        page4.set_viewport_size({"width": 430, "height": 940})
        page4.goto(url, wait_until="domcontentloaded")
        page4.wait_for_timeout(2500)
        page4.screenshot(path=str(SHOTS / "07-mobile.png"), full_page=True)
        results["mobile_scroll_width"] = page4.evaluate("document.documentElement.scrollWidth")
        results["mobile_client_width"] = page4.evaluate("document.documentElement.clientWidth")

        results["console_errors_demo_and_file"] = list(console)
        browser.close()

    httpd.shutdown()
    try:
        mock.terminate()
        mock.wait(timeout=8)
    except Exception:
        pass
    print(json.dumps(results, ensure_ascii=False, indent=2))
    (UI_DIR / "devtools" / "last_check.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


