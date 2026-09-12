from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from safety_service import get_marine_conditions


app = FastAPI(
    title="ORCA Weather & Safety API",
    description="P3 Weather and Marine Safety Service",
    version="1.0.0"
)


class MarineRequest(BaseModel):
    latitude: float
    longitude: float
    target_time: str


@app.get("/")
def health_check():

    return {
        "service": "ORCA Weather & Safety",
        "status": "running"
    }


@app.post("/marine-conditions")
def marine_conditions(request: MarineRequest):

    try:

        result = get_marine_conditions(
            request.latitude,
            request.longitude,
            request.target_time
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Marine conditions unavailable."
            )

        return result

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )