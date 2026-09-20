# Frontend Integration Notes

## What was actually there before this

`orca-x.html` (originally committed as `orca-x (5).html`, later
re-uploaded with minor CSS tweaks as `orca-x (7).html` — the two are
otherwise identical, confirmed via diff) is a fully self-contained,
client-side demo: every KPI (SST, chlorophyll, wave height, "Fishing
Risk") came from `getMarineAnalysis()`, which reads a locally-generated
`oceanSeries` array of seeded fake numbers. The only real network
calls in the file were to Google Maps, a translation API, and
OpenStreetMap search — nothing touched the backend at all.

There was also no backend HTTP endpoint to connect it to yet — the
Planner/Orchestrator/Decision Engine only ran via `main_demo.py` as a
script.

## What changed

**New: `backend/app/web_api.py`** — a minimal FastAPI app with one real
endpoint:

```
GET /api/marine-analysis?lat=13.0827&lon=80.2707
```

Runs Planner → Orchestrator → Decision Engine for those coordinates and
returns JSON shaped for the frontend:

```json
{
  "source": "live",
  "sst": 29.3, "sstAnom": 2.2,
  "chl": 0.71, "chlAnomPct": 0,
  "wave": 1.6, "waveAnomPct": -1,
  "current": null, "salinity": null,
  "risk": "MODERATE", "confidence": 80,
  "summary": "...", "recommended_actions": [...], "limitations": [...]
}
```

`current` and `salinity` are always `null` — **neither P2 nor P3
provide these yet.** The frontend keeps using its simulated values for
just those two fields even in "live" mode. Worth raising with P2/P4 if
a real current-speed or salinity source becomes available.

**Modified: `frontend/orca-x.html`** — three additive changes, nothing
else touched (verified via diff against the original):

1. Added `fetchLiveAnalysis(lat, lon)` — calls the endpoint above with a
   6-second timeout, returns `null` on any failure (network error,
   non-200, timeout).
2. `getMarineAnalysis()` now checks `state.liveAnalysis` first and uses
   live values where available, falling back to the simulated
   `oceanSeries` data for anything missing (including always for
   `current`/`salinity`).
3. `runPipeline(question)` now kicks off `fetchLiveAnalysis()` in
   parallel with the existing agent-step animation, and sets
   `state.liveAnalysis` right before the final render — so asking a
   question in the chat is what triggers a real backend call.

This means the demo **degrades gracefully by design**: if the backend
isn't running, the toast says "offline demo data" and everything still
works with simulated numbers — matching the reliability principle from
the original project brief (cached fallback so a live demo never fails
outright).

## Round 2: chatbot was giving the same answer to every question

Root cause: `renderChat()` built its answer from one fixed sentence
template — always describing chlorophyll/SST/current/wave in the same
order — that never looked at `state.lastQuery` at all. Asking about
cyclones, wind, anything: same sentence every time.

**Fix**: added `composeAnswer(question, a, live)`, which:

- Checks the question (lowercased) for keywords: `cyclone`/`storm`/
  `hurricane`, `wind`, `wave`, `chlorophyll`/`chl`, `sst`/`temperature`,
  `why`/`change` — and leads with whichever fact is actually relevant.
- For cyclone questions specifically, checks `live.hazards` (P3's real
  hazard list) and says so explicitly if one is flagged, rather than a
  generic risk sentence.
- Falls back to the live backend's own `summary` (already grounded in
  the real decision) for anything that doesn't match a keyword.
- Appends the first `recommendedActions` entry when available.
- If the backend is unreachable (`live` is `null`), falls back to a
  generic simulated-data sentence — still varies by keyword, just uses
  the simulated numbers instead of real ones.

`web_api.py`'s response shape gained two fields to support this:
`windSpeedKmh` (converted from P3's `wind_speed_mps`) and `hazards`
(list of hazard type strings, e.g. `["HIGH_WAVES"]`). Also fixed a
naming mismatch — the response used to say `recommended_actions`
(snake_case) but the frontend expects `recommendedActions`
(camelCase); all fields are camelCase now for consistency.

Verified by extracting `composeAnswer` and running it standalone in
Node against 4 different questions — confirmed 4 genuinely different
answers instead of one fixed sentence (see commit message for the
actual output).

## Round 2: geospatial mock removed

`planner.py` no longer includes a `geospatial` task in the `Plan` at
all — P4 hasn't delivered a real service yet, and generating a mock
"outside restricted zones" result and treating it as real would be
misleading in a live demo. The Decision Engine's limitation message
was also rewarded from "unavailable" (sounds like a runtime failure)
to "not yet available — P4's real service isn't built yet" (accurate:
it's an intentional gap, not an error). Re-add the task once P4 ships
their `check_geofence` service — the expected shape is already
documented in `docs/agent-contract.md`.

**Follow-up fix (same round, caught on review):** the backend-side
removal above didn't actually fix what was visible on screen — the UI
still listed "Geospatial Agent · Region boundaries processed" as one
of the animated pipeline steps, and always marked it "done" after the
animation finished, regardless of there being no real geofence check
behind it. That's now removed from `AGENT_DEFS` too (7 agents remain),
with the header copy updated from "eight cooperating AI agents" to
"seven", and the report-modal's hardcoded `8 agents` string replaced
with `${AGENT_DEFS.length}` so it can't silently drift out of sync
again if the list changes in the future.

## Known limitation: location is hardcoded

The map's search box (`goToResult` in `initGeoSearch`) pans the map and
drops a marker, but doesn't store the selected coordinates anywhere
shared — so `runPipeline()` currently always queries Chennai
(13.0827, 80.2707) regardless of what's searched. There's a `// TODO`
comment at that exact spot in the code. To fix: add a
`state.selectedLocation` set inside `goToResult`, and read it in
`runPipeline` instead of the hardcoded constant.

## How to run it

```bash
# Terminal 1: this backend (plus P2 and P3 running per docs/p2-p3-integration.md
# for genuinely live data -- without them it still works in degraded/offline mode)
pip install -r requirements.txt
uvicorn backend.app.web_api:app --port 8000

# Then just open frontend/orca-x.html directly in a browser (double-click it,
# or drag it into a browser window). No build step needed.
```

Ask a question in the chat (or click one of the suggested chips) and
watch the KPI strip — if the backend is reachable, the toast at the end
will say "live ocean & weather data" instead of "offline demo data".
Try asking specifically about "cyclone risk" vs "wind speed" vs "why
did conditions change" and confirm you get three different answers.

