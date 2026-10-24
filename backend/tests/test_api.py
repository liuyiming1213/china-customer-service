from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_knowledge_stats_exposes_expected_collections():
    response = TestClient(app).get("/api/knowledge/stats")
    assert response.status_code == 200
    assert set(response.json()) == {"support_cases", "policies", "terminology", "indexed_source"}
