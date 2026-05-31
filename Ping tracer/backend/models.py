from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class StartMonitoringRequest(BaseModel):
    targets: List[str] = Field(..., min_length=1, max_length=16)
    latency_threshold_ms: float = Field(default=200.0, ge=1.0, le=5000.0)


class StopMonitoringResponse(BaseModel):
    success: bool


class MonitoringStateResponse(BaseModel):
    running: bool
    targets: List[str]
    latency_threshold_ms: float
