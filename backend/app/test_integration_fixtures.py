"""
Verifies the Decision Engine correctly parses P2's and P3's REAL response
shapes, using fixture JSON copied from their actual test cases / models
(no live network calls -- their services need Copernicus/Open-Meteo/INCOIS
API access we don't have here). Run with:

    python -m backend.app.test_integration_fixtures
"""
from __future__ import annotations

from datetime import datetime, timezone

from backend.app.decision.decision_engine import DecisionEngine
from backend.app.planner.planner import CHENNAI
from backend.app.schemas import AgentResponse, Evidence, Plan, Task, TimeWindow

# Matches P2's tests/test_api.py test_conditions() assertions exactly.
P2_FIXTURE = {
    "location": {"lat": 10.76, "lon": 79.84},
    "requested_at": "2026-09-12T09:00:00Z",
    "ocean": {
        "sst_c": 29.3,
        "chlorophyll_mg_m3": 0.71,
        "pfz_score": 0.84,
        "pfz_status": "favourable",
        "ocean_opportunity_score": 78.5,
        "pfz": None,
    },
    "anomalies": {"sst_c": 0.4, "chlorophyll_mg_m3": None},
    "argo": {"status": "available", "nearest_profile_distance_km": 42.0, "profile_count": 3},
    "evidence": [
        {"variable": "sst_c", "value": 29.3, "source": "Copernicus Global SST", "timestamp": "2026-09-12T06:00:00Z"},
        {"variable": "pfz_score", "value": 0.84, "source": "INCOIS PFZ Advisory", "timestamp": "2026-09-11T00:00:00Z"},
    ],
    "explanation": ["SST is within a favourable range for pelagic species."],
}

# Matches P3's safety_service.py get_marine_conditions() return shape.
P3_FIXTURE_CAUTION = {
    "location": {"latitude": 13.0827, "longitude": 80.2707},
    "forecast_time": "2026-09-12T05:00:00+05:30",
    "weather": {
        "wind_speed_mps": 9.2,
        "rain_probability_percent": 40,
        "visibility_m": 8000,
        "source": "Open-Meteo",
    },
    "ocean": {"waves": {"significant_wave_height_m": 1.6}, "wind": {"u_mps": 4.0, "v_mps": 5.0}, "source": "INCOIS WW3"},
    "alerts": [],
    "hazards": [{"type": "HIGH_WAVES", "source": "INCOIS", "value": 1.6, "unit": "m", "severity": "HIGH"}],
    "risk": {"risk_score": 25, "risk_level": "MODERATE", "recommendation": "Exercise caution.", "hazard_count": 1},
    "safety": {"level": "MODERATE", "action": "EXERCISE_CAUTION", "message": "Exercise caution before venturing out."},
    "errors": [],
    "sources": ["Open-Meteo Weather API", "INCOIS WW3", "SACHET-NDMA"],
}

P3_FIXTURE_AVOID = {**P3_FIXTURE_CAUTION, "risk": {**P3_FIXTURE_CAUTION["risk"], "risk_level": "EXTREME", "risk_score": 90}}


def _build_plan() -> Plan:
    tw = TimeWindow(
        start=datetime(2026, 9, 12, 5, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 12, 13, 0, tzinfo=timezone.utc),
    )
    return Plan(
        plan_id="plan_test",
        session_id="sess_test",
        intent="safety_advisory",
        location=CHENNAI,
        time_window=tw,
        required_agents=["weather", "ocean", "geospatial"],
        tasks=[Task(agent="weather", operation="x", params={}), Task(agent="ocean", operation="x", params={})],
    )


def _agent_response(agent, data_key, payload, status="success") -> AgentResponse:
    return AgentResponse(
        agent=agent,
        task_id="t1",
        status=status,
        data={data_key: payload},
        evidence=[Evidence(source="fixture", retrieved_at=datetime.now(timezone.utc))],
        confidence=0.85,
        limitations=[],
    )


def run():
    engine = DecisionEngine()
    plan = _build_plan()

    print("--- Scenario: MODERATE risk from P3 -> expect CAUTION ---")
    responses = [
        _agent_response("weather", "marine_conditions", P3_FIXTURE_CAUTION),
        _agent_response("ocean", "ocean_conditions", P2_FIXTURE),
    ]
    decision = engine.make_decision(plan, responses)
    print(f"label={decision.decision.label} suitability={decision.decision.suitability_score}")
    assert decision.decision.label == "CAUTION", f"expected CAUTION, got {decision.decision.label}"
    assert decision.decision.suitability_score == 0.79, decision.decision.suitability_score

    print("\n--- Scenario: EXTREME risk from P3 -> expect AVOID ---")
    responses = [
        _agent_response("weather", "marine_conditions", P3_FIXTURE_AVOID),
        _agent_response("ocean", "ocean_conditions", P2_FIXTURE),
    ]
    decision = engine.make_decision(plan, responses)
    print(f"label={decision.decision.label} summary={decision.decision.summary}")
    assert decision.decision.label == "AVOID", f"expected AVOID, got {decision.decision.label}"

    print("\n--- Scenario: weather service down -> should degrade, not crash ---")
    responses = [
        AgentResponse(agent="weather", task_id="t1", status="error", data={}, evidence=[], confidence=0.0, limitations=["down"]),
        _agent_response("ocean", "ocean_conditions", P2_FIXTURE),
    ]
    decision = engine.make_decision(plan, responses)
    print(f"label={decision.decision.label} confidence={decision.decision.confidence}")

    print("\nAll fixture assertions passed.")


if __name__ == "__main__":
    run()
