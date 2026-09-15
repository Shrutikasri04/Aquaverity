"""
Real agent clients for P2 (ocean-intelligence) and P3 (weather-safety).

Both P2 and P3 built standalone FastAPI services rather than importable
functions, so integration happens over HTTP. Run each service separately
(see docs/p2-p3-integration.md) and point these clients at them via env
vars, e.g.:

    OCEAN_SERVICE_URL=http://localhost:8001
    WEATHER_SERVICE_URL=http://localhost:8002

Every function here returns an AgentResponse no matter what happens --
network errors, timeouts, and non-200s are all converted into
status="error" responses with a clear limitation, so the Decision Engine
can degrade gracefully instead of the whole plan crashing.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

from backend.app.schemas import AgentResponse, Evidence

OCEAN_SERVICE_URL = os.environ.get("OCEAN_SERVICE_URL", "http://localhost:8001")
WEATHER_SERVICE_URL = os.environ.get("WEATHER_SERVICE_URL", "http://localhost:8002")
REQUEST_TIMEOUT_S = 10


def call_ocean_service(lat: float, lon: float, task_id: str) -> AgentResponse:
    """
    Calls P2's GET /api/v1/ocean/conditions.

    P2's response shape (per docs/P2_HANDOFF.md and app/models.py):
      { location, requested_at,
        ocean: { sst_c, chlorophyll_mg_m3, pfz_score, pfz_status,
                 ocean_opportunity_score, pfz },
        anomalies, argo, evidence: [...], explanation: [...] }

    The full payload is kept as-is in AgentResponse.data under key
    "ocean_conditions" so nothing P2 provides is thrown away, even
    though the Decision Engine currently only reads a subset of it.
    """
    url = f"{OCEAN_SERVICE_URL}/api/v1/ocean/conditions"
    try:
        resp = requests.get(url, params={"lat": lat, "lon": lon}, timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 -- degrade, never crash the plan
        return AgentResponse(
            agent="ocean",
            task_id=task_id,
            status="error",
            data={},
            evidence=[],
            confidence=0.0,
            limitations=[f"P2 ocean service unreachable or errored: {exc}"],
        )

    evidence = [
        Evidence(
            source=e.get("source", "P2 ocean-intelligence"),
            retrieved_at=_parse_or_now(e.get("timestamp")),
            url=None,
        )
        for e in payload.get("evidence", [])
    ]

    return AgentResponse(
        agent="ocean",
        task_id=task_id,
        status="success",
        data={"ocean_conditions": payload},
        evidence=evidence,
        confidence=0.85,
        limitations=list(payload.get("explanation", [])) if not payload.get("evidence") else [],
    )


def call_weather_safety_service(lat: float, lon: float, target_time: str, task_id: str) -> AgentResponse:
    """
    Calls P3's POST /marine-conditions.

    P3's response shape (per main.py / safety_service.py):
      { location, forecast_time, weather: {...}, ocean: {waves, wind, ...},
        alerts: [...], hazards: [...], risk: {risk_score, risk_level,
        recommendation, hazard_count}, safety: {level, action, message},
        errors: [...], sources: [...] }

    Note: P3's own "ocean" key holds WAVE/WIND data (from INCOIS WW3),
    which is different from P2's "ocean" key (SST/chlorophyll/PFZ). Kept
    separate under "marine_conditions" here to avoid confusing the two.
    """
    url = f"{WEATHER_SERVICE_URL}/marine-conditions"
    try:
        resp = requests.post(
            url,
            json={"latitude": lat, "longitude": lon, "target_time": target_time},
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        return AgentResponse(
            agent="weather",
            task_id=task_id,
            status="error",
            data={},
            evidence=[],
            confidence=0.0,
            limitations=[f"P3 weather-safety service unreachable or errored: {exc}"],
        )

    evidence = [
        Evidence(source=src, retrieved_at=datetime.now(timezone.utc), url=None)
        for src in payload.get("sources", [])
    ]
    limitations = [f"{e.get('source')}: {e.get('message')}" for e in payload.get("errors", [])]

    return AgentResponse(
        agent="weather",
        task_id=task_id,
        status="success" if not payload.get("errors") else "partial",
        data={"marine_conditions": payload},
        evidence=evidence,
        confidence=0.9 if not payload.get("errors") else 0.6,
        limitations=limitations,
    )


def _parse_or_now(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
