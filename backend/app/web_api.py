"""
Minimal web API so the frontend (orca-x.html) has something real to call.

This is intentionally small: one endpoint that runs the existing
Planner -> Orchestrator -> DecisionEngine flow and reshapes the result
into exactly what the frontend's getMarineAnalysis() expects. P6's real
backend (sessions, DB, /sessions/{id}/query) can replace this later
without the frontend needing to change, as long as this same shape is
preserved.

Run with:
    pip install fastapi uvicorn
    uvicorn backend.app.web_api:app --port 8000
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.decision.decision_engine import DecisionEngine
from backend.app.orchestrator.orchestrator import Orchestrator
from backend.app.planner.planner import Planner
from backend.app.schemas import AgentResponse, FinalDecision, UserQuery
from backend.app.session.session_manager import SessionManager

app = FastAPI(title="ORCA-X P1 API")

# Wide open for local hackathon dev -- the frontend is opened as a local
# file (file://) or from a dev server, so its Origin header may be "null".
# Tighten this before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions = SessionManager()
_planner = Planner()
_orchestrator = Orchestrator()
_decision_engine = DecisionEngine()

# The frontend's own baseline constants (see oceanSeries in orca-x.html) --
# reused here so server-computed anomaly percentages line up with what the
# UI would have shown in simulated mode.
SST_BASELINE_C = 27.1
CHL_BASELINE_MG_M3 = 0.71
WAVE_BASELINE_M = 1.62

LABEL_TO_FRONTEND_RISK = {"SAFE": "LOW", "CAUTION": "MODERATE", "AVOID": "HIGH"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/marine-analysis")
def marine_analysis(
    lat: float = 13.0827,
    lon: float = 80.2707,
    question: str = "Is it safe to fish near Chennai tomorrow morning?",
):
    """
    Runs the full pipeline for the given coordinates and returns JSON shaped
    for orca-x.html's getMarineAnalysis()/renderKPI()/renderExplain().
    """
    session_id = f"sess_web_{uuid.uuid4().hex[:8]}"
    session = _sessions.get_or_create(session_id)

    query = UserQuery(session_id=session_id, text=question)
    plan = _planner.plan(query, session)

    # Frontend supplies its own lat/lon (map click or search box) -- override
    # whatever the template-based Planner guessed from the question text.
    plan.location.lat = lat
    plan.location.lon = lon
    for task in plan.tasks:
        task.params["lat"] = lat
        task.params["lon"] = lon

    _sessions.update_after_plan(session_id, plan.location, plan.time_window, plan.intent)

    responses = _orchestrator.run_plan(plan)
    final_decision = _decision_engine.make_decision(plan, responses)

    return _to_frontend_shape(final_decision, responses)


def _to_frontend_shape(final: FinalDecision, responses: list[AgentResponse]) -> dict:
    by_agent = {r.agent: r for r in responses}
    ocean = by_agent.get("ocean")
    weather = by_agent.get("weather")

    sst = chl = None
    if ocean and ocean.status == "success":
        ov = ocean.data.get("ocean_conditions", {}).get("ocean", {})
        sst = ov.get("sst_c")
        chl = ov.get("chlorophyll_mg_m3")

    wave = wind_kmh = None
    hazards: list[str] = []
    if weather and weather.status in ("success", "partial"):
        marine = weather.data.get("marine_conditions", {})
        wave = ((marine.get("ocean") or {}).get("waves") or {}).get("significant_wave_height_m")
        wind_mps = (marine.get("weather") or {}).get("wind_speed_mps")
        if wind_mps is not None:
            wind_kmh = round(wind_mps * 3.6, 1)
        hazards = [h.get("type") for h in marine.get("hazards", []) if h.get("type")]

    return {
        "source": "live",
        "sst": sst,
        "sstAnom": round(sst - SST_BASELINE_C, 1) if sst is not None else None,
        "chl": chl,
        "chlAnomPct": round((chl - CHL_BASELINE_MG_M3) / CHL_BASELINE_MG_M3 * 100) if chl is not None else None,
        "wave": wave,
        "waveAnomPct": round((wave - WAVE_BASELINE_M) / WAVE_BASELINE_M * 100) if wave is not None else None,
        "windSpeedKmh": wind_kmh,
        "hazards": hazards,
        # current speed & salinity: neither P2 nor P3 provide these yet.
        # Left null on purpose -- frontend should keep its simulated values
        # for just these two fields until P2/P4 add them.
        "current": None,
        "salinity": None,
        "risk": LABEL_TO_FRONTEND_RISK.get(final.decision.label, "MODERATE"),
        "confidence": round(final.decision.confidence * 100),
        "summary": final.decision.summary,
        "recommendedActions": final.decision.recommended_actions,
        "limitations": final.decision.limitations,
    }
