from __future__ import annotations

from pathlib import Path
from typing import Optional

import math
import pandas as pd


class CSVOceanProvider:
    """
    Legacy/demo ocean provider.

    This provider is still used as a fallback by the main OceanService.
    Candidate generation is intentionally kept here for compatibility,
    but the primary real-data conditions endpoint uses:
      - Copernicus SST
      - Copernicus Chlorophyll
      - INCOIS PFZ
      - ARGO
    """

    def __init__(self, ocean_path: str, pfz_path: str):
        self.ocean = pd.read_csv(Path(ocean_path))
        self.pfz = pd.read_csv(Path(pfz_path))

        required_ocean = {
            "timestamp",
            "lat",
            "lon",
            "sst_c",
            "chlorophyll_mg_m3",
        }

        required_pfz = {
            "valid_date",
            "lat",
            "lon",
            "pfz_score",
            "status",
            "sector",
            "source",
        }

        missing_ocean = (
            required_ocean
            - set(self.ocean.columns)
        )

        missing_pfz = (
            required_pfz
            - set(self.pfz.columns)
        )

        if missing_ocean:
            raise ValueError(
                f"Missing ocean columns: "
                f"{sorted(missing_ocean)}"
            )

        if missing_pfz:
            raise ValueError(
                f"Missing PFZ columns: "
                f"{sorted(missing_pfz)}"
            )

    @staticmethod
    def _distance_km(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Equirectangular approximation suitable for
        small regional distances.
        """

        lat_scale = 111.0

        lon_scale = (
            111.0
            * max(
                0.1,
                abs(
                    math.cos(
                        math.radians(lat1)
                    )
                ),
            )
        )

        dlat = (
            lat2 - lat1
        ) * lat_scale

        dlon = (
            lon2 - lon1
        ) * lon_scale

        return math.sqrt(
            dlat * dlat
            + dlon * dlon
        )

    @classmethod
    def _nearest(
        cls,
        df: pd.DataFrame,
        lat: float,
        lon: float,
    ) -> Optional[pd.Series]:

        if df.empty:
            return None

        work = df.copy()

        work["_distance_km"] = work.apply(
            lambda row: cls._distance_km(
                lat,
                lon,
                float(row["lat"]),
                float(row["lon"]),
            ),
            axis=1,
        )

        return (
            work
            .sort_values("_distance_km")
            .iloc[0]
        )

    def get_ocean(
        self,
        lat: float,
        lon: float,
    ) -> Optional[dict]:

        row = self._nearest(
            self.ocean,
            lat,
            lon,
        )

        if row is None:
            return None

        return {
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "distance_km": float(
                row["_distance_km"]
            ),
            "timestamp": str(
                row["timestamp"]
            ),
            "sst_c": float(
                row["sst_c"]
            ),
            "chlorophyll_mg_m3": float(
                row["chlorophyll_mg_m3"]
            ),
            "sst_baseline_c": (
                float(
                    row["sst_baseline_c"]
                )
                if (
                    "sst_baseline_c" in row
                    and pd.notna(
                        row["sst_baseline_c"]
                    )
                )
                else None
            ),
            "chlorophyll_baseline_mg_m3": (
                float(
                    row[
                        "chlorophyll_baseline_mg_m3"
                    ]
                )
                if (
                    "chlorophyll_baseline_mg_m3"
                    in row
                    and pd.notna(
                        row[
                            "chlorophyll_baseline_mg_m3"
                        ]
                    )
                )
                else None
            ),
        }

    def get_pfz(
        self,
        lat: float,
        lon: float,
    ) -> Optional[dict]:

        row = self._nearest(
            self.pfz,
            lat,
            lon,
        )

        if row is None:
            return None

        return {
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "distance_km": float(
                row["_distance_km"]
            ),
            "valid_date": str(
                row["valid_date"]
            ),
            "pfz_score": float(
                row["pfz_score"]
            ),
            "status": str(
                row["status"]
            ),
            "sector": str(
                row["sector"]
            ),
            "source": str(
                row["source"]
            ),
        }

    def get_candidates(
        self,
        lat: float,
        lon: float,
        radius_km: float,
    ) -> list[dict]:
        """
        Return candidate zones from the legacy CSV data.

        NOTE:
        The main real-data candidate pipeline will be added
        separately using Copernicus + INCOIS. This method
        remains here so the existing API doesn't break.
        """

        if self.ocean.empty:
            return []

        df = self.ocean.copy()

        df["_distance_km"] = df.apply(
            lambda row: self._distance_km(
                lat,
                lon,
                float(row["lat"]),
                float(row["lon"]),
            ),
            axis=1,
        )

        df = df[
            df["_distance_km"] <= radius_km
        ].copy()

        results = []

        for _, row in df.iterrows():

            candidate_lat = float(
                row["lat"]
            )

            candidate_lon = float(
                row["lon"]
            )

            pfz = self._nearest(
                self.pfz,
                candidate_lat,
                candidate_lon,
            )

            results.append(
                {
                    "lat": candidate_lat,
                    "lon": candidate_lon,
                    "distance_km": round(
                        float(
                            row[
                                "_distance_km"
                            ]
                        ),
                        2,
                    ),
                    "sst_c": float(
                        row["sst_c"]
                    ),
                    "chlorophyll_mg_m3": float(
                        row[
                            "chlorophyll_mg_m3"
                        ]
                    ),
                    "pfz_score": (
                        float(
                            pfz["pfz_score"]
                        )
                        if pfz is not None
                        else None
                    ),
                    "pfz_status": (
                        str(
                            pfz["status"]
                        )
                        if pfz is not None
                        else "unknown"
                    ),
                }
            )

        return results