# P2 & P3 Integration Notes

## What P2 and P3 actually built

Both built **standalone FastAPI services**, not importable functions —
integration happens over HTTP, not a Python function call.

| | P2 — ocean-intelligence | P3 — weather-safety |
|---|---|---|
| Branch | `p2/ocean-intelligence` | `p3/weather-safety` |
| App entrypoint | `app/main.py` (`app.main:app`) | `main.py` (`main:app`) |
| Endpoint we call | `GET /api/v1/ocean/conditions?lat=&lon=` | `POST /marine-conditions` `{latitude, longitude, target_time}` |
| Health check | `GET /health` | `GET /` |
| Sources | Copernicus (SST/CHL), INCOIS PFZ, ARGO | Open-Meteo, INCOIS WW3, SACHET-NDMA |

## Key architectural decision

P2 left a handoff doc (`docs/P2_HANDOFF.md` on their branch) that says
explicitly:

> P3 owns safety. P4 owns route/geofence. P1 combines them.

So the Decision Engine was rewritten around that split:

- **P3's `risk.risk_level`** (`LOW`/`MODERATE`/`HIGH`/`EXTREME`) is the
  authoritative safety signal — mapped directly to our `SAFE`/`CAUTION`/
  `AVOID` label. We no longer re-derive wind/wave thresholds ourselves;
  P3 already runs real hazard detection against official sources.
- **P2's `ocean.ocean_opportunity_score`** (0–100) drives the
  `suitability_score`, not safety — per their own handoff: *"P1 should
  not assume ... ocean score means total trip safety."*
- **Geofence** (P4, still mocked) is a hard veto: if
  `in_restricted_zone` is true, the label is forced to `AVOID`
  regardless of what P3 says.

## Response shape gotcha

Both services use a field called `ocean` for different things:

- P2's `ocean` = `{sst_c, chlorophyll_mg_m3, pfz_score, pfz_status, ocean_opportunity_score}`
- P3's `ocean` = `{waves: {significant_wave_height_m, ...}, wind: {u_mps, v_mps}}`

To avoid confusing the two, `real_agents.py` stores P2's full payload
under `AgentResponse.data["ocean_conditions"]` and P3's under
`AgentResponse.data["marine_conditions"]` — the Decision Engine reads
from those two distinctly-named keys.

Also note: P3's weather data uses **m/s** for wind speed; the Decision
Engine converts to km/h (`× 3.6`) only for display in `factors`.

## Running all three locally

Three separate terminals (or a docker-compose later):

```bash
# Terminal 1 — P2 (ocean-intelligence), port 8001
git checkout p2/ocean-intelligence
pip install -r requirements.txt
cp .env.example .env   # fill in any real API keys P2 needs
uvicorn app.main:app --port 8001

# Terminal 2 — P3 (weather-safety), port 8002
git checkout p3/weather-safety
pip install -r requirements.txt
uvicorn main:app --port 8002

# Terminal 3 — this repo, pointing at both
git checkout p1/integrate-p2-p3
export OCEAN_SERVICE_URL=http://localhost:8001
export WEATHER_SERVICE_URL=http://localhost:8002
python -m backend.app.main_demo
```

Without both services running, `main_demo.py` still runs and produces a
`CAUTION`-by-default decision with clear limitations explaining that
weather/ocean data was unavailable — verified working via
`backend/app/test_integration_fixtures.py`, which tests against fixture
JSON matching P2's and P3's real schemas without needing live services
or external API keys.

## Still pending

- **P4 (geospatial)** — `check_geofence` is still `mock_agents`. Same
  swap pattern applies: write a `real_agents.call_geospatial_service`
  once P4 hands off their contract, wire it into
  `orchestrator.py`'s `_run_geospatial`.
- **P3's `target_time`** — their API takes one timestamp, not a window;
  we currently pass `time_window.start`. Revisit if P3 adds a
  range-based endpoint.
- **Thresholds inside P3** (wind ≥15 m/s, waves ≥2.5m, etc. in their
  `hazard_detector.py`) haven't been jointly validated against a domain
  reference — worth a conversation with P3 before the final demo.
