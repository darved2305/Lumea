"""
Telemetry – SSE real-time telemetry stream with simulated vital signs.

Endpoints:
  GET /api/telemetry/stream   – Server-Sent Events stream (simulated vitals)
  GET /api/telemetry/latest   – latest telemetry snapshot
  GET /api/telemetry/history  – recent telemetry windows
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.security import get_current_user, decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_telemetry_store: Dict[str, List[dict]] = {}  # user_id -> [reading, ...]

# ---------------------------------------------------------------------------
# Simulated vital sign generator
# ---------------------------------------------------------------------------

# Baseline values for a "healthy" adult
_BASELINES = {
    "heart_rate":       {"base": 72, "jitter": 5, "unit": "bpm"},
    "systolic_bp":      {"base": 118, "jitter": 6, "unit": "mmHg"},
    "diastolic_bp":     {"base": 76, "jitter": 4, "unit": "mmHg"},
    "spo2":             {"base": 97.5, "jitter": 0.8, "unit": "%"},
    "respiratory_rate": {"base": 16, "jitter": 2, "unit": "bpm"},
    "temperature":      {"base": 98.4, "jitter": 0.3, "unit": "°F"},
    "stress_level":     {"base": 2.5, "jitter": 0.8, "unit": "score"},
    "sleep_hours":      {"base": 7.2, "jitter": 0.5, "unit": "hrs"},
    "creatinine":       {"base": 1.0, "jitter": 0.15, "unit": "mg/dL"},
    "urea":             {"base": 14, "jitter": 2.5, "unit": "mg/dL"},
    "egfr":             {"base": 95, "jitter": 5, "unit": "mL/min"},
    "sodium":           {"base": 140, "jitter": 2, "unit": "mEq/L"},
    "alt":              {"base": 25, "jitter": 5, "unit": "U/L"},
    "ast":              {"base": 22, "jitter": 4, "unit": "U/L"},
    "bilirubin_total":  {"base": 0.8, "jitter": 0.15, "unit": "mg/dL"},
    "glucose":          {"base": 95, "jitter": 8, "unit": "mg/dL"},
}

# Occasional spike profiles (simulate realistic anomalies)
_SPIKE_PROFILES = [
    {"metric": "heart_rate", "delta": 25, "duration_ticks": 3},
    {"metric": "systolic_bp", "delta": 20, "duration_ticks": 4},
    {"metric": "stress_level", "delta": 3.5, "duration_ticks": 5},
    {"metric": "glucose", "delta": 35, "duration_ticks": 4},
    {"metric": "respiratory_rate", "delta": 6, "duration_ticks": 3},
    {"metric": "spo2", "delta": -3, "duration_ticks": 3},
]


class _SimState:
    """Per-user simulation state."""
    def __init__(self):
        self.tick = 0
        self.active_spike: Optional[dict] = None
        self.spike_remaining = 0
        self.phase_offset = random.uniform(0, 2 * math.pi)

    def generate(self) -> dict:
        self.tick += 1
        t = self.tick
        readings: Dict[str, float] = {}

        for name, cfg in _BASELINES.items():
            base = cfg["base"]
            jitter = cfg["jitter"]
            # Circadian-like slow wave + random jitter
            wave = math.sin(t * 0.05 + self.phase_offset) * jitter * 0.4
            noise = random.gauss(0, jitter * 0.6)
            val = base + wave + noise
            readings[name] = round(val, 2)

        # Random spike injection (~8% chance per tick)
        if self.spike_remaining <= 0 and random.random() < 0.08:
            profile = random.choice(_SPIKE_PROFILES)
            self.active_spike = profile
            self.spike_remaining = profile["duration_ticks"]

        # Apply active spike
        if self.active_spike and self.spike_remaining > 0:
            m = self.active_spike["metric"]
            if m in readings:
                # Ramp-up / ramp-down envelope
                progress = 1.0 - (self.spike_remaining / self.active_spike["duration_ticks"])
                envelope = math.sin(progress * math.pi)  # 0 → 1 → 0
                readings[m] = round(readings[m] + self.active_spike["delta"] * envelope, 2)
            self.spike_remaining -= 1
            if self.spike_remaining <= 0:
                self.active_spike = None

        # Clamp spo2 to 100 max
        if "spo2" in readings:
            readings["spo2"] = min(100.0, max(70.0, readings["spo2"]))

        return readings


_sim_states: Dict[str, _SimState] = {}


def _get_sim(user_id: str) -> _SimState:
    if user_id not in _sim_states:
        _sim_states[user_id] = _SimState()
    return _sim_states[user_id]


def _build_reading(user_id: str) -> dict:
    """Generate one telemetry reading for a user."""
    sim = _get_sim(user_id)
    metrics = sim.generate()
    reading = {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "units": {k: v["unit"] for k, v in _BASELINES.items()},
    }
    # Store
    if user_id not in _telemetry_store:
        _telemetry_store[user_id] = []
    _telemetry_store[user_id].append(reading)
    # Cap at 2000 readings
    if len(_telemetry_store[user_id]) > 2000:
        _telemetry_store[user_id] = _telemetry_store[user_id][-2000:]
    return reading


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TelemetryReading(BaseModel):
    timestamp: str
    metrics: Dict[str, float]
    units: Dict[str, str]


# ---------------------------------------------------------------------------
# SSE stream endpoint
# ---------------------------------------------------------------------------

@router.get("/stream")
async def telemetry_stream(
    request: Request,
    interval: float = Query(2.0, ge=0.5, le=10.0, description="Seconds between readings"),
    token: Optional[str] = Query(None, description="JWT token (for EventSource which cannot send headers)"),
    user=Depends(get_current_user),
):
    """Server-Sent Events stream of simulated vital signs.
    
    Accepts auth via Authorization header OR ?token= query param
    (EventSource API doesn't support custom headers).
    """
    uid = str(user.id)

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                reading = _build_reading(uid)
                data = json.dumps(reading)
                yield f"data: {data}\n\n"

                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@router.get("/latest", response_model=Optional[TelemetryReading])
async def get_latest_telemetry(user=Depends(get_current_user)):
    """Return the most recent telemetry reading."""
    uid = str(user.id)
    readings = _telemetry_store.get(uid, [])
    if not readings:
        # Generate one on the fly
        return _build_reading(uid)
    return readings[-1]


@router.get("/history", response_model=List[TelemetryReading])
async def get_telemetry_history(
    minutes: int = Query(60, ge=1, le=1440),
    user=Depends(get_current_user),
):
    """Return telemetry readings within the last N minutes."""
    uid = str(user.id)
    readings = _telemetry_store.get(uid, [])
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    return [
        r for r in readings
        if datetime.fromisoformat(r["timestamp"]) >= cutoff
    ]
