"""
Stand-ins for P2 (ocean), P3 (weather), P4 (geospatial) agents.

Each function signature and return shape matches docs/agent-contract.md
exactly, so swapping a mock for the real implementation in
orchestrator.py should require zero changes to the Decision Engine.

Values below are illustrative demo data, not real observations.
"""
from __future__ import annotations

from datetime import datetime, timezone

from backend.app.schemas import AgentResponse, Evidence


def get_marine_forecast(lat: float, lon: float, start: datetime, end: datetime, task_id: str) -> AgentResponse:
    """Mock of P3's weather/safety agent."""
    return AgentResponse(
        agent="weather",
        task_id=task_id,
        status="success",
        data={
            "wind_speed_kmh": 24,
            "wave_height_m": 1.3,
            "rain_mm": 2.5,
            "alerts": [
                {
                    "type": "high_wave",
                    "severity": "medium",
                    "description": "Wave heights up to 1.8 m expected in the afternoon",
                }
            ],
        },
        evidence=[
            Evidence(
                source="Open-Meteo Marine API (mocked)",
                retrieved_at=datetime.now(timezone.utc),
                url="https://open-meteo.com/en/docs/marine-weather-api",
            )
        ],
        confidence=0.85,
        limitations=["Mock data — replace with P3's real forecast call", "Forecast resolution is ~30 km"],
    )


def get_ocean_conditions(
    lat: float, lon: float, variables: list[str], start: datetime, end: datetime, task_id: str
) -> AgentResponse:
    """Mock of P2's ocean-data agent."""
    return AgentResponse(
        agent="ocean",
        task_id=task_id,
        status="success",
        data={
            "sst_c": 28.7,
            "chlorophyll_mg_m3": 0.62,
            "anomalies": {"sst_anomaly_c": 0.3, "chlorophyll_anomaly": "slightly above baseline"},
        },
        evidence=[
            Evidence(
                source="Copernicus Marine Service (mocked)",
                retrieved_at=datetime.now(timezone.utc),
                url="https://marine.copernicus.eu/",
            )
        ],
        confidence=0.8,
        limitations=[
            "Mock data — replace with P2's real ocean-conditions call",
            "Satellite chlorophyll unreliable under cloud cover",
        ],
    )


def check_geofence(lat: float, lon: float, radius_km: float, task_id: str) -> AgentResponse:
    """Mock of P4's geospatial agent."""
    return AgentResponse(
        agent="geospatial",
        task_id=task_id,
        status="success",
        data={
            "in_restricted_zone": False,
            "restricted_zones_nearby": [],
            "distance_to_shore_km": 0.0,
        },
        evidence=[
            Evidence(
                source="Natural Earth + custom GeoJSON (mocked)",
                retrieved_at=datetime.now(timezone.utc),
                url=None,
            )
        ],
        confidence=0.9,
        limitations=["Mock data — replace with P4's real geofence service"],
    )
