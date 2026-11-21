"""Kiểm tra sâu: dữ liệu thực sự nằm trong Chart.js, lưới node ở mức tối đa,
và log khớp số tick WS."""

from __future__ import annotations

import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent
PORT = 18084


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> None:
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(
        ("127.0.0.1", PORT), functools.partial(Handler, directory=str(UI_DIR))
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        page = b.new_page(viewport={"width": 1600, "height": 1000})
        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # max clients = 200, 3 vòng
        page.eval_on_selector("#nClients", "el => { el.value = 200; el.dispatchEvent(new Event('input')); }")
        page.eval_on_selector("#rounds", "el => { el.value = 3; el.dispatchEvent(new Event('input')); }")
        page.click("#startBtn")
        page.wait_for_timeout(18000)

        out["chart_recall_data"] = page.evaluate(
            """() => {
                const c = Object.values(Chart.instances).find(x => x.canvas.id === 'chartRecall');
                return c ? {labels: c.data.labels, data: c.data.datasets[0].data} : null;
            }"""
        )
        out["chart_latency_data"] = page.evaluate(
            """() => {
                const c = Object.values(Chart.instances).find(x => x.canvas.id === 'chartLatency');
                return c ? {labels: c.data.labels, p50: c.data.datasets[0].data, p95: c.data.datasets[1].data} : null;
            }"""
        )
        out["node_cells_200"] = page.eval_on_selector_all("#nodeGrid .node", "els => els.length")
        out["node_reported"] = page.inner_text("#nodeReported").strip()
        out["run_badge"] = page.inner_text("#runBadge").strip()
        out["rounded_round"] = page.inner_text("#runRound").strip()
        out["log_line_count"] = page.eval_on_selector_all("#log .log-line", "els => els.length")
        out["log_ticks"] = page.evaluate(
            "Array.from(document.querySelectorAll('#log .log-line')).filter(e => /^round \\d+$/.test((e.querySelector('.lg-r')||{}).innerText||'')).length"
        )
        out["log_has_round_summary"] = page.evaluate(
            "Array.from(document.querySelectorAll('#log .log-line')).filter(e => e.innerText.includes('p50') && e.innerText.includes('vòng')).length"
        )
        out["node_grid_scrollable"] = page.evaluate(
            "(() => { const g = document.getElementById('nodeGrid'); return g.scrollHeight > g.clientHeight; })()"
        )
        out["log_scroll"] = page.evaluate(
            "(() => { const g = document.getElementById('log'); return {sh: g.scrollHeight, ch: g.clientHeight, st: g.scrollTop}; })()"
        )
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(200)
        page.screenshot(path=str(UI_DIR / "screenshots" / "12-live-200clients.png"), full_page=True)

        # keyboard: điều hướng bảng bằng Enter
        page.eval_on_selector("#pageSize", "el => { el.value='25'; el.dispatchEvent(new Event('change')); }")
        page.wait_for_timeout(400)
        page.eval_on_selector("#clientBody tr[data-client]", "el => el.focus()")
        page.keyboard.press("Enter")
        page.wait_for_timeout(600)
        out["keyboard_select_name"] = page.inner_text("#detailName").strip()
        out["focus_ring_ok"] = page.evaluate(
            "(() => { const el = document.activeElement; return el ? el.tagName + ':' + (getComputedStyle(el).outlineStyle !== 'none') : null; })()"
        )
        b.close()
    httpd.shutdown()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    (UI_DIR / "devtools" / "last_deep_check.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
