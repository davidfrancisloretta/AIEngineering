import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Make app/ importable from the tests/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from main import app  # noqa: E402
from dependencies import get_db  # noqa: E402
from models import Base  # noqa: E402

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

SAMPLE_PAYLOAD = {
    "campaign_name": "Test Campaign",
    "impressions": 1000,
    "clicks": 100,
    "views": 200,
    "conversions": 50,
}


# --------------------------------------------------
# Health check
# --------------------------------------------------
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "AI Docker App Running Successfully"}


# --------------------------------------------------
# Create
# --------------------------------------------------
def test_create_metric():
    response = client.post("/metrics", json=SAMPLE_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["campaign_name"] == "Test Campaign"
    assert data["ttr"] == pytest.approx(0.1)
    assert data["vtr"] == pytest.approx(0.2)
    assert data["cvr"] == pytest.approx(0.05)
    assert "id" in data


def test_create_metric_zero_impressions():
    payload = {**SAMPLE_PAYLOAD, "impressions": 0}
    response = client.post("/metrics", json=payload)
    assert response.status_code == 422


def test_create_metric_negative_impressions():
    payload = {**SAMPLE_PAYLOAD, "impressions": -1}
    response = client.post("/metrics", json=payload)
    assert response.status_code == 422


# --------------------------------------------------
# Read all
# --------------------------------------------------
def test_get_all_metrics_empty():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_metrics():
    client.post("/metrics", json=SAMPLE_PAYLOAD)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert len(response.json()) == 1


# --------------------------------------------------
# Read single
# --------------------------------------------------
def test_get_metric_by_id():
    metric_id = client.post("/metrics", json=SAMPLE_PAYLOAD).json()["id"]
    response = client.get(f"/metrics/{metric_id}")
    assert response.status_code == 200
    assert response.json()["campaign_name"] == "Test Campaign"


def test_get_metric_not_found():
    response = client.get("/metrics/999")
    assert response.status_code == 404


# --------------------------------------------------
# Update
# --------------------------------------------------
def test_update_metric_name():
    metric_id = client.post("/metrics", json=SAMPLE_PAYLOAD).json()["id"]
    response = client.put(f"/metrics/{metric_id}", json={"campaign_name": "Renamed"})
    assert response.status_code == 200
    data = response.json()
    assert data["campaign_name"] == "Renamed"
    # Rates should remain unchanged
    assert data["ttr"] == pytest.approx(0.1)
    assert data["vtr"] == pytest.approx(0.2)
    assert data["cvr"] == pytest.approx(0.05)


def test_update_metric_recalculates_rates():
    metric_id = client.post("/metrics", json=SAMPLE_PAYLOAD).json()["id"]
    response = client.put(f"/metrics/{metric_id}", json={"clicks": 200})
    assert response.status_code == 200
    assert response.json()["ttr"] == pytest.approx(0.2)


def test_update_metric_not_found():
    response = client.put("/metrics/999", json={"campaign_name": "Ghost"})
    assert response.status_code == 404


# --------------------------------------------------
# Delete
# --------------------------------------------------
def test_delete_metric():
    metric_id = client.post("/metrics", json=SAMPLE_PAYLOAD).json()["id"]
    assert client.delete(f"/metrics/{metric_id}").status_code == 204
    assert client.get(f"/metrics/{metric_id}").status_code == 404


def test_delete_metric_not_found():
    response = client.delete("/metrics/999")
    assert response.status_code == 404
