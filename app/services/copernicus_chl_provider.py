from pathlib import Path
import math

import numpy as np
import xarray as xr


class CopernicusChlorophyllProvider:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

        files = list(
            self.project_root.glob(
                "cmems_obs-oc_glo_bgc-plankton_nrt_l3-multi-4km_P1D_CHL_*.nc"
            )
        )

        if not files:
            raise FileNotFoundError(
                "Copernicus CHL .nc file not found in project folder"
            )

        self.file = files[0]

    @staticmethod
    def _distance_km(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:

        earth_radius_km = 6371.0

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)

        dlat = math.radians(
            lat2 - lat1
        )

        dlon = math.radians(
            lon2 - lon1
        )

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(dlon / 2) ** 2
        )

        return (
            2
            * earth_radius_km
            * math.atan2(
                math.sqrt(a),
                math.sqrt(1 - a),
            )
        )

    def _find_nearest_valid_pixel(
        self,
        data,
        ds,
        lat,
        lon,
    ):

        lat_grid, lon_grid = np.meshgrid(
            ds.latitude.values,
            ds.longitude.values,
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

        valid = np.isfinite(
            data.values
        )

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
            "value_mg_m3": float(
                data.values[index]
            ),
            "latitude": float(
                ds.latitude.values[
                    index[0]
                ]
            ),
            "longitude": float(
                ds.longitude.values[
                    index[1]
                ]
            ),
            "index": index,
        }

    def get_chlorophyll(
        self,
        lat: float,
        lon: float,
    ):

        ds = xr.open_dataset(
            self.file
        )

        try:

            for time_index in range(
                len(ds.time) - 1,
                -1,
                -1,
            ):

                data = ds["CHL"].isel(
                    time=time_index
                )

                result = (
                    self._find_nearest_valid_pixel(
                        data,
                        ds,
                        lat,
                        lon,
                    )
                )

                if result is None:
                    continue

                return {
                    "value_mg_m3": result[
                        "value_mg_m3"
                    ],
                    "latitude": result[
                        "latitude"
                    ],
                    "longitude": result[
                        "longitude"
                    ],
                    "observation_time": str(
                        ds.time.values[
                            time_index
                        ]
                    ),
                    "source": "Copernicus Marine",
                    "dataset": (
                        "cmems_obs-oc_glo_bgc_plankton_nrt_l3-multi-4km_P1D"
                    ),
                    "variable": "CHL",
                    "unit": "mg/m3",
                    "status": "available",
                }

            return {
                "value_mg_m3": None,
                "source": "Copernicus Marine",
                "status": "no_valid_observation",
            }

        finally:
            ds.close()

    def get_valid_points(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        max_points: int = 30,
    ) -> list[dict]:
        """
        Return real Copernicus CHL grid points inside
        the requested radius from the latest valid day.
        """

        ds = xr.open_dataset(
            self.file
        )

        try:

            selected_time = None
            selected_data = None

            # Find latest day with valid CHL values
            for time_index in range(
                len(ds.time) - 1,
                -1,
                -1,
            ):

                data = ds["CHL"].isel(
                    time=time_index
                )

                if np.isfinite(
                    data.values
                ).any():

                    selected_time = time_index
                    selected_data = data
                    break

            if selected_data is None:
                return []

            results = []

            for i, grid_lat in enumerate(
                ds.latitude.values
            ):

                for j, grid_lon in enumerate(
                    ds.longitude.values
                ):

                    value = (
                        selected_data.values[
                            i, j
                        ]
                    )

                    if not np.isfinite(
                        value
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

                    results.append(
                        {
                            "lat": float(
                                grid_lat
                            ),
                            "lon": float(
                                grid_lon
                            ),
                            "distance_km": round(
                                distance_km,
                                2,
                            ),
                            "chlorophyll_mg_m3": float(
                                value
                            ),
                            "observation_time": str(
                                ds.time.values[
                                    selected_time
                                ]
                            ),
                        }
                    )

            results.sort(
                key=lambda x:
                    x["distance_km"]
            )

            return results[:max_points]

        finally:

            ds.close()