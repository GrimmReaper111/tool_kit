from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.models import MonitoringStateResponse, StartMonitoringRequest, StopMonitoringResponse
from backend.monitor import MonitorManager


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Ping Tracer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sockets: Set[WebSocket] = set()
sockets_lock = asyncio.Lock()


async def broadcast(message: dict) -> None:
    stale: list[WebSocket] = []
    async with sockets_lock:
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)

        for ws in stale:
            sockets.discard(ws)


manager = MonitorManager(emit_event=broadcast)

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/monitor/state", response_model=MonitoringStateResponse)
async def get_monitoring_state() -> MonitoringStateResponse:
    state = await manager.get_state_snapshot()
    return MonitoringStateResponse(**state)


@app.post("/api/monitor/start")
async def start_monitoring(payload: StartMonitoringRequest) -> MonitoringStateResponse:
    cleaned = []
    seen = set()
    for target in payload.targets:
        value = target.strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)

    if not cleaned:
        return MonitoringStateResponse(
            running=False,
            targets=[],
            latency_threshold_ms=payload.latency_threshold_ms,
        )

    await manager.start(cleaned[:16], payload.latency_threshold_ms)
    state = await manager.get_state_snapshot()
    return MonitoringStateResponse(**state)


@app.post("/api/monitor/stop", response_model=StopMonitoringResponse)
async def stop_monitoring() -> StopMonitoringResponse:
    await manager.stop()
    return StopMonitoringResponse(success=True)


@app.websocket("/ws")
async def websocket_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    async with sockets_lock:
        sockets.add(websocket)

    await websocket.send_json(
        {
            "type": "monitoring_state",
            "data": await manager.get_state_snapshot(),
        }
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with sockets_lock:
            sockets.discard(websocket)
