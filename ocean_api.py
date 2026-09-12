import xarray as xr


INCOIS_WW3_URL = (
    "https://incois.gov.in/thredds/dodsC/"
    "osf/ww3/rsmc_combined_ww3_20260909.nc"
)


def validate_location(latitude, longitude):

    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")


def get_ocean_data(latitude, longitude, target_time):

    validate_location(latitude, longitude)

    try:

        dataset = xr.open_dataset(INCOIS_WW3_URL)

    except Exception as e:

        return {
            "error": True,
            "source": "INCOIS WW3",
            "message": str(e)
        }

    try:

        target = target_time[:16]
        matching_time = None

        for time in dataset["TIME"].values:

            time_string = str(time)[:16]

            if time_string == target:
                matching_time = time
                break

        if matching_time is None:
            return None

        selected = dataset.sel(
            IOYAXIS=latitude,
            IOXAXIS=longitude,
            TIME=matching_time,
            method="nearest"
        )

        actual_latitude = float(
            dataset["IOYAXIS"]
            .sel(IOYAXIS=latitude, method="nearest")
            .values
        )

        actual_longitude = float(
            dataset["IOXAXIS"]
            .sel(IOXAXIS=longitude, method="nearest")
            .values
        )

        return {
            "latitude": round(actual_latitude, 3),
            "longitude": round(actual_longitude, 3),

            "forecast_time": str(matching_time)[:19],

            "wave": {
                "significant_wave_height_m": round(
                    float(selected["HS"].values), 3
                ),

                "peak_wave_period_s": round(
                    float(selected["PWP"].values), 3
                ),

                "mean_wave_period_s": round(
                    float(selected["T02"].values), 3
                ),

                "mean_wave_direction_deg": round(
                    float(selected["MWD"].values), 3
                )
            },

            "wind": {
                "u_mps": round(
                    float(selected["UWND"].values), 3
                ),

                "v_mps": round(
                    float(selected["VWND"].values), 3
                )
            },

            "source": "INCOIS WW3"
        }

    finally:

        dataset.close()