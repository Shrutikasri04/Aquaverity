from pathlib import Path
import glob
import math

import numpy as np
import xarray as xr


class CopernicusSSTProvider:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

        pattern = str(
            self.project_root
            / "*METOFFICE*analysed_sst*.nc"
        )

        files = glob.glob(pattern)

        if not files:
            raise FileNotFoundError(
                "Copernicus OSTIA SST .nc file not found"
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

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

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

    def _latest_valid_layer(self, ds):
        """
        Return the latest SST layer containing
        at least one valid observation.
        """

        for time_index in range(
            len(ds.time) - 1,
            -1,
            -1,
        ):

            data = ds["analysed_sst"].isel(
                time=time_index
            )

            if np.isfinite(data.values).any():
                return (
                    data,
                    time_index,
                )

        return None, None

    def get_sst(
        self,
        lat: float,
        lon: float,
    ):

        ds = xr.open_dataset(self.file)

        try:

            data, time_index = (
                self._latest_valid_layer(ds)
            )

            if data is None:
                return {
                    "status": "unavailable",
                    "reason": (
                        "No valid SST observation found"
                    ),
                }

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

            distance_masked = np.where(
                valid,
                distance,
                np.inf,
            )

            index = np.unravel_index(
                np.argmin(distance_masked),
                distance_masked.shape,
            )

            value = float(
                data.values[index]
            )

            return {
                "status": "available",
                "value_c": round(
                    value - 273.15,
                    2,
                ),
                "value_k": round(
                    value,
                    2,
                ),
                "latitude": float(
                    ds.latitude.values[index[0]]
                ),
                "longitude": float(
                    ds.longitude.values[index[1]]
                ),
                "observation_time": str(
                    ds.time.values[time_index]
                ),
                "source": "Copernicus Marine",
                "dataset": (
                    "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
                ),
                "variable": "analysed_sst",
                "status": "available",
            }

        except Exception as exc:

            return {
                "status": "error",
                "reason": str(exc),
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
        Return real Copernicus SST grid points inside
        the requested radius.

        These points are later combined with real
        chlorophyll observations.
        """

        ds = xr.open_dataset(self.file)

        try:

            data, time_index = (
                self._latest_valid_layer(ds)
            )

            if data is None:
                return []

            results = []

            for i, grid_lat in enumerate(
                ds.latitude.values
            ):

                for j, grid_lon in enumerate(
                    ds.longitude.values
                ):

                    value = data.values[i, j]

                    if not np.isfinite(value):
                        continue

                    distance_km = self._distance_km(
                        lat,
                        lon,
                        float(grid_lat),
                        float(grid_lon),
                    )

                    if distance_km > radius_km:
                        continue

                    results.append(
                        {
                            "lat": float(grid_lat),
                            "lon": float(grid_lon),
                            "distance_km": round(
                                distance_km,
                                2,
                            ),
                            "sst_c": round(
                                float(value) - 273.15,
                                2,
                            ),
                            "observation_time": str(
                                ds.time.values[
                                    time_index
                                ]
                            ),
                        }
                    )

            results.sort(
                key=lambda x:
                    x["distance_km"]
            )

            # Keep the nearest real grid points.
            return results[:max_points]

        finally:

            ds.close()