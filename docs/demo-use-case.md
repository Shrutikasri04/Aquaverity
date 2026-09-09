# ORCA-X Demo Use Case (v1)

**User:** Small-scale fisherman operating from Chennai (Kasimedu).

**Question:** "Is it safe to go fishing tomorrow morning, and which direction
should I avoid?"

**Decision output:** `SAFE` / `CAUTION` / `AVOID` + a suitability score.

**Geographic scope:** Chennai coast, 13.0827° N, 80.2707° E, 20–50 km offshore.

**Time scope:** Next 24–72 hours; demo scenario uses tomorrow 05:00–13:00 IST.

**Primary data needed:**
- P3 (Weather): wind speed, wave height, rainfall, cyclone/lightning alerts
- P2 (Ocean): SST, chlorophyll-a
- P4 (Geospatial): restricted zones / geofence check, distance to shore

**Proof artifacts:** map + time-series chart + evidence trail + plain-language
explanation, in English and Tamil.

## Three preset scenarios to prepare

| Scenario | Trigger | Expected label |
|---|---|---|
| Safe day | Low wind, low waves, no alerts, outside geofence | `SAFE` |
| Caution day | Moderate wind/waves, good ocean indicators | `CAUTION` |
| Avoid day | Cyclone/high-wave alert or inside restricted zone | `AVOID` |

This document is the single source of truth for what the MVP demo shows.
Changes to scope should be reflected here first.
