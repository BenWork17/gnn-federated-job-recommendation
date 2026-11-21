"""fl_sim.py — runner mô phỏng Federated Learning chạy nền.

Điểm quan trọng: **latency được đo THẬT** bằng ``time.perf_counter()`` cho từng
client mỗi vòng (đo thời gian dựng "cập nhật cục bộ" + serialize seed của client),
rồi ghi vào ``node_latency``. Metric (recall20/ndcg20/mrr20/loss) là mô phỏng
giảm dần theo vòng, KHÔNG phải kết quả huấn luyện GNN thật — response ghi rõ
``simulated_metrics`` để người đọc không nhầm.

Khi ``artifacts/v3`` có sẵn, runner đọc ``client_of_job`` / ``client_of_user``
thật để chọn client (nhóm theo employer) và kích thước "model update" tỉ lệ
thuận với số node cục bộ; nếu chưa có thì dùng số liệu giả lập và báo
``data_source = "demo"``.
"""
from __future__ import annotations

import asyncio
import math
import random
import time
import uuid
import zlib
from dataclasses import dataclass, field
from typing import Callable, Awaitable

import numpy as np

try:
    from .artifacts import get_dataset, Dataset
except ImportError:
    from artifacts import get_dataset, Dataset

MODEL_BYTES_PER_PARAM = 4   # float32
N_PARAMS = 24_000           # "kích thước model" giả lập (≈96 KB mỗi chiều)


@dataclass
class TrainConfig:
    n_clients: int = 50
    rounds: int = 10
    algorithm: str = "fedavg"      # fedavg | fedprox
    local_epochs: int = 1
    round_seconds: float = 0.6     # nhịp mô phỏng mỗi vòng (để UI kịp vẽ)
    seed: int = 7

    def __post_init__(self):
        self.n_clients = max(1, min(int(self.n_clients), 500))
        self.rounds = max(1, min(int(self.rounds), 200))
        self.local_epochs = max(1, min(int(self.local_epochs), 20))
        if self.algorithm not in ("fedavg", "fedprox"):
            self.algorithm = "fedavg"


@dataclass
class RunState:
    run_id: str
    cfg: TrainConfig
    status: str = "running"          # running | stopping | stopped | done | failed
    round: int = 0
    data_source: str = "demo"
    metrics: list = field(default_factory=list)
    latencies: list = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    stop_requested: bool = False     # cờ yêu cầu dừng (runner check ở ĐẦU mỗi vòng)
    stopped_at_round: int = 0        # vòng cuối đã hoàn thành khi dừng
    participants: list = field(default_factory=list)   # client_id tham gia thật

    @property
    def stopped(self) -> bool:
        return self.status == "stopped"

    # ---- tổng hợp ----
    def summary(self) -> dict:
        lat = np.array([x["latency_ms"] for x in self.latencies], dtype=np.float64)
        return {
            "run_id": self.run_id,
            "status": self.status,
            "round": self.round,
            "total_rounds": self.cfg.rounds,
            "metrics": list(self.metrics),
            "latency_p50_ms": round(float(np.percentile(lat, 50)), 4) if lat.size else 0.0,
            "latency_p95_ms": round(float(np.percentile(lat, 95)), 4) if lat.size else 0.0,
            "bytes_total": int(sum(x["bytes_up"] + x["bytes_down"] for x in self.latencies)),
            "data_source": self.data_source,
            "simulated_metrics": True,
            # --- thêm mới (t7), KHÔNG đổi các field cũ ở trên ---
            "stopped": bool(self.status == "stopped"),
            "stopped_at_round": int(self.stopped_at_round),
            # danh sách client THẬT tham gia (UI vẽ lưới node theo danh sách này
            # thay vì đoán id -> tránh lệch kiểu "10/13 node báo cáo")
            "participants": [int(c["client_id"]) for c in self.participants],
        }


