"""Smoke test: chạy server uvicorn thật, gọi lần lượt 10 endpoint theo hợp đồng."""
from __future__ import annotations

import concurrent.futures
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

import websockets.sync.client as ws_client

# console Windows cp1252 -> ép UTF-8 để in tiếng Việt
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
WS = BASE.replace("http://", "ws://")
REPORT = []


def call(method: str, path: str, body=None, timeout=20):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            return r.status, json.loads(raw), (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8")), (time.perf_counter() - t0) * 1000


def check(name, cond, detail):
    REPORT.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + " :: " + detail)
    return bool(cond)


def main():
    ok = True

    # 1. /health
    st, body, ms = call("GET", "/health")
    ok &= check("GET /health", st == 200 and set(body) >= {"status", "db", "artifacts"}
                and body["status"] == "ok", f"{st} {body} ({ms:.0f}ms)")

    # 2. /api/clients
    st, body, ms = call("GET", "/api/clients?limit=5&offset=0")
    keys_ok = st == 200 and {"total", "items"} <= set(body) and isinstance(body["total"], int)
    if body.get("items"):
        keys_ok = keys_ok and set(body["items"][0]) == {"client_id", "name", "n_apps", "n_users", "n_jobs", "status"}
    ok &= check("GET /api/clients", keys_ok,
                f"{st} total={body.get('total')} n_items={len(body.get('items') or [])} "
                f"item0={json.dumps((body.get('items') or [{}])[0], ensure_ascii=False)} ({ms:.0f}ms)")

    first_client = (body.get("items") or [{}])[0].get("client_id", 0)

    # 3. /api/clients/{id}
    st, body, ms = call("GET", f"/api/clients/{first_client}")
    ok &= check("GET /api/clients/{client_id}", st == 200 and
                set(body) == {"client_id", "name", "n_apps", "n_users", "n_jobs", "top_skills", "status"},
                f"{st} {json.dumps({k: body.get(k) for k in ('client_id','name','n_apps','status')}, ensure_ascii=False)} "
                f"top_skills={ (body.get('top_skills') or [])[:4] } ({ms:.0f}ms)")

    st, body, ms = call("GET", "/api/clients/99999999")
    ok &= check("GET /api/clients/{id} 404", st == 404, f"{st} {body}")

    # 4. /api/graph/summary
    st, body, ms = call("GET", "/api/graph/summary")
    need = {"n_users", "n_jobs", "n_skills", "n_occupations", "n_edges_user_job",
            "n_edges_job_skill", "n_edges_user_skill", "n_clients", "sparsity_pct"}
    ok &= check("GET /api/graph/summary", st == 200 and set(body) == need,
                f"{st} {json.dumps(body, ensure_ascii=False)} ({ms:.0f}ms)")

    summary = body

    # 5. /api/recommend — thử nhiều user_id, ưu tiên user có gợi ý kèm matched_skills
    #    LƯU Ý: user_id là ID GỐC CareerBuilder (không phải 0..n_users-1), nên phải
    #    lấy id thật từ artifacts chứ không đoán 1,2,3 (đoán sẽ ra 0 item).
    item_ok = True
    best = None
    tried = []
    cand_ids = []
    try:
        import numpy as np
        from pathlib import Path
        npz = Path(__file__).resolve().parent.parent / "artifacts" / "v3" / "graph.npz"
        if npz.exists():
            with np.load(npz, allow_pickle=False) as z:
                ids = [int(x) for x in np.asarray(z["user_ids"]).tolist()]
                # chọn user có nhiều cạnh user-nghề nhất -> chắc chắn có gợi ý
                et = np.asarray(z["edge_type"])
                src = np.asarray(z["edge_index"])[0]
                mask = et == 3
                cnt = np.bincount(src[mask], minlength=len(ids))
                cand_ids = [ids[int(i)] for i in np.argsort(-cnt)[:6]]
                cand_ids += ids[:3]
    except Exception as exc:  # pragma: no cover
        print(f"(không lấy được user_id thật từ artifacts: {exc})")
    cand_ids += [1, 2, 3, 100, int(summary["n_users"])]
    for uid in cand_ids:
        st, body, ms = call("POST", "/api/recommend", {"user_id": uid, "k": 5})
        tried.append(uid)
        if st != 200:
            continue
        items = body.get("items") or []
        if items and items[0].get("matched_skills"):
            best = (st, body, ms)
            break
        if items and best is None:
            best = (st, body, ms)
    if best is None:
        st, body, ms = call("POST", "/api/recommend", {"user_id": cand_ids[0], "k": 5})
        best = (st, body, ms)
    st, body, ms = best
    items = body.get("items") or []
    if items:
        item_ok = set(items[0]) == {"job_id", "title", "score", "employer", "matched_skills"}
    ok &= check("POST /api/recommend", st == 200 and set(body) == {"user_id", "items"}
                and item_ok and len(items) > 0,
                f"{st} user_id={body.get('user_id')} tried={tried} n_items={len(items)} "
                f"item0={json.dumps(items[0], ensure_ascii=False) if items else None} ({ms:.0f}ms)")

    # 6. WS /ws/latency kết nối TRƯỚC khi start
    ticks = []

    def ws_latency_collect(stop_after=6.0):
        try:
            with ws_client.connect(WS + "/ws/latency", open_timeout=10) as ws:
                t0 = time.time()
                while time.time() - t0 < stop_after and len(ticks) < 5:
                    try:
                        msg = ws.recv(timeout=2)
                    except Exception:
                        continue
                    if msg:
                        ticks.append(json.loads(msg))
        except Exception as exc:
            ticks.append({"error": str(exc)})

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)
    fut_lat = pool.submit(ws_latency_collect, 8.0)
    time.sleep(0.6)

    # 7. /api/train/start
    st, body, ms = call("POST", "/api/train/start",
                        {"n_clients": 12, "rounds": 3, "algorithm": "fedavg", "local_epochs": 1})
    run_id = body.get("run_id")
    ok &= check("POST /api/train/start", st == 200 and isinstance(run_id, str) and len(run_id) >= 32,
                f"{st} run_id={run_id} source={body.get('data_source')} ({ms:.0f}ms)")

    # 8. WS /ws/train/{run_id}
    rounds_ws = []

    def ws_train_collect():
        try:
            with ws_client.connect(f"{WS}/ws/train/{run_id}", open_timeout=10) as ws:
                t0 = time.time()
                while time.time() - t0 < 10 and len(rounds_ws) < 3:
                    try:
                        msg = ws.recv(timeout=2)
                    except Exception:
                        continue
                    if msg:
                        rounds_ws.append(json.loads(msg))
        except Exception as exc:
            rounds_ws.append({"error": str(exc)})

    fut_train = pool.submit(ws_train_collect)

    # 9. /api/train/status/{run_id} — poll
    deadline = time.time() + 25
    status = None
    while time.time() < deadline:
        st, body, ms = call("GET", f"/api/train/status/{run_id}")
        status = (st, body)
        if st == 200 and body.get("status") in ("done", "failed"):
            break
        time.sleep(0.7)
    st, body = status
    need = {"run_id", "status", "round", "total_rounds", "metrics",
            "latency_p50_ms", "latency_p95_ms", "bytes_total"}
    m_ok = (not body.get("metrics")) or set(body["metrics"][0]) == {"round", "recall20", "ndcg20", "mrr20", "loss"}
    ok &= check("GET /api/train/status/{run_id}", st == 200 and need <= set(body) and m_ok,
                f"{st} status={body.get('status')} round={body.get('round')}/{body.get('total_rounds')} "
                f"p50={body.get('latency_p50_ms')} p95={body.get('latency_p95_ms')} "
                f"bytes_total={body.get('bytes_total')} n_metrics={len(body.get('metrics') or [])} "
                f"stopped={body.get('stopped')} ({ms:.0f}ms)")

    # 9b. t7 — field mới 'stopped' phải có mà KHÔNG mất field cũ
    ok &= check("status có trường 'stopped' (field cũ giữ nguyên)", "stopped" in body,
                f"keys={sorted(body.keys())}")

    # 10. /api/train/runs
    st, body, ms = call("GET", "/api/train/runs")
    rows = body.get("items") or []
    row_ok = (not rows) or set(rows[0]) >= {"run_id", "started_at", "n_clients", "rounds", "status"}
    ok &= check("GET /api/train/runs", st == 200 and "items" in body and row_ok,
                f"{st} n_runs={len(rows)} first={json.dumps(rows[0], ensure_ascii=False) if rows else None} ({ms:.0f}ms)")

    # ---------------------------------------------------------------- t7: STOP
    # 11. start run dài -> chờ >=2 vòng -> stop -> xác nhận dừng thật
    st, body, _ = call("POST", "/api/train/start",
                       {"n_clients": 10, "rounds": 40, "algorithm": "fedavg", "local_epochs": 1})
    stop_run = body.get("run_id")
    reached = 0
    deadline = time.time() + 25
    while time.time() < deadline:
        st_s, b_s, _ = call("GET", f"/api/train/status/{stop_run}")
        if st_s == 200:
            reached = int(b_s.get("round") or 0)
            if reached >= 2:
                break
        time.sleep(0.3)
    t_stop0 = time.perf_counter()
    st, body, ms = call("POST", f"/api/train/stop/{stop_run}")
    stop_elapsed = (time.perf_counter() - t_stop0) * 1000
    stop_ok = (st == 200 and body.get("run_id") == stop_run
               and body.get("status") == "stopped"
               and set(body) == {"run_id", "status", "stopped_at_round", "already_stopped"}
               and body.get("already_stopped") is False
               and 2 <= int(body.get("stopped_at_round") or 0) < 40)
    ok &= check("POST /api/train/stop/{run_id}", stop_ok,
                f"{st} body={json.dumps(body, ensure_ascii=False)} "
                f"reached_before_stop={reached} stop_duration={stop_elapsed:.0f}ms")

    # 12. status sau stop: status='stopped', stopped=true, vòng dừng < total_rounds
    st, body, ms = call("GET", f"/api/train/status/{stop_run}")
    after_ok = (st == 200 and body.get("status") == "stopped"
                and body.get("stopped") is True
                and int(body.get("round") or 0) < int(body.get("total_rounds") or 0)
                and int(body.get("stopped_at_round") or 0) == int(body.get("round") or 0))
    ok &= check("status sau stop: stopped + round < total_rounds", after_ok,
                f"{st} status={body.get('status')} stopped={body.get('stopped')} "
                f"round={body.get('round')}/{body.get('total_rounds')} "
                f"stopped_at_round={body.get('stopped_at_round')} n_metrics={len(body.get('metrics') or [])}")

    # 13. stop lần 2 -> already_stopped=true, status giữ nguyên
    st, body, ms = call("POST", f"/api/train/stop/{stop_run}")
    ok &= check("stop lần 2 -> already_stopped=true", st == 200 and body.get("already_stopped") is True
                and body.get("status") == "stopped",
                f"{st} body={json.dumps(body, ensure_ascii=False)}")

    # 14. stop run đã done -> already_stopped=true, status='done' (giữ nguyên)
    st, body, _ = call("POST", f"/api/train/stop/{run_id}")
    ok &= check("stop run đã done -> already_stopped=true", st == 200
                and body.get("already_stopped") is True and body.get("status") == "done",
                f"{st} body={json.dumps(body, ensure_ascii=False)} (run trước đó: {run_id})")

    # 15. stop run không tồn tại -> 404
    st, body, _ = call("POST", "/api/train/stop/00000000-0000-0000-0000-000000000000")
    ok &= check("stop run_id lạ -> 404", st == 404, f"{st} {body}")

    # 16. không rò task: start/stop liên tục 5 lần
    leak_rows = []
    for i in range(5):
        st, b, _ = call("POST", "/api/train/start",
                        {"n_clients": 6, "rounds": 40, "algorithm": "fedprox", "local_epochs": 1})
        rid = b.get("run_id")
        time.sleep(0.5)
        st_s, s, _ = call("POST", f"/api/train/stop/{rid}")
        st_g, g, _ = call("GET", f"/api/train/status/{rid}")
        leak_rows.append((st_s, s.get("status"), g.get("status"), g.get("round")))
    leak_ok = (len(leak_rows) == 5
               and all(r[0] == 200 and r[1] == "stopped" and r[2] == "stopped" for r in leak_rows))
    ok &= check("start/stop liên tục 5 lần không rò", leak_ok, f"rows={leak_rows}")

    fut_lat.result(timeout=30)
    fut_train.result(timeout=30)
    pool.shutdown(wait=False)

    tick_ok = bool(ticks) and "error" not in ticks[0]
    if tick_ok:
        need = {"type", "run_id", "round", "client_id", "latency_ms", "bytes_up", "bytes_down", "ts"}
        tick_ok = set(ticks[0]) >= need and ticks[0]["type"] == "tick"
    ok &= check("WS /ws/latency", tick_ok,
                f"n_ticks={len(ticks)} first={json.dumps(ticks[0], ensure_ascii=False) if ticks else None}")

    r_ok = bool(rounds_ws) and "error" not in rounds_ws[0]
    if r_ok:
        r_ok = rounds_ws[0].get("type") == "round" and {"round", "metrics", "latency_ms"} <= set(rounds_ws[0])
    ok &= check("WS /ws/train/{run_id}", r_ok,
                f"n_msgs={len(rounds_ws)} first={json.dumps(rounds_ws[0], ensure_ascii=False) if rounds_ws else None}")

    print("\n=== SUMMARY ===")
    n_pass = sum(1 for _, p, _ in REPORT if p)
    print(f"{n_pass}/{len(REPORT)} checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
