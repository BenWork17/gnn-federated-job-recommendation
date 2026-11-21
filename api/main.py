"""main.py — WebAPI FastAPI cho hệ gợi ý việc làm GNN + FL.

Chạy:
    python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
    python api/main.py --dry-run          # không cần PostgreSQL
    uvicorn api.main:app --port 8000      # dùng PostgreSQL nếu có

Chọn backend qua biến môi trường DSS_DRY_RUN=1 hoặc cờ --dry-run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:  # chạy dưới dạng package
    from .artifacts import ARTIFACT_DIR
    from .dashboard import router as dashboard_router
    from .db import make_store
    from .fl_sim import FLSimulator, TrainConfig
except ImportError:  # chạy trực tiếp trong thư mục api/
    from artifacts import ARTIFACT_DIR
    from dashboard import router as dashboard_router
    from db import make_store
    from fl_sim import FLSimulator, TrainConfig

# ------------------------------------------------------------------ khởi tạo
DRY_RUN = os.environ.get("DSS_DRY_RUN", "").lower() in ("1", "true", "yes")
STORE = make_store(dry_run=DRY_RUN, dsn=os.environ.get("DSS_PG_DSN") or None)
SIM = FLSimulator(STORE)

app = FastAPI(title="DSS Job Recommender API", version="3.0")

# UI chạy từ file:// (origin "null") hoặc http://127.0.0.1:8080 -> cần CORS mở
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)
app.include_router(dashboard_router)


def _reset_store(dry_run: bool):
    """(Re)khởi tạo store — dùng cho CLI --dry-run (phải chạy trước khi serve)."""
    global STORE, SIM
    STORE = make_store(dry_run=dry_run, dsn=os.environ.get("DSS_PG_DSN") or None)
    SIM = FLSimulator(STORE)


def _artifacts_ready() -> bool:
    return (ARTIFACT_DIR / "graph.npz").exists() and (ARTIFACT_DIR / "clients.json").exists()


def _data_source() -> str:
    """Nguồn dữ liệu thực tế: postgres | artifacts | demo."""
    if getattr(STORE, "kind", "") == "postgres" and getattr(STORE, "has_data", False):
        return "postgres"
    ds = getattr(STORE, "ds", None)
    if ds is not None:
        return ds.source
    fb = getattr(STORE, "fallback", None)
    if fb is not None:
        return fb.ds.source
    return "demo"


@app.on_event("startup")
async def _on_startup():
    # nạp sẵn dữ liệu nền để request đầu tiên không bị chậm
    try:
        _ = SIM.dataset
    except Exception as exc:  # pragma: no cover
        print(f"[startup] không nạp được dataset: {exc}")

    # PostgreSQL: 9 phép count(*) trên bảng 18M dòng mất ~20s -> đun nóng cache
    # ở nền để /api/graph/summary lần đầu đã nhanh (không chặn /health).
    if getattr(STORE, "kind", "") == "postgres" and getattr(STORE, "has_data", False):
        async def _warm():
            try:
                await asyncio.to_thread(STORE.summary)
            except Exception as exc:  # pragma: no cover
                print(f"[startup] không đun nóng được summary: {exc}")

        asyncio.create_task(_warm())


# ------------------------------------------------------------------ models
class RecommendRequest(BaseModel):
    user_id: int
    k: int = Field(default=20, ge=1, le=200)


class TrainStartRequest(BaseModel):
    n_clients: int = Field(default=50, ge=1, le=500)
    rounds: int = Field(default=10, ge=1, le=200)
    algorithm: Literal["fedavg", "fedprox"] = "fedavg"
    local_epochs: int = Field(default=1, ge=1, le=20)


# ------------------------------------------------------------------ endpoints
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "db": bool(STORE.db_ok()),
        "artifacts": bool(_artifacts_ready()),
    }


@app.get("/api/clients")
async def list_clients(
    limit: int = Query(default=50, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="n_apps"),
    order: Literal["asc", "desc"] = Query(default="desc"),
):
    total, items = STORE.clients(limit, offset)
    if sort in ("n_apps", "n_users", "n_jobs", "client_id", "name"):
        items = sorted(items, key=lambda r: (r.get(sort) is None, r.get(sort)),
                       reverse=(order == "desc"))
    return {"total": int(total), "items": items, "data_source": _data_source()}


@app.get("/api/clients/{client_id}")
async def get_client(client_id: int):
    row = STORE.client_detail(client_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"client_id {client_id} không tồn tại")
    return row


@app.get("/api/graph/summary")
async def graph_summary():
    return STORE.summary()


@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    return STORE.recommend(req.user_id, req.k)


@app.post("/api/train/start")
async def train_start(req: TrainStartRequest):
    cfg = TrainConfig(
        n_clients=req.n_clients, rounds=req.rounds,
        algorithm=req.algorithm, local_epochs=req.local_epochs,
    )
    run_id = await SIM.start(cfg)
    ds = SIM.dataset
    st = SIM.status(run_id) or {}
    return {
        "run_id": run_id,
        "status": "running",
        "n_clients": cfg.n_clients,
        "rounds": cfg.rounds,
        "algorithm": cfg.algorithm,
        "data_source": ds.source,
        "simulated_metrics": True,
        # danh sách client_id THẬT đã chọn (UI vẽ lưới node theo đây, không đoán)
        "participants": st.get("participants") or [],
        "note": ("Metric là mô phỏng; latency đo thật bằng perf_counter. "
                 f"Đồ thị: {'artifacts/v3' if ds.source == 'artifacts' else 'giả lập (artifacts/v3 chưa có)'}."),
    }


@app.post("/api/train/stop/{run_id}")
async def train_stop(run_id: str):
    """Dừng run phía server (t7 — THÊM MỚI, không đổi endpoint cũ).

    Runner tự thoát ở ĐẦU vòng kế tiếp nên vòng đang chạy vẫn hoàn tất và
    ``round_metrics`` không bị dở dang.
    """
    result = await SIM.stop(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"run_id {run_id} không tồn tại")
    return {
        "run_id": result["run_id"],
        "status": result["status"],
        "stopped_at_round": int(result.get("stopped_at_round") or 0),
        "already_stopped": bool(result.get("already_stopped", False)),
    }


@app.get("/api/train/status/{run_id}")
async def train_status(run_id: str):
    st = SIM.status(run_id)
    if st is None:
        raise HTTPException(status_code=404, detail=f"run_id {run_id} không tồn tại")
    return st


@app.get("/api/train/runs")
async def train_runs():
    live = {r["run_id"]: r for r in SIM.recent()}
    persisted = []
    try:
        persisted = STORE.runs()
    except Exception:
        persisted = []
    merged = []
    seen = set()
    for r in persisted:
        if r["run_id"] in live:
            r = {**r, **live[r["run_id"]]}
        merged.append(r)
        seen.add(r["run_id"])
    for rid, r in live.items():
        if rid not in seen:
            merged.append(r)
    merged.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return {"items": merged}


# ------------------------------------------------------------------ websockets
@app.websocket("/ws/latency")
async def ws_latency(ws: WebSocket):
    await ws.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=2000)

    async def cb(payload: dict):
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await queue.put(payload)

    SIM.subscribe_latency(cb)
    try:
        async def pump():
            while True:
                msg = await queue.get()
                await ws.send_text(json.dumps(msg, ensure_ascii=False))

        pump_task = asyncio.create_task(pump())
        try:
            while True:
                # giữ kết nối; bỏ qua message client gửi lên (ping)
                await ws.receive_text()
        finally:
            pump_task.cancel()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        SIM.unsubscribe_latency(cb)
        try:
            await ws.close()
        except Exception:
            pass


@app.websocket("/ws/train/{run_id}")
async def ws_train(ws: WebSocket, run_id: str):
    await ws.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)

    async def cb(payload: dict):
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await queue.put(payload)

    SIM.subscribe_train(run_id, cb)
    # gửi trạng thái hiện có ngay khi kết nối (UI đỡ phải chờ)
    try:
        st = SIM.status(run_id)
        if st is not None:
            for m in st.get("metrics", [])[-3:]:
                await ws.send_text(json.dumps({
                    "type": "round", "run_id": run_id, "round": m.get("round"),
                    "metrics": m, "latency_ms": 0.0,
                }, ensure_ascii=False))
    except Exception:
        pass
    try:
        async def pump():
            while True:
                msg = await queue.get()
                await ws.send_text(json.dumps(msg, ensure_ascii=False))

        pump_task = asyncio.create_task(pump())
        try:
            while True:
                await ws.receive_text()
        finally:
            pump_task.cancel()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        SIM.unsubscribe_train(run_id, cb)
        try:
            await ws.close()
        except Exception:
            pass


# ------------------------------------------------------------------ CLI
def _parse_args():
    ap = argparse.ArgumentParser(description="WebAPI GNN+FL job recommender")
    ap.add_argument("--dry-run", action="store_true",
                    help="chạy không cần PostgreSQL (in-memory)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--reload", action="store_true")
    return ap.parse_args()


def main():
    args = _parse_args()
    if args.dry_run:
        # phải đặt TRƯỚC khi import lại app (chế độ --reload)
        os.environ["DSS_DRY_RUN"] = "1"
        _reset_store(True)
    import uvicorn
    if args.reload:
        # reload cần đường dẫn import để tiến trình con tự nạp lại
        uvicorn.run("api.main:app" if Path.cwd().name != "api" else "main:app",
                    host=args.host, port=args.port, reload=True)
    else:
        # truyền thẳng app object: dùng đúng store vừa chọn (không import lại)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
