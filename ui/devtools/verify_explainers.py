"""Kiểm chứng 4 khối giải thích nc-* của FL Node Console.

Chạy: python ui/devtools/verify_explainers.py
- mở ui/index.html qua http.server (127.0.0.1:18088)
- backend thật ở 127.0.0.1:8000 (nếu có)
- kiểm tra 4 panel hiện, sơ đồ phát sáng đúng bước, trace mở khi bấm ô node
- KHÔNG có lỗi console
- chụp ảnh: đang chạy + đã xong
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
PORT = 18088
API = "http://127.0.0.1:8000"


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> int:
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(
        ("127.0.0.1", PORT), functools.partial(Handler, directory=str(UI_DIR))
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    info: dict = {"checks": {}, "console_errors": []}
    ok = True
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            page = b.new_page(viewport={"width": 1600, "height": 1100})
            page.on("console", lambda m: info["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: info["console_errors"].append(f"pageerror: {e}"))

            page.goto(f"http://127.0.0.1:{PORT}/index.html?api={API}", wait_until="networkidle")
            page.wait_for_timeout(3500)

            # ---------- 4 panel phải hiện ----------
            info["checks"]["panel_mot_node"] = page.is_visible("#ncWhatPanel")
            info["checks"]["panel_5_buoc"] = page.is_visible("#ncRoundPanel")
            info["checks"]["panel_o_lai_truyen_di"] = page.is_visible("#ncStayPanel")
            info["checks"]["claim_text"] = "Node không gửi dữ liệu thô" in page.inner_text("#ncStayPanel")
            info["checks"]["env_note"] = "MỘT tiến trình Python" in page.inner_text("#ncWhatPanel")
            info["checks"]["sim_note"] = page.eval_on_selector_all(
                ".nc-sim-note",
                "els => els.some(e => e.innerText.includes('không phải kết quả huấn luyện thật'))",
            )
            info["checks"]["step_count"] = page.eval_on_selector_all(".nc-step", "els => els.length")

            # số liệu thật của node randstad trong panel "Một node là gì"
            info["emp_name"] = page.inner_text("#ncEmpName")
            info["emp_apps"] = page.inner_text("#ncEmpApps")
            info["emp_users"] = page.inner_text("#ncEmpUsers")
            info["emp_jobs"] = page.inner_text("#ncEmpJobs")
            info["emp_source"] = page.inner_text("#ncEmpSource")
            info["total_nodes"] = page.inner_text("#ncTotalNodes")
            info["checks"]["randstad_real"] = (
                info["emp_name"].strip().lower() == "randstad"
                and info["emp_apps"].strip() == "4.745"
                and info["total_nodes"].strip() == "9.116"
            )

            # ---------- bấm Start, bắt trạng thái đang chạy ----------
            page.eval_on_selector("#rounds", "el => { el.value = 40; el.dispatchEvent(new Event('input')); }")
            page.eval_on_selector("#nClients", "el => { el.value = 40; el.dispatchEvent(new Event('input')); }")
            page.eval_on_selector("#startBtn", "el => el.click()")

            active_steps = set()
            # ngay sau khi bấm Start phải thấy BƯỚC 1 phát sáng
            page.wait_for_timeout(60)
            s1 = page.eval_on_selector_all(".nc-step.active", "els => els.map(e => Number(e.dataset.step))")
            info["step_at_start"] = s1
            trace_states = set()
            walk = []
            for i in range(40):
                page.wait_for_timeout(150)
                a = page.eval_on_selector_all(
                    ".nc-step.active", "els => els.map(e => Number(e.dataset.step))"
                )
                st = page.inner_text("#ncRoundState")
                trace_states.add(page.eval_on_selector("#ncTraceState", "e => e.dataset.state"))
                if a:
                    active_steps.add(a[0])
                    walk.append({"step": a[0], "label": st})
                if i == 4:
                    # bấm 1 ô node -> trace phải mở
                    page.eval_on_selector("#nodeGrid .node:first-child", "el => el.click()")
                    page.wait_for_timeout(200)
                    info["checks"]["trace_visible"] = page.is_visible("#ncTracePanel")
                    info["checks"]["trace_has_name"] = page.inner_text("#ncTraceName")
                    info["checks"]["trace_state"] = page.inner_text("#ncTraceState")
                    info["checks"]["trace_state_legend"] = "waiting" in page.inner_text(".nc-state-legend")
                    page.evaluate("window.scrollTo(0,0)")
                    page.wait_for_timeout(150)
                    page.screenshot(path=str(SHOTS / "nc-01-running.png"), full_page=True, timeout=90000, animations="disabled")
                if len(active_steps) >= 4 and i > 12:
                    break
            info["active_steps_seen"] = sorted(active_steps)
            info["trace_states_seen"] = sorted(trace_states)
            info["step_walk"] = walk[:24]

            # đợi hoàn tất
            for _ in range(180):
                page.wait_for_timeout(500)
                if page.inner_text("#runBadge").strip() in ("hoàn tất", "lỗi"):
                    break
            page.wait_for_timeout(600)
            info["final_badge"] = page.inner_text("#runBadge").strip()
            info["final_round"] = page.inner_text("#runRound").strip()
            info["send_up"] = page.inner_text("#ncSendUp")
            info["send_down"] = page.inner_text("#ncSendDown")
            info["send_rounds"] = page.inner_text("#ncSendRounds")
            info["send_total"] = page.inner_text("#ncSendTotal")
            info["trace_rows"] = page.eval_on_selector_all(".nc-tl-row", "els => els.length")
            info["trace_rounds_label"] = page.inner_text("#ncTraceRounds")
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(200)
            page.screenshot(path=str(SHOTS / "nc-02-done.png"), full_page=True, timeout=90000, animations="disabled")

            # ---------- DEMO MODE (backend tắt) vẫn phải hiện đủ 4 panel ----------
            page2 = b.new_page(viewport={"width": 1500, "height": 1000})
            page2.on("pageerror", lambda e: info["console_errors"].append(f"demo pageerror: {e}"))
            page2.goto(f"http://127.0.0.1:{PORT}/index.html?api=http://127.0.0.1:9", wait_until="load")
            page2.wait_for_timeout(3500)
            info["demo"] = {
                "notice": page2.is_visible("#demoNotice"),
                "what": page2.is_visible("#ncWhatPanel"),
                "round": page2.is_visible("#ncRoundPanel"),
                "stay": page2.is_visible("#ncStayPanel"),
                "steps": page2.eval_on_selector_all(".nc-step", "els => els.length"),
                "emp_name": page2.inner_text("#ncEmpName"),
                "emp_source": page2.inner_text("#ncEmpSource"),
                "total": page2.inner_text("#ncTotalNodes"),
            }
            page2.screenshot(path=str(SHOTS / "nc-03-demo-mode.png"), full_page=True, timeout=90000, animations="disabled")
            b.close()
    finally:
        httpd.shutdown()

    # tổng kết
    checks = info["checks"]
    for k in (
        "panel_mot_node",
        "panel_5_buoc",
        "panel_o_lai_truyen_di",
        "claim_text",
        "env_note",
        "sim_note",
        "randstad_real",
        "trace_visible",
    ):
        if not checks.get(k):
            ok = False
    if checks.get("step_count") != 5:
        ok = False
    if len(info.get("active_steps_seen") or []) < 3:
        ok = False
    if info["console_errors"]:
        ok = False
    info["PASS"] = ok
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
