import requests
import time


SACHET_ALERT_API = (
    "https://sachet.ndma.gov.in/"
    "cap_public_website/FetchAllAlertDetails"
)


def get_alerts():

    headers = {
        "User-Agent": "Mozilla/5.0 ORCA-Weather-Safety/1.0",
        "Accept": "application/json",
    }

    last_error = None

    for attempt in range(3):

        try:

            response = requests.get(
                SACHET_ALERT_API,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()

            try:
                data = response.json()

            except ValueError as e:

                last_error = (
                    f"Invalid JSON response from SACHET: {e}"
                )

                if attempt < 2:
                    time.sleep(2)
                    continue

                return {
                    "source": "SACHET-NDMA",
                    "data": [],
                    "error": True,
                    "message": last_error
                }

            return {
                "source": "SACHET-NDMA",
                "data": data
            }

        except requests.exceptions.RequestException as e:

            last_error = str(e)

            if attempt < 2:
                time.sleep(2)
                continue

            return {
                "source": "SACHET-NDMA",
                "data": [],
                "error": True,
                "message": last_error
            }

    return {
        "source": "SACHET-NDMA",
        "data": [],
        "error": True,
        "message": last_error or "Unknown SACHET error"
    }