from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import xarray as xr


class OceanAnomalyProvider:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

    def _find_nearest_valid_pixel(
        self,
        da,
        lat: float,
        lon: float,
    ):
        """
        Find the nearest spatial pixel that contains
        at least one valid observation.
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
                * np.cos(np.radians(lat))
            ) ** 2
        )

        values = np.asarray(
            da.values,
            dtype=float,
        )

        valid = np.isfinite(values).any(axis=0)

        if not valid.any():
            return None

        distance_masked = np.where(
            valid,
            distance,
            np.inf,
        )

        index = np.unravel_index(
            np.argmin(distance_masked),
            distance_masked.shape,
        )

        return {
            "series": da.isel(
                latitude=index[0],
                longitude=index[1],
            ),
            "latitude": float(
                latitudes[index[0]]
            ),
            "longitude": float(
                longitudes[index[1]]
            ),
        }

    def _find_latest_valid_pixel(
        self,
        da,
        lat: float,
        lon: float,
    ):
        """
        Find the nearest valid pixel on the latest
        available observation.

        This matches the spatial selection logic used
        by CopernicusChlorophyllProvider.
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
                * np.cos(np.radians(lat))
            ) ** 2
        )

        for time_index in range(
            len(da.time) - 1,
            -1,
            -1,
        ):

            data = da.isel(time=time_index)

            valid = np.isfinite(
                data.values
            )

            if not valid.any():
                continue

            distance_masked = np.where(
                valid,
                distance,
                np.inf,
            )

            index = np.unravel_index(
                np.argmin(distance_masked),
                distance_masked.shape,
            )

            return {
                "series": da.isel(
                    latitude=index[0],
                    longitude=index[1],
                ),
                "latitude": float(
                    latitudes[index[0]]
                ),
                "longitude": float(
                    longitudes[index[1]]
                ),
            }

        return None

    def _calculate_anomaly(
        self,
        series,
        baseline_days: int,
    ):

        values = np.asarray(
            series.values,
            dtype=float,
        )

        valid = values[np.isfinite(values)]

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
            latest - baseline_mean
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

        pattern = str(
            self.project_root
            / "*METOFFICE*analysed_sst*.nc"
        )

        files = glob.glob(pattern)

        if not files:
            return {
                "status": "unavailable",
                "reason": "No Copernicus SST file found",
            }

        ds = None

        try:

            file_path = files[0]

            ds = xr.open_dataset(
                file_path
            )

            if "analysed_sst" not in ds:
                return {
                    "status": "unavailable",
                    "reason": (
                        "analysed_sst variable not found"
                    ),
                }

            da = ds["analysed_sst"]

            result_pixel = (
                self._find_nearest_valid_pixel(
                    da,
                    lat,
                    lon,
                )
            )

            if result_pixel is None:
                return {
                    "status": "unavailable",
                    "reason": (
                        "No valid SST series found"
                    ),
                }

            series = result_pixel["series"]

            # Kelvin -> Celsius
            values = (
                np.asarray(
                    series.values,
                    dtype=float,
                )
                - 273.15
            )

            series = xr.DataArray(
                values,
                dims=["time"],
                coords={
                    "time": da.time.values
                },
            )

            result = self._calculate_anomaly(
                series,
                baseline_days,
            )

            if result is None:
                return {
                    "status": "unavailable",
                    "reason": (
                        "Insufficient SST observations"
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
                "latitude": result_pixel[
                    "latitude"
                ],
                "longitude": result_pixel[
                    "longitude"
                ],
                "source": "Copernicus Marine",
                "dataset": (
                    "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
                ),
            }

        except Exception as exc:

            return {
                "status": "error",
                "reason": str(exc),
            }

        finally:

            if ds is not None:
                ds.close()

    def get_chlorophyll_anomaly(
        self,
        lat: float,
        lon: float,
        baseline_days: int = 15,
    ):

        pattern = str(
            self.project_root
            / "*cmems_obs-oc*glo_bgc*CHL*.nc"
        )

        files = glob.glob(pattern)

        if not files:
            return {
                "status": "unavailable",
                "reason": (
                    "No Copernicus chlorophyll file found"
                ),
            }

        ds = None

        try:

            file_path = files[0]

            ds = xr.open_dataset(
                file_path
            )

            if "CHL" not in ds:
                return {
                    "status": "unavailable",
                    "reason": "CHL variable not found",
                }

            da = ds["CHL"]

            # IMPORTANT:
            # Select the latest valid CHL pixel first.
            # This matches the current CHL provider.
            result_pixel = (
                self._find_latest_valid_pixel(
                    da,
                    lat,
                    lon,
                )
            )

            if result_pixel is None:
                return {
                    "status": "unavailable",
                    "reason": (
                        "No valid chlorophyll pixel found"
                    ),
                }

            series = result_pixel["series"]

            result = self._calculate_anomaly(
                series,
                baseline_days,
            )

            if result is None:
                return {
                    "status": "unavailable",
                    "reason": (
                        "Insufficient chlorophyll observations"
                    ),
                }

            return {
                "status": "available",
                "variable": "chlorophyll_mg_m3",
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
                "latitude": result_pixel[
                    "latitude"
                ],
                "longitude": result_pixel[
                    "longitude"
                ],
                "source": "Copernicus Marine",
                "dataset": (
                    "cmems_obs-oc_glo_bgc_plankton_nrt_l3-multi-4km_P1D"
                ),
            }

        except Exception as exc:

            return {
                "status": "error",
                "reason": str(exc),
            }

        finally:

            if ds is not None:
                ds.close()