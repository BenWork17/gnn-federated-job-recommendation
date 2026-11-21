"""Kiểm thử UI với BACKEND THẬT (api/main.py --dry-run).

Khác run_checks.py: không dùng mock, xác nhận UI chạy được trên dữ liệu và
WebSocket thật do api-dev cung cấp. Ảnh lưu vào screenshots/backend-real-*.png

Chạy: python ui/devtools/check_real_backend.py
"""
from __future__ import annotations

import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

UI_DIR = Path(__file__).resolve().parent.parent
SHOTS = UI_DIR / "screenshots"
PORT = 18085


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> int:
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(
        ("127.0.0.1", PORT), functools.partial(Handler, directory=str(UI_DIR))
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    out: dict[str, object] = {}
    errs: list[str] = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            page = b.new_page(viewport={"width": 1600, "height": 1100})
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.on("console", lambda m: errs.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)

            page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
            page.wait_for_timeout(2000)
            out["health"] = page.inner_text("#healthBadge").strip()
            out["db"] = page.inner_text("#dbState").strip()
            out["artifacts"] = page.inner_text("#artState").strip()
            out["demo_visible"] = page.evaluate(
                "getComputedStyle(document.getElementById('demoNotice')).display !== 'none'"
            )
            out["client_total"] = page.inner_text("#clientTotal").strip()
            out["summary"] = {
                "users": page.inner_text("#sUsers").strip(),
                "jobs": page.inner_text("#sJobs").strip(),
                "skills": page.inner_text("#sSkills").strip(),
                "occ": page.inner_text("#sOcc").strip(),
                "uj": page.inner_text("#sUJ").strip(),
                "js": page.inner_text("#sJS").strip(),
                "us": page.inner_text("#sUS").strip(),
                "clients": page.inner_text("#sClients").strip(),
                "sparsity": page.inner_text("#sSparse").strip(),
            }
            out["rows"] = page.eval_on_selector_all("#clientBody tr[data-client]", "els => els.length")
            out["row_texts"] = page.eval_on_selector_all(
                "#clientBody tr[data-client]", "els => els.map(e => e.innerText.replace(/\\s+/g,' '))"
            )
            out["ws_badge"] = page.inner_text("#wsBadge").strip()
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(150)
            page.screenshot(path=str(SHOTS / "backend-real-01-idle.png"), full_page=True)

            # chi tiết client thật (top_skills)
            page.click("#clientBody tr[data-client]")
            page.wait_for_timeout(900)
            out["detail"] = page.inner_text("#detailBox").replace("\n", " | ")
            out["chips"] = page.eval_on_selector_all("#detailSkills .skill-chip", "els => els.map(e => e.innerText)")

            # start training thật
            page.eval_on_selector("#nClients", "el => { el.value = 10; el.dispatchEvent(new Event('input')); }")
            page.eval_on_selector("#rounds", "el => { el.value = 12; el.dispatchEvent(new Event('input')); }")
            page.click("#startBtn")
            page.wait_for_timeout(2500)
            out["run_id"] = page.inner_text("#runId").strip()
            out["node_cells"] = page.eval_on_selector_all("#nodeGrid .node", "els => els.length")
            page.wait_for_timeout(6000)
            out["reported"] = page.inner_text("#nodeReported").strip()
            out["p50_foot"] = page.inner_text("#nodeP50").strip()
            out["run_badge_running"] = page.inner_text("#runBadge").strip()
            out["round"] = page.inner_text("#runRound").strip()
            out["recall"] = page.inner_text("#roRecall").strip()
            out["chart_recall"] = page.evaluate(
                """() => { const c = Object.values(Chart.instances).find(x=>x.canvas.id==='chartRecall');
                           return c ? {labels:c.data.labels, data:c.data.datasets[0].data} : null; }"""
            )
            out["chart_latency"] = page.evaluate(
                """() => { const c = Object.values(Chart.instances).find(x=>x.canvas.id==='chartLatency');
                           return c ? {labels:c.data.labels, p50:c.data.datasets[0].data, p95:c.data.datasets[1].data} : null; }"""
            )
            out["log_tail"] = page.eval_on_selector_all(
                "#log .log-line", "els => els.slice(-10).map(e => e.innerText.replace(/\\s+/g,' '))"
            )
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(150)
            page.screenshot(path=str(SHOTS / "backend-real-02-running.png"), full_page=True)

            out["run_badge_mid"] = page.inner_text("#runBadge").strip()
            page.wait_for_timeout(30000)
            out["run_badge_after"] = page.inner_text("#runBadge").strip()
            out["round_after"] = page.inner_text("#runRound").strip()
            out["recall_after"] = page.inner_text("#roRecall").strip()
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(150)
            page.screenshot(path=str(SHOTS / "backend-real-03-done.png"), full_page=True)
            out["errors"] = errs
            b.close()
    finally:
        httpd.shutdown()

    print(json.dumps(out, ensure_ascii=False, indent=2))
    (UI_DIR / "devtools" / "last_real_backend.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
