# Agent Contract (v1)

Owned by P1. Any field change here must be broadcast to P2–P6.

Canonical Python types live in `backend/app/schemas.py` — this doc is the
human-readable mirror of those types. If they ever drift, the code wins and
this doc should be updated to match.

## Agents and operations

| Agent | Owner | Operation | Notes |
|---|---|---|---|
| `ocean` | P2 | `get_ocean_conditions(lat, lon, variables, start, end)` | Returns SST, chlorophyll, optional ARGO summary |
| `weather` | P3 | `get_marine_forecast(lat, lon, start, end)` | Returns wind, wave height, rain, alerts |
| `geospatial` | P4 | `check_geofence(lat, lon, radius_km)` | Returns restricted-zone hits, distance to shore |

## UserQuery (P5/P6 → P1)

```json
{
  "session_id": "sess_123",
  "user_id": "user_456",
  "text": "Is it safe to fish near Chennai tomorrow morning?",
  "language": "en",
  "context": {
    "last_location": {"name": "Chennai", "lat": 13.0827, "lon": 80.2707},
    "last_time_window": {"start": "2026-09-05T05:00:00+05:30", "end": "2026-09-05T13:00:00+05:30"}
  }
}
```

## Plan (P1 output from Planner)

```json
{
  "plan_id": "plan_abc",
  "session_id": "sess_123",
  "intent": "safety_advisory",
  "location": {"name": "Chennai", "lat": 13.0827, "lon": 80.2707, "radius_km": 30},
  "time_window": {"start": "2026-09-05T05:00:00+05:30", "end": "2026-09-05T13:00:00+05:30"},
  "required_agents": ["ocean", "weather", "geospatial"],
  "tasks": [
    {"agent": "weather", "operation": "get_marine_forecast", "params": {"lat": 13.0827, "lon": 80.2707, "start": "...", "end": "..."}},
    {"agent": "ocean", "operation": "get_ocean_conditions", "params": {"lat": 13.0827, "lon": 80.2707, "variables": ["sst", "chlorophyll"], "start": "...", "end": "..."}},
    {"agent": "geospatial", "operation": "check_geofence", "params": {"lat": 13.0827, "lon": 80.2707, "radius_km": 30}}
  ]
}
```

## AgentResponse (P2/P3/P4 → P1)

```json
{
  "agent": "weather",
  "task_id": "task_w1",
  "status": "success",
  "data": {"wind_speed_kmh": 24, "wave_height_m": 1.3, "rain_mm": 2.5, "alerts": []},
  "evidence": [{"source": "Open-Meteo Marine API", "retrieved_at": "2026-09-05T19:00:00Z", "url": "https://..."}],
  "confidence": 0.85,
  "limitations": ["Forecast resolution is 30 km"]
}
```

`status` must be one of `success`, `partial`, `error`. On `error`, `data` may
be empty but `limitations` should say why, so the Decision Engine can degrade
gracefully instead of failing.

## FinalDecision (P1 output)

```json
{
  "session_id": "sess_123",
  "plan_id": "plan_abc",
  "decision": {
    "type": "safety_advisory",
    "label": "CAUTION",
    "summary": "...",
    "factors": [{"name": "wind", "value": "24 km/h", "impact": "moderate", "source": "weather"}],
    "recommended_actions": ["..."],
    "confidence": 0.78,
    "limitations": ["..."]
  },
  "evidence_trail": [{"agent": "weather", "source": "Open-Meteo Marine API", "url": "https://...", "retrieved_at": "..."}]
}
```

## Change process

1. Propose the change in this file (PR against `develop`).
2. Tag the affected owner(s) for sign-off.
3. Update `schemas.py` in the same PR.
