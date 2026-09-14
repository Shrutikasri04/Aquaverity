from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["module"] == "P2-Ocean-Intelligence"


def test_conditions():
    response = client.get(
        "/api/v1/ocean/conditions",
        params={"lat": 10.76, "lon": 79.84},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ocean"]["sst_c"] == 29.3
    assert body["ocean"]["pfz_score"] == 0.84
    assert body["ocean"]["ocean_opportunity_score"] is not None
    assert "evidence" in body


def test_candidates():
    response = client.get(
        "/api/v1/ocean/candidates",
        params={"lat": 10.76, "lon": 79.84, "radius_km": 40},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
