# P2 → P1 Handoff

## Contract

P1 should call:

`GET /api/v1/ocean/conditions?lat=<LAT>&lon=<LON>`

For searching possible zones:

`GET /api/v1/ocean/candidates?lat=<LAT>&lon=<LON>&radius_km=<RADIUS>`

## P1 should use

- `ocean.sst_c`
- `ocean.chlorophyll_mg_m3`
- `ocean.pfz_score`
- `ocean.pfz_status`
- `ocean.ocean_opportunity_score`
- `anomalies`
- `argo`
- `evidence`
- `explanation`

## P1 should NOT use

P1 should not assume:

- high chlorophyll means fish definitely exist
- PFZ means safe to travel
- ocean score means total trip safety
- ARGO availability means a location has a real-time observation

P3 owns safety. P4 owns route/geofence. P1 combines them.

## Example P1 reasoning

```text
P2:
Ocean opportunity = 84
PFZ = favourable
SST anomaly = +1.2 C

P3:
Safety = 81
Critical hazard = false

P4:
Route = unrestricted
Distance = 28 km

P1:
Recommend candidate B
because ocean conditions are favourable,
route is feasible, and no critical safety veto exists.
```
