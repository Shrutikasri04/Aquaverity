# Orchestrator Flow (v1)

## What it does

Takes a `Plan`, runs every task in `plan.tasks` against the matching
agent, and returns a `list[AgentResponse]` — one per task. Implemented in
`orchestrator/orchestrator.py`.

```text
Plan.tasks
   |
   +--> task(agent=weather)     --\
   +--> task(agent=ocean)        |--  run concurrently (ThreadPoolExecutor)
   +--> task(agent=geospatial)  --/
   |
   v
list[AgentResponse]   (one per task, in completion order — not task order)
```

## Why parallel

Weather, ocean, and geospatial lookups don't depend on each other's
output, so there's no reason to wait for one before starting the next.
`Orchestrator.run_plan()` submits all tasks to a `ThreadPoolExecutor` and
collects results via `as_completed()`, so the whole plan takes as long as
the *slowest* single agent call, not the sum of all three.

## Failure handling

Each task is wrapped in its own try/except. If an agent call raises:

- The exception is logged.
- An `AgentResponse` with `status="error"` and an explanatory entry in
  `limitations` is appended in place of a real result.
- The orchestrator does **not** abort the rest of the plan — other
  agents' results still come back normally.

This matters because the Decision Engine is built to degrade gracefully:
missing ocean data lowers `suitability_score` reliability and adds a
limitation, but a `weather`-only or `geospatial`-only failure doesn't
crash the whole `FinalDecision` — see `decision_engine.py`'s handling of
`status != "success"` for each agent.

## Swapping mocks for real agents

`_AGENT_DISPATCH` in `orchestrator.py` maps an agent name to a handler
function. To integrate a real P2/P3/P4 implementation:

1. Write a function with the same signature as the existing
   `_run_weather` / `_run_ocean` / `_run_geospatial` (takes a `Task` and a
   `task_id`, returns an `AgentResponse`).
2. Call the real P2/P3/P4 function/endpoint inside it instead of
   `mock_agents.*`.
3. Swap the entry in `_AGENT_DISPATCH`.
4. Run `python -m backend.app.main_demo` and confirm you still get a
   sane `FinalDecision` — no other file needs to change.

Recommended order (per the P1 timeline): weather first, then ocean, then
geospatial — keep the end-to-end demo working after each swap.
