from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone

import copernicusmarine
import numpy as np
import xarray as xr


SST_DATASET = "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
SST_VARIABLE = "analysed_sst"

CHL_DATASET = (
    "cmems_obs-oc_glo_bgc-plankton_nrt_l3-multi-4km_P1D"
)
CHL_VARIABLE = "CHL"


class CopernicusGlobalProvider:

    def __init__(self):
        self.project_root = (
            Path(__file__).resolve().parents[2]
        )

        self.cache_dir = (
            self.project_root
            / "data"
            / "copernicus_cache"
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

    @staticmethod
    def _distance_km(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:

        earth_radius_km = 6371.0

        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)

        dlat = np.radians(
            lat2 - lat1
        )

        dlon = np.radians(
            lon2 - lon1
        )

        a = (
            np.sin(dlat / 2) ** 2
            + np.cos(lat1_rad)
            * np.cos(lat2_rad)
            * np.sin(dlon / 2) ** 2
        )

        return float(
            2
            * earth_radius_km
            * np.arctan2(
                np.sqrt(a),
                np.sqrt(1 - a),
            )
        )

    @staticmethod
    def _search_sizes(
        lat: float,
        lon: float,
    ) -> list[float]:
        """
        Return progressively larger search windows.

        This is important when the requested coordinate is on land
        (for example a coastal city) or falls in a masked satellite
        pixel. The provider first tries a small box and then expands
        until a valid ocean pixel is found.
        """

        # Small -> medium -> large regional searches.
        # The final 2-degree search still keeps downloads practical.
        return [0.10, 0.25, 0.50, 1.00, 2.00]

    def _download_subset(
        self,
        dataset_id: str,
        variable: str,
        lat: float,
        lon: float,
        prefix: str,
        days: int = 3,
        half_size: float = 0.1,
    ) -> Path:

        min_lat, max_lat, min_lon, max_lon = (
            self._bounds(
                lat,
                lon,
                half_size=half_size,
            )
        )

        filename = (
            f"{prefix}_"
            f"{self._safe_name(lat)}_"
            f"{self._safe_name(lon)}_"
            f"b{self._safe_name(half_size)}_"
            f"{days}d.nc"
        )

        output_file = (
            self.cache_dir / filename
        )

        if output_file.exists():
            return output_file

        end_time = (
            datetime.now(timezone.utc)
            - timedelta(days=3)
        )

        start_time = (
            end_time
            - timedelta(days=days - 1)
        )

        start_date = (
            start_time.strftime(
                "%Y-%m-%dT00:00:00"
            )
        )

        end_date = (
            end_time.strftime(
                "%Y-%m-%dT23:59:59"
            )
        )

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

        if isinstance(
            result,
            (str, Path),
        ):
            path = Path(result)

            if path.exists():
                return path

        raise FileNotFoundError(
            "Copernicus subset was requested, "
            "but the output file was not found: "
            f"{filename}"
        )

    @staticmethod
    def _nearest_valid_value(
        data,
        latitudes,
        longitudes,
        lat,
        lon,
    ):

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

        valid = np.isfinite(data)

        if not valid.any():
            return None

        masked = np.where(
            valid,
            distance,
            np.inf,
        )

        index = np.unravel_index(
            np.argmin(masked),
            masked.shape,
        )

        return (
            float(data[index]),
            float(
                latitudes[
                    index[0]
                ]
            ),
            float(
                longitudes[
                    index[1]
                ]
            ),
        )

    def _find_latest_valid(
        self,
        dataset_id: str,
        variable: str,
        lat: float,
        lon: float,
        prefix: str,
        days: int = 3,
    ):
        """
        Search increasingly large boxes and return the latest
        valid observation nearest to the requested coordinate.
        """

        last_reason = "No valid observation found"

        for half_size in self._search_sizes(lat, lon):
            try:
                file_path = self._download_subset(
                    dataset_id=dataset_id,
                    variable=variable,
                    lat=lat,
                    lon=lon,
                    prefix=prefix,
                    days=days,
                    half_size=half_size,
                )
            except Exception as exc:
                last_reason = str(exc)
                continue

            ds = None

            try:
                ds = xr.open_dataset(file_path)

                if "time" not in ds.coords:
                    last_reason = (
                        "Copernicus dataset does not contain "
                        "a time coordinate."
                    )
                    continue

                for time_index in range(
                    len(ds.time) - 1,
                    -1,
                    -1,
                ):
                    layer = ds[
                        variable
                    ].isel(
                        time=time_index
                    )

                    result = self._nearest_valid_value(
                        layer.values,
                        ds.latitude.values,
                        ds.longitude.values,
                        lat,
                        lon,
                    )

                    if result is None:
                        continue

                    value, obs_lat, obs_lon = result

                    return {
                        "value": value,
                        "latitude": obs_lat,
                        "longitude": obs_lon,
                        "observation_time": str(
                            ds.time.values[
                                time_index
                            ]
                        ),
                        "search_half_size": half_size,
                    }

                last_reason = (
                    "No valid ocean pixel in the "
                    f"{half_size} degree search window."
                )

            except Exception as exc:
                last_reason = str(exc)

            finally:
                if ds is not None:
                    ds.close()

        return None

    def get_global_sst(
        self,
        lat: float,
        lon: float,
    ):

        result = self._find_latest_valid(
            dataset_id=SST_DATASET,
            variable=SST_VARIABLE,
            lat=lat,
            lon=lon,
            prefix="global_sst",
            days=3,
        )

        if result is None:
            return {
                "status": "unavailable",
                "reason": (
                    "No valid global SST observation found"
                ),
            }

        value_k = result["value"]

        return {
            "status": "available",
            "value_c": round(
                value_k - 273.15,
                2,
            ),
            "value_k": round(
                value_k,
                2,
            ),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "observation_time": result[
                "observation_time"
            ],
            "source": "Copernicus Marine",
            "dataset": SST_DATASET,
            "variable": SST_VARIABLE,
            "coverage": "global",
            "search_half_size_deg": result[
                "search_half_size"
            ],
        }

    def get_global_chlorophyll(
        self,
        lat: float,
        lon: float,
    ):

        result = self._find_latest_valid(
            dataset_id=CHL_DATASET,
            variable=CHL_VARIABLE,
            lat=lat,
            lon=lon,
            prefix="global_chl",
            days=3,
        )

        if result is None:
            return {
                "status": "unavailable",
                "reason": (
                    "No valid global chlorophyll "
                    "observation found"
                ),
            }

        value = result["value"]

        return {
            "status": "available",
            "value_mg_m3": round(
                value,
                4,
            ),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "observation_time": result[
                "observation_time"
            ],
            "source": "Copernicus Marine",
            "dataset": CHL_DATASET,
            "variable": CHL_VARIABLE,
            "unit": "mg/m3",
            "coverage": "global",
            "search_half_size_deg": result[
                "search_half_size"
            ],
        }

    def get_candidate_points(
        self,
        lat: float,
        lon: float,
        radius_km: float = 40,
        max_points: int = 20,
    ) -> list[dict]:
        """
        Generate real candidate ocean points from the
        global Copernicus chlorophyll grid.

        The search window is expanded when the requested
        point is on land or near a coastline.

        Each candidate gets:
        - latitude
        - longitude
        - distance
        - chlorophyll
        - nearest SST
        """

        try:
            # Convert requested radius to a rough degree span.
            # Add a small margin so coastal coordinates can still
            # discover nearby ocean cells.
            radius_half_size = max(
                0.10,
                min(
                    2.00,
                    radius_km / 111.0 + 0.10,
                ),
            )

            chl_file = None

            # Try the requested-radius box first. If it contains
            # no valid chlorophyll pixels, progressively expand.
            for half_size in sorted(
                {
                    0.10,
                    0.25,
                    0.50,
                    1.00,
                    radius_half_size,
                }
            ):
                if half_size > 2.00:
                    continue

                try:
                    chl_file = self._download_subset(
                        dataset_id=CHL_DATASET,
                        variable=CHL_VARIABLE,
                        lat=lat,
                        lon=lon,
                        prefix="candidate_chl",
                        days=3,
                        half_size=half_size,
                    )

                    test_ds = xr.open_dataset(chl_file)

                    try:
                        has_valid = False

                        for time_index in range(
                            len(test_ds.time) - 1,
                            -1,
                            -1,
                        ):
                            layer = test_ds[
                                CHL_VARIABLE
                            ].isel(
                                time=time_index
                            )

                            if np.isfinite(
                                layer.values
                            ).any():
                                has_valid = True
                                break

                        if has_valid:
                            break

                    finally:
                        test_ds.close()

                    chl_file = None

                except Exception:
                    chl_file = None

            if chl_file is None:
                # Repeat using the radius-derived box so that
                # the last successful file is captured correctly.
                final_half_size = min(
                    2.00,
                    max(
                        0.10,
                        radius_km / 111.0 + 0.10,
                    ),
                )

                for half_size in [
                    final_half_size,
                    1.00,
                    0.50,
                    0.25,
                    0.10,
                ]:
                    try:
                        candidate_file = (
                            self._download_subset(
                                dataset_id=CHL_DATASET,
                                variable=CHL_VARIABLE,
                                lat=lat,
                                lon=lon,
                                prefix="candidate_chl",
                                days=3,
                                half_size=half_size,
                            )
                        )

                        check_ds = xr.open_dataset(
                            candidate_file
                        )

                        try:
                            valid_found = any(
                                np.isfinite(
                                    check_ds[
                                        CHL_VARIABLE
                                    ]
                                    .isel(
                                        time=time_index
                                    )
                                    .values
                                ).any()
                                for time_index in range(
                                    len(check_ds.time)
                                    - 1,
                                    -1,
                                    -1,
                                )
                            )
                        finally:
                            check_ds.close()

                        if valid_found:
                            chl_file = candidate_file
                            break

                    except Exception:
                        continue

            if chl_file is None:
                return []

            chl_ds = xr.open_dataset(
                chl_file
            )

            try:
                selected_time = None
                selected_data = None

                for time_index in range(
                    len(chl_ds.time) - 1,
                    -1,
                    -1,
                ):
                    layer = chl_ds[
                        CHL_VARIABLE
                    ].isel(
                        time=time_index
                    )

                    if np.isfinite(
                        layer.values
                    ).any():
                        selected_time = time_index
                        selected_data = layer
                        break

                if selected_data is None:
                    return []

                candidates = []

                for i, grid_lat in enumerate(
                    chl_ds.latitude.values
                ):
                    for j, grid_lon in enumerate(
                        chl_ds.longitude.values
                    ):
                        chl_value = (
                            selected_data.values[
                                i, j
                            ]
                        )

                        if not np.isfinite(
                            chl_value
                        ):
                            continue

                        distance_km = (
                            self._distance_km(
                                lat,
                                lon,
                                float(grid_lat),
                                float(grid_lon),
                            )
                        )

                        if distance_km > radius_km:
                            continue

                        candidates.append(
                            {
                                "lat": float(grid_lat),
                                "lon": float(grid_lon),
                                "distance_km": round(
                                    distance_km,
                                    2,
                                ),
                                "chlorophyll_mg_m3": float(
                                    chl_value
                                ),
                                "observation_time": str(
                                    chl_ds.time.values[
                                        selected_time
                                    ]
                                ),
                            }
                        )

            finally:
                chl_ds.close()

            candidates.sort(
                key=lambda item:
                item["distance_km"]
            )

            candidates = candidates[
                :max_points
            ]

            final_candidates = []

            for candidate in candidates:
                sst = self.get_global_sst(
                    candidate["lat"],
                    candidate["lon"],
                )

                if (
                    not sst
                    or sst.get("status")
                    != "available"
                ):
                    continue

                final_candidates.append(
                    {
                        "lat": candidate["lat"],
                        "lon": candidate["lon"],
                        "distance_km": candidate[
                            "distance_km"
                        ],
                        "sst_c": sst[
                            "value_c"
                        ],
                        "chlorophyll_mg_m3": (
                            candidate[
                                "chlorophyll_mg_m3"
                            ]
                        ),
                        "sst_observation_time": (
                            sst[
                                "observation_time"
                            ]
                        ),
                        "chl_observation_time": (
                            candidate[
                                "observation_time"
                            ]
                        ),
                    }
                )

            return final_candidates

        except Exception:
            return []
