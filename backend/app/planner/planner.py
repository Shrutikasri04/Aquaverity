"""
Planner Agent.

v1 is deliberately template/rule-based (per the P1 doc's Step 3: "start with
hardcoded templates for the first demo"). Swap `_extract_*` helpers for an
LLM-backed extractor later without changing the public `plan()` signature.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from backend.app.schemas import Intent, Location, Plan, SessionState, Task, TimeWindow, UserQuery

IST = timezone(timedelta(hours=5, minutes=30))

# Default location used for the MVP demo scenario until real NL location
# extraction (or a geocoder) is wired in.
CHENNAI = Location(name="Chennai Coast", lat=13.0827, lon=80.2707, radius_km=30)


class Planner:
    def plan(self, query: UserQuery, session: SessionState) -> Plan:
        location = self._extract_location(query, session)
        time_window = self._extract_time_window(query, session)
        intent = self._extract_intent(query, session)

        tasks = [
            Task(
                agent="weather",
                operation="get_marine_forecast",
                params={
                    "lat": location.lat,
                    "lon": location.lon,
                    "start": time_window.start.isoformat(),
                    "end": time_window.end.isoformat(),
                },
            ),
            Task(
                agent="ocean",
                operation="get_ocean_conditions",
                params={
                    "lat": location.lat,
                    "lon": location.lon,
                    "variables": ["sst", "chlorophyll"],
                    "start": time_window.start.isoformat(),
                    "end": time_window.end.isoformat(),
                },
            ),
            Task(
                agent="geospatial",
                operation="check_geofence",
                params={
                    "lat": location.lat,
                    "lon": location.lon,
                    "radius_km": location.radius_km or 30,
                },
            ),
        ]

        return Plan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            session_id=query.session_id,
            intent=intent,
            location=location,
            time_window=time_window,
            required_agents=["weather", "ocean", "geospatial"],
            tasks=tasks,
        )

    # --- extraction helpers (template-based v1) ---------------------------

    def _extract_location(self, query: UserQuery, session: SessionState) -> Location:
        text = query.text.lower()
        if "chennai" in text or "kasimedu" in text:
            return CHENNAI
        if session.last_location:
            return session.last_location
        return CHENNAI  # MVP default; expand to a geocoder for other regions

    def _extract_time_window(self, query: UserQuery, session: SessionState) -> TimeWindow:
        text = query.text.lower()
        now = datetime.now(IST)

        if "tomorrow" in text or not session.last_time_window:
            target_day = now + timedelta(days=1)
        else:
            return session.last_time_window

        if "afternoon" in text:
            start = target_day.replace(hour=13, minute=0, second=0, microsecond=0)
            end = target_day.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            # default: early-morning fishing window
            start = target_day.replace(hour=5, minute=0, second=0, microsecond=0)
            end = target_day.replace(hour=13, minute=0, second=0, microsecond=0)

        return TimeWindow(start=start, end=end)

    def _extract_intent(self, query: UserQuery, session: SessionState) -> Intent:
        text = query.text.lower()
        if "route" in text or "direction to" in text:
            return "route_advice"
        if "productive zone" in text or "favourable" in text or "suitability" in text:
            return "fishing_suitability"
        return "safety_advisory"
