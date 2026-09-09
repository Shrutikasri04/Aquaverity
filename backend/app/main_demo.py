"""
Run the full Planner -> Orchestrator -> Decision Engine flow once, with
mocked agents, for the Chennai demo scenario.

Usage:
    python -m backend.app.main_demo
"""
from __future__ import annotations

import json

from backend.app.decision.decision_engine import DecisionEngine
from backend.app.orchestrator.orchestrator import Orchestrator
from backend.app.planner.planner import Planner
from backend.app.session.session_manager import SessionManager
from backend.app.schemas import UserQuery


def run_demo_query() -> dict:
    sessions = SessionManager()
    planner = Planner()
    orchestrator = Orchestrator()
    decision_engine = DecisionEngine()

    session_id = "sess_demo_1"
    session = sessions.get_or_create(session_id, user_id="user_demo")

    query = UserQuery(
        session_id=session_id,
        user_id="user_demo",
        text="Is it safe to fish near Chennai tomorrow morning?",
        language="en",
    )

    plan = planner.plan(query, session)
    sessions.update_after_plan(session_id, plan.location, plan.time_window, plan.intent)

    agent_responses = orchestrator.run_plan(plan)
    final_decision = decision_engine.make_decision(plan, agent_responses)

    return final_decision.model_dump(mode="json")


if __name__ == "__main__":
    result = run_demo_query()
    print(json.dumps(result, indent=2))
