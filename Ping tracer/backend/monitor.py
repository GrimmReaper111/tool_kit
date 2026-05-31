from __future__ import annotations

import asyncio
import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Deque, Dict, List, Optional

from ping3 import ping


EventCallback = Callable[[dict], Awaitable[None]]


@dataclass
class DeviceState:
    target: str
    history: Deque[dict] = field(default_factory=lambda: deque(maxlen=60))
    successful_latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    consecutive_failures: int = 0
    last_success_ts: Optional[float] = None
    active_alerts: Dict[str, bool] = field(
        default_factory=lambda: {
            "latency_spike": False,
            "packet_loss": False,
            "dropout": False,
        }
    )


class MonitorManager:
    def __init__(self, emit_event: EventCallback) -> None:
        self._emit_event = emit_event
        self._states: Dict[str, DeviceState] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._latency_threshold_ms = 200.0
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._running

    @property
    def targets(self) -> List[str]:
        return list(self._states.keys())

    @property
    def latency_threshold_ms(self) -> float:
        return self._latency_threshold_ms

    async def get_state_snapshot(self) -> dict:
        return {
            "running": self._running,
            "targets": self.targets,
            "latency_threshold_ms": self._latency_threshold_ms,
        }

    async def start(self, targets: List[str], latency_threshold_ms: float) -> None:
        async with self._lock:
            await self._stop_locked()
            self._latency_threshold_ms = latency_threshold_ms
            self._running = True
            self._states = {target: DeviceState(target=target) for target in targets}
            for target, state in self._states.items():
                self._tasks[target] = asyncio.create_task(self._monitor_device(state))

        await self._emit_event(
            {
                "type": "monitoring_state",
                "data": await self.get_state_snapshot(),
            }
        )

    async def stop(self) -> None:
        async with self._lock:
            await self._stop_locked()

        await self._emit_event(
            {
                "type": "monitoring_state",
                "data": await self.get_state_snapshot(),
            }
        )

    async def _stop_locked(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        self._tasks.clear()
        self._states.clear()
        self._running = False

    async def _monitor_device(self, state: DeviceState) -> None:
        try:
            while True:
                now = time.time()
                latency_ms: Optional[float] = await asyncio.to_thread(
                    ping,
                    state.target,
                    timeout=1,
                    unit="ms",
                )

                success = latency_ms is not None and latency_ms is not False
                if success:
                    latency_value = float(latency_ms)
                    state.successful_latencies.append(latency_value)
                    state.consecutive_failures = 0
                    state.last_success_ts = now
                else:
                    latency_value = None
                    state.consecutive_failures += 1

                point = {
                    "timestamp": now,
                    "latency_ms": latency_value,
                    "success": success,
                }
                state.history.append(point)

                fails = sum(1 for p in state.history if not p["success"])
                packet_loss_pct = (fails / len(state.history)) * 100 if state.history else 0.0

                baseline_avg = None
                baseline_std = None
                if len(state.successful_latencies) >= 5:
                    baseline_avg = statistics.fmean(state.successful_latencies)
                    baseline_std = statistics.pstdev(state.successful_latencies)

                status = "healthy"
                anomaly_reasons: List[str] = []

                latency_spike = False
                if success and latency_value is not None:
                    if baseline_avg is not None and baseline_std is not None and baseline_std > 0:
                        if latency_value > baseline_avg + (3 * baseline_std):
                            latency_spike = True
                    if latency_value > self._latency_threshold_ms:
                        latency_spike = True

                packet_loss_critical = state.consecutive_failures >= 3
                no_success_for = (
                    None
                    if state.last_success_ts is None
                    else (now - state.last_success_ts)
                )
                dropout = False
                if state.last_success_ts is None and len(state.history) >= 5:
                    dropout = True
                if no_success_for is not None and no_success_for >= 10:
                    dropout = True

                if latency_spike:
                    status = "warning"
                    anomaly_reasons.append("High latency anomaly")

                if packet_loss_critical or dropout:
                    status = "critical"
                    if packet_loss_critical:
                        anomaly_reasons.append("Consecutive packet loss")
                    if dropout:
                        anomaly_reasons.append("Device not responding")

                await self._emit_new_anomaly_if_triggered(
                    state,
                    now,
                    latency_spike,
                    packet_loss_critical,
                    dropout,
                )

                snapshot = {
                    "target": state.target,
                    "timestamp": now,
                    "status": status,
                    "latency_ms": latency_value,
                    "packet_loss_pct": round(packet_loss_pct, 2),
                    "baseline_avg_ms": round(baseline_avg, 2) if baseline_avg is not None else None,
                    "baseline_std_ms": round(baseline_std, 2) if baseline_std is not None else None,
                    "consecutive_failures": state.consecutive_failures,
                    "anomaly_reasons": anomaly_reasons,
                    "history": list(state.history),
                }

                await self._emit_event({"type": "device_update", "data": snapshot})
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return

    async def _emit_new_anomaly_if_triggered(
        self,
        state: DeviceState,
        now: float,
        latency_spike: bool,
        packet_loss_critical: bool,
        dropout: bool,
    ) -> None:
        await self._handle_alert_toggle(
            state,
            alert_type="latency_spike",
            should_be_active=latency_spike,
            severity="amber",
            message="Latency spike detected",
            now=now,
        )
        await self._handle_alert_toggle(
            state,
            alert_type="packet_loss",
            should_be_active=packet_loss_critical,
            severity="red",
            message="3 or more consecutive packet losses",
            now=now,
        )
        await self._handle_alert_toggle(
            state,
            alert_type="dropout",
            should_be_active=dropout,
            severity="red",
            message="Device is flatlining / not responding",
            now=now,
        )

    async def _handle_alert_toggle(
        self,
        state: DeviceState,
        alert_type: str,
        should_be_active: bool,
        severity: str,
        message: str,
        now: float,
    ) -> None:
        is_active = state.active_alerts[alert_type]

        if should_be_active and not is_active:
            state.active_alerts[alert_type] = True
            await self._emit_event(
                {
                    "type": "anomaly",
                    "data": {
                        "target": state.target,
                        "timestamp": now,
                        "alert_type": alert_type,
                        "severity": severity,
                        "message": message,
                    },
                }
            )
        elif not should_be_active and is_active:
            state.active_alerts[alert_type] = False
