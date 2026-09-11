# Planner Schema (v1)

Defines how a `UserQuery` becomes a `Plan`. Canonical types are in
`backend/app/schemas.py`; this doc explains the *logic*, not just the shape.

## Input: UserQuery + SessionState

The Planner never looks at `UserQuery` alone — it always has the current
`SessionState` available, so a follow-up like "what about tomorrow
afternoon?" can reuse the last known location.

```json
// UserQuery
{
  "session_id": "sess_123",
  "text": "Is it safe to fish near Chennai tomorrow morning?",
  "language": "en",
  "context": {}
}
```

```json
// SessionState (before this query)
{
  "session_id": "sess_123",
  "last_location": null,
  "last_time_window": null,
  "last_intent": null,
  "language": "en"
}
```

## Output: Plan

```json
{
  "plan_id": "plan_a1b2c3d4",
  "session_id": "sess_123",
  "intent": "safety_advisory",
  "location": {"name": "Chennai Coast", "lat": 13.0827, "lon": 80.2707, "radius_km": 30},
  "time_window": {"start": "2026-09-12T05:00:00+05:30", "end": "2026-09-12T13:00:00+05:30"},
  "required_agents": ["weather", "ocean", "geospatial"],
  "tasks": [
    {"agent": "weather", "operation": "get_marine_forecast", "params": {"...": "..."}},
    {"agent": "ocean", "operation": "get_ocean_conditions", "params": {"...": "..."}},
    {"agent": "geospatial", "operation": "check_geofence", "params": {"...": "..."}}
  ]
}
```

## v1 extraction logic (template/rule-based)

Implemented in `planner/planner.py`. Three independent extraction steps:

1. **Location** — `_extract_location()`: keyword match on "chennai" /
   "kasimedu" → hardcoded `CHENNAI` location constant. Falls back to
   `session.last_location`, then to `CHENNAI` as the MVP default.
2. **Time window** — `_extract_time_window()`: keyword match on "tomorrow"
   / "afternoon" → fixed 05:00–13:00 or 13:00–18:00 IST windows. Falls
   back to `session.last_time_window` if the query doesn't mention time.
3. **Intent** — `_extract_intent()`: keyword match on "route" /
   "suitability" / "favourable" → `route_advice` or `fishing_suitability`.
   Defaults to `safety_advisory`.

Every task's `params` are always fully populated numbers/timestamps —
never left for a downstream agent to guess.

## Upgrade path

To move from templates to LLM-driven extraction:

1. Keep the exact same `plan(query, session) -> Plan` signature.
2. Replace the three `_extract_*` methods with a single LLM call that
   returns structured JSON (location, time window, intent) — validate the
   response against the same `Location` / `TimeWindow` / `Intent` types
   before building the `Plan`, so a malformed LLM response can't corrupt
   the pipeline.
3. Keep the keyword-based version as a fallback if the LLM call fails or
   times out — same pattern as `explanation_llm.py` in the Decision Engine.
