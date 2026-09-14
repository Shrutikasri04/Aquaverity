from fastapi import FastAPI, HTTPException, Query

from app.config import settings

from app.services.argo_provider import ArgovisProvider
from app.services.csv_provider import CSVOceanProvider
from app.services.copernicus_global_provider import (
    CopernicusGlobalProvider,
)
from app.services.incois_pfz_provider import INCOISPFZProvider
from app.services.copernicus_global_anomaly_provider import (
    CopernicusGlobalAnomalyProvider,
)
from app.services.ocean_service import OceanService


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="P2 Ocean Intelligence module for ORCA.",
)


# ---------------------------------------------------------
# Demo / fallback ocean provider
# ---------------------------------------------------------
ocean_provider = CSVOceanProvider(
    settings.ocean_data_path,
    settings.pfz_data_path,
)


# ---------------------------------------------------------
# ARGO provider
# ---------------------------------------------------------
argo_provider = ArgovisProvider(
    enabled=settings.argo_enabled,
    base_url=settings.argo_api_base,
    search_days=settings.argo_search_days,
    radius_km=settings.argo_radius_km,
)


# ---------------------------------------------------------
# Global Copernicus provider
# ---------------------------------------------------------
global_provider = CopernicusGlobalProvider()

# Use the same global provider for both SST and CHL.
sst_provider = global_provider
chlorophyll_provider = global_provider


# ---------------------------------------------------------
# INCOIS PFZ provider
# ---------------------------------------------------------
pfz_provider = INCOISPFZProvider()


# ---------------------------------------------------------
# Ocean anomaly provider
# ---------------------------------------------------------
anomaly_provider = CopernicusGlobalAnomalyProvider()


# ---------------------------------------------------------
# Main Ocean Service
# ---------------------------------------------------------
service = OceanService(
    ocean_provider,
    argo_provider,
    chlorophyll_provider,
    sst_provider,
    pfz_provider,
    anomaly_provider,
)


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "module": "P2-Ocean-Intelligence",
        "argo_enabled": settings.argo_enabled,
        "copernicus_coverage": "global",
    }


# ---------------------------------------------------------
# Ocean conditions
# ---------------------------------------------------------
@app.get("/api/v1/ocean/conditions")
def ocean_conditions(
    lat: float = Query(
        ...,
        ge=-90,
        le=90,
    ),
    lon: float = Query(
        ...,
        ge=-180,
        le=180,
    ),
):
    try:
        return service.conditions(
            lat,
            lon,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ocean data retrieval failed: {exc}",
        )


# ---------------------------------------------------------
# Candidate ocean zones
# ---------------------------------------------------------
@app.get("/api/v1/ocean/candidates")
def ocean_candidates(
    lat: float = Query(
        ...,
        ge=-90,
        le=90,
    ),
    lon: float = Query(
        ...,
        ge=-180,
        le=180,
    ),
    radius_km: float = Query(
        40,
        gt=0,
        le=500,
    ),
):
    try:
        return service.candidates(
            lat,
            lon,
            radius_km,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Candidate retrieval failed: {exc}",
        )