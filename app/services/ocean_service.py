from __future__ import annotations

from datetime import datetime, timezone

from app.models import (
    Anomalies,
    ArgoInfo,
    CandidateZone,
    Evidence,
    Location,
    OceanConditionsResponse,
    OceanValues,
    PFZInfo,
)

from app.scoring import calculate_ocean_score, classify_pfz


class OceanService:

    def __init__(
        self,
        ocean_provider,
        argo_provider,
        chlorophyll_provider,
        sst_provider,
        pfz_provider,
        anomaly_provider,
    ):
        self.ocean_provider = ocean_provider
        self.argo_provider = argo_provider
        self.chlorophyll_provider = chlorophyll_provider
        self.sst_provider = sst_provider
        self.pfz_provider = pfz_provider
        self.anomaly_provider = anomaly_provider

    def conditions(
        self,
        lat,
        lon,
    ):
        # ==================================================
        # 1. GLOBAL SST
        # ==================================================

        sst_data = self.sst_provider.get_global_sst(
            lat,
            lon,
        )

        sst = None
        sst_source = None
        sst_timestamp = None

        if (
            sst_data
            and sst_data.get("status") == "available"
        ):
            sst = sst_data.get("value_c")
            sst_source = sst_data.get("source")
            sst_timestamp = sst_data.get("observation_time")

        # ==================================================
        # 2. GLOBAL CHLOROPHYLL
        # ==================================================

        chl_data = self.chlorophyll_provider.get_global_chlorophyll(
            lat,
            lon,
        )

        chl = None
        chl_source = None
        chl_timestamp = None

        if (
            chl_data
            and chl_data.get("status") == "available"
        ):
            chl = chl_data.get("value_mg_m3")
            chl_source = chl_data.get("source")
            chl_timestamp = chl_data.get("observation_time")

        # ==================================================
        # 3. NO DEMO DATA FOR GLOBAL OPERATION
        # ==================================================

        if sst is None and chl is None:
            raise ValueError(
                "No Copernicus ocean observations "
                "are available for this location."
            )

        # ==================================================
        # 4. GLOBAL ANOMALIES
        # ==================================================

        sst_anomaly_data = self.anomaly_provider.get_sst_anomaly(
            lat,
            lon,
            baseline_days=30,
        )

        chl_anomaly_data = self.anomaly_provider.get_chlorophyll_anomaly(
            lat,
            lon,
            baseline_days=15,
        )

        sst_anomaly = None
        chl_anomaly = None
        chl_baseline = None

        if (
            sst_anomaly_data
            and sst_anomaly_data.get("status") == "available"
        ):
            sst_anomaly = sst_anomaly_data.get("anomaly_c")

        if (
            chl_anomaly_data
            and chl_anomaly_data.get("status") == "available"
        ):
            chl_anomaly = chl_anomaly_data.get("anomaly_mg_m3")
            chl_baseline = chl_anomaly_data.get(
                "baseline_mean_mg_m3"
            )

        # ==================================================
        # 5. INCOIS PFZ
        # ==================================================

        real_pfz = self.pfz_provider.get_nearest_pfz(
            lat,
            lon,
        )

        # INCOIS PFZ is regional. If the provider returns
        # a very distant feature, do not treat it as relevant.
        if (
            real_pfz
            and real_pfz.get("status") == "available"
            and real_pfz.get("distance_km", 999999) > 100
        ):
            real_pfz = {
                "status": "unavailable",
                "reason": (
                    "INCOIS PFZ is outside the "
                    "supported regional coverage."
                ),
            }

        if (
            real_pfz
            and real_pfz.get("status") == "available"
        ):
            pfz_score = 1.0
            pfz_status = "favourable"
        else:
            pfz_score = None
            pfz_status = "unknown"

        # ==================================================
        # 6. OCEAN OPPORTUNITY SCORE
        # ==================================================

        score = calculate_ocean_score(
            sst,
            chl,
            pfz_score,
            sst_anomaly_c=sst_anomaly,
            chlorophyll_anomaly_mg_m3=chl_anomaly,
            chlorophyll_baseline_mg_m3=chl_baseline,
        )

        # ==================================================
        # 7. ARGO
        # ==================================================

        argo = self.argo_provider.nearest_profile(
            lat,
            lon,
        )

        argo = argo or {
            "status": "unavailable",
            "nearest_profile_distance_km": None,
            "profile_count": 0,
            "latest_profile_time": None,
            "notes": "No nearby ARGO profile metadata available.",
        }

        # ==================================================
        # 8. EVIDENCE LEDGER
        # ==================================================

        evidence = []

        if sst is not None:
            evidence.append(
                Evidence(
                    variable="sst_c",
                    value=sst,
                    source=sst_source,
                    timestamp=sst_timestamp,
                )
            )

        if chl is not None:
            evidence.append(
                Evidence(
                    variable="chlorophyll_mg_m3",
                    value=chl,
                    source=chl_source,
                    timestamp=chl_timestamp,
                )
            )

        if (
            sst_anomaly_data
            and sst_anomaly_data.get("status") == "available"
        ):
            evidence.append(
                Evidence(
                    variable="sst_anomaly_c",
                    value=sst_anomaly_data.get("anomaly_c"),
                    source=sst_anomaly_data.get(
                        "source",
                        "Copernicus Marine",
                    ),
                    timestamp=(
                        sst_anomaly_data.get("observation_time")
                        or sst_timestamp
                    ),
                )
            )

        if (
            chl_anomaly_data
            and chl_anomaly_data.get("status") == "available"
        ):
            evidence.append(
                Evidence(
                    variable="chlorophyll_anomaly_mg_m3",
                    value=chl_anomaly_data.get(
                        "anomaly_mg_m3"
                    ),
                    source=chl_anomaly_data.get(
                        "source",
                        "Copernicus Marine",
                    ),
                    timestamp=(
                        chl_anomaly_data.get("observation_time")
                        or chl_timestamp
                    ),
                )
            )

        if (
            real_pfz
            and real_pfz.get("status") == "available"
        ):
            evidence.append(
                Evidence(
                    variable="pfz",
                    value=f"{real_pfz.get('distance_km')} km",
                    source=real_pfz.get("source", "INCOIS"),
                    timestamp=real_pfz.get("advisory_date"),
                )
            )

        if argo:
            evidence.append(
                Evidence(
                    variable="argo",
                    value=argo.get("status", "unknown"),
                    source="Argovis / Argo",
                    timestamp=argo.get("latest_profile_time"),
                )
            )

        # ==================================================
        # 9. EXPLANATION
        # ==================================================

        explanation = []

        if score is not None:
            if score >= 75:
                explanation.append(
                    "Ocean indicators are collectively "
                    "favourable in this prototype."
                )
            elif score >= 50:
                explanation.append(
                    "Ocean indicators are moderate "
                    "in this prototype."
                )
            else:
                explanation.append(
                    "Ocean indicators are relatively "
                    "unfavourable in this prototype."
                )

        if (
            real_pfz
            and real_pfz.get("status") == "available"
        ):
            explanation.append(
                f"INCOIS reports a PFZ approximately "
                f"{real_pfz.get('distance_km', 0):.2f} km "
                f"from the requested location."
            )
        else:
            explanation.append(
                "INCOIS PFZ information is not "
                "available for this location."
            )

        if (
            sst_anomaly_data
            and sst_anomaly_data.get("status") == "available"
        ):
            sst_change = sst_anomaly_data.get("anomaly_c")

            if sst_change is not None:
                if abs(sst_change) >= 0.5:
                    direction = (
                        "above" if sst_change > 0 else "below"
                    )
                    explanation.append(
                        f"SST is {abs(sst_change):.2f}°C "
                        f"{direction} its 30-day baseline."
                    )
                else:
                    explanation.append(
                        "SST is close to its "
                        "30-day baseline."
                    )
        else:
            explanation.append(
                "SST anomaly is not available "
                "for this location."
            )

        if (
            chl_anomaly_data
            and chl_anomaly_data.get("status") == "available"
        ):
            chl_change = chl_anomaly_data.get("percentage")

            if chl_change is not None:
                if chl_change > 20:
                    explanation.append(
                        f"Chlorophyll is approximately "
                        f"{chl_change:.1f}% above its "
                        f"recent 15-day valid-observation "
                        f"baseline."
                    )
                elif chl_change < -20:
                    explanation.append(
                        f"Chlorophyll is approximately "
                        f"{abs(chl_change):.1f}% below its "
                        f"recent 15-day valid-observation "
                        f"baseline."
                    )
                else:
                    explanation.append(
                        "Chlorophyll is close to its "
                        "recent short-term baseline."
                    )
        else:
            explanation.append(
                "Chlorophyll anomaly is not available "
                "for this location."
            )

        # ==================================================
        # 10. FINAL RESPONSE
        # ==================================================

        return OceanConditionsResponse(
            location=Location(
                lat=lat,
                lon=lon,
            ),
            requested_at=datetime.now(timezone.utc),
            ocean=OceanValues(
                sst_c=sst,
                chlorophyll_mg_m3=chl,
                pfz_score=pfz_score,
                pfz_status=pfz_status,
                ocean_opportunity_score=score,
                pfz=(
                    PFZInfo(
                        status=real_pfz.get("status"),
                        source=real_pfz.get("source", "INCOIS"),
                        uid=real_pfz.get("uid"),
                        state=real_pfz.get("state"),
                        distance_km=real_pfz.get("distance_km"),
                        latitude=real_pfz.get("latitude"),
                        longitude=real_pfz.get("longitude"),
                        length_km=real_pfz.get("pfz_length_km"),
                        advisory_date=real_pfz.get("advisory_date"),
                    )
                    if (
                        real_pfz
                        and real_pfz.get("status") == "available"
                    )
                    else None
                ),
            ),
            anomalies=Anomalies(
                sst_c=sst_anomaly,
                chlorophyll_mg_m3=chl_anomaly,
            ),
            argo=ArgoInfo(**argo),
            evidence=evidence,
            explanation=explanation,
        )

    def candidates(
        self,
        lat,
        lon,
        radius_km,
    ):
        """
        Generate ranked candidate ocean zones using
        global Copernicus SST + chlorophyll data.

        Each candidate also uses local SST/chlorophyll anomaly
        evidence when available.

        INCOIS PFZ is added only when a nearby valid
        PFZ exists.
        """

        candidate_points = self.sst_provider.get_candidate_points(
            lat,
            lon,
            radius_km,
            max_points=20,
        )

        if not candidate_points:
            return []

        result = []

        for point in candidate_points:
            candidate_lat = point["lat"]
            candidate_lon = point["lon"]

            sst = point.get("sst_c")
            chl = point.get("chlorophyll_mg_m3")

            # ----------------------------------------------
            # Local anomaly evidence
            # ----------------------------------------------

            sst_anomaly_data = self.anomaly_provider.get_sst_anomaly(
                candidate_lat,
                candidate_lon,
                baseline_days=30,
            )

            chl_anomaly_data = (
                self.anomaly_provider.get_chlorophyll_anomaly(
                    candidate_lat,
                    candidate_lon,
                    baseline_days=15,
                )
            )

            sst_anomaly = None
            chl_anomaly = None
            chl_baseline = None

            if (
                sst_anomaly_data
                and sst_anomaly_data.get("status") == "available"
            ):
                sst_anomaly = sst_anomaly_data.get("anomaly_c")

            if (
                chl_anomaly_data
                and chl_anomaly_data.get("status") == "available"
            ):
                chl_anomaly = chl_anomaly_data.get(
                    "anomaly_mg_m3"
                )
                chl_baseline = chl_anomaly_data.get(
                    "baseline_mean_mg_m3"
                )

            # ----------------------------------------------
            # PFZ
            # ----------------------------------------------

            pfz_data = self.pfz_provider.get_nearest_pfz(
                candidate_lat,
                candidate_lon,
            )

            pfz_score = None
            pfz_status = "unknown"

            if (
                pfz_data
                and pfz_data.get("status") == "available"
                and pfz_data.get("distance_km", 999999) <= 100
            ):
                pfz_distance = pfz_data.get(
                    "distance_km",
                    999999,
                )

                # Prototype proximity score.
                pfz_score = max(
                    0.0,
                    min(
                        1.0,
                        1.0 - (pfz_distance / 40.0),
                    ),
                )

                pfz_status = classify_pfz(pfz_score)

            # ----------------------------------------------
            # Ocean Opportunity Score
            # ----------------------------------------------

            score = calculate_ocean_score(
                sst,
                chl,
                pfz_score,
                sst_anomaly_c=sst_anomaly,
                chlorophyll_anomaly_mg_m3=chl_anomaly,
                chlorophyll_baseline_mg_m3=chl_baseline,
            )

            result.append(
                CandidateZone(
                    location=Location(
                        lat=candidate_lat,
                        lon=candidate_lon,
                    ),
                    distance_km=point["distance_km"],
                    sst_c=sst,
                    chlorophyll_mg_m3=chl,
                    pfz_score=pfz_score,
                    pfz_status=pfz_status,
                    ocean_opportunity_score=score,
                )
            )

        return sorted(
            result,
            key=lambda x: (
                x.ocean_opportunity_score
                if x.ocean_opportunity_score is not None
                else -1
            ),
            reverse=True,
        )
