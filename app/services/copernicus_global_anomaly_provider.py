from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import copernicusmarine
import numpy as np
import xarray as xr


SST_DATASET = "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
SST_VARIABLE = "analysed_sst"

CHL_DATASET = (
    "cmems_obs-oc_glo_bgc-plankton_nrt_l3-multi-4km_P1D"
)
CHL_VARIABLE = "CHL"


class CopernicusGlobalAnomalyProvider:

    def __init__(self):
        self.project_root = (
            Path(__file__).resolve().parents[2]
        )

        self.cache_dir = (
            self.project_root
            / "data"
            / "copernicus_anomaly_cache"
        )

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _safe_name(value: float) -> str:
        return (
            f"{value:.3f}"
            .replace("-", "m")
            .replace(".", "_")
        )

    @staticmethod
    def _bounds(
        lat: float,
        lon: float,
        half_size: float = 0.1,
    ):
        return (
            max(-90.0, lat - half_size),
            min(90.0, lat + half_size),
            max(-180.0, lon - half_size),
            min(180.0, lon + half_size),
        )

    def _time_window(
        self,
        days: int,
    ):
        """
        Keep the request safely inside the currently
        available near-real-time dataset.

        A 3-day lag avoids asking for future observations.
        """

        end_time = (
            datetime.now(timezone.utc)
            - timedelta(days=3)
        )

        start_time = (
            end_time
            - timedelta(days=days - 1)
        )

        return (
            start_time.strftime(
                "%Y-%m-%dT00:00:00"
            ),
            end_time.strftime(
                "%Y-%m-%dT23:59:59"
            ),
        )

    def _download_subset(
        self,
        dataset_id: str,
        variable: str,
        lat: float,
        lon: float,
        days: int,
        prefix: str,
    ) -> Path:

        min_lat, max_lat, min_lon, max_lon = (
            self._bounds(
                lat,
                lon,
            )
        )

        start_date, end_date = (
            self._time_window(days)
        )

        filename = (
            f"{prefix}_"
            f"{self._safe_name(lat)}_"
            f"{self._safe_name(lon)}_"
            f"{days}d.nc"
        )

        output_file = (
            self.cache_dir / filename
        )

        if output_file.exists():
            return output_file

        result = copernicusmarine.subset(
            dataset_id=dataset_id,
            variables=[variable],
            minimum_longitude=min_lon,
            maximum_longitude=max_lon,
            minimum_latitude=min_lat,
            maximum_latitude=max_lat,
            start_datetime=start_date,
            end_datetime=end_date,
            output_directory=str(
                self.cache_dir
            ),
            output_filename=filename,
        )

        if output_file.exists():
            return output_file

        file_path = getattr(
            result,
            "file_path",
            None,
        )

        if file_path:
            path = Path(file_path)

            if path.exists():
                return path

        if isinstance(result, (str, Path)):
            path = Path(result)

            if path.exists():
                return path

        raise FileNotFoundError(
            "Copernicus anomaly subset was requested "
            "but the output file was not found: "
            f"{filename}"
        )

    @staticmethod
    def _nearest_pixel_series(
        da,
        lat: float,
        lon: float,
    ):
        """
        Select the nearest valid spatial pixel based on
        the latest available observation, then return the
        complete time series from that SAME pixel.
        """

        latitudes = da.latitude.values
        longitudes = da.longitude.values

        lat_grid, lon_grid = np.meshgrid(
            latitudes,
            longitudes,
            indexing="ij",
        )

        distance = np.sqrt(
            (lat_grid - lat) ** 2
            + (
                (lon_grid - lon)
                * np.cos(
                    np.radians(lat)
                )
            ) ** 2
        )

        for time_index in range(
            len(da.time) - 1,
            -1,
            -1,
        ):

            layer = da.isel(
                time=time_index
            )

            valid = np.isfinite(
                layer.values
            )

            if not valid.any():
                continue

            masked = np.where(
                valid,
                distance,
                np.inf,
            )

            index = np.unravel_index(
                np.argmin(masked),
                masked.shape,
            )

            series = da.isel(
                latitude=index[0],
                longitude=index[1],
            )

            return {
                "series": series,
                "latitude": float(
                    latitudes[index[0]]
                ),
                "longitude": float(
                    longitudes[index[1]]
                ),
            }

        return None

    @staticmethod
    def _calculate_anomaly(
        series,
        baseline_days: int,
        convert_kelvin: bool = False,
    ):
        values = np.asarray(
            series.values,
            dtype=float,
        )

        if convert_kelvin:
            values = values - 273.15

        valid = values[
            np.isfinite(values)
        ]

        if len(valid) < 2:
            return None

        latest = float(valid[-1])

        baseline_values = valid[
            -baseline_days:
        ]

        baseline_mean = float(
            np.mean(baseline_values)
        )

        anomaly = (
            latest
            - baseline_mean
        )

        if baseline_mean != 0:
            percentage = (
                anomaly
                / baseline_mean
                * 100
            )
        else:
            percentage = None

        return {
            "latest": latest,
            "baseline_mean": baseline_mean,
            "anomaly": anomaly,
            "percentage": percentage,
            "sample_count": len(
                baseline_values
            ),
        }

    def get_sst_anomaly(
        self,
        lat: float,
        lon: float,
        baseline_days: int = 30,
    ):

        try:

            file_path = self._download_subset(
                dataset_id=SST_DATASET,
                variable=SST_VARIABLE,
                lat=lat,
                lon=lon,
                days=baseline_days,
                prefix="sst_anomaly",
            )

            ds = xr.open_dataset(
                file_path
            )

            try:

                da = ds[
                    SST_VARIABLE
                ]

                selected = (
                    self._nearest_pixel_series(
                        da,
                        lat,
                        lon,
                    )
                )

                if selected is None:
                    return {
                        "status": "unavailable",
                        "reason": (
                            "No valid global SST "
                            "pixel found."
                        ),
                    }

                result = self._calculate_anomaly(
                    selected["series"],
                    baseline_days,
                    convert_kelvin=True,
                )

                if result is None:
                    return {
                        "status": "unavailable",
                        "reason": (
                            "Insufficient global SST "
                            "observations."
                        ),
                    }

                return {
                    "status": "available",
                    "variable": "sst_c",
                    "latest_c": round(
                        result["latest"],
                        2,
                    ),
                    "baseline_mean_c": round(
                        result["baseline_mean"],
                        2,
                    ),
                    "anomaly_c": round(
                        result["anomaly"],
                        2,
                    ),
                    "percentage": (
                        round(
                            result["percentage"],
                            2,
                        )
                        if result["percentage"]
                        is not None
                        else None
                    ),
                    "baseline_days": baseline_days,
                    "sample_count": result[
                        "sample_count"
                    ],
                    "latitude": selected[
                        "latitude"
                    ],
                    "longitude": selected[
                        "longitude"
                    ],
                    "source": "Copernicus Marine",
                    "dataset": SST_DATASET,
                    "coverage": "global",
                }

            finally:
                ds.close()

        except Exception as exc:

            return {
                "status": "error",
                "reason": str(exc),
            }

    def get_chlorophyll_anomaly(
        self,
        lat: float,
        lon: float,
        baseline_days: int = 15,
    ):

        try:

            file_path = self._download_subset(
                dataset_id=CHL_DATASET,
                variable=CHL_VARIABLE,
                lat=lat,
                lon=lon,
                days=baseline_days,
                prefix="chl_anomaly",
            )

            ds = xr.open_dataset(
                file_path
            )

            try:

                da = ds[
                    CHL_VARIABLE
                ]

                selected = (
                    self._nearest_pixel_series(
                        da,
                        lat,
                        lon,
                    )
                )

                if selected is None:
                    return {
                        "status": "unavailable",
                        "reason": (
                            "No valid global chlorophyll "
                            "pixel found."
                        ),
                    }

                result = self._calculate_anomaly(
                    selected["series"],
                    baseline_days,
                )

                if result is None:
                    return {
                        "status": "unavailable",
                        "reason": (
                            "Insufficient global "
                            "chlorophyll observations."
                        ),
                    }

                return {
                    "status": "available",
                    "variable": (
                        "chlorophyll_mg_m3"
                    ),
                    "latest_mg_m3": round(
                        result["latest"],
                        4,
                    ),
                    "baseline_mean_mg_m3": round(
                        result["baseline_mean"],
                        4,
                    ),
                    "anomaly_mg_m3": round(
                        result["anomaly"],
                        4,
                    ),
                    "percentage": (
                        round(
                            result["percentage"],
                            2,
                        )
                        if result["percentage"]
                        is not None
                        else None
                    ),
                    "baseline_days": baseline_days,
                    "sample_count": result[
                        "sample_count"
                    ],
                    "latitude": selected[
                        "latitude"
                    ],
                    "longitude": selected[
                        "longitude"
                    ],
                    "source": "Copernicus Marine",
                    "dataset": CHL_DATASET,
                    "unit": "mg/m3",
                    "coverage": "global",
                }

            finally:
                ds.close()

        except Exception as exc:

            return {
                "status": "error",
                "reason": str(exc),
            }