from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PFZInfo(BaseModel):
    status: str
    source: str
    uid: Optional[str] = None
    state: Optional[str] = None
    distance_km: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    length_km: Optional[float] = None
    advisory_date: Optional[str] = None


class OceanValues(BaseModel):
    sst_c: Optional[float] = None
    chlorophyll_mg_m3: Optional[float] = None
    pfz_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
    )
    pfz_status: str = "unknown"
    ocean_opportunity_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )
    pfz: Optional[PFZInfo] = None


class Anomalies(BaseModel):
    sst_c: Optional[float] = None
    chlorophyll_mg_m3: Optional[float] = None


class ArgoInfo(BaseModel):
    status: str
    nearest_profile_distance_km: Optional[float] = None
    profile_count: int = 0
    latest_profile_time: Optional[str] = None
    notes: Optional[str] = None


class Evidence(BaseModel):
    variable: str
    value: Any
    source: str
    timestamp: Optional[str] = None
    quality: Optional[str] = None


class OceanConditionsResponse(BaseModel):
    location: Location
    requested_at: datetime
    ocean: OceanValues
    anomalies: Anomalies
    argo: ArgoInfo
    evidence: list[Evidence]
    explanation: list[str]


class CandidateZone(BaseModel):
    location: Location
    distance_km: float
    sst_c: Optional[float] = None
    chlorophyll_mg_m3: Optional[float] = None
    pfz_score: Optional[float] = None
    pfz_status: str = "unknown"
    ocean_opportunity_score: Optional[float] = None