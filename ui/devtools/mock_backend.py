"""Mock backend cho UI — implement ĐÚNG hợp đồng API đã chốt với api-dev.

Mục đích: test UI ở chế độ LIVE trong khi backend thật (api/main.py) đang được
viết song song. Không phải backend của sản phẩm; chỉ dùng để kiểm thử UI.

Chạy:  python ui/devtools/mock_backend.py --port 8000
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="FL UI mock backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# ---------------------------------------------------------------- dữ liệu giả

EMP_BASES = [
    "Công ty CP Công nghệ", "TNHH Thương mại Dịch vụ", "Công ty TNHH Sản xuất",
    "Tập đoàn Đầu tư", "Công ty CP Xây dựng", "TNHH Logistics", "Công ty CP Giáo dục",
    "TNHH Truyền thông", "Công ty CP Dược phẩm", "TNHH Cơ khí", "Công ty CP Bán lẻ",
    "TNHH Phần mềm", "Công ty CP Nông nghiệp", "TNHH Vận tải", "Công ty CP Bảo hiểm",
    "TNHH Thép", "Công ty CP Dệt may", "TNHH Thực phẩm", "Công ty CP Năng lượng",
    "TNHH Bất động sản",
]
EMP_TAILS = [
    "An Phát", "Minh Long", "Hoà Bình", "Thái Dương", "Đông Á", "Sao Việt", "Phú Mỹ",
    "Trường Sơn", "Bình Minh", "Hồng Hà", "Nam Việt", "Tân Tiến", "Vạn Xuân", "Kim Ngân",
    "Đại Phát", "Hải Đăng", "Phương Đông", "Tiến Đạt", "Quang Minh", "Thành Công",
]
SKILLS = [
    "Python", "SQL", "Excel", "Java", "JavaScript", "React", "Giao tiếp", "Quản lý dự án",
    "Phân tích dữ liệu", "Kế toán", "AutoCAD", "AWS", "Docker", "Kubernetes", "Git",
    "Tiếng Anh", "Bán hàng", "Marketing", "SEO", "Figma", "Django", "FastAPI", "PyTorch",
    "Machine Learning", "Power BI", "Tableau", "SAP", "Tài chính", "Logistics", "Đàm phán",
]


def _make_clients(n: int, seed: int = 20261108) -> list[dict[str, Any]]:
    rnd = random.Random(seed)
    out: list[dict[str, Any]] = []
    for i in range(n):
        n_apps = int(10 + (rnd.random() ** 2.6) * 2600)
        out.append(
            {
                "client_id": 1000 + i,
                "name": f"{rnd.choice(EMP_BASES)} {rnd.choice(EMP_TAILS)}"
                + (f" {rnd.randint(10, 99)}" if rnd.random() > 0.6 else ""),
                "n_apps": n_apps,
                "n_users": max(1, int(n_apps * (0.4 + rnd.random() * 0.8))),
                "n_jobs": max(1, int(n_apps * (0.25 + rnd.random() * 0.5))),
                "status": "active" if rnd.random() > 0.28 else "idle",
            }
        )
    out.sort(key=lambda c: c["n_apps"], reverse=True)
    # trải client_id ngẫu nhiên để bảng trông giống dữ liệu thật
    ids = [1000 + i for i in range(n)]
    rnd.shuffle(ids)
    for c, cid in zip(out, ids):
        c["client_id"] = cid
    return out


CLIENTS = _make_clients(1474)
CLIENT_BY_ID = {c["client_id"]: c for c in CLIENTS}

RUNS: dict[str, dict[str, Any]] = {}
TICKS_BY_RUN: dict[str, list[dict[str, Any]]] = {}


class StartBody(BaseModel):
    n_clients: int = 50
    rounds: int = 10
    algorithm: str = "fedavg"
    local_epochs: int = 1


# ---------------------------------------------------------------- endpoints


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "db": True, "artifacts": True}


@app.get("/api/clients")
async def clients(limit: int = 50, offset: int = 0, sort: str = "n_apps", order: str = "desc"):
    rows = sorted(CLIENTS, key=lambda c: c.get(sort, c["n_apps"]), reverse=(order != "asc"))
    page = rows[offset : offset + min(max(limit, 1), 2000)]
    return {"total": len(rows), "items": page}


@app.get("/api/clients/{client_id}")
async def client_detail(client_id: int):
    c = dict(CLIENT_BY_ID.get(client_id) or CLIENTS[0])
    rnd = random.Random(client_id)
    c["top_skills"] = rnd.sample(SKILLS, 8)
    return c


@app.get("/api/graph/summary")
async def graph_summary():
    return {
        "n_users": 389708,
        "n_jobs": 1092096,
        "n_skills": 8316,
        "n_occupations": 709,
        "n_edges_user_job": 1753901,
        "n_edges_job_skill": 1317000,
        "n_edges_user_skill": 2480000,
        "n_clients": len(CLIENTS),
        "sparsity_pct": 0.43,
    }


@app.post("/api/train/start")
async def train_start(body: StartBody):
    run_id = str(uuid.uuid4())
    participants = [c["client_id"] for c in CLIENTS[: max(1, min(body.n_clients, len(CLIENTS)))]]
    RUNS[run_id] = {
        "run_id": run_id,
        "status": "running",
        "round": 0,
        "total_rounds": max(1, body.rounds),
        "metrics": [],
        "latency_p50_ms": None,
        "latency_p95_ms": None,
        "bytes_total": 0,
        "algorithm": body.algorithm,
        "local_epochs": body.local_epochs,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "_participants": participants,
    }
    TICKS_BY_RUN[run_id] = []
    asyncio.create_task(_simulate(run_id))
    return {"run_id": run_id}


@app.get("/api/train/status/{run_id}")
async def train_status(run_id: str):
    r = RUNS.get(run_id)
    if not r:
        return {"run_id": run_id, "status": "failed", "round": 0, "total_rounds": 0,
                "metrics": [], "latency_p50_ms": None, "latency_p95_ms": None,
                "bytes_total": 0}
    return {k: v for k, v in r.items() if not k.startswith("_")}


@app.get("/api/train/runs")
async def train_runs():
    items = [
        {
            "run_id": r["run_id"],
            "started_at": r["started_at"],
            "n_clients": len(r["_participants"]),
            "rounds": r["total_rounds"],
            "status": r["status"],
        }
        for r in RUNS.values()
    ]
    return {"items": items[-20:]}


@app.websocket("/ws/latency")
async def ws_latency(ws: WebSocket):
    await ws.accept()
    try:
        sent = 0
        while True:
            await asyncio.sleep(0.35)
            active = [r for r in RUNS.values() if r["status"] == "running"]
            if not active:
                continue
            r = active[-1]
            ticks = TICKS_BY_RUN.get(r["run_id"], [])
            while sent < len(ticks):
                await ws.send_text(json.dumps(ticks[sent]))
                sent += 1
    except (WebSocketDisconnect, RuntimeError):
        return


@app.websocket("/ws/train/{run_id}")
async def ws_train(ws: WebSocket, run_id: str):
    await ws.accept()
    try:
        seen = 0
        while True:
            await asyncio.sleep(0.3)
            r = RUNS.get(run_id)
            if not r:
                continue
            mets = r["metrics"]
            while seen < len(mets):
                m = mets[seen]
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "round",
                            "round": m["round"],
                            "metrics": m,
                            "latency_ms": r["latency_p50_ms"],
                        }
                    )
                )
                seen += 1
            if r["status"] in ("done", "failed"):
                await asyncio.sleep(0.2)
                return
    except (WebSocketDisconnect, RuntimeError):
        return


def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    i = (len(s) - 1) * p
    lo, hi = int(i // 1), int(-(-i // 1))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (i - lo)


async def _simulate(run_id: str) -> None:
    r = RUNS[run_id]
    rnd = random.Random()
    recall = 0.30
    base = 40.0
    for rnd_i in range(1, r["total_rounds"] + 1):
        latencies: list[float] = []
        for cid in r["_participants"]:
            await asyncio.sleep(0.004)
            slow = 3.4 if rnd.random() > 0.88 else 1.0
            lat = max(6.0, base * (0.55 + rnd.random() * 0.95) * slow)
            await asyncio.sleep(0)
            t0 = time.perf_counter()
            _ = t0  # đo latency giả lập bằng công thức, không đo thật
            bu = 108608 + rnd.randint(0, 8000)
            bd = 108608 + rnd.randint(0, 8000)
            r["bytes_total"] += bu + bd
            latencies.append(lat)
            TICKS_BY_RUN[run_id].append(
                {
                    "type": "tick",
                    "run_id": run_id,
                    "round": rnd_i,
                    "client_id": cid,
                    "latency_ms": round(lat, 1),
                    "bytes_up": bu,
                    "bytes_down": bd,
                    "ts": int(time.time() * 1000),
                }
            )
        r["round"] = rnd_i
        r["latency_p50_ms"] = round(_pct(latencies, 0.5), 1)
        r["latency_p95_ms"] = round(_pct(latencies, 0.95), 1)
        recall = min(0.63, recall + (0.63 - recall) * 0.26 + (rnd.random() - 0.5) * 0.01)
        r["metrics"].append(
            {
                "round": rnd_i,
                "recall20": round(recall, 4),
                "ndcg20": round(recall * 0.56, 4),
                "mrr20": round(recall * 0.57, 4),
                "loss": round(max(0.09, 1.6 * (0.78 ** rnd_i) + rnd.random() * 0.02), 4),
            }
        )
        base = 34 + rnd.random() * 28
        await asyncio.sleep(1.0)
    r["status"] = "done"


if __name__ == "__main__":
    import uvicorn

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")
