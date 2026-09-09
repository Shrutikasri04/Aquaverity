"""
Agent Orchestrator.

Executes every task in a Plan against the relevant agent, in parallel, and
collects AgentResponse objects. When you have real P2/P3/P4 implementations,
swap the calls inside `_AGENT_DISPATCH` — everything downstream (Decision
Engine) only depends on the AgentResponse shape, not on how it was produced.
"""
from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from backend.app.agents import mock_agents
from backend.app.schemas import AgentResponse, Plan, Task

logger = logging.getLogger("orca.orchestrator")


def _run_weather(task: Task, task_id: str) -> AgentResponse:
    p = task.params
    return mock_agents.get_marine_forecast(
        lat=p["lat"],
        lon=p["lon"],
        start=datetime.fromisoformat(p["start"]),
        end=datetime.fromisoformat(p["end"]),
        task_id=task_id,
    )


def _run_ocean(task: Task, task_id: str) -> AgentResponse:
    p = task.params
    return mock_agents.get_ocean_conditions(
        lat=p["lat"],
        lon=p["lon"],
        variables=p["variables"],
        start=datetime.fromisoformat(p["start"]),
        end=datetime.fromisoformat(p["end"]),
        task_id=task_id,
    )


def _run_geospatial(task: Task, task_id: str) -> AgentResponse:
    p = task.params
    return mock_agents.check_geofence(lat=p["lat"], lon=p["lon"], radius_km=p["radius_km"], task_id=task_id)


_AGENT_DISPATCH = {
    "weather": _run_weather,
    "ocean": _run_ocean,
    "geospatial": _run_geospatial,
}


class Orchestrator:
    def run_plan(self, plan: Plan) -> list[AgentResponse]:
        responses: list[AgentResponse] = []

        with ThreadPoolExecutor(max_workers=len(plan.tasks) or 1) as pool:
            futures = {}
            for task in plan.tasks:
                task_id = f"task_{uuid.uuid4().hex[:6]}"
                handler = _AGENT_DISPATCH.get(task.agent)
                if handler is None:
                    logger.warning("No handler registered for agent=%s", task.agent)
                    continue
                futures[pool.submit(handler, task, task_id)] = task

            for future in as_completed(futures):
                task = futures[future]
                try:
                    responses.append(future.result())
                except Exception as exc:  # noqa: BLE001 — degrade, don't crash the whole plan
                    logger.exception("Agent %s failed", task.agent)
                    responses.append(
                        AgentResponse(
                            agent=task.agent,
                            task_id=f"task_error_{uuid.uuid4().hex[:6]}",
                            status="error",
                            data={},
                            evidence=[],
                            confidence=0.0,
                            limitations=[f"{task.agent} agent failed: {exc}"],
                        )
                    )

        return responses
