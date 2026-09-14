# ORCA P2 — Ocean Intelligence Module

This is the P2 (Ocean Data Lead) module for ORCA Marine Ecosystem Reasoning with Collaborative Agents.

## What this module does

Given latitude, longitude, and an optional time/radius, it returns:

- Sea Surface Temperature (SST)
- Chlorophyll-a
- PFZ status/score
- nearest ARGO profile information
- simple anomaly values when a baseline is available
- an explainable Ocean Opportunity Score
- evidence/source/timestamp metadata

The module is intentionally separated from the main ORCA brain. P1 can call this service and use the returned JSON in agent reasoning.

## Important data-source note

The included CSV files are DEMO data so the project runs immediately.

For the SIH prototype, replace the demo CSV values with data obtained from official/authorized sources. INCOIS publishes PFZ, SST and chlorophyll products and its PFZ WebGIS. ARGO data can be retrieved programmatically through Argovis or from the official Argo GDACs.

Do not claim that the demo values are live observations.

## Project structure

```text
orca_p2_ocean_intelligence/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── config.py
│   ├── scoring.py
│   └── services/
│       ├── ocean_service.py
│       ├── csv_provider.py
│       └── argo_provider.py
├── data/
│   ├── ocean_samples.csv
│   └── pfz_samples.csv
├── tests/
│   └── test_api.py
├── requirements.txt
├── .env.example
└── README.md
```

## 1. Install

Python 3.11+ recommended.

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Run

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 3. Test the demo endpoint

```text
GET /api/v1/ocean/conditions?lat=10.76&lon=79.84
```

Example:

```bash
curl "http://127.0.0.1:8000/api/v1/ocean/conditions?lat=10.76&lon=79.84"
```

## 4. Find candidate ocean zones

```text
GET /api/v1/ocean/candidates?lat=10.76&lon=79.84&radius_km=40
```

This returns the best demo candidate points sorted by ocean score.

## 5. ARGO

ARGO lookup is enabled by default.

The service uses the public Argovis API for a small spatial/time query. If internet access is unavailable, the API returns a graceful `argo.status = unavailable` result instead of crashing.

You can disable live ARGO temporarily:

```env
ARGO_ENABLED=false
```

## 6. What you should replace for the SIH build

### A. SST + Chlorophyll

Replace `data/ocean_samples.csv` with real observations or an ingestion pipeline from an approved source.

Minimum fields:

```text
timestamp,lat,lon,sst_c,chlorophyll_mg_m3
```

### B. PFZ

Replace `data/pfz_samples.csv` with current PFZ information obtained through the official INCOIS service/process available to your team.

Minimum fields:

```text
valid_date,lat,lon,pfz_score,status,sector,source
```

Do NOT scrape a web page blindly in the final system if an official machine-readable service is available to your team.

### C. Historical anomaly

Add historical baseline fields:

```text
sst_baseline_c
chlorophyll_baseline_mg_m3
```

Then the service can calculate:

```text
sst_anomaly = current_sst - baseline_sst
chlorophyll_anomaly = current_chlorophyll - baseline_chlorophyll
```

## 7. What P1 receives

P1 can call:

```text
GET /api/v1/ocean/conditions?lat=10.76&lon=79.84
```

and receive a structure similar to:

```json
{
  "location": {"lat": 10.76, "lon": 79.84},
  "ocean": {
    "sst_c": 29.3,
    "chlorophyll_mg_m3": 1.72,
    "pfz_score": 0.84,
    "pfz_status": "favourable",
    "ocean_opportunity_score": 84.2
  },
  "argo": {
    "status": "available",
    "nearest_profile_distance_km": 18.4
  },
  "anomalies": {
    "sst_c": 1.2,
    "chlorophyll_mg_m3": 0.35
  },
  "evidence": [...]
}
```

P1 should NOT need to know how these values were retrieved.

## 8. Recommended team boundary

P2 owns:

- ocean data retrieval
- ocean data cleaning
- spatial/temporal matching
- SST
- chlorophyll
- PFZ
- ARGO
- ocean anomaly calculations
- ocean opportunity score
- evidence metadata

P4 owns:

- map rendering
- geofencing
- route optimization

P3 owns:

- weather
- cyclone
- lightning
- waves
- safety score
- safety veto

P6 owns:

- deployment
- central API gateway
- database integration
- authentication

P1 owns:

- agent orchestration
- reasoning
- final decision

P5 owns:

- UI

## 9. Do not overclaim the science

A high chlorophyll value does NOT mean "fish definitely exist here".

The module therefore uses the wording:

- favourable
- potentially favourable
- moderate
- unfavourable

and combines PFZ with other variables.

The final fishing recommendation must also consider P3 safety outputs and P4 restrictions/routes.

## 10. Next implementation stage

After this module works:

1. Replace demo CSVs with approved live/near-real-time feeds.
2. Add a proper spatial database (PostGIS) through P6.
3. Add historical baselines for anomaly detection.
4. Add quality-control flags.
5. Add caching so repeated requests do not repeatedly download data.
6. Add dataset timestamps and provenance.
7. Give P1 a stable JSON contract.