class FLSimulator:
    """Quản lý các lần chạy: giữ trạng thái, fan-out sự kiện tới WebSocket."""

    def __init__(self, store):
        self.store = store
        self.runs: dict[str, RunState] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._subscribers: list[Callable[[dict], Awaitable[None]]] = []
        self._train_subscribers: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}
        self._start_event = asyncio.Event()  # báo "đã có run mới" cho /ws/latency
        self._dataset: Dataset | None = None
        self._dataset_loaded = False

    # ---- dataset ----
    @property
    def dataset(self) -> Dataset:
        if not self._dataset_loaded:
            self._dataset = get_dataset(prefer_artifacts=True)
            self._dataset_loaded = True
        return self._dataset

    # ---- pub/sub ----
    def subscribe_latency(self, cb):
        self._subscribers.append(cb)

    def unsubscribe_latency(self, cb):
        if cb in self._subscribers:
            self._subscribers.remove(cb)

    def subscribe_train(self, run_id: str, cb):
        self._train_subscribers.setdefault(run_id, []).append(cb)

    def unsubscribe_train(self, run_id: str, cb):
        lst = self._train_subscribers.get(run_id, [])
        if cb in lst:
            lst.remove(cb)

    async def _emit_latency(self, payload: dict):
        for cb in list(self._subscribers):
            try:
                await cb(payload)
            except Exception:
                pass

    async def _emit_train(self, run_id: str, payload: dict):
        for cb in list(self._train_subscribers.get(run_id, [])):
            try:
                await cb(payload)
            except Exception:
                pass

    # ---- chọn client ----
    def pick_clients(self, n: int, rng: random.Random) -> list:
        """Chọn n client (employer). Ưu tiên client lớn nếu có artifacts."""
        rows = self.dataset.client_rows()
        if not rows:
            return [{"client_id": i, "n_apps": 10, "n_users": 10, "n_jobs": 5} for i in range(n)]
        if len(rows) > n:
            order = sorted(rows, key=lambda r: -r["n_apps"])
            head = order[: int(n * 0.7)]
            tail = order[int(n * 0.7):]
            chosen = head + rng.sample(tail, max(0, n - len(head)))
        else:
            chosen = list(rows)
        return chosen[:n]

    # ---- ước lượng "bytes" upload/download theo client ----
    def _bytes_for(self, client: dict, rng: random.Random) -> tuple:
        n_users = int(client.get("n_users") or 1)
        local_edges = max(1, n_users + int(client.get("n_apps") or 0))
        # model delta co lại theo sparsity cục bộ + gradient compression
        frac = min(1.0, 0.05 + 0.35 * (local_edges / max(1.0, n_users * 8.0)))
        up = int(N_PARAMS * MODEL_BYTES_PER_PARAM * frac * rng.uniform(0.9, 1.1))
        down = int(N_PARAMS * MODEL_BYTES_PER_PARAM * rng.uniform(0.98, 1.02))
        return max(1, up), max(1, down)

    # ---- mô phỏng 1 lượt "local update" và ĐO THẬT ----
    def _local_update(self, client: dict, cfg: TrainConfig) -> float:
        """Trả latency ms đo bằng perf_counter cho công việc cục bộ của client."""
        t0 = time.perf_counter()
        # khối lượng tính toán tỉ lệ với số node cục bộ; chạy numpy thật để đo
        n_local = max(1, int(client.get("n_users") or 1) + int(client.get("n_jobs") or 1))
        dim = min(256, max(32, n_local))
        # seed tiền định (hash() của str bị randomize theo process -> dùng crc32)
        seed_key = zlib.crc32(
            f"{client.get('client_id')}|{cfg.local_epochs}|{cfg.algorithm}".encode()
        )
        rng = np.random.default_rng(seed_key % (2 ** 32))
        w = rng.standard_normal((dim, dim), dtype=np.float32) * 0.01
        acc = np.zeros((dim, dim), dtype=np.float32)
        for _ in range(cfg.local_epochs):
            # "gradient step" giả lập — công việc CPU thật
            acc += (w @ w.T).astype(np.float32)
            w -= 0.001 * acc
        # serialize "cập nhật" (giống chi phí thật khi upload)
        payload = w.tobytes()
        _ = len(payload)
        if cfg.algorithm == "fedprox":
            # proxy term: thêm phép tính như bản FedProx thật
            _ = float(np.linalg.norm(w))
        return (time.perf_counter() - t0) * 1000.0

    # ---- vòng chạy nền ----
    def _metric_for(self, rnd: int, cfg: TrainConfig, rng: random.Random) -> dict:
        progress = rnd / max(1, cfg.rounds)
        base_recall = 0.30 if cfg.algorithm == "fedavg" else 0.315
        # học nhanh ở các vòng đầu, sau đó bão hoà
        gain = 1.0 - math.exp(-3.2 * progress)
        recall = base_recall + (0.62 - base_recall) * gain
        ndcg = recall * 0.78
        mrr = recall * 0.55
        loss = 1.85 * math.exp(-2.6 * progress) + 0.24 + rng.uniform(-0.01, 0.01)
        jitter = 1.0 + rng.uniform(-0.02, 0.02)
        return {
            "round": rnd,
            "recall20": round(min(0.95, recall * jitter), 6),
            "ndcg20": round(min(0.95, ndcg * jitter), 6),
            "mrr20": round(min(0.95, mrr * jitter), 6),
            "loss": round(max(0.01, loss), 6),
        }

    async def _run(self, state: RunState):
        cfg = state.cfg
        rng = random.Random(cfg.seed + zlib.crc32(state.run_id.encode()) % 10_000)
        state.data_source = self.dataset.source
        # clients đã chọn đồng bộ trong start() -> state.participants có ngay
        clients = state.participants or self.pick_clients(cfg.n_clients, rng)
        state.participants = list(clients)
        try:
            for rnd in range(1, cfg.rounds + 1):
                # ---- CHECK CỜ DỪNG Ở ĐẦU MỖI VÒNG (không phải giữa vòng) ----
                if state.stop_requested:
                    break
                tick_rows = []
                # mỗi client "tính local update" và được đo latency thật
                for c in clients:
                    latency_ms = self._local_update(c, cfg)
                    up, down = self._bytes_for(c, rng)
                    tick = {
                        "type": "tick",
                        "run_id": state.run_id,
                        "round": rnd,
                        "client_id": int(c["client_id"]),
                        "latency_ms": round(latency_ms, 4),
                        "bytes_up": up,
                        "bytes_down": down,
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                    }
                    tick_rows.append(tick)
                    state.latencies.append(tick)
                    await self._emit_latency(tick)
                    # nhường event loop để WebSocket kịp gửi
                    if len(tick_rows) % 8 == 0:
                        await asyncio.sleep(0)

                metrics = self._metric_for(rnd, cfg, rng)
                state.round = rnd
                state.metrics.append(metrics)

                # ghi xuống store (PostgreSQL hoặc in-memory)
                await asyncio.to_thread(self.store.add_round, state.run_id, rnd, metrics, tick_rows)

                await self._emit_train(state.run_id, {
                    "type": "round",
                    "run_id": state.run_id,
                    "round": rnd,
                    "metrics": metrics,
                    "latency_ms": round(float(np.mean([t["latency_ms"] for t in tick_rows])), 4)
                    if tick_rows else 0.0,
                })

                # nhịp mô phỏng còn lại của vòng (ngắt ngắn để phản hồi stop nhanh)
                spent = sum(t["latency_ms"] for t in tick_rows) / 1000.0
                remain = cfg.round_seconds - spent
                if remain > 0:
                    await asyncio.sleep(min(remain, cfg.round_seconds))

            # ---- kết thúc: stopped nếu có cờ dừng, ngược lại done ----
            state.finished_at = time.time()
            if state.stop_requested:
                state.status = "stopped"
                state.stopped_at_round = int(state.round)
                await asyncio.to_thread(self.store.set_run_status, state.run_id,
                                        "stopped", state.stopped_at_round)
                await self._emit_train(state.run_id, {
                    "type": "round", "run_id": state.run_id, "round": state.round,
                    "metrics": state.metrics[-1] if state.metrics else {},
                    "latency_ms": 0.0, "status": "stopped",
                    "stopped": True, "stopped_at_round": state.stopped_at_round,
                })
            else:
                state.status = "done"
                await asyncio.to_thread(self.store.set_run_status, state.run_id, "done")
                await self._emit_train(state.run_id, {
                    "type": "round", "run_id": state.run_id, "round": cfg.rounds,
                    "metrics": state.metrics[-1] if state.metrics else {}, "latency_ms": 0.0,
                    "status": "done", "stopped": False,
                    "stopped_at_round": state.stopped_at_round,
                })
        except asyncio.CancelledError:
            state.status = "stopped" if state.stop_requested else "failed"
            if state.status == "stopped":
                state.stopped_at_round = int(state.round)
            await asyncio.to_thread(self.store.set_run_status, state.run_id,
                                    state.status, state.stopped_at_round or None)
            raise
        except Exception as exc:
            state.status = "failed"
            await asyncio.to_thread(self.store.set_run_status, state.run_id, "failed")
            print(f"[fl_sim] run {state.run_id} failed: {exc}")
        finally:
            state.finished_at = state.finished_at or time.time()

    # ---- API nội bộ ----
    async def start(self, cfg: TrainConfig, run_id: str | None = None) -> str:
        run_id = run_id or str(uuid.uuid4())
        # dọn task đã xong để không tích luỹ qua nhiều lần start/stop
        self._prune_tasks()
        state = RunState(run_id=run_id, cfg=cfg)
        # chọn client NGAY (đồng bộ) để response start trả được danh sách thật;
        # runner dùng lại đúng danh sách này -> lưới node UI khớp 100%.
        rng = random.Random(cfg.seed + zlib.crc32(run_id.encode()) % 10_000)
        state.participants = list(self.pick_clients(cfg.n_clients, rng))
        self.runs[run_id] = state
        # ghi header run ngay để /api/train/runs thấy
        await asyncio.to_thread(self.store.create_run, run_id, cfg.n_clients, cfg.rounds)
        self._start_event.set()
        task = asyncio.create_task(self._run(state))
        self._tasks[run_id] = task
        task.add_done_callback(lambda _t, rid=run_id: self._on_task_done(rid))
        return run_id

    def _on_task_done(self, run_id: str):
        """Task kết thúc -> đảm bảo không giữ task chết trong dict."""
        task = self._tasks.get(run_id)
        if task is not None and task.done():
            self._tasks.pop(run_id, None)
        try:
            # lấy exception (nếu có) để asyncio không cảnh báo "never retrieved"
            if task is not None:
                task.exception()
        except (asyncio.CancelledError, Exception):
            pass

    def _prune_tasks(self):
        for rid in [r for r, t in self._tasks.items() if t.done()]:
            self._tasks.pop(rid, None)

    async def stop(self, run_id: str) -> dict | None:
        """Yêu cầu dừng run. Trả dict kết quả, hoặc None nếu run_id không tồn tại.

        Cơ chế: set cờ ``stop_requested`` -> runner tự thoát ở ĐẦU vòng kế tiếp.
        Vòng đang chạy vẫn hoàn tất (để round_metrics không bị dở dang), sau đó
        runner ghi round cuối cùng rồi dừng.
        """
        state = self.runs.get(run_id)
        if state is None:
            # run cũ chỉ còn trong DB -> coi là đã kết thúc, không dừng được nữa
            persisted = self.store.run_status(run_id)
            if persisted is None:
                return None
            return {
                "run_id": run_id,
                "status": persisted.get("status", "done"),
                "stopped_at_round": int(persisted.get("round") or 0),
                "already_stopped": True,
            }

        if state.status in ("done", "failed", "stopped"):
            return {
                "run_id": run_id,
                "status": state.status,
                "stopped_at_round": int(state.stopped_at_round or state.round),
                "already_stopped": True,
            }

        # run đang chạy -> bật cờ, chờ runner tự thoát (tối đa ~1 vòng)
        # GIỮ status='running' trong lúc chờ để không phá tập giá trị hợp đồng
        # (running|done|failed|stopped) mà ui-dev đang đọc.
        state.stop_requested = True
        task = self._tasks.get(run_id)
        if task is not None and not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=30.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
            except Exception:
                pass
        # runner đã set status='stopped' trong _run; nếu vì lý do gì chưa, chốt lại
        if state.status not in ("stopped", "done", "failed"):
            state.status = "stopped"
            state.stopped_at_round = int(state.round)
            await asyncio.to_thread(self.store.set_run_status, run_id, "stopped")
        return {
            "run_id": run_id,
            "status": state.status,
            "stopped_at_round": int(state.stopped_at_round or state.round),
            "already_stopped": False,
        }

    def status(self, run_id: str):
        st = self.runs.get(run_id)
        if st is not None:
            return st.summary()
        # run cũ tồn tại trong DB nhưng không còn trong RAM
        persisted = self.store.run_status(run_id)
        if persisted is not None and "stopped" not in persisted:
            persisted["stopped"] = persisted.get("status") == "stopped"
            persisted.setdefault("stopped_at_round", int(persisted.get("round") or 0))
        return persisted

    def recent(self):
        rows = [
            {
                "run_id": st.run_id,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.started_at)),
                "n_clients": st.cfg.n_clients,
                "rounds": st.cfg.rounds,
                "status": st.status,
            }
            for st in self.runs.values()
        ]
        rows.sort(key=lambda r: r["started_at"], reverse=True)
        return rows
